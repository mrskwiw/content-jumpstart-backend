/**
 * Smoke tests for TemplateLibrary page
 */
import { describe, it, expect } from '@jest/globals';
import { renderWithProviders } from '@/__tests__/setup/test-utils';
import TemplateLibrary from '../TemplateLibrary';

describe('TemplateLibrary Page', () => {
  it('should render without crashing', () => {
    const { container } = renderWithProviders(<TemplateLibrary />);
    expect(container).toBeInTheDocument();
  });

  it('should render template library header', () => {
    const { container } = renderWithProviders(<TemplateLibrary />);
    expect(container).toHaveTextContent('Template Library');
  });

  it('should render template cards or grid', () => {
    const { container } = renderWithProviders(<TemplateLibrary />);
    // Should render templates
    const cards = container.querySelectorAll('[class*="rounded"], [class*="border"]');
    expect(cards.length).toBeGreaterThan(0);
  });

  it('should render search or filter controls', () => {
    const { container } = renderWithProviders(<TemplateLibrary />);
    // Should have controls
    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThan(0);
  });
});
