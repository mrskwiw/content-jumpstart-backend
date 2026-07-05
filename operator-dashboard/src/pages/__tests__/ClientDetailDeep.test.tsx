/**
 * Comprehensive tests for ClientDetail page (1,277 LOC)
 */
import { describe, it, expect, jest, beforeEach } from '@jest/globals';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ClientDetail from '../ClientDetail';

jest.mock('@/api/clients');
jest.mock('@/api/projects');
jest.mock('@/api/posts');

const mockClient = {
  id: 'client-1',
  name: 'Test Client',
  business_description: 'Test business',
  ideal_customer: 'B2B companies',
  created_at: '2024-01-01T00:00:00Z',
};

const mockProjects = [
  { id: 'proj-1', name: 'Project 1', client_id: 'client-1', status: 'active', created_at: '2024-01-01T00:00:00Z' },
  { id: 'proj-2', name: 'Project 2', client_id: 'client-1', status: 'completed', created_at: '2024-01-02T00:00:00Z' },
];

describe('ClientDetail', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { clientsApi } = require('@/api/clients');
    const { projectsApi } = require('@/api/projects');
    const { postsApi } = require('@/api/posts');

    clientsApi.get = jest.fn().mockResolvedValue(mockClient);
    projectsApi.list = jest.fn().mockResolvedValue(mockProjects);
    postsApi.list = jest.fn().mockResolvedValue({ items: [], total: 0, page: 1, pageSize: 10, totalPages: 0 });
  });

  it('should render loading state', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/clients/client-1']}>
          <ClientDetail />
        </MemoryRouter>
      </QueryClientProvider>
    );
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it('should render client name', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/clients/client-1']}>
          <ClientDetail />
        </MemoryRouter>
      </QueryClientProvider>
    );
    await waitFor(() => expect(screen.getByText('Test Client')).toBeInTheDocument());
  });

  it('should show project count', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/clients/client-1']}>
          <ClientDetail />
        </MemoryRouter>
      </QueryClientProvider>
    );
    await waitFor(() => expect(screen.getByText(/2/)).toBeInTheDocument());
  });
});
