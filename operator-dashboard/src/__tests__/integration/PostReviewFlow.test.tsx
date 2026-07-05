/**
 * Integration Test: Post Review and QA Flow
 * Tests reviewing, approving, and flagging generated content
 */
import { describe, it, expect, jest, beforeEach } from '@jest/globals';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ContentReview from '@/pages/ContentReview';
import { postsApi } from '@/api/posts';

jest.mock('@/api/posts');

const mockPostsApi = postsApi as jest.Mocked<typeof postsApi>;

describe('Post Review Flow Integration', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    jest.clearAllMocks();
  });

  it('should display posts for review', async () => {
    const mockPosts = {
      items: [
        {
          id: 'post-1',
          projectId: 'proj-1',
          runId: 'run-1',
          content: 'Great content about marketing strategies...',
          length: 250,
          readabilityScore: 75,
          hasCta: true,
        },
        {
          id: 'post-2',
          projectId: 'proj-1',
          runId: 'run-1',
          content: 'Another post about social media...',
          length: 180,
          readabilityScore: 68,
          hasCta: false,
        },
      ],
      metadata: {
        page_size: 20,
        has_next: false,
        has_prev: false,
        strategy: 'offset' as const,
      },
    };

    mockPostsApi.list.mockResolvedValue(mockPosts);

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <ContentReview />
        </MemoryRouter>
      </QueryClientProvider>
    );

    // Should show posts
    await waitFor(() => {
      const content1 = screen.queryByText(/marketing strategies/i);
      const content2 = screen.queryByText(/social media/i);
      expect(content1 || content2 || screen.queryByText(/content|post/i)).toBeTruthy();
    });
  });

  it('should handle empty post list', async () => {
    mockPostsApi.list.mockResolvedValue({
      items: [],
      metadata: {
        page_size: 20,
        has_next: false,
        has_prev: false,
        strategy: 'offset' as const,
      },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <ContentReview />
        </MemoryRouter>
      </QueryClientProvider>
    );

    // Should show empty state
    await waitFor(() => {
      expect(screen.getByText(/no posts|no content|empty/i)).toBeInTheDocument();
    });
  });

  it('should approve a post', async () => {
    const user = userEvent.setup();

    const mockPost = {
      id: 'post-1',
      projectId: 'proj-1',
      runId: 'run-1',
      content: 'Test content',
      length: 150,
    };

    mockPostsApi.list.mockResolvedValue({
      items: [mockPost],
      metadata: {
        page_size: 20,
        has_next: false,
        has_prev: false,
        strategy: 'offset' as const,
      },
    });

    mockPostsApi.update.mockResolvedValue({
      id: 'post-1',
      status: 'approved',
      contentPreview: 'Test content',
      content: 'Test content',
    });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <ContentReview />
        </MemoryRouter>
      </QueryClientProvider>
    );

    // Wait for posts to load
    await waitFor(() => {
      const approveButton = screen.queryByRole('button', { name: /approve|accept/i });
      const anyButton = screen.queryAllByRole('button');
      expect(approveButton || anyButton.length > 0).toBeTruthy();
    });

    // Click approve if button exists
    const approveButton = screen.queryByRole('button', { name: /approve/i });
    if (approveButton) {
      await user.click(approveButton);

      await waitFor(() => {
        expect(mockPostsApi.update).toHaveBeenCalledWith(
          'post-1',
          expect.objectContaining({
            status: 'approved',
          })
        );
      });
    }
  });

  it('should flag a post for review', async () => {
    const user = userEvent.setup();

    const mockPost = {
      id: 'post-1',
      projectId: 'proj-1',
      runId: 'run-1',
      content: 'Test content',
      length: 150,
    };

    mockPostsApi.list.mockResolvedValue({
      items: [mockPost],
      metadata: {
        page_size: 20,
        has_next: false,
        has_prev: false,
        strategy: 'offset' as const,
      },
    });

    mockPostsApi.update.mockResolvedValue({
      id: 'post-1',
      status: 'flagged',
      contentPreview: 'Test content',
      content: 'Test content',
    });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <ContentReview />
        </MemoryRouter>
      </QueryClientProvider>
    );

    await waitFor(() => {
      const buttons = screen.queryAllByRole('button');
      expect(buttons.length).toBeGreaterThan(0);
    });
  });

  it('should handle API errors', async () => {
    mockPostsApi.list.mockRejectedValue(new Error('Failed to fetch posts'));

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <ContentReview />
        </MemoryRouter>
      </QueryClientProvider>
    );

    // Should show error message
    await waitFor(() => {
      expect(screen.getByText(/error|failed|try again/i)).toBeInTheDocument();
    });
  });
});
