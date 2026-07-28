import { useState, type FormEvent } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Eye, EyeOff } from 'lucide-react';
import { authApi } from '@/api/auth';
import { getAuthErrorMessage } from '@/utils/errorMessages';
import { Button, Input, Alert, AlertDescription } from '@/components/ui';
import { ROUTES } from '@/config/routes';

/**
 * Completes a self-service password reset (GAP-AUTH-01).
 *
 * Reads the single-use token from the `?token=` query param (delivered by
 * email), validates the new password client-side against the same rules the
 * backend enforces, then calls /auth/reset-password.
 */
function passwordProblem(pw: string): string | null {
  if (pw.length < 8) return 'Password must be at least 8 characters.';
  if (!/[A-Z]/.test(pw)) return 'Password must contain an uppercase letter.';
  if (!/[a-z]/.test(pw)) return 'Password must contain a lowercase letter.';
  if (!/[0-9]/.test(pw)) return 'Password must contain a digit.';
  return null;
}

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') ?? '';

  const [newPassword, setNewPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError('');

    const problem = passwordProblem(newPassword);
    if (problem) {
      setError(problem);
      return;
    }
    if (newPassword !== confirm) {
      setError('Passwords do not match.');
      return;
    }

    setIsLoading(true);
    try {
      await authApi.resetPassword(token, newPassword);
      setDone(true);
    } catch (err: unknown) {
      setError(getAuthErrorMessage(err));
    } finally {
      setIsLoading(false);
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
            Choose a new password
          </h2>
        </div>

        {done ? (
          <div className="space-y-6">
            <Alert variant="success">
              <AlertDescription>
                Your password has been updated. You can now sign in with your new password.
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
        ) : !token ? (
          <div className="space-y-6">
            <Alert variant="danger">
              <AlertDescription>
                This reset link is missing or malformed. Please request a new one.
              </AlertDescription>
            </Alert>
            <Button
              type="button"
              variant="primary"
              className="w-full"
              onClick={() => navigate(ROUTES.FORGOT_PASSWORD)}
            >
              Request a new link
            </Button>
          </div>
        ) : (
          <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
            {error && (
              <Alert variant="danger">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <div>
              <label
                htmlFor="new-password"
                className="block text-sm font-medium text-neutral-900 dark:text-neutral-100 mb-1"
              >
                New password
              </label>
              <div className="relative">
                <input
                  id="new-password"
                  type={showPassword ? 'text' : 'password'}
                  required
                  autoFocus
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full rounded-md border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-3 py-2 pr-10 text-sm text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200 transition-colors"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">
                At least 8 characters, with an uppercase letter, a lowercase letter, and a digit.
              </p>
            </div>

            <Input
              id="confirm-password"
              type={showPassword ? 'text' : 'password'}
              label="Confirm new password"
              required
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              placeholder="••••••••"
            />

            <Button
              type="submit"
              variant="primary"
              disabled={isLoading}
              loading={isLoading}
              className="w-full"
            >
              {isLoading ? 'Updating...' : 'Update password'}
            </Button>
          </form>
        )}
      </div>
    </div>
  );
}
