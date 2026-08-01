/**
 * Tests for the internal-ops Analytics page (GAP-UI-01) — real business summary.
 */
import { describe, it, expect, jest, beforeEach } from '@jest/globals';
import { screen, waitFor, fireEvent } from '@testing-library/react';
import { renderWithProviders } from '@/__tests__/setup/test-utils';
import Analytics from '../Analytics';
import { engagementApi } from '@/api/engagement';

jest.mock('@/api/engagement', () => ({
  engagementApi: { businessSummary: jest.fn() },
}));

const mockedSummary = engagementApi.businessSummary as jest.MockedFunction<
  typeof engagementApi.businessSummary
>;

describe('Analytics Page', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockedSummary.mockResolvedValue({
      days: 90,
      totals: { projects: 12, posts: 340, clients: 5 },
      monthly: [{ month: '2026-07', projects: 12, posts: 340 }],
      by_client: [{ client_name: 'Acme', projects: 8, posts: 240 }],
      by_template: [{ template_name: 'How-To', usage_count: 118 }],
    });
  });

  it('renders the header and range selector', async () => {
    renderWithProviders(<Analytics />);
    expect(screen.getByRole('heading', { name: 'Analytics' })).toBeInTheDocument();
    expect(screen.getByRole('combobox')).toBeInTheDocument();
  });

  it('renders real totals and breakdowns from the business summary', async () => {
    renderWithProviders(<Analytics />);

    // "340" (posts) and "12" (projects) appear in both the KPI card and the monthly row.
    await waitFor(() => expect(screen.getAllByText('340').length).toBeGreaterThan(0)); // posts
    expect(screen.getAllByText('12').length).toBeGreaterThan(0); // projects
    // Client + template breakdown rows come through.
    expect(screen.getByText('Acme')).toBeInTheDocument();
    expect(screen.getByText('How-To')).toBeInTheDocument();
    // No fabricated revenue/quality copy on the page.
    expect(screen.queryByText(/revenue/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/quality/i)).not.toBeInTheDocument();
  });

  it('exports the shown data as CSV', async () => {
    const createURL = jest.fn(() => 'blob:x');
    const revokeURL = jest.fn();
    // jsdom lacks URL.createObjectURL; stub it plus the anchor click.
    (URL as unknown as { createObjectURL: unknown }).createObjectURL = createURL;
    (URL as unknown as { revokeObjectURL: unknown }).revokeObjectURL = revokeURL;
    const clickSpy = jest.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});

    renderWithProviders(<Analytics />);
    const exportBtn = await screen.findByRole('button', { name: /export csv/i });
    await waitFor(() => expect(exportBtn).not.toBeDisabled());
    fireEvent.click(exportBtn);

    expect(createURL).toHaveBeenCalled();
    expect(clickSpy).toHaveBeenCalled();
    clickSpy.mockRestore();
  });
});
