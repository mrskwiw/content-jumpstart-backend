import { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';
import { Button } from '@/components/ui';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  isChunkError: boolean;
}

/**
 * ErrorBoundary component to catch and handle React errors gracefully
 *
 * Features:
 * - Catches chunk loading errors (dynamic import failures)
 * - Provides user-friendly error messages
 * - Offers reload and navigation options
 * - Logs errors for debugging
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      isChunkError: false,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    // Check if this is a chunk loading error
    const isChunkError =
      error.message.includes('Failed to fetch dynamically imported module') ||
      error.message.includes('Importing a module script failed') ||
      error.message.includes('error loading dynamically imported module');

    return {
      hasError: true,
      error,
      isChunkError,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log error details for debugging
    console.error('ErrorBoundary caught an error:', error, errorInfo);

    this.setState({
      error,
      errorInfo,
    });

    // You could send error to logging service here
    // Example: logErrorToService(error, errorInfo);
  }

  handleReload = () => {
    // Clear any cached data and reload
    window.location.reload();
  };

  handleGoHome = () => {
    // Navigate to home and reload to clear error state
    window.location.href = '/dashboard';
  };

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      isChunkError: false,
    });
  };

  render() {
    if (this.state.hasError) {
      // Use custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback;
      }

      const { error, isChunkError } = this.state;

      return (
        <div className="flex min-h-screen items-center justify-center bg-neutral-50 dark:bg-neutral-950 px-4">
          <div className="w-full max-w-md">
            <div className="rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 p-6 shadow-lg">
              {/* Icon */}
              <div className="flex justify-center mb-4">
                <div className="rounded-full bg-rose-100 dark:bg-rose-900/30 p-3">
                  <AlertTriangle className="h-8 w-8 text-rose-600 dark:text-rose-400" />
                </div>
              </div>

              {/* Title */}
              <h1 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100 text-center mb-2">
                {isChunkError ? 'Update Required' : 'Something Went Wrong'}
              </h1>

              {/* Description */}
              <p className="text-sm text-neutral-600 dark:text-neutral-400 text-center mb-6">
                {isChunkError ? (
                  <>
                    A new version of the application is available. Please reload the page to continue.
                  </>
                ) : (
                  <>
                    We encountered an unexpected error. This has been logged and we'll look into it.
                  </>
                )}
              </p>

              {/* Error details (only in development) */}
              {process.env.NODE_ENV === 'development' && error && (
                <div className="mb-6 rounded-md bg-neutral-100 dark:bg-neutral-800 p-3">
                  <p className="text-xs font-mono text-neutral-700 dark:text-neutral-300 break-all">
                    {error.toString()}
                  </p>
                </div>
              )}

              {/* Actions */}
              <div className="space-y-2">
                <Button
                  variant="primary"
                  className="w-full"
                  onClick={this.handleReload}
                >
                  <RefreshCw className="h-4 w-4 mr-2" />
                  {isChunkError ? 'Reload Page' : 'Reload Application'}
                </Button>

                {!isChunkError && (
                  <>
                    <Button
                      variant="secondary"
                      className="w-full"
                      onClick={this.handleGoHome}
                    >
                      <Home className="h-4 w-4 mr-2" />
                      Go to Dashboard
                    </Button>

                    <Button
                      variant="secondary"
                      className="w-full"
                      onClick={this.handleReset}
                    >
                      Try Again
                    </Button>
                  </>
                )}
              </div>

              {/* Help text */}
              <p className="text-xs text-neutral-500 dark:text-neutral-400 text-center mt-4">
                If this problem persists, please contact support.
              </p>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

/**
 * Hook-based error boundary wrapper for function components
 * Usage: Wrap routes or components that might fail
 */
export const withErrorBoundary = (
  Component: React.ComponentType<any>,
  fallback?: ReactNode
) => {
  return function WithErrorBoundary(props: any) {
    return (
      <ErrorBoundary fallback={fallback}>
        <Component {...props} />
      </ErrorBoundary>
    );
  };
};
