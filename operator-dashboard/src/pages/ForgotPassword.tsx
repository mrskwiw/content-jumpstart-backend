import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { authApi } from '@/api/auth';
import { getAuthErrorMessage } from '@/utils/errorMessages';
import { Button, Input, Alert, AlertDescription } from '@/components/ui';
import { ROUTES } from '@/config/routes';

/**
 * Self-service "forgot password" request page (GAP-AUTH-01).
 *
 * On submit we always show the same generic confirmation — the backend never
 * reveals whether the email maps to an account, so neither does this page.
 */
export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);
    try {
      await authApi.forgotPassword(email);
      setSubmitted(true);
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
            Reset your password
          </h2>
          <p className="mt-2 text-center text-sm text-neutral-600 dark:text-neutral-400">
            {submitted
              ? 'Check your inbox'
              : "Enter your account email and we'll send a reset link"}
          </p>
        </div>

        {submitted ? (
          <div className="space-y-6">
            <Alert variant="success">
              <AlertDescription>
                If an account exists for <strong>{email}</strong>, a password reset link is on
                its way. The link expires in 30 minutes and can only be used once.
              </AlertDescription>
            </Alert>
            <Button
              type="button"
              variant="primary"
              className="w-full"
              onClick={() => navigate(ROUTES.LOGIN)}
            >
              Back to sign in
            </Button>
          </div>
        ) : (
          <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
            {error && (
              <Alert variant="danger">
                <AlertDescription>{error}</AlertDescription>
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
              disabled={isLoading}
              loading={isLoading}
              className="w-full"
            >
              {isLoading ? 'Sending...' : 'Send reset link'}
            </Button>

            <button
              type="button"
              className="w-full text-center text-sm text-neutral-500 dark:text-neutral-400 hover:underline"
              onClick={() => navigate(ROUTES.LOGIN)}
            >
              Back to sign in
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
