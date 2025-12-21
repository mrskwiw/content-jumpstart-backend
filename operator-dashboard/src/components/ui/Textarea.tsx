import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { clsx } from 'clsx';

const textareaVariants = cva(
  'flex min-h-[80px] w-full rounded-lg border bg-white dark:bg-neutral-900 px-3 py-2 text-sm transition-colors placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-0 disabled:cursor-not-allowed disabled:opacity-50',
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

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement>,
    VariantProps<typeof textareaVariants> {
  label?: string;
  error?: string;
  helperText?: string;
  showCount?: boolean;
  maxLength?: number;
}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, variant, label, error, helperText, showCount, maxLength, id, value, ...props }, ref) => {
    const textareaId = id || `textarea-${Math.random().toString(36).substr(2, 9)}`;
    const hasError = !!error;
    const currentLength = typeof value === 'string' ? value.length : 0;

    return (
      <div className="w-full">
        {label && (
          <label
            htmlFor={textareaId}
            className="mb-2 block text-sm font-medium text-neutral-700 dark:text-neutral-300"
          >
            {label}
          </label>
        )}
        <textarea
          className={clsx(textareaVariants({ variant: hasError ? 'error' : variant }), className)}
          ref={ref}
          id={textareaId}
          maxLength={maxLength}
          value={value}
          {...props}
        />
        <div className="mt-1 flex items-center justify-between">
          <div>
            {error && (
              <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
            )}
            {helperText && !error && (
              <p className="text-sm text-neutral-500 dark:text-neutral-400">{helperText}</p>
            )}
          </div>
          {showCount && maxLength && (
            <p className="text-xs text-neutral-500 dark:text-neutral-400">
              {currentLength}/{maxLength}
            </p>
          )}
        </div>
      </div>
    );
  }
);

Textarea.displayName = 'Textarea';

export { Textarea, textareaVariants };
