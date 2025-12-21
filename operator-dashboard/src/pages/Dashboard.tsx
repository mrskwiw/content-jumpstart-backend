import { useAuth } from '@/contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { Button, Badge } from '@/components/ui';

export default function Dashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-neutral-100 dark:bg-neutral-950">
      <nav className="bg-white dark:bg-neutral-900 shadow-sm border-b border-neutral-200 dark:border-neutral-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <h1 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">Operator Dashboard</h1>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-sm">
                <span className="text-neutral-600 dark:text-neutral-400">Welcome,</span>{' '}
                <span className="font-medium text-neutral-900 dark:text-neutral-100">{user?.name || user?.email}</span>
              </div>
              <Badge variant="info">{user?.role}</Badge>
              <Button variant="ghost" onClick={handleLogout}>
                Logout
              </Button>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <div className="border-4 border-dashed border-neutral-200 dark:border-neutral-700 rounded-lg h-96 flex items-center justify-center bg-white dark:bg-neutral-900">
            <div className="text-center">
              <h2 className="text-2xl font-semibold text-neutral-700 dark:text-neutral-300 mb-4">
                Welcome to the Operator Dashboard
              </h2>
              <p className="text-neutral-500 dark:text-neutral-400">
                Phase 13 - Week 1 setup complete! Additional features coming in Week 2-8.
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
