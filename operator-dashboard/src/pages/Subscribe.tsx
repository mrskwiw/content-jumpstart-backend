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
import { useMutation, useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { useState } from 'react';
import apiClient from '@/api/client';
// AppProviders wraps the whole router, so useAuth works here even though this page
// sits outside ProtectedRoute.
import { useAuth } from '@/contexts/AuthContext';

interface CreditPackage {
  id: string;
  name: string;
  credits: number;
  price_usd: number;
}

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

  const [termsAccepted, setTermsAccepted] = useState(false);
  const [buying, setBuying] = useState<string | null>(null);
  const [buyError, setBuyError] = useState<string | null>(null);

  const { data, isLoading, isError } = useQuery<AccountStatus>({
    queryKey: ['account', 'status'],
    queryFn: async () => (await apiClient.get('/api/account/status')).data,
    // This page is the fallback for a broken-entitlement state; retrying a failing
    // status call forever just spins a spinner at someone trying to give us money.
    retry: 1,
  });

  // Both /api/credits and /api/stripe are on the gate's allowlist — deliberately,
  // since gating the endpoints that SELL access would make the lockout permanent.
  const packagesQuery = useQuery<CreditPackage[]>({
    queryKey: ['credits', 'packages'],
    queryFn: async () => (await apiClient.get('/api/credits/packages')).data,
    retry: 1,
  });
  const packages = packagesQuery.data ?? [];

  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState('');
  const [dataError, setDataError] = useState<string | null>(null);

  const exportData = useMutation({
    mutationFn: async () => {
      setDataError(null);
      // Must go through apiClient, not a plain <a href>: the export needs the
      // bearer token, which a browser navigation would not send.
      const { data: payload } = await apiClient.get('/api/privacy/account/export');
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'content-jumpstart-account-export.json';
      a.click();
      URL.revokeObjectURL(url);
    },
    onError: () => setDataError('Could not prepare your export. Please contact support.'),
  });

  const deleteAccount = useMutation({
    mutationFn: async () => {
      setDataError(null);
      await apiClient.delete('/api/privacy/account');
    },
    onSuccess: () => logout(),
    onError: (err: unknown) => {
      // The backend refuses to delete the last active administrator; surface that
      // reason rather than a generic failure.
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setDataError(detail || 'Could not delete the account. Please contact support.');
    },
  });

  const buyCredits = useMutation({
    mutationFn: async (packageId: string) => {
      setBuying(packageId);
      setBuyError(null);
      const { data: session } = await apiClient.post('/api/stripe/checkout', {
        package_id: packageId,
        accepted_terms: true,
      });
      return session as { checkout_url: string };
    },
    onSuccess: ({ checkout_url }) => {
      window.location.href = checkout_url;
    },
    onError: () => {
      setBuying(null);
      // Stripe may not be configured on this instance yet. Say so and offer the
      // manual route rather than leaving a dead button.
      setBuyError('Card checkout is not available right now.');
    },
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
        ? 'This account has no credits left and no active subscription. Your work is safe and nothing has been deleted — choose a plan or top up to start generating again.'
        : gated
          ? 'This account has no credits left and no active subscription. Your work is safe and nothing has been deleted.'
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

        {/* Honest about the mechanism: there is no automated subscription checkout
            yet, so do not render a button that implies one. */}
        <p className="mt-8 text-center text-sm text-neutral-600 dark:text-neutral-400">
          Subscriptions are set up by hand while we are in early access — normally within one
          business day. Choosing a plan opens an email to {SUPPORT_EMAIL}.
        </p>

        {/* ── Top-up ────────────────────────────────────────────────────────────
            The other way out. Someone gated for an exhausted balance may want
            credits now rather than a subscription, and this path IS automated
            (Stripe Checkout for a credit package), so it gets real buttons. */}
        <section className="mt-14 border-t border-neutral-200 dark:border-neutral-800 pt-10">
          <h2 className="text-center text-xl font-semibold text-neutral-900 dark:text-neutral-50">
            Or just buy credits
          </h2>
          <p className="mt-2 text-center text-sm text-neutral-600 dark:text-neutral-400">
            A one-off top-up, no subscription. Credits you buy do not expire.
          </p>
          {/* State the rate difference plainly. It is the honest reason to prefer a
              plan, and a customer who finds out later that they overpaid 2x for the
              same credits has a fair complaint. */}
          <p className="mt-2 text-center text-sm text-neutral-500">
            Top-up credits cost <strong>$1 each</strong>. On a plan they are{' '}
            <strong>$0.50</strong> — half the price — so if you expect to keep
            generating, a subscription is the cheaper route.
          </p>

          {packagesQuery.isLoading && (
            <p className="mt-6 text-center text-neutral-500">Loading credit packages…</p>
          )}

          {/* No packages configured, or the catalogue failed to load: fall back to
              the manual route rather than showing an empty shelf. */}
          {!packagesQuery.isLoading && packages.length === 0 && (
            <p className="mt-6 text-center text-sm text-neutral-600 dark:text-neutral-400">
              <a className="underline" href={`mailto:${SUPPORT_EMAIL}?subject=Buy%20credits`}>
                Email us to buy credits
              </a>
            </p>
          )}

          {packages.length > 0 && (
            <>
              <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {packages.map((pkg) => (
                  <div
                    key={pkg.id}
                    className="rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 p-5"
                  >
                    <p className="font-medium text-neutral-900 dark:text-neutral-50">{pkg.name}</p>
                    <p className="mt-1 font-mono text-xl text-neutral-900 dark:text-neutral-50">
                      {money(pkg.price_usd)}
                    </p>
                    <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-400">
                      {pkg.credits.toLocaleString('en-US')} credits
                    </p>
                    <button
                      type="button"
                      disabled={!termsAccepted || buying === pkg.id}
                      onClick={() => buyCredits.mutate(pkg.id)}
                      className="mt-4 w-full rounded bg-primary-500 px-3 py-2 text-white hover:bg-primary-600 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {buying === pkg.id ? 'Opening checkout…' : `Buy ${pkg.name}`}
                    </button>
                  </div>
                ))}
              </div>

              {/* The backend rejects a purchase without this regardless of the
                  checkbox, so the control here mirrors a real server-side rule. */}
              <label className="mt-5 flex items-start justify-center gap-2 text-sm text-neutral-600 dark:text-neutral-400">
                <input
                  type="checkbox"
                  checked={termsAccepted}
                  onChange={(e) => setTermsAccepted(e.target.checked)}
                  className="mt-1"
                />
                <span>
                  I accept the Terms of Service and Refund Policy.
                </span>
              </label>

              {buyError && (
                <p className="mt-4 text-center text-sm text-error-600">
                  {buyError}{' '}
                  <a className="underline" href={`mailto:${SUPPORT_EMAIL}?subject=Buy%20credits`}>
                    Email us instead
                  </a>
                  .
                </p>
              )}
            </>
          )}
        </section>

        {/* ── Data rights ───────────────────────────────────────────────────────
            Reachable whatever the billing state: withholding someone's data
            because they stopped paying is hostile, and blocking erasure would let
            a billing state override a statutory right. Both endpoints sit on the
            entitlement gate's allowlist for exactly this reason. */}
        <section className="mt-14 border-t border-neutral-200 dark:border-neutral-800 pt-10">
          <h2 className="text-center text-xl font-semibold text-neutral-900 dark:text-neutral-50">
            Your data
          </h2>
          <p className="mt-2 text-center text-sm text-neutral-600 dark:text-neutral-400">
            Available whether or not you subscribe. GDPR Article 15 (access) and
            Article 17 (erasure).
          </p>
          <div className="mt-5 flex flex-wrap items-center justify-center gap-3">
            <button
              type="button"
              onClick={() => exportData.mutate()}
              disabled={exportData.isPending}
              className="rounded border border-neutral-300 dark:border-neutral-700 px-4 py-2 text-sm hover:bg-neutral-100 dark:hover:bg-neutral-800"
            >
              {exportData.isPending ? 'Preparing…' : 'Download my data'}
            </button>
            <button
              type="button"
              onClick={() => setConfirmDelete(true)}
              className="rounded border border-error-500 px-4 py-2 text-sm text-error-600 hover:bg-error-50 dark:hover:bg-neutral-800"
            >
              Delete my account
            </button>
          </div>

          {confirmDelete && (
            // Irreversible, so it takes a deliberate typed confirmation rather than
            // a second click that muscle memory can supply.
            <div className="mx-auto mt-5 max-w-md rounded-lg border border-error-500 p-4">
              <p className="text-sm text-neutral-700 dark:text-neutral-300">
                This deactivates your account and revokes every session. Clients and
                projects you created stay with the instance. Type <strong>DELETE</strong>{' '}
                to confirm.
              </p>
              <input
                value={deleteConfirmText}
                onChange={(e) => setDeleteConfirmText(e.target.value)}
                aria-label="Type DELETE to confirm"
                className="mt-3 w-full rounded border border-neutral-300 dark:border-neutral-700 bg-transparent px-3 py-2"
              />
              <div className="mt-3 flex gap-2">
                <button
                  type="button"
                  disabled={deleteConfirmText !== 'DELETE' || deleteAccount.isPending}
                  onClick={() => deleteAccount.mutate()}
                  className="rounded bg-error-600 px-4 py-2 text-sm text-white disabled:opacity-50"
                >
                  {deleteAccount.isPending ? 'Deleting…' : 'Permanently delete'}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setConfirmDelete(false);
                    setDeleteConfirmText('');
                  }}
                  className="rounded border border-neutral-300 dark:border-neutral-700 px-4 py-2 text-sm"
                >
                  Cancel
                </button>
              </div>
              {dataError && <p className="mt-3 text-sm text-error-600">{dataError}</p>}
            </div>
          )}
          {!confirmDelete && dataError && (
            <p className="mt-4 text-center text-sm text-error-600">{dataError}</p>
          )}
        </section>

        <div className="mt-10 flex flex-wrap items-center justify-center gap-4 text-sm">
          <a className="underline" href="/privacy">
            Privacy policy
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
