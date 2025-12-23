/**
 * Chunk Loading Retry Utility
 *
 * Automatically retries failed dynamic imports with exponential backoff.
 * This prevents "Failed to fetch dynamically imported module" errors in production.
 *
 * Common causes of chunk loading failures:
 * - New deployment while user has old HTML cached
 * - Network issues during chunk fetch
 * - CDN cache invalidation delays
 * - User navigating during deployment
 */

interface RetryOptions {
  maxRetries?: number;
  initialDelay?: number;
  maxDelay?: number;
  shouldReload?: boolean;
}

const DEFAULT_OPTIONS: Required<RetryOptions> = {
  maxRetries: 3,
  initialDelay: 1000, // 1 second
  maxDelay: 5000, // 5 seconds
  shouldReload: true, // Reload page on final failure (gets fresh HTML)
};

/**
 * Check if an error is a chunk loading error
 */
export function isChunkLoadError(error: any): boolean {
  if (!error) return false;

  const errorMessage = error.message || error.toString();

  return (
    errorMessage.includes('Failed to fetch dynamically imported module') ||
    errorMessage.includes('Importing a module script failed') ||
    errorMessage.includes('error loading dynamically imported module') ||
    errorMessage.includes('ChunkLoadError') ||
    // Check for network errors that might affect chunk loading
    errorMessage.includes('Failed to fetch') ||
    errorMessage.includes('NetworkError')
  );
}

/**
 * Sleep for a specified duration
 */
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Calculate delay with exponential backoff
 */
function getRetryDelay(attempt: number, options: Required<RetryOptions>): number {
  const delay = options.initialDelay * Math.pow(2, attempt);
  return Math.min(delay, options.maxDelay);
}

/**
 * Retry a dynamic import with exponential backoff
 *
 * Usage:
 * ```typescript
 * const Component = lazy(() =>
 *   retryChunkImport(() => import('./MyComponent'))
 * );
 * ```
 */
export async function retryChunkImport<T>(
  importFn: () => Promise<T>,
  options: RetryOptions = {}
): Promise<T> {
  const opts = { ...DEFAULT_OPTIONS, ...options };
  let lastError: any;

  for (let attempt = 0; attempt < opts.maxRetries; attempt++) {
    try {
      // Try the import
      return await importFn();
    } catch (error) {
      lastError = error;

      // Only retry if it's a chunk load error
      if (!isChunkLoadError(error)) {
        throw error;
      }

      // Log the retry attempt (only in development)
      if (process.env.NODE_ENV === 'development') {
        console.warn(
          `Chunk load failed (attempt ${attempt + 1}/${opts.maxRetries}):`,
          error
        );
      }

      // Don't sleep after the last attempt
      if (attempt < opts.maxRetries - 1) {
        const delay = getRetryDelay(attempt, opts);
        await sleep(delay);
      }
    }
  }

  // All retries failed
  console.error('Chunk loading failed after all retries:', lastError);

  // Reload the page to get fresh HTML and JS files
  if (opts.shouldReload) {
    console.log('Reloading page to fetch latest version...');
    window.location.reload();
    // Return a never-resolving promise to prevent further execution
    return new Promise(() => {});
  }

  // If reload is disabled, throw the error
  throw lastError;
}

/**
 * Create a lazy component with automatic chunk retry
 *
 * Usage:
 * ```typescript
 * const MyComponent = lazyWithRetry(() => import('./MyComponent'));
 * ```
 */
export function lazyWithRetry<T extends React.ComponentType<any>>(
  importFn: () => Promise<{ default: T }>,
  options?: RetryOptions
): React.LazyExoticComponent<T> {
  return React.lazy(() => retryChunkImport(importFn, options));
}

/**
 * Global error handler for chunk loading errors
 * Add this to your main.tsx to catch unhandled chunk errors
 */
export function setupChunkErrorHandler() {
  // Listen for unhandled errors
  window.addEventListener('error', (event) => {
    if (isChunkLoadError(event.error)) {
      console.error('Unhandled chunk loading error detected, reloading page...');
      event.preventDefault();
      window.location.reload();
    }
  });

  // Listen for unhandled promise rejections
  window.addEventListener('unhandledrejection', (event) => {
    if (isChunkLoadError(event.reason)) {
      console.error('Unhandled chunk loading rejection detected, reloading page...');
      event.preventDefault();
      window.location.reload();
    }
  });
}

// Export React for lazyWithRetry
import React from 'react';
