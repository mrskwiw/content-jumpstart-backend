import React, { useState, useMemo } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { researchApi, costsApi, ResearchTool, clientsApi } from "@/api";
import type { Client } from '@/types/domain';
import { deliverablesApi } from '@/api/deliverables';
import { getDisabledToolIds } from '@/config/featureRegistry';
import { ToolCard } from '../../components/research/ToolCard';
import { PricingSummaryCard } from '../../components/research/PricingSummaryCard';
import { Search, Filter, AlertCircle, Link2, Info, Loader2, FileOutput } from 'lucide-react';
import { ToolRunStatusList, type ToolStatusItem } from '@/components/wizard/ToolRunStatusList';

// Tool prerequisites mapping (from backend research_prerequisites.py)
const TOOL_PREREQUISITES: Record<string, { required: string[]; recommended: string[] }> = {
  // Tier 1 - Foundation (no prerequisites)
  voice_analysis: { required: [], recommended: [] },
  brand_archetype: { required: [], recommended: [] },
  seo_keyword_research: { required: [], recommended: [] },
  audience_research: { required: [], recommended: [] },
  determine_competitors: { required: [], recommended: [] },
  competitive_analysis: { required: ['determine_competitors'], recommended: [] },

  // Tier 2 - Analysis
  business_report: { required: [], recommended: ['determine_competitors'] },
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
  business_report: 'Business Report',
  icp_workshop: 'ICP Workshop',
  content_audit: 'Content Audit',
  platform_strategy: 'Platform Strategy',
  story_mining: 'Story Mining',
  content_calendar: 'Content Calendar',
};

export default function ResearchToolsLibrary() {
  const [selectedTools, setSelectedTools] = useState<string[]>([]);
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [selectedClientId, setSelectedClientId] = useState<string | null>(null);
  const [exportFormat, setExportFormat] = useState<'md' | 'docx' | 'pdf'>('docx');
  const [executionStatus, setExecutionStatus] = useState<Record<string, string>>({});
  const navigate = useNavigate();

  // Fetch available tools
  const { data: tools = [], isLoading: toolsLoading, isError: toolsError } = useQuery({
    queryKey: ['research-tools'],
    queryFn: () => researchApi.listTools()
  });

  // Fetch clients for client selector
  const { data: clients = [], isError: clientsError } = useQuery<Client[]>({
    queryKey: ['clients'],
    queryFn: () => clientsApi.list(),
  });

  // Fetch client prerequisite status when client is selected
  const { data: clientPrerequisites, isError: prerequisitesError } = useQuery({
    queryKey: ['client-prerequisites', selectedClientId],
    queryFn: () => selectedClientId ? researchApi.getClientPrerequisites(selectedClientId) : null,
    enabled: selectedClientId !== null,
  });

  // Fetch run history for the selected client to show completion indicators on cards
  const { data: clientHistory, isError: historyError } = useQuery({
    queryKey: ['research-history', selectedClientId],
    queryFn: () => selectedClientId ? researchApi.getClientHistory(selectedClientId) : null,
    enabled: selectedClientId !== null,
    staleTime: 60 * 1000,
  });

  // Fetch deliverable count filtered by selected client to enable/disable the CTA.
  // Re-runs when selectedClientId changes so the button reflects the current client.
  const { data: deliverablesList = [] } = useQuery({
    queryKey: ['deliverables', 'list', selectedClientId],
    queryFn: () => deliverablesApi.list(selectedClientId ? { clientId: selectedClientId } : {}),
    staleTime: 30 * 1000,
  });
  const hasDeliverables = deliverablesList.length > 0;

  // Build per-tool execution status map: tool_name → { executed, executionCount, lastRun }
  const toolExecutionStatus = useMemo(() => {
    if (!clientHistory?.results) return {} as Record<string, { executed: boolean; executionCount: number; lastRun?: string }>;
    const map: Record<string, { executed: boolean; executionCount: number; lastRun?: string }> = {};
    clientHistory.results.forEach((result) => {
      const entry = map[result.toolName];
      if (!entry) {
        map[result.toolName] = { executed: true, executionCount: 1, lastRun: result.createdAt };
      } else {
        entry.executionCount += 1;
        // Keep the most recent run date
        if (!entry.lastRun || result.createdAt > entry.lastRun) {
          entry.lastRun = result.createdAt;
        }
      }
    });
    return map;
  }, [clientHistory]);

  // Real-time pricing preview with bundle detection
  const { data: pricing } = useQuery({
    queryKey: ['pricing-preview', selectedTools],
    queryFn: () => researchApi.getPricingPreview(selectedTools),
    enabled: selectedTools.length > 0
  });

  // Build completed tools set from client prerequisites
  const completedToolsForClient = clientPrerequisites?.completedTools || [];

  // Mutation: Generate research report
  const generateReportMutation = useMutation({
    mutationFn: async () => {
      if (!selectedClientId) throw new Error('No client selected');
      if (selectedTools.length === 0) throw new Error('No tools selected');

      // Step 1: Get research project ID
      const { projectId } = await researchApi.getResearchProject(selectedClientId);

      // Step 2: Execute each tool sequentially
      setExecutionStatus({});
      for (const tool of selectedTools) {
        setExecutionStatus(prev => ({ ...prev, [tool]: 'running' }));
        try {
          await researchApi.run({
            projectId,
            clientId: selectedClientId,
            tool,
            params: {},
          });
          setExecutionStatus(prev => ({ ...prev, [tool]: 'complete' }));
        } catch (err) {
          setExecutionStatus(prev => ({ ...prev, [tool]: 'failed' }));
          throw new Error(`Failed to execute ${tool}: ${err}`);
        }
      }

      // Step 3: Create deliverable record in DB (matches wizard flow)
      const { deliverableId, fileName } = await researchApi.generateResearchReport({
        clientId: selectedClientId,
        tools: selectedTools,
        format: exportFormat,
      });

      // Step 4: Download via blob fetch (matches wizard flow — surfaces errors as
      // JS exceptions rather than silently saving a JSON error file)
      const { blob, filename: resolvedFilename } = await deliverablesApi.download(
        deliverableId,
        exportFormat
      );
      const blobUrl = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = resolvedFilename || fileName;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(blobUrl);

      return { deliverableId, fileName: resolvedFilename || fileName };
    },
    onSuccess: () => {
      setSelectedTools([]);
      setExecutionStatus({});
      setError(null);
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : 'Failed to generate report');
    },
  });

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

  const handleToggleTool = (toolId: string) => {
    if (disabledToolIds.has(toolId)) return;
    setSelectedTools(prev =>
      prev.includes(toolId)
        ? prev.filter(id => id !== toolId)
        : [...prev, toolId]
    );
  };

  const handleClearSelection = () => {
    setSelectedTools([]);
  };

  const handleGenerateReport = () => {
    if (!selectedClientId) {
      setError('Please select a client');
      return;
    }
    if (selectedTools.length === 0) {
      setError('Please select at least one research tool');
      return;
    }
    setError(null);
    generateReportMutation.mutate();
  };

  if (toolsError) {
    return (
      <div className="flex items-center justify-center h-96 text-red-500">
        <AlertCircle className="h-5 w-5 mr-2" />
        <span>Failed to load research tools. Please refresh the page.</span>
      </div>
    );
  }

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
            Generate comprehensive research reports tailored to your client
          </p>
        </div>
        <button
          onClick={() => navigate('/dashboard/deliverables')}
          disabled={!hasDeliverables}
          title={!hasDeliverables ? 'Generate a deliverable first' : 'View your deliverables'}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed border border-gray-300 dark:border-neutral-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-neutral-800 enabled:border-blue-600 enabled:text-blue-600 enabled:dark:text-blue-400 enabled:hover:bg-blue-50 enabled:dark:hover:bg-blue-950"
        >
          <FileOutput className="h-4 w-4" />
          View Deliverables
        </button>
      </div>

      {/* Client & Format Selector */}
      <div className="bg-white dark:bg-neutral-900 rounded-lg border border-gray-200 dark:border-neutral-700 p-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Client Selector */}
          <div>
            <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
              Select Client for Research Report
            </label>
            <select
              value={selectedClientId || ''}
              onChange={(e) => setSelectedClientId(e.target.value || null)}
              className="w-full px-4 py-2 border border-gray-300 dark:border-neutral-600 rounded-lg bg-white dark:bg-neutral-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">Choose a client...</option>
              {clients.map((client: Client) => (
                <option key={client.id} value={client.id}>
                  {client.name}
                </option>
              ))}
            </select>
            {selectedClientId && completedToolsForClient.length > 0 && (
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
                {completedToolsForClient.length} research tool{completedToolsForClient.length !== 1 ? 's' : ''} previously completed for this client
              </p>
            )}
          </div>

          {/* Format Selector */}
          <div>
            <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
              Export Format
            </label>
            <select
              value={exportFormat}
              onChange={(e) => setExportFormat(e.target.value as 'md' | 'docx' | 'pdf')}
              className="w-full px-4 py-2 border border-gray-300 dark:border-neutral-600 rounded-lg bg-white dark:bg-neutral-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="md">Markdown (.md)</option>
              <option value="docx">Word Document (.docx)</option>
              <option value="pdf">PDF Document (.pdf)</option>
            </select>
          </div>
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
              aria-label="Search research tools"
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
                  <span className="text-blue-900 dark:text-blue-100">Tools that must be completed first</span>
                </div>
              </div>
              <div className="flex items-start gap-2">
                <Link2 className="h-4 w-4 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
                <div>
                  <span className="inline-flex items-center rounded-full bg-amber-100 dark:bg-amber-900/30 px-2 py-0.5 text-xs font-medium text-amber-700 dark:text-amber-400 mr-2">
                    Recommended
                  </span>
                  <span className="text-blue-900 dark:text-blue-100">Enhances results of this tool</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Error Alert */}
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

      {/* Execution Status */}
      {Object.keys(executionStatus).length > 0 && (
        <div className="rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 p-4">
          <h3 className="text-sm font-semibold text-blue-900 dark:text-blue-100 mb-3">
            Tool Execution Status
          </h3>
          <ToolRunStatusList
            items={selectedTools.map((tool): ToolStatusItem => ({
              name: tool,
              label: TOOL_LABELS[tool] || tool,
              status: (executionStatus[tool] ?? 'pending') as ToolStatusItem['status'],
            }))}
          />
        </div>
      )}

      {/* Tools Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredTools.map((tool: ResearchTool) => (
          <ToolCard
            key={tool.name}
            tool={tool}
            isSelected={selectedTools.includes(tool.name)}
            onToggle={() => handleToggleTool(tool.name)}
            prerequisites={TOOL_PREREQUISITES[tool.name] || { required: [], recommended: [] }}
            completedTools={completedToolsForClient}
            executionStatus={toolExecutionStatus[tool.name]}
            toolLabels={TOOL_LABELS}
          />
        ))}
      </div>

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
            <div className="flex gap-3">
              <button
                onClick={handleClearSelection}
                disabled={generateReportMutation.isPending}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-neutral-800 rounded-lg transition-colors disabled:opacity-50"
              >
                Clear Selection
              </button>
              <button
                onClick={handleGenerateReport}
                disabled={!selectedClientId || generateReportMutation.isPending}
                className="px-6 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {generateReportMutation.isPending && (
                  <Loader2 className="h-4 w-4 animate-spin" />
                )}
                Generate Report
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
