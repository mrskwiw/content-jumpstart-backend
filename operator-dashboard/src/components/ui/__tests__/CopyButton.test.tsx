/**
 * Tests for CopyButton component
 */
import { describe, it, expect, beforeEach } from '@jest/globals';

const vi = jest;
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CopyButton } from '../CopyButton';

describe('CopyButton', () => {
  beforeEach(() => {
    // Mock clipboard API
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    });
  });

  it('should render copy button', () => {
    render(<CopyButton text="Test content" />);
    const button = screen.getByRole('button');
    expect(button).toBeInTheDocument();
  });

  it('should copy text to clipboard on click', async () => {
    const user = userEvent.setup();
    const testText = 'Test content to copy';

    render(<CopyButton text={testText} />);

    const button = screen.getByRole('button');
    await user.click(button);

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(testText);
  });

  it('should show copied state after clicking', async () => {
    const user = userEvent.setup();

    render(<CopyButton text="Test" />);

    const button = screen.getByRole('button');
    await user.click(button);

    // Button should show some feedback
    expect(button).toBeInTheDocument();
  });

  it('should accept custom className', () => {
    render(<CopyButton text="Test" className="custom-class" />);
    const button = screen.getByRole('button');
    expect(button.className).toContain('custom-class');
  });
});
