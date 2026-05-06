/**
 * Integrations Settings Page
 *
 * Configure third-party integrations like web search APIs.
 */

import { useState, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Search, Check, X, AlertCircle, Loader2, ExternalLink, Trash2 } from 'lucide-react';
import { settingsApi, WebSearchConfig, IntegrationStatus } from '../../api/settings';

export default function Integrations() {
  const queryClient = useQueryClient();
  const [config, setConfig] = useState<WebSearchConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{
    provider: string;
    success: boolean;
    message: string;
  } | null>(null);

  // Form state
  const [provider, setProvider] = useState<'brave' | 'tavily' | 'serpapi' | 'stub'>('stub');
  const [braveApiKey, setBraveApiKey] = useState('');
  const [tavilyApiKey, setTavilyApiKey] = useState('');
  const [serpapiApiKey, setSerpapiApiKey] = useState('');
  const [showBraveKey, setShowBraveKey] = useState(false);
  const [showTavilyKey, setShowTavilyKey] = useState(false);
  const [showSerpapiKey, setShowSerpapiKey] = useState(false);

  // Load current configuration
  const [integrationStatus, setIntegrationStatus] = useState<IntegrationStatus | null>(null);

  useEffect(() => {
    loadConfig();
    loadIntegrationStatus();
  }, []);

  const loadConfig = async () => {
    try {
      const data = await settingsApi.getWebSearchConfig();
      setConfig(data);
      setProvider(data.provider);
      setLoading(false);
    } catch (error) {
      console.error('Failed to load config:', error);
      setLoading(false);
    }
  };

  const loadIntegrationStatus = async () => {
    try {
      const status = await settingsApi.getIntegrationStatus();
      setIntegrationStatus(status);
    } catch (error) {
      console.error('Failed to load integration status:', error);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setTestResult(null);

    try {
      const update = {
        provider,
        brave_api_key: braveApiKey || null,
        tavily_api_key: tavilyApiKey || null,
        serpapi_api_key: serpapiApiKey || null,
      };

      const updated = await settingsApi.updateWebSearchConfig(update);
      setConfig(updated);

      // Test connection for newly added keys
      const keysToTest: Array<{ provider: 'brave' | 'tavily' | 'serpapi'; key: string }> = [];
      if (braveApiKey) keysToTest.push({ provider: 'brave', key: braveApiKey });
      if (tavilyApiKey) keysToTest.push({ provider: 'tavily', key: tavilyApiKey });
      if (serpapiApiKey) keysToTest.push({ provider: 'serpapi', key: serpapiApiKey });

      // Test each newly configured key
      let allTestsPassed = true;
      for (const { provider: testProvider, key } of keysToTest) {
        try {
          const result = await settingsApi.testConnection({
            provider: testProvider,
            api_key: key,
          });

          if (!result.success) {
            allTestsPassed = false;
            setTestResult({
              provider: testProvider,
              success: false,
              message: result.message,
            });
            alert(`${testProvider.charAt(0).toUpperCase() + testProvider.slice(1)} connection test failed: ${result.message}`);
            break;
          }
        } catch (error) {
          allTestsPassed = false;
          setTestResult({
            provider: testProvider,
            success: false,
            message: `Connection test failed: ${(error as Error).message}`,
          });
          alert(`${testProvider.charAt(0).toUpperCase() + testProvider.slice(1)} connection test failed: ${(error as Error).message}`);
          break;
        }
      }

      // Clear form after save
      setBraveApiKey('');
      setTavilyApiKey('');
      setSerpapiApiKey('');

      // Invalidate integrations cache to update status badges in Settings.tsx
      queryClient.invalidateQueries({ queryKey: ['settings', 'web-search'] });
      queryClient.invalidateQueries({ queryKey: ['integrations'] });

      if (allTestsPassed && keysToTest.length > 0) {
        alert('Settings saved and connection verified successfully!');
      } else if (keysToTest.length === 0) {
        alert('Settings saved successfully!');
      }
    } catch (error) {
      console.error('Failed to save:', error);
      alert('Failed to save settings. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async (testProvider: 'brave' | 'tavily' | 'serpapi') => {
    const apiKey = testProvider === 'brave' ? braveApiKey : testProvider === 'tavily' ? tavilyApiKey : serpapiApiKey;

    if (!apiKey) {
      alert('Please enter an API key to test');
      return;
    }

    setTesting(true);
    setTestResult(null);

    try {
      const result = await settingsApi.testConnection({
        provider: testProvider,
        api_key: apiKey,
      });

      setTestResult({
        provider: testProvider,
        success: result.success,
        message: result.message,
      });
    } catch (error) {
      setTestResult({
        provider: testProvider,
        success: false,
        message: 'Connection test failed: ' + (error as Error).message,
      });
    } finally {
      setTesting(false);
    }
  };

  const handleDelete = async (deleteProvider: 'brave' | 'tavily' | 'serpapi') => {
    if (!confirm(`Delete ${deleteProvider} API key?`)) {
      return;
    }

    try {
      await settingsApi.deleteApiKey(deleteProvider);
      await loadConfig();

      // Invalidate integrations cache to update status badges in Settings.tsx
      queryClient.invalidateQueries({ queryKey: ['settings', 'web-search'] });
      queryClient.invalidateQueries({ queryKey: ['integrations'] });

      alert('API key deleted successfully');
    } catch (error) {
      console.error('Failed to delete key:', error);
      alert('Failed to delete API key');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Integrations</h1>
        <p className="mt-2 text-gray-600 dark:text-gray-400">
          Configure third-party services and API keys
        </p>
      </div>

      {/* Web Search Section */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <Search className="w-6 h-6 text-indigo-600" />
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                Web Search API
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Configure real-time web search for research tools
              </p>
            </div>
          </div>
        </div>

        <div className="p-6 space-y-6">
          {/* Current Status */}
          <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4">
            <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Current Configuration
            </h3>
            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-2">
                <span className="text-gray-600 dark:text-gray-400">Provider:</span>
                <span className="font-medium text-gray-900 dark:text-gray-100">
                  {config?.provider.toUpperCase()}
                  {config?.provider === 'stub' && (
                    <span className="ml-2 text-amber-600">(Development Mode)</span>
                  )}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-gray-600 dark:text-gray-400">Brave API Key:</span>
                {config?.brave_api_key_configured ? (
                  <span className="flex items-center gap-1 text-green-600">
                    <Check className="w-4 h-4" />
                    Configured
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-gray-500">
                    <X className="w-4 h-4" />
                    Not configured
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <span className="text-gray-600 dark:text-gray-400">Tavily API Key:</span>
                {config?.tavily_api_key_configured ? (
                  <span className="flex items-center gap-1 text-green-600">
                    <Check className="w-4 h-4" />
                    Configured
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-gray-500">
                    <X className="w-4 h-4" />
                    Not configured
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Provider Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Active Provider
            </label>
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value as 'brave' | 'tavily' | 'serpapi' | 'stub')}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            >
              <option value="stub">Stub (Development - Synthetic Data)</option>
              <option value="brave">Brave Search ($5/month, 1000 free searches)</option>
              <option value="tavily">Tavily ($0.001/query, cheaper at scale)</option>
              <option value="serpapi">SerpAPI ($50/month, 5000 searches)</option>
            </select>
          </div>

          {/* Brave Search Configuration */}
          <div className="border dark:border-gray-700 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                Brave Search API
              </h3>
              {config?.brave_api_key_configured && (
                <button
                  onClick={() => handleDelete('brave')}
                  className="text-sm text-red-600 hover:text-red-700 flex items-center gap-1"
                >
                  <Trash2 className="w-4 h-4" />
                  Delete Key
                </button>
              )}
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">
                  API Key
                </label>
                <div className="flex gap-2">
                  <input
                    type={showBraveKey ? 'text' : 'password'}
                    value={braveApiKey}
                    onChange={(e) => setBraveApiKey(e.target.value)}
                    placeholder="Enter Brave API key..."
                    className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                  />
                  <button
                    onClick={() => setShowBraveKey(!showBraveKey)}
                    className="px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100"
                  >
                    {showBraveKey ? 'Hide' : 'Show'}
                  </button>
                  <button
                    onClick={() => handleTest('brave')}
                    disabled={!braveApiKey || testing}
                    className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {testing ? 'Testing...' : 'Test'}
                  </button>
                </div>
              </div>

              <a
                href="https://brave.com/search/api/"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-sm text-indigo-600 hover:text-indigo-700"
              >
                Get Brave API Key
                <ExternalLink className="w-4 h-4" />
              </a>
            </div>
          </div>

          {/* Tavily Configuration */}
          <div className="border dark:border-gray-700 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                Tavily API
              </h3>
              {config?.tavily_api_key_configured && (
                <button
                  onClick={() => handleDelete('tavily')}
                  className="text-sm text-red-600 hover:text-red-700 flex items-center gap-1"
                >
                  <Trash2 className="w-4 h-4" />
                  Delete Key
                </button>
              )}
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">
                  API Key
                </label>
                <div className="flex gap-2">
                  <input
                    type={showTavilyKey ? 'text' : 'password'}
                    value={tavilyApiKey}
                    onChange={(e) => setTavilyApiKey(e.target.value)}
                    placeholder="Enter Tavily API key..."
                    className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                  />
                  <button
                    onClick={() => setShowTavilyKey(!showTavilyKey)}
                    className="px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100"
                  >
                    {showTavilyKey ? 'Hide' : 'Show'}
                  </button>
                  <button
                    onClick={() => handleTest('tavily')}
                    disabled={!tavilyApiKey || testing}
                    className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {testing ? 'Testing...' : 'Test'}
                  </button>
                </div>
              </div>

              <a
                href="https://tavily.com/"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-sm text-indigo-600 hover:text-indigo-700"
              >
                Get Tavily API Key
                <ExternalLink className="w-4 h-4" />
              </a>
            </div>
          </div>

          {/* SerpAPI Configuration */}
          <div className="border dark:border-gray-700 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                SerpAPI (Google Maps & Search)
              </h3>
              {config?.serpapi_api_key_configured && (
                <button
                  onClick={() => handleDelete('serpapi')}
                  className="text-sm text-red-600 hover:text-red-700 flex items-center gap-1"
                >
                  <Trash2 className="w-4 h-4" />
                  Delete Key
                </button>
              )}
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">
                  API Key
                </label>
                <div className="flex gap-2">
                  <input
                    type={showSerpapiKey ? 'text' : 'password'}
                    value={serpapiApiKey}
                    onChange={(e) => setSerpapiApiKey(e.target.value)}
                    placeholder="Enter SerpAPI key..."
                    className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                  />
                  <button
                    onClick={() => setShowSerpapiKey(!showSerpapiKey)}
                    className="px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100"
                  >
                    {showSerpapiKey ? 'Hide' : 'Show'}
                  </button>
                  <button
                    onClick={() => handleTest('serpapi')}
                    disabled={!serpapiApiKey || testing}
                    className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {testing ? 'Testing...' : 'Test'}
                  </button>
                </div>
              </div>

              <a
                href="https://serpapi.com/"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-sm text-indigo-600 hover:text-indigo-700"
              >
                Get SerpAPI Key
                <ExternalLink className="w-4 h-4" />
              </a>
            </div>
          </div>

          {/* Test Result */}
          {testResult && (
            <div
              className={`p-4 rounded-lg ${
                testResult.success
                  ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800'
                  : 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800'
              }`}
            >
              <div className="flex items-start gap-2">
                {testResult.success ? (
                  <Check className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                ) : (
                  <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                )}
                <div>
                  <p
                    className={`text-sm font-medium ${
                      testResult.success ? 'text-green-900 dark:text-green-100' : 'text-red-900 dark:text-red-100'
                    }`}
                  >
                    {testResult.success ? 'Connection Successful' : 'Connection Failed'}
                  </p>
                  <p
                    className={`text-sm mt-1 ${
                      testResult.success ? 'text-green-700 dark:text-green-300' : 'text-red-700 dark:text-red-300'
                    }`}
                  >
                    {testResult.message}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Save Button */}
          <div className="flex justify-end gap-3 pt-4 border-t dark:border-gray-700">
            <button
              onClick={() => {
                setBraveApiKey('');
                setTavilyApiKey('');
                setTestResult(null);
                setProvider(config?.provider || 'stub');
              }}
              className="px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {saving && <Loader2 className="w-4 h-4 animate-spin" />}
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </div>
      </div>

      {/* DataForSEO Trends Fallback — read-only status, configured via env vars */}
      <div className="mt-6 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              DataForSEO — Trends Fallback
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Provides Google Trends data when pytrends is rate-limited (~$0.002/keyword).
              Configured via environment variables — not stored in the database.
            </p>
          </div>
          {integrationStatus?.dataforseo ? (
            <span className="flex items-center gap-1.5 text-sm font-medium text-green-700 dark:text-green-400">
              <Check className="w-4 h-4" />
              Active
            </span>
          ) : (
            <span className="flex items-center gap-1.5 text-sm font-medium text-gray-400 dark:text-gray-500">
              <X className="w-4 h-4" />
              Not configured
            </span>
          )}
        </div>
        {!integrationStatus?.dataforseo && (
          <div className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
            <p>To enable, set the following in your Render environment (or <code className="bg-gray-100 dark:bg-gray-800 px-1 rounded">.env</code>):</p>
            <pre className="mt-2 bg-gray-50 dark:bg-gray-800 rounded p-3 text-xs font-mono">
{`DATAFORSEO_LOGIN=your@email.com
DATAFORSEO_PASSWORD=your_password`}
            </pre>
            <a
              href="https://dataforseo.com"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 mt-2"
            >
              Sign up at dataforseo.com
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        )}
      </div>

      {/* Info Section */}
      <div className="mt-6 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <div className="flex gap-2">
          <AlertCircle className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-blue-900 dark:text-blue-100">
            <p className="font-medium mb-1">About Web Search Integration</p>
            <ul className="list-disc list-inside space-y-1 text-blue-700 dark:text-blue-300">
              <li>Enables research tools to retrieve real-time, factual data</li>
              <li>Prevents AI hallucinations by using actual search results</li>
              <li>Stub mode works without API keys (synthetic data for development)</li>
              <li>API keys are encrypted and stored securely</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
