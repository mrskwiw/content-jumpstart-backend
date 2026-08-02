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

    // Panel is lazy: no review requests until the reviewer opens it.
    expect(mockedReview.getApproval).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: /review & comments/i }));

    await waitFor(() => expect(screen.getByText('Pending review')).toBeInTheDocument());
    expect(screen.getByRole('button', { name: /approve/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /request changes/i })).toBeInTheDocument();
    expect(screen.getByText('Tighten the hook')).toBeInTheDocument();
  });

  it('patches the affected row in the posts cache after approving (no catalog refetch)', async () => {
    mockedReview.getApproval.mockResolvedValue({
      post_id: 'p1',
      status: 'pending',
      submitted_by_user_id: 'u-ed',
      decided_by_user_id: null,
      decided_at: null,
      note: null,
    });
    mockedReview.listComments.mockResolvedValue([]);
    mockedReview.approve.mockResolvedValue({
      post_id: 'p1',
      status: 'approved',
      submitted_by_user_id: 'u-ed',
      decided_by_user_id: 'u-admin',
      decided_at: '2026-08-02T00:00:00Z',
      note: null,
    });

    const { wrapper, client } = renderWithProviders();
    // Seed a cached posts list containing the row whose badge should update.
    client.setQueryData(['posts'], {
      items: [{ id: 'p1', approval_status: null }, { id: 'p2', approval_status: null }],
    });
    const invalidateSpy = jest.spyOn(client, 'invalidateQueries');
    render(<PostReviewPanel postId="p1" />, { wrapper });

    fireEvent.click(screen.getByRole('button', { name: /review & comments/i }));
    const approveBtn = await screen.findByRole('button', { name: /approve/i });
    fireEvent.click(approveBtn);

    await waitFor(() => expect(mockedReview.approve).toHaveBeenCalledWith('p1'));
    // Only the approved row is patched in-place (instant); the other row is untouched…
    await waitFor(() => {
      const cached = client.getQueryData(['posts']) as {
        items: Array<{ id: string; approval_status?: string | null }>;
      };
      expect(cached.items.find((p) => p.id === 'p1')?.approval_status).toBe('approved');
      expect(cached.items.find((p) => p.id === 'p2')?.approval_status).toBeNull();
    });
    // …and we reconcile ONLY currently-mounted ['posts'] consumers (active-only, no fan-out to
    // unmounted screens), never the broad refetch-everything invalidation.
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['posts'], refetchType: 'active' });
    expect(invalidateSpy).not.toHaveBeenCalledWith({ queryKey: ['posts'] });
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

    fireEvent.click(screen.getByRole('button', { name: /review & comments/i }));
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

    fireEvent.click(screen.getByRole('button', { name: /review & comments/i }));
    const box = await screen.findByPlaceholderText(/leave a comment/i);
    fireEvent.change(box, { target: { value: 'Looks good' } });
    fireEvent.click(screen.getByRole('button', { name: 'Post' }));

    await waitFor(() => expect(mockedReview.addComment).toHaveBeenCalledWith('p1', 'Looks good'));
  });

  it('withholds privileged controls when the team lookup fails (no implicit manager)', async () => {
    // A failed getMyTeam() must NOT be treated as a solo/legacy manager — approve/
    // submit controls stay hidden even though the post is unsubmitted/pending.
    mockedTeams.getMyTeam.mockRejectedValue(new Error('network'));
    mockedReview.getApproval.mockResolvedValue(null);
    mockedReview.listComments.mockResolvedValue([]);

    const { wrapper } = renderWithProviders();
    render(<PostReviewPanel postId="p1" />, { wrapper });

    fireEvent.click(screen.getByRole('button', { name: /review & comments/i }));
    // The panel body renders (approval resolved to "Not submitted")…
    await screen.findByText(/not submitted/i);
    // …but with the team lookup failed, no privileged action is offered…
    expect(screen.queryByRole('button', { name: /submit for review/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /approve/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /request changes/i })).not.toBeInTheDocument();
    // …and the failure is recoverable, not a silent lockout: an explicit retry shows.
    expect(await screen.findByText(/couldn't load your permissions/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
  });

  it('recovers privileged controls when a retried team lookup succeeds', async () => {
    mockedReview.getApproval.mockResolvedValue(null);
    mockedReview.listComments.mockResolvedValue([]);
    // First team fetch fails, the retry succeeds as an admin.
    mockedTeams.getMyTeam
      .mockRejectedValueOnce(new Error('network'))
      .mockResolvedValueOnce({
        team: { team_id: 't1', name: 'Acme', my_role: 'admin', members: [] },
      });

    const { wrapper } = renderWithProviders();
    render(<PostReviewPanel postId="p1" />, { wrapper });

    fireEvent.click(screen.getByRole('button', { name: /review & comments/i }));
    const retry = await screen.findByRole('button', { name: /retry/i });
    expect(screen.queryByRole('button', { name: /submit for review/i })).not.toBeInTheDocument();

    fireEvent.click(retry);

    // After a successful retry the admin's submit control appears (post is unsubmitted).
    expect(await screen.findByRole('button', { name: /submit for review/i })).toBeInTheDocument();
  });
});
