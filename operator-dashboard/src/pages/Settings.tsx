import { useSearchParams } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Settings as SettingsIcon, Server, Zap, Bell, Shield, HardDrive, Users, Coins, Save } from 'lucide-react';

import { IntegrationsTab } from '@/components/settings/IntegrationsTab';
import { WorkflowsTab } from '@/components/settings/WorkflowsTab';
import { NotificationsTab } from '@/components/settings/NotificationsTab';
import { PreferencesTab } from '@/components/settings/PreferencesTab';
import { SecurityTab } from '@/components/settings/SecurityTab';
import { CreditsTab } from '@/components/settings/CreditsTab';
import { DatabaseTab } from '@/components/settings/DatabaseTab';
import UsersTab from '@/components/settings/UsersTab';

type TabId = 'integrations' | 'workflows' | 'notifications' | 'preferences' | 'security' | 'credits' | 'database' | 'users';

const TABS: Array<{ id: TabId; label: string; icon: React.ElementType; adminOnly?: boolean }> = [
  { id: 'integrations', label: 'Integrations', icon: Server },
  { id: 'workflows', label: 'Workflows', icon: Zap },
  { id: 'notifications', label: 'Notifications', icon: Bell },
  { id: 'preferences', label: 'Preferences', icon: SettingsIcon },
  { id: 'security', label: 'Security', icon: Shield },
  { id: 'credits', label: 'Credits', icon: Coins },
  { id: 'database', label: 'Database', icon: HardDrive },
  { id: 'users', label: 'Users', icon: Users, adminOnly: true },
];

export default function Settings() {
  const { user } = useAuth();
  const isAdmin = user?.isSuperuser === true;
  const isSuperAdmin = isAdmin;

  const [searchParams, setSearchParams] = useSearchParams();

  const visibleTabs = TABS.filter(t => !t.adminOnly || (t.adminOnly && isAdmin));

  // The URL query param is the single source of truth for the active tab, so tab state
  // and the URL stay in sync in BOTH directions: deep-links (?tab=credits) and later
  // navigations resolve to the right tab, and clicking a tab updates the URL. An unknown
  // or not-permitted tab falls back to Integrations. No local state / effect needed, so
  // there is no stale-tab window and no setState-in-effect.
  const tabParam = searchParams.get('tab');
  const activeTab: TabId = visibleTabs.some(t => t.id === tabParam)
    ? (tabParam as TabId)
    : 'integrations';

  const setActiveTab = (id: TabId) => {
    // Push (not replace) so each tab is a distinct, shareable, back-navigable history
    // entry — consistent with the URL being the source of truth for the active tab, and
    // it preserves normal Back/Forward behavior across tab changes.
    setSearchParams(prev => {
      const next = new URLSearchParams(prev);
      if (id === 'integrations') next.delete('tab');
      else next.set('tab', id);
      return next;
    });
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">Advanced Settings</h1>
        <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">Manage integrations, API keys, workflows, and system preferences</p>
      </div>

      <div className="border-b border-neutral-200 dark:border-neutral-700">
        <div className="flex gap-4 overflow-x-auto">
          {visibleTabs.map(tab => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 pb-3 px-1 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                  activeTab === tab.id
                    ? 'border-primary-600 dark:border-primary-500 text-primary-600 dark:text-primary-400'
                    : 'border-transparent text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100'
                }`}
              >
                <Icon className="h-4 w-4" />
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {activeTab === 'integrations' && <IntegrationsTab />}
      {activeTab === 'workflows' && <WorkflowsTab />}
      {activeTab === 'notifications' && <NotificationsTab />}
      {activeTab === 'preferences' && <PreferencesTab />}
      {activeTab === 'security' && <SecurityTab />}
      {activeTab === 'credits' && <CreditsTab isSuperAdmin={isSuperAdmin} />}
      {activeTab === 'database' && <DatabaseTab />}
      {activeTab === 'users' && isAdmin && <UsersTab />}

      <div className="flex justify-end gap-3">
        <button className="rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-4 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700">Reset to Defaults</button>
        <button className="inline-flex items-center gap-2 rounded-lg bg-primary-600 dark:bg-primary-500 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 dark:hover:bg-primary-600">
          <Save className="h-4 w-4" />Save Changes
        </button>
      </div>
    </div>
  );
}
