/**
 * Tests for ContentReview page component
 */
import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from '@/__tests__/setup/test-utils';
import ContentReview from '../ContentReview';
import { approvalBadge } from '../contentReviewHelpers';

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

  it('offers an "Awaiting review" filter toggle (COLLAB-01)', () => {
    renderWithProviders(<ContentReview />);
    expect(screen.getByRole('button', { name: /awaiting review/i })).toBeInTheDocument();
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
