/**
 * Tests for ContentReview page component
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import { renderWithProviders } from '@/__tests__/setup/test-utils';
import ContentReview from '../ContentReview';
import { approvalBadge } from '../contentReviewHelpers';
import { postsApi } from '@/api/posts';
import { projectsApi } from '@/api/projects';
import { clientsApi } from '@/api/clients';

jest.mock('@/api/posts', () => ({ postsApi: { list: jest.fn() } }));
jest.mock('@/api/projects', () => ({ projectsApi: { list: jest.fn() } }));
jest.mock('@/api/clients', () => ({ clientsApi: { list: jest.fn() } }));

const mockedPosts = postsApi.list as jest.Mock;
const mockedProjects = projectsApi.list as jest.Mock;
const mockedClients = clientsApi.list as jest.Mock;

beforeEach(() => {
  mockedPosts.mockResolvedValue({ items: [], metadata: {} });
  mockedProjects.mockResolvedValue({ items: [] });
  mockedClients.mockResolvedValue([]);
});

describe('ContentReview Page', () => {
  it('should render content review page', () => {
    renderWithProviders(<ContentReview />);

    // Basic rendering test - adjust based on actual page content
    expect(screen.getByText(/Content Review/i)).toBeInTheDocument();
  });

  it('should render page container', () => {
    const { container } = renderWithProviders(<ContentReview />);
    expect(container).toBeInTheDocument();
  });

  it('offers a "Pending review" filter toggle (COLLAB-01)', () => {
    renderWithProviders(<ContentReview />);
    expect(screen.getByRole('button', { name: /pending review/i })).toBeInTheDocument();
  });

  it('Pending review shows submitted-awaiting posts only, not never-submitted ones', async () => {
    // Two QA posts: one SUBMITTED & awaiting a decision (pending), one NEVER submitted (null).
    mockedPosts.mockResolvedValue({
      items: [
        { id: 'p-pending', content: 'AWAITING A DECISION NOW', projectId: 'proj1', approval_status: 'pending' },
        { id: 'p-null', content: 'NEVER SUBMITTED YET', projectId: 'proj1', approval_status: null },
      ],
      metadata: {},
    });
    mockedProjects.mockResolvedValue({
      items: [{ id: 'proj1', name: 'Proj', clientId: 'c1', status: 'qa' }],
    });
    mockedClients.mockResolvedValue([{ id: 'c1', name: 'Client' }]);

    renderWithProviders(<ContentReview />);

    // Both QA posts are visible before filtering…
    await waitFor(() => expect(screen.getByText('AWAITING A DECISION NOW')).toBeInTheDocument());
    expect(screen.getByText('NEVER SUBMITTED YET')).toBeInTheDocument();

    // The count reflects the one pending post, not the never-submitted one.
    expect(screen.getByRole('button', { name: /pending review \(1\)/i })).toBeInTheDocument();

    // Toggling the filter keeps only the submitted-and-awaiting post; the null one drops out
    // (it isn't awaiting a reviewer — an editor must submit it first).
    fireEvent.click(screen.getByRole('button', { name: /pending review/i }));
    expect(screen.getByText('AWAITING A DECISION NOW')).toBeInTheDocument();
    expect(screen.queryByText('NEVER SUBMITTED YET')).not.toBeInTheDocument();
  });
});

describe('approvalBadge (COLLAB-01 team-review status)', () => {
  it('labels each review state distinctly', () => {
    expect(approvalBadge('approved')?.label).toBe('Review: approved');
    expect(approvalBadge('pending')?.label).toBe('Review: pending');
    expect(approvalBadge('rejected')?.label).toBe('Review: rejected');
  });

  it('renders no badge when the post was never submitted for review', () => {
    // null / undefined / unknown → no badge (avoids implying a review that never happened).
    expect(approvalBadge(null)).toBeNull();
    expect(approvalBadge(undefined)).toBeNull();
    expect(approvalBadge('something-else')).toBeNull();
  });
});
