/**
 * Integration Test: Client Management Flow
 * Tests creating, viewing, and editing clients
 */
import { describe, it, expect, jest, beforeEach } from '@jest/globals';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Clients from '@/pages/Clients';
import ClientDetail from '@/pages/ClientDetail';
import { clientsApi } from '@/api/clients';
import { projectsApi } from '@/api/projects';
import { ROUTES } from '@/config/routes';

jest.mock('@/api/clients');
jest.mock('@/api/projects');

const mockClientsApi = clientsApi as jest.Mocked<typeof clientsApi>;
const mockProjectsApi = projectsApi as jest.Mocked<typeof projectsApi>;

describe('Client Management Flow Integration', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    jest.clearAllMocks();
  });

  it('should display client list', async () => {
    const mockClients = [
      {
        id: 'client-1',
        name: 'Acme Corp',
        businessDescription: 'Software company',
      },
      {
        id: 'client-2',
        name: 'TechStart Inc',
        businessDescription: 'Startup',
      },
    ];

    mockClientsApi.list.mockResolvedValue(mockClients);

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <Clients />
        </MemoryRouter>
      </QueryClientProvider>
    );

    // Should show clients
    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
      expect(screen.getByText('TechStart Inc')).toBeInTheDocument();
    });
  });

  it('should navigate to the new-client page from the Clients list', async () => {
    const user = userEvent.setup();

    mockClientsApi.list.mockResolvedValue([]);

    // Client creation is no longer an inline dialog on the Clients page — the
    // "Add Client" button navigates to a dedicated new-client route.
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[ROUTES.CLIENTS]}>
          <Routes>
            <Route path={ROUTES.CLIENTS} element={<Clients />} />
            <Route path={ROUTES.CLIENT_NEW} element={<div>New Client Page</div>} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );

    const addButton = await screen.findByRole('button', { name: /add client/i });
    await user.click(addButton);

    await waitFor(() => {
      expect(screen.getByText('New Client Page')).toBeInTheDocument();
    });
  });

  it('should view client details', async () => {
    const user = userEvent.setup();
    const mockClient = {
      id: 'client-1',
      name: 'Acme Corp',
      businessDescription: 'Software company',
      idealCustomer: 'B2B SaaS',
      industry: 'Software',
    };

    const mockProjects = {
      items: [
        {
          id: 'proj-1',
          name: 'Q1 Campaign',
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

    mockClientsApi.get.mockResolvedValue(mockClient);
    mockProjectsApi.list.mockResolvedValue(mockProjects);

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/clients/client-1']}>
          <Routes>
            <Route path="/clients/:clientId" element={<ClientDetail />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );

    // Client name appears in both the header and the contact card, so assert at least
    // one match. The overview tab shows business details (industry), not the raw
    // businessDescription field.
    await waitFor(() => {
      expect(screen.getAllByText('Acme Corp').length).toBeGreaterThan(0);
    });

    // Associated projects live under the Projects tab, not the default Overview tab.
    await user.click(screen.getByRole('button', { name: /projects/i }));
    await waitFor(() => {
      expect(screen.getByText('Q1 Campaign')).toBeInTheDocument();
    });
  });

  it('should handle empty client list', async () => {
    mockClientsApi.list.mockResolvedValue([]);

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <Clients />
        </MemoryRouter>
      </QueryClientProvider>
    );

    // Should show empty state ("No clients found" + "Add your first client to get
    // started" both match, so assert at least one).
    await waitFor(() => {
      expect(screen.getAllByText(/no clients|empty|get started/i).length).toBeGreaterThan(0);
    });
  });

  it('should handle API errors gracefully', async () => {
    mockClientsApi.list.mockRejectedValue(new Error('Network error'));

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <Clients />
        </MemoryRouter>
      </QueryClientProvider>
    );

    // Should show error message or empty state (queryByText throws on multiple
    // matches, so use queryAllByText).
    await waitFor(() => {
      const errorMessages = screen.queryAllByText(/error|failed|try again/i);
      const emptyState = screen.queryAllByText(/no clients|empty|get started/i);
      expect(errorMessages.length > 0 || emptyState.length > 0).toBeTruthy();
    }, { timeout: 3000 });
  });
});
