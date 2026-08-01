import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import PostReviewPanel from '@/components/review/PostReviewPanel';
import { reviewApi } from '@/api/review';
import { teamsApi } from '@/api/teams';
import { renderWithProviders } from '@/test-utils';
import '@testing-library/jest-dom';

jest.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ user: { id: 'u-admin', email: 'admin@example.com' } }),
}));

jest.mock('@/api/review', () => ({
  reviewApi: {
    getApproval: jest.fn(),
    listComments: jest.fn(),
    submitForApproval: jest.fn(),
    approve: jest.fn(),
    reject: jest.fn(),
    addComment: jest.fn(),
    deleteComment: jest.fn(),
  },
}));

jest.mock('@/api/teams', () => ({
  teamsApi: { getMyTeam: jest.fn() },
}));

const mockedReview = reviewApi as jest.Mocked<typeof reviewApi>;
const mockedTeams = teamsApi as jest.Mocked<typeof teamsApi>;

beforeEach(() => {
  jest.clearAllMocks();
  mockedTeams.getMyTeam.mockResolvedValue({
    team: { team_id: 't1', name: 'Acme', my_role: 'admin', members: [] },
  });
});

describe('PostReviewPanel', () => {
  it('shows Approve/Request-changes to a manager on a pending post', async () => {
    mockedReview.getApproval.mockResolvedValue({
      post_id: 'p1',
      status: 'pending',
      submitted_by_user_id: 'u-ed',
      decided_by_user_id: null,
      decided_at: null,
      note: null,
    });
    mockedReview.listComments.mockResolvedValue([
      {
        id: 'c1',
        post_id: 'p1',
        author_user_id: 'u-ed',
        author_email: 'ed@example.com',
        body: 'Tighten the hook',
        created_at: '2026-08-01T00:00:00Z',
      },
    ]);

    const { wrapper } = renderWithProviders();
    render(<PostReviewPanel postId="p1" />, { wrapper });

    await waitFor(() => expect(screen.getByText('Pending review')).toBeInTheDocument());
    expect(screen.getByRole('button', { name: /approve/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /request changes/i })).toBeInTheDocument();
    expect(screen.getByText('Tighten the hook')).toBeInTheDocument();
  });

  it('submits a not-yet-submitted post for review', async () => {
    mockedReview.getApproval.mockResolvedValue(null);
    mockedReview.listComments.mockResolvedValue([]);
    mockedReview.submitForApproval.mockResolvedValue({
      post_id: 'p1',
      status: 'pending',
      submitted_by_user_id: 'u-admin',
      decided_by_user_id: null,
      decided_at: null,
      note: null,
    });

    const { wrapper } = renderWithProviders();
    render(<PostReviewPanel postId="p1" />, { wrapper });

    const submitBtn = await screen.findByRole('button', { name: /submit for review/i });
    fireEvent.click(submitBtn);

    await waitFor(() => expect(mockedReview.submitForApproval).toHaveBeenCalledWith('p1'));
  });

  it('adds a comment', async () => {
    mockedReview.getApproval.mockResolvedValue(null);
    mockedReview.listComments.mockResolvedValue([]);
    mockedReview.addComment.mockResolvedValue({
      id: 'c2',
      post_id: 'p1',
      author_user_id: 'u-admin',
      author_email: 'admin@example.com',
      body: 'Looks good',
      created_at: '2026-08-01T00:00:00Z',
    });

    const { wrapper } = renderWithProviders();
    render(<PostReviewPanel postId="p1" />, { wrapper });

    const box = await screen.findByPlaceholderText(/leave a comment/i);
    fireEvent.change(box, { target: { value: 'Looks good' } });
    fireEvent.click(screen.getByRole('button', { name: 'Post' }));

    await waitFor(() => expect(mockedReview.addComment).toHaveBeenCalledWith('p1', 'Looks good'));
  });
});
