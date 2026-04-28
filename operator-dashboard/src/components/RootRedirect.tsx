import { Navigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';

/**
 * Root route handler that redirects based on authentication status
 * - Authenticated users → /dashboard
 * - Unauthenticated users → /login
 * - Shows loading spinner during auth check (prevents flash)
 */
export default function RootRedirect() {
  const { isAuthenticated, isLoading } = useAuth();

  // Show loading state while checking authentication
  // This prevents the flash of login page for authenticated users
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-neutral-900">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600 dark:text-gray-400">Loading...</p>
        </div>
      </div>
    );
  }

  // Redirect based on authentication status
  // Show the portfolio/WIP splash once per session for authenticated users
  if (isAuthenticated) {
    let seen = null;
    try {
      seen = sessionStorage.getItem('portfolioNoticeSeen');
    } catch {
      seen = null;
    }
    return <Navigate to={seen ? '/dashboard' : '/portfolio-notice'} replace />;
  }
  return <Navigate to="/login" replace />;
}
