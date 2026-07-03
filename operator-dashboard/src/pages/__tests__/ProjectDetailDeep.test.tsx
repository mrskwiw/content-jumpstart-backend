/**
 * Deeper tests for ProjectDetail page
 */
import { describe, it, expect, jest } from '@jest/globals';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ProjectDetail from '../ProjectDetail';
import * as projectsApi from '@/api/projects';
import * as clientsApi from '@/api/clients';
import * as postsApi from '@/api/posts';
import * as deliverablesApi from '@/api/deliverables';

jest.mock('@/api/projects');
jest.mock('@/api/clients');
jest.mock('@/api/posts');
jest.mock('@/api/deliverables');

describe('ProjectDetail - Deep Tests', () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  const mockProject = {
    id: 'proj-1',
    name: 'Test Project',
    client_id: 'client-1',
    description: 'Test Description',
    status: 'active' as const,
    created_at: '2024-01-01T00:00:00Z',
  };

  const mockClients = [
    {
      id: 'client-1',
      name: 'Test Client',
      created_at: '2024-01-01T00:00:00Z',
    },
  ];

  beforeEach(() => {
    jest.clearAllMocks();
    queryClient.clear();
    (projectsApi.projectsApi.get as jest.Mock).mockResolvedValue(mockProject);
    (clientsApi.clientsApi.list as jest.Mock).mockResolvedValue(mockClients);
    (postsApi.postsApi.list as jest.Mock).mockResolvedValue({ items: [], total: 0, page: 1, pageSize: 10, totalPages: 0 });
    (deliverablesApi.deliverablesApi.list as jest.Mock).mockResolvedValue([]);
  });

  it('should show loading state initially', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/projects/proj-1']}>
          <ProjectDetail />
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(screen.getByText(/loading project/i)).toBeInTheDocument();
  });

  it('should render project name when loaded', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/projects/proj-1']}>
          <ProjectDetail />
        </MemoryRouter>
      </QueryClientProvider>
    );

    await screen.findByText('Test Project');
    expect(screen.getByText('Test Project')).toBeInTheDocument();
  });

  it('should show project description', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/projects/proj-1']}>
          <ProjectDetail />
        </MemoryRouter>
      </QueryClientProvider>
    );

    await screen.findByText('Test Description');
    expect(screen.getByText('Test Description')).toBeInTheDocument();
  });

  it('should fetch project data with correct ID', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/projects/proj-1']}>
          <ProjectDetail />
        </MemoryRouter>
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(projectsApi.projectsApi.get).toHaveBeenCalledWith('proj-1');
    });
  });

  it('should fetch clients list', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/projects/proj-1']}>
          <ProjectDetail />
        </MemoryRouter>
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(clientsApi.clientsApi.list).toHaveBeenCalled();
    });
  });

  it('should fetch posts list', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/projects/proj-1']}>
          <ProjectDetail />
        </MemoryRouter>
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(postsApi.postsApi.list).toHaveBeenCalled();
    });
  });

  it('should fetch deliverables list', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/projects/proj-1']}>
          <ProjectDetail />
        </MemoryRouter>
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(deliverablesApi.deliverablesApi.list).toHaveBeenCalled();
    });
  });
});
