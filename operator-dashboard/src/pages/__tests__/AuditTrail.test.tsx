/**
 * Smoke tests for AuditTrail page
 */
import { describe, it, expect } from '@jest/globals';
import { renderWithProviders } from '@/__tests__/setup/test-utils';
import AuditTrail from '../AuditTrail';

describe('AuditTrail Page', () => {
  it('should render without crashing', () => {
    const { container } = renderWithProviders(<AuditTrail />);
    expect(container).toBeInTheDocument();
  });

  it('should render audit trail header', () => {
    const { container } = renderWithProviders(<AuditTrail />);
    expect(container).toHaveTextContent('Audit Trail');
  });

  it('should render audit log entries or empty state', () => {
    const { container } = renderWithProviders(<AuditTrail />);
    // Should render content area
    const content = container.querySelector('[class*="rounded"]');
    expect(content).toBeInTheDocument();
  });

  it('should render filter and search controls', () => {
    const { container } = renderWithProviders(<AuditTrail />);
    // Should have interactive controls
    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThan(0);
  });
});
