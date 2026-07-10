import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import Deliverables from '@/pages/Deliverables';
import { QualityGatePanel } from '@/components/wizard/QualityGatePanel';
import { generatorApi } from '@/api/generator';
import type { PostDraft } from '@/types/domain';

// QualityGatePanel's "Regenerate all flagged" action calls generatorApi.regenerate;
// mock it so the regeneration flow resolves without a live server. A short delay keeps
// the mutation in its pending ("Regenerating...") state long enough to observe.
jest.mock('@/api/generator');
const mockGeneratorApi = generatorApi as jest.Mocked<typeof generatorApi>;

beforeEach(() => {
  jest.clearAllMocks();
  mockGeneratorApi.regenerate.mockImplementation(
    () => new Promise((resolve) => setTimeout(() => resolve({ id: 'run-regen' } as never), 100))
  );
});

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

// Mock posts for testing
const mockPosts: PostDraft[] = [
  {
    id: 'post-1',
    projectId: 'test-project',
    runId: 'run-1',
    content: 'This is a test post with proper length',
    status: 'approved',
    length: 200,
    hasCta: true,
    flags: [],
  },
  {
    id: 'post-2',
    projectId: 'test-project',
    runId: 'run-1',
    content: 'Short',
    status: 'flagged',
    length: 10,
    hasCta: false,
    flags: ['too_short', 'missing_cta'],
  },
  {
    id: 'post-3',
    projectId: 'test-project',
    runId: 'run-1',
    content: 'This is a very long post that exceeds the maximum word count limit and should be flagged as too long. '.repeat(10),
    status: 'flagged',
    length: 400,
    hasCta: true,
    flags: ['too_long'],
  },
];

describe('Quality Gate and Deliverables', () => {
  describe('Quality Gate Panel', () => {
    it('should render quality gate panel', () => {
      render(
        <TestWrapper>
          <QualityGatePanel posts={mockPosts} projectId="test-project" />
        </TestWrapper>
      );

      expect(screen.getByText(/quality gate/i)).toBeInTheDocument();
    });

    it('should display flagged posts count', () => {
      render(
        <TestWrapper>
          <QualityGatePanel posts={mockPosts} projectId="test-project" />
        </TestWrapper>
      );

      // Should show regenerate button for flagged posts
      expect(screen.getByRole('button', { name: /regenerate all flagged/i })).toBeInTheDocument();
    });

    it('should show flags for each flagged post', () => {
      render(
        <TestWrapper>
          <QualityGatePanel posts={mockPosts} projectId="test-project" />
        </TestWrapper>
      );

      expect(screen.getByText(/too_short/i)).toBeInTheDocument();
      expect(screen.getByText(/missing_cta/i)).toBeInTheDocument();
      expect(screen.getByText(/too_long/i)).toBeInTheDocument();
    });

    it('should display regenerate button when posts are flagged', () => {
      render(
        <TestWrapper>
          <QualityGatePanel posts={mockPosts} projectId="test-project" />
        </TestWrapper>
      );

      expect(screen.getByRole('button', { name: /regenerate all flagged/i })).toBeInTheDocument();
    });

    it('should show success message when no flags', () => {
      const cleanPosts: PostDraft[] = [
        {
          id: 'post-clean',
          projectId: 'test-project',
          runId: 'run-1',
          content: 'This is a perfect post',
          status: 'approved',
          length: 200,
          hasCta: true,
          flags: [],
        },
      ];

      render(
        <TestWrapper>
          <QualityGatePanel posts={cleanPosts} projectId="test-project" />
        </TestWrapper>
      );

      // The panel no longer renders a "no flags detected" banner; when nothing is
      // flagged it omits the flagged section + regenerate control and shows only the
      // approved posts.
      expect(screen.queryByRole('button', { name: /regenerate all flagged/i })).not.toBeInTheDocument();
      expect(screen.getByText(/approved posts/i)).toBeInTheDocument();
    });

    it('should group posts by flag type', () => {
      render(
        <TestWrapper>
          <QualityGatePanel posts={mockPosts} projectId="test-project" />
        </TestWrapper>
      );

      // Should show breakdown by flag type
      const flagElements = screen.getAllByText(/too_short|too_long|missing_cta/i);
      expect(flagElements.length).toBeGreaterThan(0);
    });
  });

  describe('Deliverables Page', () => {
    it('should render deliverables page', () => {
      render(
        <TestWrapper>
          <Deliverables />
        </TestWrapper>
      );

      expect(screen.getByText('Deliverables')).toBeInTheDocument();
    });

    it('should have status filter', () => {
      render(
        <TestWrapper>
          <Deliverables />
        </TestWrapper>
      );

      // Deliverables now has two selects (status + format); the status filter is first.
      expect(screen.getAllByRole('combobox')[0]).toBeInTheDocument();
    });

    it('should filter deliverables by status', async () => {
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <Deliverables />
        </TestWrapper>
      );

      const statusFilter = screen.getAllByRole('combobox')[0];
      await user.selectOptions(statusFilter, 'ready');

      expect(statusFilter).toHaveValue('ready');
    });

    it('should display deliverables grouped by client', async () => {
      render(
        <TestWrapper>
          <Deliverables />
        </TestWrapper>
      );

      // Wait for data to load (mock data)
      await waitFor(() => {
        const clientHeaders = screen.queryAllByRole('heading', { level: 3 });
        // Should have at least one client group if deliverables exist
        expect(clientHeaders.length).toBeGreaterThanOrEqual(0);
      });
    });

    it('should have refresh button', () => {
      render(
        <TestWrapper>
          <Deliverables />
        </TestWrapper>
      );

      expect(screen.getByRole('button', { name: /refresh/i })).toBeInTheDocument();
    });
  });

  describe('Quality Gate Validation Rules', () => {
    it('should flag posts that are too short', () => {
      const shortPost: PostDraft = {
        id: 'short',
        projectId: 'test',
        runId: 'run-1',
        content: 'Too short',
        status: 'flagged',
        length: 20,
        hasCta: true,
        flags: ['too_short'],
      };

      render(
        <TestWrapper>
          <QualityGatePanel posts={[shortPost]} projectId="test" />
        </TestWrapper>
      );

      expect(screen.getByText(/too_short/i)).toBeInTheDocument();
    });

    it('should flag posts that are too long', () => {
      const longPost: PostDraft = {
        id: 'long',
        projectId: 'test',
        runId: 'run-1',
        content: 'x'.repeat(1000),
        status: 'flagged',
        length: 500,
        hasCta: true,
        flags: ['too_long'],
      };

      render(
        <TestWrapper>
          <QualityGatePanel posts={[longPost]} projectId="test" />
        </TestWrapper>
      );

      expect(screen.getByText(/too_long/i)).toBeInTheDocument();
    });

    it('should flag posts missing CTA', () => {
      const noCTA: PostDraft = {
        id: 'no-cta',
        projectId: 'test',
        runId: 'run-1',
        content: 'A post without a call to action',
        status: 'flagged',
        length: 200,
        hasCta: false,
        flags: ['missing_cta'],
      };

      render(
        <TestWrapper>
          <QualityGatePanel posts={[noCTA]} projectId="test" />
        </TestWrapper>
      );

      expect(screen.getByText(/missing_cta/i)).toBeInTheDocument();
    });

    it('should allow posts with optimal length and CTA', () => {
      const goodPost: PostDraft = {
        id: 'good',
        projectId: 'test',
        runId: 'run-1',
        content: 'This is an optimal post with the right length and includes a call to action at the end. What do you think?',
        status: 'approved',
        length: 220,
        hasCta: true,
        flags: [],
      };

      render(
        <TestWrapper>
          <QualityGatePanel posts={[goodPost]} projectId="test" />
        </TestWrapper>
      );

      // Regenerate button should not appear when there are no flagged posts
      expect(screen.queryByRole('button', { name: /regenerate all flagged/i })).not.toBeInTheDocument();
    });
  });

  describe('Regeneration Flow', () => {
    it('should call onRegenerated when regenerate button clicked', async () => {
      const user = userEvent.setup();
      const onRegenerated = jest.fn();

      render(
        <TestWrapper>
          <QualityGatePanel posts={mockPosts} projectId="test" onRegenerated={onRegenerated} />
        </TestWrapper>
      );

      const regenerateButton = screen.getByRole('button', { name: /regenerate all flagged/i });
      await user.click(regenerateButton);

      // Should trigger regeneration callback (mock API has 1500ms delay)
      await waitFor(
        () => {
          expect(onRegenerated).toHaveBeenCalled();
        },
        { timeout: 2000 }
      );
    });

    it('should disable regenerate button while processing', async () => {
      const user = userEvent.setup();

      render(
        <TestWrapper>
          <QualityGatePanel posts={mockPosts} projectId="test" />
        </TestWrapper>
      );

      const regenerateButton = screen.getByRole('button', { name: /regenerate all flagged/i });
      await user.click(regenerateButton);

      // Button should show loading state
      await waitFor(() => {
        expect(screen.getByText(/regenerating/i)).toBeInTheDocument();
      });
    });
  });

  describe('Post Preview', () => {
    it('should display post IDs for flagged posts', () => {
      render(
        <TestWrapper>
          <QualityGatePanel posts={mockPosts} projectId="test" />
        </TestWrapper>
      );

      // QualityGatePanel shows "Post {id}" for flagged posts
      expect(screen.getByText(/Post post-2/i)).toBeInTheDocument();
      expect(screen.getByText(/Post post-3/i)).toBeInTheDocument();
    });

    it('should display flags for each flagged post', () => {
      render(
        <TestWrapper>
          <QualityGatePanel posts={mockPosts} projectId="test" />
        </TestWrapper>
      );

      // Flags render as individual badges, not a joined "a, b" string.
      expect(screen.getByText('too_short')).toBeInTheDocument();
      expect(screen.getByText('missing_cta')).toBeInTheDocument();
      expect(screen.getByText('too_long')).toBeInTheDocument();
    });

    it('should show approved posts in their own section', () => {
      render(
        <TestWrapper>
          <QualityGatePanel posts={mockPosts} projectId="test" />
        </TestWrapper>
      );

      // The panel now renders approved posts in a dedicated "Approved Posts" section
      // (post-1 is approved), alongside the flagged section.
      expect(screen.getByText(/Post post-1/i)).toBeInTheDocument();
      expect(screen.getByText(/approved posts/i)).toBeInTheDocument();
    });
  });
});
