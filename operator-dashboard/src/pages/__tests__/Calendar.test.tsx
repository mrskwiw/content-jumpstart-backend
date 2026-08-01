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

  it('renders scheduled distribution posts from the queue as calendar events', async () => {
    mockedQueue.mockResolvedValue([
      {
        id: 'sp1',
        platform: 'linkedin',
        content: 'Launch announcement for the new feature',
        status: 'scheduled',
        scheduled_for: '2026-02-10T14:30:00Z',
        posted_at: null,
        platform_url: null,
        error_message: null,
        retry_count: 0,
      },
    ]);

    renderWithProviders(<Calendar />);

    // List view shows every event regardless of the visible month.
    fireEvent.click(screen.getByText('List View'));

    await waitFor(() => expect(screen.getByText('Linkedin post')).toBeInTheDocument());
    // The content excerpt is carried through as the event description.
    expect(screen.getByText(/launch announcement/i)).toBeInTheDocument();
    expect(mockedQueue).toHaveBeenCalled();
  });
});
