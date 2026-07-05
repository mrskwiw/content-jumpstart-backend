/**
 * Tests for ThemeToggle component
 */
import { describe, it, expect, jest } from '@jest/globals';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ThemeToggle from '../ThemeToggle';
import { ThemeProvider } from '@/contexts/ThemeContext';

describe('ThemeToggle', () => {
  const mockMatchMedia = (matches: boolean) => {
    return jest.fn().mockImplementation((query: string) => ({
      matches,
      media: query,
      onchange: null,
      addListener: jest.fn(),
      removeListener: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      dispatchEvent: jest.fn(),
    })) as unknown as typeof window.matchMedia;
  };

  beforeEach(() => {
    localStorage.clear();
    document.documentElement.className = '';
    window.matchMedia = mockMatchMedia(false);
  });

  it('should render all three theme buttons', () => {
    render(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>
    );

    expect(screen.getByLabelText(/light theme/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/system theme/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/dark theme/i)).toBeInTheDocument();
  });

  it('should highlight system theme by default', () => {
    render(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>
    );

    const systemButton = screen.getByLabelText(/system theme/i);
    expect(systemButton).toHaveClass('bg-primary-500');
  });

  it('should switch to light theme when clicked', async () => {
    const user = userEvent.setup();

    render(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>
    );

    const lightButton = screen.getByLabelText(/light theme/i);
    await user.click(lightButton);

    expect(lightButton).toHaveClass('bg-primary-500');
    expect(localStorage.getItem('theme')).toBe('light');
  });

  it('should switch to dark theme when clicked', async () => {
    const user = userEvent.setup();

    render(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>
    );

    const darkButton = screen.getByLabelText(/dark theme/i);
    await user.click(darkButton);

    expect(darkButton).toHaveClass('bg-primary-500');
    expect(localStorage.getItem('theme')).toBe('dark');
  });

  it('should switch back to system theme', async () => {
    const user = userEvent.setup();
    localStorage.setItem('theme', 'dark');

    render(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>
    );

    const systemButton = screen.getByLabelText(/system theme/i);
    await user.click(systemButton);

    expect(systemButton).toHaveClass('bg-primary-500');
    expect(localStorage.getItem('theme')).toBe('system');
  });

  it('should persist theme selection', async () => {
    const user = userEvent.setup();

    const { unmount } = render(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>
    );

    const darkButton = screen.getByLabelText(/dark theme/i);
    await user.click(darkButton);

    unmount();

    render(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>
    );

    const darkButtonAfterRemount = screen.getByLabelText(/dark theme/i);
    expect(darkButtonAfterRemount).toHaveClass('bg-primary-500');
  });
});
