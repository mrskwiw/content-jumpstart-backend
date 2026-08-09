/**
 * Subscribe — the terminus for an account with no live entitlement.
 *
 * Every gated endpoint answers 402 `account_expired`, and the axios interceptor
 * sends the user here regardless of which request tripped first. So this page must
 * stand on its own: it can only call allowlisted endpoints, and it must always
 * offer a way out (subscribe, export, sign out) rather than becoming a dead end.
 *
 * It deliberately does NOT assume the account is expired — an active user who
 * navigates here directly gets their real state and a link back.
 */
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { useState } from 'react';
import apiClient from '@/api/client';
// AppProviders wraps the whole router, so useAuth works here even though this page
// sits outside ProtectedRoute.
import { useAuth } from '@/contexts/AuthContext';

interface PlanOption {
  id: string;
  name: string;
  price_usd_month: number;
  monthly_credits: number;
  annual_price_usd: number;
}

interface AccountStatus {
  state: string;
  expired: boolean;
  spend_blocked: boolean;
  plan_id: string | null;
  plans: PlanOption[];
}

const SUPPORT_EMAIL = 'hello@content-jumpstart.com';

const money = (n: number) => `$${n.toLocaleString('en-US')}`;

export default function Subscribe() {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const [annual, setAnnual] = useState(false);

  const { data, isLoading, isError } = useQuery<AccountStatus>({
    queryKey: ['account', 'status'],
    queryFn: async () => (await apiClient.get('/api/account/status')).data,
    // This page is the fallback for a broken-entitlement state; retrying a failing
    // status call forever just spins a spinner at someone trying to give us money.
    retry: 1,
  });

  const expired = data?.expired ?? true;

  return (
    <div className="min-h-screen bg-neutral-50 dark:bg-neutral-950 px-4 py-12">
      <div className="mx-auto max-w-4xl">
        <header className="mb-10 text-center">
          <h1 className="text-3xl font-semibold text-neutral-900 dark:text-neutral-50">
            {expired ? 'Your subscription has ended' : 'Your subscription'}
          </h1>
          <p className="mt-3 text-neutral-600 dark:text-neutral-400">
            {expired
              ? 'Your work is safe and nothing has been deleted. Choose a plan to pick up where you left off.'
              : 'Your account is active. You can change your plan here at any time.'}
          </p>
          {isError && (
            <p className="mt-3 text-sm text-error-600">
              We could not load your account status. The options below are still correct —
              contact us if anything looks wrong.
            </p>
          )}
        </header>

        <div className="mb-8 flex items-center justify-center gap-3">
          <span className={!annual ? 'font-medium' : 'text-neutral-500'}>Monthly</span>
          <button
            type="button"
            role="switch"
            aria-checked={annual}
            aria-label="Bill annually"
            onClick={() => setAnnual((v) => !v)}
            className="relative h-6 w-11 rounded-full bg-neutral-300 dark:bg-neutral-700 transition-colors data-[on=true]:bg-primary-500"
            data-on={annual}
          >
            <span
              className="absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform"
              style={{ transform: annual ? 'translateX(1.375rem)' : 'translateX(0.125rem)' }}
            />
          </button>
          <span className={annual ? 'font-medium' : 'text-neutral-500'}>
            Annual <span className="text-success-600">(2 months free)</span>
          </span>
        </div>

        {isLoading ? (
          <p className="text-center text-neutral-500">Loading plans…</p>
        ) : (
          <div className="grid gap-6 md:grid-cols-3">
            {(data?.plans ?? []).map((plan) => (
              <div
                key={plan.id}
                className="rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 p-6 flex flex-col"
              >
                <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
                  {plan.name}
                </h2>
                <p className="mt-3 font-mono text-2xl text-neutral-900 dark:text-neutral-50">
                  {annual ? money(plan.annual_price_usd) : money(plan.price_usd_month)}
                  <span className="text-sm text-neutral-500">{annual ? '/yr' : '/mo'}</span>
                </p>
                <p className="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
                  {plan.monthly_credits.toLocaleString('en-US')} credits per month
                </p>
                <p className="mt-1 text-sm text-neutral-500">Every feature, on every plan.</p>
                <a
                  className="mt-6 inline-flex justify-center rounded bg-primary-500 px-4 py-2 text-white hover:bg-primary-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
                  href={`mailto:${SUPPORT_EMAIL}?subject=${encodeURIComponent(
                    `Subscribe: ${plan.name}${annual ? ' (annual)' : ''}`
                  )}`}
                >
                  Choose {plan.name}
                </a>
              </div>
            ))}
          </div>
        )}

        {/* Honest about the mechanism: there is no automated checkout yet, so do not
            render a button that implies one. */}
        <p className="mt-8 text-center text-sm text-neutral-600 dark:text-neutral-400">
          Subscriptions are set up by hand while we are in early access — normally within one
          business day. Choosing a plan opens an email to {SUPPORT_EMAIL}.
        </p>

        <div className="mt-10 flex flex-wrap items-center justify-center gap-4 text-sm">
          {/* Always available, expired or not: their content is theirs. */}
          <a className="underline" href="/api/privacy/export">
            Export your data
          </a>
          {!expired && (
            <button type="button" className="underline" onClick={() => navigate('/dashboard')}>
              Back to dashboard
            </button>
          )}
          <button type="button" className="underline" onClick={() => logout()}>
            Sign out
          </button>
        </div>
      </div>
    </div>
  );
}
