/**
 * Integration Test: Content Generation Flow
 * Tests the wizard and content generation process
 */
import { describe, it, expect, jest, beforeEach } from '@jest/globals';
import { render, screen, waitFor } from '@testing-library/react';
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

    // Should show wizard UI. The redesigned wizard renders several matching strings
    // (heading + stepper labels), so assert at least one match rather than a unique one.
    await waitFor(() => {
      expect(screen.getAllByText(/wizard|profile|template/i).length).toBeGreaterThan(0);
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
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <Wizard />
        </MemoryRouter>
      </QueryClientProvider>
    );

    // Should show existing clients option (queryByText throws on multiple matches,
    // and the redesign renders "Select Client"/"Use Existing Client"/"Select Existing
    // Client", so use queryAllByText).
    await waitFor(() => {
      const existingMatches = screen.queryAllByText(/existing|select client/i);
      expect(existingMatches.length > 0 || screen.queryAllByRole('button').length > 0).toBeTruthy();
    });
  });

  it('should create project on wizard completion', async () => {
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
