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
  gated: boolean;
  gate_reason: 'trial_ended' | 'credits_exhausted' | null;
  spend_blocked: boolean;
  credits_remaining: number;
  trial_ends_at: string | null;
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

  const gated = data?.gated ?? true;

  // The two triggers need different words: a trial that ran out of TIME and a
  // lapsed subscription that ran out of CREDITS are not the same situation, and
  // "your subscription has ended" is simply false for the first one.
  const heading =
    data?.gate_reason === 'trial_ended'
      ? 'Your free trial has ended'
      : data?.gate_reason === 'credits_exhausted'
        ? 'You have used all your credits'
        : gated
          ? 'Choose a plan to continue'
          : 'Your subscription';

  const blurb =
    data?.gate_reason === 'trial_ended'
      ? 'Your 30 days are up. Nothing has been charged and nothing has been deleted — choose a plan to pick up exactly where you left off.'
      : data?.gate_reason === 'credits_exhausted'
        ? 'Your subscription has ended and the credits you had left are now used up. Your work is safe; choose a plan to start generating again.'
        : gated
          ? 'Choose a plan to continue. Your work is safe and nothing has been deleted.'
          : 'Your account is active. You can change your plan here at any time.';

  return (
    <div className="min-h-screen bg-neutral-50 dark:bg-neutral-950 px-4 py-12">
      <div className="mx-auto max-w-4xl">
        <header className="mb-10 text-center">
          <h1 className="text-3xl font-semibold text-neutral-900 dark:text-neutral-50">
            {heading}
          </h1>
          <p className="mt-3 text-neutral-600 dark:text-neutral-400">{blurb}</p>
          {/* Credits outlive a lapsed subscription, so a non-zero balance here is
              worth stating — it is the customer's, and it explains why they still
              had access after the subscription ended. */}
          {!gated && (data?.credits_remaining ?? 0) > 0 && (
            <p className="mt-2 font-mono text-sm text-neutral-500">
              {data!.credits_remaining.toLocaleString('en-US')} credits remaining
            </p>
          )}
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
          {!gated && (
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
