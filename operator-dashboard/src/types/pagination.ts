/**
 * Pagination types for Week 3 backend optimization
 *
 * The backend now uses hybrid pagination (offset + cursor)
 * that automatically selects the best strategy based on page depth.
 */

import { z } from 'zod';

export const PaginationMetadataSchema = z.object({
  total: z.number().int().optional(),
  page: z.number().int().optional(),
  page_size: z.number().int(),
  total_pages: z.number().int().optional(),
  has_next: z.boolean(),
  has_prev: z.boolean(),
  next_cursor: z.string().nullish(),
  prev_cursor: z.string().nullish(),
  strategy: z.enum(['offset', 'cursor']),
});

export interface PaginationMetadata {
  /** Total number of items across all pages */
  total?: number;

  /** Current page number (1-indexed) */
  page?: number;

  /** Number of items per page */
  page_size: number;

  /** Total number of pages (only for offset pagination) */
  total_pages?: number;

  /** Whether there's a next page */
  has_next: boolean;

  /** Whether there's a previous page */
  has_prev: boolean;

  /** Cursor for next page (cursor pagination only) */
  next_cursor?: string | null;

  /** Cursor for previous page (cursor pagination only) */
  prev_cursor?: string | null;

  /** Pagination strategy used: "offset" or "cursor" */
  strategy: 'offset' | 'cursor';
}

export interface PaginatedResponse<T> {
  /** Array of items for current page */
  items: T[];

  /** Pagination metadata */
  metadata: PaginationMetadata;
}

export interface PaginationParams {
  /** Page number (1-indexed, for offset pagination) */
  page?: number;

  /** Cursor for keyset pagination (for deep pagination) */
  cursor?: string;

  /** Number of items per page (default: 20) */
  page_size?: number;
}

/**
 * Helper to create initial pagination params
 */
export const createPaginationParams = (
  page: number = 1,
  pageSize: number = 20
): PaginationParams => ({
  page,
  page_size: pageSize,
});

/**
 * Helper to check if we should use cursor pagination
 * Backend automatically switches at page 6 (offset > 100)
 */
export const shouldUseCursor = (page: number): boolean => {
  return page > 5;
};

/**
 * Helper to create a PaginatedResponse Zod schema for a specific item type
 * Usage: createPaginatedResponseSchema(ProjectSchema)
 */
export const createPaginatedResponseSchema = <T extends z.ZodTypeAny>(itemSchema: T) => {
  return z.object({
    items: z.array(itemSchema),
    metadata: PaginationMetadataSchema,
  });
};
