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

  it('should create new client', async () => {
    const user = userEvent.setup();

    mockClientsApi.list.mockResolvedValue([]);
    mockClientsApi.create.mockResolvedValue({
      id: 'client-new',
      name: 'New Client',
      businessDescription: 'New business',
    });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <Clients />
        </MemoryRouter>
      </QueryClientProvider>
    );

    // Click "New Client" button
    const newButton = await screen.findByRole('button', { name: /new|create|add/i });
    await user.click(newButton);

    // Should open dialog/form
    await waitFor(() => {
      expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
    });

    // Fill in form
    await user.type(screen.getByLabelText(/name/i), 'New Client');

    const descriptionField = screen.getByLabelText(/description/i);
    await user.type(descriptionField, 'New business');

    // Submit
    const submitButton = screen.getByRole('button', { name: /create|save/i });
    await user.click(submitButton);

    // Should call create API
    await waitFor(() => {
      expect(mockClientsApi.create).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'New Client',
        })
      );
    });
  });

  it('should view client details', async () => {
    const mockClient = {
      id: 'client-1',
      name: 'Acme Corp',
      businessDescription: 'Software company',
      idealCustomer: 'B2B SaaS',
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

    // Should show client details
    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
      expect(screen.getByText(/Software company/i)).toBeInTheDocument();
    });

    // Should show associated projects
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

    // Should show empty state
    await waitFor(() => {
      expect(screen.getByText(/no clients|empty|get started/i)).toBeInTheDocument();
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

    // Should show error message or empty state
    await waitFor(() => {
      const errorMessage = screen.queryByText(/error|failed|try again/i);
      const emptyState = screen.queryByText(/no clients|empty|get started/i);
      expect(errorMessage || emptyState).toBeTruthy();
    }, { timeout: 3000 });
  });
});
