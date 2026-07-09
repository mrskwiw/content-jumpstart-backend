/**
 * Tests for Clients page component
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '@/__tests__/setup/test-utils';
import Clients from '../Clients';
import * as clientsApi from '@/api/clients';
import * as projectsApi from '@/api/projects';
import * as deliverablesApi from '@/api/deliverables';

// Mock API modules
jest.mock('@/api/clients');
jest.mock('@/api/projects');
jest.mock('@/api/deliverables');

// Mock navigate
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => {
  const actual = jest.requireActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('Clients Page', () => {
  beforeEach(() => {
    jest.clearAllMocks();

    // Setup default mocks (each API module exposes a namespaced client object)
    jest.mocked(clientsApi.clientsApi.list).mockResolvedValue([
      {
        id: 'client-1',
        name: 'Acme Corp',
        email: 'contact@acme.com',
        createdAt: new Date().toISOString(),
      },
      {
        id: 'client-2',
        name: 'StartupXYZ',
        email: 'hello@startupxyz.com',
        createdAt: new Date().toISOString(),
      },
    ]);

    jest.mocked(projectsApi.projectsApi.list).mockResolvedValue({
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
      totalPages: 1,
    });

    jest.mocked(deliverablesApi.deliverablesApi.list).mockResolvedValue([]);
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

  it('should display add client button', async () => {
    renderWithProviders(<Clients />);

    await waitFor(() => {
      // Copy is "Add Client" (was previously "New Client").
      const newButton = screen.getByRole('button', { name: /add client/i });
      expect(newButton).toBeInTheDocument();
    });
  });

  it('should handle loading state', () => {
    jest.mocked(clientsApi.clientsApi.list).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    renderWithProviders(<Clients />);

    // Header renders immediately (page shell is not gated on the query).
    // Use an exact match to avoid colliding with "Total Clients"/"Active Clients".
    expect(screen.getByText('Clients')).toBeInTheDocument();
  });
});
