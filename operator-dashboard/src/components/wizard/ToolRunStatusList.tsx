import { AlertCircle, CheckCircle2, Circle, Loader2 } from 'lucide-react';

export interface ToolStatusItem {
  name: string;
  label: string;
  status: 'pending' | 'running' | 'complete' | 'failed' | 'blocked';
  error?: string;
}

interface Props {
  items: ToolStatusItem[];
}

export function ToolRunStatusList({ items }: Props) {
  return (
    <div className="w-full max-w-2xl divide-y divide-neutral-100 dark:divide-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 overflow-hidden">
      {items.map(({ name, label, status, error }) => (
        <div
          key={name}
          className={`flex items-center gap-3 px-4 py-2.5 text-sm ${
            status === 'running'
              ? 'bg-blue-50 dark:bg-blue-900/20'
              : status === 'complete'
              ? 'bg-white dark:bg-neutral-800'
              : status === 'failed'
              ? 'bg-red-50 dark:bg-red-900/10'
              : status === 'blocked'
              ? 'bg-amber-50 dark:bg-amber-900/10'
              : 'bg-neutral-50 dark:bg-neutral-800/50'
          }`}
        >
          <span className="shrink-0">
            {status === 'running' && <Loader2 className="h-4 w-4 animate-spin text-blue-500" />}
            {status === 'complete' && <CheckCircle2 className="h-4 w-4 text-emerald-500" />}
            {status === 'failed' && <AlertCircle className="h-4 w-4 text-red-500" />}
            {status === 'blocked' && <AlertCircle className="h-4 w-4 text-amber-500" />}
            {status === 'pending' && <Circle className="h-4 w-4 text-neutral-300 dark:text-neutral-600" />}
          </span>

          <span
            className={`flex-1 font-medium ${
              status === 'running'
                ? 'text-blue-700 dark:text-blue-300'
                : status === 'complete'
                ? 'text-neutral-800 dark:text-neutral-200'
                : status === 'failed'
                ? 'text-red-700 dark:text-red-300'
                : status === 'blocked'
                ? 'text-amber-700 dark:text-amber-300'
                : 'text-neutral-400 dark:text-neutral-500'
            }`}
          >
            {label}
            {error && (
              <span
                className={`ml-2 text-xs font-normal ${
                  status === 'blocked'
                    ? 'text-amber-600 dark:text-amber-400'
                    : 'text-red-600 dark:text-red-400'
                }`}
              >
                — {status === 'blocked' ? 'prerequisite failed' : error}
              </span>
            )}
          </span>

          <span
            className={`shrink-0 text-xs font-medium ${
              status === 'running'
                ? 'text-blue-600 dark:text-blue-400'
                : status === 'complete'
                ? 'text-emerald-600 dark:text-emerald-400'
                : status === 'failed'
                ? 'text-red-600 dark:text-red-400'
                : status === 'blocked'
                ? 'text-amber-600 dark:text-amber-400'
                : 'text-neutral-400 dark:text-neutral-500'
            }`}
          >
            {status === 'running'
              ? 'Running'
              : status === 'complete'
              ? 'Done'
              : status === 'blocked'
              ? 'Blocked'
              : status === 'failed'
              ? 'Failed'
              : 'Pending'}
          </span>
        </div>
      ))}
    </div>
  );
}
