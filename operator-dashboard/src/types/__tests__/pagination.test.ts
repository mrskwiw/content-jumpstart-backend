/**
 * Regression test for Bug #251: the backend sends `next_cursor`/`prev_cursor`
 * as JSON `null` (not omitted) on every offset-paginated response — Pydantic's
 * `Optional[str] = None` serializes to `null`. `PaginationMetadataSchema`
 * previously declared those fields `.optional()`, which Zod only treats as
 * "may be undefined", not "may be null" — so parsing a real response threw a
 * ZodError, and every list page (Projects, and ClientDetail which reuses the
 * same query) rendered "Failed to load projects." despite a clean 200.
 */
import { describe, it, expect } from '@jest/globals';
import { PaginationMetadataSchema, createPaginatedResponseSchema } from '@/types/pagination';
import { ProjectSchema } from '@/types/domain';

describe('PaginationMetadataSchema', () => {
  it('accepts the real offset-pagination shape the backend actually sends (null cursors)', () => {
    const realMetadata = {
      total: 25,
      page: 1,
      page_size: 20,
      total_pages: 2,
      has_next: true,
      has_prev: false,
      next_cursor: null,
      prev_cursor: null,
      strategy: 'offset',
    };

    const result = PaginationMetadataSchema.safeParse(realMetadata);
    expect(result.success).toBe(true);
  });

  it('still accepts cursors omitted entirely (cursor-pagination first page)', () => {
    const result = PaginationMetadataSchema.safeParse({
      page_size: 20,
      has_next: true,
      has_prev: false,
      strategy: 'cursor',
    });
    expect(result.success).toBe(true);
  });

  it('still accepts a real string cursor', () => {
    const result = PaginationMetadataSchema.safeParse({
      page_size: 20,
      has_next: true,
      has_prev: true,
      next_cursor: '2026-07-13T10:52:17:proj-abc123',
      strategy: 'cursor',
    });
    expect(result.success).toBe(true);
  });
});

describe('createPaginatedResponseSchema(ProjectSchema) — the projects list response', () => {
  it('parses a real /api/projects page-1 response without throwing', () => {
    const schema = createPaginatedResponseSchema(ProjectSchema);
    const realResponse = {
      items: [
        {
          id: 'proj-2bdf6612a500',
          clientId: 'client-ace6bddabaf3',
          name: 'Stumptown Coffee Roasters - Content Project',
          status: 'draft',
          templates: [],
          templateQuantities: {},
          numPosts: null,
          pricePerPost: 0.0,
          researchPricePerPost: 0.0,
          totalPrice: 0.0,
          postsCost: null,
          researchAddonCost: 0.0,
          toolsCost: null,
          discountAmount: null,
          selectedTools: null,
          platforms: [],
          targetPlatform: 'generic',
          tone: 'professional',
          createdAt: '2026-07-13T10:52:17.635562+00:00',
          updatedAt: null,
        },
      ],
      metadata: {
        total: 25,
        page: 1,
        page_size: 20,
        total_pages: 2,
        has_next: true,
        has_prev: false,
        next_cursor: null,
        prev_cursor: null,
        strategy: 'offset',
      },
    };

    expect(() => schema.parse(realResponse)).not.toThrow();
  });
});
