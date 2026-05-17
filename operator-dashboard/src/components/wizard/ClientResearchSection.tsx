import { useState } from 'react';
import { Globe, Loader2, CheckCircle2, AlertCircle, ExternalLink } from 'lucide-react';
import { Button } from '../ui/Button';
import { clientResearchApi, type ClientResearchResult } from '@/api/clientResearch';
import type { ClientBrief } from '@/types/domain';

interface Props {
  businessName: string;
  location: string;
  creditBalance?: number;
  onApply: (fields: Partial<ClientBrief>) => void;
}

const CREDIT_COST = 200;

function ConfidenceBadge({ score }: { score: number }) {
  if (score >= 0.7) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-green-100 dark:bg-green-900/30 px-2 py-0.5 text-xs font-medium text-green-700 dark:text-green-400">
        <CheckCircle2 className="h-3 w-3" /> High
      </span>
    );
  }
  if (score >= 0.4) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 dark:bg-amber-900/30 px-2 py-0.5 text-xs font-medium text-amber-700 dark:text-amber-400">
        Medium
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-neutral-100 dark:bg-neutral-800 px-2 py-0.5 text-xs font-medium text-neutral-500 dark:text-neutral-400">
      Low
    </span>
  );
}

function FieldRow({
  label,
  value,
  confidence,
}: {
  label: string;
  value: string | string[] | undefined;
  confidence: number;
}) {
  if (!value || (Array.isArray(value) && value.length === 0)) return null;
  const display = Array.isArray(value) ? value.join(', ') : value;
  return (
    <div className="flex items-start justify-between gap-4 py-2 border-b border-neutral-100 dark:border-neutral-800 last:border-0">
      <div className="min-w-0 flex-1">
        <span className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wide">
          {label}
        </span>
        <p className="mt-0.5 text-sm text-neutral-900 dark:text-neutral-100 break-words">{display}</p>
      </div>
      <ConfidenceBadge score={confidence} />
    </div>
  );
}

export function ClientResearchSection({ businessName, location, creditBalance, onApply }: Props) {
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<ClientResearchResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const insufficientCredits = creditBalance !== undefined && creditBalance < CREDIT_COST;

  const handleResearch = async () => {
    if (!businessName.trim() || !location.trim()) {
      setError('Please enter a business name and location in the form above before researching.');
      return;
    }
    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await clientResearchApi.researchBrief({ name: businessName, location });
      setResult(data);
    } catch (err: unknown) {
      const msg =
        err && typeof err === 'object' && 'response' in err
          ? ((err as { response?: { data?: { detail?: string } } }).response?.data?.detail ??
            'Research failed. Please try again.')
          : 'Research failed. Please try again.';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleApply = () => {
    if (!result) return;
    onApply(result.brief);
    setResult(null);
    setIsOpen(false);
  };

  return (
    <div className="mb-6 border border-neutral-200 dark:border-neutral-700 rounded-lg p-4 bg-neutral-50 dark:bg-neutral-800">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between w-full text-left"
        type="button"
      >
        <span className="flex items-center gap-2 font-medium text-neutral-900 dark:text-neutral-100">
          <Globe className="h-4 w-4 text-blue-500" />
          Research This Client
          <span className="text-xs font-normal text-neutral-500 dark:text-neutral-400">
            — {CREDIT_COST} credits
          </span>
        </span>
        <span className="text-neutral-500 dark:text-neutral-400 text-xl font-light">
          {isOpen ? '−' : '+'}
        </span>
      </button>

      {isOpen && (
        <div className="mt-4 space-y-4">
          <p className="text-sm text-neutral-600 dark:text-neutral-400">
            Searches the web for publicly available information about{' '}
            <strong>{businessName || 'this business'}</strong> and pre-populates the profile fields below.
            You review and apply the results.
          </p>

          {insufficientCredits && (
            <div className="flex items-center gap-2 rounded-md bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 px-3 py-2 text-sm text-amber-800 dark:text-amber-400">
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              Insufficient credits ({creditBalance} available, {CREDIT_COST} required).
            </div>
          )}

          {error && (
            <div className="rounded-md bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 px-3 py-2 text-sm text-red-800 dark:text-red-400">
              {error}
            </div>
          )}

          {!result && (
            <Button
              onClick={handleResearch}
              disabled={isLoading || insufficientCredits || !businessName.trim() || !location.trim()}
              type="button"
            >
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {isLoading ? 'Researching…' : `Research — ${CREDIT_COST} credits`}
            </Button>
          )}

          {result && (
            <div className="space-y-4">
              {result.warning && (
                <div className="flex items-center gap-2 rounded-md bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 px-3 py-2 text-sm text-amber-800 dark:text-amber-400">
                  <AlertCircle className="h-4 w-4 flex-shrink-0" />
                  {result.warning}
                </div>
              )}

              <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-4 space-y-1">
                <p className="text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-3">
                  Discovered fields — review before applying
                </p>
                <FieldRow
                  label="Business Description"
                  value={result.brief.businessDescription}
                  confidence={result.confidence.business_description ?? 0}
                />
                <FieldRow
                  label="Industry"
                  value={result.brief.industry}
                  confidence={result.confidence.industry ?? 0}
                />
                <FieldRow
                  label="Founder"
                  value={result.brief.founderName}
                  confidence={result.confidence.founder_name ?? 0}
                />
                <FieldRow
                  label="Ideal Customer"
                  value={result.brief.idealCustomer}
                  confidence={result.confidence.ideal_customer ?? 0}
                />
                <FieldRow
                  label="Main Problem Solved"
                  value={result.brief.mainProblemSolved}
                  confidence={result.confidence.main_problem_solved ?? 0}
                />
                <FieldRow
                  label="Pain Points"
                  value={result.brief.customerPainPoints}
                  confidence={result.confidence.customer_pain_points ?? 0}
                />
                <FieldRow
                  label="Competitors"
                  value={result.brief.competitors}
                  confidence={result.confidence.competitors ?? 0}
                />
                <FieldRow
                  label="Keywords"
                  value={result.brief.keywords}
                  confidence={result.confidence.keywords ?? 0}
                />
                <FieldRow
                  label="Tone"
                  value={result.brief.tonePreference}
                  confidence={result.confidence.tone_preference ?? 0}
                />
                <FieldRow
                  label="Brand Personality"
                  value={result.brief.brandPersonality}
                  confidence={result.confidence.brand_personality ?? 0}
                />
                <FieldRow
                  label="Key Phrases"
                  value={result.brief.keyPhrases}
                  confidence={result.confidence.key_phrases ?? 0}
                />
                <FieldRow
                  label="Platforms"
                  value={result.brief.platforms}
                  confidence={result.confidence.target_platforms ?? 0}
                />
                <FieldRow
                  label="Main CTA"
                  value={result.brief.mainCta}
                  confidence={result.confidence.main_cta ?? 0}
                />
                <FieldRow
                  label="Measurable Results"
                  value={result.brief.measurableResults}
                  confidence={result.confidence.measurable_results ?? 0}
                />
              </div>

              {result.sources.length > 0 && (
                <details className="text-xs text-neutral-500 dark:text-neutral-400">
                  <summary className="cursor-pointer hover:text-neutral-700 dark:hover:text-neutral-300">
                    {result.sources.length} sources used
                  </summary>
                  <ul className="mt-2 space-y-1 max-h-40 overflow-y-auto">
                    {result.sources.slice(0, 20).map((url) => (
                      <li key={url}>
                        <a
                          href={url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 hover:underline"
                        >
                          <ExternalLink className="h-3 w-3" />
                          {url.length > 60 ? url.slice(0, 60) + '…' : url}
                        </a>
                      </li>
                    ))}
                  </ul>
                </details>
              )}

              <div className="flex gap-3">
                <Button onClick={handleApply} type="button">
                  Apply to Profile
                </Button>
                <Button
                  variant="outline"
                  onClick={() => {
                    setResult(null);
                    setError(null);
                  }}
                  type="button"
                >
                  Discard
                </Button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
