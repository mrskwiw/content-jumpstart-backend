/**
 * Pagination types for Week 3 backend optimization
 *
 * The backend now uses hybrid pagination (offset + cursor)
 * that automatically selects the best strategy based on page depth.
 */

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
  next_cursor?: string;

  /** Cursor for previous page (cursor pagination only) */
  prev_cursor?: string;

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
