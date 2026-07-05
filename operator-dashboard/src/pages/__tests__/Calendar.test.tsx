/**
 * Smoke tests for Calendar page
 */
import { describe, it, expect } from '@jest/globals';
import { renderWithProviders } from '@/__tests__/setup/test-utils';
import Calendar from '../Calendar';

describe('Calendar Page', () => {
  it('should render without crashing', () => {
    const { container } = renderWithProviders(<Calendar />);
    expect(container).toBeInTheDocument();
  });

  it('should render calendar header', () => {
    const { container } = renderWithProviders(<Calendar />);
    expect(container).toHaveTextContent('Calendar');
  });

  it('should render calendar grid or view', () => {
    const { container } = renderWithProviders(<Calendar />);
    // Should render calendar structure
    const elements = container.querySelectorAll('[class*="grid"], [class*="flex"]');
    expect(elements.length).toBeGreaterThan(0);
  });

  it('should render navigation controls', () => {
    const { container } = renderWithProviders(<Calendar />);
    // Should have buttons for navigation
    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThan(0);
  });
});
