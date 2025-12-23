interface StepperProps {
  steps: { key: string; label: string }[];
  active: string;
  maxReached?: string;
  onChange?: (key: string) => void;
}

export function WizardStepper({ steps, active, maxReached, onChange }: StepperProps) {
  const maxReachedIndex = maxReached ? steps.findIndex(s => s.key === maxReached) : 0;

  return (
    <div className="flex flex-wrap gap-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-neutral-800 p-3 shadow-sm">
      {steps.map((step, idx) => {
        const isActive = step.key === active;
        const isReached = idx <= maxReachedIndex;
        const isDisabled = !isReached;

        return (
          <button
            key={step.key}
            onClick={() => isReached && onChange?.(step.key)}
            disabled={isDisabled}
            className={[
              'flex items-center gap-2 rounded-md px-3 py-2 text-sm font-semibold transition-colors',
              isActive
                ? 'bg-blue-600 text-white'
                : isReached
                ? 'bg-slate-100 dark:bg-slate-700 text-slate-800 dark:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-600'
                : 'bg-slate-50 dark:bg-slate-800 text-slate-400 dark:text-slate-600 cursor-not-allowed opacity-50',
            ].join(' ')}
            title={isDisabled ? 'Complete previous steps to unlock' : step.label}
          >
            <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-white/20 text-xs">
              {idx + 1}
            </span>
            {step.label}
          </button>
        );
      })}
    </div>
  );
}
