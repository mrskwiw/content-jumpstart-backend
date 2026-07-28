import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { creditsApi } from '@/api/credits';
import { stripeApi } from '@/api/stripe';
import { adminApi } from '@/api/admin';
import type { User as AdminUser } from '@/api/admin';
import type { ApiError } from '@/types/api-types';
import {
  Coins, CreditCard, CheckCircle, AlertCircle, RefreshCw,
  ArrowUpRight, ArrowDownRight, Gift, X,
} from 'lucide-react';

// Version of the Terms/Refund copy the buyer is accepting at checkout. Bump when
// the legal pages' "Last updated" date changes so consent records stay meaningful.
const LEGAL_CONSENT_VERSION = '2026-07-27';

function GrantCreditsModal({
  isOpen, onClose, users, form, onFormChange, onSubmit, isSubmitting, error,
}: {
  isOpen: boolean;
  onClose: () => void;
  users: AdminUser[];
  form: { user_id: string; credits: number; reason: string };
  onFormChange: (field: string, value: string | number) => void;
  onSubmit: () => void;
  isSubmitting: boolean;
  error: string | null;
}) {
  if (!isOpen) return null;
  const selectedUser = users.find(u => u.id === form.user_id);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40 dark:bg-black/60 px-4">
      <div className="w-full max-w-md rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6 shadow-xl">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 flex items-center gap-2">
              <Gift className="h-5 w-5 text-primary-600 dark:text-primary-400" />
              Grant Free Credits
            </h3>
            <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">🔒 Super Admin Only - Logged for audit</p>
          </div>
          <button onClick={onClose} disabled={isSubmitting} className="rounded-lg p-2 text-neutral-400 dark:text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-800 hover:text-neutral-600 dark:hover:text-neutral-300 disabled:opacity-50"><X className="h-5 w-5" /></button>
        </div>

        {error && (
          <div className="mb-4 rounded-lg border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 p-3">
            <div className="flex gap-2">
              <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
            </div>
          </div>
        )}

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">Select User *</label>
            <select value={form.user_id} onChange={e => onFormChange('user_id', e.target.value)} disabled={isSubmitting} className="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-3 py-2 text-sm text-neutral-900 dark:text-neutral-100 focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-500/20 dark:focus:ring-primary-400/20 disabled:opacity-50">
              <option value="">-- Select a user --</option>
              {users.map(u => <option key={u.id} value={u.id}>{u.email} - {u.fullName}</option>)}
            </select>
            {selectedUser && <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-1">Active: {selectedUser.isActive ? '✅ Yes' : '❌ No'} • Admin: {selectedUser.isSuperuser ? '👑 Yes' : 'No'}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">Credits to Grant * (1-10,000)</label>
            <input type="number" min="1" max="10000" value={form.credits} onChange={e => onFormChange('credits', parseInt(e.target.value) || 0)} disabled={isSubmitting} className="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-3 py-2 text-sm text-neutral-900 dark:text-neutral-100 focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-500/20 dark:focus:ring-primary-400/20 disabled:opacity-50" placeholder="1000" />
          </div>

          <div>
            <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">Reason * (Required for audit trail)</label>
            <textarea value={form.reason} onChange={e => onFormChange('reason', e.target.value)} disabled={isSubmitting} rows={3} maxLength={500} className="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-3 py-2 text-sm text-neutral-900 dark:text-neutral-100 focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-500/20 dark:focus:ring-primary-400/20 disabled:opacity-50 resize-none" placeholder="e.g., Beta tester reward, compensation for downtime, promotional campaign" />
            <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-1">{form.reason.length}/500 characters</p>
          </div>

          <div className="rounded-lg border border-primary-200 dark:border-primary-700 bg-primary-50 dark:bg-primary-900/20 p-3">
            <p className="text-xs font-medium text-primary-900 dark:text-primary-100 mb-1">Common Use Cases:</p>
            <ul className="text-xs text-primary-700 dark:text-primary-300 space-y-1">
              <li>• Beta testing participant reward</li>
              <li>• Service downtime compensation</li>
              <li>• Marketing promotion / early adopter bonus</li>
              <li>• Customer support case resolution</li>
            </ul>
          </div>
        </div>

        <div className="flex gap-3 mt-6">
          <button onClick={onClose} disabled={isSubmitting} className="flex-1 rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-4 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700 disabled:opacity-50">Cancel</button>
          <button onClick={onSubmit} disabled={!form.user_id || !form.credits || form.credits < 1 || form.credits > 10000 || !form.reason.trim() || isSubmitting} className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg bg-primary-600 dark:bg-primary-500 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 dark:hover:bg-primary-600 disabled:opacity-50">
            {isSubmitting ? <><RefreshCw className="h-4 w-4 animate-spin" />Granting...</> : <><Gift className="h-4 w-4" />Grant {form.credits} Credits</>}
          </button>
        </div>
      </div>
    </div>
  );
}

interface Props {
  isSuperAdmin: boolean;
}

export function CreditsTab({ isSuperAdmin }: Props) {
  const queryClient = useQueryClient();
  const [showGrantCreditsModal, setShowGrantCreditsModal] = useState(false);
  const [grantCreditsForm, setGrantCreditsForm] = useState({ user_id: '', credits: 1000, reason: '' });
  const [grantCreditsError, setGrantCreditsError] = useState<string | null>(null);
  // Refund-policy acknowledgement gates checkout (enforceability of "no refunds
  // once generation begins" — see /refund).
  const [refundAck, setRefundAck] = useState(false);

  const { data: creditBalance } = useQuery({ queryKey: ['credits', 'balance'], queryFn: () => creditsApi.getBalance() });
  const { data: creditPackages = [] } = useQuery({ queryKey: ['credits', 'packages'], queryFn: () => creditsApi.getPackages() });
  const { data: creditTransactions = [] } = useQuery({ queryKey: ['credits', 'transactions'], queryFn: () => creditsApi.getTransactions(50, 0) });
  const { data: paymentHistory = [] } = useQuery({ queryKey: ['stripe', 'payments'], queryFn: () => stripeApi.getPayments() });
  const { data: allUsers = [] } = useQuery({ queryKey: ['admin', 'users'], queryFn: () => adminApi.listUsers({ limit: 100 }), enabled: isSuperAdmin && showGrantCreditsModal });

  const grantCreditsMutation = useMutation({
    mutationFn: adminApi.grantCredits,
    onSuccess: data => {
      queryClient.invalidateQueries({ queryKey: ['credits', 'balance'] });
      queryClient.invalidateQueries({ queryKey: ['credits', 'transactions'] });
      setShowGrantCreditsModal(false);
      setGrantCreditsForm({ user_id: '', credits: 1000, reason: '' });
      setGrantCreditsError(null);
      alert(`Successfully granted ${data.credits_granted} credits to ${data.user_email}`);
    },
    onError: (error: unknown) => {
      setGrantCreditsError((error as ApiError).response?.data?.detail || (error as Error).message || 'Failed to grant credits');
    },
  });

  return (
    <>
      <div className="space-y-4">
        {/* Current Balance */}
        <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
          <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-4">Credit Balance</h3>
          {creditBalance ? (
            <div className="space-y-4">
              <div className="flex items-center gap-4">
                <div className="rounded-full bg-yellow-100 dark:bg-yellow-900/20 p-4"><Coins className="h-8 w-8 text-yellow-600 dark:text-yellow-400" /></div>
                <div>
                  <p className="text-3xl font-bold text-neutral-900 dark:text-neutral-100">{creditBalance.balance.toLocaleString()}</p>
                  <p className="text-sm text-neutral-600 dark:text-neutral-400">Available Credits</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4 pt-4 border-t border-neutral-200 dark:border-neutral-700">
                <div><p className="text-sm text-neutral-600 dark:text-neutral-400">Total Purchased</p><p className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">{creditBalance.total_purchased.toLocaleString()}</p></div>
                <div><p className="text-sm text-neutral-600 dark:text-neutral-400">Total Used</p><p className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">{creditBalance.total_used.toLocaleString()}</p></div>
              </div>
              {creditBalance.is_enterprise && (
                <div className="rounded-lg border border-primary-200 dark:border-primary-700 bg-primary-50 dark:bg-primary-900/20 p-3">
                  <div className="flex gap-2">
                    <CheckCircle className="h-4 w-4 text-primary-600 dark:text-primary-400 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-primary-900 dark:text-primary-100">Enterprise Account</p>
                      <p className="text-sm text-primary-700 dark:text-primary-300 mt-1">You have a custom credit rate: ${(creditBalance.custom_credit_rate ?? 0.1).toFixed(3)} per credit</p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-sm text-neutral-600 dark:text-neutral-400">Loading balance...</div>
          )}
          {isSuperAdmin && (
            <div className="mt-4 pt-4 border-t border-neutral-200 dark:border-neutral-700">
              <button onClick={() => setShowGrantCreditsModal(true)} className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-primary-600 dark:bg-primary-500 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 dark:hover:bg-primary-600 transition-colors">
                <Gift className="h-4 w-4" />Grant Free Credits to User
              </button>
              <p className="text-xs text-neutral-500 dark:text-neutral-400 text-center mt-2">🔒 Super Admin Only - Visible only to original system administrators</p>
            </div>
          )}
        </div>

        {/* Credit Packages */}
        <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
          <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-4">Purchase Credits</h3>

          {/* Refund notice + required acknowledgement (gates checkout) */}
          <div className="mb-4 rounded-lg border border-amber-200 dark:border-amber-900/40 bg-amber-50 dark:bg-amber-900/10 p-3">
            <p className="text-xs text-amber-800 dark:text-amber-300">
              Credits are non-refundable once content generation or research begins. Please
              review our{' '}
              <a href="/refund" target="_blank" rel="noopener noreferrer" className="font-medium underline hover:no-underline">Refund Policy</a>{' '}
              and{' '}
              <a href="/terms" target="_blank" rel="noopener noreferrer" className="font-medium underline hover:no-underline">Terms of Service</a>.
            </p>
            <label className="mt-2 flex items-start gap-2 text-xs text-neutral-700 dark:text-neutral-300 cursor-pointer">
              <input
                type="checkbox"
                checked={refundAck}
                onChange={e => setRefundAck(e.target.checked)}
                className="mt-0.5 h-4 w-4 rounded border-neutral-300 dark:border-neutral-600 text-primary-600 focus:ring-primary-500"
              />
              <span>I understand credits are non-refundable once generation begins, and I agree to the Refund Policy and Terms of Service.</span>
            </label>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {creditPackages.map(pkg => (
              <div key={pkg.id} className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800 p-4 hover:border-primary-400 dark:hover:border-primary-600 transition-colors">
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <h4 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">{pkg.name}</h4>
                    {pkg.description && <p className="text-xs text-neutral-600 dark:text-neutral-400 mt-1">{pkg.description}</p>}
                  </div>
                  {pkg.rate_per_credit < 0.1 && <span className="inline-flex items-center rounded-md bg-green-100 dark:bg-green-900/20 px-2 py-1 text-xs font-medium text-green-700 dark:text-green-400">Best Value</span>}
                </div>
                <div className="mb-4">
                  <p className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">{pkg.credits.toLocaleString()} credits</p>
                  <p className="text-sm text-neutral-600 dark:text-neutral-400">${pkg.price_usd.toFixed(2)} (${pkg.rate_per_credit.toFixed(3)}/credit)</p>
                </div>
                <button disabled={!refundAck} title={!refundAck ? 'Please acknowledge the Refund Policy above to continue' : undefined} onClick={async () => { if (!refundAck) return; try { const origin = window.location.origin; const result = await stripeApi.createCheckoutSession({ package_id: pkg.id, success_url: `${origin}/payment-success?session_id={CHECKOUT_SESSION_ID}`, cancel_url: `${origin}/dashboard/settings?tab=credits`, accepted_terms: refundAck, consent_version: LEGAL_CONSENT_VERSION }); window.location.href = result.checkout_url; } catch { alert('Failed to start checkout. Please try again.'); } }} className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-primary-600 dark:bg-primary-500 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 dark:hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed">
                  <CreditCard className="h-4 w-4" />Purchase
                </button>
              </div>
            ))}
          </div>
          {creditPackages.length === 0 && <div className="text-sm text-neutral-600 dark:text-neutral-400 text-center py-8">No credit packages available. Contact support for custom pricing.</div>}
        </div>

        {/* Payment History */}
        <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">Payment History</h3>
            <button onClick={async () => { try { const url = await stripeApi.getBillingPortalUrl(`${window.location.origin}/dashboard/settings?tab=credits`); window.location.href = url; } catch { alert('Unable to open billing portal. Please try again.'); } }} className="inline-flex items-center gap-2 rounded-lg border border-neutral-300 dark:border-neutral-600 px-3 py-1.5 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800">
              <CreditCard className="h-4 w-4" />Manage Billing
            </button>
          </div>
          {paymentHistory.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead><tr className="border-b border-neutral-200 dark:border-neutral-700"><th className="text-left py-3 px-2 text-xs font-medium text-neutral-600 dark:text-neutral-400 uppercase tracking-wider">Date</th><th className="text-left py-3 px-2 text-xs font-medium text-neutral-600 dark:text-neutral-400 uppercase tracking-wider">Amount</th><th className="text-left py-3 px-2 text-xs font-medium text-neutral-600 dark:text-neutral-400 uppercase tracking-wider">Credits</th><th className="text-left py-3 px-2 text-xs font-medium text-neutral-600 dark:text-neutral-400 uppercase tracking-wider">Status</th></tr></thead>
                <tbody>
                  {paymentHistory.map(payment => (
                    <tr key={payment.id} className="border-b border-neutral-100 dark:border-neutral-800 hover:bg-neutral-50 dark:hover:bg-neutral-800/50">
                      <td className="py-3 px-2 text-sm text-neutral-900 dark:text-neutral-100">{new Date(payment.created_at).toLocaleDateString()}</td>
                      <td className="py-3 px-2 text-sm text-neutral-900 dark:text-neutral-100">{payment.amount_usd != null ? `$${payment.amount_usd.toFixed(2)}` : '—'}</td>
                      <td className="py-3 px-2 text-sm text-neutral-900 dark:text-neutral-100">{payment.credits != null ? payment.credits.toLocaleString() : '—'}</td>
                      <td className="py-3 px-2"><span className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ${payment.status === 'completed' ? 'bg-green-100 dark:bg-green-900/20 text-green-700 dark:text-green-400' : payment.status === 'pending' ? 'bg-yellow-100 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-400' : 'bg-red-100 dark:bg-red-900/20 text-red-700 dark:text-red-400'}`}>{payment.status.charAt(0).toUpperCase() + payment.status.slice(1)}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : <div className="text-sm text-neutral-600 dark:text-neutral-400 text-center py-8">No payment history yet.</div>}
        </div>

        {/* Transaction History */}
        <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
          <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-4">Transaction History</h3>
          {creditTransactions.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead><tr className="border-b border-neutral-200 dark:border-neutral-700"><th className="text-left py-3 px-2 text-xs font-medium text-neutral-600 dark:text-neutral-400 uppercase tracking-wider">Date</th><th className="text-left py-3 px-2 text-xs font-medium text-neutral-600 dark:text-neutral-400 uppercase tracking-wider">Type</th><th className="text-left py-3 px-2 text-xs font-medium text-neutral-600 dark:text-neutral-400 uppercase tracking-wider">Description</th><th className="text-right py-3 px-2 text-xs font-medium text-neutral-600 dark:text-neutral-400 uppercase tracking-wider">Amount</th></tr></thead>
                <tbody>
                  {creditTransactions.map(transaction => (
                    <tr key={transaction.id} className="border-b border-neutral-100 dark:border-neutral-800 hover:bg-neutral-50 dark:hover:bg-neutral-800/50">
                      <td className="py-3 px-2 text-sm text-neutral-900 dark:text-neutral-100">{new Date(transaction.created_at).toLocaleDateString()}</td>
                      <td className="py-3 px-2"><span className={`inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium ${transaction.transaction_type === 'purchase' ? 'bg-green-100 dark:bg-green-900/20 text-green-700 dark:text-green-400' : transaction.transaction_type === 'deduction' ? 'bg-red-100 dark:bg-red-900/20 text-red-700 dark:text-red-400' : transaction.transaction_type === 'refund' ? 'bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400' : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300'}`}>{transaction.transaction_type === 'purchase' && <ArrowUpRight className="h-3 w-3" />}{transaction.transaction_type === 'deduction' && <ArrowDownRight className="h-3 w-3" />}{transaction.transaction_type === 'refund' && <ArrowUpRight className="h-3 w-3" />}{transaction.transaction_type.charAt(0).toUpperCase() + transaction.transaction_type.slice(1)}</span></td>
                      <td className="py-3 px-2 text-sm text-neutral-600 dark:text-neutral-400">{transaction.description}</td>
                      <td className="py-3 px-2 text-right"><span className={`text-sm font-medium ${transaction.amount > 0 ? 'text-green-700 dark:text-green-400' : 'text-red-700 dark:text-red-400'}`}>{transaction.amount > 0 ? '+' : ''}{transaction.amount.toLocaleString()}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : <div className="text-sm text-neutral-600 dark:text-neutral-400 text-center py-8">No transactions yet. Purchase credits to get started.</div>}
        </div>
      </div>

      <GrantCreditsModal
        isOpen={showGrantCreditsModal}
        onClose={() => { setShowGrantCreditsModal(false); setGrantCreditsError(null); }}
        users={allUsers}
        form={grantCreditsForm}
        onFormChange={(field, value) => setGrantCreditsForm(prev => ({ ...prev, [field]: value }))}
        onSubmit={() => grantCreditsMutation.mutate(grantCreditsForm)}
        isSubmitting={grantCreditsMutation.isPending}
        error={grantCreditsError}
      />
    </>
  );
}
