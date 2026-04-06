import { useEffect, useRef, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { generatorApi } from '@/api/generator';
import { runsApi } from '@/api/runs';
import { creditsApi } from '@/api/credits';
import type { GenerateAllInput, Run } from '@/types/domain';
import { Play, Loader2, CheckCircle2, Coins, AlertTriangle } from 'lucide-react';
import { getApiErrorMessage } from '@/utils/apiError';
import { TokenUsageDisplay } from '@/components/costs';

interface Props {
  projectId: string;
  clientId: string;
  templateQuantities?: Record<number, number>;
  customTopics?: string[];  // NEW: topic override for content generation
  targetPlatform?: string;  // NEW: target platform for platform-specific generation
  onStarted?: (run: Run) => void;
}

export function GenerationPanel({ projectId, clientId, templateQuantities, customTopics, targetPlatform, onStarted }: Props) {
  const [runId, setRunId] = useState<string | null>(null);
  const [pollingEnabled, setPollingEnabled] = useState(false);
  // Ref to prevent onStarted firing multiple times when parent re-renders
  const onStartedCalledRef = useRef(false);
  const onStartedRef = useRef(onStarted);
  useEffect(() => { onStartedRef.current = onStarted; }, [onStarted]);
  // Reset the guard when a new run starts
  useEffect(() => { onStartedCalledRef.current = false; }, [runId]);
  // Safety: stop polling after 5 minutes to prevent infinite spinner
  useEffect(() => {
    if (!pollingEnabled) return;
    const timeout = setTimeout(() => setPollingEnabled(false), 5 * 60 * 1000);
    return () => clearTimeout(timeout);
  }, [pollingEnabled]);

  // Fetch credit balance — don't retry on 401/403 (token expired; avoids console spam)
  const { data: creditBalance } = useQuery({
    queryKey: ['credits', 'balance'],
    queryFn: () => creditsApi.getBalance(),
    refetchInterval: 30000,
    retry: (failureCount, error) => {
      const status = (error as { response?: { status?: number } })?.response?.status;
      if (status === 401 || status === 403) return false;
      return failureCount < 2;
    },
  });

  // Calculate total posts and credit cost
  const totalPosts = templateQuantities ? Object.values(templateQuantities).reduce((sum, qty) => sum + qty, 0) : 0;
  const creditCost = totalPosts * 20; // 20 credits per post ($40 ÷ $2/credit)
  const hasInsufficientCredits = creditBalance ? creditBalance.balance < creditCost : false;

  const generate = useMutation({
    mutationFn: (input: GenerateAllInput) => generatorApi.generateAll(input),
    onSuccess: (run) => {
      setRunId(run.id);
      setPollingEnabled(true);
    },
    onError: (error) => {
      alert(`Failed to start generation: ${getApiErrorMessage(error)}`);
    },
  });

  // Poll for run status every 2s while pollingEnabled; effect handles stopping
  const { data: runStatus } = useQuery({
    queryKey: ['run-status', runId],
    queryFn: () => (runId ? runsApi.get(runId) : null),
    enabled: pollingEnabled && !!runId,
    refetchInterval: 2000,
    staleTime: 0,
  });

  // Handle status changes — use ref for onStarted to avoid effect loop when parent re-renders
  useEffect(() => {
    if ((runStatus?.status === 'succeeded' || runStatus?.status === 'failed') && !onStartedCalledRef.current) {
      onStartedCalledRef.current = true;
      setPollingEnabled(false);
      onStartedRef.current?.(runStatus);
    }
  }, [runStatus]);

  const isGenerating = generate.isPending || pollingEnabled;
  // Keep button disabled after success to prevent accidental re-generation
  const isSucceeded = runStatus?.status === 'succeeded';
  const statusMessage = runStatus?.status === 'running'
    ? 'Generating posts...'
    : runStatus?.status === 'pending'
    ? 'Queued...'
    : generate.isPending
    ? 'Starting...'
    : isSucceeded
    ? 'Loading results...'
    : null;

  return (
    <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">Generate All</h3>
          <p className="text-xs text-neutral-600 dark:text-neutral-400">
            {statusMessage || 'Run full batch generation for this project.'}
          </p>
          {totalPosts > 0 && (
            <div className="mt-2 flex items-center gap-3">
              <div className="flex items-center gap-1.5 text-xs">
                <Coins className="h-3.5 w-3.5 text-yellow-600 dark:text-yellow-400" />
                <span className="font-medium text-neutral-900 dark:text-neutral-100">
                  {creditCost.toLocaleString()} credits
                </span>
                <span className="text-neutral-500 dark:text-neutral-400">
                  ({totalPosts} {totalPosts === 1 ? 'post' : 'posts'} × 20 credits)
                </span>
              </div>
              {creditBalance && (
                <span className={`text-xs ${hasInsufficientCredits ? 'text-red-600 dark:text-red-400' : 'text-neutral-500 dark:text-neutral-400'}`}>
                  Balance: {creditBalance.balance.toLocaleString()} credits
                </span>
              )}
            </div>
          )}
          {hasInsufficientCredits && (
            <div className="mt-2 flex items-center gap-1.5 text-xs text-red-600 dark:text-red-400">
              <AlertTriangle className="h-3.5 w-3.5" />
              <span>Insufficient credits. Please purchase more credits to continue.</span>
            </div>
          )}
        </div>
        <button
          disabled={isGenerating || isSucceeded || hasInsufficientCredits}
          onClick={() =>
            generate.mutate({
              projectId,
              clientId,
              isBatch: true,
              templateQuantities,
              customTopics,
              targetPlatform,
            })
          }
          className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 dark:hover:bg-blue-800 disabled:opacity-50"
        >
          {isGenerating ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : isSucceeded ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Play className="h-4 w-4" />
          )}
          {isGenerating ? statusMessage : isSucceeded ? 'Loading results...' : 'Generate All'}
        </button>
      </div>
      {generate.error && (
        <div className="mt-3 rounded-md bg-rose-50 dark:bg-rose-900/20 px-3 py-2 text-sm text-rose-700 dark:text-rose-300">
          {(generate.error as Error).message || 'Failed to queue generation'}
        </div>
      )}
      {isSucceeded && (
        <div className="mt-3 space-y-3">
          <div className="rounded-md bg-emerald-50 dark:bg-emerald-900/20 px-3 py-2 text-sm text-emerald-700 dark:text-emerald-300">
            Generation complete! Loading quality results...
          </div>
          {runStatus && (runStatus.totalInputTokens || runStatus.totalOutputTokens) && (
            <TokenUsageDisplay
              inputTokens={runStatus.totalInputTokens ?? undefined}
              outputTokens={runStatus.totalOutputTokens ?? undefined}
              cacheCreationTokens={runStatus.totalCacheCreationTokens ?? undefined}
              cacheReadTokens={runStatus.totalCacheReadTokens ?? undefined}
              costUsd={runStatus.totalCostUsd ?? undefined}
              estimatedCostUsd={runStatus.estimatedCostUsd ?? undefined}
              variant="compact"
            />
          )}
        </div>
      )}
    </div>
  );
}
