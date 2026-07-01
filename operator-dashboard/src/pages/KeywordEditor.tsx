/**
 * Standalone keyword editor page.
 * Route: /dashboard/clients/:clientId/keywords
 *
 * Loads all 4 keyword types from the DB on mount.
 * Customers (and operators) can add, edit, and remove keywords.
 * Changes take effect on the next SEO research run or content generation.
 */

import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { ArrowLeft, RefreshCw, ExternalLink } from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent, Button } from '@/components/ui';
import { KeywordTypeTab } from '@/components/keywords/KeywordTypeTab';
import { keywordsApi, type KeywordType } from '@/api/keywords';
import { researchApi } from '@/api/research';

const TABS: { type: KeywordType; label: string; description: string }[] = [
  {
    type: 'primary',
    label: 'Primary',
    description: '3–5 high-priority target keywords. Used directly in content generation.',
  },
  {
    type: 'secondary',
    label: 'Secondary',
    description: '10–30 supporting long-tail keywords for content variety.',
  },
  {
    type: 'negative',
    label: 'Negative',
    description:
      'Topics, brands, or terms to avoid. Excluded from keyword suggestions and generation prompts.',
  },
  {
    type: 'quick_win',
    label: 'Quick Wins',
    description: 'Low-difficulty keywords flagged as easy ranking opportunities.',
  },
];

export default function KeywordEditor() {
  const { clientId } = useParams<{ clientId: string }>();
  const [activeTab, setActiveTab] = useState<KeywordType>('primary');

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['client-keywords', clientId],
    queryFn: () => keywordsApi.getKeywords(clientId!),
    enabled: !!clientId,
    staleTime: 30_000,
  });

  // Fetch latest SEO research result ID so we can offer "Refresh from research"
  const { data: researchHistory } = useQuery({
    queryKey: ['research-history-seo', clientId],
    queryFn: async () => {
      const history = await researchApi.getClientHistory(clientId!, 'seo_keyword_research');
      const completed = history.results
        .filter((r) => r.status === 'completed')
        .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
      return completed[0] ?? null;
    },
    enabled: !!clientId,
    staleTime: 60_000,
  });

  const importMutation = useMutation({
    mutationFn: () => keywordsApi.importFromResult(clientId!, researchHistory!.id),
    onSuccess: (result) => {
      toast.success(`Refreshed: ${result.imported} new keywords added`);
      refetch();
    },
    onError: () => toast.error('Could not import from research result'),
  });

  const currentKeywords = {
    primary: data?.primary ?? [],
    secondary: data?.secondary ?? [],
    negative: data?.negative ?? [],
    quick_win: data?.quick_win ?? [],
  };

  const activeTabData = TABS.find((t) => t.type === activeTab)!;

  return (
    <div className="max-w-3xl mx-auto py-6 px-4 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <Link
            to={clientId ? `/dashboard/clients/${clientId}` : '/dashboard/clients'}
            className="inline-flex items-center gap-1 text-sm text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300 mb-2"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to client
          </Link>
          <h1 className="text-2xl font-semibold text-neutral-900 dark:text-neutral-100">
            Keyword Editor
          </h1>
          <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
            Edit your keyword lists. Changes take effect on your next content generation run.
          </p>
        </div>

        {researchHistory && (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => importMutation.mutate()}
            disabled={importMutation.isPending}
            className="shrink-0 flex items-center gap-1.5"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${importMutation.isPending ? 'animate-spin' : ''}`} />
            Refresh from research
          </Button>
        )}
      </div>

      {/* Tab navigation */}
      <div className="flex border-b border-neutral-200 dark:border-neutral-700 gap-0">
        {TABS.map((tab) => {
          const count = currentKeywords[tab.type].length;
          return (
            <button
              key={tab.type}
              onClick={() => setActiveTab(tab.type)}
              className={`
                px-4 py-2.5 text-sm font-medium border-b-2 transition-colors
                ${
                  activeTab === tab.type
                    ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                    : 'border-transparent text-neutral-600 hover:text-neutral-900 dark:text-neutral-400 dark:hover:text-neutral-200'
                }
              `}
            >
              {tab.label}
              {count > 0 && (
                <span className="ml-1.5 text-xs text-neutral-400 dark:text-neutral-500">
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Tab body */}
      <Card>
        <CardContent className="p-5 space-y-3">
          <p className="text-sm text-neutral-500 dark:text-neutral-400">
            {activeTabData.description}
          </p>

          {isLoading ? (
            <div className="py-8 text-center text-sm text-neutral-400">Loading keywords…</div>
          ) : isError ? (
            <div className="py-8 text-center text-sm text-rose-500">
              Could not load keywords.{' '}
              <button className="underline" onClick={() => refetch()}>
                Retry
              </button>
            </div>
          ) : (
            <KeywordTypeTab
              clientId={clientId!}
              type={activeTab}
              keywords={currentKeywords[activeTab]}
              label={activeTabData.label}
            />
          )}
        </CardContent>
      </Card>

      <p className="text-xs text-neutral-400 dark:text-neutral-500 flex items-center gap-1">
        <ExternalLink className="h-3 w-3" />
        Keyword changes apply to future SEO research and content generation runs only.
        Existing posts are not affected.
      </p>
    </div>
  );
}
