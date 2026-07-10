import { toast } from 'sonner';

/**
 * Research tool execution result notifications
 * Standardized success and failure messaging for research tools
 */

export interface ResearchSuccessOptions {
  toolName: string;
  toolLabel?: string;
  summary?: string;
  metrics?: {
    count?: number;
    duration?: number;
  };
  onViewResults?: () => void;
}

export interface ResearchErrorOptions {
  toolName: string;
  toolLabel?: string;
  error: string;
  actionMessage?: string;
  onRetry?: () => void;
  onHelp?: () => void;
}

/**
 * Show success notification for research tool execution
 */
export function notifyResearchSuccess(options: ResearchSuccessOptions) {
  const {
    toolName,
    toolLabel,
    summary,
    metrics,
    onViewResults,
  } = options;

  const displayName = toolLabel || toolName;
  const timestamp = new Date().toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
  });

  // Build description with metrics if available
  let description = summary || 'Research complete';

  if (metrics) {
    const metricParts: string[] = [];
    if (metrics.count !== undefined) {
      metricParts.push(`${metrics.count} results`);
    }
    if (metrics.duration !== undefined) {
      const seconds = Math.round(metrics.duration);
      metricParts.push(`took ${seconds}s`);
    }
    if (metricParts.length > 0) {
      description += ` • ${metricParts.join(', ')}`;
    }
  }

  description += ` • ${timestamp}`;

  toast.success(`${displayName} - Complete`, {
    description,
    duration: 5000,
    action: onViewResults
      ? {
          label: 'View Results',
          onClick: onViewResults,
        }
      : undefined,
  });
}

/**
 * Show error notification for research tool execution
 */
export function notifyResearchError(options: ResearchErrorOptions) {
  const {
    toolName,
    toolLabel,
    error,
    actionMessage,
    onRetry,
  } = options;

  const displayName = toolLabel || toolName;
  const timestamp = new Date().toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
  });

  // Build description with error and action message
  let description = error;

  if (actionMessage) {
    description += `\n\n${actionMessage}`;
  }

  description += `\n\nFailed at ${timestamp}`;

  toast.error(`${displayName} - Failed`, {
    description,
    duration: 10000, // Longer duration for errors
    action: onRetry
      ? {
          label: 'Retry',
          onClick: onRetry,
        }
      : undefined,
  });
}

/**
 * Get a user-friendly tool label from tool name
 * Converts snake_case to Title Case
 */
export function getToolLabel(toolName: string): string {
  return toolName
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

/**
 * Extract key metrics from research result data
 */
export function extractResearchMetrics(
  outputs: Record<string, string>
): { count?: number; summary?: string } {
  const metrics: { count?: number; summary?: string } = {};

  // Try to find count in common output field names
  const countFields = [
    'keyword_count',
    'competitor_count',
    'insights_count',
    'results_count',
    'total',
  ];

  for (const field of countFields) {
    if (outputs[field]) {
      const parsed = parseInt(outputs[field], 10);
      if (!isNaN(parsed)) {
        metrics.count = parsed;
        break;
      }
    }
  }

  // Try to extract summary from description fields
  const summaryFields = ['summary', 'description', 'overview'];

  for (const field of summaryFields) {
    if (outputs[field] && outputs[field].length > 0) {
      // Take first 100 characters
      metrics.summary = outputs[field].substring(0, 100);
      if (outputs[field].length > 100) {
        metrics.summary += '...';
      }
      break;
    }
  }

  return metrics;
}
