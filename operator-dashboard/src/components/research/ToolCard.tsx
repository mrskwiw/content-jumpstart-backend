import React, { memo } from 'react';
import { CheckCircle2, Clock, AlertCircle, Coins, Link2, Settings } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { ResearchTool } from '../../api/research';

interface ToolCardProps {
  tool: ResearchTool;
  isSelected: boolean;
  onToggle: () => void;
  executionStatus?: {
    executed: boolean;
    executionCount: number;
    lastRun?: string;
  };
  prerequisites?: {
    required: string[];
    recommended: string[];
  };
  toolLabels?: Record<string, string>;
  disabled?: boolean;
  missingIntegrations?: string[];
  completedTools?: string[];
}

export const ToolCard = memo(function ToolCard({ tool, isSelected, onToggle, executionStatus, prerequisites, toolLabels, disabled, missingIntegrations, completedTools }: ToolCardProps) {
  const categoryColors = {
    foundation: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
    seo: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    market: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    strategy: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
    workshop: 'bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-400',
    advanced: 'bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400',
  };

  const categoryColor = categoryColors[tool.category as keyof typeof categoryColors] || categoryColors.advanced;

  return (
    <div
      onClick={disabled ? undefined : onToggle}
      role="button"
      aria-label={`Select ${tool.label}`}
      tabIndex={disabled ? -1 : 0}
      onKeyDown={(e) => { if (!disabled && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); onToggle(); } }}
      className={`relative p-4 rounded-lg border-2 transition-all ${
        disabled ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'
      } ${
        isSelected
          ? 'border-blue-600 bg-blue-50 dark:bg-blue-900/20'
          : 'border-gray-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 hover:border-gray-300 dark:hover:border-neutral-600'
      }`}
    >
      {/* Selection Indicator */}
      {isSelected && (
        <div className="absolute top-3 right-3">
          <CheckCircle2 className="h-5 w-5 text-blue-600" />
        </div>
      )}

      {/* Category Badge */}
      <div className="flex items-center gap-2 mb-3">
        <span className={`px-2 py-1 text-xs font-medium rounded ${categoryColor}`}>
          {tool.category?.charAt(0).toUpperCase() + (tool.category?.slice(1) || '')}
        </span>
        {executionStatus?.executed && (
          <span className="px-2 py-1 text-xs font-medium rounded bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400">
            ✓ Run {executionStatus.executionCount}x
          </span>
        )}
      </div>

      {/* Tool Name */}
      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-1">
        {tool.label}
      </h3>

      {/* Credit Cost */}
      <div className="flex items-center gap-1.5 text-2xl font-bold text-blue-600 dark:text-blue-400 mb-2">
        <Coins className="h-6 w-6" />
        <span>{tool.credits || '—'} credits</span>
      </div>

      {/* Description */}
      <p className="text-sm text-gray-600 dark:text-gray-400 mb-3 line-clamp-2">
        {tool.description}
      </p>

      {/* Prerequisites */}
      {prerequisites && (prerequisites.required.length > 0 || prerequisites.recommended.length > 0) && (
        <div className="mb-3 space-y-2">
          {prerequisites.required.length > 0 && (
            <div className="flex flex-wrap items-center gap-1">
              <Link2 className="h-3 w-3 text-red-600 dark:text-red-400" />
              <span className="text-xs font-medium text-red-600 dark:text-red-400">Required:</span>
              {prerequisites.required.map((prereqTool) => {
                const isCompleted = completedTools?.includes(prereqTool);
                return (
                  <span
                    key={prereqTool}
                    className={"inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium " + (
                      isCompleted
                        ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400"
                        : "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400"
                    )}
                  >
                    {isCompleted && <CheckCircle2 className="h-3 w-3" />}
                    {toolLabels?.[prereqTool] || prereqTool}
                  </span>
                );
              })}
            </div>
          )}
          {prerequisites.recommended.length > 0 && (
            <div className="flex flex-wrap items-center gap-1">
              <Link2 className="h-3 w-3 text-blue-600 dark:text-blue-400" />
              <span className="text-xs font-medium text-blue-600 dark:text-blue-400">Recommended:</span>
              {prerequisites.recommended.map((prereqTool) => {
                const isCompleted = completedTools?.includes(prereqTool);
                return (
                  <span
                    key={prereqTool}
                    className={"inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium " + (
                      isCompleted
                        ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400"
                        : "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400"
                    )}
                  >
                    {isCompleted && <CheckCircle2 className="h-3 w-3" />}
                    {toolLabels?.[prereqTool] || prereqTool}
                  </span>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Integration Warning */}
      {missingIntegrations && missingIntegrations.length > 0 && (
        <div className="mt-3 rounded-md bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 px-3 py-2">
          <div className="flex items-start gap-2">
            <Settings className="h-4 w-4 flex-shrink-0 text-red-600 dark:text-red-400 mt-0.5" />
            <div className="flex-1 text-xs">
              <p className="font-semibold text-red-700 dark:text-red-400">Integration Required</p>
              <p className="mt-1 text-red-600 dark:text-red-400">{missingIntegrations.join(', ')}</p>
              <a
                href="/dashboard/settings?tab=integrations"
                onClick={(e) => e.stopPropagation()}
                className="mt-1.5 inline-block text-red-600 dark:text-red-400 underline hover:text-red-800 dark:hover:text-red-300"
              >
                Configure in Settings →
              </a>
            </div>
          </div>
        </div>
      )}

      {/* Execution Status */}
      {executionStatus?.executed && executionStatus.lastRun && (
        <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
          <Clock className="h-3 w-3" />
          <span>Last run: {formatDistanceToNow(new Date(executionStatus.lastRun), { addSuffix: true })}</span>
        </div>
      )}

      {/* Coming Soon Status */}
      {tool.status === 'coming_soon' && (
        <div className="flex items-center gap-1 text-xs text-orange-600 dark:text-orange-400">
          <AlertCircle className="h-3 w-3" />
          <span>Coming Soon</span>
        </div>
      )}
    </div>
  );
});
