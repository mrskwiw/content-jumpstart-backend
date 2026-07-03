/**
 * Smoke tests for Notifications page
 */
import { describe, it, expect } from '@jest/globals';
import { renderWithProviders } from '@/__tests__/setup/test-utils';
import Notifications from '../Notifications';

describe('Notifications Page', () => {
  it('should render without crashing', () => {
    const { container } = renderWithProviders(<Notifications />);
    expect(container).toBeInTheDocument();
  });

  it('should render notifications header', () => {
    const { container } = renderWithProviders(<Notifications />);
    expect(container).toHaveTextContent('Notifications');
  });

  it('should render notification list or empty state', () => {
    const { container } = renderWithProviders(<Notifications />);
    // Should render content area
    const content = container.querySelector('[class*="p-"]');
    expect(content).toBeInTheDocument();
  });

  it('should render filter controls', () => {
    const { container } = renderWithProviders(<Notifications />);
    // Should have buttons/controls
    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThan(0);
  });
});
