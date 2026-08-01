import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { Users, FolderKanban, Coins, DollarSign, type LucideIcon } from 'lucide-react';
import { Button, Badge } from '@/components/ui';
import { ROUTES } from '@/config/routes';
import { clientsApi } from '@/api/clients';
import { projectsApi } from '@/api/projects';
import { creditsApi } from '@/api/credits';
import { costsApi } from '@/api/costs';

interface StatCardProps {
  label: string;
  value: string | number;
  icon: LucideIcon;
  isLoading: boolean;
  isError: boolean;
}

function StatCard({ label, value, icon: Icon, isLoading, isError }: StatCardProps) {
  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-5 dark:border-neutral-700 dark:bg-neutral-900">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-neutral-500 dark:text-neutral-400">{label}</span>
        <Icon className="h-5 w-5 text-neutral-400 dark:text-neutral-500" />
      </div>
      <div className="mt-2 text-2xl font-semibold text-neutral-900 dark:text-neutral-100">
        {isLoading ? (
          <span className="text-neutral-400 dark:text-neutral-600">…</span>
        ) : isError ? (
          <span className="text-base font-normal text-red-500 dark:text-red-400">Unavailable</span>
        ) : (
          value
        )}
      </div>
    </div>
  );
}

export default function Dashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate(ROUTES.LOGIN);
  };

  // Shared cache keys (consistent with the rest of the app, so Dashboard dedupes with
  // e.g. ContentReview). Cross-user isolation is handled centrally: AuthContext clears
  // the singleton QueryClient on login/logout, so no prior operator's data survives an
  // auth transition on the same tab.
  const clients = useQuery({ queryKey: ['clients'], queryFn: () => clientsApi.list() });
  const projects = useQuery({ queryKey: ['projects'], queryFn: () => projectsApi.list() });
  const credits = useQuery({ queryKey: ['credits', 'balance'], queryFn: () => creditsApi.getBalance() });
  const costs = useQuery({
    queryKey: ['costs', 'summary', 30],
    queryFn: () => costsApi.getUserCostSummary(30),
  });

  const clientCount = clients.data?.length ?? 0;
  const projectCount = projects.data?.total ?? projects.data?.items?.length ?? 0;
  const creditBalance = credits.data?.balance ?? 0;
  const spend30d = costs.data?.totalCostUsd ?? 0;

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
                <span className="font-medium text-neutral-900 dark:text-neutral-100">{user?.fullName || user?.email}</span>
              </div>
              <Badge variant="info">{user?.isSuperuser ? 'Admin' : 'Operator'}</Badge>
              <Button variant="ghost" onClick={handleLogout}>
                Logout
              </Button>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        <div className="py-2">
          <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
            Your workspace at a glance
          </h2>
          <p className="text-sm text-neutral-500 dark:text-neutral-400">
            Live totals across your clients, projects, and credit usage.
          </p>
        </div>

        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            label="Clients"
            value={clientCount.toLocaleString()}
            icon={Users}
            isLoading={clients.isLoading}
            isError={clients.isError}
          />
          <StatCard
            label="Projects"
            value={projectCount.toLocaleString()}
            icon={FolderKanban}
            isLoading={projects.isLoading}
            isError={projects.isError}
          />
          <StatCard
            label="Credit balance"
            value={creditBalance.toLocaleString()}
            icon={Coins}
            isLoading={credits.isLoading}
            isError={credits.isError}
          />
          <StatCard
            label="Spend (30d)"
            value={`$${spend30d.toFixed(2)}`}
            icon={DollarSign}
            isLoading={costs.isLoading}
            isError={costs.isError}
          />
        </div>
      </main>
    </div>
  );
}
