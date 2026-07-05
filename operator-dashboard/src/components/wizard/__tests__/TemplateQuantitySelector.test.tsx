/**
 * Smoke tests for TemplateQuantitySelector component
 */
import { describe, it, expect, jest } from '@jest/globals';
import { render } from '@testing-library/react';
import { TemplateQuantitySelector } from '../TemplateQuantitySelector';

describe('TemplateQuantitySelector Component', () => {
  const mockOnChange = jest.fn();

  it('should render without crashing', () => {
    const { container } = render(
      <TemplateQuantitySelector
        templateId={1}
        quantity={5}
        onChange={mockOnChange}
      />
    );
    expect(container).toBeInTheDocument();
  });

  it('should render quantity controls', () => {
    const { container } = render(
      <TemplateQuantitySelector
        templateId={1}
        quantity={5}
        onChange={mockOnChange}
      />
    );
    // Should have buttons or input for quantity
    const inputs = container.querySelectorAll('button, input');
    expect(inputs.length).toBeGreaterThan(0);
  });

  it('should display current quantity', () => {
    const { container } = render(
      <TemplateQuantitySelector
        templateId={1}
        quantity={10}
        onChange={mockOnChange}
      />
    );
    expect(container).toHaveTextContent('10');
  });
});
