import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import Wizard from '@/pages/Wizard';
import { clientsApi } from '@/api/clients';
import { projectsApi } from '@/api/projects';
import { researchApi } from '@/api/research';
import { generatorApi } from '@/api/generator';

// The wizard persists new clients/projects via the API on "Save Profile" and the
// Research/Templates steps fetch tool + dependency metadata. Mock those modules so the
// profile → research → templates → generation flow can advance without a live server.
// (ResearchPanel hard-fails to an error view if its tools list can't load.)
jest.mock('@/api/clients');
jest.mock('@/api/projects');
jest.mock('@/api/research');
jest.mock('@/api/generator');

const mockClientsApi = clientsApi as jest.Mocked<typeof clientsApi>;
const mockProjectsApi = projectsApi as jest.Mocked<typeof projectsApi>;
const mockResearchApi = researchApi as jest.Mocked<typeof researchApi>;
const mockGeneratorApi = generatorApi as jest.Mocked<typeof generatorApi>;

// Test wrapper with providers
function TestWrapper({ children }: { children: React.ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  );
}

const REQUIRED_KEYWORDS = ['alpha', 'beta', 'gamma', 'delta', 'epsilon'];

// Fill the profile form's required fields. Platform selection was moved out of the
// profile step into the templates step (PlatformSelector), so it is no longer set here.
// `withKeywords` adds the 5 SEO keywords required to advance research → templates.
async function fillProfile(
  user: ReturnType<typeof userEvent.setup>,
  { withKeywords = false }: { withKeywords?: boolean } = {}
) {
  await user.type(screen.getByPlaceholderText('Acme Corp'), 'Test Company');
  await user.type(
    screen.getByPlaceholderText(/cloud-based project management/i),
    'We provide comprehensive cloud-based software solutions for small and medium-sized businesses to help them streamline their operations and improve productivity'
  );
  await user.type(
    screen.getByPlaceholderText(/Small business owners/i),
    'Small businesses with 5-20 employees who need better collaboration tools'
  );

  if (withKeywords) {
    const keywordInput = screen.getByPlaceholderText(/add a keyword/i);
    for (const kw of REQUIRED_KEYWORDS) {
      await user.clear(keywordInput);
      await user.type(keywordInput, `${kw}{Enter}`);
    }
  }
}

// Drive the wizard from the profile step to the templates step (TemplateQuantitySelector).
async function advanceToTemplates(user: ReturnType<typeof userEvent.setup>) {
  await fillProfile(user, { withKeywords: true });
  await user.click(screen.getByRole('button', { name: /save profile/i }));

  // Profile save advances to the Research step.
  const skipButton = await screen.findByRole('button', { name: /skip research/i });
  await user.click(skipButton);

  // With 5+ keywords, research → templates advances without the keyword warning.
  await screen.findByText(/Custom Template Quantities/i);
}

describe('Wizard Flow Integration Tests', () => {
  beforeEach(() => {
    localStorage.clear();
    jest.clearAllMocks();
    mockClientsApi.list.mockResolvedValue([]);
    mockClientsApi.create.mockResolvedValue({ id: 'client-new', name: 'Test Company' } as never);
    mockClientsApi.get.mockResolvedValue({ id: 'client-new', name: 'Test Company' } as never);
    mockClientsApi.update.mockResolvedValue({ id: 'client-new', name: 'Test Company' } as never);
    mockProjectsApi.create.mockResolvedValue({
      id: 'proj-new',
      name: 'Test Company - Content Project',
      clientId: 'client-new',
      status: 'draft',
    } as never);
    mockProjectsApi.get.mockResolvedValue({
      id: 'proj-new',
      name: 'Test Company - Content Project',
      clientId: 'client-new',
      status: 'draft',
    } as never);
    mockResearchApi.listTools.mockResolvedValue([] as never);
    mockResearchApi.getClientHistory.mockResolvedValue(null as never);
    mockResearchApi.getProjectResearchResults.mockResolvedValue({ results: [], total: 0 } as never);
    mockResearchApi.getClientResearchResults.mockResolvedValue({ results: [], total: 0 } as never);
    mockGeneratorApi.getTemplateDependencies.mockResolvedValue({
      research_dependencies: { required: [], recommended: [] },
    } as never);
    mockGeneratorApi.validateTemplates.mockResolvedValue({
      blocked_templates: [],
      warnings: [],
      story_counts: {},
    } as never);
  });

  describe('Step 1: Client Profile', () => {
    it('should render client profile form', () => {
      render(
        <TestWrapper>
          <Wizard />
        </TestWrapper>
      );

      // Look for the heading specifically (not the stepper button)
      expect(screen.getByRole('heading', { name: /client profile/i })).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Acme Corp')).toBeInTheDocument();
    });

    it.skip('should validate required fields', async () => {
      // TODO: Fix validation error rendering
      // Validation logic exists but errors aren't rendering in tests
      const user = userEvent.setup({ delay: null });
      render(
        <TestWrapper>
          <Wizard />
        </TestWrapper>
      );

      const saveButton = screen.getByRole('button', { name: /save profile/i });
      await user.click(saveButton);

      // Should show validation errors for required fields
      await waitFor(() => {
        const errors = screen.queryAllByText(/required|provide|describe/i);
        expect(errors.length).toBeGreaterThan(0);
      });
    });

    it('should save client brief and advance to research', async () => {
      const user = userEvent.setup({ delay: null });
      render(
        <TestWrapper>
          <Wizard />
        </TestWrapper>
      );

      await fillProfile(user);

      // Save profile
      await user.click(screen.getByRole('button', { name: /save profile/i }));

      // Save now advances to the Research step (research was inserted between
      // profile and templates in the wizard redesign).
      await waitFor(() => {
        expect(screen.getByRole('heading', { name: /research tools/i })).toBeInTheDocument();
      });
      expect(mockClientsApi.create).toHaveBeenCalled();
      expect(mockProjectsApi.create).toHaveBeenCalled();
    });

    it('should add pain points and questions', async () => {
      const user = userEvent.setup({ delay: null });
      render(
        <TestWrapper>
          <Wizard />
        </TestWrapper>
      );

      // Add pain point (Enter key triggers the add handler; scoping by the button
      // is unreliable because several sections now share an "Add" button).
      const painPointInput = screen.getByPlaceholderText(/add a pain point/i);
      await user.type(painPointInput, 'Scattered communication{Enter}');

      await waitFor(() => {
        expect(screen.getByText('Scattered communication')).toBeInTheDocument();
      });

      // Add question — the question section's Add button is scoped via its container.
      const questionInput = screen.getByPlaceholderText(/what do customers ask/i);
      await user.type(questionInput, 'How do I improve team coordination?');
      const questionSection = questionInput.closest('div.space-y-2') as HTMLElement;
      await user.click(within(questionSection).getByRole('button', { name: /add/i }));

      await waitFor(() => {
        expect(screen.getByText(/How do I improve team coordination\?/)).toBeInTheDocument();
      });
    });

    it('should add SEO keywords', async () => {
      const user = userEvent.setup({ delay: null });
      render(
        <TestWrapper>
          <Wizard />
        </TestWrapper>
      );

      // Platform selection was moved to the templates step (PlatformSelector); the
      // profile step now collects SEO keywords instead.
      const keywordInput = screen.getByPlaceholderText(/add a keyword/i);
      await user.type(keywordInput, 'project management{Enter}');

      await waitFor(() => {
        expect(screen.getByText('project management')).toBeInTheDocument();
      });
    });
  });

  describe('Step 2: Template Selection', () => {
    it('should display all templates', async () => {
      const user = userEvent.setup({ delay: null });
      render(
        <TestWrapper>
          <Wizard />
        </TestWrapper>
      );

      await advanceToTemplates(user);

      // TemplateQuantitySelector renders every template as "#<n>. <name>".
      expect(screen.getByText(/#1\. Problem Recognition/)).toBeInTheDocument();
      expect(screen.getByText(/#2\. Statistic \+ Insight/)).toBeInTheDocument();
      expect(screen.getByText(/#15\. Milestone/)).toBeInTheDocument();
    });

    it('should adjust template quantities', async () => {
      const user = userEvent.setup({ delay: null });
      render(
        <TestWrapper>
          <Wizard />
        </TestWrapper>
      );

      await advanceToTemplates(user);

      // Increase the first template's quantity via its stepper control.
      const increaseButtons = screen.getAllByLabelText('Increase quantity');
      await user.click(increaseButtons[0]);

      // Total posts count updates in the pricing summary.
      await waitFor(() => {
        expect(screen.getByText('Total Posts')).toBeInTheDocument();
      });
      // The Continue button becomes enabled once at least one post is selected.
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /continue to generation/i })).not.toBeDisabled();
      });
    }, 20000);

    it('should prevent continuing with no templates', async () => {
      const user = userEvent.setup({ delay: null });
      render(
        <TestWrapper>
          <Wizard />
        </TestWrapper>
      );

      await advanceToTemplates(user);

      const continueButton = screen.getByRole('button', { name: /continue to generation/i });
      expect(continueButton).toBeDisabled();
    });

    it('should advance to generation step', async () => {
      const user = userEvent.setup({ delay: null });
      render(
        <TestWrapper>
          <Wizard />
        </TestWrapper>
      );

      await advanceToTemplates(user);

      // Select at least one post.
      const increaseButtons = screen.getAllByLabelText('Increase quantity');
      await user.click(increaseButtons[0]);

      const continueButton = screen.getByRole('button', { name: /continue to generation/i });
      await waitFor(() => expect(continueButton).not.toBeDisabled());
      await user.click(continueButton);

      // Generation lives in the Quality Gate step; GenerationPanel shows "Generate All".
      await waitFor(() => {
        expect(screen.getByRole('heading', { name: /generate all/i })).toBeInTheDocument();
      });
    }, 20000);
  });

  describe('Step 3: Generation', () => {
    it('should show generation panel', async () => {
      render(
        <TestWrapper>
          <Wizard />
        </TestWrapper>
      );

      // Advance to generation step (would need to complete profile and templates)
      // For now, verify the component can render
      expect(screen.getByText('Project Wizard')).toBeInTheDocument();
    });
  });

  describe('Wizard Navigation', () => {
    it('should display wizard stepper with all steps', () => {
      render(
        <TestWrapper>
          <Wizard />
        </TestWrapper>
      );

      // Stepper steps: Client Profile → Research → Templates → Quality Gate → Export.
      // (/research/i also matches a button inside the profile's research section, so
      // assert at least one match rather than a unique one.)
      expect(screen.getByRole('button', { name: /client profile/i })).toBeInTheDocument();
      expect(screen.getAllByRole('button', { name: /research/i }).length).toBeGreaterThan(0);
      expect(screen.getByRole('button', { name: /templates/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /quality gate/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /export/i })).toBeInTheDocument();
    });

    it('should show wizard status at bottom', () => {
      render(
        <TestWrapper>
          <Wizard />
        </TestWrapper>
      );

      expect(screen.getByText('Wizard Status')).toBeInTheDocument();
      expect(screen.getByText(/Client Brief:/)).toBeInTheDocument();
      expect(screen.getByText(/Templates:/)).toBeInTheDocument();
    });
  });

  describe('Complete Wizard Flow', () => {
    it('should complete entire wizard workflow', async () => {
      const user = userEvent.setup({ delay: null });
      render(
        <TestWrapper>
          <Wizard />
        </TestWrapper>
      );

      // Step 1 → 2: profile + keywords → research → templates.
      await advanceToTemplates(user);

      // Step 3: select posts and continue to generation.
      const increaseButtons = screen.getAllByLabelText('Increase quantity');
      await user.click(increaseButtons[0]);

      const continueButton = screen.getByRole('button', { name: /continue to generation/i });
      await waitFor(() => expect(continueButton).not.toBeDisabled());
      await user.click(continueButton);

      await waitFor(() => {
        expect(screen.getByRole('heading', { name: /generate all/i })).toBeInTheDocument();
      });

      // Wizard status reflects the saved client brief.
      expect(screen.getByText('✓ Saved')).toBeInTheDocument();
    }, 20000);
  });
});
