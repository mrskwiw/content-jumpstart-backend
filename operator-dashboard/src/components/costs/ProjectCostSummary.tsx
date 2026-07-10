/**
 * Project Cost Summary Component
 *
 * Displays project-level cost analytics including generation and research costs.
 */
import { useQuery } from '@tanstack/react-query';
import { DollarSign, TrendingUp, Zap, FlaskConical, AlertCircle } from 'lucide-react';
import { costsApi } from '../../api/costs';

interface ProjectCostSummaryProps {
  projectId: string;
}

export function ProjectCostSummary({ projectId }: ProjectCostSummaryProps) {
  const { data: costs, isLoading, error } = useQuery({
    queryKey: ['project-costs', projectId],
    queryFn: () => costsApi.getProjectCosts(projectId),
    retry: 1,
  });

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-1/3 mb-4"></div>
          <div className="grid grid-cols-3 gap-4">
            <div className="h-16 bg-slate-100 dark:bg-slate-700/50 rounded"></div>
            <div className="h-16 bg-slate-100 dark:bg-slate-700/50 rounded"></div>
            <div className="h-16 bg-slate-100 dark:bg-slate-700/50 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error || !costs) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
        <div className="flex items-center gap-2 text-slate-600 dark:text-slate-400 text-sm">
          <AlertCircle className="h-4 w-4" />
          <span>Cost data not available</span>
        </div>
      </div>
    );
  }

  const formatCost = (cost: number) => {
    if (cost >= 1) return `$${cost.toFixed(2)}`;
    return `$${cost.toFixed(4)}`;
  };

  const formatTokens = (tokens: number) => {
    if (tokens >= 1_000_000) {
      return `${(tokens / 1_000_000).toFixed(2)}M`;
    }
    if (tokens >= 1_000) {
      return `${(tokens / 1_000).toFixed(1)}K`;
    }
    return tokens.toLocaleString();
  };

  const totalTokens = costs.totalInputTokens + costs.totalOutputTokens;
  const cacheRatio = totalTokens > 0 ? (costs.totalCacheReadTokens / totalTokens) * 100 : 0;

  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <DollarSign className="h-5 w-5 text-slate-600 dark:text-slate-400" />
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
            API Cost Summary
          </h3>
        </div>
        <div className="text-2xl font-bold text-slate-900 dark:text-slate-100">
          {formatCost(costs.totalCostUsd)}
        </div>
      </div>

      {/* Cost Breakdown */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 border border-blue-200 dark:border-blue-800">
          <div className="flex items-center gap-2 mb-2">
            <Zap className="h-4 w-4 text-blue-600 dark:text-blue-400" />
            <div className="text-xs text-blue-600 dark:text-blue-400 font-medium">Generation</div>
          </div>
          <div className="text-xl font-bold text-blue-900 dark:text-blue-100">
            {formatCost(costs.totalGenerationCostUsd)}
          </div>
          <div className="text-xs text-blue-600 dark:text-blue-400 mt-1">
            {costs.totalPosts} posts • {costs.totalRuns} runs
          </div>
        </div>

        <div className="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-4 border border-purple-200 dark:border-purple-800">
          <div className="flex items-center gap-2 mb-2">
            <FlaskConical className="h-4 w-4 text-purple-600 dark:text-purple-400" />
            <div className="text-xs text-purple-600 dark:text-purple-400 font-medium">Research</div>
          </div>
          <div className="text-xl font-bold text-purple-900 dark:text-purple-100">
            {formatCost(costs.totalResearchCostUsd)}
          </div>
          <div className="text-xs text-purple-600 dark:text-purple-400 mt-1">
            {costs.totalResearchTools} tools executed
          </div>
        </div>

        <div className="bg-emerald-50 dark:bg-emerald-900/20 rounded-lg p-4 border border-emerald-200 dark:border-emerald-800">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            <div className="text-xs text-emerald-600 dark:text-emerald-400 font-medium">Per Post</div>
          </div>
          <div className="text-xl font-bold text-emerald-900 dark:text-emerald-100">
            {costs.costPerPost ? formatCost(costs.costPerPost) : 'N/A'}
          </div>
          <div className="text-xs text-emerald-600 dark:text-emerald-400 mt-1">
            Average cost per post
          </div>
        </div>
      </div>

      {/* Token Stats */}
      <div className="border-t border-slate-200 dark:border-slate-700 pt-4">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <div className="text-slate-600 dark:text-slate-400 text-xs mb-1">Total Tokens</div>
            <div className="font-semibold text-slate-900 dark:text-slate-100">
              {formatTokens(totalTokens)}
            </div>
          </div>

          <div>
            <div className="text-slate-600 dark:text-slate-400 text-xs mb-1">Cache Usage</div>
            <div className="font-semibold text-emerald-600 dark:text-emerald-400">
              {formatTokens(costs.totalCacheReadTokens)} ({cacheRatio.toFixed(1)}%)
            </div>
          </div>

          <div>
            <div className="text-slate-600 dark:text-slate-400 text-xs mb-1">Input Tokens</div>
            <div className="font-medium text-slate-900 dark:text-slate-100">
              {formatTokens(costs.totalInputTokens)}
            </div>
          </div>

          <div>
            <div className="text-slate-600 dark:text-slate-400 text-xs mb-1">Output Tokens</div>
            <div className="font-medium text-slate-900 dark:text-slate-100">
              {formatTokens(costs.totalOutputTokens)}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
