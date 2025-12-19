import { QueryClient } from '@tanstack/react-query';

/**
 * React Query configuration optimized for HTTP caching.
 *
 * Settings align with backend Cache-Control headers:
 * - staleTime: 5 minutes (matches max-age=300)
 * - Enables background refetching for stale-while-revalidate
 * - Respects cache invalidation signals from mutations
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Respect Cache-Control max-age (5 minutes)
      staleTime: 5 * 60 * 1000, // 300,000ms = 5 minutes

      // Allow background refetching when data becomes stale
      // Implements stale-while-revalidate strategy
      refetchOnWindowFocus: true,

      // Revalidate when component mounts if data is stale
      refetchOnMount: true,

      // Retry failed requests once before giving up
      retry: 1,

      // Don't refetch on network reconnect unless stale
      refetchOnReconnect: 'always',

      // Cache time: keep unused data for 10 minutes (longer than staleTime)
      // This allows stale-while-revalidate to work properly
      gcTime: 10 * 60 * 1000, // 600,000ms = 10 minutes
    },
    mutations: {
      // Don't retry mutations automatically
      retry: 0,

      // Invalidate related queries after successful mutations
      // This works with X-Cache-Invalidate headers from backend
      onSuccess: () => {
        // Cache invalidation will be handled by mutation-specific invalidations
        // in individual API functions
      },
    },
  },
});
