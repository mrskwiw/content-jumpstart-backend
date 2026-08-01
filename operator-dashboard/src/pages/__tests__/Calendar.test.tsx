/**
 * Smoke + data tests for Calendar page.
 */
import { describe, it, expect, jest, beforeEach } from '@jest/globals';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import { renderWithProviders } from '@/__tests__/setup/test-utils';
import Calendar from '../Calendar';
import { distributionApi } from '@/api/distribution';

jest.mock('@/api/distribution', () => ({
  distributionApi: { queue: jest.fn() },
}));

const mockedQueue = distributionApi.queue as jest.MockedFunction<typeof distributionApi.queue>;

describe('Calendar Page', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockedQueue.mockResolvedValue([]);
  });

  it('should render without crashing', () => {
    const { container } = renderWithProviders(<Calendar />);
    expect(container).toBeInTheDocument();
  });

  it('should render calendar header', () => {
    const { container } = renderWithProviders(<Calendar />);
    expect(container).toHaveTextContent('Calendar');
  });

  it('should render calendar grid or view', () => {
    const { container } = renderWithProviders(<Calendar />);
    const elements = container.querySelectorAll('[class*="grid"], [class*="flex"]');
    expect(elements.length).toBeGreaterThan(0);
  });

  it('should render navigation controls', () => {
    const { container } = renderWithProviders(<Calendar />);
    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('shows pending + retryable-failed posts (flagged) but hides terminal posted rows', async () => {
    mockedQueue.mockResolvedValue([
      {
        id: 'sp1',
        platform: 'linkedin',
        content: 'Launch announcement for the new feature',
        status: 'pending',
        scheduled_for: '2026-02-10T14:30:00Z',
        posted_at: null,
        platform_url: null,
        error_message: null,
        retry_count: 0,
      },
      {
        id: 'sp2',
        platform: 'twitter',
        content: 'Already published thread',
        status: 'posted',
        scheduled_for: '2026-02-11T09:00:00Z',
        posted_at: '2026-02-11T09:00:05Z',
        platform_url: 'https://x.com/x/1',
        error_message: null,
        retry_count: 0,
      },
      {
        id: 'sp3',
        platform: 'facebook',
        content: 'Post that hit an outage',
        status: 'failed',
        scheduled_for: '2026-02-12T12:00:00Z',
        posted_at: null,
        platform_url: null,
        error_message: 'rate limited',
        retry_count: 1,
      },
    ]);

    renderWithProviders(<Calendar />);

    // List view shows every (non-terminal) event regardless of the visible month.
    fireEvent.click(screen.getByText('List View'));

    // The pending post appears…
    await waitFor(() => expect(screen.getByText('Linkedin post')).toBeInTheDocument());
    expect(screen.getByText(/launch announcement/i)).toBeInTheDocument();
    // …the failed post stays visible (still retrying) and is flagged distinctly…
    expect(screen.getByText('Facebook post')).toBeInTheDocument();
    expect(screen.getByText(/failed — retrying/i)).toBeInTheDocument();
    // …but the already-posted row is NOT shown as an upcoming schedule entry.
    expect(screen.queryByText('Twitter post')).not.toBeInTheDocument();
    expect(screen.queryByText(/already published/i)).not.toBeInTheDocument();
    expect(mockedQueue).toHaveBeenCalled();
  });
});
