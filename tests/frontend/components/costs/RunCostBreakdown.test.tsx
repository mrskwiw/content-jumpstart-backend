/**
 * RunCostBreakdown Component Tests
 *
 * Tests for the run-level detailed cost breakdown component.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tantml:function_calls>
import { RunCostBreakdown } from '@/components/costs/RunCostBreakdown';
import { costsApi } from '@/api/costs';

vi.mock('@/api/costs', () => ({
  costsApi: {
    getRunCosts: vi.fn(),
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

describe('RunCostBreakdown', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Loading State', () => {
    it('renders loading skeleton while fetching data', () => {
      vi.mocked(costsApi.getRunCosts).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );

      const { container } = render(
        <RunCostBreakdown runId="run_123" />,
        { wrapper: createWrapper() }
      );

      const skeleton = container.querySelector('.animate-pulse');
      expect(skeleton).toBeInTheDocument();
    });
  });

  describe('Success State', () => {
    const mockRunCosts = {
      runId: 'run_123',
      projectId: 'proj_456',
      status: 'succeeded',
      startedAt: '2026-03-09T10:00:00Z',
      completedAt: '2026-03-09T10:02:00Z',
      totalInputTokens: 45000,
      totalOutputTokens: 25000,
      totalCacheCreationTokens: 5000,
      totalCacheReadTokens: 15000,
      totalCostUsd: 1.50,
      estimatedCostUsd: null,
      totalPosts: 30,
      postsWithTokenData: 28,
      avgCostPerPost: 0.05,
      cacheSavingsUsd: 0.0405,
    };

    beforeEach(() => {
      vi.mocked(costsApi.getRunCosts).mockResolvedValue(mockRunCosts);
    });

    it('renders status with correct icon and label', async () => {
      render(
        <RunCostBreakdown runId="run_123" />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(screen.getByText('succeeded')).toBeInTheDocument();
      });

      // Check for CheckCircle2 icon (succeeded status)
      const statusSection = screen.getByText('succeeded').closest('div');
      expect(statusSection).toBeInTheDocument();
    });

    it('calculates and displays run duration', async () => {
      render(
        <RunCostBreakdown runId="run_123" />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        // 2 minutes = 120 seconds
        expect(screen.getByText('120s duration')).toBeInTheDocument();
      });
    });

    it('does not display duration when run is not completed', async () => {
      vi.mocked(costsApi.getRunCosts).mockResolvedValue({
        ...mockRunCosts,
        completedAt: null,
        status: 'running',
      });

      render(
        <RunCostBreakdown runId="run_123" />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(screen.queryByText(/duration/)).not.toBeInTheDocument();
      });
    });

    it('renders total cost prominently', async () => {
      render(
        <RunCostBreakdown runId="run_123" />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(screen.getByText('$1.50')).toBeInTheDocument();
      });
    });

    it('renders estimated cost when actual cost not available', async () => {
      vi.mocked(costsApi.getRunCosts).mockResolvedValue({
        ...mockRunCosts,
        totalCostUsd: 0,
        estimatedCostUsd: 1.45,
      });

      render(
        <RunCostBreakdown runId="run_123" />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(screen.getByText(/est\. \$1\.45/i)).toBeInTheDocument();
      });
    });

    it('renders token breakdown with all token types', async () => {
      render(
        <RunCostBreakdown runId="run_123" />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(screen.getByText('Token Usage')).toBeInTheDocument();
        expect(screen.getByText('Input Tokens')).toBeInTheDocument();
        expect(screen.getByText('45,000')).toBeInTheDocument();
        expect(screen.getByText('Output Tokens')).toBeInTheDocument();
        expect(screen.getByText('25,000')).toBeInTheDocument();
      });
    });

    it('calculates and displays per-token costs', async () => {
      render(
        <RunCostBreakdown runId="run_123" />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        // Input cost: (45000 / 1M) * 3.0 = $0.135
        expect(screen.getByText(/~\$0\.1350/)).toBeInTheDocument();
        // Output cost: (25000 / 1M) * 15.0 = $0.375
        expect(screen.getByText(/~\$0\.3750/)).toBeInTheDocument();
      });
    });

    it('renders cache sections when cache tokens present', async () => {
      render(
        <RunCostBreakdown runId="run_123" />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(screen.getByText('Cache Created')).toBeInTheDocument();
        expect(screen.getByText('5,000')).toBeInTheDocument();
        expect(screen.getByText('Cache Read')).toBeInTheDocument();
        expect(screen.getByText('15,000')).toBeInTheDocument();
      });
    });

    it('does not render cache sections when no cache tokens', async () => {
      vi.mocked(costsApi.getRunCosts).mockResolvedValue({
        ...mockRunCosts,
        totalCacheReadTokens: 0,
        totalCacheCreationTokens: 0,
        cacheSavingsUsd: null,
      });

      render(
        <RunCostBreakdown runId="run_123" />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(screen.queryByText('Cache Created')).not.toBeInTheDocument();
        expect(screen.queryByText('Cache Read')).not.toBeInTheDocument();
      });
    });

    it('renders cache savings with percentage', async () => {
      render(
        <RunCostBreakdown runId="run_123" />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(screen.getByText('Cache Savings')).toBeInTheDocument();
        expect(screen.getByText('$0.0405')).toBeInTheDocument();
        // Cache % = (15000 / (45000 + 25000)) * 100 = 21.4%
        expect(screen.getByText(/21\.4%/)).toBeInTheDocument();
        expect(screen.getByText(/10x cost reduction/)).toBeInTheDocument();
      });
    });

    it('does not render cache savings when savings is zero or null', async () => {
      vi.mocked(costsApi.getRunCosts).mockResolvedValue({
        ...mockRunCosts,
        cacheSavingsUsd: null,
        totalCacheReadTokens: 0,
      });

      render(
        <RunCostBreakdown runId="run_123" />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(screen.queryByText('Cache Savings')).not.toBeInTheDocument();
      });
    });

    it('renders post statistics', async () => {
      render(
        <RunCostBreakdown runId="run_123" />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(screen.getByText('Post Statistics')).toBeInTheDocument();
        expect(screen.getByText('Total Posts')).toBeInTheDocument();
        expect(screen.getByText('30')).toBeInTheDocument();
        expect(screen.getByText('With Token Data')).toBeInTheDocument();
        expect(screen.getByText('28')).toBeInTheDocument();
        expect(screen.getByText('Avg Cost/Post')).toBeInTheDocument();
        expect(screen.getByText('$0.0500')).toBeInTheDocument();
      });
    });

    it('renders N/A for average cost per post when null', async () => {
      vi.mocked(costsApi.getRunCosts).mockResolvedValue({
        ...mockRunCosts,
        avgCostPerPost: null,
      });

      render(
        <RunCostBreakdown runId="run_123" />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(screen.getByText('N/A')).toBeInTheDocument();
      });
    });
  });

  describe('Status Icons and Colors', () => {
    const baseRunCosts = {
      runId: 'run_123',
      projectId: 'proj_456',
      startedAt: '2026-03-09T10:00:00Z',
      completedAt: '2026-03-09T10:02:00Z',
      totalInputTokens: 1000,
      totalOutputTokens: 500,
      totalCacheCreationTokens: 0,
      totalCacheReadTokens: 0,
      totalCostUsd: 0.05,
      estimatedCostUsd: null,
      totalPosts: 5,
      postsWithTokenData: 5,
      avgCostPerPost: 0.01,
      cacheSavingsUsd: null,
    };

    it('renders succeeded status with emerald color', async () => {
      vi.mocked(costsApi.getRunCosts).mockResolvedValue({
        ...baseRunCosts,
        status: 'succeeded',
      });

      const { container } = render(
        <RunCostBreakdown runId="run_123" />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(screen.getByText('succeeded')).toBeInTheDocument();
      });
    });

    it('renders failed status with red color', async () => {
      vi.mocked(costsApi.getRunCosts).mockResolvedValue({
        ...baseRunCosts,
        status: 'failed',
      });

      const { container } = render(
        <RunCostBreakdown runId="run_123" />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(screen.getByText('failed')).toBeInTheDocument();
      });
    });

    it('renders running status with blue animated spinner', async () => {
      vi.mocked(costsApi.getRunCosts).mockResolvedValue({
        ...baseRunCosts,
        status: 'running',
        completedAt: null,
      });

      const { container } = render(
        <RunCostBreakdown runId="run_123" />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(screen.getByText('running')).toBeInTheDocument();
      });

      const spinner = container.querySelector('.animate-spin');
      expect(spinner).toBeInTheDocument();
    });

    it('renders pending status with gray color', async () => {
      vi.mocked(costsApi.getRunCosts).mockResolvedValue({
        ...baseRunCosts,
        status: 'pending',
        completedAt: null,
      });

      render(
        <RunCostBreakdown runId="run_123" />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(screen.getByText('pending')).toBeInTheDocument();
      });
    });
  });

  describe('Cost Formatting', () => {
    const baseRunCosts = {
      runId: 'run_123',
      projectId: 'proj_456',
      status: 'succeeded',
      startedAt: '2026-03-09T10:00:00Z',
      completedAt: '2026-03-09T10:02:00Z',
      totalInputTokens: 1000,
      totalOutputTokens: 500,
      totalCacheCreationTokens: 0,
      totalCacheReadTokens: 0,
      estimatedCostUsd: null,
      totalPosts: 5,
      postsWithTokenData: 5,
      avgCostPerPost: null,
      cacheSavingsUsd: null,
    };

    it('formats costs >= $1 with 2 decimals', async () => {
      vi.mocked(costsApi.getRunCosts).mockResolvedValue({
        ...baseRunCosts,
        totalCostUsd: 5.50,
        avgCostPerPost: 1.10,
      });

      render(
        <RunCostBreakdown runId="run_123" />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(screen.getByText('$5.50')).toBeInTheDocument();
        expect(screen.getByText('$1.10')).toBeInTheDocument();
      });
    });

    it('formats costs < $1 with 4 decimals', async () => {
      vi.mocked(costsApi.getRunCosts).mockResolvedValue({
        ...baseRunCosts,
        totalCostUsd: 0.1234,
        avgCostPerPost: 0.0247,
      });

      render(
        <RunCostBreakdown runId="run_123" />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(screen.getByText('$0.1234')).toBeInTheDocument();
        expect(screen.getByText('$0.0247')).toBeInTheDocument();
      });
    });
  });
});
