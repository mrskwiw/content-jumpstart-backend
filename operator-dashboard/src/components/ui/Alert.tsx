import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { clsx } from 'clsx';
import { AlertCircle, CheckCircle2, Info, AlertTriangle, X } from 'lucide-react';

const alertVariants = cva(
  'relative w-full rounded-lg border p-4 transition-all',
  {
    variants: {
      variant: {
        default:
          'bg-neutral-50 dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 border-neutral-200 dark:border-neutral-700',
        info:
          'bg-blue-50 dark:bg-blue-900/20 text-blue-900 dark:text-blue-100 border-blue-200 dark:border-blue-700',
        success:
          'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-900 dark:text-emerald-100 border-emerald-200 dark:border-emerald-700',
        warning:
          'bg-amber-50 dark:bg-amber-900/20 text-amber-900 dark:text-amber-100 border-amber-200 dark:border-amber-700',
        danger:
          'bg-red-50 dark:bg-red-900/20 text-red-900 dark:text-red-100 border-red-200 dark:border-red-700',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
);

const iconMap = {
  default: Info,
  info: Info,
  success: CheckCircle2,
  warning: AlertTriangle,
  danger: AlertCircle,
};

const iconColorMap = {
  default: 'text-neutral-600 dark:text-neutral-400',
  info: 'text-blue-600 dark:text-blue-400',
  success: 'text-emerald-600 dark:text-emerald-400',
  warning: 'text-amber-600 dark:text-amber-400',
  danger: 'text-red-600 dark:text-red-400',
};

export interface AlertProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof alertVariants> {
  onClose?: () => void;
  icon?: React.ReactNode;
  showIcon?: boolean;
}

const Alert = React.forwardRef<HTMLDivElement, AlertProps>(
  ({ className, variant = 'default', onClose, icon, showIcon = true, children, ...props }, ref) => {
    const currentVariant = variant || 'default';
    const Icon = iconMap[currentVariant];

    return (
      <div
        ref={ref}
        role="alert"
        className={clsx(alertVariants({ variant: currentVariant }), className)}
        {...props}
      >
        <div className="flex gap-3">
          {showIcon && (
            <div className={clsx('flex-shrink-0', iconColorMap[currentVariant])}>
              {icon || <Icon className="h-5 w-5" />}
            </div>
          )}
          <div className="flex-1">{children}</div>
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className={clsx(
                'flex-shrink-0 inline-flex items-center justify-center rounded-md p-1 transition-colors hover:bg-black/10 dark:hover:bg-white/10',
                iconColorMap[currentVariant]
              )}
            >
              <X className="h-4 w-4" />
              <span className="sr-only">Close</span>
            </button>
          )}
        </div>
      </div>
    );
  }
);

Alert.displayName = 'Alert';

const AlertTitle = React.forwardRef<
  HTMLHeadingElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h5
    ref={ref}
    className={clsx('mb-1 font-semibold leading-none tracking-tight', className)}
    {...props}
  />
));
AlertTitle.displayName = 'AlertTitle';

const AlertDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={clsx('text-sm opacity-90', className)}
    {...props}
  />
));
AlertDescription.displayName = 'AlertDescription';

export { Alert, AlertTitle, AlertDescription };
