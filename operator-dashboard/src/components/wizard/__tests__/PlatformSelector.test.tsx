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
      <PlatformSelector selected="" onChange={mockOnChange} />
    );
    expect(container).toBeInTheDocument();
  });

  it('should render platform options', () => {
    const { container } = render(
      <PlatformSelector selected="" onChange={mockOnChange} />
    );
    // Platforms render as single-select radio inputs.
    const options = container.querySelectorAll('input[type="radio"]');
    expect(options.length).toBeGreaterThan(0);
  });

  it('should render with a selected platform', () => {
    const { container } = render(
      <PlatformSelector selected="linkedin" onChange={mockOnChange} />
    );
    expect(container).toBeInTheDocument();
  });
});
