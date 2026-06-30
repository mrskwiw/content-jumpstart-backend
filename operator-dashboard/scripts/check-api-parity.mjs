#!/usr/bin/env node
/**
 * API type parity check (tracked + CI-enforceable).
 *
 * Ensures the canonical Zod domain schemas (src/types/domain.ts) cover every field
 * the backend serializes in its OpenAPI contract (openapi.json), so backend
 * additions can't be silently dropped by Zod's unknown-key stripping. This is the
 * durable counterpart to the local jest test src/types/__tests__/api-parity.test.ts.
 *
 * Pure Node (no Python/backend needed): it checks domain.ts against the COMMITTED
 * openapi.json, so it runs anywhere — including the frontend-only CI build.
 *
 * Usage:
 *   npm run check:parity          # also runs automatically in prebuild
 *   npm run generate:openapi      # refresh openapi.json when the backend changes
 *
 * On failure: add the missing field to the matching schema in src/types/domain.ts,
 * or add it to the case's `ignore` list below (with a comment explaining why).
 */
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, '..'); // operator-dashboard/
const OPENAPI_PATH = join(root, 'openapi.json');
const DOMAIN_PATH = join(root, 'src', 'types', 'domain.ts');

/**
 * Core read models to keep in parity.
 * zodConst = `const <name> = z.object({...})` in domain.ts
 * schema   = backend OpenAPI component schema name (the response model)
 * ignore   = backend fields the frontend intentionally does not consume
 */
const CASES = [
  { zodConst: 'ClientSchemaInput', schema: 'ClientResponse', ignore: [] },
  { zodConst: 'ProjectSchema', schema: 'ProjectResponse', ignore: [] },
  { zodConst: 'RunSchema', schema: 'RunResponse', ignore: [] },
];

/**
 * Extract the top-level (depth-1) field names of a Zod object literal from source.
 * Walks the matching braces of `const <constName> = z.object({ ... })` and collects
 * keys declared at the object's own level (nested object keys are ignored).
 */
function extractZodFields(src, constName) {
  const decl = `const ${constName} = z.object({`;
  const start = src.indexOf(decl);
  if (start === -1) {
    throw new Error(`Could not find Zod schema '${constName}' in domain.ts`);
  }

  // Capture the object body via brace matching, starting at the opening '{'.
  let i = src.indexOf('{', start);
  let depth = 0;
  let body = '';
  for (; i < src.length; i++) {
    const ch = src[i];
    if (ch === '{') depth++;
    if (depth >= 1) body += ch;
    if (ch === '}') {
      depth--;
      if (depth === 0) break;
    }
  }

  // Collect keys that appear at depth 1 (line-by-line; brace depth tracked across lines).
  const fields = new Set();
  let d = 0;
  for (const line of body.split('\n')) {
    if (d === 1) {
      const m = /^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:/.exec(line);
      if (m) fields.add(m[1]);
    }
    for (const c of line) {
      if (c === '{') d++;
      else if (c === '}') d--;
    }
  }
  return fields;
}

function loadOpenApi() {
  // Never trust the artifact blindly: a missing/empty/invalid contract must FAIL
  // loudly, not pass silently or crash opaquely. Freshness vs the live backend is
  // enforced separately by `npm run check:openapi-fresh` (generate-openapi.mjs --check).
  if (!existsSync(OPENAPI_PATH)) {
    console.error('✖ openapi.json not found. Run: npm run generate:openapi');
    process.exit(1);
  }
  const raw = readFileSync(OPENAPI_PATH, 'utf8').trim();
  if (!raw) {
    console.error('✖ openapi.json is empty (generation likely failed). Run: npm run generate:openapi');
    process.exit(1);
  }
  let doc;
  try {
    doc = JSON.parse(raw);
  } catch (e) {
    console.error(`✖ openapi.json is not valid JSON: ${e.message}. Run: npm run generate:openapi`);
    process.exit(1);
  }
  if (!doc.components?.schemas || Object.keys(doc.components.schemas).length === 0) {
    console.error('✖ openapi.json has no component schemas. Run: npm run generate:openapi');
    process.exit(1);
  }
  return doc;
}

function main() {
  const openapi = loadOpenApi();
  const domainSrc = readFileSync(DOMAIN_PATH, 'utf8');
  const schemas = openapi.components?.schemas ?? {};

  let failed = false;
  for (const { zodConst, schema, ignore } of CASES) {
    const backend = schemas[schema];
    if (!backend) {
      console.error(`✖ ${schema}: not found in openapi.json (regenerate with npm run generate:openapi)`);
      failed = true;
      continue;
    }
    const backendFields = Object.keys(backend.properties ?? {});
    const domainFields = extractZodFields(domainSrc, zodConst);
    const missing = backendFields.filter((f) => !domainFields.has(f) && !ignore.includes(f));
    if (missing.length > 0) {
      console.error(`✖ ${schema} → ${zodConst}: domain schema missing backend field(s): ${missing.join(', ')}`);
      failed = true;
    } else {
      console.log(`✓ ${schema} → ${zodConst}: ${backendFields.length} backend fields covered`);
    }
  }

  if (failed) {
    console.error(
      '\nAPI type parity FAILED. Add the field(s) to src/types/domain.ts, ' +
        'or to the case\'s ignore list in scripts/check-api-parity.mjs.',
    );
    process.exit(1);
  }
  console.log('\nAPI type parity OK.');
}

main();
