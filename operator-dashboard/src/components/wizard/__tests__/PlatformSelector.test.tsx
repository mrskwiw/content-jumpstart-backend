/**
 * Smoke tests for PlatformSelector component
 */
import { describe, it, expect, jest } from '@jest/globals';
import { render } from '@testing-library/react';
import { PlatformSelector } from '../PlatformSelector';

describe('PlatformSelector Component', () => {
  const mockOnChange = jest.fn();

  it('should render without crashing', () => {
    const { container } = render(
      <PlatformSelector selected={[]} onChange={mockOnChange} />
    );
    expect(container).toBeInTheDocument();
  });

  it('should render platform options', () => {
    const { container } = render(
      <PlatformSelector selected={[]} onChange={mockOnChange} />
    );
    // Should have platform buttons/options
    const buttons = container.querySelectorAll('button, input[type="checkbox"], [role="checkbox"]');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('should render with selected platforms', () => {
    const { container } = render(
      <PlatformSelector selected={['linkedin', 'twitter']} onChange={mockOnChange} />
    );
    expect(container).toBeInTheDocument();
  });
});
