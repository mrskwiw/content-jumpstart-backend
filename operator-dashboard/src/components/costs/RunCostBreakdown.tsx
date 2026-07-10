/**
 * Run Cost Breakdown Component
 *
 * Displays detailed cost breakdown for a specific generation run.
 */
import { useQuery } from '@tanstack/react-query';
import {
  Zap,
  FileText,
  Database,
  TrendingDown,
  Clock,
  CheckCircle2,
  XCircle,
} from 'lucide-react';
import { costsApi } from '../../api/costs';

interface RunCostBreakdownProps {
  runId: string;
}

export function RunCostBreakdown({ runId }: RunCostBreakdownProps) {
  const { data: costs, isLoading } = useQuery({
    queryKey: ['run-costs', runId],
    queryFn: () => costsApi.getRunCosts(runId),
    retry: 1,
  });

  if (isLoading || !costs) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-20 bg-slate-100 dark:bg-slate-700/50 rounded"></div>
        <div className="h-40 bg-slate-100 dark:bg-slate-700/50 rounded"></div>
      </div>
    );
  }

  const formatCost = (cost: number) => {
    if (cost >= 1) return `$${cost.toFixed(2)}`;
    return `$${cost.toFixed(4)}`;
  };

  const formatTokens = (tokens: number) => tokens.toLocaleString();

  const statusIcon = {
    succeeded: <CheckCircle2 className="h-4 w-4 text-emerald-500" />,
    failed: <XCircle className="h-4 w-4 text-red-500" />,
    running: <Clock className="h-4 w-4 text-blue-500 animate-spin" />,
    pending: <Clock className="h-4 w-4 text-slate-400" />,
  }[costs.status] || <Clock className="h-4 w-4" />;

  const duration = costs.completedAt && costs.startedAt
    ? Math.round((new Date(costs.completedAt).getTime() - new Date(costs.startedAt).getTime()) / 1000)
    : null;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 rounded-lg p-4 border border-blue-200 dark:border-blue-800">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            {statusIcon}
            <span className="text-sm font-medium text-slate-700 dark:text-slate-300 capitalize">
              {costs.status}
            </span>
          </div>
          {duration && (
            <div className="text-xs text-slate-600 dark:text-slate-400">
              {duration}s duration
            </div>
          )}
        </div>
        <div className="flex items-baseline gap-2">
          <div className="text-3xl font-bold text-slate-900 dark:text-slate-100">
            {formatCost(costs.totalCostUsd)}
          </div>
          {costs.estimatedCostUsd && (
            <div className="text-sm text-slate-600 dark:text-slate-400">
              (est. {formatCost(costs.estimatedCostUsd)})
            </div>
          )}
        </div>
      </div>

      {/* Token Breakdown */}
      <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
        <div className="flex items-center gap-2 mb-4">
          <Zap className="h-4 w-4 text-slate-600 dark:text-slate-400" />
          <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
            Token Usage
          </h4>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="text-xs text-slate-600 dark:text-slate-400 mb-1">Input Tokens</div>
            <div className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              {formatTokens(costs.totalInputTokens)}
            </div>
            <div className="text-xs text-slate-500 dark:text-slate-500 mt-0.5">
              ~${((costs.totalInputTokens / 1_000_000) * 3.0).toFixed(4)}
            </div>
          </div>

          <div>
            <div className="text-xs text-slate-600 dark:text-slate-400 mb-1">Output Tokens</div>
            <div className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              {formatTokens(costs.totalOutputTokens)}
            </div>
            <div className="text-xs text-slate-500 dark:text-slate-500 mt-0.5">
              ~${((costs.totalOutputTokens / 1_000_000) * 15.0).toFixed(4)}
            </div>
          </div>

          {costs.totalCacheReadTokens > 0 && (
            <>
              <div>
                <div className="text-xs text-slate-600 dark:text-slate-400 mb-1 flex items-center gap-1">
                  <Database className="h-3 w-3" />
                  Cache Created
                </div>
                <div className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                  {formatTokens(costs.totalCacheCreationTokens)}
                </div>
              </div>

              <div>
                <div className="text-xs text-emerald-600 dark:text-emerald-400 mb-1 flex items-center gap-1">
                  <Database className="h-3 w-3" />
                  Cache Read
                </div>
                <div className="text-lg font-semibold text-emerald-600 dark:text-emerald-400">
                  {formatTokens(costs.totalCacheReadTokens)}
                </div>
              </div>
            </>
          )}
        </div>

        {costs.cacheSavingsUsd && costs.cacheSavingsUsd > 0 && (
          <div className="mt-4 pt-3 border-t border-slate-200 dark:border-slate-700">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 text-sm">
                <TrendingDown className="h-4 w-4" />
                <span>Cache Savings</span>
              </div>
              <div className="text-lg font-semibold text-emerald-600 dark:text-emerald-400">
                {formatCost(costs.cacheSavingsUsd)}
              </div>
            </div>
            <div className="text-xs text-slate-500 dark:text-slate-500 mt-1">
              {((costs.totalCacheReadTokens / (costs.totalInputTokens + costs.totalOutputTokens)) * 100).toFixed(1)}%
              of tokens from cache (10x cost reduction)
            </div>
          </div>
        )}
      </div>

      {/* Post Stats */}
      <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
        <div className="flex items-center gap-2 mb-4">
          <FileText className="h-4 w-4 text-slate-600 dark:text-slate-400" />
          <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
            Post Statistics
          </h4>
        </div>

        <div className="grid grid-cols-3 gap-4 text-sm">
          <div>
            <div className="text-xs text-slate-600 dark:text-slate-400 mb-1">Total Posts</div>
            <div className="text-2xl font-bold text-slate-900 dark:text-slate-100">
              {costs.totalPosts}
            </div>
          </div>

          <div>
            <div className="text-xs text-slate-600 dark:text-slate-400 mb-1">With Token Data</div>
            <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
              {costs.postsWithTokenData}
            </div>
          </div>

          <div>
            <div className="text-xs text-slate-600 dark:text-slate-400 mb-1">Avg Cost/Post</div>
            <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
              {costs.avgCostPerPost ? formatCost(costs.avgCostPerPost) : 'N/A'}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
