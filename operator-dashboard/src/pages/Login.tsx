import { useState, useEffect, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { Eye, EyeOff } from 'lucide-react';
import axios from 'axios';
import { useAuth } from '@/contexts/AuthContext';
import { getAuthErrorMessage } from '@/utils/errorMessages';
import { Button, Input, Alert, AlertDescription } from '@/components/ui';
import { ROUTES } from '@/config/routes';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [totpCode, setTotpCode] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [mfaRequired, setMfaRequired] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const { login, isAuthenticated, isLoading: authLoading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      navigate(ROUTES.PORTFOLIO_NOTICE, { replace: true });
    }
  }, [isAuthenticated, authLoading, navigate]);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await login({ email, password, totp_code: mfaRequired ? totpCode : undefined });
      navigate(ROUTES.PORTFOLIO_NOTICE, { replace: true });
    } catch (err: unknown) {
      // Backend signals MFA is required with 401 "MFA code required" — transition
      // to the TOTP step rather than treating it as a login failure.
      if (
        axios.isAxiosError(err) &&
        err.response?.data?.detail === 'MFA code required'
      ) {
        setMfaRequired(true);
        setTotpCode('');
      } else {
        setError(getAuthErrorMessage(err));
        console.error('Login failed', err);
      }
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
            Operator Dashboard
          </h2>
          <p className="mt-2 text-center text-sm text-neutral-600 dark:text-neutral-400">
            {mfaRequired ? 'Enter your authenticator code' : 'Sign in to your account'}
          </p>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <Alert variant="danger">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <div className="space-y-4">
            {!mfaRequired ? (
              <>
                <Input
                  id="email"
                  type="email"
                  label="Email address"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                />

                <div>
                  <label htmlFor="password" className="block text-sm font-medium text-neutral-900 dark:text-neutral-100 mb-1">
                    Password
                  </label>
                  <div className="relative">
                    <input
                      id="password"
                      type={showPassword ? 'text' : 'password'}
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      className="w-full rounded-md border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-3 py-2 pr-10 text-sm text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200 transition-colors"
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                    >
                      {showPassword ? (
                        <EyeOff className="h-4 w-4" />
                      ) : (
                        <Eye className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                </div>
              </>
            ) : (
              <div>
                <Input
                  id="totp"
                  type="text"
                  label="Authenticator code"
                  required
                  autoFocus
                  inputMode="numeric"
                  maxLength={6}
                  value={totpCode}
                  onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ''))}
                  placeholder="000000"
                />
                <button
                  type="button"
                  className="mt-2 text-xs text-neutral-500 dark:text-neutral-400 hover:underline"
                  onClick={() => { setMfaRequired(false); setError(''); }}
                >
                  Back to sign in
                </button>
              </div>
            )}
          </div>

          <Button
            type="submit"
            variant="primary"
            disabled={isLoading}
            loading={isLoading}
            className="w-full"
          >
            {isLoading ? 'Signing in...' : mfaRequired ? 'Verify code' : 'Sign in'}
          </Button>
        </form>
      </div>

      <footer className="mt-6 text-center text-xs text-neutral-500 dark:text-neutral-400">
        <a href="/terms" className="hover:underline">Terms</a>
        {' · '}
        <a href="/privacy" className="hover:underline">Privacy</a>
        {' · '}
        <a href="/refund" className="hover:underline">Refund Policy</a>
      </footer>
    </div>
  );
}
