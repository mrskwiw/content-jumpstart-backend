import { LogOut, PanelsTopLeft, FileStack, ClipboardList, Settings, Rocket, Users, Library, FileSearch, BarChart3, Coins, Globe, Share2, Send, TrendingUp, Clapperboard, Film } from 'lucide-react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/contexts/AuthContext';
import ThemeToggle from '@/components/ui/ThemeToggle';
import AIAssistantSidebar from '@/components/ui/AIAssistantSidebar';
import { creditsApi } from '@/api/credits';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';

const navItems = [
  { to: '/dashboard', label: 'Overview', icon: PanelsTopLeft, end: true },
  { to: '/dashboard/projects', label: 'Projects', icon: ClipboardList },
  { to: '/dashboard/clients', label: 'Clients', icon: Users },
  { to: '/dashboard/deliverables', label: 'Deliverables', icon: FileStack },
  { to: '/dashboard/wizard', label: 'Wizard / QA', icon: Rocket },
  { to: '/dashboard/settings', label: 'Settings', icon: Settings },
];

const distributionItems = [
  { to: '/dashboard/media/generate', label: 'Generate Media', icon: Clapperboard },
  { to: '/dashboard/media/jobs', label: 'Media Jobs', icon: Film },
  { to: '/dashboard/settings/connections', label: 'Connections', icon: Share2 },
  { to: '/dashboard/distribution/queue', label: 'Publishing Queue', icon: Send },
  { to: '/dashboard/engagement', label: 'Engagement', icon: TrendingUp },
];

const researchToolsItems = [
  { to: '/dashboard/research-tools/library', label: 'Tool Library', icon: Library },
  { to: '/dashboard/research-tools/results', label: 'Results', icon: FileSearch },
  { to: '/dashboard/research-tools/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/dashboard/research-tools/client-research', label: 'Client Research', icon: Globe },
];

export default function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  // Fetch credit balance — only when authenticated; don't retry on 401 (token expired)
  const { data: creditBalance } = useQuery({
    queryKey: ['credits', 'balance'],
    queryFn: () => creditsApi.getBalance(),
    enabled: !!user,
    refetchInterval: 30000,
    retry: (failureCount, error) => {
      const status = (error as { response?: { status?: number } })?.response?.status;
      if (status === 401 || status === 403) return false;
      return failureCount < 2;
    },
  });

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const handleBuyCredits = () => {
    // TODO: Open purchase modal
    navigate('/dashboard/settings?tab=credits');
  };

  return (
    <div className="min-h-screen bg-neutral-50 dark:bg-neutral-950">
      <header className="border-b border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900">
        <div className="mx-auto flex h-14 items-center justify-between px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-2">
            <div className="h-9 w-9 rounded-lg bg-primary-500 text-primary-50 flex items-center justify-center font-semibold">
              O
            </div>
            <div>
              <p className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">Operator Dashboard</p>
              <p className="text-xs text-neutral-500 dark:text-neutral-400">Content Jumpstart</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {/* Credit Balance Display */}
            {creditBalance && (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-md border border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800">
                <Coins className="h-4 w-4 text-yellow-500" />
                <span className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                  {creditBalance.balance.toLocaleString()}
                </span>
                <span className="text-xs text-neutral-500 dark:text-neutral-400">credits</span>
                {creditBalance.is_enterprise && (
                  <Badge variant="secondary" className="text-xs ml-1">
                    Enterprise
                  </Badge>
                )}
              </div>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={handleBuyCredits}
              className="text-xs"
            >
              Buy Credits
            </Button>
            <ThemeToggle />
            <div className="text-right">
              <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">{user?.fullName || user?.email}</p>
              <p className="text-xs text-neutral-500 dark:text-neutral-400 capitalize">{user?.isSuperuser ? 'Admin' : 'Operator'}</p>
            </div>
            <button
              onClick={handleLogout}
              className="inline-flex items-center gap-1 rounded-md border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 px-3 py-1.5 text-sm font-medium text-neutral-700 dark:text-neutral-200 shadow-sm hover:bg-neutral-50 dark:hover:bg-neutral-700"
            >
              <LogOut className="h-4 w-4" />
              Logout
            </button>
          </div>
        </div>
      </header>
      <div className="mx-auto flex max-w-7xl gap-6 px-4 py-6 sm:px-6 lg:px-8">
        <aside className="hidden w-60 flex-shrink-0 md:block">
          <nav className="space-y-1 rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-2 shadow-sm">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) =>
                    [
                      'flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                      isActive
                        ? 'bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300 border-l-2 border-primary-500'
                        : 'text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800',
                    ].join(' ')
                  }
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </NavLink>
              );
            })}

            {/* Research Tools Section */}
            <div className="pt-4 mt-4 border-t border-neutral-200 dark:border-neutral-700">
              <div className="px-3 py-2 text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
                Research Tools
              </div>
              {researchToolsItems.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    className={({ isActive }) =>
                      [
                        'flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                        isActive
                          ? 'bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300 border-l-2 border-primary-500'
                          : 'text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800',
                      ].join(' ')
                    }
                  >
                    <Icon className="h-4 w-4" />
                    {item.label}
                  </NavLink>
                );
              })}
            </div>

            {/* Distribution Section */}
            <div className="pt-4 mt-4 border-t border-neutral-200 dark:border-neutral-700">
              <div className="px-3 py-2 text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
                Distribution
              </div>
              {distributionItems.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    className={({ isActive }) =>
                      [
                        'flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                        isActive
                          ? 'bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300 border-l-2 border-primary-500'
                          : 'text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800',
                      ].join(' ')
                    }
                  >
                    <Icon className="h-4 w-4" />
                    {item.label}
                  </NavLink>
                );
              })}
            </div>
          </nav>
        </aside>
        <main className="flex-1">
          <Outlet />
        </main>
      </div>

      {/* AI Assistant Sidebar - Available on all pages */}
      <AIAssistantSidebar />
    </div>
  );
}
