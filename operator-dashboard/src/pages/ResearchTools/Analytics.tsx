import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { researchApi, ToolStats } from '@/api';
import { DollarSign, TrendingDown, Target, Percent, Database } from 'lucide-react';

export default function ResearchAnalytics() {
  const [dateRange, setDateRange] = useState(90);

  // Fetch analytics
  const { data: analytics, isLoading } = useQuery({
    queryKey: ['research-analytics', dateRange],
    queryFn: () => researchApi.getAnalytics(dateRange)
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!analytics) {
    return (
      <div className="text-center py-16">
        <p className="text-gray-500 dark:text-gray-400">Failed to load analytics</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            Research Analytics
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Track ROI and usage patterns for research tools
          </p>
        </div>
        <select
          value={dateRange}
          onChange={(e) => setDateRange(Number(e.target.value))}
          className="px-4 py-2 border border-gray-300 dark:border-neutral-600 rounded-lg bg-white dark:bg-neutral-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500"
        >
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
          <option value={365}>Last year</option>
        </select>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          title="Total Revenue"
          value={`$${(analytics?.totalRevenue ?? 0).toFixed(2)}`}
          trend={`${analytics?.totalExecutions ?? 0} executions`}
          icon={<DollarSign className="h-5 w-5" />}
          color="blue"
        />
        <KPICard
          title="API Costs"
          value={`$${(analytics?.totalApiCost ?? 0).toFixed(2)}`}
          trend={`${(analytics?.profitMargin ?? 0).toFixed(1)}% margin`}
          icon={<TrendingDown className="h-5 w-5" />}
          color="emerald"
        />
        <KPICard
          title="Cache Hit Rate"
          value={`${(analytics?.cacheHitRate ?? 0).toFixed(1)}%`}
          trend={`Saved $${(analytics?.cacheSavings ?? 0).toFixed(2)}`}
          icon={<Database className="h-5 w-5" />}
          color="purple"
        />
        <KPICard
          title="Avg Cost/Tool"
          value={`$${(analytics?.avgCostPerTool ?? 0).toFixed(4)}`}
          trend="Actual API cost"
          icon={<Target className="h-5 w-5" />}
          color="orange"
        />
      </div>

      {/* Profit Margin Visualization */}
      <div className="bg-white dark:bg-neutral-900 rounded-lg border border-gray-200 dark:border-neutral-700 p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          Profit Margin
        </h2>
        <div className="flex items-center gap-6">
          <div className="flex-1">
            <div className="relative h-8 bg-gray-200 dark:bg-neutral-700 rounded-full overflow-hidden">
              <div
                className="absolute h-full bg-gradient-to-r from-emerald-500 to-emerald-600 rounded-full transition-all"
                style={{ width: `${analytics?.profitMargin ?? 0}%` }}
              />
            </div>
            <div className="flex justify-between mt-2 text-sm text-gray-600 dark:text-gray-400">
              <span>0%</span>
              <span className="font-medium text-emerald-600 dark:text-emerald-400">
                {(analytics?.profitMargin ?? 0).toFixed(2)}%
              </span>
              <span>100%</span>
            </div>
          </div>
          <div className="flex items-center gap-2 px-4 py-2 bg-emerald-50 dark:bg-emerald-900/20 rounded-lg">
            <Percent className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
            <div>
              <div className="text-sm text-gray-600 dark:text-gray-400">Profit</div>
              <div className="text-lg font-bold text-emerald-600 dark:text-emerald-400">
                ${((analytics?.totalRevenue ?? 0) - (analytics?.totalApiCost ?? 0)).toFixed(2)}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Top Tools */}
      <div className="bg-white dark:bg-neutral-900 rounded-lg border border-gray-200 dark:border-neutral-700 p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          Most Popular Tools
        </h2>
        {(analytics.topTools?.length ?? 0) > 0 ? (
          <div className="space-y-3">
            {(analytics.topTools ?? []).map((tool: ToolStats, index: number) => (
              <div
                key={tool.toolName}
                className="flex items-center justify-between p-3 bg-gray-50 dark:bg-neutral-800 rounded-lg"
              >
                <div className="flex items-center gap-3">
                  <span className="flex items-center justify-center w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 font-bold text-sm">
                    {index + 1}
                  </span>
                  <div>
                    <div className="font-medium text-gray-900 dark:text-gray-100">
                      {tool.toolLabel}
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">
                      {tool.executionCount} execution{tool.executionCount !== 1 ? 's' : ''}
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-semibold text-gray-900 dark:text-gray-100">
                    ${(tool?.totalRevenue ?? 0).toFixed(2)}
                  </div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">
                    ${(tool?.totalApiCost ?? 0).toFixed(4)} cost
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            No tool executions in this time period
          </div>
        )}
      </div>

      {/* Cache Efficiency */}
      <div className="bg-white dark:bg-neutral-900 rounded-lg border border-gray-200 dark:border-neutral-700 p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          Cache Efficiency
        </h2>
        <div className="grid grid-cols-3 gap-4">
          <div className="text-center">
            <div className="text-3xl font-bold text-blue-600 dark:text-blue-400">
              {(analytics?.cacheHitRate ?? 0).toFixed(1)}%
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">Hit Rate</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-emerald-600 dark:text-emerald-400">
              ${(analytics?.cacheSavings ?? 0).toFixed(2)}
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">Saved</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-purple-600 dark:text-purple-400">
              {Math.round(((analytics?.cacheHitRate ?? 0) / 100) * (analytics?.totalExecutions ?? 0))}
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">Cached Hits</div>
          </div>
        </div>
      </div>
    </div>
  );
}

interface KPICardProps {
  title: string;
  value: string;
  trend: string;
  icon: React.ReactNode;
  color: 'blue' | 'emerald' | 'purple' | 'orange';
}

function KPICard({ title, value, trend, icon, color }: KPICardProps) {
  const colorClasses = {
    blue: 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400',
    emerald: 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400',
    purple: 'bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400',
    orange: 'bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400',
  };

  return (
    <div className="bg-white dark:bg-neutral-900 rounded-lg border border-gray-200 dark:border-neutral-700 p-6">
      <div className="flex items-center justify-between mb-4">
        <span className="text-sm text-gray-600 dark:text-gray-400">{title}</span>
        <div className={`p-2 rounded-lg ${colorClasses[color]}`}>{icon}</div>
      </div>
      <div className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-1">{value}</div>
      <div className="text-xs text-gray-600 dark:text-gray-400">{trend}</div>
    </div>
  );
}
