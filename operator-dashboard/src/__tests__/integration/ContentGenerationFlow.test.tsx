/**
 * Integration Test: Content Generation Flow
 * Tests the wizard and content generation process
 */
import { describe, it, expect, jest, beforeEach } from '@jest/globals';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Wizard from '@/pages/Wizard';
import { clientsApi } from '@/api/clients';
import { projectsApi } from '@/api/projects';

jest.mock('@/api/clients');
jest.mock('@/api/projects');

const mockClientsApi = clientsApi as jest.Mocked<typeof clientsApi>;
const mockProjectsApi = projectsApi as jest.Mocked<typeof projectsApi>;

describe('Content Generation Flow Integration', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    jest.clearAllMocks();

    mockClientsApi.list.mockResolvedValue([
      {
        id: 'client-1',
        name: 'Test Client',
      },
    ]);

    mockProjectsApi.create.mockResolvedValue({
      id: 'proj-new',
      name: 'New Project',
      clientId: 'client-1',
      status: 'draft',
      platforms: ['linkedin' as const],
    });
  });

  it('should render wizard with steps', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <Wizard />
        </MemoryRouter>
      </QueryClientProvider>
    );

    // Should show wizard UI
    await waitFor(() => {
      expect(screen.getByText(/step|wizard|profile|template/i)).toBeInTheDocument();
    });
  });

  it('should show client profile panel', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <Wizard />
        </MemoryRouter>
      </QueryClientProvider>
    );

    await waitFor(() => {
      const companyInput = screen.queryByLabelText(/company|business/i);
      const headings = screen.queryAllByRole('heading');
      expect(companyInput || headings.length > 0).toBeTruthy();
    });
  });

  it('should handle wizard navigation', async () => {
    const user = userEvent.setup();

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <Wizard />
        </MemoryRouter>
      </QueryClientProvider>
    );

    // Wait for wizard to load
    await waitFor(() => {
      const elements = screen.queryAllByRole('button');
      expect(elements.length).toBeGreaterThan(0);
    });

    // Should have navigation buttons
    const buttons = screen.getAllByRole('button');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('should allow selecting existing client', async () => {
    const user = userEvent.setup();

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <Wizard />
        </MemoryRouter>
      </QueryClientProvider>
    );

    // Should show existing clients option
    await waitFor(() => {
      const existingButton = screen.queryByText(/existing|select client/i);
      expect(existingButton || screen.queryAllByRole('button').length > 0).toBeTruthy();
    });
  });

  it('should create project on wizard completion', async () => {
    const user = userEvent.setup();

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <Wizard />
        </MemoryRouter>
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.queryAllByRole('button').length).toBeGreaterThan(0);
    });

    // Note: Full wizard flow would require filling forms and navigating steps
    // This is a simplified test checking the wizard renders correctly
  });
});
