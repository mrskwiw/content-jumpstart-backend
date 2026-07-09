/**
 * Tests for ProjectDetail page component
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '@/__tests__/setup/test-utils';
import ProjectDetail from '../ProjectDetail';
import * as projectsApi from '@/api/projects';
import * as clientsApi from '@/api/clients';
import * as postsApi from '@/api/posts';
import * as deliverablesApi from '@/api/deliverables';
import * as runsApi from '@/api/runs';

// Mock API modules (each module exports a namespaced client object, e.g.
// `projectsApi.projectsApi`, so mocks target the nested method).
jest.mock('@/api/projects');
jest.mock('@/api/clients');
jest.mock('@/api/posts');
jest.mock('@/api/deliverables');
jest.mock('@/api/runs');
jest.mock('@/api/costs');

// Mock useParams to return a project ID (synchronous factory — an async factory
// returns a Promise whose named exports resolve to undefined here).
jest.mock('react-router-dom', () => {
  const actual = jest.requireActual('react-router-dom');
  return {
    ...actual,
    useParams: () => ({ projectId: 'project-123' }),
    useNavigate: () => jest.fn(),
  };
});

describe('ProjectDetail Page', () => {
  beforeEach(() => {
    jest.clearAllMocks();

    // Setup default mocks
    jest.mocked(projectsApi.projectsApi.get).mockResolvedValue({
      id: 'project-123',
      clientId: 'client-1',
      name: 'Q1 Campaign',
      status: 'ready',
      platforms: ['linkedin', 'twitter'],
      createdAt: new Date().toISOString(),
    });

    // The component resolves the client name from the clients list (clientsApi.list),
    // matching on project.clientId.
    jest.mocked(clientsApi.clientsApi.list).mockResolvedValue([
      {
        id: 'client-1',
        name: 'Acme Corp',
        email: 'contact@acme.com',
        createdAt: new Date().toISOString(),
      },
    ]);

    jest.mocked(postsApi.postsApi.list).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      pageSize: 100,
      totalPages: 0,
    });

    jest.mocked(deliverablesApi.deliverablesApi.list).mockResolvedValue([]);
    jest.mocked(runsApi.runsApi.listByProject).mockResolvedValue([]);
  });

  it('should render project detail page', async () => {
    renderWithProviders(<ProjectDetail />);

    // Name renders in the heading (and repeats in the breadcrumb) — scope to heading.
    expect(await screen.findByRole('heading', { name: 'Q1 Campaign' })).toBeInTheDocument();
  });

  it('should display client name', async () => {
    renderWithProviders(<ProjectDetail />);

    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    });
  });

  it('should show project status', async () => {
    renderWithProviders(<ProjectDetail />);

    // "ready" appears in the status badge and status filter/progress — assert presence.
    await waitFor(() => {
      expect(screen.getAllByText(/ready/i).length).toBeGreaterThan(0);
    });
  });

  it('should handle loading state', () => {
    jest.mocked(projectsApi.projectsApi.get).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    renderWithProviders(<ProjectDetail />);

    // Should show loading indicator
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });
});
