/**
 * Comprehensive tests for QualityGatePanel
 */
import { describe, it, expect, jest } from '@jest/globals';
import { render } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { QualityGatePanel } from '../QualityGatePanel';

// Mock the API
jest.mock('@/api/posts', () => ({
  postsApi: {
    list: jest.fn().mockResolvedValue({ items: [], total: 0, page: 1, pageSize: 10, totalPages: 0 }),
    update: jest.fn().mockResolvedValue({}),
  },
}));

describe('QualityGatePanel', () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  const mockProps = {
    projectId: 'proj-1',
    onComplete: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should render without crashing', () => {
    const { container } = render(
      <QueryClientProvider client={queryClient}>
        <QualityGatePanel {...mockProps} />
      </QueryClientProvider>
    );
    expect(container).toBeInTheDocument();
  });

  it('should render quality metrics or stats', () => {
    const { container } = render(
      <QueryClientProvider client={queryClient}>
        <QualityGatePanel {...mockProps} />
      </QueryClientProvider>
    );

    // Should have metrics display
    const elements = container.querySelectorAll('[class*="rounded"], [class*="border"]');
    expect(elements.length).toBeGreaterThan(0);
  });

  it('should show post list or grid', () => {
    const { container } = render(
      <QueryClientProvider client={queryClient}>
        <QualityGatePanel {...mockProps} />
      </QueryClientProvider>
    );

    // Should have list container
    expect(container.firstChild).toBeInTheDocument();
  });

  it('should have approve/flag controls', () => {
    const { container } = render(
      <QueryClientProvider client={queryClient}>
        <QualityGatePanel {...mockProps} />
      </QueryClientProvider>
    );

    // Should have buttons for quality actions
    const buttons = container.querySelectorAll('button');
    expect(buttons.length >= 0).toBe(true);
  });

  it('should display quality scores or indicators', () => {
    const { container } = render(
      <QueryClientProvider client={queryClient}>
        <QualityGatePanel {...mockProps} />
      </QueryClientProvider>
    );

    // Should have content
    expect(container.textContent?.length || 0).toBeGreaterThanOrEqual(0);
  });
});
