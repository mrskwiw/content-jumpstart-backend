/**
 * Tests for ContentReview page component
 */
import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from '@/__tests__/setup/test-utils';
import ContentReview from '../ContentReview';

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
});
