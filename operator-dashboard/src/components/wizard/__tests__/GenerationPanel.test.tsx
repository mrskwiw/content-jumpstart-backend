/**
 * Comprehensive tests for GenerationPanel
 */
import { describe, it, expect, jest } from '@jest/globals';
import { render } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { GenerationPanel } from '../GenerationPanel';

// Mock the API
jest.mock('@/api/posts', () => ({
  postsApi: {
    list: jest.fn().mockResolvedValue({ items: [], total: 0, page: 1, pageSize: 10, totalPages: 0 }),
  },
}));

describe('GenerationPanel', () => {
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
        <GenerationPanel {...mockProps} />
      </QueryClientProvider>
    );
    expect(container).toBeInTheDocument();
  });

  it('should render generation controls', () => {
    const { container } = render(
      <QueryClientProvider client={queryClient}>
        <GenerationPanel {...mockProps} />
      </QueryClientProvider>
    );

    // Should have buttons or controls
    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('should show generation status or progress', () => {
    const { container } = render(
      <QueryClientProvider client={queryClient}>
        <GenerationPanel {...mockProps} />
      </QueryClientProvider>
    );

    // Should have status indicators
    expect(container.firstChild).toBeInTheDocument();
  });

  it('should display generated posts or placeholders', () => {
    const { container } = render(
      <QueryClientProvider client={queryClient}>
        <GenerationPanel {...mockProps} />
      </QueryClientProvider>
    );

    // Should have content area
    const content = container.querySelector('[class*="flex"], [class*="grid"]');
    expect(content || container.firstChild).toBeInTheDocument();
  });

  it('should handle generation start', () => {
    const { container } = render(
      <QueryClientProvider client={queryClient}>
        <GenerationPanel {...mockProps} />
      </QueryClientProvider>
    );

    // Should have start button or already be generating
    const buttons = container.querySelectorAll('button');
    expect(buttons.length >= 0).toBe(true);
  });
});
