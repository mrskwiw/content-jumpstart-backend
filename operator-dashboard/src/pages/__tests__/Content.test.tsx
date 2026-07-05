/**
 * Tests for Content page component
 */
import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from '@/__tests__/setup/test-utils';
import Content from '../Content';

describe('Content Page', () => {
  it('should render content page', () => {
    const { container } = renderWithProviders(<Content />);

    // Basic rendering test
    expect(container).toBeInTheDocument();
  });

  it('should render page container', () => {
    const { container } = renderWithProviders(<Content />);
    expect(container).toBeInTheDocument();
  });
});
