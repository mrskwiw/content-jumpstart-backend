/**
 * Smoke tests for Analytics page
 */
import { describe, it, expect } from '@jest/globals';
import { render } from '@testing-library/react';
import { renderWithProviders } from '@/__tests__/setup/test-utils';
import Analytics from '../Analytics';

describe('Analytics Page', () => {
  it('should render without crashing', () => {
    const { container } = renderWithProviders(<Analytics />);
    expect(container).toBeInTheDocument();
  });

  it('should render analytics dashboard header', () => {
    const { container } = renderWithProviders(<Analytics />);
    expect(container).toHaveTextContent('Analytics');
  });

  it('should render time range filters', () => {
    const { container } = renderWithProviders(<Analytics />);
    // Should have time range buttons
    expect(container.querySelector('button')).toBeInTheDocument();
  });

  it('should render metric cards', () => {
    const { container } = renderWithProviders(<Analytics />);
    // Should render multiple metric cards
    const cards = container.querySelectorAll('[class*="rounded"]');
    expect(cards.length).toBeGreaterThan(0);
  });
});
