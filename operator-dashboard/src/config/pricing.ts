/**
 * Credit pricing constants — single source of truth for the frontend.
 *
 * BILLING-01 locked rate (2026-07-30): subscription credits are $0.50 each
 * (2 credits/$); non-expiring top-up credits are $1.00 each. Mirrors
 * backend/pricing/credit_pricing.py's STANDARD_PACKAGE_RATE /
 * ADDITIONAL_CREDIT_RATE. Before this file existed, this rate was
 * hardcoded independently in multiple components and drifted out of sync
 * (Bug #247) — import from here instead of hardcoding a new copy.
 */
export const SUBSCRIPTION_CREDIT_RATE_USD = 0.5;
export const TOPUP_CREDIT_RATE_USD = 1.0;

/**
 * Per-post generation cost, mirroring backend/routers/generator.py's
 * _generation_credit_cost() (Bug #246): blog is the only long-form content
 * type; everything else is the flagship short-form social post. Was
 * duplicated as a flat 20-credits-per-post constant in both
 * TemplateQuantitySelector.tsx and GenerationPanel.tsx before this existed —
 * import creditsPerPost() instead of hardcoding a new copy.
 */
export const CREDITS_PER_POST_BLOG = 20;
export const CREDITS_PER_POST_SOCIAL = 5;

export function creditsPerPost(targetPlatform: string | null | undefined): number {
  return (targetPlatform ?? '').toLowerCase() === 'blog'
    ? CREDITS_PER_POST_BLOG
    : CREDITS_PER_POST_SOCIAL;
}
