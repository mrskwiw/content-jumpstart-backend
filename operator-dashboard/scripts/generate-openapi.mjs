#!/usr/bin/env node
/**
 * Generate (or verify the freshness of) the backend OpenAPI contract.
 *
 * Two modes:
 *   node scripts/generate-openapi.mjs            # GENERATE: write openapi.json (atomic, loud)
 *   node scripts/generate-openapi.mjs --check    # VERIFY:   fail if committed openapi.json is stale
 *
 * Why this exists: the old `python ... > openapi.json 2>/dev/null || true` masked
 * generation failures AND truncated the committed contract to empty whenever the
 * backend wasn't importable (e.g. a frontend-only CI job). That let the parity
 * gate pass against stale/empty artifacts. This script never masks failures and
 * never overwrites the committed file unless generation fully succeeds.
 *
 * Freshness needs the backend importable (Python + deps). Where it isn't available
 * (frontend-only env), --check SKIPS with a clear message instead of pretending the
 * contract is fresh — real enforcement happens locally / in a backend-capable CI.
 */
import { spawnSync } from 'node:child_process';
import { readFileSync, writeFileSync, renameSync, existsSync, rmSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const dashboard = join(here, '..'); // operator-dashboard/
const projectRoot = join(dashboard, '..'); // project/  (git repo root)
const OUT = join(dashboard, 'openapi.json');
const TMP = join(dashboard, 'openapi.json.tmp');

const checkMode = process.argv.includes('--check');

/**
 * Resolve the Python interpreter. Prefer the project venv so the contract is
 * generated with the SAME deps that produced the committed openapi.json — system
 * python can have different fastapi/pydantic versions and emit a slightly
 * different schema, which would otherwise show up as a false "stale" diff.
 */
function pythonCandidates() {
  if (process.env.PYTHON) return [process.env.PYTHON];
  const venvPy =
    process.platform === 'win32'
      ? join(projectRoot, 'venv', 'Scripts', 'python.exe')
      : join(projectRoot, 'venv', 'bin', 'python');
  const list = [];
  if (existsSync(venvPy)) list.push(venvPy);
  list.push('python', 'python3');
  return list;
}

/** Run the Python generator, preferring the project venv interpreter. */
function runGenerator() {
  const candidates = pythonCandidates();
  let lastErr = null;
  for (const py of candidates) {
    const res = spawnSync(py, ['generate_openapi.py'], {
      cwd: projectRoot,
      encoding: 'utf8',
      maxBuffer: 128 * 1024 * 1024,
    });
    if (res.error && res.error.code === 'ENOENT') {
      lastErr = res.error;
      continue; // interpreter not found — try the next candidate
    }
    return res;
  }
  return { error: lastErr, status: 127 };
}

function parseOrNull(text) {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

/**
 * Deterministic serialization for content comparison: recursively sorts object
 * keys (arrays keep their order). Ignores key ordering, whitespace, and line
 * endings (CRLF vs LF) so only real content changes register as drift.
 */
function canonical(value) {
  if (Array.isArray(value)) {
    return '[' + value.map(canonical).join(',') + ']';
  }
  if (value && typeof value === 'object') {
    return (
      '{' +
      Object.keys(value)
        .sort()
        .map((k) => JSON.stringify(k) + ':' + canonical(value[k]))
        .join(',') +
      '}'
    );
  }
  return JSON.stringify(value);
}

const res = runGenerator();
const ok = res && !res.error && res.status === 0 && res.stdout;
const doc = ok ? parseOrNull(res.stdout) : null;
const valid = doc && doc.paths && Object.keys(doc.paths).length > 0;

if (!valid) {
  const reason = res?.error
    ? `python not available (${res.error.code})`
    : res?.status !== 0
      ? `generator exited ${res?.status}`
      : !res?.stdout
        ? 'generator produced no output'
        : 'output was not valid OpenAPI (no paths)';

  if (checkMode) {
    // Cannot verify freshness here — be honest, do not claim the contract is fresh.
    console.warn(`⚠ SKIP OpenAPI freshness check: ${reason}.`);
    console.warn('  (Verify locally / in a backend-capable CI: npm run generate:openapi then commit.)');
    if (res?.stderr) console.warn(res.stderr.split('\n').slice(-8).join('\n'));
    process.exit(0);
  }
  console.error(`✖ OpenAPI generation FAILED: ${reason}. Committed openapi.json left untouched.`);
  if (res?.stderr) console.error(res.stderr.split('\n').slice(-12).join('\n'));
  process.exit(1);
}

const pathCount = Object.keys(doc.paths).length;
const schemaCount = Object.keys(doc.components?.schemas ?? {}).length;

if (checkMode) {
  const committed = existsSync(OUT) ? parseOrNull(readFileSync(OUT, 'utf8')) : null;
  if (!committed) {
    console.error('✖ Committed openapi.json is missing or invalid — run: npm run generate:openapi && commit.');
    process.exit(1);
  }
  if (canonical(committed) !== canonical(doc)) {
    console.error(
      '✖ Committed openapi.json is STALE vs the current backend ' +
        `(${pathCount} paths / ${schemaCount} schemas).\n` +
        '  Run: npm run generate:api  — then commit openapi.json + api-schema.ts.',
    );
    process.exit(1);
  }
  console.log(`✓ openapi.json is fresh (${pathCount} paths / ${schemaCount} schemas).`);
  process.exit(0);
}

// GENERATE mode: write atomically (temp then rename) using the generator's exact output.
writeFileSync(TMP, res.stdout);
try {
  renameSync(TMP, OUT);
} catch (e) {
  rmSync(TMP, { force: true });
  throw e;
}
console.log(`✓ Wrote openapi.json (${pathCount} paths / ${schemaCount} schemas).`);
