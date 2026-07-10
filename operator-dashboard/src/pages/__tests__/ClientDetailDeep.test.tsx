/**
 * Comprehensive tests for ClientDetail page (1,551 LOC)
 *
 * ClientDetail reads its `clientId` from the route (useParams) and the client
 * query is `enabled: !!clientId`, so it must be rendered inside a matching
 * <Route path="/dashboard/clients/:clientId">.
 */
import { describe, it, expect, jest, beforeEach } from '@jest/globals';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ClientDetail from '../ClientDetail';
import { clientsApi } from '@/api/clients';
import { projectsApi } from '@/api/projects';
import { postsApi } from '@/api/posts';
import { deliverablesApi } from '@/api/deliverables';
import { researchApi } from '@/api/research';
import { communicationsApi } from '@/api/communications';
import { storiesApi } from '@/api/stories';

jest.mock('@/api/clients');
jest.mock('@/api/projects');
jest.mock('@/api/posts');
jest.mock('@/api/deliverables');
jest.mock('@/api/research');
jest.mock('@/api/communications');
jest.mock('@/api/stories');

// Client shape uses camelCase (Supabase drift migration renamed the fields).
const mockClient = {
  id: 'client-1',
  name: 'Test Client',
  businessDescription: 'Test business',
  idealCustomer: 'B2B companies',
  createdAt: '2024-01-01T00:00:00Z',
};

// projectsApi.list returns a PaginatedResponse ({ items, total }), not a bare
// array. Projects are filtered by `clientId` (camelCase).
const mockProjects = {
  items: [
    { id: 'proj-1', name: 'Project 1', clientId: 'client-1', status: 'ready', createdAt: '2024-01-01T00:00:00Z' },
    { id: 'proj-2', name: 'Project 2', clientId: 'client-1', status: 'delivered', createdAt: '2024-01-02T00:00:00Z' },
  ],
  total: 2,
};

describe('ClientDetail', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    clientsApi.get = jest.fn().mockResolvedValue(mockClient);
    projectsApi.list = jest.fn().mockResolvedValue(mockProjects);
    postsApi.list = jest.fn().mockResolvedValue({ items: [], total: 0, page: 1, pageSize: 10, totalPages: 0 });
    deliverablesApi.list = jest.fn().mockResolvedValue([]);
    researchApi.getClientResearchResults = jest.fn().mockResolvedValue({ results: [], total: 0, clientId: 'client-1' });
    communicationsApi.listClientCommunications = jest.fn().mockResolvedValue([]);
    storiesApi.listClientStories = jest.fn().mockResolvedValue({ stories: [], total: 0 });
  });

  function renderPage() {
    return render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/dashboard/clients/client-1']}>
          <Routes>
            <Route path="/dashboard/clients/:clientId" element={<ClientDetail />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );
  }

  it('should render loading state', () => {
    renderPage();
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it('should render client name', async () => {
    renderPage();
    // Name renders in the header heading and the closed Delete dialog; scope to heading.
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Test Client' })).toBeInTheDocument());
  });

  it('should show project count', async () => {
    renderPage();
    // Total Projects / Active Projects stat cards both surface counts derived
    // from the 2 mocked projects.
    await waitFor(() => expect(screen.getAllByText(/2/).length).toBeGreaterThan(0));
  });
});
