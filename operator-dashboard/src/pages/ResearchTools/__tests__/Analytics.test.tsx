/**
 * Regression tests for Bug #187 (part 1): the Research Analytics page crashed
 * with "TypeError: reading '.length' of undefined" when the analytics response
 * omitted `topTools`. Every other field used `?? 0` null-safety, but
 * `analytics.topTools.length` / `.map` were unguarded.
 */
import { describe, it, expect, jest, beforeEach, beforeAll, afterAll } from '@jest/globals';
import { renderWithProviders, screen } from '@/__tests__/setup/test-utils';
import type { ResearchAnalytics } from '@/api';

jest.mock('@/api', () => ({
  researchApi: { getAnalytics: jest.fn() },
}));

// Imported after the mock so we get the mocked instance.
import { researchApi } from '@/api';
import ResearchAnalyticsPage from '../Analytics';

const mockGetAnalytics = researchApi.getAnalytics as jest.MockedFunction<
  typeof researchApi.getAnalytics
>;

const baseAnalytics = {
  totalRevenue: 100,
  totalApiCost: 10,
  profitMargin: 90,
  totalExecutions: 5,
  cacheHitRate: 50,
  cacheSavings: 5,
  avgCostPerTool: 2,
  dateRange: 90,
};

describe('ResearchTools/Analytics — Bug #187 regression', () => {
  // The boundary/React log an error when a component would throw; keep output clean.
  let errSpy: ReturnType<typeof jest.spyOn>;
  beforeAll(() => {
    errSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
  });
  afterAll(() => {
    errSpy.mockRestore();
  });
  beforeEach(() => {
    mockGetAnalytics.mockReset();
  });

  it('renders without crashing when topTools is missing from the response', async () => {
    // Intentionally omit topTools to reproduce the pre-fix crash.
    mockGetAnalytics.mockResolvedValue(baseAnalytics as unknown as ResearchAnalytics);

    renderWithProviders(<ResearchAnalyticsPage />);

    expect(await screen.findByText('Research Analytics')).toBeInTheDocument();
    // The tools card should fall back to its empty state rather than throwing.
    expect(
      await screen.findByText('No tool executions in this time period')
    ).toBeInTheDocument();
  });

  it('renders the tool list when topTools is present', async () => {
    mockGetAnalytics.mockResolvedValue({
      ...baseAnalytics,
      topTools: [
        {
          toolName: 'seo',
          toolLabel: 'SEO Keyword Research',
          executionCount: 2,
          totalRevenue: 60,
          totalApiCost: 4,
        },
      ],
    } as ResearchAnalytics);

    renderWithProviders(<ResearchAnalyticsPage />);

    expect(await screen.findByText('SEO Keyword Research')).toBeInTheDocument();
  });
});
