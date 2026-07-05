/**
 * Smoke tests for Team page
 */
import { describe, it, expect } from '@jest/globals';
import { renderWithProviders } from '@/__tests__/setup/test-utils';
import Team from '../Team';

describe('Team Page', () => {
  it('should render without crashing', () => {
    const { container } = renderWithProviders(<Team />);
    expect(container).toBeInTheDocument();
  });

  it('should render team header', () => {
    const { container } = renderWithProviders(<Team />);
    expect(container).toHaveTextContent('Team Management');
  });

  it('should render team member cards', () => {
    const { container } = renderWithProviders(<Team />);
    // Should render multiple cards/rows
    const elements = container.querySelectorAll('[class*="rounded"]');
    expect(elements.length).toBeGreaterThan(0);
  });

  it('should render search and filter controls', () => {
    const { container } = renderWithProviders(<Team />);
    // Should have interactive controls
    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThan(0);
  });
});
