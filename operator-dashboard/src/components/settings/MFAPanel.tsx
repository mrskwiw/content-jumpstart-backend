import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { mfaApi, type MFAEnrollment } from '@/api/mfa';

/** Extract a human-readable message from an axios-style error. */
function errorMessage(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  return typeof detail === 'string' ? detail : fallback;
}

const BTN_PRIMARY =
  'rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-60';
const BTN_SECONDARY =
  'rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-4 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700 disabled:opacity-60';
const INPUT =
  'w-full rounded-md border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-3 py-2 text-sm text-neutral-900 dark:text-neutral-100';

/**
 * The one-time list of backup codes. Rendered at enrollment and after a regeneration —
 * the plaintext exists only in this response, so it is offered for download before the
 * user can navigate away.
 */
function BackupCodes({ codes, onDone }: { codes: string[]; onDone?: () => void }) {
  const download = () => {
    const blob = new Blob(
      [
        'Content Jumpstart — two-factor backup codes\n',
        'Each code works once. Store them somewhere safe and offline.\n\n',
        codes.join('\n'),
        '\n',
      ],
      { type: 'text/plain' }
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'content-jumpstart-backup-codes.txt';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-3 rounded-lg border border-amber-300 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20 p-4">
      <p className="text-sm font-medium text-amber-900 dark:text-amber-200">
        Save these backup codes now — they are shown only once.
      </p>
      <p className="text-xs text-amber-800 dark:text-amber-300">
        Each code signs you in once if you lose your authenticator app.
      </p>
      <ul className="grid grid-cols-2 gap-2 font-mono text-sm text-neutral-900 dark:text-neutral-100">
        {codes.map((code) => (
          <li key={code}>{code}</li>
        ))}
      </ul>
      <div className="flex gap-2">
        <button type="button" onClick={download} className={BTN_SECONDARY}>
          Download codes
        </button>
        {onDone && (
          <button type="button" onClick={onDone} className={BTN_SECONDARY}>
            Done
          </button>
        )}
      </div>
    </div>
  );
}

/** Step 2 of enrollment: scan the QR, then prove the secret landed by entering a code. */
function EnrollmentFlow({
  enrollment,
  onCancel,
  onActivated,
}: {
  enrollment: MFAEnrollment;
  onCancel: () => void;
  onActivated: () => void;
}) {
  const [code, setCode] = useState('');
  const [error, setError] = useState<string | null>(null);

  const verify = useMutation({
    mutationFn: () => mfaApi.verify(code),
    onSuccess: (data) => {
      // An invalid code is a 200 with success:false, not an error response.
      if (data.success) onActivated();
      else setError(data.message || 'Invalid verification code');
    },
    onError: (err) => setError(errorMessage(err, 'Could not verify the code')),
  });

  return (
    <div className="space-y-4">
      <ol className="space-y-4 text-sm text-neutral-700 dark:text-neutral-300">
        <li>
          <p className="font-medium">1. Scan this QR code with your authenticator app</p>
          <img
            src={enrollment.qr_code}
            alt="Two-factor QR code"
            className="mt-2 h-44 w-44 rounded border border-neutral-200 dark:border-neutral-700 bg-white"
          />
        </li>
        <li>
          <p className="font-medium">2. Or enter this key manually</p>
          <code className="mt-1 block break-all rounded bg-neutral-100 dark:bg-neutral-800 px-2 py-1 font-mono text-xs">
            {enrollment.secret}
          </code>
        </li>
        <li>
          <p className="font-medium">3. Enter the 6-digit code to finish</p>
          <form
            className="mt-2 flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              setError(null);
              verify.mutate();
            }}
          >
            <input
              aria-label="Verification code"
              inputMode="numeric"
              maxLength={6}
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
              placeholder="000000"
              className={INPUT}
            />
            <button type="submit" disabled={code.length !== 6 || verify.isPending} className={BTN_PRIMARY}>
              {verify.isPending ? 'Verifying…' : 'Activate'}
            </button>
          </form>
        </li>
      </ol>

      <BackupCodes codes={enrollment.backup_codes} />

      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
      <button type="button" onClick={onCancel} className="text-sm text-neutral-500 hover:underline">
        Cancel setup
      </button>
    </div>
  );
}

function DisableForm({ onCancel, onDisabled }: { onCancel: () => void; onDisabled: () => void }) {
  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const [error, setError] = useState<string | null>(null);

  const disable = useMutation({
    mutationFn: () => mfaApi.disable(password, code),
    onSuccess: onDisabled,
    onError: (err) => setError(errorMessage(err, 'Could not disable two-factor authentication')),
  });

  return (
    <form
      className="space-y-3 rounded-lg border border-red-300 dark:border-red-800 bg-red-50 dark:bg-red-900/20 p-4"
      onSubmit={(e) => {
        e.preventDefault();
        setError(null);
        disable.mutate();
      }}
    >
      <p className="text-sm text-red-800 dark:text-red-300">
        Turning off two-factor authentication needs your password and a current code (an unused
        backup code works too).
      </p>
      <input
        type="password"
        aria-label="Password"
        autoComplete="current-password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="Password"
        className={INPUT}
      />
      <input
        aria-label="Verification or backup code"
        value={code}
        onChange={(e) => setCode(e.target.value)}
        placeholder="123456 or backup code"
        className={INPUT}
      />
      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
      <div className="flex gap-2">
        <button type="button" onClick={onCancel} className={BTN_SECONDARY}>
          Cancel
        </button>
        <button
          type="submit"
          disabled={!password || code.length < 6 || disable.isPending}
          className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-60"
        >
          {disable.isPending ? 'Disabling…' : 'Turn off two-factor'}
        </button>
      </div>
    </form>
  );
}

function RegenerateForm({ onCancel, onCodes }: { onCancel: () => void; onCodes: (codes: string[]) => void }) {
  const [code, setCode] = useState('');
  const [error, setError] = useState<string | null>(null);

  const regenerate = useMutation({
    mutationFn: () => mfaApi.regenerateBackupCodes(code),
    onSuccess: (data) => onCodes(data.backup_codes),
    onError: (err) => setError(errorMessage(err, 'Could not regenerate backup codes')),
  });

  return (
    <form
      className="space-y-3 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4"
      onSubmit={(e) => {
        e.preventDefault();
        setError(null);
        regenerate.mutate();
      }}
    >
      <p className="text-sm text-neutral-700 dark:text-neutral-300">
        Enter a code from your authenticator app. This replaces every existing backup code.
      </p>
      <input
        aria-label="Verification code"
        inputMode="numeric"
        maxLength={6}
        value={code}
        onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
        placeholder="000000"
        className={INPUT}
      />
      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
      <div className="flex gap-2">
        <button type="button" onClick={onCancel} className={BTN_SECONDARY}>
          Cancel
        </button>
        <button type="submit" disabled={code.length !== 6 || regenerate.isPending} className={BTN_PRIMARY}>
          {regenerate.isPending ? 'Generating…' : 'Generate new codes'}
        </button>
      </div>
    </form>
  );
}

/**
 * Two-factor authentication settings (BUGS #172).
 *
 * MFA is opt-in per account: nothing here changes how anyone signs in until they finish
 * enrollment, and an account under an operator policy (`mfa_enforced`) can't switch it off.
 */
export function MFAPanel() {
  const queryClient = useQueryClient();
  const [enrollment, setEnrollment] = useState<MFAEnrollment | null>(null);
  const [freshCodes, setFreshCodes] = useState<string[] | null>(null);
  const [mode, setMode] = useState<'idle' | 'disabling' | 'regenerating'>('idle');
  const [error, setError] = useState<string | null>(null);

  const { data: status, isLoading, isError } = useQuery({
    queryKey: ['mfa', 'status'],
    queryFn: mfaApi.status,
  });

  const refresh = () => queryClient.invalidateQueries({ queryKey: ['mfa', 'status'] });

  const startEnrollment = useMutation({
    mutationFn: mfaApi.enroll,
    onSuccess: (data) => {
      setError(null);
      setEnrollment(data);
    },
    onError: (err) => setError(errorMessage(err, 'Could not start two-factor setup')),
  });

  const enabled = status?.mfa_enabled === true;

  // The section label is always rendered — a settings row that collapses to "Loading…"
  // hides what the section even is, and only the state below it actually depends on the
  // request. Everything past this point is gated on having a status.
  const subtitle = isLoading
    ? 'Checking…'
    : isError
      ? "Couldn't load two-factor status — retry in a moment."
      : enabled
        ? `Enabled · ${status?.remaining_backup_codes ?? 0} backup codes left`
        : 'Not enabled — sign-in uses your password only';

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
            Two-factor authentication
          </p>
          <p className="text-xs text-neutral-500 dark:text-neutral-400">{subtitle}</p>
        </div>
        <span
          className={`rounded-full px-2 py-0.5 text-xs font-medium ${
            enabled
              ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300'
              : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400'
          }`}
        >
          {isLoading || isError ? '—' : enabled ? 'On' : 'Off'}
        </span>
      </div>

      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}

      {/* Freshly regenerated codes take over the panel until acknowledged. */}
      {freshCodes && <BackupCodes codes={freshCodes} onDone={() => setFreshCodes(null)} />}

      {enrollment && (
        <EnrollmentFlow
          enrollment={enrollment}
          onCancel={() => setEnrollment(null)}
          onActivated={() => {
            setEnrollment(null);
            refresh();
          }}
        />
      )}

      {/* Actions need a known state — offering "set up" while the status is still
          loading would also offer it to someone who already has MFA on. */}
      {status && !enrollment && !enabled && (
        <button
          type="button"
          onClick={() => startEnrollment.mutate()}
          disabled={startEnrollment.isPending}
          className={BTN_SECONDARY + ' w-full'}
        >
          {startEnrollment.isPending ? 'Preparing…' : 'Set up two-factor authentication'}
        </button>
      )}

      {enabled && mode === 'idle' && !freshCodes && (
        <div className="flex gap-2">
          <button type="button" onClick={() => setMode('regenerating')} className={BTN_SECONDARY}>
            Regenerate backup codes
          </button>
          {status?.mfa_enforced ? (
            <p className="self-center text-xs text-neutral-500 dark:text-neutral-400">
              Required by your administrator — this can't be turned off.
            </p>
          ) : (
            <button type="button" onClick={() => setMode('disabling')} className={BTN_SECONDARY}>
              Turn off
            </button>
          )}
        </div>
      )}

      {mode === 'regenerating' && (
        <RegenerateForm
          onCancel={() => setMode('idle')}
          onCodes={(codes) => {
            setMode('idle');
            setFreshCodes(codes);
            refresh();
          }}
        />
      )}

      {mode === 'disabling' && (
        <DisableForm
          onCancel={() => setMode('idle')}
          onDisabled={() => {
            setMode('idle');
            refresh();
          }}
        />
      )}
    </div>
  );
}
