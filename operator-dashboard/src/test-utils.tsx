import { ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, MemoryRouterProps } from 'react-router-dom';

export function renderWithProviders(route: MemoryRouterProps['initialEntries'] = ['/']) {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return {
    client,
    wrapper: ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={route}>{children}</MemoryRouter>
      </QueryClientProvider>
    ),
  };
}
