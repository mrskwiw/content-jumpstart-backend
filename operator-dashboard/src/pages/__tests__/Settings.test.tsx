/**
 * Smoke tests for Settings page
 */
import { describe, it, expect, jest } from '@jest/globals';
import { renderWithProviders } from '@/__tests__/setup/test-utils';
import Settings from '../Settings';

// Mock ThemeContext. ThemeProvider must be a real pass-through because the shared
// test wrapper (AllTheProviders) mounts it around every rendered component.
jest.mock('@/contexts/ThemeContext', () => ({
  useTheme: () => ({
    theme: 'light',
    setTheme: jest.fn(),
    actualTheme: 'light',
  }),
  ThemeProvider: ({ children }: { children: React.ReactNode }) => children,
}));

describe('Settings Page', () => {
  it('should render without crashing', () => {
    const { container } = renderWithProviders(<Settings />);
    expect(container).toBeInTheDocument();
  });

  it('should render settings header', () => {
    const { container } = renderWithProviders(<Settings />);
    expect(container).toHaveTextContent('Settings');
  });

  it('should render settings tabs or sections', () => {
    const { container } = renderWithProviders(<Settings />);
    // Should have multiple sections/tabs
    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('should render settings content area', () => {
    const { container } = renderWithProviders(<Settings />);
    // Should have content area
    const content = container.querySelector('[class*="p-"]');
    expect(content).toBeInTheDocument();
  });
});
