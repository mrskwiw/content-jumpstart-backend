/**
 * ProjectCostSummary Component Tests
 *
 * Tests for the project-level cost summary widget.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ProjectCostSummary } from '@/components/costs/ProjectCostSummary';
import { costsApi } from '@/api/costs';

vi.mock('@/api/costs', () => ({
  costsApi: {
    getProjectCosts: vi.fn(),
  },
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('ProjectCostSummary', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Loading State', () => {
    it('renders loading skeleton while fetching data', () => {
      vi.mocked(costsApi.getProjectCosts).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );

      const { container } = render(
        <ProjectCostSummary projectId="proj_123" />,
        { wrapper: createWrapper() }
      );

      const skeleton = container.querySelector('.animate-pulse');
      expect(skeleton).toBeInTheDocument();
    });
  });

  describe('Error State', () => {
    it('renders error message when API call fails', async () => {
      vi.mocked(costsApi.getProjectCosts).mockRejectedValue(
        new Error('Failed to fetch costs')
      );

      render(
        <ProjectCostSummary projectId="proj_123" />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(screen.getByText('Cost data not available')).toBeInTheDocument();
      });
    });

    it('renders error message when no cost data returned', async () => {
      vi.mocked(costsApi.getProjectCosts).mockResolvedValue(null as any);

      render(
        <ProjectCostSummary projectId="proj_123" />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(screen.getByText('Cost data not available')).toBeInTheDocument();
      });
    });
  });

  describe('Success State', () => {
    const mockCostData = {
      projectId: 'proj_123',
      projectName: 'Test Project',
      totalRuns: 5,
      totalPosts: 30,
      totalInputTokens: 50000,
      totalOutputTokens: 30000,
      totalCacheCreationTokens: 10000,
      totalCacheReadTokens: 20000,
      totalGenerationCostUsd: 1.25,
      totalResearchTools: 3,
      totalResearchCostUsd: 0.50,
      totalCostUsd: 1.75,
      costPerPost: 0.0583,
    };

    beforeEach(() => {
      vi.mocked(costsApi.getProjectCosts).mockResolvedValue(mockCostData);
    });

    it('renders total cost prominently', async () => {
      render(
        <ProjectCostSummary projectId="proj_123" />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(screen.getByText('$1.75')).toBeInTheDocument();
      });
    });

    it('renders generation cost breakdown', async () => {
      render(
        <ProjectCostSummary projectId="proj_123" />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(screen.getByText('Generation')).toBeInTheDocument();
        expect(screen.getByText('$1.25')).toBeInTheDocument();
        expect(screen.getByText(/30 posts.*5 runs/)).toBeInTheDocument();
      });
    });

    it('renders research cost breakdown', async () => {
      render(
        <ProjectCostSummary projectId="proj_123" />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(screen.getByText('Research')).toBeInTheDocument();
        expect(screen.getByText('$0.50')).toBeInTheDocument();
        expect(screen.getByText(/3 tools executed/)).toBeInTheDocument();
      });
    });

    it('renders cost per post', async () => {
      render(
        <ProjectCostSummary projectId="proj_123" />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(screen.getByText('Per Post')).toBeInTheDocument();
        expect(screen.getByText('$0.0583')).toBeInTheDocument();
        expect(screen.getByText('Average cost per post')).toBeInTheDocument();
      });
    });

    it('renders N/A for cost per post when null', async () => {
      vi.mocked(costsApi.getProjectCosts).mockResolvedValue({
        ...mockCostData,
        costPerPost: null,
      });

      render(
        <ProjectCostSummary projectId="proj_123" />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(screen.getByText('N/A')).toBeInTheDocument();
      });
    });

    it('renders total tokens formatted', async () => {
      render(
        <ProjectCostSummary projectId="proj_123" />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(screen.getByText('Total Tokens')).toBeInTheDocument();
        // 50K + 30K = 80K tokens (formatted as 80K or 0.08M depending on threshold)
        expect(screen.getByText(/80/)).toBeInTheDocument();
      });
    });

    it('formats large token counts with M suffix', async () => {
      vi.mocked(costsApi.getProjectCosts).mockResolvedValue({
        ...mockCostData,
        totalInputTokens: 2_000_000,
        totalOutputTokens: 1_000_000,
      });

      render(
        <ProjectCostSummary projectId="proj_123" />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(screen.getByText(/3\.00M/)).toBeInTheDocument();
      });
    });

    it('formats medium token counts with K suffix', async () => {
      vi.mocked(costsApi.getProjectCosts).mockResolvedValue({
        ...mockCostData,
        totalInputTokens: 50_000,
        totalOutputTokens: 30_000,
      });

      render(
        <ProjectCostSummary projectId="proj_123" />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(screen.getByText(/80\.0K/)).toBeInTheDocument();
      });
    });

    it('renders cache usage with percentage', async () => {
      render(
        <ProjectCostSummary projectId="proj_123" />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(screen.getByText('Cache Usage')).toBeInTheDocument();
        expect(screen.getByText(/20\.0K/)).toBeInTheDocument();
        // Cache ratio: 20000 / (50000 + 30000) = 25%
        expect(screen.getByText(/\(25\.0%\)/)).toBeInTheDocument();
      });
    });

    it('handles zero cache reads gracefully', async () => {
      vi.mocked(costsApi.getProjectCosts).mockResolvedValue({
        ...mockCostData,
        totalCacheReadTokens: 0,
      });

      render(
        <ProjectCostSummary projectId="proj_123" />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(screen.getByText(/\(0\.0%\)/)).toBeInTheDocument();
      });
    });

    it('renders input and output token breakdowns', async () => {
      render(
        <ProjectCostSummary projectId="proj_123" />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(screen.getByText('Input Tokens')).toBeInTheDocument();
        expect(screen.getByText('Output Tokens')).toBeInTheDocument();
        expect(screen.getByText(/50\.0K/)).toBeInTheDocument();
        expect(screen.getByText(/30\.0K/)).toBeInTheDocument();
      });
    });
  });

  describe('Cost Formatting', () => {
    it('formats costs >= $1 with 2 decimals', async () => {
      vi.mocked(costsApi.getProjectCosts).mockResolvedValue({
        projectId: 'proj_123',
        projectName: 'Test Project',
        totalRuns: 1,
        totalPosts: 30,
        totalInputTokens: 0,
        totalOutputTokens: 0,
        totalCacheCreationTokens: 0,
        totalCacheReadTokens: 0,
        totalGenerationCostUsd: 5.00,
        totalResearchTools: 0,
        totalResearchCostUsd: 0,
        totalCostUsd: 5.50,
        costPerPost: 0.18,
      });

      render(
        <ProjectCostSummary projectId="proj_123" />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(screen.getByText('$5.50')).toBeInTheDocument();
        expect(screen.getByText('$5.00')).toBeInTheDocument();
      });
    });

    it('formats costs < $1 with 4 decimals', async () => {
      vi.mocked(costsApi.getProjectCosts).mockResolvedValue({
        projectId: 'proj_123',
        projectName: 'Test Project',
        totalRuns: 1,
        totalPosts: 30,
        totalInputTokens: 0,
        totalOutputTokens: 0,
        totalCacheCreationTokens: 0,
        totalCacheReadTokens: 0,
        totalGenerationCostUsd: 0.1234,
        totalResearchTools: 0,
        totalResearchCostUsd: 0.0567,
        totalCostUsd: 0.1801,
        costPerPost: 0.0060,
      });

      render(
        <ProjectCostSummary projectId="proj_123" />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(screen.getByText('$0.1801')).toBeInTheDocument();
        expect(screen.getByText('$0.1234')).toBeInTheDocument();
        expect(screen.getByText('$0.0567')).toBeInTheDocument();
        expect(screen.getByText('$0.0060')).toBeInTheDocument();
      });
    });
  });
});
