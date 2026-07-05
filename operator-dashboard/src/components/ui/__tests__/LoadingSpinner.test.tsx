/**
 * Tests for LoadingSpinner component
 */
import { describe, it, expect } from '@jest/globals';
import { render } from '@testing-library/react';
import { LoadingSpinner } from '../LoadingSpinner';

describe('LoadingSpinner', () => {
  it('should render spinner with default message', () => {
    const { container } = render(<LoadingSpinner />);
    const spinner = container.querySelector('.animate-spin');
    expect(spinner).toBeInTheDocument();
    expect(container).toHaveTextContent('Loading...');
  });

  it('should render spinner with custom message', () => {
    const { container } = render(<LoadingSpinner message="Please wait..." />);
    expect(container).toHaveTextContent('Please wait...');
  });

  it('should render with small size', () => {
    const { container } = render(<LoadingSpinner size="sm" />);
    const spinner = container.querySelector('.h-4');
    expect(spinner).toBeInTheDocument();
  });

  it('should render with medium size (default)', () => {
    const { container } = render(<LoadingSpinner size="md" />);
    const spinner = container.querySelector('.h-8');
    expect(spinner).toBeInTheDocument();
  });

  it('should render with large size', () => {
    const { container } = render(<LoadingSpinner size="lg" />);
    const spinner = container.querySelector('.h-12');
    expect(spinner).toBeInTheDocument();
  });

  it('should render inline variant', () => {
    const { container } = render(<LoadingSpinner inline />);
    const inlineContainer = container.querySelector('.flex.items-center.gap-2');
    expect(inlineContainer).toBeInTheDocument();
  });

  it('should render block variant (default)', () => {
    const { container } = render(<LoadingSpinner />);
    const blockContainer = container.querySelector('.rounded-lg.border');
    expect(blockContainer).toBeInTheDocument();
  });
});
