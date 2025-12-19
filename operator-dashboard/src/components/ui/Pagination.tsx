/**
 * Pagination component for Week 3 backend optimization
 *
 * Supports both offset and cursor-based pagination:
 * - Pages 1-5: Shows page numbers and total count
 * - Pages 6+: Shows only Previous/Next (cursor pagination)
 */
import { ChevronLeft, ChevronRight } from 'lucide-react';
import type { PaginationMetadata } from '@/types/pagination';

export interface PaginationProps {
  /** Pagination metadata from API response */
  metadata?: PaginationMetadata;

  /** Current page number (1-indexed) */
  currentPage: number;

  /** Callback when page changes */
  onPageChange: (page: number) => void;

  /** Callback when cursor changes (for cursor pagination) */
  onCursorChange?: (cursor: string) => void;

  /** Show items per page selector */
  showPageSize?: boolean;

  /** Current page size */
  pageSize?: number;

  /** Callback when page size changes */
  onPageSizeChange?: (pageSize: number) => void;
}

export function Pagination({
  metadata,
  currentPage,
  onPageChange,
  onCursorChange,
  showPageSize = false,
  pageSize = 20,
  onPageSizeChange,
}: PaginationProps) {
  if (!metadata) return null;

  const { has_next, has_prev, total, total_pages, strategy, next_cursor, prev_cursor } = metadata;

  // Don't show pagination if only one page
  if (!has_next && !has_prev && currentPage === 1) {
    return null;
  }

  const handlePrevious = () => {
    if (!has_prev) return;

    if (strategy === 'cursor' && prev_cursor && onCursorChange) {
      onCursorChange(prev_cursor);
    } else {
      onPageChange(currentPage - 1);
    }
  };

  const handleNext = () => {
    if (!has_next) return;

    if (strategy === 'cursor' && next_cursor && onCursorChange) {
      onCursorChange(next_cursor);
    } else {
      onPageChange(currentPage + 1);
    }
  };

  return (
    <div className="flex items-center justify-between border-t border-slate-200 bg-white px-4 py-3 sm:px-6">
      {/* Info Text */}
      <div className="flex flex-1 justify-between sm:hidden">
        <button
          onClick={handlePrevious}
          disabled={!has_prev}
          className="relative inline-flex items-center rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Previous
        </button>
        <button
          onClick={handleNext}
          disabled={!has_next}
          className="relative ml-3 inline-flex items-center rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Next
        </button>
      </div>

      <div className="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          {/* Total count (offset pagination only) */}
          {strategy === 'offset' && total !== undefined && (
            <p className="text-sm text-slate-700">
              Showing page <span className="font-medium">{currentPage}</span> of{' '}
              <span className="font-medium">{total_pages}</span>
              {' • '}
              <span className="font-medium">{total}</span> total items
            </p>
          )}

          {/* Cursor pagination indicator */}
          {strategy === 'cursor' && (
            <p className="text-sm text-slate-700">
              Page <span className="font-medium">{currentPage}</span>
              <span className="ml-2 text-xs text-slate-500">(Deep pagination mode)</span>
            </p>
          )}

          {/* Page size selector */}
          {showPageSize && onPageSizeChange && (
            <div className="flex items-center gap-2">
              <label htmlFor="page-size" className="text-sm text-slate-700">
                Items per page:
              </label>
              <select
                id="page-size"
                value={pageSize}
                onChange={(e) => onPageSizeChange(Number(e.target.value))}
                className="rounded-md border-slate-300 text-sm focus:border-blue-500 focus:ring-blue-500"
              >
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
              </select>
            </div>
          )}
        </div>

        {/* Navigation buttons */}
        <div>
          <nav className="isolate inline-flex -space-x-px rounded-md shadow-sm" aria-label="Pagination">
            <button
              onClick={handlePrevious}
              disabled={!has_prev}
              className="relative inline-flex items-center rounded-l-md px-2 py-2 text-slate-400 ring-1 ring-inset ring-slate-300 hover:bg-slate-50 focus:z-20 focus:outline-offset-0 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span className="sr-only">Previous</span>
              <ChevronLeft className="h-5 w-5" aria-hidden="true" />
            </button>

            {/* Page numbers (offset pagination only, pages 1-5) */}
            {strategy === 'offset' && total_pages !== undefined && total_pages <= 10 && (
              <>
                {Array.from({ length: Math.min(total_pages, 10) }, (_, i) => i + 1).map((page) => (
                  <button
                    key={page}
                    onClick={() => onPageChange(page)}
                    className={`relative inline-flex items-center px-4 py-2 text-sm font-semibold ring-1 ring-inset ring-slate-300 hover:bg-slate-50 focus:z-20 focus:outline-offset-0 ${
                      page === currentPage
                        ? 'z-10 bg-blue-600 text-white hover:bg-blue-700'
                        : 'text-slate-900'
                    }`}
                  >
                    {page}
                  </button>
                ))}
              </>
            )}

            <button
              onClick={handleNext}
              disabled={!has_next}
              className="relative inline-flex items-center rounded-r-md px-2 py-2 text-slate-400 ring-1 ring-inset ring-slate-300 hover:bg-slate-50 focus:z-20 focus:outline-offset-0 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span className="sr-only">Next</span>
              <ChevronRight className="h-5 w-5" aria-hidden="true" />
            </button>
          </nav>
        </div>
      </div>
    </div>
  );
}
