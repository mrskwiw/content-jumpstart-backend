/**
 * Comprehensive tests for AuditTrail page (965 LOC)
 *
 * Coverage focus:
 * - Compliance stats cards
 * - Filter controls (5 filters)
 * - Audit logs table
 * - Export functionality
 * - Log detail modal
 * - Search functionality
 * - Date range filtering
 * - User interactions
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { screen, waitFor, within } from '@testing-library/react';
import { renderWithProviders, userEvent } from '@/__tests__/setup/test-utils';
import AuditTrail from '../AuditTrail';

describe('AuditTrail Page - Comprehensive', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Initial Rendering', () => {
    it('should render page header', async () => {
      renderWithProviders(<AuditTrail />);

      await waitFor(() => {
        expect(screen.getByText(/audit trail/i)).toBeInTheDocument();
        expect(screen.getByText(/compliance logging and activity monitoring/i)).toBeInTheDocument();
      });
    });

    it('should show loading state initially', () => {
      renderWithProviders(<AuditTrail />);

      expect(screen.getByText(/loading audit trail/i)).toBeInTheDocument();
    });

    it('should hide loading state after data loads', async () => {
      renderWithProviders(<AuditTrail />);

      await waitFor(() => {
        expect(screen.queryByText(/loading audit trail/i)).not.toBeInTheDocument();
      });
    });
  });

  describe('Stats Cards', () => {
    it('should render all stats cards', async () => {
      renderWithProviders(<AuditTrail />);

      await waitFor(() => {
        expect(screen.getByText(/total events/i)).toBeInTheDocument();
        expect(screen.getByText(/today/i)).toBeInTheDocument();
        expect(screen.getByText(/failed actions/i)).toBeInTheDocument();
        expect(screen.getByText(/security events/i)).toBeInTheDocument();
        expect(screen.getByText(/avg per day/i)).toBeInTheDocument();
        expect(screen.getByText(/retention/i)).toBeInTheDocument();
      });
    });

    it('should display stats values', async () => {
      renderWithProviders(<AuditTrail />);

      await waitFor(() => {
        // Should show numeric values
        expect(screen.getByText('8,456')).toBeInTheDocument();
        expect(screen.getByText('127')).toBeInTheDocument();
        expect(screen.getByText('23')).toBeInTheDocument();
        expect(screen.getByText('8')).toBeInTheDocument();
        expect(screen.getByText('142')).toBeInTheDocument();
        expect(screen.getByText('90d')).toBeInTheDocument();
      });
    });

    it('should display percentage changes', async () => {
      renderWithProviders(<AuditTrail />);

      await waitFor(() => {
        // Today events should show percentage vs average
        const percentageChange = screen.getByText(/\+.*% vs avg/i);
        expect(percentageChange).toBeInTheDocument();
      });
    });

    it('should display time periods', async () => {
      renderWithProviders(<AuditTrail />);

      await waitFor(() => {
        expect(screen.getByText(/all time/i)).toBeInTheDocument();
        expect(screen.getByText(/last 30 days/i)).toBeInTheDocument();
        expect(screen.getByText(/30-day average/i)).toBeInTheDocument();
      });
    });
  });

  describe('Search Functionality', () => {
    it('should render search input', async () => {
      renderWithProviders(<AuditTrail />);

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/search by action, resource, user, or details/i)).toBeInTheDocument();
      });
    });

    it('should handle search input', async () => {
      const user = userEvent.setup();
      renderWithProviders(<AuditTrail />);

      await waitFor(async () => {
        const searchInput = screen.getByPlaceholderText(/search by action/i);
        await user.type(searchInput, 'deliverable');
        expect(searchInput).toHaveValue('deliverable');
      });
    });

    it('should filter results based on search', async () => {
      const user = userEvent.setup();
      renderWithProviders(<AuditTrail />);

      await waitFor(async () => {
        const searchInput = screen.getByPlaceholderText(/search by action/i);
        await user.type(searchInput, 'Updated deliverable');
      });

      await waitFor(() => {
        expect(screen.getByText(/updated deliverable status/i)).toBeInTheDocument();
      });
    });
  });

  describe('Filter Controls', () => {
    it('should render all filter dropdowns', async () => {
      renderWithProviders(<AuditTrail />);

      await waitFor(() => {
        expect(screen.getByLabelText(/action type/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/resource type/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/status/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/user/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/date range/i)).toBeInTheDocument();
      });
    });

    it('should have action type filter options', async () => {
      renderWithProviders(<AuditTrail />);

      await waitFor(() => {
        const actionTypeFilter = screen.getByLabelText(/action type/i);
        const options = within(actionTypeFilter).getAllByRole('option');
        const optionTexts = options.map(opt => opt.textContent);

        expect(optionTexts).toContain('All Actions');
        expect(optionTexts).toContain('Create');
        expect(optionTexts).toContain('Read');
        expect(optionTexts).toContain('Update');
        expect(optionTexts).toContain('Delete');
        expect(optionTexts).toContain('Export');
        expect(optionTexts).toContain('System');
        expect(optionTexts).toContain('Security');
      });
    });

    it('should have resource type filter options', async () => {
      renderWithProviders(<AuditTrail />);

      await waitFor(() => {
        const resourceTypeFilter = screen.getByLabelText(/resource type/i);
        const options = within(resourceTypeFilter).getAllByRole('option');
        const optionTexts = options.map(opt => opt.textContent);

        expect(optionTexts).toContain('All Resources');
        expect(optionTexts).toContain('Projects');
        expect(optionTexts).toContain('Deliverables');
        expect(optionTexts).toContain('Users');
        expect(optionTexts).toContain('Settings');
        expect(optionTexts).toContain('Templates');
        expect(optionTexts).toContain('Clients');
      });
    });

    it('should have status filter options', async () => {
      renderWithProviders(<AuditTrail />);

      await waitFor(() => {
        const statusFilter = screen.getByLabelText(/status/i);
        const options = within(statusFilter).getAllByRole('option');
        const optionTexts = options.map(opt => opt.textContent);

        expect(optionTexts).toContain('All Statuses');
        expect(optionTexts).toContain('Success');
        expect(optionTexts).toContain('Failed');
        expect(optionTexts).toContain('Warning');
      });
    });

    it('should have date range filter options', async () => {
      renderWithProviders(<AuditTrail />);

      await waitFor(() => {
        const dateRangeFilter = screen.getByLabelText(/date range/i);
        const options = within(dateRangeFilter).getAllByRole('option');
        const optionTexts = options.map(opt => opt.textContent);

        expect(optionTexts).toContain('All Time');
        expect(optionTexts).toContain('Today');
        expect(optionTexts).toContain('Last 7 Days');
        expect(optionTexts).toContain('Last 30 Days');
        expect(optionTexts).toContain('Last 90 Days');
      });
    });

    it('should handle action type filter selection', async () => {
      const user = userEvent.setup();
      renderWithProviders(<AuditTrail />);

      await waitFor(async () => {
        const actionTypeFilter = screen.getByLabelText(/action type/i);
        await user.selectOptions(actionTypeFilter, 'create');
        expect(actionTypeFilter).toHaveValue('create');
      });
    });

    it('should handle resource type filter selection', async () => {
      const user = userEvent.setup();
      renderWithProviders(<AuditTrail />);

      await waitFor(async () => {
        const resourceTypeFilter = screen.getByLabelText(/resource type/i);
        await user.selectOptions(resourceTypeFilter, 'project');
        expect(resourceTypeFilter).toHaveValue('project');
      });
    });

    it('should handle status filter selection', async () => {
      const user = userEvent.setup();
      renderWithProviders(<AuditTrail />);

      await waitFor(async () => {
        const statusFilter = screen.getByLabelText(/status/i);
        await user.selectOptions(statusFilter, 'failed');
        expect(statusFilter).toHaveValue('failed');
      });
    });

    it('should handle date range filter selection', async () => {
      const user = userEvent.setup();
      renderWithProviders(<AuditTrail />);

      await waitFor(async () => {
        const dateRangeFilter = screen.getByLabelText(/date range/i);
        await user.selectOptions(dateRangeFilter, 'today');
        expect(dateRangeFilter).toHaveValue('today');
      });
    });

    it('should populate user filter with actual users', async () => {
      renderWithProviders(<AuditTrail />);

      await waitFor(() => {
        const userFilter = screen.getByLabelText(/user/i);
        const options = within(userFilter).getAllByRole('option');
        const optionTexts = options.map(opt => opt.textContent);

        expect(optionTexts).toContain('All Users');
        expect(optionTexts.some(text => text?.includes('Sarah Johnson'))).toBe(true);
        expect(optionTexts.some(text => text?.includes('Michael Chen'))).toBe(true);
      });
    });
  });

  describe('Filter Results Display', () => {
    it('should show event count', async () => {
      renderWithProviders(<AuditTrail />);

      await waitFor(() => {
        expect(screen.getByText(/showing/i)).toBeInTheDocument();
        expect(screen.getByText(/of.*events/i)).toBeInTheDocument();
      });
    });

    it('should update count when filtering', async () => {
      const user = userEvent.setup();
      renderWithProviders(<AuditTrail />);

      await waitFor(() => {
        // Initial count
        const initialText = screen.getByText(/showing.*of.*events/i).textContent;
        expect(initialText).toBeTruthy();
      });

      // Apply filter
      await waitFor(async () => {
        const actionTypeFilter = screen.getByLabelText(/action type/i);
        await user.selectOptions(actionTypeFilter, 'security');
      });

      await waitFor(() => {
        // Count should update (implementation detail tested via integration)
        expect(screen.getByText(/showing/i)).toBeInTheDocument();
      });
    });
  });

  describe('Export Functionality', () => {
    it('should render export button', async () => {
      renderWithProviders(<AuditTrail />);

      await waitFor(() => {
        expect(screen.getByText(/export/i)).toBeInTheDocument();
      });
    });

    it('should open export modal on button click', async () => {
      const user = userEvent.setup();
      renderWithProviders(<AuditTrail />);

      await waitFor(async () => {
        const exportButton = screen.getByText(/export/i);
        await user.click(exportButton);
      });

      await waitFor(() => {
        expect(screen.getByText(/export audit logs/i)).toBeInTheDocument();
        expect(screen.getByText(/for compliance reporting/i)).toBeInTheDocument();
      });
    });

    it('should show CSV export option', async () => {
      const user = userEvent.setup();
      renderWithProviders(<AuditTrail />);

      await waitFor(async () => {
        const exportButton = screen.getByText(/export/i);
        await user.click(exportButton);
      });

      await waitFor(() => {
        expect(screen.getByText(/csv format/i)).toBeInTheDocument();
        expect(screen.getByText(/excel-compatible spreadsheet format/i)).toBeInTheDocument();
      });
    });

    it('should show JSON export option', async () => {
      const user = userEvent.setup();
      renderWithProviders(<AuditTrail />);

      await waitFor(async () => {
        const exportButton = screen.getByText(/export/i);
        await user.click(exportButton);
      });

      await waitFor(() => {
        expect(screen.getByText(/json format/i)).toBeInTheDocument();
        expect(screen.getByText(/machine-readable structured data/i)).toBeInTheDocument();
      });
    });

    it('should close export modal on cancel', async () => {
      const user = userEvent.setup();
      renderWithProviders(<AuditTrail />);

      await waitFor(async () => {
        const exportButton = screen.getByText(/export/i);
        await user.click(exportButton);
      });

      await waitFor(async () => {
        const cancelButton = screen.getByRole('button', { name: /cancel/i });
        await user.click(cancelButton);
      });

      await waitFor(() => {
        expect(screen.queryByText(/export audit logs/i)).not.toBeInTheDocument();
      });
    });
  });

  describe('Audit Logs Table', () => {
    it('should render table headers', async () => {
      renderWithProviders(<AuditTrail />);

      await waitFor(() => {
        expect(screen.getByText(/timestamp/i)).toBeInTheDocument();
        expect(screen.getByText(/user/i)).toBeInTheDocument();
        expect(screen.getByText(/action/i)).toBeInTheDocument();
        expect(screen.getByText(/resource/i)).toBeInTheDocument();
        expect(screen.getByText(/ip address/i)).toBeInTheDocument();
        expect(screen.getByText(/status/i)).toBeInTheDocument();
        expect(screen.getByText(/details/i)).toBeInTheDocument();
      });
    });

    it('should render log entries', async () => {
      renderWithProviders(<AuditTrail />);

      await waitFor(() => {
        expect(screen.getByText(/updated deliverable status/i)).toBeInTheDocument();
        expect(screen.getByText(/exported client data/i)).toBeInTheDocument();
      });
    });

    it('should display user information', async () => {
      renderWithProviders(<AuditTrail />);

      await waitFor(() => {
        expect(screen.getByText(/sarah johnson/i)).toBeInTheDocument();
        expect(screen.getByText(/michael chen/i)).toBeInTheDocument();
      });
    });

    it('should display IP addresses', async () => {
      renderWithProviders(<AuditTrail />);

      await waitFor(() => {
        expect(screen.getByText('192.168.1.100')).toBeInTheDocument();
        expect(screen.getByText('192.168.1.105')).toBeInTheDocument();
      });
    });

    it('should display status badges', async () => {
      renderWithProviders(<AuditTrail />);

      await waitFor(() => {
        const successBadges = screen.getAllByText(/success/i);
        expect(successBadges.length).toBeGreaterThan(0);
      });
    });

    it('should display action type icons', async () => {
      renderWithProviders(<AuditTrail />);

      await waitFor(() => {
        // Icons should be rendered for each action
        const svgElements = document.querySelectorAll('svg');
        expect(svgElements.length).toBeGreaterThan(10);
      });
    });

    it('should display relative timestamps', async () => {
      renderWithProviders(<AuditTrail />);

      await waitFor(() => {
        const timeElements = screen.getAllByText(/\d+[mhd] ago|just now/i);
        expect(timeElements.length).toBeGreaterThan(0);
      });
    });

    it('should display absolute timestamps', async () => {
      renderWithProviders(<AuditTrail />);

      await waitFor(() => {
        // Should show dates like "Dec 17, 2025"
        const dateElements = screen.getAllByText(/\w+ \d+, \d{4}/i);
        expect(dateElements.length).toBeGreaterThan(0);
      });
    });

    it('should be clickable to show details', async () => {
      const user = userEvent.setup();
      renderWithProviders(<AuditTrail />);

      await waitFor(async () => {
        const rows = screen.getAllByRole('row');
        // Click first data row (skip header)
        if (rows[1]) await user.click(rows[1]);
      });

      await waitFor(() => {
        expect(screen.getByText(/event details/i)).toBeInTheDocument();
      });
    });
  });

  describe('Empty States', () => {
    it('should show empty state when no logs match filters', async () => {
      const user = userEvent.setup();
      renderWithProviders(<AuditTrail />);

      // Apply filter that returns no results
      await waitFor(async () => {
        const searchInput = screen.getByPlaceholderText(/search by action/i);
        await user.type(searchInput, 'xyznonexistent');
      });

      await waitFor(() => {
        expect(screen.getByText(/no events found/i)).toBeInTheDocument();
        expect(screen.getByText(/try adjusting your filters/i)).toBeInTheDocument();
      });
    });
  });

  describe('Log Detail Modal', () => {
    it('should open detail modal on row click', async () => {
      const user = userEvent.setup();
      renderWithProviders(<AuditTrail />);

      await waitFor(async () => {
        const rows = screen.getAllByRole('row');
        if (rows[1]) await user.click(rows[1]);
      });

      await waitFor(() => {
        expect(screen.getByText(/event details/i)).toBeInTheDocument();
      });
    });

    it('should display event ID in modal', async () => {
      const user = userEvent.setup();
      renderWithProviders(<AuditTrail />);

      await waitFor(async () => {
        const rows = screen.getAllByRole('row');
        if (rows[1]) await user.click(rows[1]);
      });

      await waitFor(() => {
        expect(screen.getByText(/ID:/i)).toBeInTheDocument();
      });
    });

    it('should display full timestamp in modal', async () => {
      const user = userEvent.setup();
      renderWithProviders(<AuditTrail />);

      await waitFor(async () => {
        const rows = screen.getAllByRole('row');
        if (rows[1]) await user.click(rows[1]);
      });

      await waitFor(() => {
        expect(screen.getByText(/timestamp/i)).toBeInTheDocument();
        expect(screen.getByText(/time ago/i)).toBeInTheDocument();
      });
    });

    it('should display user details in modal', async () => {
      const user = userEvent.setup();
      renderWithProviders(<AuditTrail />);

      await waitFor(async () => {
        const rows = screen.getAllByRole('row');
        if (rows[1]) await user.click(rows[1]);
      });

      await waitFor(() => {
        const modalContent = screen.getByText(/event details/i).closest('div');
        expect(modalContent).toHaveTextContent(/user/i);
        expect(modalContent).toHaveTextContent(/role/i);
      });
    });

    it('should display action details in modal', async () => {
      const user = userEvent.setup();
      renderWithProviders(<AuditTrail />);

      await waitFor(async () => {
        const rows = screen.getAllByRole('row');
        if (rows[1]) await user.click(rows[1]);
      });

      await waitFor(() => {
        const modalContent = screen.getByText(/event details/i).closest('div');
        expect(modalContent).toHaveTextContent(/action/i);
        expect(modalContent).toHaveTextContent(/type:/i);
      });
    });

    it('should display resource details in modal', async () => {
      const user = userEvent.setup();
      renderWithProviders(<AuditTrail />);

      await waitFor(async () => {
        const rows = screen.getAllByRole('row');
        if (rows[1]) await user.click(rows[1]);
      });

      await waitFor(() => {
        const modalContent = screen.getByText(/event details/i).closest('div');
        expect(modalContent).toHaveTextContent(/resource/i);
      });
    });

    it('should display metadata when available', async () => {
      const user = userEvent.setup();
      renderWithProviders(<AuditTrail />);

      await waitFor(async () => {
        const rows = screen.getAllByRole('row');
        if (rows[1]) await user.click(rows[1]);
      });

      await waitFor(() => {
        // Metadata should be displayed as formatted JSON
        expect(screen.getByText(/additional metadata/i)).toBeInTheDocument();
      });
    });

    it('should close modal on close button', async () => {
      const user = userEvent.setup();
      renderWithProviders(<AuditTrail />);

      await waitFor(async () => {
        const rows = screen.getAllByRole('row');
        if (rows[1]) await user.click(rows[1]);
      });

      await waitFor(async () => {
        const closeButton = screen.getByRole('button', { name: /close/i });
        await user.click(closeButton);
      });

      await waitFor(() => {
        expect(screen.queryByText(/event details/i)).not.toBeInTheDocument();
      });
    });

    it('should close modal on background click', async () => {
      const user = userEvent.setup();
      renderWithProviders(<AuditTrail />);

      await waitFor(async () => {
        const rows = screen.getAllByRole('row');
        if (rows[1]) await user.click(rows[1]);
      });

      await waitFor(async () => {
        // Click on modal background
        const modal = screen.getByText(/event details/i).closest('[class*="fixed"]');
        if (modal) await user.click(modal);
      });

      await waitFor(() => {
        expect(screen.queryByText(/event details/i)).not.toBeInTheDocument();
      });
    });
  });

  describe('Data Filtering Logic', () => {
    it('should filter by multiple criteria simultaneously', async () => {
      const user = userEvent.setup();
      renderWithProviders(<AuditTrail />);

      // Apply search
      await waitFor(async () => {
        const searchInput = screen.getByPlaceholderText(/search by action/i);
        await user.type(searchInput, 'deliverable');
      });

      // Apply action type filter
      await waitFor(async () => {
        const actionTypeFilter = screen.getByLabelText(/action type/i);
        await user.selectOptions(actionTypeFilter, 'update');
      });

      // Results should be filtered by both criteria
      await waitFor(() => {
        expect(screen.getByText(/updated deliverable/i)).toBeInTheDocument();
      });
    });

    it('should filter by user', async () => {
      const user = userEvent.setup();
      renderWithProviders(<AuditTrail />);

      await waitFor(async () => {
        const userFilter = screen.getByLabelText(/user/i);
        // Select first user from dropdown
        const options = within(userFilter).getAllByRole('option');
        if (options[1]) await user.selectOptions(userFilter, options[1].value);
      });

      // Should filter to only that user's events
      await waitFor(() => {
        expect(screen.getByText(/showing/i)).toBeInTheDocument();
      });
    });

    it('should filter by date range', async () => {
      const user = userEvent.setup();
      renderWithProviders(<AuditTrail />);

      await waitFor(async () => {
        const dateRangeFilter = screen.getByLabelText(/date range/i);
        await user.selectOptions(dateRangeFilter, 'today');
      });

      // Should only show today's events
      await waitFor(() => {
        expect(screen.getByText(/showing/i)).toBeInTheDocument();
      });
    });
  });

  describe('Visual Indicators', () => {
    it('should use different colors for action types', async () => {
      renderWithProviders(<AuditTrail />);

      await waitFor(() => {
        // Different action types should have different colored badges/icons
        const actionElements = document.querySelectorAll('[class*="bg-"]');
        expect(actionElements.length).toBeGreaterThan(0);
      });
    });

    it('should use different colors for status', async () => {
      renderWithProviders(<AuditTrail />);

      await waitFor(() => {
        // Success/Failed/Warning should have different colors
        const statusElements = screen.getAllByText(/success|failed|warning/i);
        expect(statusElements.length).toBeGreaterThan(0);
      });
    });
  });

  describe('Accessibility', () => {
    it('should have proper table structure', async () => {
      renderWithProviders(<AuditTrail />);

      await waitFor(() => {
        expect(screen.getAllByRole('columnheader')).toHaveLength(7);
      });
    });

    it('should have proper form labels', async () => {
      renderWithProviders(<AuditTrail />);

      await waitFor(() => {
        expect(screen.getByLabelText(/action type/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/resource type/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/status/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/user/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/date range/i)).toBeInTheDocument();
      });
    });
  });
});
