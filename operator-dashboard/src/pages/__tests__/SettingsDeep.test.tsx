/**
 * Comprehensive tests for Settings page (1,139 LOC)
 *
 * Coverage focus:
 * - Tab switching between 7 tabs
 * - Integration cards and configuration
 * - Workflow rules and toggles
 * - Notification settings
 * - Preferences (theme, timezone)
 * - Security features
 * - Database backup/restore
 * - User interactions
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders, userEvent } from '@/__tests__/setup/test-utils';
import Settings from '../Settings';

// Mock window.URL
global.URL.createObjectURL = jest.fn(() => 'blob:mock-url');
global.URL.revokeObjectURL = jest.fn();

// Mock fetch for database operations
global.fetch = jest.fn();

describe('Settings Page', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    // Settings derives the active tab from the URL (?tab=), and renderWithProviders uses
    // a BrowserRouter backed by the shared window.location — reset it so a tab click in
    // one test can't leak a ?tab= param into the next test's initial render.
    window.history.pushState({}, '', '/');

    // Mock successful fetch responses
    (global.fetch).mockResolvedValue({
      ok: true,
      blob: async () => new Blob(['mock backup data']),
      json: async () => ({ success: true }),
      headers: {
        get: (name: string) => {
          if (name === 'Content-Disposition') {
            return 'attachment; filename="backup.db"';
          }
          return null;
        },
      },
    } as Response);
  });

  describe('Initial Rendering', () => {
    it('should render settings header', () => {
      renderWithProviders(<Settings />);
      expect(screen.getByText(/advanced settings/i)).toBeInTheDocument();
    });

    it('should render all tab buttons', () => {
      renderWithProviders(<Settings />);

      expect(screen.getByText('Integrations')).toBeInTheDocument();
      expect(screen.getByText('Workflows')).toBeInTheDocument();
      expect(screen.getByText('Notifications')).toBeInTheDocument();
      expect(screen.getByText('Preferences')).toBeInTheDocument();
      expect(screen.getByText('Security')).toBeInTheDocument();
      expect(screen.getByText('Database')).toBeInTheDocument();
    });

    it('should show integrations tab by default', () => {
      renderWithProviders(<Settings />);

      expect(screen.getByText(/anthropic claude api/i)).toBeInTheDocument();
    });

    it('should render save actions footer', () => {
      renderWithProviders(<Settings />);

      expect(screen.getByText(/reset to defaults/i)).toBeInTheDocument();
      expect(screen.getByText(/save changes/i)).toBeInTheDocument();
    });
  });

  describe('Tab Navigation', () => {
    it('should switch to workflows tab', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Settings />);

      const workflowsTab = screen.getByRole('button', { name: /workflows/i });
      await user.click(workflowsTab);

      await waitFor(() => {
        expect(screen.getByText(/workflow automation/i)).toBeInTheDocument();
      });
    });

    it('should switch to notifications tab', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Settings />);

      const notificationsTab = screen.getByRole('button', { name: /notifications/i });
      await user.click(notificationsTab);

      await waitFor(() => {
        expect(screen.getByText(/email notifications/i)).toBeInTheDocument();
        expect(screen.getByText(/in-app notifications/i)).toBeInTheDocument();
      });
    });

    it('should switch to preferences tab', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Settings />);

      const preferencesTab = screen.getByRole('button', { name: /preferences/i });
      await user.click(preferencesTab);

      await waitFor(() => {
        expect(screen.getByText(/ui preferences/i)).toBeInTheDocument();
        expect(screen.getByText(/theme/i)).toBeInTheDocument();
      });
    });

    it('should switch to security tab', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Settings />);

      const securityTab = screen.getByRole('button', { name: /security/i });
      await user.click(securityTab);

      await waitFor(() => {
        expect(screen.getByText(/session management/i)).toBeInTheDocument();
        expect(screen.getByText(/password & authentication/i)).toBeInTheDocument();
      });
    });

    it('should switch to database tab', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Settings />);

      const databaseTab = screen.getByRole('button', { name: /database/i });
      await user.click(databaseTab);

      await waitFor(() => {
        // "Database Backup" is both a heading and part of a button label; use the
        // exact heading text. "Database Restore" is unique.
        expect(screen.getByText('Database Backup')).toBeInTheDocument();
        expect(screen.getByText('Database Restore')).toBeInTheDocument();
      });
    });

    it('should switch to users tab for admin', async () => {
      const user = userEvent.setup();
      // AuthProvider loads the user from localStorage only when BOTH an access
      // token and a user record are present, and the User model is camelCase.
      localStorage.setItem('access_token', 'test-token');
      localStorage.setItem('user', JSON.stringify({ isSuperuser: true }));

      renderWithProviders(<Settings />);

      // Wait for the auth effect to populate the user and reveal the admin tab.
      const usersTab = await screen.findByRole('button', { name: /users/i });
      await user.click(usersTab);

      // Users tab renders UsersTab component; active tab gets the primary border.
      await waitFor(() => {
        expect(usersTab.className).toMatch(/border-primary/);
      });
    });

    it('honors a ?tab=credits deep-link on initial render', () => {
      window.history.pushState({}, '', '/?tab=credits');

      renderWithProviders(<Settings />);

      // Tab is derived from the URL during render, so Credits is active immediately.
      const creditsTab = screen.getByRole('button', { name: /credits/i });
      expect(creditsTab.className).toMatch(/border-primary/);
    });

    it('reflects a tab change back into the URL (bidirectional sync)', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Settings />);

      await user.click(screen.getByRole('button', { name: /security/i }));

      await waitFor(() => {
        expect(window.location.search).toContain('tab=security');
      });
      // And the URL is the source of truth, so the Security tab is active.
      expect(screen.getByRole('button', { name: /security/i }).className).toMatch(/border-primary/);
    });

    it('should not show users tab for non-admin', () => {
      localStorage.setItem('user', JSON.stringify({ is_superuser: false }));

      renderWithProviders(<Settings />);

      expect(screen.queryByRole('button', { name: /users/i })).not.toBeInTheDocument();
    });
  });

  describe('Integrations Tab', () => {
    it('should render all integration cards', () => {
      renderWithProviders(<Settings />);

      expect(screen.getByText(/anthropic claude api/i)).toBeInTheDocument();
      expect(screen.getByText(/email service \(sendgrid\)/i)).toBeInTheDocument();
      expect(screen.getByText(/cloud storage \(s3\)/i)).toBeInTheDocument();
      expect(screen.getByText(/analytics \(google analytics\)/i)).toBeInTheDocument();
    });

    it('should show integration status badges', () => {
      renderWithProviders(<Settings />);

      const statusBadges = screen.getAllByText(/connected|disconnected|error/i);
      expect(statusBadges.length).toBeGreaterThan(0);
    });

    it('should render configure buttons for integrations', () => {
      renderWithProviders(<Settings />);

      const configureButtons = screen.getAllByText(/configure|connect/i);
      expect(configureButtons.length).toBeGreaterThan(3);
    });

    it('should open configure modal on button click', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Settings />);

      // Query buttons, not text: /connect/i also matches the "Connected"/
      // "Disconnected" status badges, which aren't clickable.
      const configureButtons = screen.getAllByRole('button', { name: /configure|connect/i });
      await user.click(configureButtons[0]);

      await waitFor(() => {
        expect(screen.getByText(/integration settings and credentials/i)).toBeInTheDocument();
      });
    });

    it('should close configure modal', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Settings />);

      const configureButtons = screen.getAllByRole('button', { name: /configure|connect/i });
      await user.click(configureButtons[0]);

      await waitFor(() => {
        expect(screen.getByText(/integration settings and credentials/i)).toBeInTheDocument();
      });

      // The modal has both an X (aria-label "Close integration configuration")
      // and a footer "Close" button; target the X by its specific label.
      const closeButton = screen.getByRole('button', { name: /close integration configuration/i });
      await user.click(closeButton);

      await waitFor(() => {
        expect(screen.queryByText(/integration settings and credentials/i)).not.toBeInTheDocument();
      });
    });
  });

  describe('Workflows Tab', () => {
    it('should render workflow rules', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Settings />);

      const workflowsTab = screen.getByRole('button', { name: /workflows/i });
      await user.click(workflowsTab);

      await waitFor(() => {
        expect(screen.getByText(/send client satisfaction survey/i)).toBeInTheDocument();
      });
    });

    it('should render workflow toggle switches', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Settings />);

      const workflowsTab = screen.getByRole('button', { name: /workflows/i });
      await user.click(workflowsTab);

      await waitFor(() => {
        const toggles = screen.getAllByRole('checkbox');
        expect(toggles.length).toBeGreaterThan(0);
      });
    });

    it('should render workflow configuration sliders', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Settings />);

      const workflowsTab = screen.getByRole('button', { name: /workflows/i });
      await user.click(workflowsTab);

      await waitFor(() => {
        expect(screen.getByText(/days delay/i)).toBeInTheDocument();
        const sliders = screen.getAllByRole('slider');
        expect(sliders.length).toBeGreaterThan(0);
      });
    });

    it('should handle workflow toggle', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Settings />);

      const workflowsTab = screen.getByRole('button', { name: /workflows/i });
      await user.click(workflowsTab);

      await waitFor(async () => {
        const toggle = screen.getAllByRole('checkbox')[0];
        await user.click(toggle);
      });

      // Mutation would be called in real scenario
    });

    it('should handle slider value change', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Settings />);

      const workflowsTab = screen.getByRole('button', { name: /workflows/i });
      await user.click(workflowsTab);

      await waitFor(async () => {
        const slider = screen.getAllByRole('slider')[0];
        await user.type(slider, '20');
      });
    });

    it('should render create new workflow button', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Settings />);

      const workflowsTab = screen.getByRole('button', { name: /workflows/i });
      await user.click(workflowsTab);

      await waitFor(() => {
        expect(screen.getByText(/create new workflow rule/i)).toBeInTheDocument();
      });
    });
  });

  describe('Notifications Tab', () => {
    it('should render email notification settings', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Settings />);

      const notificationsTab = screen.getByRole('button', { name: /notifications/i });
      await user.click(notificationsTab);

      await waitFor(() => {
        expect(screen.getByText(/deliverable ready for client/i)).toBeInTheDocument();
        expect(screen.getByText(/new project assigned/i)).toBeInTheDocument();
        expect(screen.getByText(/deadline approaching/i)).toBeInTheDocument();
      });
    });

    it('should render in-app notification settings', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Settings />);

      const notificationsTab = screen.getByRole('button', { name: /notifications/i });
      await user.click(notificationsTab);

      await waitFor(() => {
        expect(screen.getByText(/desktop notifications/i)).toBeInTheDocument();
        expect(screen.getByText(/sound alerts/i)).toBeInTheDocument();
        expect(screen.getByText(/daily activity summary/i)).toBeInTheDocument();
      });
    });

    it('should have toggle switches for notifications', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Settings />);

      const notificationsTab = screen.getByRole('button', { name: /notifications/i });
      await user.click(notificationsTab);

      await waitFor(() => {
        const toggles = screen.getAllByRole('checkbox');
        expect(toggles.length).toBeGreaterThan(5);
      });
    });
  });

  describe('Preferences Tab', () => {
    it('should render theme selector', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Settings />);

      const preferencesTab = screen.getByRole('button', { name: /preferences/i });
      await user.click(preferencesTab);

      await waitFor(() => {
        // The Theme/Timezone <label>s aren't associated with their <select>s
        // (no htmlFor/id), so query positionally: [0] = theme, [1] = timezone.
        const themeSelect = screen.getAllByRole('combobox')[0];
        expect(themeSelect).toBeInTheDocument();
      });
    });

    it('should render timezone selector', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Settings />);

      const preferencesTab = screen.getByRole('button', { name: /preferences/i });
      await user.click(preferencesTab);

      await waitFor(() => {
        const timezoneSelect = screen.getAllByRole('combobox')[1];
        expect(timezoneSelect).toBeInTheDocument();
      });
    });

    it('should have multiple timezone options', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Settings />);

      const preferencesTab = screen.getByRole('button', { name: /preferences/i });
      await user.click(preferencesTab);

      await waitFor(() => {
        expect(screen.getByText(/eastern time/i)).toBeInTheDocument();
        expect(screen.getByText(/pacific time/i)).toBeInTheDocument();
      });
    });

    it('should handle theme change', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Settings />);

      const preferencesTab = screen.getByRole('button', { name: /preferences/i });
      await user.click(preferencesTab);

      await waitFor(async () => {
        // Theme select is the first combobox (labels aren't associated).
        const themeSelect = screen.getAllByRole('combobox')[0];
        await user.selectOptions(themeSelect, 'dark');
        expect(themeSelect).toHaveValue('dark');
      });
    });

    it('should render view mode toggles', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Settings />);

      const preferencesTab = screen.getByRole('button', { name: /preferences/i });
      await user.click(preferencesTab);

      await waitFor(() => {
        expect(screen.getByText(/compact view mode/i)).toBeInTheDocument();
        expect(screen.getByText(/auto-refresh data/i)).toBeInTheDocument();
      });
    });
  });

  describe('Security Tab', () => {
    it('should render session management section', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Settings />);

      const securityTab = screen.getByRole('button', { name: /security/i });
      await user.click(securityTab);

      await waitFor(() => {
        expect(screen.getByText(/session management/i)).toBeInTheDocument();
        expect(screen.getByText(/active session/i)).toBeInTheDocument();
      });
    });

    it('should render sign out button', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Settings />);

      const securityTab = screen.getByRole('button', { name: /security/i });
      await user.click(securityTab);

      await waitFor(() => {
        expect(screen.getByText(/sign out & clear session/i)).toBeInTheDocument();
      });
    });

    it('should render password section', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Settings />);

      const securityTab = screen.getByRole('button', { name: /security/i });
      await user.click(securityTab);

      await waitFor(() => {
        expect(screen.getByText(/password & authentication/i)).toBeInTheDocument();
        expect(screen.getByText(/change password/i)).toBeInTheDocument();
        expect(screen.getByText(/two-factor authentication/i)).toBeInTheDocument();
      });
    });

    it('should render data & privacy section', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Settings />);

      const securityTab = screen.getByRole('button', { name: /security/i });
      await user.click(securityTab);

      // The export control was redesigned to be role-aware; a non-superuser (the default
      // test auth state) sees the admin-export note. Assert that exact control text rather
      // than the stale "Export My Data" label or a too-generic /export/i match.
      await waitFor(() => {
        expect(screen.getByText(/data & privacy/i)).toBeInTheDocument();
        expect(
          screen.getByText(/full-instance data export is available to administrators/i)
        ).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /delete my account/i })).toBeInTheDocument();
      });
    });
  });

  describe('Database Tab', () => {
    it('should render database backup section', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Settings />);

      const databaseTab = screen.getByRole('button', { name: /database/i });
      await user.click(databaseTab);

      await waitFor(() => {
        // Exact heading — /database backup/i also matches the download button.
        expect(screen.getByText('Database Backup')).toBeInTheDocument();
        expect(screen.getByText(/download database backup/i)).toBeInTheDocument();
      });
    });

    it('should render database restore section', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Settings />);

      const databaseTab = screen.getByRole('button', { name: /database/i });
      await user.click(databaseTab);

      await waitFor(() => {
        expect(screen.getByText('Database Restore')).toBeInTheDocument();
        // Both the restore and merge sections have a "Select Backup File" label.
        expect(screen.getAllByText(/select backup file/i).length).toBeGreaterThan(0);
      });
    });

    it('should render database information', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Settings />);

      const databaseTab = screen.getByRole('button', { name: /database/i });
      await user.click(databaseTab);

      await waitFor(() => {
        expect(screen.getByText(/database information/i)).toBeInTheDocument();
        expect(screen.getByText(/sqlite/i)).toBeInTheDocument();
      });
    });

    it('should handle backup download', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Settings />);

      const databaseTab = screen.getByRole('button', { name: /database/i });
      await user.click(databaseTab);

      await waitFor(async () => {
        const backupButton = screen.getByText(/download database backup/i);
        await user.click(backupButton);
      });

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          '/api/database/backup',
          expect.objectContaining({
            headers: expect.objectContaining({
              Authorization: expect.any(String),
            }),
          })
        );
      });
    });

    it('should show loading state during backup', async () => {
      const user = userEvent.setup();

      // Mock delayed response
      (global.fetch).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({
          ok: true,
          blob: async () => new Blob(['mock']),
          headers: { get: () => 'attachment; filename="backup.db"' },
        } as Response), 1000))
      );

      renderWithProviders(<Settings />);

      const databaseTab = screen.getByRole('button', { name: /database/i });
      await user.click(databaseTab);

      await waitFor(async () => {
        const backupButton = screen.getByText(/download database backup/i);
        await user.click(backupButton);
      });

      expect(screen.getByText(/creating backup/i)).toBeInTheDocument();
    });

    it('should handle file selection for restore', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Settings />);

      const databaseTab = screen.getByRole('button', { name: /database/i });
      await user.click(databaseTab);

      await waitFor(async () => {
        // The file-input <label>s aren't associated (no htmlFor/id); the restore
        // section's input is the first file input in the DOM.
        const fileInput = document.querySelectorAll('input[type="file"]')[0] as HTMLInputElement;
        const file = new File(['database content'], 'backup.db', { type: 'application/x-sqlite3' });
        await user.upload(fileInput, file);
      });

      await waitFor(() => {
        expect(screen.getByText('backup.db')).toBeInTheDocument();
      });
    });

    it('should show restore confirmation modal', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Settings />);

      const databaseTab = screen.getByRole('button', { name: /database/i });
      await user.click(databaseTab);

      await waitFor(async () => {
        // The file-input <label>s aren't associated (no htmlFor/id); the restore
        // section's input is the first file input in the DOM.
        const fileInput = document.querySelectorAll('input[type="file"]')[0] as HTMLInputElement;
        const file = new File(['database content'], 'backup.db', { type: 'application/x-sqlite3' });
        await user.upload(fileInput, file);
      });

      await waitFor(async () => {
        const restoreButton = screen.getByText(/restore database from backup/i);
        await user.click(restoreButton);
      });

      await waitFor(() => {
        expect(screen.getByText(/confirm database restore/i)).toBeInTheDocument();
      });
    });

    it('should handle restore confirmation', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Settings />);

      const databaseTab = screen.getByRole('button', { name: /database/i });
      await user.click(databaseTab);

      // Upload file
      await waitFor(async () => {
        // The file-input <label>s aren't associated (no htmlFor/id); the restore
        // section's input is the first file input in the DOM.
        const fileInput = document.querySelectorAll('input[type="file"]')[0] as HTMLInputElement;
        const file = new File(['database content'], 'backup.db', { type: 'application/x-sqlite3' });
        await user.upload(fileInput, file);
      });

      // Click restore
      await waitFor(async () => {
        const restoreButton = screen.getByText(/restore database from backup/i);
        await user.click(restoreButton);
      });

      // Confirm
      await waitFor(async () => {
        const confirmButtons = screen.getAllByText(/restore database/i);
        const confirmButton = confirmButtons[confirmButtons.length - 1];
        await user.click(confirmButton);
      });

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          '/api/database/restore',
          expect.objectContaining({
            method: 'POST',
          })
        );
      });
    });

    it('should cancel restore confirmation', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Settings />);

      const databaseTab = screen.getByRole('button', { name: /database/i });
      await user.click(databaseTab);

      // Upload file
      await waitFor(async () => {
        // The file-input <label>s aren't associated (no htmlFor/id); the restore
        // section's input is the first file input in the DOM.
        const fileInput = document.querySelectorAll('input[type="file"]')[0] as HTMLInputElement;
        const file = new File(['database content'], 'backup.db', { type: 'application/x-sqlite3' });
        await user.upload(fileInput, file);
      });

      // Click restore
      await waitFor(async () => {
        const restoreButton = screen.getByText(/restore database from backup/i);
        await user.click(restoreButton);
      });

      // Cancel
      await waitFor(async () => {
        const cancelButton = screen.getByRole('button', { name: /cancel/i });
        await user.click(cancelButton);
      });

      await waitFor(() => {
        expect(screen.queryByText(/confirm database restore/i)).not.toBeInTheDocument();
      });
    });
  });

  describe('User Interactions', () => {
    it('should handle save changes button', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Settings />);

      const saveButton = screen.getByText(/save changes/i);
      await user.click(saveButton);

      // In real scenario, this would trigger save mutations
    });

    it('should handle reset to defaults button', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Settings />);

      const resetButton = screen.getByText(/reset to defaults/i);
      await user.click(resetButton);

      // In real scenario, this would reset all settings
    });
  });

  describe('Modal Interactions', () => {
    it('should close modal with X button', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Settings />);

      const configureButtons = screen.getAllByText(/configure|connect/i);
      await user.click(configureButtons[0]);

      await waitFor(async () => {
        const closeButtons = screen.getAllByRole('button');
        const xButton = closeButtons.find(btn => btn.querySelector('svg'));
        if (xButton) await user.click(xButton);
      });

      await waitFor(() => {
        expect(screen.queryByText(/integration settings/i)).not.toBeInTheDocument();
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle backup download error', async () => {
      const user = userEvent.setup();
      const alertSpy = jest.spyOn(window, 'alert').mockImplementation(() => {});

      (global.fetch).mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => ({ detail: 'Backup failed' }),
      } as Response);

      renderWithProviders(<Settings />);

      const databaseTab = screen.getByRole('button', { name: /database/i });
      await user.click(databaseTab);

      await waitFor(async () => {
        const backupButton = screen.getByText(/download database backup/i);
        await user.click(backupButton);
      });

      await waitFor(() => {
        expect(alertSpy).toHaveBeenCalledWith(expect.stringContaining('Backup failed'));
      });

      alertSpy.mockRestore();
    });

    it('should handle restore error', async () => {
      const user = userEvent.setup();
      const alertSpy = jest.spyOn(window, 'alert').mockImplementation(() => {});

      (global.fetch).mockImplementation((url) => {
        if (url === '/api/database/restore') {
          return Promise.resolve({
            ok: false,
            json: async () => ({ detail: 'Restore failed' }),
          } as Response);
        }
        // Return backup success for the automatic backup before restore
        return Promise.resolve({
          ok: true,
          blob: async () => new Blob(['mock']),
          headers: { get: () => 'attachment; filename="backup.db"' },
        } as Response);
      });

      renderWithProviders(<Settings />);

      const databaseTab = screen.getByRole('button', { name: /database/i });
      await user.click(databaseTab);

      // Upload file
      await waitFor(async () => {
        // The file-input <label>s aren't associated (no htmlFor/id); the restore
        // section's input is the first file input in the DOM.
        const fileInput = document.querySelectorAll('input[type="file"]')[0] as HTMLInputElement;
        const file = new File(['database content'], 'backup.db', { type: 'application/x-sqlite3' });
        await user.upload(fileInput, file);
      });

      // Click restore
      await waitFor(async () => {
        const restoreButton = screen.getByText(/restore database from backup/i);
        await user.click(restoreButton);
      });

      // Confirm
      await waitFor(async () => {
        const confirmButtons = screen.getAllByText(/restore database/i);
        const confirmButton = confirmButtons[confirmButtons.length - 1];
        await user.click(confirmButton);
      });

      await waitFor(() => {
        expect(alertSpy).toHaveBeenCalledWith(expect.stringContaining('Restore failed'));
      });

      alertSpy.mockRestore();
    });
  });
});
