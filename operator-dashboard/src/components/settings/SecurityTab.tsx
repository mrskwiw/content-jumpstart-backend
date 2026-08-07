import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { authApi } from '@/api/auth';
import { exportInstanceData, downloadJson } from '@/api/privacyApi';
import { MFAPanel } from './MFAPanel';

/** Extract a human-readable message from an axios-style error. */
function errorMessage(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (detail && typeof detail === 'object') {
    const d = detail as { message?: string; requirements?: string[] };
    if (d.requirements?.length) return `${d.message ?? 'Invalid password'}: ${d.requirements.join('; ')}`;
    if (d.message) return d.message;
  }
  return fallback;
}

function ChangePasswordModal({ onClose }: { onClose: () => void }) {
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (next !== confirm) {
      setError('New password and confirmation do not match');
      return;
    }
    if (next.length < 8) {
      setError('New password must be at least 8 characters');
      return;
    }
    setSubmitting(true);
    try {
      await authApi.changePassword(current, next);
      setSuccess(true);
    } catch (err) {
      setError(errorMessage(err, 'Failed to change password'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" role="dialog" aria-modal="true">
      <div className="w-full max-w-md rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6 shadow-xl">
        <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-4">Change Password</h3>
        {success ? (
          <div className="space-y-4">
            <p className="text-sm text-green-700 dark:text-green-400">Your password has been updated. For your security, all sessions have been signed out — please sign in again with your new password.</p>
            <button onClick={() => { localStorage.clear(); window.location.href = '/login'; }} className="w-full rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700">Sign In Again</button>
          </div>
        ) : (
          <form onSubmit={submit} className="space-y-3">
            <input type="password" autoComplete="current-password" placeholder="Current password" value={current} onChange={(e) => setCurrent(e.target.value)} required
              className="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-3 py-2 text-sm text-neutral-900 dark:text-neutral-100" />
            <input type="password" autoComplete="new-password" placeholder="New password" value={next} onChange={(e) => setNext(e.target.value)} required
              className="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-3 py-2 text-sm text-neutral-900 dark:text-neutral-100" />
            <input type="password" autoComplete="new-password" placeholder="Confirm new password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required
              className="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-3 py-2 text-sm text-neutral-900 dark:text-neutral-100" />
            <p className="text-xs text-neutral-500 dark:text-neutral-400">At least 8 characters, with an uppercase letter, a lowercase letter, and a digit.</p>
            {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
            <div className="flex gap-2 pt-1">
              <button type="button" onClick={onClose} disabled={submitting}
                className="flex-1 rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-4 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700">Cancel</button>
              <button type="submit" disabled={submitting}
                className="flex-1 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-60">{submitting ? 'Saving…' : 'Update Password'}</button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

export function SecurityTab() {
  const { user } = useAuth();
  const [showChangePassword, setShowChangePassword] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const isSuperuser = !!user?.isSuperuser;

  const handleInstanceExport = async () => {
    setExportError(null);
    setExporting(true);
    try {
      const data = await exportInstanceData();
      const stamp = new Date().toISOString().slice(0, 10);
      downloadJson(data, `instance_export_${stamp}`);
    } catch (err) {
      setExportError(errorMessage(err, 'Export failed'));
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
        <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-4">Session Management</h3>
        <div className="space-y-3">
          <div className="flex items-center justify-between text-sm">
            <span className="text-neutral-700 dark:text-neutral-300">Active Session</span>
            <span className="font-mono text-xs text-neutral-500 dark:text-neutral-400">
              {localStorage.getItem('token') ? 'Authenticated' : 'Not authenticated'}
            </span>
          </div>
          <button onClick={() => { localStorage.clear(); window.location.href = '/login'; }} className="w-full rounded-lg border border-red-300 dark:border-red-700 bg-red-50 dark:bg-red-900/20 px-4 py-2 text-sm font-medium text-red-700 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/30">
            Sign Out & Clear Session
          </button>
        </div>
      </div>

      <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
        <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-4">Password & Authentication</h3>
        <div className="space-y-3">
          <button onClick={() => setShowChangePassword(true)} className="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-4 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700">Change Password</button>
          {/* BUGS #172: real TOTP enrollment, replacing a toggle that was wired to nothing. */}
          <div className="border-t border-neutral-200 dark:border-neutral-700 pt-3">
            <MFAPanel />
          </div>
        </div>
      </div>

      <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
        <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-4">Data & Privacy</h3>
        <div className="space-y-3">
          {isSuperuser ? (
            <>
              <button onClick={handleInstanceExport} disabled={exporting}
                className="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-4 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700 text-left disabled:opacity-60">
                {exporting ? 'Preparing export…' : 'Export All Data (full instance)'}
              </button>
              <p className="text-xs text-neutral-500 dark:text-neutral-400">Downloads the entire instance database as JSON for migration. Password hashes and other secrets are redacted.</p>
              {exportError && <p className="text-sm text-red-600 dark:text-red-400">{exportError}</p>}
            </>
          ) : (
            <p className="text-sm text-neutral-500 dark:text-neutral-400">Full-instance data export is available to administrators. Per-client exports are available from each client's page.</p>
          )}
          <button disabled title="Account deletion is handled per-client and per-instance by an administrator — coming soon."
            className="w-full rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-800 px-4 py-2 text-sm font-medium text-neutral-400 dark:text-neutral-600 text-left cursor-not-allowed">
            Delete My Account (coming soon)
          </button>
        </div>
      </div>

      {showChangePassword && <ChangePasswordModal onClose={() => setShowChangePassword(false)} />}
    </div>
  );
}
