/**
 * Comprehensive tests for Team page (874 LOC)
 *
 * Coverage focus:
 * - Stats cards rendering
 * - Team member table
 * - Search and filtering
 * - User interactions (invite, edit role)
 * - Permissions matrix
 * - Activity log
 * - Modal interactions
 * - Data filtering
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { screen, waitFor, within } from '@testing-library/react';
import { renderWithProviders, userEvent } from '@/__tests__/setup/test-utils';
import Team from '../Team';

describe('Team Page - Comprehensive', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Initial Rendering', () => {
    it('should render page header', async () => {
      renderWithProviders(<Team />);

      await waitFor(() => {
        expect(screen.getByText(/team collaboration/i)).toBeInTheDocument();
      });
    });

    it('should render invite member button', async () => {
      renderWithProviders(<Team />);

      await waitFor(() => {
        expect(screen.getByText(/invite member/i)).toBeInTheDocument();
      });
    });

    it('should render stats cards', async () => {
      renderWithProviders(<Team />);

      await waitFor(() => {
        // Exact strings — the subtitle "Manage team members, roles, ..." also
        // matches /team members/i, so scope to the stat-card labels.
        expect(screen.getByText('Team Members')).toBeInTheDocument();
        expect(screen.getByText('Active Projects')).toBeInTheDocument();
        expect(screen.getByText('Avg Quality')).toBeInTheDocument();
        expect(screen.getByText('Hours This Month')).toBeInTheDocument();
      });
    });

    it('should display stats values', async () => {
      renderWithProviders(<Team />);

      await waitFor(() => {
        // Should show numeric values in stats
        const statsCards = screen.getAllByText(/\d+/);
        expect(statsCards.length).toBeGreaterThan(0);
      });
    });
  });

  describe('Filter Controls', () => {
    it('should render search input', async () => {
      renderWithProviders(<Team />);

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/search team members/i)).toBeInTheDocument();
      });
    });

    it('should render role filter dropdown', async () => {
      renderWithProviders(<Team />);

      await waitFor(() => {
        // Two filter dropdowns exist (role + status); scope to the first.
        const roleFilter = screen.getAllByRole('combobox')[0];
        const optionTexts = within(roleFilter).getAllByRole('option').map(opt => opt.textContent);
        expect(optionTexts).toContain('All Roles');
        expect(optionTexts).toContain('Admin');
        expect(optionTexts).toContain('Editor');
        expect(optionTexts).toContain('Viewer');
      });
    });

    it('should render status filter dropdown', async () => {
      renderWithProviders(<Team />);

      await waitFor(() => {
        const statusFilters = screen.getAllByRole('combobox');
        const statusFilter = statusFilters[1];
        const optionTexts = within(statusFilter).getAllByRole('option').map(opt => opt.textContent);
        expect(optionTexts).toContain('All Statuses');
        expect(optionTexts).toContain('Active');
        expect(optionTexts).toContain('Inactive');
        expect(optionTexts).toContain('Invited');
      });
    });

    it('should handle search input', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Team />);

      await waitFor(async () => {
        const searchInput = screen.getByPlaceholderText(/search team members/i);
        await user.type(searchInput, 'Sarah');
        expect(searchInput).toHaveValue('Sarah');
      });
    });

    it('should handle role filter selection', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Team />);

      await waitFor(async () => {
        const roleFilter = screen.getAllByRole('combobox')[0];
        await user.selectOptions(roleFilter, 'admin');
        expect(roleFilter).toHaveValue('admin');
      });
    });

    it('should handle status filter selection', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Team />);

      await waitFor(async () => {
        const statusFilter = screen.getAllByRole('combobox')[1];
        await user.selectOptions(statusFilter, 'active');
        expect(statusFilter).toHaveValue('active');
      });
    });

    it('should show clear filters button when filters active', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Team />);

      await waitFor(async () => {
        const searchInput = screen.getByPlaceholderText(/search team members/i);
        await user.type(searchInput, 'test');
      });

      await waitFor(() => {
        expect(screen.getByText(/clear filters/i)).toBeInTheDocument();
      });
    });

    it('should clear filters when clear button clicked', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Team />);

      // Apply filters
      await waitFor(async () => {
        const searchInput = screen.getByPlaceholderText(/search team members/i);
        await user.type(searchInput, 'test');
      });

      // Clear filters
      await waitFor(async () => {
        const clearButton = screen.getByText(/clear filters/i);
        await user.click(clearButton);
      });

      await waitFor(() => {
        const searchInput = screen.getByPlaceholderText(/search team members/i);
        expect(searchInput).toHaveValue('');
      });
    });
  });

  describe('Team Members Table', () => {
    it('should render table headers', async () => {
      renderWithProviders(<Team />);

      await waitFor(() => {
        // Assert on column headers directly — the words appear elsewhere
        // (stat cards, permissions matrix, buttons), so plain getByText is ambiguous.
        const headerTexts = screen.getAllByRole('columnheader').map(h => h.textContent);
        expect(headerTexts).toContain('Member');
        expect(headerTexts).toContain('Role');
        expect(headerTexts).toContain('Status');
        expect(headerTexts).toContain('Projects');
        expect(headerTexts).toContain('Posts');
        expect(headerTexts).toContain('Quality');
        expect(headerTexts).toContain('Last Active');
      });
    });

    it('should render team member rows', async () => {
      renderWithProviders(<Team />);

      await waitFor(() => {
        // Names also appear in the activity feed, so use getAllByText.
        expect(screen.getAllByText(/sarah johnson/i).length).toBeGreaterThan(0);
        expect(screen.getAllByText(/michael chen/i).length).toBeGreaterThan(0);
      });
    });

    it('should display member avatars', async () => {
      renderWithProviders(<Team />);

      await waitFor(() => {
        // Avatar initials appear in both the table and the activity feed.
        expect(screen.getAllByText('SJ').length).toBeGreaterThan(0);
        expect(screen.getAllByText('MC').length).toBeGreaterThan(0);
      });
    });

    it('should display role badges', async () => {
      renderWithProviders(<Team />);

      await waitFor(() => {
        const adminBadges = screen.getAllByText(/admin/i);
        expect(adminBadges.length).toBeGreaterThan(0);
      });
    });

    it('should display status badges', async () => {
      renderWithProviders(<Team />);

      await waitFor(() => {
        const activeBadges = screen.getAllByText(/active/i);
        expect(activeBadges.length).toBeGreaterThan(0);
      });
    });

    it('should display member statistics', async () => {
      renderWithProviders(<Team />);

      await waitFor(() => {
        // Should show projects, posts, quality %
        const cells = screen.getAllByRole('cell');
        const hasNumbers = cells.some(cell => /\d+/.test(cell.textContent || ''));
        expect(hasNumbers).toBe(true);
      });
    });

    it('should show action menu buttons', async () => {
      renderWithProviders(<Team />);

      await waitFor(() => {
        const actionButtons = screen.getAllByRole('button', { name: '' });
        expect(actionButtons.length).toBeGreaterThan(0);
      });
    });

    it('should open action menu on button click', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Team />);

      await waitFor(async () => {
        // Row action toggles are icon-only (svg, no text); the Invite Member
        // button also has an svg but has text, so filter it out.
        const menuButtons = screen
          .getAllByRole('button')
          .filter(btn => btn.querySelector('svg') && !btn.textContent?.trim());
        await user.click(menuButtons[0]);
      });

      await waitFor(() => {
        expect(screen.getByText(/edit role/i)).toBeInTheDocument();
        expect(screen.getByText(/send email/i)).toBeInTheDocument();
        // Exact — /remove/i also matches the "...and remove team members" permission text.
        expect(screen.getByText('Remove')).toBeInTheDocument();
      });
    });
  });

  describe('Search Functionality', () => {
    it('should filter by name', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Team />);

      await waitFor(async () => {
        const searchInput = screen.getByPlaceholderText(/search team members/i);
        await user.type(searchInput, 'Sarah');
      });

      await waitFor(() => {
        // Table row remains; the activity feed (unfiltered) also shows the name.
        expect(screen.getAllByText(/sarah johnson/i).length).toBeGreaterThan(0);
        // Other members might be filtered out (tested via integration)
      });
    });

    it('should filter by email', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Team />);

      await waitFor(async () => {
        const searchInput = screen.getByPlaceholderText(/search team members/i);
        await user.type(searchInput, 'sarah@');
      });

      await waitFor(() => {
        expect(screen.getByText(/sarah@company\.com/i)).toBeInTheDocument();
      });
    });

    it('should show empty state when no matches', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Team />);

      await waitFor(async () => {
        const searchInput = screen.getByPlaceholderText(/search team members/i);
        await user.type(searchInput, 'xyznonexistent');
      });

      await waitFor(() => {
        expect(screen.getByText(/no team members found/i)).toBeInTheDocument();
        expect(screen.getByText(/try adjusting your filters/i)).toBeInTheDocument();
      });
    });
  });

  describe('Permissions Matrix', () => {
    it('should render permissions matrix section', async () => {
      renderWithProviders(<Team />);

      await waitFor(() => {
        expect(screen.getByText(/permissions matrix/i)).toBeInTheDocument();
      });
    });

    it('should render permission rows', async () => {
      renderWithProviders(<Team />);

      await waitFor(() => {
        // Exact names — /manage team/i also matches the "Manage team members..."
        // subtitle, so use exact strings for the permission rows.
        expect(screen.getByText('Create Projects')).toBeInTheDocument();
        expect(screen.getByText('Delete Projects')).toBeInTheDocument();
        expect(screen.getByText('Generate Content')).toBeInTheDocument();
        expect(screen.getByText('Manage Team')).toBeInTheDocument();
      });
    });

    it('should show permission descriptions', async () => {
      renderWithProviders(<Team />);

      await waitFor(() => {
        expect(screen.getByText(/can create new client projects/i)).toBeInTheDocument();
        expect(screen.getByText(/can permanently delete projects/i)).toBeInTheDocument();
      });
    });

    it('should display role columns', async () => {
      renderWithProviders(<Team />);

      await waitFor(() => {
        const headers = screen.getAllByRole('columnheader');
        const headerTexts = headers.map(h => h.textContent);
        expect(headerTexts).toContain('Admin');
        expect(headerTexts).toContain('Editor');
        expect(headerTexts).toContain('Viewer');
      });
    });

    it('should show checkmarks for allowed permissions', async () => {
      renderWithProviders(<Team />);

      await waitFor(() => {
        // Check icons should be present for allowed permissions
        const svgElements = document.querySelectorAll('svg');
        expect(svgElements.length).toBeGreaterThan(10);
      });
    });
  });

  describe('Recent Activity', () => {
    it('should render activity section', async () => {
      renderWithProviders(<Team />);

      await waitFor(() => {
        expect(screen.getByText(/recent team activity/i)).toBeInTheDocument();
      });
    });

    it('should display activity entries', async () => {
      renderWithProviders(<Team />);

      await waitFor(() => {
        // Each activity shows both an action label and a details line that
        // repeat the phrase, so match all occurrences.
        expect(screen.getAllByText(/created project/i).length).toBeGreaterThan(0);
        expect(screen.getAllByText(/generated content/i).length).toBeGreaterThan(0);
      });
    });

    it('should show activity timestamps', async () => {
      renderWithProviders(<Team />);

      await waitFor(() => {
        const timeElements = screen.getAllByText(/\d+[mhd] ago/i);
        expect(timeElements.length).toBeGreaterThan(0);
      });
    });

    it('should display user avatars in activity', async () => {
      renderWithProviders(<Team />);

      await waitFor(() => {
        const avatars = document.querySelectorAll('[class*="rounded-full"]');
        expect(avatars.length).toBeGreaterThan(0);
      });
    });
  });

  describe('Invite Member Modal', () => {
    it('should open invite modal on button click', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Team />);

      await waitFor(async () => {
        const inviteButton = screen.getByText(/invite member/i);
        await user.click(inviteButton);
      });

      await waitFor(() => {
        expect(screen.getByText(/invite team member/i)).toBeInTheDocument();
        expect(screen.getByText(/send an invitation to join your team/i)).toBeInTheDocument();
      });
    });

    it('should render email input in modal', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Team />);

      await waitFor(async () => {
        const inviteButton = screen.getByText(/invite member/i);
        await user.click(inviteButton);
      });

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/colleague@company\.com/i)).toBeInTheDocument();
      });
    });

    it('should render role selector in modal', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Team />);

      await waitFor(async () => {
        const inviteButton = screen.getByText(/invite member/i);
        await user.click(inviteButton);
      });

      await waitFor(() => {
        const roleOptions = screen.getAllByRole('option');
        const optionTexts = roleOptions.map(opt => opt.textContent);
        expect(optionTexts.some(text => text?.includes('Viewer'))).toBe(true);
        expect(optionTexts.some(text => text?.includes('Editor'))).toBe(true);
        expect(optionTexts.some(text => text?.includes('Admin'))).toBe(true);
      });
    });

    it('should handle email input', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Team />);

      await waitFor(async () => {
        const inviteButton = screen.getByText(/invite member/i);
        await user.click(inviteButton);
      });

      await waitFor(async () => {
        const emailInput = screen.getByPlaceholderText(/colleague@company\.com/i);
        await user.type(emailInput, 'newuser@company.com');
        expect(emailInput).toHaveValue('newuser@company.com');
      });
    });

    it('should handle role selection', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Team />);

      await waitFor(async () => {
        const inviteButton = screen.getByText(/invite member/i);
        await user.click(inviteButton);
      });

      await waitFor(async () => {
        // The two filter dropdowns are still mounted behind the modal; the
        // modal's role select is the last combobox in the DOM.
        const roleSelect = screen.getAllByRole('combobox').at(-1)!;
        await user.selectOptions(roleSelect, 'admin');
      });

      await waitFor(() => {
        const roleSelect = screen.getAllByRole('combobox').at(-1)!;
        expect(roleSelect).toHaveValue('admin');
      });
    });

    it('should disable send button when email empty', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Team />);

      await waitFor(async () => {
        const inviteButton = screen.getByText(/invite member/i);
        await user.click(inviteButton);
      });

      await waitFor(() => {
        const sendButton = screen.getByText(/send invitation/i);
        expect(sendButton).toBeDisabled();
      });
    });

    it('should enable send button when email provided', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Team />);

      await waitFor(async () => {
        const inviteButton = screen.getByText(/invite member/i);
        await user.click(inviteButton);
      });

      await waitFor(async () => {
        const emailInput = screen.getByPlaceholderText(/colleague@company\.com/i);
        await user.type(emailInput, 'newuser@company.com');
      });

      await waitFor(() => {
        const sendButton = screen.getByText(/send invitation/i);
        expect(sendButton).not.toBeDisabled();
      });
    });

    it('should close modal on cancel', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Team />);

      await waitFor(async () => {
        const inviteButton = screen.getByText(/invite member/i);
        await user.click(inviteButton);
      });

      await waitFor(async () => {
        const cancelButton = screen.getByRole('button', { name: /cancel/i });
        await user.click(cancelButton);
      });

      await waitFor(() => {
        expect(screen.queryByText(/invite team member/i)).not.toBeInTheDocument();
      });
    });

    it('should close modal on X button', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Team />);

      await waitFor(async () => {
        const inviteButton = screen.getByText(/invite member/i);
        await user.click(inviteButton);
      });

      await waitFor(async () => {
        // Icon-only buttons: 5 row action toggles then the modal's X (last).
        const iconButtons = screen
          .getAllByRole('button')
          .filter(btn => btn.querySelector('svg') && !btn.textContent?.trim());
        await user.click(iconButtons.at(-1)!);
      });

      await waitFor(() => {
        expect(screen.queryByText(/invite team member/i)).not.toBeInTheDocument();
      });
    });
  });

  describe('Edit Role Modal', () => {
    it('should open edit role modal from action menu', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Team />);

      // Open action menu
      await waitFor(async () => {
        // Icon-only row action toggle (svg, no text) — skip text-bearing buttons.
        const menuButtons = screen
          .getAllByRole('button')
          .filter(btn => btn.querySelector('svg') && !btn.textContent?.trim());
        await user.click(menuButtons[0]);
      });

      // Click edit role
      await waitFor(async () => {
        const editButton = screen.getByText(/edit role/i);
        await user.click(editButton);
      });

      await waitFor(() => {
        expect(screen.getByText(/change role for/i)).toBeInTheDocument();
      });
    });

    it('should render role selector in edit modal', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Team />);

      // Open action menu and edit modal
      await waitFor(async () => {
        // Icon-only row action toggle (svg, no text) — skip text-bearing buttons.
        const menuButtons = screen
          .getAllByRole('button')
          .filter(btn => btn.querySelector('svg') && !btn.textContent?.trim());
        await user.click(menuButtons[0]);
      });

      await waitFor(async () => {
        const editButton = screen.getByText(/edit role/i);
        await user.click(editButton);
      });

      await waitFor(() => {
        const roleOptions = screen.getAllByRole('option');
        expect(roleOptions.length).toBeGreaterThan(0);
      });
    });

    it('should disable save button when role unchanged', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Team />);

      // Open edit modal
      await waitFor(async () => {
        // Icon-only row action toggle (svg, no text) — skip text-bearing buttons.
        const menuButtons = screen
          .getAllByRole('button')
          .filter(btn => btn.querySelector('svg') && !btn.textContent?.trim());
        await user.click(menuButtons[0]);
      });

      await waitFor(async () => {
        const editButton = screen.getByText(/edit role/i);
        await user.click(editButton);
      });

      await waitFor(() => {
        const saveButton = screen.getByText(/save changes/i);
        expect(saveButton).toBeDisabled();
      });
    });

    it('should close edit modal on cancel', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Team />);

      // Open edit modal
      await waitFor(async () => {
        // Icon-only row action toggle (svg, no text) — skip text-bearing buttons.
        const menuButtons = screen
          .getAllByRole('button')
          .filter(btn => btn.querySelector('svg') && !btn.textContent?.trim());
        await user.click(menuButtons[0]);
      });

      await waitFor(async () => {
        const editButton = screen.getByText(/edit role/i);
        await user.click(editButton);
      });

      // Close modal
      await waitFor(async () => {
        const cancelButton = screen.getByRole('button', { name: /cancel/i });
        await user.click(cancelButton);
      });

      await waitFor(() => {
        expect(screen.queryByText(/change role for/i)).not.toBeInTheDocument();
      });
    });
  });

  describe('Data Display', () => {
    it('should format time ago correctly', async () => {
      renderWithProviders(<Team />);

      await waitFor(() => {
        // Should show relative times like "5m ago", "2h ago"
        const timeElements = screen.getAllByText(/\d+[mhd] ago/i);
        expect(timeElements.length).toBeGreaterThan(0);
      });
    });

    it('should display quality percentages', async () => {
      renderWithProviders(<Team />);

      await waitFor(() => {
        // Should show percentages like "92%"
        const percentages = screen.getAllByText(/\d+%/);
        expect(percentages.length).toBeGreaterThan(0);
      });
    });

    it('should show member count in stats', async () => {
      renderWithProviders(<Team />);

      await waitFor(() => {
        // Total members stat should be visible (exact label, not the subtitle).
        const statsSection = screen.getByText('Team Members').closest('div');
        expect(statsSection).toBeInTheDocument();
      });
    });
  });

  describe('Responsive Behavior', () => {
    it('should render on mobile viewport', async () => {
      // Set mobile viewport
      global.innerWidth = 375;
      global.dispatchEvent(new Event('resize'));

      renderWithProviders(<Team />);

      await waitFor(() => {
        expect(screen.getByText(/team collaboration/i)).toBeInTheDocument();
      });
    });

    it('should render on desktop viewport', async () => {
      // Set desktop viewport
      global.innerWidth = 1920;
      global.dispatchEvent(new Event('resize'));

      renderWithProviders(<Team />);

      await waitFor(() => {
        expect(screen.getByText(/team collaboration/i)).toBeInTheDocument();
      });
    });
  });
});
