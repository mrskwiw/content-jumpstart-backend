import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { clsx } from 'clsx';

const badgeVariants = cva(
  'inline-flex items-center rounded-full font-medium transition-colors',
  {
    variants: {
      variant: {
        default:
          'bg-neutral-100 dark:bg-neutral-800 text-neutral-800 dark:text-neutral-300 border border-neutral-200 dark:border-neutral-700',
        primary:
          'bg-primary-100 dark:bg-primary-900/20 text-primary-800 dark:text-primary-300',
        secondary:
          'bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300',
        success:
          'bg-emerald-100 dark:bg-emerald-900/20 text-emerald-800 dark:text-emerald-300',
        warning:
          'bg-amber-100 dark:bg-amber-900/20 text-amber-800 dark:text-amber-300',
        danger:
          'bg-red-100 dark:bg-red-900/20 text-red-800 dark:text-red-300',
        info:
          'bg-blue-100 dark:bg-blue-900/20 text-blue-800 dark:text-blue-300',
        purple:
          'bg-purple-100 dark:bg-purple-900/20 text-purple-800 dark:text-purple-300',
        orange:
          'bg-orange-100 dark:bg-orange-900/20 text-orange-800 dark:text-orange-300',
        // Status-specific variants
        draft:
          'bg-neutral-100 dark:bg-neutral-800 text-neutral-800 dark:text-neutral-300',
        ready:
          'bg-emerald-100 dark:bg-emerald-900/20 text-emerald-800 dark:text-emerald-300',
        generating:
          'bg-primary-100 dark:bg-primary-900/20 text-primary-800 dark:text-primary-300',
        qa:
          'bg-amber-100 dark:bg-amber-900/20 text-amber-800 dark:text-amber-300',
        exported:
          'bg-purple-100 dark:bg-purple-900/20 text-purple-800 dark:text-purple-300',
        delivered:
          'bg-emerald-100 dark:bg-emerald-900/20 text-emerald-800 dark:text-emerald-300',
        error:
          'bg-rose-100 dark:bg-rose-900/20 text-rose-800 dark:text-rose-300',
      },
      size: {
        sm: 'px-2 py-0.5 text-xs',
        md: 'px-2.5 py-0.5 text-xs',
        lg: 'px-3 py-1 text-sm',
      },
      removable: {
        true: 'pr-1',
        false: '',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'md',
      removable: false,
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {
  onRemove?: () => void;
}

const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant, size, removable, onRemove, children, ...props }, ref) => {
    const hasRemove = removable || !!onRemove;

    return (
      <span
        ref={ref}
        className={clsx(badgeVariants({ variant, size, removable: hasRemove }), className)}
        {...props}
      >
        {children}
        {hasRemove && onRemove && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onRemove();
            }}
            className="ml-1 inline-flex h-4 w-4 items-center justify-center rounded-full hover:bg-black/10 dark:hover:bg-white/10 focus:outline-none"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              className="h-3 w-3"
            >
              <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
            </svg>
          </button>
        )}
      </span>
    );
  }
);

Badge.displayName = 'Badge';

export { Badge, badgeVariants };
