import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { useTheme } from '@/contexts/ThemeContext';
import { useAuth } from '@/contexts/AuthContext';
import type { ApiError } from '@/types/api-types';
import UsersTab from '@/components/settings/UsersTab';
import { creditsApi } from '@/api/credits';
import { stripeApi } from '@/api/stripe';
import { settingsApi, WebSearchConfigUpdate } from '@/api/settings';
import { adminApi } from '@/api/admin';
import type { User as AdminUser } from '@/api/admin';
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
  Download,
  Upload,
  HardDrive,
  Users,
  TrendingUp,
  Coins,
  CreditCard,
  ArrowUpRight,
  ArrowDownRight,
  Search,
  UserPlus,
  Gift,
  GitMerge,
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
  type: 'anthropic' | 'pytrends' | 'email' | 'storage' | 'analytics' | 'brave' | 'tavily' | 'serpapi';
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
  config?: {
    qualityThreshold?: number;
    daysDelay?: number;
    minScore?: number;
  };
}

interface MergePreviewResult {
  success: boolean;
  dry_run: boolean;
  message: string;
  merged: Record<string, number>;
  skipped: Record<string, number>;
  total_merged: number;
  total_skipped: number;
  user_mapping: Record<string, string>;
  warnings: string[];
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
    name: 'Google Trends (Pytrends)',
    type: 'pytrends',
    status: 'connected',
    configured: true,
    lastSync: new Date().toISOString(), // Will be updated by health check
  },
  {
    id: '3',
    name: 'Email Service (SendGrid)',
    type: 'email',
    status: 'disconnected',
    configured: false,
  },
  {
    id: '4',
    name: 'Cloud Storage (S3)',
    type: 'storage',
    status: 'disconnected',
    configured: false,
  },
  {
    id: '5',
    name: 'Analytics (Google Analytics)',
    type: 'analytics',
    status: 'error',
    configured: true,
    lastSync: '2025-12-16T08:00:00',
  },
  {
    id: '6',
    name: 'Brave Search',
    type: 'brave',
    status: 'disconnected',
    configured: false,
  },
  {
    id: '7',
    name: 'Tavily Web Search',
    type: 'tavily',
    status: 'disconnected',
    configured: false,
  },
  {
    id: '8',
    name: 'SerpAPI (Google Search)',
    type: 'serpapi',
    status: 'disconnected',
    configured: false,
  },
];

const mockWorkflowRules: WorkflowRule[] = [
  {
    id: '2',
    name: 'Send client satisfaction survey',
    trigger: 'Days after delivery',
    action: 'Email satisfaction survey',
    enabled: true,
    config: {
      daysDelay: 14,
    },
  },
];

export default function Settings() {
  const queryClient = useQueryClient();
  const { theme, setTheme } = useTheme();
  const { user } = useAuth();
  const isAdmin = user?.isSuperuser === true;
  const [searchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState<'integrations' | 'workflows' | 'notifications' | 'preferences' | 'security' | 'database' | 'credits' | 'users'>('integrations');

  // Handle tab parameter from URL
  useEffect(() => {
    const tabParam = searchParams.get('tab');
    if (tabParam === 'credits') {
      setActiveTab('credits');
    }
  }, [searchParams]);
  const [showNewApiKeyModal, setShowNewApiKeyModal] = useState(false);
  const [showKeyValue, setShowKeyValue] = useState<string | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [workflowConfigs, setWorkflowConfigs] = useState<Record<string, WorkflowRule['config']>>({});
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [showRestoreConfirm, setShowRestoreConfirm] = useState(false);
  const [mergeFile, setMergeFile] = useState<File | null>(null);
  const [showMergeConfirm, setShowMergeConfirm] = useState(false);
  const [mergePreview, setMergePreview] = useState<MergePreviewResult | null>(null);
  const [showConfigureModal, setShowConfigureModal] = useState<Integration | null>(null);
  const [restorePoints, setRestorePoints] = useState<Array<{ filename: string; path: string; size_bytes: number; created_at: number }>>([]);
  const [showRestorePointsModal, setShowRestorePointsModal] = useState(false);

  // Grant credits state (super admin only)
  const [showGrantCreditsModal, setShowGrantCreditsModal] = useState(false);
  const [grantCreditsForm, setGrantCreditsForm] = useState({
    user_id: '',
    credits: 1000,
    reason: '',
  });
  const [grantCreditsError, setGrantCreditsError] = useState<string | null>(null);

  // Check if current user is a super admin (from SUPER_ADMIN_EMAILS env var)
  // This will be validated on the backend
  const isSuperAdmin = isAdmin; // Backend will enforce SUPER_ADMIN_EMAILS check

  // Mock queries
  const { data: apiKeys = mockApiKeys } = useQuery({
    queryKey: ['api-keys'],
    queryFn: async () => {
      await new Promise(resolve => setTimeout(resolve, 300));
      return mockApiKeys;
    },
  });

  // Fetch pytrends health status
  const { data: pytrendsHealth } = useQuery({
    queryKey: ['health', 'pytrends'],
    queryFn: async () => {
      const response = await fetch('/api/health/pytrends');
      if (!response.ok) throw new Error('Failed to check pytrends health');
      return response.json();
    },
    enabled: activeTab === 'integrations', // Only check when on integrations tab
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // Fetch web search configuration status
  const { data: webSearchConfig } = useQuery({
    queryKey: ['settings', 'web-search'],
    queryFn: () => settingsApi.getWebSearchConfig(),
    enabled: activeTab === 'integrations',
  });

  const { data: integrations = mockIntegrations } = useQuery({
    queryKey: ['integrations', pytrendsHealth, webSearchConfig],
    queryFn: async (): Promise<Integration[]> => {
      return mockIntegrations.map(integration => {
        // Update Google Trends status based on health check
        if (integration.type === 'pytrends' && pytrendsHealth) {
          const status: Integration['status'] = pytrendsHealth.status === 'connected' ? 'connected' :
                    pytrendsHealth.status === 'warning' ? 'error' : 'error';
          return {
            ...integration,
            status,
            configured: pytrendsHealth.status === 'connected',
            lastSync: new Date().toISOString(),
          };
        }

        // Update web search integration statuses based on API key configuration
        if (webSearchConfig) {
          if (integration.type === 'brave') {
            return {
              ...integration,
              status: webSearchConfig.brave_api_key_configured ? 'connected' : 'disconnected',
              configured: webSearchConfig.brave_api_key_configured,
            };
          }
          if (integration.type === 'tavily') {
            return {
              ...integration,
              status: webSearchConfig.tavily_api_key_configured ? 'connected' : 'disconnected',
              configured: webSearchConfig.tavily_api_key_configured,
            };
          }
          if (integration.type === 'serpapi') {
            return {
              ...integration,
              status: webSearchConfig.serpapi_api_key_configured ? 'connected' : 'disconnected',
              configured: webSearchConfig.serpapi_api_key_configured,
            };
          }
        }

        return integration;
      });
    },
  });

  const { data: workflowRules = mockWorkflowRules } = useQuery({
    queryKey: ['workflow-rules'],
    queryFn: async () => {
      await new Promise(resolve => setTimeout(resolve, 300));
      return mockWorkflowRules;
    },
  });

  // Credit queries
  const { data: creditBalance } = useQuery({
    queryKey: ['credits', 'balance'],
    queryFn: () => creditsApi.getBalance(),
    enabled: activeTab === 'credits',
  });

  const { data: creditPackages = [] } = useQuery({
    queryKey: ['credits', 'packages'],
    queryFn: () => creditsApi.getPackages(),
    enabled: activeTab === 'credits',
  });

  const { data: creditTransactions = [] } = useQuery({
    queryKey: ['credits', 'transactions'],
    queryFn: () => creditsApi.getTransactions(50, 0),
    enabled: activeTab === 'credits',
  });

  const { data: paymentHistory = [] } = useQuery({
    queryKey: ['stripe', 'payments'],
    queryFn: () => stripeApi.getPayments(),
    enabled: activeTab === 'credits',
  });

  // Admin queries (super admin only)
  const { data: allUsers = [] } = useQuery({
    queryKey: ['admin', 'users'],
    queryFn: () => adminApi.listUsers({ limit: 100 }),
    enabled: activeTab === 'credits' && isSuperAdmin && showGrantCreditsModal,
  });

  // Mutations
  const grantCreditsMutation = useMutation({
    mutationFn: adminApi.grantCredits,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['credits', 'balance'] });
      queryClient.invalidateQueries({ queryKey: ['credits', 'transactions'] });
      setShowGrantCreditsModal(false);
      setGrantCreditsForm({ user_id: '', credits: 1000, reason: '' });
      setGrantCreditsError(null);
      alert(`Successfully granted ${data.credits_granted} credits to ${data.user_email}`);
    },
    onError: (error: unknown) => {
      const message = (error as ApiError).response?.data?.detail || (error as Error).message || 'Failed to grant credits';
      setGrantCreditsError(message);
    },
  });
  const createApiKeyMutation = useMutation({
    mutationFn: async (name: string) => {
      await new Promise(resolve => setTimeout(resolve, 1000));
      // SECURITY FIX: Use crypto.getRandomValues() instead of Math.random() for API keys (TR-016)
      const randomBytes = new Uint8Array(16);
      crypto.getRandomValues(randomBytes);
      const key = Array.from(randomBytes, byte => byte.toString(36)).join('').substring(0, 15);
      return { name, key: `sk_${key}` };
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

  // Shared helper: request a backup from the API and immediately push it to the
  // browser as a file download. Called by the manual button AND automatically
  // before every restore so the container-volatile server copy is never the
  // only copy.
  const triggerBackupDownload = async (): Promise<void> => {
    const token = localStorage.getItem('access_token');
    const response = await fetch('/api/database/backup', {
      headers: { 'Authorization': `Bearer ${token}` },
    });

    if (!response.ok) {
      let detail = `Request failed: ${response.status} ${response.statusText}`;
      try { const err = await response.json(); detail = err.detail || detail; } catch { /* not JSON */ }
      throw new Error(detail);
    }

    const blob = await response.blob();
    const contentDisposition = response.headers.get('Content-Disposition');
    const filename = contentDisposition
      ? contentDisposition.split('filename=')[1].replace(/"/g, '')
      : `jumpstart_backup_${new Date().toISOString().slice(0, 10)}.db`;

    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  };

  // Database backup mutation
  const downloadBackupMutation = useMutation({
    mutationFn: triggerBackupDownload,
    onError: (error: Error) => {
      alert(`Backup failed: ${error.message}`);
    },
  });

  // Database restore mutation
  const restoreDatabaseMutation = useMutation({
    mutationFn: async (file: File) => {
      const token = localStorage.getItem('access_token');
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('/api/database/restore', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to restore database');
      }

      return response.json();
    },
    onSuccess: async () => {
      // Fetch restore points after successful restore
      const token = localStorage.getItem('access_token');
      try {
        const response = await fetch('/api/database/restore-points', {
          headers: { 'Authorization': `Bearer ${token}` },
        });
        if (response.ok) {
          const data = await response.json();
          setRestorePoints(data.restore_points || []);
        }
      } catch (error) {
        console.error('Failed to fetch restore points:', error);
      }

      // Clear all queries after restore
      queryClient.clear();
      setShowRestoreConfirm(false);
      setUploadFile(null);
      alert('Database restored successfully. You can now undo this restore using the restore points below.');
      setShowRestorePointsModal(true);
    },
    onError: (error: Error) => {
      alert(`Restore failed: ${error.message}`);
    },
  });

  // Revert to restore point mutation
  const revertToRestorePointMutation = useMutation({
    mutationFn: async (filename: string) => {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/api/database/restore-to-point?filename=${encodeURIComponent(filename)}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to revert to restore point');
      }

      return response.json();
    },
    onSuccess: () => {
      queryClient.clear();
      setShowRestorePointsModal(false);
      alert('Database reverted to previous state successfully. Please refresh the page.');
    },
    onError: (error: Error) => {
      alert(`Revert failed: ${error.message}`);
    },
  });

  // Database merge — dry-run preview
  const previewMergeMutation = useMutation({
    mutationFn: async (file: File): Promise<MergePreviewResult> => {
      const token = localStorage.getItem('access_token');
      const formData = new FormData();
      formData.append('file', file);
      const response = await fetch('/api/database/merge?dry_run=true', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData,
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Preview failed');
      }
      return response.json();
    },
    onSuccess: (data) => {
      setMergePreview(data);
    },
    onError: (error: Error) => {
      alert(`Merge preview failed: ${error.message}`);
    },
  });

  // Database merge — execute
  const executeMergeMutation = useMutation({
    mutationFn: async (file: File): Promise<MergePreviewResult> => {
      const token = localStorage.getItem('access_token');
      const formData = new FormData();
      formData.append('file', file);
      const response = await fetch('/api/database/merge', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData,
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Merge failed');
      }
      return response.json();
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries();
      setShowMergeConfirm(false);
      setMergeFile(null);
      setMergePreview(null);
      alert(
        `Merge complete: ${data.total_merged} records imported` +
        (data.total_skipped > 0 ? `, ${data.total_skipped} duplicates skipped` : '') +
        '.'
      );
    },
    onError: (error: Error) => {
      alert(`Merge failed: ${error.message}`);
    },
  });

  // Update workflow configuration
  const updateWorkflowConfig = (ruleId: string, configKey: string, value: number) => {
    setWorkflowConfigs(prev => ({
      ...prev,
      [ruleId]: {
        ...prev[ruleId],
        [configKey]: value,
      },
    }));
  };

  // Get current config value (from local state or default)
  const getConfigValue = (rule: WorkflowRule, key: string): number => {
    const localConfig = workflowConfigs[rule.id];
    if (localConfig && key in localConfig) {
      return (localConfig as any)[key];
    }
    return rule.config?.[key as keyof typeof rule.config] ?? 0;
  };

  // Copy to clipboard
  const copyToClipboard = (text: string, keyId: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(keyId);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  // Handle integration configuration
  const handleConfigure = (integration: Integration) => {
    setShowConfigureModal(integration);
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
      case 'pytrends':
        return TrendingUp;
      case 'email':
        return Mail;
      case 'storage':
        return Database;
      case 'analytics':
        return Globe;
      case 'brave':
        return Search;
      case 'tavily':
        return Search;
      case 'serpapi':
        return Search;
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
            { id: 'workflows', label: 'Workflows', icon: Zap },
            { id: 'notifications', label: 'Notifications', icon: Bell },
            { id: 'preferences', label: 'Preferences', icon: SettingsIcon },
            { id: 'security', label: 'Security', icon: Shield },
            { id: 'credits', label: 'Credits', icon: Coins },
            { id: 'database', label: 'Database', icon: HardDrive },
            { id: 'users', label: 'Users', icon: Users, adminOnly: true },
          ].filter(tab => !('adminOnly' in tab) || (tab.adminOnly && isAdmin)).map(tab => {
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
                    <button
                      onClick={() => handleConfigure(integration)}
                      className="rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-4 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700"
                    >
                      {integration.configured ? 'Configure' : 'Connect'}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
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
              <div className="space-y-4">
                {/* Header with toggle */}
                <div className="flex items-center justify-between">
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

                {/* Trigger and Action */}
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

                {/* Configuration Sliders */}
                {rule.config && (
                  <div className="space-y-4 pt-4 border-t border-neutral-200 dark:border-neutral-700">
                    <h4 className="text-sm font-medium text-neutral-900 dark:text-neutral-100">Configuration</h4>

                    {rule.config.qualityThreshold !== undefined && (
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <label className="text-sm text-neutral-700 dark:text-neutral-300">Quality Threshold</label>
                          <span className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                            {getConfigValue(rule, 'qualityThreshold')}%
                          </span>
                        </div>
                        <input
                          type="range"
                          min="0"
                          max="100"
                          step="5"
                          value={getConfigValue(rule, 'qualityThreshold')}
                          onChange={e => updateWorkflowConfig(rule.id, 'qualityThreshold', parseInt(e.target.value))}
                          className="w-full h-2 bg-neutral-200 dark:bg-neutral-700 rounded-lg appearance-none cursor-pointer accent-primary-600 dark:accent-primary-500"
                        />
                        <div className="flex justify-between text-xs text-neutral-500 dark:text-neutral-400">
                          <span>0%</span>
                          <span>50%</span>
                          <span>100%</span>
                        </div>
                      </div>
                    )}

                    {rule.config.daysDelay !== undefined && (
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <label className="text-sm text-neutral-700 dark:text-neutral-300">Days Delay</label>
                          <span className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                            {getConfigValue(rule, 'daysDelay')} days
                          </span>
                        </div>
                        <input
                          type="range"
                          min="1"
                          max="30"
                          step="1"
                          value={getConfigValue(rule, 'daysDelay')}
                          onChange={e => updateWorkflowConfig(rule.id, 'daysDelay', parseInt(e.target.value))}
                          className="w-full h-2 bg-neutral-200 dark:bg-neutral-700 rounded-lg appearance-none cursor-pointer accent-primary-600 dark:accent-primary-500"
                        />
                        <div className="flex justify-between text-xs text-neutral-500 dark:text-neutral-400">
                          <span>1 day</span>
                          <span>15 days</span>
                          <span>30 days</span>
                        </div>
                      </div>
                    )}

                    {rule.config.minScore !== undefined && (
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <label className="text-sm text-neutral-700 dark:text-neutral-300">Minimum Score</label>
                          <span className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                            {getConfigValue(rule, 'minScore')}%
                          </span>
                        </div>
                        <input
                          type="range"
                          min="0"
                          max="100"
                          step="5"
                          value={getConfigValue(rule, 'minScore')}
                          onChange={e => updateWorkflowConfig(rule.id, 'minScore', parseInt(e.target.value))}
                          className="w-full h-2 bg-neutral-200 dark:bg-neutral-700 rounded-lg appearance-none cursor-pointer accent-primary-600 dark:accent-primary-500"
                        />
                        <div className="flex justify-between text-xs text-neutral-500 dark:text-neutral-400">
                          <span>0%</span>
                          <span>50%</span>
                          <span>100%</span>
                        </div>
                      </div>
                    )}
                  </div>
                )}
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
                <select
                  value={theme === 'system' ? 'light' : theme}
                  onChange={(e) => setTheme(e.target.value as 'light' | 'dark')}
                  className="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                >
                  <option value="light">Light</option>
                  <option value="dark">Dark</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">Timezone</label>
                <select className="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500">
                  <option value="UTC">UTC (Coordinated Universal Time)</option>
                  <optgroup label="Americas">
                    <option value="America/New_York">Eastern Time (ET)</option>
                    <option value="America/Chicago">Central Time (CT)</option>
                    <option value="America/Denver">Mountain Time (MT)</option>
                    <option value="America/Los_Angeles">Pacific Time (PT)</option>
                    <option value="America/Anchorage">Alaska Time (AKT)</option>
                    <option value="Pacific/Honolulu">Hawaii-Aleutian Time (HAT)</option>
                    <option value="America/Toronto">Toronto</option>
                    <option value="America/Vancouver">Vancouver</option>
                    <option value="America/Mexico_City">Mexico City</option>
                    <option value="America/Sao_Paulo">São Paulo</option>
                    <option value="America/Buenos_Aires">Buenos Aires</option>
                  </optgroup>
                  <optgroup label="Europe">
                    <option value="Europe/London">London (GMT/BST)</option>
                    <option value="Europe/Paris">Paris (CET/CEST)</option>
                    <option value="Europe/Berlin">Berlin (CET/CEST)</option>
                    <option value="Europe/Rome">Rome (CET/CEST)</option>
                    <option value="Europe/Madrid">Madrid (CET/CEST)</option>
                    <option value="Europe/Amsterdam">Amsterdam (CET/CEST)</option>
                    <option value="Europe/Brussels">Brussels (CET/CEST)</option>
                    <option value="Europe/Vienna">Vienna (CET/CEST)</option>
                    <option value="Europe/Stockholm">Stockholm (CET/CEST)</option>
                    <option value="Europe/Warsaw">Warsaw (CET/CEST)</option>
                    <option value="Europe/Istanbul">Istanbul (TRT)</option>
                    <option value="Europe/Moscow">Moscow (MSK)</option>
                  </optgroup>
                  <optgroup label="Asia">
                    <option value="Asia/Dubai">Dubai (GST)</option>
                    <option value="Asia/Kolkata">India (IST)</option>
                    <option value="Asia/Bangkok">Bangkok (ICT)</option>
                    <option value="Asia/Singapore">Singapore (SGT)</option>
                    <option value="Asia/Hong_Kong">Hong Kong (HKT)</option>
                    <option value="Asia/Shanghai">Shanghai (CST)</option>
                    <option value="Asia/Tokyo">Tokyo (JST)</option>
                    <option value="Asia/Seoul">Seoul (KST)</option>
                  </optgroup>
                  <optgroup label="Australia & Pacific">
                    <option value="Australia/Sydney">Sydney (AEDT/AEST)</option>
                    <option value="Australia/Melbourne">Melbourne (AEDT/AEST)</option>
                    <option value="Australia/Brisbane">Brisbane (AEST)</option>
                    <option value="Australia/Perth">Perth (AWST)</option>
                    <option value="Pacific/Auckland">Auckland (NZDT/NZST)</option>
                  </optgroup>
                  <optgroup label="Africa">
                    <option value="Africa/Cairo">Cairo (EET)</option>
                    <option value="Africa/Johannesburg">Johannesburg (SAST)</option>
                    <option value="Africa/Lagos">Lagos (WAT)</option>
                  </optgroup>
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

      {/* Credits Tab */}
      {activeTab === 'credits' && (
        <div className="space-y-4">
          {/* Current Balance */}
          <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
            <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-4">Credit Balance</h3>
            {creditBalance ? (
              <div className="space-y-4">
                <div className="flex items-center gap-4">
                  <div className="rounded-full bg-yellow-100 dark:bg-yellow-900/20 p-4">
                    <Coins className="h-8 w-8 text-yellow-600 dark:text-yellow-400" />
                  </div>
                  <div>
                    <p className="text-3xl font-bold text-neutral-900 dark:text-neutral-100">
                      {creditBalance.balance.toLocaleString()}
                    </p>
                    <p className="text-sm text-neutral-600 dark:text-neutral-400">Available Credits</p>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4 pt-4 border-t border-neutral-200 dark:border-neutral-700">
                  <div>
                    <p className="text-sm text-neutral-600 dark:text-neutral-400">Total Purchased</p>
                    <p className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
                      {creditBalance.total_purchased.toLocaleString()}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-neutral-600 dark:text-neutral-400">Total Used</p>
                    <p className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
                      {creditBalance.total_used.toLocaleString()}
                    </p>
                  </div>
                </div>
                {creditBalance.is_enterprise && (
                  <div className="rounded-lg border border-primary-200 dark:border-primary-700 bg-primary-50 dark:bg-primary-900/20 p-3">
                    <div className="flex gap-2">
                      <CheckCircle className="h-4 w-4 text-primary-600 dark:text-primary-400 flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="text-sm font-medium text-primary-900 dark:text-primary-100">
                          Enterprise Account
                        </p>
                        <p className="text-sm text-primary-700 dark:text-primary-300 mt-1">
                          You have a custom credit rate: ${(creditBalance.custom_credit_rate ?? 0.1).toFixed(3)} per credit
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-sm text-neutral-600 dark:text-neutral-400">Loading balance...</div>
            )}

            {/* Grant Credits Button (Super Admin Only) */}
            {isSuperAdmin && (
              <div className="mt-4 pt-4 border-t border-neutral-200 dark:border-neutral-700">
                <button
                  onClick={() => setShowGrantCreditsModal(true)}
                  className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-primary-600 dark:bg-primary-500 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 dark:hover:bg-primary-600 transition-colors"
                >
                  <Gift className="h-4 w-4" />
                  Grant Free Credits to User
                </button>
                <p className="text-xs text-neutral-500 dark:text-neutral-400 text-center mt-2">
                  🔒 Super Admin Only - Visible only to original system administrators
                </p>
              </div>
            )}
          </div>

          {/* Credit Packages */}
          <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
            <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-4">Purchase Credits</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {creditPackages.map(pkg => (
                <div
                  key={pkg.id}
                  className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800 p-4 hover:border-primary-400 dark:hover:border-primary-600 transition-colors"
                >
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <h4 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
                        {pkg.name}
                      </h4>
                      {pkg.description && (
                        <p className="text-xs text-neutral-600 dark:text-neutral-400 mt-1">
                          {pkg.description}
                        </p>
                      )}
                    </div>
                    {pkg.rate_per_credit < 0.1 && (
                      <span className="inline-flex items-center rounded-md bg-green-100 dark:bg-green-900/20 px-2 py-1 text-xs font-medium text-green-700 dark:text-green-400">
                        Best Value
                      </span>
                    )}
                  </div>
                  <div className="mb-4">
                    <p className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">
                      {pkg.credits.toLocaleString()} credits
                    </p>
                    <p className="text-sm text-neutral-600 dark:text-neutral-400">
                      ${pkg.price_usd.toFixed(2)} (${(pkg.rate_per_credit).toFixed(3)}/credit)
                    </p>
                  </div>
                  <button
                    onClick={async () => {
                      try {
                        const origin = window.location.origin;
                        const result = await stripeApi.createCheckoutSession({
                          package_id: pkg.id,
                          success_url: `${origin}/payment-success?session_id={CHECKOUT_SESSION_ID}`,
                          cancel_url: `${origin}/dashboard/settings?tab=credits`,
                        });
                        window.location.href = result.checkout_url;
                      } catch {
                        alert('Failed to start checkout. Please try again.');
                      }
                    }}
                    className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-primary-600 dark:bg-primary-500 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 dark:hover:bg-primary-600"
                  >
                    <CreditCard className="h-4 w-4" />
                    Purchase
                  </button>
                </div>
              ))}
            </div>
            {creditPackages.length === 0 && (
              <div className="text-sm text-neutral-600 dark:text-neutral-400 text-center py-8">
                No credit packages available. Contact support for custom pricing.
              </div>
            )}
          </div>

          {/* Payment History */}
          <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">Payment History</h3>
              <button
                onClick={async () => {
                  try {
                    const returnUrl = `${window.location.origin}/dashboard/settings?tab=credits`;
                    const url = await stripeApi.getBillingPortalUrl(returnUrl);
                    window.location.href = url;
                  } catch {
                    alert('Unable to open billing portal. Please try again.');
                  }
                }}
                className="inline-flex items-center gap-2 rounded-lg border border-neutral-300 dark:border-neutral-600 px-3 py-1.5 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800"
              >
                <CreditCard className="h-4 w-4" />
                Manage Billing
              </button>
            </div>
            {paymentHistory.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-neutral-200 dark:border-neutral-700">
                      <th className="text-left py-3 px-2 text-xs font-medium text-neutral-600 dark:text-neutral-400 uppercase tracking-wider">Date</th>
                      <th className="text-left py-3 px-2 text-xs font-medium text-neutral-600 dark:text-neutral-400 uppercase tracking-wider">Amount</th>
                      <th className="text-left py-3 px-2 text-xs font-medium text-neutral-600 dark:text-neutral-400 uppercase tracking-wider">Credits</th>
                      <th className="text-left py-3 px-2 text-xs font-medium text-neutral-600 dark:text-neutral-400 uppercase tracking-wider">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paymentHistory.map(payment => (
                      <tr key={payment.id} className="border-b border-neutral-100 dark:border-neutral-800 hover:bg-neutral-50 dark:hover:bg-neutral-800/50">
                        <td className="py-3 px-2 text-sm text-neutral-900 dark:text-neutral-100">
                          {new Date(payment.created_at).toLocaleDateString()}
                        </td>
                        <td className="py-3 px-2 text-sm text-neutral-900 dark:text-neutral-100">
                          {payment.amount_usd != null ? `$${payment.amount_usd.toFixed(2)}` : '—'}
                        </td>
                        <td className="py-3 px-2 text-sm text-neutral-900 dark:text-neutral-100">
                          {payment.credits != null ? payment.credits.toLocaleString() : '—'}
                        </td>
                        <td className="py-3 px-2">
                          <span className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ${
                            payment.status === 'completed'
                              ? 'bg-green-100 dark:bg-green-900/20 text-green-700 dark:text-green-400'
                              : payment.status === 'pending'
                              ? 'bg-yellow-100 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-400'
                              : 'bg-red-100 dark:bg-red-900/20 text-red-700 dark:text-red-400'
                          }`}>
                            {payment.status.charAt(0).toUpperCase() + payment.status.slice(1)}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-sm text-neutral-600 dark:text-neutral-400 text-center py-8">
                No payment history yet.
              </div>
            )}
          </div>

          {/* Transaction History */}
          <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
            <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-4">Transaction History</h3>
            {creditTransactions.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-neutral-200 dark:border-neutral-700">
                      <th className="text-left py-3 px-2 text-xs font-medium text-neutral-600 dark:text-neutral-400 uppercase tracking-wider">
                        Date
                      </th>
                      <th className="text-left py-3 px-2 text-xs font-medium text-neutral-600 dark:text-neutral-400 uppercase tracking-wider">
                        Type
                      </th>
                      <th className="text-left py-3 px-2 text-xs font-medium text-neutral-600 dark:text-neutral-400 uppercase tracking-wider">
                        Description
                      </th>
                      <th className="text-right py-3 px-2 text-xs font-medium text-neutral-600 dark:text-neutral-400 uppercase tracking-wider">
                        Amount
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {creditTransactions.map(transaction => (
                      <tr
                        key={transaction.id}
                        className="border-b border-neutral-100 dark:border-neutral-800 hover:bg-neutral-50 dark:hover:bg-neutral-800/50"
                      >
                        <td className="py-3 px-2 text-sm text-neutral-900 dark:text-neutral-100">
                          {new Date(transaction.created_at).toLocaleDateString()}
                        </td>
                        <td className="py-3 px-2">
                          <span
                            className={`inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium ${
                              transaction.transaction_type === 'purchase'
                                ? 'bg-green-100 dark:bg-green-900/20 text-green-700 dark:text-green-400'
                                : transaction.transaction_type === 'deduction'
                                ? 'bg-red-100 dark:bg-red-900/20 text-red-700 dark:text-red-400'
                                : transaction.transaction_type === 'refund'
                                ? 'bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400'
                                : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300'
                            }`}
                          >
                            {transaction.transaction_type === 'purchase' && <ArrowUpRight className="h-3 w-3" />}
                            {transaction.transaction_type === 'deduction' && <ArrowDownRight className="h-3 w-3" />}
                            {transaction.transaction_type === 'refund' && <ArrowUpRight className="h-3 w-3" />}
                            {transaction.transaction_type.charAt(0).toUpperCase() + transaction.transaction_type.slice(1)}
                          </span>
                        </td>
                        <td className="py-3 px-2 text-sm text-neutral-600 dark:text-neutral-400">
                          {transaction.description}
                        </td>
                        <td className="py-3 px-2 text-right">
                          <span
                            className={`text-sm font-medium ${
                              transaction.amount > 0
                                ? 'text-green-700 dark:text-green-400'
                                : 'text-red-700 dark:text-red-400'
                            }`}
                          >
                            {transaction.amount > 0 ? '+' : ''}
                            {transaction.amount.toLocaleString()}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-sm text-neutral-600 dark:text-neutral-400 text-center py-8">
                No transactions yet. Purchase credits to get started.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Database Tab */}
      {activeTab === 'database' && (
        <div className="space-y-4">
          <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
            <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-4">Database Backup</h3>
            <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-4">
              Download a complete backup of your database. This includes all clients, projects, posts, runs, and deliverables.
            </p>
            <button
              onClick={() => downloadBackupMutation.mutate()}
              disabled={downloadBackupMutation.isPending}
              className="inline-flex items-center gap-2 rounded-lg bg-primary-600 dark:bg-primary-500 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 dark:hover:bg-primary-600 disabled:opacity-50"
            >
              {downloadBackupMutation.isPending ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  Creating Backup...
                </>
              ) : (
                <>
                  <Download className="h-4 w-4" />
                  Download Database Backup
                </>
              )}
            </button>
          </div>

          <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
            <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-4">Database Restore</h3>
            <div className="rounded-lg border border-amber-200 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/20 p-3 mb-4">
              <div className="flex gap-2">
                <AlertCircle className="h-4 w-4 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
                <div className="text-xs text-amber-700 dark:text-amber-300">
                  <strong>Warning:</strong> Restoring a database backup will replace all current data.
                  You can undo the restore operation using restore points.
                </div>
              </div>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
                  Select Backup File (.db)
                </label>
                <input
                  type="file"
                  accept=".db"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) {
                      setUploadFile(file);
                    }
                  }}
                  className="block w-full text-sm text-neutral-500 dark:text-neutral-400
                    file:mr-4 file:py-2 file:px-4
                    file:rounded-lg file:border-0
                    file:text-sm file:font-medium
                    file:bg-primary-50 dark:file:bg-primary-900/20 file:text-primary-700 dark:file:text-primary-400
                    hover:file:bg-primary-100 dark:hover:file:bg-primary-900/30
                    cursor-pointer"
                />
              </div>

              {uploadFile && (
                <div className="flex items-center justify-between rounded-lg border border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800 p-3">
                  <div className="flex items-center gap-2">
                    <Database className="h-4 w-4 text-neutral-500 dark:text-neutral-400" />
                    <span className="text-sm text-neutral-700 dark:text-neutral-300">{uploadFile.name}</span>
                    <span className="text-xs text-neutral-500 dark:text-neutral-400">
                      ({(uploadFile.size / 1024).toFixed(1)} KB)
                    </span>
                  </div>
                  <button
                    onClick={() => setUploadFile(null)}
                    className="text-neutral-400 dark:text-neutral-500 hover:text-neutral-600 dark:hover:text-neutral-300"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              )}

              <button
                onClick={() => setShowRestoreConfirm(true)}
                disabled={!uploadFile || restoreDatabaseMutation.isPending}
                className="w-full rounded-lg border border-red-300 dark:border-red-700 bg-red-50 dark:bg-red-900/20 px-4 py-2 text-sm font-medium text-red-700 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/30 disabled:opacity-50"
              >
                <Upload className="inline h-4 w-4 mr-2" />
                Restore Database from Backup
              </button>
            </div>
          </div>

          {/* Merge section */}
          <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
            <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-1">Merge from Backup</h3>
            <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-4">
              Import clients, projects, posts, and related content from another database backup
              without replacing your current users, credits, or settings. Duplicate records are
              skipped automatically.
            </p>

            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
                  Select Backup File (.db)
                </label>
                <input
                  type="file"
                  accept=".db"
                  onChange={(e) => {
                    const file = e.target.files?.[0] ?? null;
                    setMergeFile(file);
                    setMergePreview(null);
                  }}
                  className="block w-full text-sm text-neutral-500 dark:text-neutral-400
                    file:mr-4 file:py-2 file:px-4
                    file:rounded-lg file:border-0
                    file:text-sm file:font-medium
                    file:bg-primary-50 dark:file:bg-primary-900/20 file:text-primary-700 dark:file:text-primary-400
                    hover:file:bg-primary-100 dark:hover:file:bg-primary-900/30
                    cursor-pointer"
                />
              </div>

              {mergeFile && (
                <div className="flex items-center justify-between rounded-lg border border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800 p-3">
                  <div className="flex items-center gap-2">
                    <Database className="h-4 w-4 text-neutral-500 dark:text-neutral-400" />
                    <span className="text-sm text-neutral-700 dark:text-neutral-300">{mergeFile.name}</span>
                    <span className="text-xs text-neutral-500 dark:text-neutral-400">
                      ({(mergeFile.size / 1024).toFixed(1)} KB)
                    </span>
                  </div>
                  <button
                    onClick={() => { setMergeFile(null); setMergePreview(null); }}
                    className="text-neutral-400 dark:text-neutral-500 hover:text-neutral-600 dark:hover:text-neutral-300"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              )}

              <button
                onClick={() => mergeFile && previewMergeMutation.mutate(mergeFile)}
                disabled={!mergeFile || previewMergeMutation.isPending || executeMergeMutation.isPending}
                className="inline-flex items-center gap-2 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 px-4 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700 disabled:opacity-50"
              >
                {previewMergeMutation.isPending ? (
                  <><RefreshCw className="h-4 w-4 animate-spin" />Analyzing...</>
                ) : (
                  <><GitMerge className="h-4 w-4" />Preview Merge</>
                )}
              </button>

              {/* Preview results */}
              {mergePreview && (
                <div className="rounded-lg border border-blue-200 dark:border-blue-700 bg-blue-50 dark:bg-blue-900/20 p-4 space-y-3">
                  <p className="text-sm font-medium text-blue-800 dark:text-blue-300">
                    Preview: {mergePreview.total_merged} records to import,{' '}
                    {mergePreview.total_skipped} duplicates to skip
                  </p>

                  {Object.keys(mergePreview.merged).length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-blue-700 dark:text-blue-400 mb-1">Will import:</p>
                      <div className="grid grid-cols-2 gap-x-4 gap-y-0.5">
                        {Object.entries(mergePreview.merged).map(([table, count]) => (
                          <div key={table} className="flex justify-between text-xs text-blue-700 dark:text-blue-400">
                            <span className="capitalize">{table.replace('_', ' ')}</span>
                            <span className="font-medium">{count}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {Object.keys(mergePreview.skipped).length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-blue-700 dark:text-blue-400 mb-1">Will skip (duplicates):</p>
                      <div className="grid grid-cols-2 gap-x-4 gap-y-0.5">
                        {Object.entries(mergePreview.skipped).map(([table, count]) => (
                          <div key={table} className="flex justify-between text-xs text-blue-600 dark:text-blue-500">
                            <span className="capitalize">{table.replace('_', ' ')}</span>
                            <span>{count}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {mergePreview.warnings.length > 0 && (
                    <div className="space-y-1">
                      {mergePreview.warnings.map((w, i) => (
                        <div key={i} className="flex gap-2 text-xs text-amber-700 dark:text-amber-400">
                          <AlertCircle className="h-3 w-3 flex-shrink-0 mt-0.5" />
                          <span>{w}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {mergePreview.total_merged > 0 && (
                    <button
                      onClick={() => setShowMergeConfirm(true)}
                      disabled={executeMergeMutation.isPending}
                      className="inline-flex items-center gap-2 rounded-lg bg-blue-600 dark:bg-blue-500 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 dark:hover:bg-blue-600 disabled:opacity-50"
                    >
                      <GitMerge className="h-4 w-4" />
                      Confirm Merge
                    </button>
                  )}

                  {mergePreview.total_merged === 0 && (
                    <p className="text-xs text-blue-600 dark:text-blue-400">
                      Nothing to import — all records already exist in the current database.
                    </p>
                  )}
                </div>
              )}
            </div>
          </div>

          <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
            <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-4">Database Information</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-neutral-600 dark:text-neutral-400">Database Type:</span>
                <span className="font-medium text-neutral-900 dark:text-neutral-100">SQLite</span>
              </div>
              <div className="flex justify-between">
                <span className="text-neutral-600 dark:text-neutral-400">Backup Location:</span>
                <span className="font-mono text-xs text-neutral-500 dark:text-neutral-400">data/backups/</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Users Tab (Admin Only) */}
      {activeTab === 'users' && isAdmin && <UsersTab />}

      {/* Restore Confirmation Modal */}
      {showRestoreConfirm && uploadFile && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40 dark:bg-black/60 px-4">
          <div className="w-full max-w-md rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6 shadow-xl">
            <div className="flex items-start gap-4 mb-6">
              <div className="rounded-full bg-red-100 dark:bg-red-900/20 p-3">
                <AlertCircle className="h-6 w-6 text-red-600 dark:text-red-400" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">Confirm Database Restore</h3>
                <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">
                  This will replace all current data with the backup file. This action cannot be undone.
                </p>
                <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100 mt-3">
                  Restoring: {uploadFile.name}
                </p>
              </div>
            </div>

            <div className="rounded-lg border border-amber-200 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/20 p-3 mb-6">
              <p className="text-xs text-amber-700 dark:text-amber-300">
                After restore, you can undo this operation using the restore points feature.
              </p>
            </div>

            <div className="flex justify-end gap-3">
              <button
                onClick={() => {
                  setShowRestoreConfirm(false);
                }}
                disabled={restoreDatabaseMutation.isPending}
                className="rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-4 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700"
              >
                Cancel
              </button>
              <button
                onClick={() => restoreDatabaseMutation.mutate(uploadFile)}
                disabled={restoreDatabaseMutation.isPending}
                className="inline-flex items-center gap-2 rounded-lg bg-red-600 dark:bg-red-500 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-red-700 dark:hover:bg-red-600 disabled:opacity-50"
              >
                {restoreDatabaseMutation.isPending ? (
                  <>
                    <RefreshCw className="h-4 w-4 animate-spin" />
                    Restoring...
                  </>
                ) : (
                  <>
                    <Upload className="h-4 w-4" />
                    Restore Database
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Merge Confirmation Modal */}
      {showMergeConfirm && mergeFile && mergePreview && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40 dark:bg-black/60 px-4">
          <div className="w-full max-w-md rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6 shadow-xl">
            <div className="flex items-start gap-4 mb-6">
              <div className="rounded-full bg-blue-100 dark:bg-blue-900/20 p-3">
                <GitMerge className="h-6 w-6 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">Confirm Database Merge</h3>
                <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">
                  This will import {mergePreview.total_merged} records from{' '}
                  <span className="font-medium">{mergeFile.name}</span>.
                  Your current users and credits will not be affected.
                </p>
              </div>
            </div>

            {mergePreview.warnings.length > 0 && (
              <div className="rounded-lg border border-amber-200 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/20 p-3 mb-6 space-y-1">
                {mergePreview.warnings.map((w, i) => (
                  <div key={i} className="flex gap-2 text-xs text-amber-700 dark:text-amber-300">
                    <AlertCircle className="h-3 w-3 flex-shrink-0 mt-0.5" />
                    <span>{w}</span>
                  </div>
                ))}
              </div>
            )}

            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowMergeConfirm(false)}
                disabled={executeMergeMutation.isPending}
                className="rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-4 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700"
              >
                Cancel
              </button>
              <button
                onClick={() => executeMergeMutation.mutate(mergeFile)}
                disabled={executeMergeMutation.isPending}
                className="inline-flex items-center gap-2 rounded-lg bg-blue-600 dark:bg-blue-500 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 dark:hover:bg-blue-600 disabled:opacity-50"
              >
                {executeMergeMutation.isPending ? (
                  <><RefreshCw className="h-4 w-4 animate-spin" />Merging...</>
                ) : (
                  <><GitMerge className="h-4 w-4" />Merge Database</>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Restore Points Modal */}
      {showRestorePointsModal && restorePoints.length > 0 && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40 dark:bg-black/60 px-4">
          <div className="w-full max-w-md rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6 shadow-xl">
            <div className="flex items-start gap-4 mb-6">
              <div className="rounded-full bg-green-100 dark:bg-green-900/20 p-3">
                <CheckCircle className="h-6 w-6 text-green-600 dark:text-green-400" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">Database Restored</h3>
                <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">
                  Your restore was successful. You can undo this operation using the restore points below.
                </p>
              </div>
            </div>

            <div className="max-h-64 overflow-y-auto mb-6 space-y-2">
              {restorePoints.map((point) => (
                <div
                  key={point.filename}
                  className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800 p-3"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <p className="text-xs font-medium text-neutral-900 dark:text-neutral-100 truncate">
                        {point.filename}
                      </p>
                      <p className="text-xs text-neutral-500 dark:text-neutral-400">
                        {(point.size_bytes / 1024 / 1024).toFixed(1)} MB • {' '}
                        {new Date(point.created_at * 1000).toLocaleString()}
                      </p>
                    </div>
                    <button
                      onClick={() => revertToRestorePointMutation.mutate(point.filename)}
                      disabled={revertToRestorePointMutation.isPending}
                      className="ml-2 px-3 py-1 text-xs font-medium rounded text-white bg-red-600 dark:bg-red-500 hover:bg-red-700 dark:hover:bg-red-600 disabled:opacity-50"
                    >
                      {revertToRestorePointMutation.isPending ? 'Reverting...' : 'Undo'}
                    </button>
                  </div>
                </div>
              ))}
            </div>

            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowRestorePointsModal(false)}
                disabled={revertToRestorePointMutation.isPending}
                className="rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-4 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700"
              >
                Keep This Restore
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

      {/* Configure Integration Modal */}
      {showConfigureModal && (
        <ConfigureIntegrationModal
          integration={showConfigureModal}
          onClose={() => setShowConfigureModal(null)}
        />
      )}

      {/* New API Key Modal */}
      {showNewApiKeyModal && (
        <NewApiKeyModal
          onClose={() => setShowNewApiKeyModal(false)}
          onSubmit={name => createApiKeyMutation.mutate(name)}
          isSubmitting={createApiKeyMutation.isPending}
        />
      )}

      {/* Grant Credits Modal (Super Admin Only) */}
      <GrantCreditsModal
        isOpen={showGrantCreditsModal}
        onClose={() => {
          setShowGrantCreditsModal(false);
          setGrantCreditsError(null);
        }}
        users={allUsers}
        form={grantCreditsForm}
        onFormChange={(field, value) =>
          setGrantCreditsForm((prev) => ({ ...prev, [field]: value }))
        }
        onSubmit={() => grantCreditsMutation.mutate(grantCreditsForm)}
        isSubmitting={grantCreditsMutation.isPending}
        error={grantCreditsError}
      />
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

// Grant Credits Modal Component (Super Admin Only)
function GrantCreditsModal({
  isOpen,
  onClose,
  users,
  form,
  onFormChange,
  onSubmit,
  isSubmitting,
  error,
}: {
  isOpen: boolean;
  onClose: () => void;
  users: AdminUser[];
  form: { user_id: string; credits: number; reason: string };
  onFormChange: (field: string, value: string | number) => void;
  onSubmit: () => void;
  isSubmitting: boolean;
  error: string | null;
}) {
  if (!isOpen) return null;

  const selectedUser = users.find((u) => u.id === form.user_id);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40 dark:bg-black/60 px-4">
      <div className="w-full max-w-md rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6 shadow-xl">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 flex items-center gap-2">
              <Gift className="h-5 w-5 text-primary-600 dark:text-primary-400" />
              Grant Free Credits
            </h3>
            <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">
              🔒 Super Admin Only - Logged for audit
            </p>
          </div>
          <button
            onClick={onClose}
            disabled={isSubmitting}
            className="rounded-lg p-2 text-neutral-400 dark:text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-800 hover:text-neutral-600 dark:hover:text-neutral-300 disabled:opacity-50"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {error && (
          <div className="mb-4 rounded-lg border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 p-3">
            <div className="flex gap-2">
              <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
            </div>
          </div>
        )}

        <div className="space-y-4">
          {/* User Selector */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
              Select User *
            </label>
            <select
              value={form.user_id}
              onChange={(e) => onFormChange('user_id', e.target.value)}
              disabled={isSubmitting}
              className="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-3 py-2 text-sm text-neutral-900 dark:text-neutral-100 focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-500/20 dark:focus:ring-primary-400/20 disabled:opacity-50"
            >
              <option value="">-- Select a user --</option>
              {users.map((user) => (
                <option key={user.id} value={user.id}>
                  {user.email} - {user.fullName}
                </option>
              ))}
            </select>
            {selectedUser && (
              <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-1">
                Active: {selectedUser.isActive ? '✅ Yes' : '❌ No'} •
                Admin: {selectedUser.isSuperuser ? '👑 Yes' : 'No'}
              </p>
            )}
          </div>

          {/* Credits Amount */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
              Credits to Grant * (1-10,000)
            </label>
            <input
              type="number"
              min="1"
              max="10000"
              value={form.credits}
              onChange={(e) => onFormChange('credits', parseInt(e.target.value) || 0)}
              disabled={isSubmitting}
              className="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-3 py-2 text-sm text-neutral-900 dark:text-neutral-100 focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-500/20 dark:focus:ring-primary-400/20 disabled:opacity-50"
              placeholder="1000"
            />
          </div>

          {/* Reason */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
              Reason * (Required for audit trail)
            </label>
            <textarea
              value={form.reason}
              onChange={(e) => onFormChange('reason', e.target.value)}
              disabled={isSubmitting}
              rows={3}
              maxLength={500}
              className="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-3 py-2 text-sm text-neutral-900 dark:text-neutral-100 focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-500/20 dark:focus:ring-primary-400/20 disabled:opacity-50 resize-none"
              placeholder="e.g., Beta tester reward, compensation for downtime, promotional campaign"
            />
            <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-1">
              {form.reason.length}/500 characters
            </p>
          </div>

          {/* Example Use Cases */}
          <div className="rounded-lg border border-primary-200 dark:border-primary-700 bg-primary-50 dark:bg-primary-900/20 p-3">
            <p className="text-xs font-medium text-primary-900 dark:text-primary-100 mb-1">
              Common Use Cases:
            </p>
            <ul className="text-xs text-primary-700 dark:text-primary-300 space-y-1">
              <li>• Beta testing participant reward</li>
              <li>• Service downtime compensation</li>
              <li>• Marketing promotion / early adopter bonus</li>
              <li>• Customer support case resolution</li>
            </ul>
          </div>
        </div>

        <div className="flex gap-3 mt-6">
          <button
            onClick={onClose}
            disabled={isSubmitting}
            className="flex-1 rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-4 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={onSubmit}
            disabled={
              !form.user_id ||
              !form.credits ||
              form.credits < 1 ||
              form.credits > 10000 ||
              !form.reason.trim() ||
              isSubmitting
            }
            className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg bg-primary-600 dark:bg-primary-500 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 dark:hover:bg-primary-600 disabled:opacity-50"
          >
            {isSubmitting ? (
              <>
                <RefreshCw className="h-4 w-4 animate-spin" />
                Granting...
              </>
            ) : (
              <>
                <Gift className="h-4 w-4" />
                Grant {form.credits} Credits
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

// Configure Integration Modal Component
function ConfigureIntegrationModal({
  integration,
  onClose,
}: {
  integration: Integration;
  onClose: () => void;
}) {
  const [apiKey, setApiKey] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const queryClient = useQueryClient();

  const Icon = (() => {
    switch (integration.type) {
      case 'anthropic': return Server;
      case 'pytrends': return TrendingUp;
      case 'email': return Mail;
      case 'storage': return Database;
      case 'analytics': return Globe;
      case 'brave': return Search;
      case 'tavily': return Search;
      case 'serpapi': return Search;
      default: return Server;
    }
  })();

  const isWebSearch = ['brave', 'tavily', 'serpapi'].includes(integration.type);

  const handleTest = async () => {
    if (!apiKey.trim()) {
      setTestResult({ success: false, message: 'Please enter an API key first' });
      return;
    }

    setTesting(true);
    setTestResult(null);

    try {
      const { settingsApi } = await import('@/api/settings');
      const result = await settingsApi.testConnection({
        provider: integration.type as 'brave' | 'tavily' | 'serpapi',
        api_key: apiKey,
      });
      setTestResult(result);
    } catch (error: unknown) {
      setTestResult({
        success: false,
        message: (error as ApiError).response?.data?.detail || 'Connection test failed',
      });
    } finally {
      setTesting(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const { settingsApi } = await import('@/api/settings');

      if (isWebSearch) {
        const update: WebSearchConfigUpdate = {
          provider: integration.type as WebSearchConfigUpdate["provider"],
          [`${integration.type}_api_key`]: apiKey || null
        };

        await settingsApi.updateWebSearchConfig(update);

        queryClient.invalidateQueries({ queryKey: ['integrations'] });
        setTestResult({ success: true, message: 'API key saved successfully!' });

        // Close modal after short delay
        setTimeout(() => {
          onClose();
        }, 1500);
      }
    } catch (error: unknown) {
      setTestResult({
        success: false,
        message: (error as ApiError).response?.data?.detail || 'Failed to save API key',
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40 dark:bg-black/60 px-4">
      <div className="w-full max-w-md rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6 shadow-xl">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-neutral-100 dark:bg-neutral-800 p-2">
              <Icon className="h-5 w-5 text-neutral-600 dark:text-neutral-400" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
                Configure {integration.name}
              </h3>
              <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">
                Integration settings and credentials
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-2 text-neutral-400 dark:text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-800 hover:text-neutral-600 dark:hover:text-neutral-300"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Configuration Form */}
        {isWebSearch ? (
          <div className="space-y-4 mb-6">
            <div>
              <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
                API Key
              </label>
              <div className="relative">
                <input
                  type={showKey ? 'text' : 'password'}
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder={`Enter your ${integration.name} API key`}
                  className="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 px-3 py-2 pr-10 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                />
                <button
                  type="button"
                  onClick={() => setShowKey(!showKey)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"
                >
                  {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-1">
                Get your API key from{' '}
                {integration.type === 'brave' && (
                  <a href="https://brave.com/search/api/" target="_blank" rel="noopener noreferrer" className="text-primary-600 dark:text-primary-400 hover:underline">
                    Brave Search API
                  </a>
                )}
                {integration.type === 'tavily' && (
                  <a href="https://tavily.com/" target="_blank" rel="noopener noreferrer" className="text-primary-600 dark:text-primary-400 hover:underline">
                    Tavily
                  </a>
                )}
                {integration.type === 'serpapi' && (
                  <a href="https://serpapi.com/" target="_blank" rel="noopener noreferrer" className="text-primary-600 dark:text-primary-400 hover:underline">
                    SerpAPI
                  </a>
                )}
              </p>
            </div>

            {testResult && (
              <div className={`rounded-lg p-3 ${testResult.success ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700' : 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700'}`}>
                <div className="flex gap-2">
                  {testResult.success ? (
                    <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" />
                  ) : (
                    <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
                  )}
                  <p className={`text-sm ${testResult.success ? 'text-green-700 dark:text-green-300' : 'text-red-700 dark:text-red-300'}`}>
                    {testResult.message}
                  </p>
                </div>
              </div>
            )}
          </div>
        ) : integration.type === 'pytrends' ? (
          <div className="rounded-lg border border-blue-200 dark:border-blue-700 bg-blue-50 dark:bg-blue-900/20 p-4 mb-6">
            <div className="flex gap-2">
              <AlertCircle className="h-4 w-4 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-blue-900 dark:text-blue-100">
                  No Configuration Required
                </p>
                <p className="text-sm text-blue-700 dark:text-blue-300 mt-1">
                  Google Trends (Pytrends) is a Python library that doesn't require an API key. It's ready to use.
                </p>
              </div>
            </div>
          </div>
        ) : (
          <div className="rounded-lg border border-amber-200 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/20 p-4 mb-6">
            <div className="flex gap-2">
              <AlertCircle className="h-4 w-4 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-amber-900 dark:text-amber-100">
                  Coming Soon
                </p>
                <p className="text-sm text-amber-700 dark:text-amber-300 mt-1">
                  Configuration for {integration.name} will be available soon.
                </p>
              </div>
            </div>
          </div>
        )}

        <div className="flex justify-end gap-3">
          {isWebSearch ? (
            <>
              <button
                onClick={onClose}
                disabled={testing || saving}
                className="rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-4 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleTest}
                disabled={!apiKey.trim() || testing || saving}
                className="inline-flex items-center gap-2 rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-4 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700 disabled:opacity-50"
              >
                {testing ? <RefreshCw className="h-4 w-4 animate-spin" /> : <CheckCircle className="h-4 w-4" />}
                {testing ? 'Testing...' : 'Test Connection'}
              </button>
              <button
                onClick={handleSave}
                disabled={!apiKey.trim() || saving}
                className="inline-flex items-center gap-2 rounded-lg bg-primary-600 dark:bg-primary-500 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 dark:hover:bg-primary-600 disabled:opacity-50"
              >
                {saving ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                {saving ? 'Saving...' : 'Save API Key'}
              </button>
            </>
          ) : (
            <button
              onClick={onClose}
              className="rounded-lg bg-primary-600 dark:bg-primary-500 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 dark:hover:bg-primary-600"
            >
              Close
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
