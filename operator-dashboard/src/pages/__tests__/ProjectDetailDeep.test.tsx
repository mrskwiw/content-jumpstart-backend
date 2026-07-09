/**
 * Deeper tests for ProjectDetail page
 */
import { describe, it, expect, jest } from '@jest/globals';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ProjectDetail from '../ProjectDetail';
import * as projectsApi from '@/api/projects';
import * as clientsApi from '@/api/clients';
import * as postsApi from '@/api/posts';
import * as deliverablesApi from '@/api/deliverables';
import * as runsApi from '@/api/runs';

jest.mock('@/api/projects');
jest.mock('@/api/clients');
jest.mock('@/api/posts');
jest.mock('@/api/deliverables');
jest.mock('@/api/runs');
jest.mock('@/api/costs');

// Render ProjectDetail behind a matching route so useParams() resolves the id.
function renderProjectDetail(queryClient: QueryClient) {
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/projects/proj-1']}>
        <Routes>
          <Route path="/projects/:projectId" element={<ProjectDetail />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe('ProjectDetail - Deep Tests', () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  const mockProject = {
    id: 'proj-1',
    name: 'Test Project',
    clientId: 'client-1',
    status: 'ready' as const,
    createdAt: '2024-01-01T00:00:00Z',
  };

  const mockClients = [
    {
      id: 'client-1',
      name: 'Test Client',
      createdAt: '2024-01-01T00:00:00Z',
    },
  ];

  beforeEach(() => {
    jest.clearAllMocks();
    queryClient.clear();
    (projectsApi.projectsApi.get as jest.Mock).mockResolvedValue(mockProject);
    (clientsApi.clientsApi.list as jest.Mock).mockResolvedValue(mockClients);
    (postsApi.postsApi.list as jest.Mock).mockResolvedValue({ items: [], total: 0, page: 1, pageSize: 10, totalPages: 0 });
    (deliverablesApi.deliverablesApi.list as jest.Mock).mockResolvedValue([]);
    (runsApi.runsApi.listByProject as jest.Mock).mockResolvedValue([]);
  });

  it('should show loading state initially', () => {
    renderProjectDetail(queryClient);

    expect(screen.getByText(/loading project/i)).toBeInTheDocument();
  });

  it('should render project name when loaded', async () => {
    renderProjectDetail(queryClient);

    // Name renders in the page heading (and repeats elsewhere, e.g. breadcrumb),
    // so scope to the heading to disambiguate.
    expect(await screen.findByRole('heading', { name: 'Test Project' })).toBeInTheDocument();
  });

  it('should show client name resolved from the clients list', async () => {
    // NOTE: the Project model has no `description` field and ProjectDetail does
    // not render one (the Overview "Brief Summary" is static placeholder copy).
    // This test now asserts the real behavior it can verify: the client name is
    // looked up from the clients list via project.clientId.
    renderProjectDetail(queryClient);

    await screen.findByText('Test Client');
    expect(screen.getByText('Test Client')).toBeInTheDocument();
  });

  it('should fetch project data with correct ID', async () => {
    renderProjectDetail(queryClient);

    await waitFor(() => {
      expect(projectsApi.projectsApi.get).toHaveBeenCalledWith('proj-1');
    });
  });

  it('should fetch clients list', async () => {
    renderProjectDetail(queryClient);

    await waitFor(() => {
      expect(clientsApi.clientsApi.list).toHaveBeenCalled();
    });
  });

  it('should fetch posts list', async () => {
    renderProjectDetail(queryClient);

    await waitFor(() => {
      expect(postsApi.postsApi.list).toHaveBeenCalled();
    });
  });

  it('should fetch deliverables list', async () => {
    renderProjectDetail(queryClient);

    await waitFor(() => {
      expect(deliverablesApi.deliverablesApi.list).toHaveBeenCalled();
    });
  });
});
