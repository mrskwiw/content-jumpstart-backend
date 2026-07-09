/**
 * Smoke tests for AuditTrail page
 */
import { describe, it, expect } from '@jest/globals';
import { renderWithProviders, waitFor } from '@/__tests__/setup/test-utils';
import AuditTrail from '../AuditTrail';

// The page fetches audit logs + compliance stats via React Query. In jsdom the real
// axios request never resolves, leaving the page stuck on its loading spinner. Mock
// the audit API so the page renders its real UI (header, controls, table).
jest.mock('@/api/audit', () => ({
  auditApi: {
    list: jest.fn().mockResolvedValue([
      {
        id: 'evt_001',
        timestamp: new Date().toISOString(),
        user: { id: 'u1', name: 'Sarah Johnson', email: 'sarah.johnson@example.com', role: 'Admin' },
        action: 'Updated deliverable status',
        actionType: 'update',
        resource: 'Q4 Campaign Post #12',
        resourceType: 'deliverable',
        details: 'Changed status from draft to approved',
        ipAddress: '192.168.1.100',
        status: 'success',
        metadata: { previousStatus: 'draft', newStatus: 'approved' },
      },
    ]),
    stats: jest.fn().mockResolvedValue({
      totalEvents: 8456,
      todayEvents: 127,
      failedActions: 23,
      securityEvents: 8,
      avgEventsPerDay: 142,
      retentionDays: 90,
    }),
    exportUrl: jest.fn(() => '/api/audit/export.csv'),
  },
}));

describe('AuditTrail Page', () => {
  it('should render without crashing', () => {
    const { container } = renderWithProviders(<AuditTrail />);
    expect(container).toBeInTheDocument();
  });

  it('should render audit trail header', async () => {
    const { container } = renderWithProviders(<AuditTrail />);
    await waitFor(() => {
      expect(container).toHaveTextContent('Audit Trail');
    });
  });

  it('should render audit log entries or empty state', () => {
    const { container } = renderWithProviders(<AuditTrail />);
    // Should render content area
    const content = container.querySelector('[class*="rounded"]');
    expect(content).toBeInTheDocument();
  });

  it('should render filter and search controls', async () => {
    const { container } = renderWithProviders(<AuditTrail />);
    // Should have interactive controls once the page has loaded
    await waitFor(() => {
      const buttons = container.querySelectorAll('button');
      expect(buttons.length).toBeGreaterThan(0);
    });
  });
});
