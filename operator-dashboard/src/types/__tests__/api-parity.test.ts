/**
 * API type parity check.
 *
 * Guards against drift between the hand-written Zod domain schemas (the canonical
 * source of truth, see ../domain.ts) and the backend OpenAPI contract. For each
 * core read model we assert that every field the backend serializes is represented
 * in the domain schema, so backend additions can't be silently dropped by Zod's
 * unknown-key stripping (this is exactly how `recommendedPlatforms` went missing).
 *
 * The contract is `openapi.json`, regenerated from the FastAPI app via
 * `npm run generate:openapi`. Keep it fresh when backend response models change.
 *
 * If this test fails:
 *   - add the new field to the matching schema in domain.ts, OR
 *   - if the frontend intentionally does not consume the field, add it to the
 *     case's `ignore` list below (with a comment explaining why).
 */
import { describe, it, expect } from '@jest/globals';
import { readFileSync, existsSync } from 'fs';
import { join } from 'path';
import type { z } from 'zod';
import { ClientSchemaInput, ProjectSchema, RunSchema } from '@/types/domain';

interface OpenApiDoc {
  components: { schemas: Record<string, { properties?: Record<string, unknown> }> };
}

const OPENAPI_PATH = join(process.cwd(), 'openapi.json');

interface ParityCase {
  /** Backend OpenAPI component schema name (the response model). */
  schemaName: string;
  /** Canonical Zod object schema in domain.ts. */
  zod: z.ZodObject<z.ZodRawShape>;
  /** Backend fields the frontend intentionally ignores (document each). */
  ignore?: string[];
}

const CASES: ParityCase[] = [
  { schemaName: 'ClientResponse', zod: ClientSchemaInput },
  { schemaName: 'ProjectResponse', zod: ProjectSchema },
  { schemaName: 'RunResponse', zod: RunSchema },
];

describe('API type parity: domain.ts covers the backend response contract', () => {
  it('has a generated openapi.json to check against', () => {
    expect(existsSync(OPENAPI_PATH)).toBe(true);
  });

  const openapi: OpenApiDoc = JSON.parse(readFileSync(OPENAPI_PATH, 'utf-8'));

  it.each(CASES)(
    '$schemaName: every backend field exists in the domain schema',
    ({ schemaName, zod, ignore = [] }) => {
      const backend = openapi.components.schemas[schemaName];
      expect(backend).toBeDefined();

      const backendFields = Object.keys(backend.properties ?? {});
      const domainFields = new Set(Object.keys(zod.shape));
      const missing = backendFields.filter(
        (field) => !domainFields.has(field) && !ignore.includes(field),
      );

      // A non-empty list means the backend serializes fields the frontend would
      // silently drop. Fix domain.ts or add to `ignore` above.
      expect(missing).toEqual([]);
    },
  );
});
