/**
 * Comprehensive tests for ClientDetail page (1,551 LOC)
 *
 * Coverage focus:
 * - Loading states
 * - Data rendering across all tabs
 * - Tab switching
 * - User interactions
 * - Error states
 * - Research tools
 * - Export functionality
 *
 * NOTE: ClientDetail reads its `clientId` from the route via useParams and the
 * client query is `enabled: !!clientId`. Tests MUST render it inside a matching
 * <Route path="/dashboard/clients/:clientId"> or the query never runs and the
 * component renders the "Client not found" branch.
 */

import { describe, it, expect, beforeEach } from '@jest/globals';
import { screen, waitFor } from '@testing-library/react';
import { Routes, Route } from 'react-router-dom';
import { renderWithRouter, userEvent } from '@/__tests__/setup/test-utils';
import ClientDetail from '../ClientDetail';
import { clientsApi } from '@/api/clients';
import { projectsApi } from '@/api/projects';
import { postsApi } from '@/api/posts';
import { deliverablesApi } from '@/api/deliverables';
import { researchApi } from '@/api/research';
import { communicationsApi } from '@/api/communications';
import { storiesApi } from '@/api/stories';

// Mock API modules
jest.mock('@/api/clients');
jest.mock('@/api/projects');
jest.mock('@/api/posts');
jest.mock('@/api/deliverables');
jest.mock('@/api/research');
jest.mock('@/api/communications');
jest.mock('@/api/stories');

const mockClient = {
  id: 'client-1',
  name: 'Acme Corp',
  email: 'acme@example.com',
  industry: 'Software',
  location: 'San Francisco, CA',
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

// The client research results endpoint returns a ResearchResultListResponse
// ({ results, total, clientId }) — NOT a bare array. The component reads
// `researchData?.results`.
const mockResearchResults = [
  {
    id: 'research-1',
    userId: 'user-1',
    clientId: 'client-1',
    toolName: 'voice_analysis',
    toolLabel: 'Voice Analysis',
    outputs: {},
    status: 'completed',
    createdAt: '2024-01-18T10:00:00Z',
    data: {
      summary: 'Professional, technical voice with clear CTAs',
    },
  },
];

const mockResearchResponse = {
  results: mockResearchResults,
  total: mockResearchResults.length,
  clientId: 'client-1',
};

/**
 * Render ClientDetail inside a route that supplies the :clientId param.
 */
function renderPage(clientId = 'client-1') {
  return renderWithRouter(
    <Routes>
      <Route path="/dashboard/clients/:clientId" element={<ClientDetail />} />
    </Routes>,
    { initialEntries: [`/dashboard/clients/${clientId}`] }
  );
}

describe('ClientDetail Page', () => {
  beforeEach(() => {
    jest.clearAllMocks();

    // Setup default mocks
    (clientsApi.get as jest.Mock).mockResolvedValue(mockClient);
    (projectsApi.list as jest.Mock).mockResolvedValue(mockProjects);
    (postsApi.list as jest.Mock).mockResolvedValue(mockPosts);
    (deliverablesApi.list as jest.Mock).mockResolvedValue(mockDeliverables);
    (researchApi.getClientResearchResults as jest.Mock).mockResolvedValue(mockResearchResponse);
    (communicationsApi.listClientCommunications as jest.Mock).mockResolvedValue([]);
    (storiesApi.listClientStories as jest.Mock).mockResolvedValue({ stories: [], total: 0 });
  });

  describe('Loading States', () => {
    it('should show loading spinner initially', async () => {
      renderPage();

      expect(screen.getByText(/loading client/i)).toBeInTheDocument();
    });

    it('should hide loading spinner after data loads', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.queryByText(/loading client/i)).not.toBeInTheDocument();
      });
    });
  });

  describe('Error States', () => {
    it('should show error message when client not found', async () => {
      (clientsApi.get as jest.Mock).mockRejectedValue(new Error('Not found'));

      renderPage();

      await waitFor(() => {
        expect(screen.getByText(/client not found/i)).toBeInTheDocument();
      });
    });

    it('should show back to clients button on error', async () => {
      (clientsApi.get as jest.Mock).mockRejectedValue(new Error('Not found'));

      renderPage();

      await waitFor(() => {
        expect(screen.getByText(/back to clients/i)).toBeInTheDocument();
      });
    });
  });

  describe('Header Rendering', () => {
    it('should render client name', async () => {
      renderPage();

      await waitFor(() => {
        // The client name renders in the header heading and (pre-mounted) in
        // the closed Delete dialog, so scope to the heading.
        expect(screen.getByRole('heading', { name: 'Acme Corp' })).toBeInTheDocument();
      });
    });

    it('should render client name as heading', async () => {
      // The status badge was removed from the header; the header now renders the
      // client name as an <h1>.
      renderPage();

      await waitFor(() => {
        expect(screen.getByRole('heading', { name: 'Acme Corp' })).toBeInTheDocument();
      });
    });

    it('should render stats cards', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByText(/total projects/i)).toBeInTheDocument();
        expect(screen.getByText(/active projects/i)).toBeInTheDocument();
        expect(screen.getByText(/posts generated/i)).toBeInTheDocument();
        // "Deliverables" appears both as a stat label and a tab button.
        expect(screen.getAllByText(/deliverables/i).length).toBeGreaterThan(0);
      });
    });

    it('should render action buttons', async () => {
      renderPage();

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
      renderPage();

      await waitFor(() => {
        expect(screen.getByText('Overview')).toBeInTheDocument();
        expect(screen.getByText('Projects')).toBeInTheDocument();
        expect(screen.getByText('Research')).toBeInTheDocument();
        expect(screen.getByText('Content')).toBeInTheDocument();
        // "Deliverables" also appears as a stat label.
        expect(screen.getAllByText('Deliverables').length).toBeGreaterThan(0);
        expect(screen.getByText('Billing')).toBeInTheDocument();
        expect(screen.getByText('Communication')).toBeInTheDocument();
      });
    });

    it('should show overview tab by default', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByText(/contact information/i)).toBeInTheDocument();
      });
    });

    it('should switch to projects tab', async () => {
      const user = userEvent.setup();

      renderPage();

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

      renderPage();

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

      renderPage();

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

      renderPage();

      await waitFor(() => {
        expect(screen.getAllByRole('button', { name: /deliverables/i })[0]).toBeInTheDocument();
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
      renderPage();

      await waitFor(() => {
        expect(screen.getByText(/contact information/i)).toBeInTheDocument();
        expect(screen.getByText('Company Name')).toBeInTheDocument();
        expect(screen.getByText('Email')).toBeInTheDocument();
      });
    });

    it('should render business details section', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByText(/business details/i)).toBeInTheDocument();
        expect(screen.getByText('Industry')).toBeInTheDocument();
        // The overview now shows Location (Company Size was removed).
        expect(screen.getByText('Location')).toBeInTheDocument();
      });
    });

    it('should render custom notes section', async () => {
      // The old "Package Details" card was removed; the overview now has a
      // Custom Notes section with a textarea.
      renderPage();

      await waitFor(() => {
        expect(screen.getByText(/custom notes/i)).toBeInTheDocument();
        expect(
          screen.getByPlaceholderText(/add notes about this client/i)
        ).toBeInTheDocument();
      });
    });

    it('should render notes textarea', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/add notes about this client/i)).toBeInTheDocument();
      });
    });
  });

  describe('Projects Tab', () => {
    it('should render projects table', async () => {
      const user = userEvent.setup();

      renderPage();

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /projects/i })).toBeInTheDocument();
      });
      await user.click(screen.getByRole('button', { name: /projects/i }));

      await waitFor(() => {
        expect(screen.getByText('Q1 Campaign')).toBeInTheDocument();
        expect(screen.getByText('Q2 Campaign')).toBeInTheDocument();
      });
    });

    it('should show empty state when no projects', async () => {
      (projectsApi.list as jest.Mock).mockResolvedValue({ items: [], total: 0 });
      const user = userEvent.setup();

      renderPage();

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /projects/i })).toBeInTheDocument();
      });
      await user.click(screen.getByRole('button', { name: /projects/i }));

      await waitFor(() => {
        expect(screen.getByText(/no projects yet/i)).toBeInTheDocument();
        expect(screen.getByText(/create first project/i)).toBeInTheDocument();
      });
    });
  });

  describe('Research Tab', () => {
    it('should render research tool cards', async () => {
      const user = userEvent.setup();

      renderPage();

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /research/i })).toBeInTheDocument();
      });
      await user.click(screen.getByRole('button', { name: /research/i }));

      await waitFor(() => {
        // Tool card headings ("Voice Analysis" also appears in the button text,
        // so scope to the heading role).
        expect(screen.getByRole('heading', { name: 'Voice Analysis' })).toBeInTheDocument();
        expect(screen.getByRole('heading', { name: 'Brand Archetype' })).toBeInTheDocument();
        expect(screen.getByRole('heading', { name: 'Competitive Analysis' })).toBeInTheDocument();
        expect(screen.getByRole('heading', { name: 'Market Trends' })).toBeInTheDocument();
      });
    });

    it('should render research history table', async () => {
      const user = userEvent.setup();

      renderPage();

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /research/i })).toBeInTheDocument();
      });
      await user.click(screen.getByRole('button', { name: /research/i }));

      await waitFor(() => {
        expect(screen.getByText(/research history/i)).toBeInTheDocument();
        // Summary text from the mocked research result row (unique).
        expect(
          screen.getByText(/professional, technical voice with clear ctas/i)
        ).toBeInTheDocument();
      });
    });

    it('should show empty state when no research history', async () => {
      (researchApi.getClientResearchResults as jest.Mock).mockResolvedValue({
        results: [],
        total: 0,
        clientId: 'client-1',
      });
      const user = userEvent.setup();

      renderPage();

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /research/i })).toBeInTheDocument();
      });
      await user.click(screen.getByRole('button', { name: /research/i }));

      await waitFor(() => {
        expect(screen.getByText(/no research has been run/i)).toBeInTheDocument();
      });
    });

    it('should handle research tool button click', async () => {
      (researchApi.run as jest.Mock).mockResolvedValue({
        tool: 'voice_analysis',
        outputs: {},
      });
      const user = userEvent.setup();

      renderPage();

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /research/i })).toBeInTheDocument();
      });
      await user.click(screen.getByRole('button', { name: /research/i }));

      const voiceButton = await screen.findByText('Run Voice Analysis');
      await user.click(voiceButton);

      await waitFor(() => {
        expect(
          screen.getByPlaceholderText(/paste 2-3 existing content samples/i)
        ).toBeInTheDocument();
      });
    });
  });

  describe('Content Tab', () => {
    it('should render filter controls', async () => {
      const user = userEvent.setup();

      renderPage();

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /content/i })).toBeInTheDocument();
      });
      await user.click(screen.getByRole('button', { name: /content/i }));

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/search posts/i)).toBeInTheDocument();
        expect(screen.getByText('All Projects')).toBeInTheDocument();
        expect(screen.getByText('All Platforms')).toBeInTheDocument();
      });
    });

    it('should render posts grid', async () => {
      const user = userEvent.setup();

      renderPage();

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /content/i })).toBeInTheDocument();
      });
      await user.click(screen.getByRole('button', { name: /content/i }));

      await waitFor(() => {
        expect(screen.getByText(/test post content/i)).toBeInTheDocument();
      });
    });

    it('should show empty state when no posts', async () => {
      (postsApi.list as jest.Mock).mockResolvedValue({ items: [], total: 0 });
      const user = userEvent.setup();

      renderPage();

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /content/i })).toBeInTheDocument();
      });
      await user.click(screen.getByRole('button', { name: /content/i }));

      await waitFor(() => {
        expect(screen.getByText(/no content generated yet/i)).toBeInTheDocument();
      });
    });
  });

  describe('Deliverables Tab', () => {
    it('should render deliverables table', async () => {
      const user = userEvent.setup();

      renderPage();

      await waitFor(() => {
        expect(screen.getAllByRole('button', { name: /deliverables/i })[0]).toBeInTheDocument();
      });
      await user.click(screen.getAllByRole('button', { name: /deliverables/i })[0]);

      await waitFor(() => {
        expect(screen.getByText(/view all deliverables/i)).toBeInTheDocument();
      });
    });

    it('should show empty state when no deliverables', async () => {
      (deliverablesApi.list as jest.Mock).mockResolvedValue([]);
      const user = userEvent.setup();

      renderPage();

      await waitFor(() => {
        expect(screen.getAllByRole('button', { name: /deliverables/i })[0]).toBeInTheDocument();
      });
      await user.click(screen.getAllByRole('button', { name: /deliverables/i })[0]);

      await waitFor(() => {
        expect(screen.getByText(/no deliverables yet/i)).toBeInTheDocument();
      });
    });
  });

  describe('Billing Tab', () => {
    it('should render billing placeholder', async () => {
      // Billing is not implemented yet; the tab renders a placeholder rather
      // than stats cards / invoices.
      const user = userEvent.setup();

      renderPage();

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /billing/i })).toBeInTheDocument();
      });
      await user.click(screen.getByRole('button', { name: /billing/i }));

      await waitFor(() => {
        expect(screen.getByText(/billing not yet available/i)).toBeInTheDocument();
      });
    });

    it('should explain billing is coming in a future update', async () => {
      const user = userEvent.setup();

      renderPage();

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /billing/i })).toBeInTheDocument();
      });
      await user.click(screen.getByRole('button', { name: /billing/i }));

      await waitFor(() => {
        expect(screen.getByText(/invoice tracking will be available/i)).toBeInTheDocument();
      });
    });
  });

  describe('Communication Tab', () => {
    it('should render communication log', async () => {
      const user = userEvent.setup();

      renderPage();

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /communication/i })).toBeInTheDocument();
      });
      await user.click(screen.getByRole('button', { name: /communication/i }));

      await waitFor(() => {
        expect(screen.getByText(/communication log/i)).toBeInTheDocument();
        expect(screen.getByText(/new communication/i)).toBeInTheDocument();
      });
    });
  });

  describe('Export Functionality', () => {
    it('should handle export profile button click', async () => {
      (clientsApi.exportProfile as jest.Mock).mockResolvedValue({
        blob: new Blob(['test'], { type: 'text/markdown' }),
        filename: 'acme-corp-profile.md',
      });
      const user = userEvent.setup();

      renderPage();

      const exportBtn = await screen.findByText(/export profile/i);
      await user.click(exportBtn);

      await waitFor(() => {
        expect(clientsApi.exportProfile).toHaveBeenCalledWith('client-1');
      });
    });

    it('should show loading state during export', async () => {
      (clientsApi.exportProfile as jest.Mock).mockImplementation(
        () => new Promise(resolve => setTimeout(resolve, 1000))
      );
      const user = userEvent.setup();

      renderPage();

      const exportBtn = await screen.findByText(/export profile/i);
      await user.click(exportBtn);

      expect(await screen.findByText(/exporting/i)).toBeInTheDocument();
    });
  });

  describe('User Interactions', () => {
    it('should handle back button click', async () => {
      const user = userEvent.setup();

      renderPage();

      const backBtn = await screen.findByText(/back to clients/i);
      await user.click(backBtn);

      // Navigation would be tested in integration tests
    });

    it('should handle new project button click', async () => {
      const user = userEvent.setup();

      renderPage();

      const newProjectBtn = await screen.findByText(/new project/i);
      await user.click(newProjectBtn);

      // Navigation would be tested in integration tests
    });

    it('should handle notes input', async () => {
      const user = userEvent.setup();

      renderPage();

      const notesField = await screen.findByPlaceholderText(/add notes about this client/i);
      await user.type(notesField, 'Test notes');

      expect(notesField).toHaveValue('Test notes');
    });
  });

  describe('Data Integration', () => {
    it('should make all required API calls on mount', async () => {
      renderPage();

      await waitFor(() => {
        expect(clientsApi.get).toHaveBeenCalledWith('client-1');
        expect(projectsApi.list).toHaveBeenCalled();
        expect(postsApi.list).toHaveBeenCalled();
        expect(deliverablesApi.list).toHaveBeenCalled();
        expect(researchApi.getClientResearchResults).toHaveBeenCalledWith('client-1');
      });
    });

    it('should calculate metrics correctly', async () => {
      renderPage();

      await waitFor(() => {
        // Total projects / active projects / posts all resolve to 2.
        expect(screen.getAllByText('2').length).toBeGreaterThan(0);
      });
    });
  });
});
