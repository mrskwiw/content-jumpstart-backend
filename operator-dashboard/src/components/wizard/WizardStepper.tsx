interface StepperProps {
  steps: { key: string; label: string }[];
  active: string;
  onChange?: (key: string) => void;
}

export function WizardStepper({ steps, active, onChange }: StepperProps) {
  return (
    <div className="flex flex-wrap gap-2 rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
      {steps.map((step, idx) => {
        const isActive = step.key === active;
        return (
          <button
            key={step.key}
            onClick={() => onChange?.(step.key)}
            className={[
              'flex items-center gap-2 rounded-md px-3 py-2 text-sm font-semibold transition-colors',
              isActive ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-800 hover:bg-slate-200',
            ].join(' ')}
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
