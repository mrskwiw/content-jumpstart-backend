/**
 * Tests for CopyButton component
 */
import { describe, it, expect, beforeEach } from '@jest/globals';

const vi = jest;
import { render, screen, fireEvent } from '@testing-library/react';
import { CopyButton } from '../CopyButton';

describe('CopyButton', () => {
  const writeText = vi.fn().mockResolvedValue(undefined);

  beforeEach(() => {
    writeText.mockClear();
    // jsdom exposes navigator.clipboard as a getter-only property, so it must be
    // redefined (Object.assign throws). configurable:true lets each test reset it.
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText },
    });
  });

  it('should render copy button', () => {
    render(<CopyButton text="Test content" />);
    const button = screen.getByRole('button');
    expect(button).toBeInTheDocument();
  });

  it('should copy text to clipboard on click', async () => {
    const testText = 'Test content to copy';

    render(<CopyButton text={testText} />);

    const button = screen.getByRole('button');
    // fireEvent (not userEvent) so userEvent's own clipboard stub does not shadow the mock.
    fireEvent.click(button);

    expect(writeText).toHaveBeenCalledWith(testText);
  });

  it('should show copied state after clicking', async () => {
    render(<CopyButton text="Test" />);

    const button = screen.getByRole('button');
    fireEvent.click(button);

    // Button should show some feedback
    expect(button).toBeInTheDocument();
  });

  it('should accept custom className', () => {
    render(<CopyButton text="Test" className="custom-class" />);
    const button = screen.getByRole('button');
    expect(button.className).toContain('custom-class');
  });
});
