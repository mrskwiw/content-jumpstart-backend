import { type ReactNode } from 'react';
import './LegalDocument.css';

/**
 * Renders a first-party legal policy (our own Termly HTML export, cleaned) inside
 * our page chrome, restyled to match the app theme via LegalDocument.css.
 *
 * The HTML is our own trusted content (exported from our Termly account, cleaned
 * by scripts/clean_termly — not user input), so dangerouslySetInnerHTML is safe
 * here; there is no untrusted-input path into `html`.
 */
interface LegalDocumentProps {
  html: string;
  /** Cross-links rendered beneath the policy. */
  footer?: ReactNode;
}

export default function LegalDocument({ html, footer }: LegalDocumentProps) {
  return (
    <div className="min-h-screen bg-white dark:bg-neutral-950">
      <div className="max-w-4xl mx-auto px-6 py-12">
        <div className="legal-content" dangerouslySetInnerHTML={{ __html: html }} />
        {footer && (
          <div className="mt-10 pt-6 border-t border-neutral-200 dark:border-neutral-800 text-sm text-neutral-500 dark:text-neutral-400">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}

/** Shared cross-links for the legal pages. */
export function LegalLinks() {
  const cls = 'text-blue-600 dark:text-blue-400 hover:underline';
  return (
    <nav className="flex flex-wrap gap-x-3 gap-y-1">
      <a href="/terms" className={cls}>
        Terms of Service
      </a>
      <span aria-hidden>·</span>
      <a href="/privacy" className={cls}>
        Privacy Policy
      </a>
      <span aria-hidden>·</span>
      <a href="/cookies" className={cls}>
        Cookie Policy
      </a>
      <span aria-hidden>·</span>
      <a href="/refund" className={cls}>
        Refund Policy
      </a>
    </nav>
  );
}
