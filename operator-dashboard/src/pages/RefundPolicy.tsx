// Refund Policy — DRAFT pending legal review.
// Generated as review-ready starting copy (legal-advisor). For a payment platform,
// have this reviewed / regenerated via Termly or counsel before Stripe live activation.
// Governing-law and entity-address placeholders are marked [[...]] — fill before publishing.

export default function RefundPolicy() {
  return (
    <div className="min-h-screen bg-white dark:bg-neutral-950">
      <div className="max-w-4xl mx-auto px-6 py-12 text-neutral-800 dark:text-neutral-200">
        <h1 className="text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-2">
          REFUND POLICY
        </h1>
        <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-8">
          Last updated July 27, 2026
        </p>

        <div className="space-y-4 text-sm leading-relaxed">
          <p>
            This Refund Policy explains when and how refunds are issued for{' '}
            <strong>Content Jumpstart</strong> (the &ldquo;Services&rdquo;), operated by{' '}
            <strong>Basement Squirrel Games</strong> (&ldquo;we,&rdquo; &ldquo;us,&rdquo; or
            &ldquo;our&rdquo;). It forms part of, and should be read together with, our{' '}
            <a href="/terms" className="text-blue-600 dark:text-blue-400 hover:underline">
              Terms of Service
            </a>
            . By purchasing credits or a subscription, you agree to this policy.
          </p>

          <section className="mt-6">
            <h2 className="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-3">
              1. How billing works
            </h2>
            <p>
              The Services are sold on a prepaid <strong>credit</strong> basis. Credits are
              purchased through our payment processor, Stripe, and are consumed when you run
              paid operations such as AI content generation and research tools. The credit cost
              of each operation is shown before you confirm it.
            </p>
          </section>

          <section className="mt-6">
            <h2 className="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-3">
              2. No refunds once generation begins
            </h2>
            <p>
              Our Services deliver AI-generated output that is computed on demand and incurs
              non-recoverable third-party processing costs the moment an operation starts.{' '}
              <strong>
                Credits that have been spent, and any operation for which content generation or
                research has begun, are non-refundable.
              </strong>{' '}
              This includes cases where you are dissatisfied with the style, tone, accuracy, or
              usefulness of the generated output. AI output is inherently variable; you are
              responsible for reviewing and editing it before use (see our Terms of Service).
            </p>
            <p className="mt-2">
              This limitation is disclosed to you at the point of purchase and again before each
              paid operation, and your acknowledgement of it is a condition of completing your
              purchase.
            </p>
          </section>

          <section className="mt-6">
            <h2 className="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-3">
              3. When we do issue refunds
            </h2>
            <p>We will refund, or restore the affected credits, in these limited circumstances:</p>
            <ul className="list-disc ml-6 space-y-1 mt-2">
              <li>
                <strong>Duplicate or erroneous charges</strong> — you were charged more than once
                for the same purchase, or charged in error.
              </li>
              <li>
                <strong>Failed operation with no deliverable</strong> — a paid operation failed on
                our side and produced no usable output, and the credits were not automatically
                restored.
              </li>
              <li>
                <strong>Unused credits within 14 days</strong> — at our discretion, we may refund
                credits from a purchase made within the last 14 days that have <em>not</em> been
                spent on any operation.
              </li>
              <li>Where a refund is required by applicable law.</li>
            </ul>
          </section>

          <section className="mt-6">
            <h2 className="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-3">
              4. How to request a refund
            </h2>
            <p>
              Email{' '}
              <a
                href="mailto:support@content-jumpstart.com"
                className="text-blue-600 dark:text-blue-400 hover:underline"
              >
                support@content-jumpstart.com
              </a>{' '}
              within <strong>14 days</strong> of the charge, including your account email, the
              approximate date and amount, and a description of the issue. We aim to respond within
              5 business days. Approved refunds are returned to your original payment method via
              Stripe and may take several business days to appear.
            </p>
          </section>

          <section className="mt-6">
            <h2 className="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-3">
              5. Chargebacks
            </h2>
            <p>
              If you believe a charge is incorrect, please contact us first so we can resolve it.
              Initiating a chargeback for credits that have already been spent may result in
              suspension of your account pending resolution.
            </p>
          </section>

          <section className="mt-6">
            <h2 className="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-3">
              6. Contact
            </h2>
            <p>
              Basement Squirrel Games
              <br />
              [[Business mailing address]]
              <br />
              <a
                href="mailto:support@content-jumpstart.com"
                className="text-blue-600 dark:text-blue-400 hover:underline"
              >
                support@content-jumpstart.com
              </a>
            </p>
          </section>
        </div>

        <div className="mt-10 pt-6 border-t border-neutral-200 dark:border-neutral-800 text-sm text-neutral-500 dark:text-neutral-400">
          <a href="/terms" className="text-blue-600 dark:text-blue-400 hover:underline">
            Terms of Service
          </a>
          {' · '}
          <a href="/privacy" className="text-blue-600 dark:text-blue-400 hover:underline">
            Privacy Policy
          </a>
        </div>
      </div>
    </div>
  );
}
