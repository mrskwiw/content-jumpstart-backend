import React, { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { researchApi, costsApi, ResearchTool, projectsApi, settingsApi, clientsApi } from "@/api";
import { getDisabledToolIds } from '@/config/featureRegistry';
import type { Project } from '@/types/api-types';
import { ToolCard } from '../../components/research/ToolCard';
import { PricingSummaryCard } from '../../components/research/PricingSummaryCard';
import { Search, Filter, AlertCircle, Link2, Info } from 'lucide-react';

// Tool prerequisites mapping (from backend research_prerequisites.py)
const TOOL_PREREQUISITES: Record<string, { required: string[]; recommended: string[] }> = {
  // Tier 1 - Foundation (no prerequisites)
  voice_analysis: { required: [], recommended: [] },
  brand_archetype: { required: [], recommended: [] },
  seo_keyword_research: { required: [], recommended: [] },
  audience_research: { required: [], recommended: [] },
  determine_competitors: { required: [], recommended: [] },
  competitive_analysis: { required: [], recommended: ['determine_competitors'] },

  // Tier 2 - Analysis
  content_gap_analysis: { required: ['competitive_analysis'], recommended: ['seo_keyword_research'] },
  market_trends_research: { required: [], recommended: ['seo_keyword_research'] },
  icp_workshop: { required: [], recommended: ['audience_research'] },
  content_audit: { required: [], recommended: [] },

  // Tier 3 - Strategy
  platform_strategy: { required: ['audience_research'], recommended: ['content_gap_analysis', 'market_trends_research'] },
  story_mining: { required: [], recommended: ['voice_analysis', 'brand_archetype'] },

  // Tier 4 - Execution
  content_calendar: { required: ['seo_keyword_research', 'platform_strategy'], recommended: ['content_gap_analysis', 'market_trends_research'] },
};

// Tool name label mapping
const TOOL_LABELS: Record<string, string> = {
  voice_analysis: 'Voice Analysis',
  brand_archetype: 'Brand Archetype',
  seo_keyword_research: 'SEO Keywords',
  audience_research: 'Audience Research',
  determine_competitors: 'Determine Competitors',
  competitive_analysis: 'Competitive Analysis',
  content_gap_analysis: 'Content Gap',
  market_trends_research: 'Market Trends',
  icp_workshop: 'ICP Workshop',
  content_audit: 'Content Audit',
  platform_strategy: 'Platform Strategy',
  story_mining: 'Story Mining',
  content_calendar: 'Content Calendar',
};

export default function ResearchToolsLibrary() {
  const navigate = useNavigate();
  const [selectedTools, setSelectedTools] = useState<string[]>([]);
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [selectedClientId, setSelectedClientId] = useState<string | null>(null);
  const [isExecuting, setIsExecuting] = useState(false);
  const [exportFormat, setExportFormat] = useState<'md' | 'docx' | 'pdf'>('md');

  // Fetch available tools
  const { data: tools = [], isLoading: toolsLoading } = useQuery({
    queryKey: ['research-tools'],
    queryFn: () => researchApi.listTools()
  });

  // Fetch integration status to check which tools can be enabled
  const { data: integrationStatus } = useQuery({
    queryKey: ['integrations', 'status'],
    queryFn: () => settingsApi.getIntegrationStatus(),
    staleTime: 30 * 1000, // 30 seconds
  });

  // Real-time pricing preview with bundle detection
  const { data: pricing } = useQuery({
    queryKey: ['pricing-preview', selectedTools],
    queryFn: () => researchApi.getPricingPreview(selectedTools),
    enabled: selectedTools.length > 0
  });

  // Fetch clients for client selector
  const { data: clients = [] } = useQuery({
    queryKey: ['clients'],
    queryFn: () => clientsApi.list(),
  });

  // Fetch client prerequisite status when client is selected
  const { data: clientPrerequisites } = useQuery({
    queryKey: ['client-prerequisites', selectedClientId],
    queryFn: () => researchApi.getClientPrerequisites(selectedClientId as string),
    enabled: selectedClientId !== null,
  });

  // Build completed tools set from client prerequisites
  const completedToolsForClient = clientPrerequisites?.completedTools || [];

  // Apply registry disabled status — overrides backend status so UI stays in sync with registry
  const disabledToolIds = useMemo(() => getDisabledToolIds(), []);
  const effectiveTools = useMemo<ResearchTool[]>(
    () => tools.map((t: ResearchTool) =>
      disabledToolIds.has(t.name) ? { ...t, status: 'coming_soon' as const } : t
    ),
    [tools, disabledToolIds]
  );

  // Filter tools by category and search
  const filteredTools = effectiveTools.filter((tool: ResearchTool) => {
    const matchesCategory = categoryFilter === 'all' || tool.category === categoryFilter;
    const matchesSearch = !searchQuery ||
      tool.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (tool.description || '').toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  // Get unique categories
  const categories: string[] = ['all', ...new Set(effectiveTools.map((t: ResearchTool) => t.category).filter((c): c is string => Boolean(c)))];

  // Check if a tool is enabled based on integration requirements
  const isToolEnabled = (tool: ResearchTool): { enabled: boolean; missingIntegrations: string[] } => {
    if (!tool.required_integrations || tool.required_integrations.length === 0) {
      return { enabled: true, missingIntegrations: [] };
    }

    if (!integrationStatus) {
      // If we haven't loaded integration status yet, assume enabled to avoid flashing
      return { enabled: true, missingIntegrations: [] };
    }

    const missing: string[] = [];

    for (const requirement of tool.required_integrations) {
      if (requirement === 'web_search') {
        // web_search requires ANY web search provider (Brave, Tavily, or SerpAPI)
        if (!integrationStatus.web_search) {
          missing.push('Web Search (Brave, Tavily, or SerpAPI)');
        }
      } else if (requirement === 'serpapi') {
        // serpapi specifically requires SerpAPI
        if (!integrationStatus.serpapi) {
          missing.push('SerpAPI');
        }
      }
      // Add more integration checks here as needed
    }

    return {
      enabled: missing.length === 0,
      missingIntegrations: missing,
    };
  };

  const handleToggleTool = (toolId: string) => {
    // Registry-disabled tools cannot be selected
    if (disabledToolIds.has(toolId)) return;

    // Check if tool is enabled based on integration requirements
    const tool = effectiveTools.find(t => t.name === toolId);
    if (tool) {
      const { enabled } = isToolEnabled(tool);
      if (!enabled) {
        return; // Don't allow selecting disabled tools
      }
    }

    setSelectedTools(prev =>
      prev.includes(toolId)
        ? prev.filter(id => id !== toolId)
        : [...prev, toolId]
    );
  };

  const handleClearSelection = () => {
    setSelectedTools([]);
  };

  const handleGenerateReport = async () => {
    if (!selectedClientId) {
      setError('Please select a client');
      return;
    }
    if (selectedTools.length === 0) {
      setError('Please select at least one research tool');
      return;
    }

    setError(null);
    setIsExecuting(true);

    try {
      // Execute research tools sequentially
      for (const tool of selectedTools) {
        await researchApi.run({
          projectId: selectedClientId, // Use clientId as project for research-only
          clientId: selectedClientId,
          tool,
          params: {},
        });
      }

      // After all tools complete, generate report
      const response = await researchApi.generateResearchReport({
        clientId: selectedClientId,
        tools: selectedTools,
        format: exportFormat,
      });

      // Download the report
      if (response && response.url) {
        window.location.href = response.url;
      }

      setSelectedTools([]);
    } catch (err: any) {
      setError(err?.message || 'Failed to generate research report');
      console.error('Generation error:', err);
    } finally {
      setIsExecuting(false);
    }
  };

  if (toolsLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            Research Tools Library
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Select tools to enhance your content strategy with AI-powered research
          </p>
        </div>
      </div>


      {/* Client Selection */}
      <div className="bg-white dark:bg-neutral-900 rounded-lg border border-gray-200 dark:border-neutral-700 p-4">
        <div className="space-y-3">
          <label className="block text-sm font-medium text-gray-900 dark:text-gray-100">
            Select Client for Research Report
          </label>
          <select
            value={selectedClientId || ''}
            onChange={(e) => setSelectedClientId(e.target.value || null)}
            className="w-full px-4 py-2 border border-gray-300 dark:border-neutral-600 rounded-lg bg-white dark:bg-neutral-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">-- Select a client --</option>
            {clients.map((client: any) => (
              <option key={client.id} value={client.id}>
                {client.companyName || client.name}
              </option>
            ))}
          </select>

          {selectedClientId && (
            <div className="mt-2 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
              <p className="text-sm text-blue-900 dark:text-blue-100">
                <span className="font-medium">{completedToolsForClient.length}</span> research tool{completedToolsForClient.length !== 1 ? 's' : ''} previously completed for this client
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Search and Filters */}
      <div className="bg-white dark:bg-neutral-900 rounded-lg border border-gray-200 dark:border-neutral-700 p-4">
        <div className="flex gap-4">
          {/* Search */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search tools..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-neutral-600 rounded-lg bg-white dark:bg-neutral-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Category Filter */}
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-gray-400" />
            <div className="flex gap-2">
              {categories.map((category: string) => (
                <button
                  key={category}
                  onClick={() => setCategoryFilter(category)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    categoryFilter === category
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 dark:bg-neutral-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-neutral-700'
                  }`}
                >
                  {category.charAt(0).toUpperCase() + category.slice(1)}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Prerequisite Legend */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <Info className="h-5 w-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-blue-900 dark:text-blue-100 mb-2">
              Tool Prerequisites Guide
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
              <div className="flex items-start gap-2">
                <Link2 className="h-4 w-4 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
                <div>
                  <span className="inline-flex items-center rounded-full bg-red-100 dark:bg-red-900/30 px-2 py-0.5 text-xs font-medium text-red-700 dark:text-red-400 mr-2">
                    Required
                  </span>
                  <span className="text-blue-900 dark:text-blue-100">
                    Must complete these tools first. Tool cannot execute without them.
                  </span>
                </div>
              </div>
              <div className="flex items-start gap-2">
                <Link2 className="h-4 w-4 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
                <div>
                  <span className="inline-flex items-center rounded-full bg-blue-100 dark:bg-blue-900/30 px-2 py-0.5 text-xs font-medium text-blue-700 dark:text-blue-400 mr-2">
                    Recommended
                  </span>
                  <span className="text-blue-900 dark:text-blue-100">
                    Suggested for better results. Provides additional context and insights.
                  </span>
                </div>
              </div>
            </div>
            <p className="text-xs text-blue-700 dark:text-blue-300 mt-3">
              💡 Tools without prerequisites can be run independently at any time.
            </p>
          </div>
        </div>
      </div>

      {/* Pricing Summary */}
      {selectedTools.length > 0 && pricing && (
        <PricingSummaryCard
          pricing={pricing}
          selectedCount={selectedTools.length}
        />
      )}

      {/* Tool Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredTools.map((tool: ResearchTool) => {
          const { enabled, missingIntegrations } = isToolEnabled(tool);
          // Get execution status for this tool from client history
          const toolStatus = selectedClientId && clientPrerequisites?.tools?.find(t => t.toolName === tool.name);
          const executionStatus = toolStatus ? {
            executed: toolStatus.completed,
            executionCount: toolStatus.completed ? 1 : 0,
            lastRun: toolStatus.lastRunAt,
          } : undefined;

          return (
            <ToolCard
              key={tool.name}
              tool={tool}
              isSelected={selectedTools.includes(tool.name)}
              onToggle={() => handleToggleTool(tool.name)}
              prerequisites={TOOL_PREREQUISITES[tool.name]}
              toolLabels={TOOL_LABELS}
              disabled={!enabled || disabledToolIds.has(tool.name)}
              missingIntegrations={missingIntegrations}
              completedTools={completedToolsForClient}
              executionStatus={executionStatus}
            />
          );
        })}
      </div>

      {/* Empty State */}
      {filteredTools.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-500 dark:text-gray-400">
            No tools found matching your filters.
          </p>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="text-sm font-medium text-red-900 dark:text-red-100">Error</h3>
              <p className="text-sm text-red-700 dark:text-red-300 mt-1">{error}</p>
            </div>
            <button
              onClick={() => setError(null)}
              className="ml-auto text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-200"
            >
              ×
            </button>
          </div>
        </div>
      )}

      {/* Action Bar */}
      {selectedTools.length > 0 && (
        <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-neutral-900 border-t border-gray-200 dark:border-neutral-700 p-4 shadow-lg">
          <div className="max-w-7xl mx-auto flex items-center justify-between">
            <div className="text-sm text-gray-600 dark:text-gray-400">
              {selectedTools.length} tool{selectedTools.length !== 1 ? 's' : ''} selected
              {pricing && (
                <span className="ml-2 font-medium text-gray-900 dark:text-gray-100">
                  • {pricing.finalCost} credits
                </span>
              )}
            </div>
            <div className="flex gap-3 items-center">
              <div className="flex items-center gap-2">
                <label className="text-xs font-medium text-gray-600 dark:text-gray-400">Format:</label>
                <select
                  value={exportFormat}
                  onChange={(e) => setExportFormat(e.target.value as 'md' | 'docx' | 'pdf')}
                  className="px-3 py-1 text-sm border border-gray-300 dark:border-neutral-600 rounded bg-white dark:bg-neutral-800 text-gray-900 dark:text-gray-100"
                >
                  <option value="md">Markdown</option>
                  <option value="docx">Word (DOCX)</option>
                  <option value="pdf">PDF</option>
                </select>
              </div>
              <button
                onClick={handleClearSelection}
                disabled={isExecuting}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-neutral-800 rounded-lg transition-colors disabled:opacity-50"
              >
                Clear
              </button>
              <button
                onClick={handleGenerateReport}
                disabled={!selectedClientId || isExecuting}
                className="px-6 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isExecuting ? 'Generating...' : 'Generate Report'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
