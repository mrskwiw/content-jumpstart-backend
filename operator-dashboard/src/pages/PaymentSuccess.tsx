import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { stripeApi } from '@/api/stripe';

export default function PaymentSuccess() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const sessionId = searchParams.get('session_id');
  const [timedOut, setTimedOut] = useState(false);

  const { data: status } = useQuery({
    queryKey: ['payment-status', sessionId],
    queryFn: () => stripeApi.getPaymentStatus(sessionId!),
    enabled: !!sessionId && !timedOut,
    refetchInterval: (query) =>
      query.state.data?.status === 'pending' ? 2000 : false,
  });

  // 30-second timeout
  useEffect(() => {
    const timer = setTimeout(() => setTimedOut(true), 30000);
    return () => clearTimeout(timer);
  }, []);

  // On completion, navigate back to wizard
  useEffect(() => {
    if (status?.status === 'completed') {
      const pending = sessionStorage.getItem('stripe_pending');
      sessionStorage.removeItem('stripe_pending');
      if (pending) {
        try {
          const { projectId, clientId } = JSON.parse(pending);
          navigate('/dashboard/wizard', {
            state: { projectId, clientId, step: 'quality' },
          });
          return;
        } catch {
          // ignore — malformed pending payload; fall through to default dashboard nav
        }
      }
      navigate('/dashboard');
    }
  }, [status?.status, navigate]);

  if (!sessionId) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-neutral-600 dark:text-neutral-400">Invalid payment link.</p>
      </div>
    );
  }

  if (status?.status === 'failed' || status?.status === 'expired') {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-semibold text-red-600 mb-2">Payment Failed</h1>
          <p className="text-neutral-600 dark:text-neutral-400 mb-4">
            Your payment was not completed. No credits were charged.
          </p>
          <button
            onClick={() => navigate(-1)}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  if (timedOut) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-semibold text-neutral-900 dark:text-neutral-100 mb-2">
            Taking Longer Than Expected
          </h1>
          <p className="text-neutral-600 dark:text-neutral-400 mb-4">
            Your payment may have been processed. Please check your credit balance.
          </p>
          <button
            onClick={() => navigate('/dashboard')}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            Go to Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center">
        <div className="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
        <h1 className="text-2xl font-semibold text-neutral-900 dark:text-neutral-100 mb-2">
          Processing Payment
        </h1>
        <p className="text-neutral-600 dark:text-neutral-400">
          {status?.status === 'completed'
            ? `Success! ${status.credits} credits added. Redirecting...`
            : 'Confirming your payment with Stripe...'}
        </p>
      </div>
    </div>
  );
}
