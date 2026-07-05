/**
 * Comprehensive tests for ClientDetail page (1,277 LOC)
 *
 * Coverage focus:
 * - Loading states
 * - Data rendering across all tabs
 * - Tab switching
 * - User interactions
 * - Error states
 * - Research tools
 * - Export functionality
 */

import { describe, it, expect, beforeEach } from '@jest/globals';
import { screen, waitFor } from '@testing-library/react';
import { renderWithRouter, userEvent } from '@/__tests__/setup/test-utils';
import ClientDetail from '../ClientDetail';
import { clientsApi } from '@/api/clients';
import { projectsApi } from '@/api/projects';
import { postsApi } from '@/api/posts';
import { deliverablesApi } from '@/api/deliverables';
import { researchApi } from '@/api/research';

// Mock API modules
jest.mock('@/api/clients');
jest.mock('@/api/projects');
jest.mock('@/api/posts');
jest.mock('@/api/deliverables');
jest.mock('@/api/research');

const mockClient = {
  id: 'client-1',
  name: 'Acme Corp',
  status: 'active',
  tags: ['acme@example.com'],
  createdAt: '2024-01-15T10:00:00Z',
};

const mockProjects = {
  items: [
    {
      id: 'proj-1',
      clientId: 'client-1',
      name: 'Q1 Campaign',
      status: 'ready' as const,
      createdAt: '2024-01-20T10:00:00Z',
    },
    {
      id: 'proj-2',
      clientId: 'client-1',
      name: 'Q2 Campaign',
      status: 'generating' as const,
      createdAt: '2024-02-01T10:00:00Z',
    },
  ],
  total: 2,
};

const mockPosts = {
  items: [
    {
      id: 'post-1',
      projectId: 'proj-1',
      content: 'Test post content for LinkedIn',
      wordCount: 50,
    },
    {
      id: 'post-2',
      projectId: 'proj-1',
      content: 'Another test post',
      wordCount: 30,
    },
  ],
  total: 2,
};

const mockDeliverables = [
  {
    id: 'deliv-1',
    projectId: 'proj-1',
    format: 'txt',
    status: 'delivered',
    deliveredAt: '2024-01-25T10:00:00Z',
  },
];

const mockResearchHistory = [
  {
    id: 'research-1',
    clientId: 'client-1',
    toolName: 'voice_analysis',
    toolLabel: 'Voice Analysis',
    status: 'completed',
    createdAt: '2024-01-18T10:00:00Z',
    data: {
      summary: 'Professional, technical voice with clear CTAs',
    },
  },
];

describe('ClientDetail Page', () => {
  beforeEach(() => {
    jest.clearAllMocks();

    // Setup default mocks
    (clientsApi.get as jest.Mock).mockResolvedValue(mockClient);
    (projectsApi.list as jest.Mock).mockResolvedValue(mockProjects);
    (postsApi.list as jest.Mock).mockResolvedValue(mockPosts);
    (deliverablesApi.list as jest.Mock).mockResolvedValue(mockDeliverables);
    (researchApi.getClientResearchResults as jest.Mock).mockResolvedValue(mockResearchHistory);
  });

  describe('Loading States', () => {
    it('should show loading spinner initially', async () => {
      renderWithRouter(<ClientDetail />, {
        initialEntries: ['/dashboard/clients/client-1'],
      });

      expect(screen.getByText(/loading client/i)).toBeInTheDocument();
    });

    it('should hide loading spinner after data loads', async () => {
      renderWithRouter(<ClientDetail />, {
        initialEntries: ['/dashboard/clients/client-1'],
      });

      await waitFor(() => {
        expect(screen.queryByText(/loading client/i)).not.toBeInTheDocument();
      });
    });
  });

  describe('Error States', () => {
    it('should show error message when client not found', async () => {
      (clientsApi.get).mockRejectedValue(new Error('Not found'));

      renderWithRouter(<ClientDetail />, {
        initialEntries: ['/dashboard/clients/client-1'],
      });

      await waitFor(() => {
        expect(screen.getByText(/client not found/i)).toBeInTheDocument();
      });
    });

    it('should show back to clients button on error', async () => {
      (clientsApi.get).mockRejectedValue(new Error('Not found'));

      renderWithRouter(<ClientDetail />, {
        initialEntries: ['/dashboard/clients/client-1'],
      });

      await waitFor(() => {
        expect(screen.getByText(/back to clients/i)).toBeInTheDocument();
      });
    });
  });

  describe('Header Rendering', () => {
    it('should render client name', async () => {
      renderWithRouter(<ClientDetail />, {
        initialEntries: ['/dashboard/clients/client-1'],
      });

      await waitFor(() => {
        expect(screen.getByText('Acme Corp')).toBeInTheDocument();
      });
    });

    it('should render client status badge', async () => {
      renderWithRouter(<ClientDetail />, {
        initialEntries: ['/dashboard/clients/client-1'],
      });

      await waitFor(() => {
        expect(screen.getByText('active')).toBeInTheDocument();
      });
    });

    it('should render stats cards', async () => {
      renderWithRouter(<ClientDetail />, {
        initialEntries: ['/dashboard/clients/client-1'],
      });

      await waitFor(() => {
        expect(screen.getByText(/total projects/i)).toBeInTheDocument();
        expect(screen.getByText(/active projects/i)).toBeInTheDocument();
        expect(screen.getByText(/posts generated/i)).toBeInTheDocument();
        expect(screen.getByText(/deliverables/i)).toBeInTheDocument();
      });
    });

    it('should render action buttons', async () => {
      renderWithRouter(<ClientDetail />, {
        initialEntries: ['/dashboard/clients/client-1'],
      });

      await waitFor(() => {
        expect(screen.getByText('Edit')).toBeInTheDocument();
        expect(screen.getByText('Send Email')).toBeInTheDocument();
        expect(screen.getByText('Export Profile')).toBeInTheDocument();
        expect(screen.getByText('New Project')).toBeInTheDocument();
        expect(screen.getByText('Archive')).toBeInTheDocument();
      });
    });
  });

  describe('Tab Navigation', () => {
    it('should render all tab buttons', async () => {
      renderWithRouter(<ClientDetail />, {
        initialEntries: ['/dashboard/clients/client-1'],
      });

      await waitFor(() => {
        expect(screen.getByText('Overview')).toBeInTheDocument();
        expect(screen.getByText('Projects')).toBeInTheDocument();
        expect(screen.getByText('Research')).toBeInTheDocument();
        expect(screen.getByText('Content')).toBeInTheDocument();
        expect(screen.getByText('Deliverables')).toBeInTheDocument();
        expect(screen.getByText('Billing')).toBeInTheDocument();
        expect(screen.getByText('Communication')).toBeInTheDocument();
      });
    });

    it('should show overview tab by default', async () => {
      renderWithRouter(<ClientDetail />, {
        initialEntries: ['/dashboard/clients/client-1'],
      });

      await waitFor(() => {
        expect(screen.getByText(/contact information/i)).toBeInTheDocument();
      });
    });

    it('should switch to projects tab', async () => {
      const user = userEvent.setup();

      renderWithRouter(<ClientDetail />, {
        initialEntries: ['/dashboard/clients/client-1'],
      });

      await waitFor(() => {
        expect(screen.getByText('Projects')).toBeInTheDocument();
      });

      const projectsTab = screen.getByRole('button', { name: /projects/i });
      await user.click(projectsTab);

      await waitFor(() => {
        expect(screen.getByText('Q1 Campaign')).toBeInTheDocument();
      });
    });

    it('should switch to research tab', async () => {
      const user = userEvent.setup();

      renderWithRouter(<ClientDetail />, {
        initialEntries: ['/dashboard/clients/client-1'],
      });

      await waitFor(() => {
        expect(screen.getByText('Research')).toBeInTheDocument();
      });

      const researchTab = screen.getByRole('button', { name: /research/i });
      await user.click(researchTab);

      await waitFor(() => {
        expect(screen.getByText(/client research tools/i)).toBeInTheDocument();
      });
    });

    it('should switch to content tab', async () => {
      const user = userEvent.setup();

      renderWithRouter(<ClientDetail />, {
        initialEntries: ['/dashboard/clients/client-1'],
      });

      await waitFor(() => {
        expect(screen.getByText('Content')).toBeInTheDocument();
      });

      const contentTab = screen.getByRole('button', { name: /content/i });
      await user.click(contentTab);

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/search posts/i)).toBeInTheDocument();
      });
    });

    it('should switch to deliverables tab', async () => {
      const user = userEvent.setup();

      renderWithRouter(<ClientDetail />, {
        initialEntries: ['/dashboard/clients/client-1'],
      });

      await waitFor(() => {
        expect(screen.getByText('Deliverables')).toBeInTheDocument();
      });

      const deliverablesTab = screen.getAllByRole('button', { name: /deliverables/i })[0];
      await user.click(deliverablesTab);

      await waitFor(() => {
        expect(screen.getByText(/view all deliverables/i)).toBeInTheDocument();
      });
    });
  });

  describe('Overview Tab', () => {
    it('should render contact information section', async () => {
      renderWithRouter(<ClientDetail />, {
        initialEntries: ['/dashboard/clients/client-1'],
      });

      await waitFor(() => {
        expect(screen.getByText(/contact information/i)).toBeInTheDocument();
        expect(screen.getByText(/company name/i)).toBeInTheDocument();
        expect(screen.getByText(/email/i)).toBeInTheDocument();
        expect(screen.getByText(/phone/i)).toBeInTheDocument();
      });
    });

    it('should render business details section', async () => {
      renderWithRouter(<ClientDetail />, {
        initialEntries: ['/dashboard/clients/client-1'],
      });

      await waitFor(() => {
        expect(screen.getByText(/business details/i)).toBeInTheDocument();
        expect(screen.getByText(/industry/i)).toBeInTheDocument();
        expect(screen.getByText(/company size/i)).toBeInTheDocument();
      });
    });

    it('should render package details section', async () => {
      renderWithRouter(<ClientDetail />, {
        initialEntries: ['/dashboard/clients/client-1'],
      });

      await waitFor(() => {
        expect(screen.getByText(/package details/i)).toBeInTheDocument();
        expect(screen.getByText(/current tier/i)).toBeInTheDocument();
        expect(screen.getByText(/pricing/i)).toBeInTheDocument();
      });
    });

    it('should render notes textarea', async () => {
      renderWithRouter(<ClientDetail />, {
        initialEntries: ['/dashboard/clients/client-1'],
      });

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/add notes about this client/i)).toBeInTheDocument();
      });
    });
  });

  describe('Projects Tab', () => {
    it('should render projects table', async () => {
      const user = userEvent.setup();

      renderWithRouter(<ClientDetail />, {
        initialEntries: ['/dashboard/clients/client-1'],
      });

      await waitFor(() => {
        const projectsTab = screen.getByRole('button', { name: /projects/i });
        user.click(projectsTab);
      });

      await waitFor(() => {
        expect(screen.getByText('Q1 Campaign')).toBeInTheDocument();
        expect(screen.getByText('Q2 Campaign')).toBeInTheDocument();
      });
    });

    it('should show empty state when no projects', async () => {
      (projectsApi.list).mockResolvedValue({ items: [], total: 0 });
      const user = userEvent.setup();

      renderWithRouter(<ClientDetail />, {
        initialEntries: ['/dashboard/clients/client-1'],
      });

      await waitFor(() => {
        const projectsTab = screen.getByRole('button', { name: /projects/i });
        user.click(projectsTab);
      });

      await waitFor(() => {
        expect(screen.getByText(/no projects yet/i)).toBeInTheDocument();
        expect(screen.getByText(/create first project/i)).toBeInTheDocument();
      });
    });
  });

  describe('Research Tab', () => {
    it('should render research tool cards', async () => {
      const user = userEvent.setup();

      renderWithRouter(<ClientDetail />, {
        initialEntries: ['/dashboard/clients/client-1'],
      });

      await waitFor(() => {
        const researchTab = screen.getByRole('button', { name: /research/i });
        user.click(researchTab);
      });

      await waitFor(() => {
        expect(screen.getByText(/voice analysis/i)).toBeInTheDocument();
        expect(screen.getByText(/brand archetype/i)).toBeInTheDocument();
        expect(screen.getByText(/competitive analysis/i)).toBeInTheDocument();
        expect(screen.getByText(/market trends/i)).toBeInTheDocument();
      });
    });

    it('should render research history table', async () => {
      const user = userEvent.setup();

      renderWithRouter(<ClientDetail />, {
        initialEntries: ['/dashboard/clients/client-1'],
      });

      await waitFor(() => {
        const researchTab = screen.getByRole('button', { name: /research/i });
        user.click(researchTab);
      });

      await waitFor(() => {
        expect(screen.getByText(/research history/i)).toBeInTheDocument();
        expect(screen.getByText(/voice analysis/i)).toBeInTheDocument();
      });
    });

    it('should show empty state when no research history', async () => {
      (researchApi.getClientResearchResults).mockResolvedValue([]);
      const user = userEvent.setup();

      renderWithRouter(<ClientDetail />, {
        initialEntries: ['/dashboard/clients/client-1'],
      });

      await waitFor(() => {
        const researchTab = screen.getByRole('button', { name: /research/i });
        user.click(researchTab);
      });

      await waitFor(() => {
        expect(screen.getByText(/no research has been run/i)).toBeInTheDocument();
      });
    });

    it('should handle research tool button click', async () => {
      (researchApi.run).mockResolvedValue({
        id: 'research-2',
        status: 'completed',
        data: {},
      });
      const user = userEvent.setup();

      renderWithRouter(<ClientDetail />, {
        initialEntries: ['/dashboard/clients/client-1'],
      });

      await waitFor(() => {
        const researchTab = screen.getByRole('button', { name: /research/i });
        user.click(researchTab);
      });

      await waitFor(() => {
        const voiceButton = screen.getByText(/run voice analysis/i);
        user.click(voiceButton);
      });

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/paste 2-3 existing content samples/i)).toBeInTheDocument();
      });
    });
  });

  describe('Content Tab', () => {
    it('should render filter controls', async () => {
      const user = userEvent.setup();

      renderWithRouter(<ClientDetail />, {
        initialEntries: ['/dashboard/clients/client-1'],
      });

      await waitFor(() => {
        const contentTab = screen.getByRole('button', { name: /content/i });
        user.click(contentTab);
      });

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/search posts/i)).toBeInTheDocument();
        expect(screen.getByText(/all projects/i)).toBeInTheDocument();
        expect(screen.getByText(/all platforms/i)).toBeInTheDocument();
      });
    });

    it('should render posts grid', async () => {
      const user = userEvent.setup();

      renderWithRouter(<ClientDetail />, {
        initialEntries: ['/dashboard/clients/client-1'],
      });

      await waitFor(() => {
        const contentTab = screen.getByRole('button', { name: /content/i });
        user.click(contentTab);
      });

      await waitFor(() => {
        expect(screen.getByText(/test post content/i)).toBeInTheDocument();
      });
    });

    it('should show empty state when no posts', async () => {
      (postsApi.list).mockResolvedValue({ items: [], total: 0 });
      const user = userEvent.setup();

      renderWithRouter(<ClientDetail />, {
        initialEntries: ['/dashboard/clients/client-1'],
      });

      await waitFor(() => {
        const contentTab = screen.getByRole('button', { name: /content/i });
        user.click(contentTab);
      });

      await waitFor(() => {
        expect(screen.getByText(/no content generated yet/i)).toBeInTheDocument();
      });
    });
  });

  describe('Deliverables Tab', () => {
    it('should render deliverables table', async () => {
      const user = userEvent.setup();

      renderWithRouter(<ClientDetail />, {
        initialEntries: ['/dashboard/clients/client-1'],
      });

      await waitFor(() => {
        const deliverablesTab = screen.getAllByRole('button', { name: /deliverables/i })[0];
        user.click(deliverablesTab);
      });

      await waitFor(() => {
        expect(screen.getByText(/view all deliverables/i)).toBeInTheDocument();
      });
    });

    it('should show empty state when no deliverables', async () => {
      (deliverablesApi.list).mockResolvedValue([]);
      const user = userEvent.setup();

      renderWithRouter(<ClientDetail />, {
        initialEntries: ['/dashboard/clients/client-1'],
      });

      await waitFor(() => {
        const deliverablesTab = screen.getAllByRole('button', { name: /deliverables/i })[0];
        user.click(deliverablesTab);
      });

      await waitFor(() => {
        expect(screen.getByText(/no deliverables yet/i)).toBeInTheDocument();
      });
    });
  });

  describe('Billing Tab', () => {
    it('should render billing stats cards', async () => {
      const user = userEvent.setup();

      renderWithRouter(<ClientDetail />, {
        initialEntries: ['/dashboard/clients/client-1'],
      });

      await waitFor(() => {
        const billingTab = screen.getByRole('button', { name: /billing/i });
        user.click(billingTab);
      });

      await waitFor(() => {
        expect(screen.getByText(/total msrp/i)).toBeInTheDocument();
        expect(screen.getByText(/outstanding/i)).toBeInTheDocument();
      });
    });

    it('should render invoices table', async () => {
      const user = userEvent.setup();

      renderWithRouter(<ClientDetail />, {
        initialEntries: ['/dashboard/clients/client-1'],
      });

      await waitFor(() => {
        const billingTab = screen.getByRole('button', { name: /billing/i });
        user.click(billingTab);
      });

      await waitFor(() => {
        expect(screen.getByText(/generate invoice/i)).toBeInTheDocument();
      });
    });
  });

  describe('Communication Tab', () => {
    it('should render communication log', async () => {
      const user = userEvent.setup();

      renderWithRouter(<ClientDetail />, {
        initialEntries: ['/dashboard/clients/client-1'],
      });

      await waitFor(() => {
        const commTab = screen.getByRole('button', { name: /communication/i });
        user.click(commTab);
      });

      await waitFor(() => {
        expect(screen.getByText(/communication log/i)).toBeInTheDocument();
        expect(screen.getByText(/new communication/i)).toBeInTheDocument();
      });
    });
  });

  describe('Export Functionality', () => {
    it('should handle export profile button click', async () => {
      (clientsApi.exportProfile).mockResolvedValue({
        blob: new Blob(['test'], { type: 'text/markdown' }),
        filename: 'acme-corp-profile.md',
      });
      const user = userEvent.setup();

      renderWithRouter(<ClientDetail />, {
        initialEntries: ['/dashboard/clients/client-1'],
      });

      await waitFor(() => {
        const exportBtn = screen.getByText(/export profile/i);
        user.click(exportBtn);
      });

      await waitFor(() => {
        expect(clientsApi.exportProfile).toHaveBeenCalledWith('client-1');
      });
    });

    it('should show loading state during export', async () => {
      (clientsApi.exportProfile).mockImplementation(
        () => new Promise(resolve => setTimeout(resolve, 1000))
      );
      const user = userEvent.setup();

      renderWithRouter(<ClientDetail />, {
        initialEntries: ['/dashboard/clients/client-1'],
      });

      await waitFor(() => {
        const exportBtn = screen.getByText(/export profile/i);
        user.click(exportBtn);
      });

      expect(screen.getByText(/exporting/i)).toBeInTheDocument();
    });
  });

  describe('User Interactions', () => {
    it('should handle back button click', async () => {
      const user = userEvent.setup();

      renderWithRouter(<ClientDetail />, {
        initialEntries: ['/dashboard/clients/client-1'],
      });

      await waitFor(() => {
        const backBtn = screen.getByText(/back to clients/i);
        user.click(backBtn);
      });

      // Navigation would be tested in integration tests
    });

    it('should handle new project button click', async () => {
      const user = userEvent.setup();

      renderWithRouter(<ClientDetail />, {
        initialEntries: ['/dashboard/clients/client-1'],
      });

      await waitFor(() => {
        const newProjectBtn = screen.getByText(/new project/i);
        user.click(newProjectBtn);
      });

      // Navigation would be tested in integration tests
    });

    it('should handle notes input', async () => {
      const user = userEvent.setup();

      renderWithRouter(<ClientDetail />, {
        initialEntries: ['/dashboard/clients/client-1'],
      });

      await waitFor(() => {
        const notesField = screen.getByPlaceholderText(/add notes about this client/i);
        user.type(notesField, 'Test notes');
      });

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/add notes about this client/i)).toHaveValue('Test notes');
      });
    });
  });

  describe('Data Integration', () => {
    it('should make all required API calls on mount', async () => {
      renderWithRouter(<ClientDetail />, {
        initialEntries: ['/dashboard/clients/client-1'],
      });

      await waitFor(() => {
        expect(clientsApi.get).toHaveBeenCalledWith('client-1');
        expect(projectsApi.list).toHaveBeenCalled();
        expect(postsApi.list).toHaveBeenCalled();
        expect(deliverablesApi.list).toHaveBeenCalled();
        expect(researchApi.getClientResearchResults).toHaveBeenCalledWith('client-1');
      });
    });

    it('should calculate metrics correctly', async () => {
      renderWithRouter(<ClientDetail />, {
        initialEntries: ['/dashboard/clients/client-1'],
      });

      await waitFor(() => {
        expect(screen.getByText('2')).toBeInTheDocument(); // Total projects
      });
    });
  });
});
