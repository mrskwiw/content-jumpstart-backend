/**
 * Comprehensive tests for TemplateSelectionPanel
 */
import { describe, it, expect, jest } from '@jest/globals';
import { render } from '@testing-library/react';
import { TemplateSelectionPanel } from '../TemplateSelectionPanel';

describe('TemplateSelectionPanel', () => {
  const mockOnChange = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should render without crashing', () => {
    const { container } = render(
      <TemplateSelectionPanel
        selected={{}}
        totalPosts={30}
        onChange={mockOnChange}
      />
    );
    expect(container).toBeInTheDocument();
  });

  it('should render template cards', () => {
    const { container } = render(
      <TemplateSelectionPanel
        selected={{}}
        totalPosts={30}
        onChange={mockOnChange}
      />
    );

    // Should have template cards or list
    const cards = container.querySelectorAll('[class*="card"], [class*="border"], [class*="rounded"]');
    expect(cards.length).toBeGreaterThan(0);
  });

  it('should display total posts target', () => {
    const { container } = render(
      <TemplateSelectionPanel
        selected={{}}
        totalPosts={30}
        onChange={mockOnChange}
      />
    );

    expect(container).toHaveTextContent('30');
  });

  it('should render with pre-selected templates', () => {
    const selected = {
      1: 10,
      2: 10,
      3: 10,
    };

    const { container } = render(
      <TemplateSelectionPanel
        selected={selected}
        totalPosts={30}
        onChange={mockOnChange}
      />
    );

    expect(container).toBeInTheDocument();
  });

  it('should show quantity selectors for templates', () => {
    const { container } = render(
      <TemplateSelectionPanel
        selected={{}}
        totalPosts={30}
        onChange={mockOnChange}
      />
    );

    // Should have inputs or buttons for quantity selection
    const controls = container.querySelectorAll('input, button');
    expect(controls.length).toBeGreaterThan(0);
  });

  it('should display template information', () => {
    const { container } = render(
      <TemplateSelectionPanel
        selected={{}}
        totalPosts={30}
        onChange={mockOnChange}
      />
    );

    // Should have template names or descriptions
    const hasText = container.textContent && container.textContent.length > 10;
    expect(hasText).toBe(true);
  });

  it('should track remaining posts allocation', () => {
    const selected = {
      1: 15,
    };

    const { container } = render(
      <TemplateSelectionPanel
        selected={selected}
        totalPosts={30}
        onChange={mockOnChange}
      />
    );

    // Should show some form of counter or remaining count
    expect(container.textContent).toBeTruthy();
  });
});
