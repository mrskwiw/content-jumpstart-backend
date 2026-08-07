import { useEffect, useRef, useState, type FormEvent } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { authApi } from '@/api/auth';
import { getAuthErrorMessage } from '@/utils/errorMessages';
import { Button, Input, Alert, AlertDescription } from '@/components/ui';
import { ROUTES } from '@/config/routes';

type Status = 'verifying' | 'success' | 'error';

/**
 * Landing page for the emailed verification link (GAP-AUTH-02).
 *
 * Reads the `?token=` from the `/verify-email` link and confirms the account on
 * mount. On failure (missing / expired / invalid token) it offers to resend a
 * fresh link — always with a generic, no-enumeration confirmation.
 */
export default function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') ?? '';
  const navigate = useNavigate();

  // `?email=` (no token) means Login sent the user here after refusing an unverified
  // sign-in — not a broken link, so say what actually happened.
  const emailParam = searchParams.get('email') ?? '';
  const [status, setStatus] = useState<Status>(token ? 'verifying' : 'error');
  const [error, setError] = useState(() => {
    if (token) return '';
    return emailParam
      ? 'Your email address needs to be verified before you can sign in.'
      : 'This verification link is missing or malformed.';
  });

  // Resend sub-form state. Login sends the address along (`?email=`) when it refuses an
  // unverified sign-in, so the user doesn't retype it; the resend response is generic
  // either way, so a prefilled address discloses nothing.
  const [email, setEmail] = useState(emailParam);
  const [resendSubmitted, setResendSubmitted] = useState(false);
  const [resendError, setResendError] = useState('');
  const [resending, setResending] = useState(false);

  // Guard against the effect firing twice (React 18 StrictMode double-mount); the
  // backend is idempotent, but a single call keeps the state transitions clean.
  const verifiedRef = useRef(false);
  useEffect(() => {
    if (!token || verifiedRef.current) return;
    verifiedRef.current = true;
    authApi
      .verifyEmail(token)
      .then(() => setStatus('success'))
      .catch((err: unknown) => {
        setStatus('error');
        setError(getAuthErrorMessage(err));
      });
  }, [token]);

  const handleResend = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setResendError('');
    setResending(true);
    try {
      await authApi.resendVerification(email);
      setResendSubmitted(true);
    } catch (err: unknown) {
      setResendError(getAuthErrorMessage(err));
    } finally {
      setResending(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-neutral-50 dark:bg-neutral-950">
      <div className="max-w-md w-full space-y-8 p-8 bg-white dark:bg-neutral-900 rounded-lg shadow-lg border border-neutral-200 dark:border-neutral-700">
        <div>
          <div className="mx-auto h-12 w-12 rounded-lg bg-primary-500 text-primary-50 flex items-center justify-center font-bold text-xl mb-4">
            O
          </div>
          <h2 className="text-center text-3xl font-bold text-neutral-900 dark:text-neutral-100">
            Verify your email
          </h2>
        </div>

        {status === 'verifying' && (
          <p className="text-center text-sm text-neutral-600 dark:text-neutral-400">
            Confirming your email address…
          </p>
        )}

        {status === 'success' && (
          <div className="space-y-6">
            <Alert variant="success">
              <AlertDescription>
                Your email address is verified. You can now sign in.
              </AlertDescription>
            </Alert>
            <Button
              type="button"
              variant="primary"
              className="w-full"
              onClick={() => navigate(ROUTES.LOGIN)}
            >
              Go to sign in
            </Button>
          </div>
        )}

        {status === 'error' && (
          <div className="space-y-6">
            <Alert variant="danger">
              <AlertDescription>
                {error || 'This verification link is invalid or has expired.'}
              </AlertDescription>
            </Alert>

            {resendSubmitted ? (
              <Alert variant="success">
                <AlertDescription>
                  If an account exists for <strong>{email}</strong> and still needs verification, a
                  new link is on its way.
                </AlertDescription>
              </Alert>
            ) : (
              <form className="space-y-4" onSubmit={handleResend}>
                <p className="text-sm text-neutral-600 dark:text-neutral-400">
                  Enter your account email to get a fresh verification link.
                </p>
                {resendError && (
                  <Alert variant="danger">
                    <AlertDescription>{resendError}</AlertDescription>
                  </Alert>
                )}
                <Input
                  id="email"
                  type="email"
                  label="Email address"
                  required
                  autoFocus
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                />
                <Button
                  type="submit"
                  variant="primary"
                  disabled={resending}
                  loading={resending}
                  className="w-full"
                >
                  {resending ? 'Sending...' : 'Resend verification link'}
                </Button>
              </form>
            )}

            <button
              type="button"
              className="w-full text-center text-sm text-neutral-500 dark:text-neutral-400 hover:underline"
              onClick={() => navigate(ROUTES.LOGIN)}
            >
              Back to sign in
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
