import { Check } from 'lucide-react';

export type ProjectStatus = 'draft' | 'generating' | 'qa' | 'ready' | 'exported' | 'delivered' | 'error';

interface StatusProgressBarProps {
  status: ProjectStatus;
  size?: 'sm' | 'md' | 'lg';
  showLabels?: boolean;
}

const STATUS_ORDER: ProjectStatus[] = ['draft', 'generating', 'qa', 'ready', 'delivered'];

const STATUS_LABELS: Record<ProjectStatus, string> = {
  draft: 'Draft',
  generating: 'Generating',
  qa: 'QA Review',
  ready: 'Ready',
  exported: 'Exported',
  delivered: 'Delivered',
  error: 'Error',
};

export function StatusProgressBar({ status, size = 'md', showLabels = false }: StatusProgressBarProps) {
  // Handle error and exported states
  if (status === 'error') {
    return (
      <div className="flex items-center gap-2">
        <div className="flex-1 h-2 rounded-full bg-rose-100 dark:bg-rose-900/20">
          <div className="h-full rounded-full bg-rose-600 dark:bg-rose-500" style={{ width: '100%' }} />
        </div>
        <span className="text-xs font-medium text-rose-600 dark:text-rose-400">Error</span>
      </div>
    );
  }

  // Treat exported as delivered for progress purposes
  const normalizedStatus = status === 'exported' ? 'delivered' : status;
  const currentIndex = STATUS_ORDER.indexOf(normalizedStatus);
  const progressPercentage = currentIndex >= 0 ? ((currentIndex + 1) / STATUS_ORDER.length) * 100 : 0;

  const sizeClasses = {
    sm: 'h-1.5',
    md: 'h-2',
    lg: 'h-2.5',
  };

  const dotSizeClasses = {
    sm: 'h-3 w-3',
    md: 'h-4 w-4',
    lg: 'h-5 w-5',
  };

  const iconSizeClasses = {
    sm: 'h-2 w-2',
    md: 'h-2.5 w-2.5',
    lg: 'h-3 w-3',
  };

  if (!showLabels) {
    return (
      <div className="flex items-center gap-2">
        <div className={`flex-1 rounded-full bg-neutral-200 dark:bg-neutral-700 ${sizeClasses[size]}`}>
          <div
            className={`${sizeClasses[size]} rounded-full bg-gradient-to-r from-primary-500 to-primary-600 dark:from-primary-400 dark:to-primary-500 transition-all duration-500`}
            style={{ width: `${progressPercentage}%` }}
          />
        </div>
        <span className="text-xs font-medium text-neutral-600 dark:text-neutral-400 min-w-[60px]">
          {STATUS_LABELS[status]}
        </span>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {/* Progress bar with labels */}
      <div className="relative">
        {/* Background bar */}
        <div className={`w-full rounded-full bg-neutral-200 dark:bg-neutral-700 ${sizeClasses[size]}`}>
          <div
            className={`${sizeClasses[size]} rounded-full bg-gradient-to-r from-primary-500 to-primary-600 dark:from-primary-400 dark:to-primary-500 transition-all duration-500`}
            style={{ width: `${progressPercentage}%` }}
          />
        </div>

        {/* Status dots */}
        <div className="absolute top-1/2 -translate-y-1/2 left-0 right-0 flex justify-between px-0.5">
          {STATUS_ORDER.map((stepStatus, index) => {
            const isCompleted = index <= currentIndex;
            const isCurrent = index === currentIndex;

            return (
              <div
                key={stepStatus}
                className={`${dotSizeClasses[size]} rounded-full border-2 flex items-center justify-center transition-all ${
                  isCompleted
                    ? 'bg-primary-600 dark:bg-primary-500 border-primary-600 dark:border-primary-500'
                    : 'bg-white dark:bg-neutral-800 border-neutral-300 dark:border-neutral-600'
                } ${isCurrent ? 'ring-2 ring-primary-200 dark:ring-primary-900/50 ring-offset-1' : ''}`}
              >
                {isCompleted && (
                  <Check className={`${iconSizeClasses[size]} text-white`} />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Labels */}
      <div className="flex justify-between text-xs">
        {STATUS_ORDER.map((stepStatus, index) => {
          const isCompleted = index <= currentIndex;
          const isCurrent = index === currentIndex;

          return (
            <span
              key={stepStatus}
              className={`transition-colors ${
                isCurrent
                  ? 'font-semibold text-primary-600 dark:text-primary-400'
                  : isCompleted
                  ? 'text-neutral-700 dark:text-neutral-300'
                  : 'text-neutral-400 dark:text-neutral-500'
              }`}
            >
              {STATUS_LABELS[stepStatus]}
            </span>
          );
        })}
      </div>
    </div>
  );
}
