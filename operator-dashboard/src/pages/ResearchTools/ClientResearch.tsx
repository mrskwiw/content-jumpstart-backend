import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Globe, Loader2, CheckCircle2, AlertCircle, ExternalLink, UserPlus } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { creditsApi } from '@/api/credits';
import { clientsApi } from '@/api/clients';
import { clientResearchApi, type ClientResearchResult } from '@/api/clientResearch';
import { Button } from '@/components/ui/Button';
import { BriefDownloadButton } from '@/components/ui/BriefDownloadButton';
import type { Platform } from '@/types/domain';

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
      <span className="rounded-full bg-amber-100 dark:bg-amber-900/30 px-2 py-0.5 text-xs font-medium text-amber-700 dark:text-amber-400">
        Medium
      </span>
    );
  }
  return (
    <span className="rounded-full bg-neutral-100 dark:bg-neutral-800 px-2 py-0.5 text-xs font-medium text-neutral-500 dark:text-neutral-400">
      Low
    </span>
  );
}

function ResultCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-4">
      <h3 className="text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-3">
        {title}
      </h3>
      <div className="space-y-2">{children}</div>
    </div>
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
  if (!value || (Array.isArray(value) && value.length === 0)) {
    return (
      <div className="flex items-center justify-between text-sm py-1">
        <span className="text-neutral-400 dark:text-neutral-600">{label}</span>
        <span className="text-neutral-300 dark:text-neutral-700 text-xs italic">Not found</span>
      </div>
    );
  }
  const display = Array.isArray(value) ? value.join(', ') : value;
  return (
    <div className="flex items-start justify-between gap-3 py-1">
      <div className="min-w-0 flex-1">
        <span className="text-xs text-neutral-500 dark:text-neutral-400">{label}</span>
        <p className="text-sm text-neutral-900 dark:text-neutral-100 break-words">{display}</p>
      </div>
      <ConfidenceBadge score={confidence} />
    </div>
  );
}

export default function ClientResearch() {
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [location, setLocation] = useState('');
  const [website, setWebsite] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<ClientResearchResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isCreatingClient, setIsCreatingClient] = useState(false);

  const { data: creditData } = useQuery({
    queryKey: ['credits', 'balance'],
    queryFn: () => creditsApi.getBalance(),
  });

  const insufficientCredits =
    creditData !== undefined && (creditData.balance ?? 0) < CREDIT_COST;

  const handleResearch = async () => {
    setIsLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await clientResearchApi.researchBrief({
        name: name.trim(),
        location: location.trim(),
        website: website.trim() || undefined,
      });
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

  const handleCreateClient = async () => {
    if (!result) return;
    setIsCreatingClient(true);
    try {
      const brief = result.brief;
      const client = await clientsApi.create({
        name: brief.companyName || name,
        location: brief.location || location,
        businessDescription: brief.businessDescription,
        industry: brief.industry,
        founderName: brief.founderName,
        idealCustomer: brief.idealCustomer,
        mainProblemSolved: brief.mainProblemSolved,
        tonePreference: brief.tonePreference,
        brandPersonality: brief.brandPersonality,
        keywords: brief.keywords,
        competitors: brief.competitors,
        customerPainPoints: brief.customerPainPoints,
        platforms: (brief.platforms ?? []) as Platform[],
        mainCta: brief.mainCta,
      });
      navigate(`/dashboard/clients/${client.id}`);
    } catch {
      setError('Failed to create client. Please try again.');
    } finally {
      setIsCreatingClient(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">Client Research</h1>
        <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
          Enter a business name and location to automatically discover and pre-populate client brief fields.
        </p>
      </div>

      {/* Search Form */}
      <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6 space-y-4">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-sm font-medium text-neutral-700 dark:text-neutral-300">
              Business Name *
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Acme Marketing Agency"
              className="w-full rounded-md border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 px-3 py-2 text-sm text-neutral-900 dark:text-neutral-100 placeholder-neutral-400 dark:placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-neutral-700 dark:text-neutral-300">
              Location *
            </label>
            <input
              type="text"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="e.g. Austin, TX"
              className="w-full rounded-md border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 px-3 py-2 text-sm text-neutral-900 dark:text-neutral-100 placeholder-neutral-400 dark:placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-neutral-700 dark:text-neutral-300">
            Website <span className="font-normal text-neutral-400">(optional)</span>
          </label>
          <input
            type="text"
            value={website}
            onChange={(e) => setWebsite(e.target.value)}
            placeholder="e.g. acmemarketing.com"
            className="w-full rounded-md border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 px-3 py-2 text-sm text-neutral-900 dark:text-neutral-100 placeholder-neutral-400 dark:placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>

        {insufficientCredits && (
          <div className="flex items-center gap-2 rounded-md bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 px-3 py-2 text-sm text-amber-800 dark:text-amber-400">
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
            Insufficient credits ({creditData?.balance ?? 0} available, {CREDIT_COST} required).
          </div>
        )}

        {error && (
          <div className="rounded-md bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 px-3 py-2 text-sm text-red-800 dark:text-red-400">
            {error}
          </div>
        )}

        <div className="flex items-center gap-4">
          <Button
            onClick={handleResearch}
            disabled={isLoading || insufficientCredits || !name.trim() || !location.trim()}
          >
            {isLoading ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Globe className="mr-2 h-4 w-4" />
            )}
            {isLoading ? 'Researching…' : `Research — ${CREDIT_COST} credits`}
          </Button>
          {creditData && (
            <span className="text-xs text-neutral-400 dark:text-neutral-500">
              Balance: {creditData.balance.toLocaleString()} credits
            </span>
          )}
        </div>
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-4">
          {result.warning && (
            <div className="flex items-center gap-2 rounded-md bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 px-3 py-2 text-sm text-amber-800 dark:text-amber-400">
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              {result.warning}
            </div>
          )}

          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
              Research Results
              <span className="ml-2 text-sm font-normal text-neutral-400 dark:text-neutral-500">
                ({result.durationSeconds}s)
              </span>
            </h2>
            <div className="flex flex-wrap items-center gap-3">
              <BriefDownloadButton
                brief={result.rawBrief}
                confidence={result.confidence}
                companyName={result.brief.companyName}
              />
              <Button onClick={handleCreateClient} disabled={isCreatingClient} variant="outline">
                {isCreatingClient ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <UserPlus className="mr-2 h-4 w-4" />
                )}
                Create Client
              </Button>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <ResultCard title="Business">
              <FieldRow label="Description" value={result.brief.businessDescription} confidence={result.confidence.business_description ?? 0} />
              <FieldRow label="Industry" value={result.brief.industry} confidence={result.confidence.industry ?? 0} />
              <FieldRow label="Founder" value={result.brief.founderName} confidence={result.confidence.founder_name ?? 0} />
              <FieldRow label="Website" value={result.brief.businessDescription ? undefined : undefined} confidence={0} />
            </ResultCard>

            <ResultCard title="Audience">
              <FieldRow label="Ideal Customer" value={result.brief.idealCustomer} confidence={result.confidence.ideal_customer ?? 0} />
              <FieldRow label="Main Problem" value={result.brief.mainProblemSolved} confidence={result.confidence.main_problem_solved ?? 0} />
              <FieldRow label="Pain Points" value={result.brief.customerPainPoints} confidence={result.confidence.customer_pain_points ?? 0} />
              <FieldRow label="Measurable Results" value={result.brief.measurableResults} confidence={result.confidence.measurable_results ?? 0} />
            </ResultCard>

            <ResultCard title="Brand Voice">
              <FieldRow label="Tone" value={result.brief.tonePreference} confidence={result.confidence.tone_preference ?? 0} />
              <FieldRow label="Personality" value={result.brief.brandPersonality} confidence={result.confidence.brand_personality ?? 0} />
              <FieldRow label="Key Phrases" value={result.brief.keyPhrases} confidence={result.confidence.key_phrases ?? 0} />
              <FieldRow label="Main CTA" value={result.brief.mainCta} confidence={result.confidence.main_cta ?? 0} />
            </ResultCard>

            <ResultCard title="Market">
              <FieldRow label="Competitors" value={result.brief.competitors} confidence={result.confidence.competitors ?? 0} />
              <FieldRow label="Keywords" value={result.brief.keywords} confidence={result.confidence.keywords ?? 0} />
              <FieldRow label="Platforms" value={result.brief.platforms} confidence={result.confidence.target_platforms ?? 0} />
            </ResultCard>
          </div>

          {result.sources.length > 0 && (
            <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-4">
              <h3 className="text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-3">
                Sources ({result.sources.length})
              </h3>
              <ul className="space-y-1 max-h-48 overflow-y-auto">
                {result.sources.map((url) => (
                  <li key={url}>
                    <a
                      href={url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-sm text-blue-600 dark:text-blue-400 hover:underline"
                    >
                      <ExternalLink className="h-3 w-3 flex-shrink-0" />
                      <span className="truncate">{url}</span>
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
