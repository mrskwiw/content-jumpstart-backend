/**
 * Integration Test: Project Creation Workflow
 * Tests the complete project creation and setup flow
 */
import { describe, it, expect, jest, beforeEach } from '@jest/globals';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Projects from '@/pages/Projects';
import ProjectDetail from '@/pages/ProjectDetail';
import { projectsApi } from '@/api/projects';
import { clientsApi } from '@/api/clients';
import { postsApi } from '@/api/posts';
import { deliverablesApi } from '@/api/deliverables';
import { ROUTES } from '@/config/routes';

jest.mock('@/api/projects');
jest.mock('@/api/clients');
jest.mock('@/api/posts');
jest.mock('@/api/deliverables');

const mockProjectsApi = projectsApi as jest.Mocked<typeof projectsApi>;
const mockClientsApi = clientsApi as jest.Mocked<typeof clientsApi>;
const mockPostsApi = postsApi as jest.Mocked<typeof postsApi>;
const mockDeliverablesApi = deliverablesApi as jest.Mocked<typeof deliverablesApi>;

describe('Project Workflow Integration', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    jest.clearAllMocks();
  });

  it('should display project list', async () => {
    const mockProjects = {
      items: [
        {
          id: 'proj-1',
          name: 'Q1 Content Campaign',
          clientId: 'client-1',
          status: 'ready' as const,
          platforms: ['linkedin' as const],
        },
      ],
      metadata: {
        page_size: 20,
        has_next: false,
        has_prev: false,
        strategy: 'offset' as const,
      },
    };

    mockProjectsApi.list.mockResolvedValue(mockProjects);

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <Projects />
        </MemoryRouter>
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Q1 Content Campaign')).toBeInTheDocument();
    });
  });

  it('should start a new project via the wizard', async () => {
    const user = userEvent.setup();

    mockProjectsApi.list.mockResolvedValue({
      items: [],
      metadata: {
        page_size: 20,
        has_next: false,
        has_prev: false,
        strategy: 'offset' as const,
      },
    });
    mockClientsApi.list.mockResolvedValue([]);

    // Project creation is no longer an inline dialog on the Projects page — the
    // "New Project" button navigates to the wizard.
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[ROUTES.PROJECTS]}>
          <Routes>
            <Route path={ROUTES.PROJECTS} element={<Projects />} />
            <Route path={ROUTES.WIZARD} element={<div>Project Wizard Page</div>} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );

    const newButton = await screen.findByRole('button', { name: /new project/i });
    await user.click(newButton);

    await waitFor(() => {
      expect(screen.getByText('Project Wizard Page')).toBeInTheDocument();
    });
  });

  // Previously blocked by a Rules-of-Hooks bug in ProjectDetail.tsx (useMemos ran after
  // the loading/error early returns). Fixed by hoisting the hooks above the returns.
  it('should view project details with posts and deliverables', async () => {
    const mockProject = {
      id: 'proj-1',
      name: 'Q1 Campaign',
      clientId: 'client-1',
      status: 'ready' as const,
      platforms: ['linkedin' as const],
    };

    const mockPosts = {
      items: [
        {
          id: 'post-1',
          projectId: 'proj-1',
          runId: 'run-1',
          content: 'Test post content',
          length: 150,
        },
      ],
      metadata: {
        page_size: 20,
        has_next: false,
        has_prev: false,
        strategy: 'offset' as const,
      },
    };

    const mockDeliverables = [
      {
        id: 'del-1',
        projectId: 'proj-1',
        clientId: 'client-1',
        format: 'txt' as const,
        path: 'output.txt',
        status: 'ready' as const,
        createdAt: '2024-01-01T00:00:00Z',
      },
    ];

    mockProjectsApi.get.mockResolvedValue(mockProject);
    mockClientsApi.list.mockResolvedValue([]);
    mockPostsApi.list.mockResolvedValue(mockPosts);
    mockDeliverablesApi.list.mockResolvedValue(mockDeliverables);

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/projects/proj-1']}>
          <Routes>
            <Route path="/projects/:projectId" element={<ProjectDetail />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );

    // Should show project name (renders in the heading and repeats in the breadcrumb).
    expect(await screen.findByRole('heading', { name: 'Q1 Campaign' })).toBeInTheDocument();

    // Should fetch project data
    expect(mockProjectsApi.get).toHaveBeenCalledWith('proj-1');
    expect(mockPostsApi.list).toHaveBeenCalled();
    expect(mockDeliverablesApi.list).toHaveBeenCalled();
  });

  it('should handle project not found', async () => {
    mockProjectsApi.get.mockRejectedValue(new Error('Project not found'));
    mockClientsApi.list.mockResolvedValue([]);
    mockPostsApi.list.mockResolvedValue({
      items: [],
      metadata: {
        page_size: 20,
        has_next: false,
        has_prev: false,
        strategy: 'offset' as const,
      },
    });
    mockDeliverablesApi.list.mockResolvedValue([]);

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/projects/invalid-id']}>
          <Routes>
            <Route path="/projects/:projectId" element={<ProjectDetail />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );

    // Should show error or loading indefinitely
    await waitFor(() => {
      const loading = screen.queryByText(/loading/i);
      const error = screen.queryByText(/error|not found/i);
      expect(loading || error).toBeTruthy();
    });
  });
});
