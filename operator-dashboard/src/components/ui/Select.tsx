import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { clsx } from 'clsx';

const selectVariants = cva(
  'flex w-full rounded-lg border bg-white dark:bg-neutral-900 px-3 py-2 text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-0 disabled:cursor-not-allowed disabled:opacity-50',
  {
    variants: {
      variant: {
        default:
          'border-neutral-300 dark:border-neutral-600 text-neutral-900 dark:text-neutral-100 focus:border-primary-500 dark:focus:border-primary-400',
        error:
          'border-red-300 dark:border-red-600 text-neutral-900 dark:text-neutral-100 focus:border-red-500 dark:focus:border-red-400 focus:ring-red-500',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
);

export interface SelectProps
  extends React.SelectHTMLAttributes<HTMLSelectElement>,
    VariantProps<typeof selectVariants> {
  label?: string;
  error?: string;
  helperText?: string;
}

const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, variant, label, error, helperText, id, children, ...props }, ref) => {
    // SECURITY FIX: Use useId() instead of Math.random() for React purity (TR-016)
    const generatedId = React.useId();
    const selectId = id || `select-${generatedId}`;
    const hasError = !!error;

    return (
      <div className="w-full">
        {label && (
          <label
            htmlFor={selectId}
            className="mb-2 block text-sm font-medium text-neutral-700 dark:text-neutral-300"
          >
            {label}
          </label>
        )}
        <select
          className={clsx(selectVariants({ variant: hasError ? 'error' : variant }), className)}
          ref={ref}
          id={selectId}
          {...props}
        >
          {children}
        </select>
        {error && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error}</p>
        )}
        {helperText && !error && (
          <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">{helperText}</p>
        )}
      </div>
    );
  }
);

Select.displayName = 'Select';

export { Select, selectVariants };
