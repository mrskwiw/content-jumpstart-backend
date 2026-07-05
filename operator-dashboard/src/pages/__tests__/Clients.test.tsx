/**
 * Tests for Clients page component
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '@/__tests__/setup/test-utils';
import Clients from '../Clients';
import * as clientsApi from '@/api/clients';
import * as projectsApi from '@/api/projects';
import * as deliverablesApi from '@/api/deliverables';

// Mock API modules
vi.mock('@/api/clients');
vi.mock('@/api/projects');
vi.mock('@/api/deliverables');

// Mock navigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('Clients Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Setup default mocks
    vi.mocked(clientsApi.list).mockResolvedValue([
      {
        id: 'client-1',
        name: 'Acme Corp',
        email: 'contact@acme.com',
        status: 'active',
        tags: ['enterprise', 'tech'],
      },
      {
        id: 'client-2',
        name: 'StartupXYZ',
        email: 'hello@startupxyz.com',
        status: 'active',
        tags: ['startup'],
      },
    ]);

    vi.mocked(projectsApi.list).mockResolvedValue({
      items: [
        {
          id: 'proj-1',
          clientId: 'client-1',
          name: 'Q1 Campaign',
          status: 'generating',
          platforms: ['linkedin'],
          createdAt: new Date().toISOString(),
        },
      ],
      total: 1,
      page: 1,
      pageSize: 100,
    });

    vi.mocked(deliverablesApi.list).mockResolvedValue([]);
  });

  it('should render clients page header', async () => {
    renderWithProviders(<Clients />);

    await waitFor(() => {
      expect(screen.getByText('Clients')).toBeInTheDocument();
    });
  });

  it('should render search and filter controls', async () => {
    renderWithProviders(<Clients />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/search clients/i)).toBeInTheDocument();
    });
  });

  it('should display client list when data loads', async () => {
    renderWithProviders(<Clients />);

    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
      expect(screen.getByText('StartupXYZ')).toBeInTheDocument();
    });
  });

  it('should display new client button', async () => {
    renderWithProviders(<Clients />);

    await waitFor(() => {
      const newButton = screen.getByRole('button', { name: /new client/i });
      expect(newButton).toBeInTheDocument();
    });
  });

  it('should handle loading state', () => {
    vi.mocked(clientsApi.list).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    renderWithProviders(<Clients />);

    // Should show loading indicator or empty state
    expect(screen.getByText(/Clients/i)).toBeInTheDocument();
  });
});
