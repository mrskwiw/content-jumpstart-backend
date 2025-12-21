import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Settings as SettingsIcon,
  Server,
  Key,
  Zap,
  Bell,
  Shield,
  Save,
  Plus,
  Trash2,
  Eye,
  EyeOff,
  Copy,
  CheckCircle,
  AlertCircle,
  Mail,
  Globe,
  Clock,
  Database,
  RefreshCw,
  X,
} from 'lucide-react';

// Interfaces
interface ApiKey {
  id: string;
  name: string;
  key: string;
  created: string;
  lastUsed: string;
  usageCount: number;
  status: 'active' | 'revoked';
}

interface Integration {
  id: string;
  name: string;
  type: 'anthropic' | 'email' | 'storage' | 'analytics';
  status: 'connected' | 'disconnected' | 'error';
  configured: boolean;
  lastSync?: string;
}

interface WorkflowRule {
  id: string;
  name: string;
  trigger: string;
  action: string;
  enabled: boolean;
}

// Mock data
const mockApiKeys: ApiKey[] = [
  {
    id: '1',
    name: 'Production API Key',
    key: 'sk_prod_abc123***************************',
    created: '2024-01-15',
    lastUsed: '2025-12-17T14:30:00',
    usageCount: 1247,
    status: 'active',
  },
  {
    id: '2',
    name: 'Development API Key',
    key: 'sk_dev_xyz789***************************',
    created: '2024-06-20',
    lastUsed: '2025-12-16T10:15:00',
    usageCount: 523,
    status: 'active',
  },
];

const mockIntegrations: Integration[] = [
  {
    id: '1',
    name: 'Anthropic Claude API',
    type: 'anthropic',
    status: 'connected',
    configured: true,
    lastSync: '2025-12-17T14:30:00',
  },
  {
    id: '2',
    name: 'Email Service (SendGrid)',
    type: 'email',
    status: 'connected',
    configured: true,
    lastSync: '2025-12-17T12:00:00',
  },
  {
    id: '3',
    name: 'Cloud Storage (S3)',
    type: 'storage',
    status: 'disconnected',
    configured: false,
  },
  {
    id: '4',
    name: 'Analytics (Google Analytics)',
    type: 'analytics',
    status: 'error',
    configured: true,
    lastSync: '2025-12-16T08:00:00',
  },
];

const mockWorkflowRules: WorkflowRule[] = [
  {
    id: '1',
    name: 'Auto-approve high quality posts',
    trigger: 'Quality score > 90%',
    action: 'Mark as ready for delivery',
    enabled: true,
  },
  {
    id: '2',
    name: 'Send client satisfaction survey',
    trigger: '2 weeks after delivery',
    action: 'Email satisfaction survey',
    enabled: true,
  },
  {
    id: '3',
    name: 'Alert on low quality',
    trigger: 'Quality score < 70%',
    action: 'Notify team for review',
    enabled: false,
  },
];

export default function Settings() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'integrations' | 'api-keys' | 'workflows' | 'notifications' | 'preferences' | 'security'>('integrations');
  const [showNewApiKeyModal, setShowNewApiKeyModal] = useState(false);
  const [showKeyValue, setShowKeyValue] = useState<string | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  // Mock queries
  const { data: apiKeys = mockApiKeys } = useQuery({
    queryKey: ['api-keys'],
    queryFn: async () => {
      await new Promise(resolve => setTimeout(resolve, 300));
      return mockApiKeys;
    },
  });

  const { data: integrations = mockIntegrations } = useQuery({
    queryKey: ['integrations'],
    queryFn: async () => {
      await new Promise(resolve => setTimeout(resolve, 300));
      return mockIntegrations;
    },
  });

  const { data: workflowRules = mockWorkflowRules } = useQuery({
    queryKey: ['workflow-rules'],
    queryFn: async () => {
      await new Promise(resolve => setTimeout(resolve, 300));
      return mockWorkflowRules;
    },
  });

  // Mutations
  const createApiKeyMutation = useMutation({
    mutationFn: async (name: string) => {
      await new Promise(resolve => setTimeout(resolve, 1000));
      return { name, key: `sk_${Math.random().toString(36).substring(2, 15)}` };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] });
      setShowNewApiKeyModal(false);
    },
  });

  const revokeApiKeyMutation = useMutation({
    mutationFn: async (id: string) => {
      await new Promise(resolve => setTimeout(resolve, 500));
      return id;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] });
    },
  });

  const toggleWorkflowMutation = useMutation({
    mutationFn: async (data: { id: string; enabled: boolean }) => {
      await new Promise(resolve => setTimeout(resolve, 300));
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflow-rules'] });
    },
  });

  // Copy to clipboard
  const copyToClipboard = (text: string, keyId: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(keyId);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  // Get integration status badge
  const getIntegrationBadge = (status: Integration['status']) => {
    switch (status) {
      case 'connected':
        return 'bg-green-100 dark:bg-green-900/20 text-green-700 dark:text-green-400 border-green-200 dark:border-green-700';
      case 'disconnected':
        return 'bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 border-neutral-200 dark:border-neutral-700';
      case 'error':
        return 'bg-red-100 dark:bg-red-900/20 text-red-700 dark:text-red-400 border-red-200 dark:border-red-700';
    }
  };

  // Get integration icon
  const getIntegrationIcon = (type: Integration['type']) => {
    switch (type) {
      case 'anthropic':
        return Server;
      case 'email':
        return Mail;
      case 'storage':
        return Database;
      case 'analytics':
        return Globe;
    }
  };

  // Format time ago
  const formatTimeAgo = (dateString?: string) => {
    if (!dateString) return 'Never';
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${diffDays}d ago`;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">Advanced Settings</h1>
        <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">
          Manage integrations, API keys, workflows, and system preferences
        </p>
      </div>

      {/* Tabs */}
      <div className="border-b border-neutral-200 dark:border-neutral-700">
        <div className="flex gap-4 overflow-x-auto">
          {[
            { id: 'integrations', label: 'Integrations', icon: Server },
            { id: 'api-keys', label: 'API Keys', icon: Key },
            { id: 'workflows', label: 'Workflows', icon: Zap },
            { id: 'notifications', label: 'Notifications', icon: Bell },
            { id: 'preferences', label: 'Preferences', icon: SettingsIcon },
            { id: 'security', label: 'Security', icon: Shield },
          ].map(tab => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
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

      {/* Integrations Tab */}
      {activeTab === 'integrations' && (
        <div className="space-y-4">
          {integrations.map(integration => {
            const Icon = getIntegrationIcon(integration.type);
            return (
              <div key={integration.id} className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-4">
                    <div className="rounded-lg bg-neutral-100 dark:bg-neutral-800 p-3">
                      <Icon className="h-6 w-6 text-neutral-600 dark:text-neutral-400" />
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">{integration.name}</h3>
                      <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">
                        {integration.configured
                          ? `Last synced ${formatTimeAgo(integration.lastSync)}`
                          : 'Not configured'}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span
                      className={`inline-flex items-center gap-1.5 rounded-md border px-3 py-1 text-sm font-medium ${getIntegrationBadge(
                        integration.status
                      )}`}
                    >
                      {integration.status === 'connected' && <CheckCircle className="h-3 w-3" />}
                      {integration.status === 'error' && <AlertCircle className="h-3 w-3" />}
                      {integration.status.charAt(0).toUpperCase() + integration.status.slice(1)}
                    </span>
                    <button className="rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-4 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700">
                      {integration.configured ? 'Configure' : 'Connect'}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* API Keys Tab */}
      {activeTab === 'api-keys' && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <button
              onClick={() => setShowNewApiKeyModal(true)}
              className="inline-flex items-center gap-2 rounded-lg bg-primary-600 dark:bg-primary-500 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 dark:hover:bg-primary-600"
            >
              <Plus className="h-4 w-4" />
              Create API Key
            </button>
          </div>

          {apiKeys.map(apiKey => (
            <div key={apiKey.id} className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">{apiKey.name}</h3>
                  <div className="flex items-center gap-4 mt-2 text-sm text-neutral-600 dark:text-neutral-400">
                    <span>Created {new Date(apiKey.created).toLocaleDateString()}</span>
                    <span>•</span>
                    <span>Last used {formatTimeAgo(apiKey.lastUsed)}</span>
                    <span>•</span>
                    <span>{apiKey.usageCount.toLocaleString()} requests</span>
                  </div>
                </div>
                <span
                  className={`inline-flex items-center gap-1.5 rounded-md border px-3 py-1 text-sm font-medium ${
                    apiKey.status === 'active'
                      ? 'bg-green-100 dark:bg-green-900/20 text-green-700 dark:text-green-400 border-green-200 dark:border-green-700'
                      : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 border-neutral-200 dark:border-neutral-700'
                  }`}
                >
                  {apiKey.status === 'active' && <CheckCircle className="h-3 w-3" />}
                  {apiKey.status.charAt(0).toUpperCase() + apiKey.status.slice(1)}
                </span>
              </div>

              <div className="flex items-center gap-2">
                <div className="flex-1 rounded-lg border border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 px-4 py-2 font-mono text-sm">
                  {showKeyValue === apiKey.id ? apiKey.key : apiKey.key.replace(/\*/g, '•')}
                </div>
                <button
                  onClick={() => setShowKeyValue(showKeyValue === apiKey.id ? null : apiKey.id)}
                  className="rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 p-2 text-neutral-600 dark:text-neutral-400 hover:bg-neutral-50 dark:hover:bg-neutral-700"
                >
                  {showKeyValue === apiKey.id ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
                <button
                  onClick={() => copyToClipboard(apiKey.key, apiKey.id)}
                  className="rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 p-2 text-neutral-600 dark:text-neutral-400 hover:bg-neutral-50 dark:hover:bg-neutral-700"
                >
                  {copiedKey === apiKey.id ? <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400" /> : <Copy className="h-4 w-4" />}
                </button>
                {apiKey.status === 'active' && (
                  <button
                    onClick={() => revokeApiKeyMutation.mutate(apiKey.id)}
                    className="rounded-lg border border-red-300 dark:border-red-700 bg-white dark:bg-neutral-800 p-2 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Workflows Tab */}
      {activeTab === 'workflows' && (
        <div className="space-y-4">
          <div className="rounded-lg border border-primary-200 dark:border-primary-700 bg-primary-50 dark:bg-primary-900/20 p-4">
            <div className="flex gap-2">
              <AlertCircle className="h-4 w-4 text-primary-600 dark:text-primary-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-primary-900 dark:text-primary-100">Workflow Automation</p>
                <p className="text-sm text-primary-700 dark:text-primary-300 mt-1">
                  Automate repetitive tasks with custom workflow rules. Rules are evaluated in real-time.
                </p>
              </div>
            </div>
          </div>

          {workflowRules.map(rule => (
            <div key={rule.id} className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">{rule.name}</h3>
                    <label className="relative inline-flex cursor-pointer items-center">
                      <input
                        type="checkbox"
                        checked={rule.enabled}
                        onChange={e =>
                          toggleWorkflowMutation.mutate({ id: rule.id, enabled: e.target.checked })
                        }
                        className="peer sr-only"
                      />
                      <div className="peer h-6 w-11 rounded-full bg-neutral-200 dark:bg-neutral-700 after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-gray-300 dark:border-neutral-600 after:bg-white dark:after:bg-neutral-300 after:transition-all after:content-[''] peer-checked:bg-primary-600 dark:peer-checked:bg-primary-500 peer-checked:after:translate-x-full peer-checked:after:border-white"></div>
                    </label>
                  </div>
                  <div className="space-y-2 text-sm">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-neutral-700 dark:text-neutral-300">Trigger:</span>
                      <span className="text-neutral-600 dark:text-neutral-400">{rule.trigger}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-neutral-700 dark:text-neutral-300">Action:</span>
                      <span className="text-neutral-600 dark:text-neutral-400">{rule.action}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))}

          <button className="w-full rounded-lg border-2 border-dashed border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6 text-neutral-600 dark:text-neutral-400 hover:border-primary-400 dark:hover:border-primary-600 hover:text-primary-600 dark:hover:text-primary-400 transition-colors">
            <Plus className="h-5 w-5 mx-auto mb-2" />
            <span className="text-sm font-medium">Create New Workflow Rule</span>
          </button>
        </div>
      )}

      {/* Notifications Tab */}
      {activeTab === 'notifications' && (
        <div className="space-y-4">
          <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
            <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-4">Email Notifications</h3>
            <div className="space-y-4">
              {[
                { id: 'deliverable_ready', label: 'Deliverable ready for client', default: true },
                { id: 'quality_issues', label: 'Quality issues detected', default: true },
                { id: 'new_project', label: 'New project assigned', default: true },
                { id: 'client_feedback', label: 'Client feedback received', default: false },
                { id: 'deadline_approaching', label: 'Deadline approaching (24h)', default: true },
              ].map(notification => (
                <div key={notification.id} className="flex items-center justify-between">
                  <span className="text-sm text-neutral-700 dark:text-neutral-300">{notification.label}</span>
                  <label className="relative inline-flex cursor-pointer items-center">
                    <input
                      type="checkbox"
                      defaultChecked={notification.default}
                      className="peer sr-only"
                    />
                    <div className="peer h-6 w-11 rounded-full bg-neutral-200 dark:bg-neutral-700 after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-gray-300 dark:border-neutral-600 after:bg-white dark:after:bg-neutral-300 after:transition-all after:content-[''] peer-checked:bg-primary-600 dark:peer-checked:bg-primary-500 peer-checked:after:translate-x-full peer-checked:after:border-white"></div>
                  </label>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
            <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-4">In-App Notifications</h3>
            <div className="space-y-4">
              {[
                { id: 'desktop_notifications', label: 'Desktop notifications', default: false },
                { id: 'sound_alerts', label: 'Sound alerts', default: false },
                { id: 'daily_summary', label: 'Daily activity summary (9:00 AM)', default: true },
              ].map(notification => (
                <div key={notification.id} className="flex items-center justify-between">
                  <span className="text-sm text-neutral-700 dark:text-neutral-300">{notification.label}</span>
                  <label className="relative inline-flex cursor-pointer items-center">
                    <input
                      type="checkbox"
                      defaultChecked={notification.default}
                      className="peer sr-only"
                    />
                    <div className="peer h-6 w-11 rounded-full bg-neutral-200 dark:bg-neutral-700 after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-gray-300 dark:border-neutral-600 after:bg-white dark:after:bg-neutral-300 after:transition-all after:content-[''] peer-checked:bg-primary-600 dark:peer-checked:bg-primary-500 peer-checked:after:translate-x-full peer-checked:after:border-white"></div>
                  </label>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Preferences Tab */}
      {activeTab === 'preferences' && (
        <div className="space-y-4">
          <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
            <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-4">UI Preferences</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">Theme</label>
                <select className="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500">
                  <option value="light">Light</option>
                  <option value="dark">Dark</option>
                  <option value="system">System</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">Language</label>
                <select className="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500">
                  <option value="en">English</option>
                  <option value="es">Spanish</option>
                  <option value="fr">French</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">Timezone</label>
                <select className="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500">
                  <option value="utc">UTC</option>
                  <option value="est">Eastern Time (EST)</option>
                  <option value="pst">Pacific Time (PST)</option>
                  <option value="cet">Central European Time (CET)</option>
                </select>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-sm text-neutral-700 dark:text-neutral-300">Compact view mode</span>
                <label className="relative inline-flex cursor-pointer items-center">
                  <input type="checkbox" className="peer sr-only" />
                  <div className="peer h-6 w-11 rounded-full bg-neutral-200 dark:bg-neutral-700 after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-gray-300 dark:border-neutral-600 after:bg-white dark:after:bg-neutral-300 after:transition-all after:content-[''] peer-checked:bg-primary-600 dark:peer-checked:bg-primary-500 peer-checked:after:translate-x-full peer-checked:after:border-white"></div>
                </label>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-sm text-neutral-700 dark:text-neutral-300">Auto-refresh data</span>
                <label className="relative inline-flex cursor-pointer items-center">
                  <input type="checkbox" defaultChecked className="peer sr-only" />
                  <div className="peer h-6 w-11 rounded-full bg-neutral-200 dark:bg-neutral-700 after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-gray-300 dark:border-neutral-600 after:bg-white dark:after:bg-neutral-300 after:transition-all after:content-[''] peer-checked:bg-primary-600 dark:peer-checked:bg-primary-500 peer-checked:after:translate-x-full peer-checked:after:border-white"></div>
                </label>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Security Tab */}
      {activeTab === 'security' && (
        <div className="space-y-4">
          <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
            <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-4">Session Management</h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between text-sm">
                <span className="text-neutral-700 dark:text-neutral-300">Active Session</span>
                <span className="font-mono text-xs text-neutral-500 dark:text-neutral-400">
                  {localStorage.getItem('token') ? 'Authenticated' : 'Not authenticated'}
                </span>
              </div>
              <button
                onClick={() => {
                  localStorage.clear();
                  window.location.href = '/login';
                }}
                className="w-full rounded-lg border border-red-300 dark:border-red-700 bg-red-50 dark:bg-red-900/20 px-4 py-2 text-sm font-medium text-red-700 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/30"
              >
                Sign Out & Clear Session
              </button>
            </div>
          </div>

          <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
            <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-4">Password & Authentication</h3>
            <div className="space-y-3">
              <button className="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-4 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700">
                Change Password
              </button>
              <div className="flex items-center justify-between">
                <span className="text-sm text-neutral-700 dark:text-neutral-300">Two-factor authentication</span>
                <label className="relative inline-flex cursor-pointer items-center">
                  <input type="checkbox" className="peer sr-only" />
                  <div className="peer h-6 w-11 rounded-full bg-neutral-200 dark:bg-neutral-700 after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-gray-300 dark:border-neutral-600 after:bg-white dark:after:bg-neutral-300 after:transition-all after:content-[''] peer-checked:bg-primary-600 dark:peer-checked:bg-primary-500 peer-checked:after:translate-x-full peer-checked:after:border-white"></div>
                </label>
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
            <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-4">Data & Privacy</h3>
            <div className="space-y-3">
              <button className="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-4 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700 text-left">
                Export My Data
              </button>
              <button className="w-full rounded-lg border border-red-300 dark:border-red-700 bg-white dark:bg-neutral-800 px-4 py-2 text-sm font-medium text-red-700 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 text-left">
                Delete My Account
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Save Actions */}
      <div className="flex justify-end gap-3">
        <button className="rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-4 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700">
          Reset to Defaults
        </button>
        <button className="inline-flex items-center gap-2 rounded-lg bg-primary-600 dark:bg-primary-500 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 dark:hover:bg-primary-600">
          <Save className="h-4 w-4" />
          Save Changes
        </button>
      </div>

      {/* New API Key Modal */}
      {showNewApiKeyModal && (
        <NewApiKeyModal
          onClose={() => setShowNewApiKeyModal(false)}
          onSubmit={name => createApiKeyMutation.mutate(name)}
          isSubmitting={createApiKeyMutation.isPending}
        />
      )}
    </div>
  );
}

// New API Key Modal Component
function NewApiKeyModal({
  onClose,
  onSubmit,
  isSubmitting,
}: {
  onClose: () => void;
  onSubmit: (name: string) => void;
  isSubmitting: boolean;
}) {
  const [name, setName] = useState('');

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40 dark:bg-black/60 px-4">
      <div className="w-full max-w-md rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6 shadow-xl">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">Create API Key</h3>
            <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">Generate a new API key for integrations</p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-2 text-neutral-400 dark:text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-800 hover:text-neutral-600 dark:hover:text-neutral-300"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">Key Name</label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="e.g., Production API Key"
              className="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
          </div>

          <div className="rounded-lg border border-amber-200 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/20 p-3">
            <div className="flex gap-2">
              <AlertCircle className="h-4 w-4 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-amber-700 dark:text-amber-300">
                Make sure to copy your API key now. You won't be able to see it again!
              </p>
            </div>
          </div>
        </div>

        <div className="mt-6 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-4 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700"
          >
            Cancel
          </button>
          <button
            disabled={!name || isSubmitting}
            onClick={() => onSubmit(name)}
            className="inline-flex items-center gap-2 rounded-lg bg-primary-600 dark:bg-primary-500 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 dark:hover:bg-primary-600 disabled:opacity-50"
          >
            <Key className="h-4 w-4" />
            {isSubmitting ? 'Creating...' : 'Create Key'}
          </button>
        </div>
      </div>
    </div>
  );
}
