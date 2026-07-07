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

// Mock API modules
jest.mock('@/api/projects');
jest.mock('@/api/clients');
jest.mock('@/api/posts');

// Mock useParams to return a project ID
jest.mock('react-router-dom', async () => {
  const actual = await jest.requireActual('react-router-dom');
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
    jest.mocked(projectsApi.get).mockResolvedValue({
      id: 'project-123',
      clientId: 'client-1',
      name: 'Q1 Campaign',
      status: 'ready',
      platforms: ['linkedin', 'twitter'],
      createdAt: new Date().toISOString(),
    });

    jest.mocked(clientsApi.get).mockResolvedValue({
      id: 'client-1',
      name: 'Acme Corp',
      email: 'contact@acme.com',
      status: 'active',
    });

    jest.mocked(postsApi.list).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      pageSize: 100,
    });
  });

  it('should render project detail page', async () => {
    renderWithProviders(<ProjectDetail />);

    await waitFor(() => {
      expect(screen.getByText('Q1 Campaign')).toBeInTheDocument();
    });
  });

  it('should display client name', async () => {
    renderWithProviders(<ProjectDetail />);

    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    });
  });

  it('should show project status', async () => {
    renderWithProviders(<ProjectDetail />);

    await waitFor(() => {
      expect(screen.getByText(/ready/i)).toBeInTheDocument();
    });
  });

  it('should handle loading state', () => {
    jest.mocked(projectsApi.get).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    renderWithProviders(<ProjectDetail />);

    // Should show loading indicator
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });
});
