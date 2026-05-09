import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { settingsApi, WebSearchConfigUpdate } from '@/api/settings';
import type { ApiError } from '@/types/api-types';
import {
  Server, TrendingUp, Mail, Database, Globe, Search, Key,
  CheckCircle, AlertCircle, Eye, EyeOff, RefreshCw, Save, X,
} from 'lucide-react';

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

const mockApiKeys: ApiKey[] = [
  { id: '1', name: 'Production API Key', key: 'sk_prod_abc123***************************', created: '2024-01-15', lastUsed: '2025-12-17T14:30:00', usageCount: 1247, status: 'active' },
  { id: '2', name: 'Development API Key', key: 'sk_dev_xyz789***************************', created: '2024-06-20', lastUsed: '2025-12-16T10:15:00', usageCount: 523, status: 'active' },
];

const mockIntegrations: Integration[] = [
  { id: '1', name: 'Anthropic Claude API', type: 'anthropic', status: 'connected', configured: true, lastSync: '2025-12-17T14:30:00' },
  { id: '2', name: 'Google Trends (Pytrends)', type: 'pytrends', status: 'connected', configured: true, lastSync: new Date().toISOString() },
  { id: '3', name: 'Email Service (SendGrid)', type: 'email', status: 'disconnected', configured: false },
  { id: '4', name: 'Cloud Storage (S3)', type: 'storage', status: 'disconnected', configured: false },
  { id: '5', name: 'Analytics (Google Analytics)', type: 'analytics', status: 'error', configured: true, lastSync: '2025-12-16T08:00:00' },
  { id: '6', name: 'Brave Search', type: 'brave', status: 'disconnected', configured: false },
  { id: '7', name: 'Tavily Web Search', type: 'tavily', status: 'disconnected', configured: false },
  { id: '8', name: 'SerpAPI (Google Search)', type: 'serpapi', status: 'disconnected', configured: false },
];

function getIntegrationBadge(status: Integration['status']) {
  switch (status) {
    case 'connected': return 'bg-green-100 dark:bg-green-900/20 text-green-700 dark:text-green-400 border-green-200 dark:border-green-700';
    case 'disconnected': return 'bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 border-neutral-200 dark:border-neutral-700';
    case 'error': return 'bg-red-100 dark:bg-red-900/20 text-red-700 dark:text-red-400 border-red-200 dark:border-red-700';
  }
}

function getIntegrationIcon(type: Integration['type']) {
  switch (type) {
    case 'anthropic': return Server;
    case 'pytrends': return TrendingUp;
    case 'email': return Mail;
    case 'storage': return Database;
    case 'analytics': return Globe;
    case 'brave': case 'tavily': case 'serpapi': return Search;
  }
}

function formatTimeAgo(dateString?: string) {
  if (!dateString) return 'Never';
  const diffMs = Date.now() - new Date(dateString).getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${diffDays}d ago`;
}

function NewApiKeyModal({ onClose, onSubmit, isSubmitting }: { onClose: () => void; onSubmit: (name: string) => void; isSubmitting: boolean }) {
  const [name, setName] = useState('');
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40 dark:bg-black/60 px-4">
      <div className="w-full max-w-md rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6 shadow-xl">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">Create API Key</h3>
            <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">Generate a new API key for integrations</p>
          </div>
          <button onClick={onClose} className="rounded-lg p-2 text-neutral-400 dark:text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-800 hover:text-neutral-600 dark:hover:text-neutral-300">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">Key Name</label>
            <input type="text" value={name} onChange={e => setName(e.target.value)} placeholder="e.g., Production API Key" className="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500" />
          </div>
          <div className="rounded-lg border border-amber-200 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/20 p-3">
            <div className="flex gap-2">
              <AlertCircle className="h-4 w-4 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-amber-700 dark:text-amber-300">Make sure to copy your API key now. You won't be able to see it again!</p>
            </div>
          </div>
        </div>
        <div className="mt-6 flex justify-end gap-3">
          <button onClick={onClose} className="rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-4 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700">Cancel</button>
          <button disabled={!name || isSubmitting} onClick={() => onSubmit(name)} className="inline-flex items-center gap-2 rounded-lg bg-primary-600 dark:bg-primary-500 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 dark:hover:bg-primary-600 disabled:opacity-50">
            <Key className="h-4 w-4" />
            {isSubmitting ? 'Creating...' : 'Create Key'}
          </button>
        </div>
      </div>
    </div>
  );
}

function ConfigureIntegrationModal({ integration, onClose }: { integration: Integration; onClose: () => void }) {
  const [apiKey, setApiKey] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const queryClient = useQueryClient();

  const Icon = getIntegrationIcon(integration.type);
  const isWebSearch = ['brave', 'tavily', 'serpapi'].includes(integration.type);

  const handleTest = async () => {
    if (!apiKey.trim()) { setTestResult({ success: false, message: 'Please enter an API key first' }); return; }
    setTesting(true); setTestResult(null);
    try {
      const { settingsApi: api } = await import('@/api/settings');
      const result = await api.testConnection({ provider: integration.type as 'brave' | 'tavily' | 'serpapi', api_key: apiKey });
      setTestResult(result);
    } catch (error: unknown) {
      setTestResult({ success: false, message: (error as ApiError).response?.data?.detail || 'Connection test failed' });
    } finally { setTesting(false); }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const { settingsApi: api } = await import('@/api/settings');
      if (isWebSearch) {
        const update: WebSearchConfigUpdate = { provider: integration.type as WebSearchConfigUpdate['provider'], [`${integration.type}_api_key`]: apiKey || null };
        await api.updateWebSearchConfig(update);
        queryClient.invalidateQueries({ queryKey: ['integrations'] });
        setTestResult({ success: true, message: 'API key saved successfully!' });
        setTimeout(() => onClose(), 1500);
      }
    } catch (error: unknown) {
      setTestResult({ success: false, message: (error as ApiError).response?.data?.detail || 'Failed to save API key' });
    } finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40 dark:bg-black/60 px-4">
      <div className="w-full max-w-md rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6 shadow-xl">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-neutral-100 dark:bg-neutral-800 p-2"><Icon className="h-5 w-5 text-neutral-600 dark:text-neutral-400" /></div>
            <div>
              <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">Configure {integration.name}</h3>
              <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">Integration settings and credentials</p>
            </div>
          </div>
          <button aria-label="Close integration configuration" onClick={onClose} className="rounded-lg p-2 text-neutral-400 dark:text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-800 hover:text-neutral-600 dark:hover:text-neutral-300"><X className="h-5 w-5" /></button>
        </div>

        {isWebSearch ? (
          <div className="space-y-4 mb-6">
            <div>
              <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">API Key</label>
              <div className="relative">
                <input type={showKey ? 'text' : 'password'} value={apiKey} onChange={e => setApiKey(e.target.value)} placeholder={`Enter your ${integration.name} API key`} className="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 px-3 py-2 pr-10 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500" />
                <button aria-label={showKey ? 'Hide API key' : 'Show API key'} type="button" onClick={() => setShowKey(!showKey)} className="absolute right-2 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300">
                  {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-1">
                Get your API key from{' '}
                {integration.type === 'brave' && <a href="https://brave.com/search/api/" target="_blank" rel="noopener noreferrer" className="text-primary-600 dark:text-primary-400 hover:underline">Brave Search API</a>}
                {integration.type === 'tavily' && <a href="https://tavily.com/" target="_blank" rel="noopener noreferrer" className="text-primary-600 dark:text-primary-400 hover:underline">Tavily</a>}
                {integration.type === 'serpapi' && <a href="https://serpapi.com/" target="_blank" rel="noopener noreferrer" className="text-primary-600 dark:text-primary-400 hover:underline">SerpAPI</a>}
              </p>
            </div>
            {testResult && (
              <div className={`rounded-lg p-3 ${testResult.success ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700' : 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700'}`}>
                <div className="flex gap-2">
                  {testResult.success ? <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" /> : <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />}
                  <p className={`text-sm ${testResult.success ? 'text-green-700 dark:text-green-300' : 'text-red-700 dark:text-red-300'}`}>{testResult.message}</p>
                </div>
              </div>
            )}
          </div>
        ) : integration.type === 'pytrends' ? (
          <div className="rounded-lg border border-blue-200 dark:border-blue-700 bg-blue-50 dark:bg-blue-900/20 p-4 mb-6">
            <div className="flex gap-2">
              <AlertCircle className="h-4 w-4 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-blue-900 dark:text-blue-100">No Configuration Required</p>
                <p className="text-sm text-blue-700 dark:text-blue-300 mt-1">Google Trends (Pytrends) is a Python library that doesn't require an API key. It's ready to use.</p>
              </div>
            </div>
          </div>
        ) : (
          <div className="rounded-lg border border-amber-200 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/20 p-4 mb-6">
            <div className="flex gap-2">
              <AlertCircle className="h-4 w-4 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-amber-900 dark:text-amber-100">Coming Soon</p>
                <p className="text-sm text-amber-700 dark:text-amber-300 mt-1">Configuration for {integration.name} will be available soon.</p>
              </div>
            </div>
          </div>
        )}

        <div className="flex justify-end gap-3">
          {isWebSearch ? (
            <>
              <button onClick={onClose} disabled={testing || saving} className="rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-4 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700 disabled:opacity-50">Cancel</button>
              <button onClick={handleTest} disabled={!apiKey.trim() || testing || saving} className="inline-flex items-center gap-2 rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-4 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700 disabled:opacity-50">
                {testing ? <RefreshCw className="h-4 w-4 animate-spin" /> : <CheckCircle className="h-4 w-4" />}
                {testing ? 'Testing...' : 'Test Connection'}
              </button>
              <button onClick={handleSave} disabled={!apiKey.trim() || saving} className="inline-flex items-center gap-2 rounded-lg bg-primary-600 dark:bg-primary-500 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 dark:hover:bg-primary-600 disabled:opacity-50">
                {saving ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                {saving ? 'Saving...' : 'Save API Key'}
              </button>
            </>
          ) : (
            <button onClick={onClose} className="rounded-lg bg-primary-600 dark:bg-primary-500 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 dark:hover:bg-primary-600">Close</button>
          )}
        </div>
      </div>
    </div>
  );
}

export function IntegrationsTab() {
  const queryClient = useQueryClient();
  const [showNewApiKeyModal, setShowNewApiKeyModal] = useState(false);
  const [showKeyValue, setShowKeyValue] = useState<string | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [showConfigureModal, setShowConfigureModal] = useState<Integration | null>(null);

  const { data: apiKeys = mockApiKeys } = useQuery({
    queryKey: ['api-keys'],
    queryFn: async () => { await new Promise(r => setTimeout(r, 300)); return mockApiKeys; },
  });

  const { data: pytrendsHealth } = useQuery({
    queryKey: ['health', 'pytrends'],
    queryFn: async () => { const r = await fetch('/api/health/pytrends'); if (!r.ok) throw new Error('Failed'); return r.json(); },
    refetchInterval: 30000,
  });

  const { data: webSearchConfig } = useQuery({
    queryKey: ['settings', 'web-search'],
    queryFn: () => settingsApi.getWebSearchConfig(),
  });

  const { data: integrations = mockIntegrations } = useQuery({
    queryKey: ['integrations', pytrendsHealth, webSearchConfig],
    queryFn: async (): Promise<Integration[]> => mockIntegrations.map(integration => {
      if (integration.type === 'pytrends' && pytrendsHealth) {
        return { ...integration, status: pytrendsHealth.status === 'connected' ? 'connected' : 'error', configured: pytrendsHealth.status === 'connected', lastSync: new Date().toISOString() };
      }
      if (webSearchConfig) {
        if (integration.type === 'brave') return { ...integration, status: webSearchConfig.brave_api_key_configured ? 'connected' : 'disconnected', configured: webSearchConfig.brave_api_key_configured };
        if (integration.type === 'tavily') return { ...integration, status: webSearchConfig.tavily_api_key_configured ? 'connected' : 'disconnected', configured: webSearchConfig.tavily_api_key_configured };
        if (integration.type === 'serpapi') return { ...integration, status: webSearchConfig.serpapi_api_key_configured ? 'connected' : 'disconnected', configured: webSearchConfig.serpapi_api_key_configured };
      }
      return integration;
    }),
  });

  const createApiKeyMutation = useMutation({
    mutationFn: async (name: string) => {
      await new Promise(r => setTimeout(r, 1000));
      const randomBytes = new Uint8Array(16);
      crypto.getRandomValues(randomBytes);
      const key = Array.from(randomBytes, b => b.toString(36)).join('').substring(0, 15);
      return { name, key: `sk_${key}` };
    },
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['api-keys'] }); setShowNewApiKeyModal(false); },
  });

  const revokeApiKeyMutation = useMutation({
    mutationFn: async (id: string) => { await new Promise(r => setTimeout(r, 500)); return id; },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['api-keys'] }),
  });

  const copyToClipboard = (text: string, keyId: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(keyId);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  void revokeApiKeyMutation; // used via UI (not yet wired to a button — existing behaviour preserved)
  void showKeyValue; void setShowKeyValue; void copyToClipboard; void copiedKey; void apiKeys;

  return (
    <>
      <div className="space-y-4">
        {integrations.map(integration => {
          const Icon = getIntegrationIcon(integration.type);
          return (
            <div key={integration.id} className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-4">
                  <div className="rounded-lg bg-neutral-100 dark:bg-neutral-800 p-3"><Icon className="h-6 w-6 text-neutral-600 dark:text-neutral-400" /></div>
                  <div>
                    <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">{integration.name}</h3>
                    <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">{integration.configured ? `Last synced ${formatTimeAgo(integration.lastSync)}` : 'Not configured'}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`inline-flex items-center gap-1.5 rounded-md border px-3 py-1 text-sm font-medium ${getIntegrationBadge(integration.status)}`}>
                    {integration.status === 'connected' && <CheckCircle className="h-3 w-3" />}
                    {integration.status === 'error' && <AlertCircle className="h-3 w-3" />}
                    {integration.status.charAt(0).toUpperCase() + integration.status.slice(1)}
                  </span>
                  <button onClick={() => setShowConfigureModal(integration)} className="rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-4 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700">
                    {integration.configured ? 'Configure' : 'Connect'}
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {showConfigureModal && <ConfigureIntegrationModal integration={showConfigureModal} onClose={() => setShowConfigureModal(null)} />}
      {showNewApiKeyModal && <NewApiKeyModal onClose={() => setShowNewApiKeyModal(false)} onSubmit={name => createApiKeyMutation.mutate(name)} isSubmitting={createApiKeyMutation.isPending} />}
    </>
  );
}
