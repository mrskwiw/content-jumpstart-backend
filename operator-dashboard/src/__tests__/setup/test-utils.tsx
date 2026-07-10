/**
 * Test utilities for React component testing.
 *
 * Provides helper functions and wrappers to reduce boilerplate in tests.
 */
import { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, MemoryRouter } from 'react-router-dom';
import { AuthProvider } from '@/contexts/AuthContext';
import { ThemeProvider } from '@/contexts/ThemeContext';

/**
 * Create a fresh QueryClient for each test.
 * Disables retries and refetching to make tests deterministic.
 */
export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        refetchOnWindowFocus: false,
        refetchOnMount: false,
        refetchOnReconnect: false,
        staleTime: Infinity,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

/**
 * Wrapper component that provides all necessary context providers for tests.
 *
 * Includes:
 * - QueryClientProvider (React Query)
 * - BrowserRouter (React Router)
 */
interface AllTheProvidersProps {
  children: React.ReactNode;
}

export function AllTheProviders({ children }: AllTheProvidersProps) {
  const queryClient = createTestQueryClient();

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <BrowserRouter>
          <AuthProvider>{children}</AuthProvider>
        </BrowserRouter>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

/**
 * Wrapper component with MemoryRouter for route-aware tests.
 *
 * Use this when you need to test routing or have initial route state.
 */
interface AllTheProvidersWithMemoryRouterProps {
  children: React.ReactNode;
  initialEntries?: string[];
  initialIndex?: number;
}

export function AllTheProvidersWithMemoryRouter({
  children,
  initialEntries = ['/'],
  initialIndex = 0,
}: AllTheProvidersWithMemoryRouterProps) {
  const queryClient = createTestQueryClient();

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <MemoryRouter initialEntries={initialEntries} initialIndex={initialIndex}>
          {children}
        </MemoryRouter>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

/**
 * Custom render function that wraps components with providers.
 *
 * This is the recommended way to render components in tests.
 *
 * @example
 * ```typescript
 * import { renderWithProviders } from '@/__tests__/setup/test-utils';
 *
 * test('should render component', () => {
 *   renderWithProviders(<MyComponent />);
 *   expect(screen.getByText('Hello')).toBeInTheDocument();
 * });
 * ```
 */
export function renderWithProviders(
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) {
  return render(ui, { wrapper: AllTheProviders, ...options });
}

/**
 * Custom render function with MemoryRouter for route-aware tests.
 *
 * @example
 * ```typescript
 * import { renderWithRouter } from '@/__tests__/setup/test-utils';
 *
 * test('should navigate to dashboard', () => {
 *   renderWithRouter(<App />, { initialEntries: ['/dashboard'] });
 *   expect(screen.getByText('Dashboard')).toBeInTheDocument();
 * });
 * ```
 */
export function renderWithRouter(
  ui: ReactElement,
  options?: {
    initialEntries?: string[];
    initialIndex?: number;
  } & Omit<RenderOptions, 'wrapper'>
) {
  const { initialEntries, initialIndex, ...renderOptions } = options || {};

  return render(ui, {
    wrapper: ({ children }) => (
      <AllTheProvidersWithMemoryRouter
        initialEntries={initialEntries}
        initialIndex={initialIndex}
      >
        {children}
      </AllTheProvidersWithMemoryRouter>
    ),
    ...renderOptions,
  });
}

/**
 * Wait for async operations to complete in tests.
 *
 * This is a convenience wrapper around waitFor that includes common options.
 *
 * @example
 * ```typescript
 * await waitForLoadingToFinish();
 * expect(screen.getByText('Data loaded')).toBeInTheDocument();
 * ```
 */
export async function waitForLoadingToFinish(timeout = 3000): Promise<void> {
  const { waitFor } = await import('@testing-library/react');
  await waitFor(
    () => {
      // Wait for loading indicators to disappear
      const loadingIndicators = document.querySelectorAll('[aria-busy="true"]');
      expect(loadingIndicators).toHaveLength(0);
    },
    { timeout }
  );
}

/**
 * Helper to wait for an async mutation to complete.
 *
 * @example
 * ```typescript
 * await user.click(submitButton);
 * await waitForMutation();
 * expect(screen.getByText('Success')).toBeInTheDocument();
 * ```
 */
export async function waitForMutation(timeout = 3000): Promise<void> {
  const { waitFor } = await import('@testing-library/react');
  // Wait a tick for the mutation to process
  await waitFor(() => {}, { timeout: 100 });
}

// Re-export everything from React Testing Library
export * from '@testing-library/react';

// Export userEvent as a named export for convenience
export { default as userEvent } from '@testing-library/user-event';
