import { useState, useEffect, memo, useMemo } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { CheckCircle2, Circle, FlaskConical, ArrowRight, Loader2, Coins, Clock, Link2, AlertCircle, Settings } from 'lucide-react';
import { researchApi, ResearchTool } from '@/api/research';
import { clientsApi } from '@/api/clients';
import { settingsApi } from '@/api/settings';
import { getApiErrorMessage } from '@/utils/apiError';
import { notifyResearchSuccess, notifyResearchError, extractResearchMetrics } from '@/utils/researchNotifications';
import { ResearchDataCollectionPanel } from './ResearchDataCollectionPanel';
import { getDisabledToolIds } from '@/config/featureRegistry';

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

interface Props {
  projectId?: string;
  clientId?: string;
  onContinue?: () => void;
}

type Step = 'selection' | 'data-collection' | 'executing';

interface ExecutionState {
  currentTool: string | null;
  completed: string[];
  failed: Array<{ tool: string; error: string }>;
  isComplete: boolean;
}

// Memoized to prevent re-renders when parent updates (Performance optimization - December 25, 2025)
export const ResearchPanel = memo(function ResearchPanel({ projectId, clientId, onContinue }: Props) {
  const [step, setStep] = useState<Step>('selection');
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [collectedData, setCollectedData] = useState<Record<string, any>>({});
  const [results, setResults] = useState<Map<string, any>>(new Map());
  const [executionState, setExecutionState] = useState<ExecutionState>({
    currentTool: null,
    completed: [],
    failed: [],
    isComplete: false,
  });

  // Bug #58 Fix: Persist execution state across tab navigation using sessionStorage
  const storageKey = `research-execution-${projectId}`;

  // Restore execution state from sessionStorage on mount
  useEffect(() => {
    if (!projectId) return;

    try {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      const saved = sessionStorage.getItem(storageKey);
      if (saved) {
        const { step: savedStep, executionState: savedExecution, selected: savedSelected, collectedData: savedData } = JSON.parse(saved);

        // Only restore if we were in the executing step
        if (savedStep === 'executing') {
          setStep(savedStep);
          setExecutionState(savedExecution);
          setSelected(new Set(savedSelected));
          setCollectedData(savedData);
        }
      }
    } catch (error) {
      console.error('Failed to restore research execution state:', error);
      // Clear corrupted data
      sessionStorage.removeItem(storageKey);
    }
  }, [projectId, storageKey]); // Only run on mount or projectId change

  // Save execution state to sessionStorage whenever it changes
  useEffect(() => {
    if (!projectId || step !== 'executing') return;

    try {
      const state = {
        step,
        executionState,
        selected: Array.from(selected),
        collectedData,
        timestamp: new Date().toISOString(),
      };
      sessionStorage.setItem(storageKey, JSON.stringify(state));
    } catch (error) {
      console.error('Failed to save research execution state:', error);
    }
  }, [projectId, step, executionState, selected, collectedData, storageKey]);

  // Clear storage when execution completes and user continues
  const clearExecutionState = () => {
    if (projectId) {
      sessionStorage.removeItem(storageKey);
    }
  };


  // Fetch available research tools
  const { data: rawTools = [], isLoading } = useQuery({
    queryKey: ['research', 'tools'],
    queryFn: () => researchApi.listTools(),
  });

  // Apply registry disabled status — overrides backend status so UI stays in sync with registry
  const disabledToolIds = useMemo(() => getDisabledToolIds(), []);
  const tools = useMemo<ResearchTool[]>(
    () => rawTools.map((t: ResearchTool) =>
      disabledToolIds.has(t.name) ? { ...t, status: 'coming_soon' as const } : t
    ),
    [rawTools, disabledToolIds]
  );

  // Fetch research history for current client
  const historyQuery = useQuery({
    queryKey: ['research', 'history', clientId],
    queryFn: () => clientId ? researchApi.getClientHistory(clientId) : Promise.resolve(null),
    enabled: !!clientId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
  const historyData = historyQuery.data;

  // Fetch completed tools for current project (for prerequisite checking)
  const { data: completedToolsData } = useQuery({
    queryKey: ['research', 'completed', projectId],
    queryFn: () => projectId ? researchApi.getProjectResearchResults(projectId) : Promise.resolve(null),
    enabled: !!projectId,
    staleTime: 60 * 1000, // 1 minute
  });

  // Fetch integration status to check which tools can be enabled
  const { data: integrationStatus } = useQuery({
    queryKey: ['integrations', 'status'],
    queryFn: () => settingsApi.getIntegrationStatus(),
    staleTime: 30 * 1000, // 30 seconds
  });

  // Fetch client data for pre-populating research tool inputs
  const { data: clientData } = useQuery({
    queryKey: ['client', clientId],
    queryFn: () => clientId ? clientsApi.get(clientId) : Promise.resolve(null),
    enabled: !!clientId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Process history into map: tool_name -> most recent run date
  const toolHistory = useMemo(() => {
    if (!historyData?.results) return new Map<string, Date>();

    const map = new Map<string, Date>();
    historyData.results.forEach((result) => {
      const existingDate = map.get(result.toolName);
      const newDate = new Date(result.createdAt);

      // Keep only the most recent run
      if (!existingDate || newDate > existingDate) {
        map.set(result.toolName, newDate);
      }
    });

    return map;
  }, [historyData]);

  // Process completed tools for prerequisite checking
  const completedTools = useMemo(() => {
    if (!completedToolsData?.results) return new Set<string>();

    const completed = new Set<string>();
    completedToolsData.results.forEach((result) => {
      if (result.status === 'completed') {
        completed.add(result.toolName);
      }
    });

    return completed;
  }, [completedToolsData]);

  // Helper: Check if a prerequisite is fulfilled
  const isPrerequisiteFulfilled = (prereqToolName: string): boolean => {
    // Prerequisite is fulfilled if it's already completed OR if it's in the current selection
    return completedTools.has(prereqToolName) || selected.has(prereqToolName);
  };

  // Helper: Get prerequisite status for a tool
  const getPrerequisiteStatus = (toolName: string) => {
    const prereqs = TOOL_PREREQUISITES[toolName];
    if (!prereqs) return { fulfilled: [], unfulfilled: [], hasUnfulfilled: false, requiredUnfulfilled: [] };

    const allPrereqs = [...prereqs.required, ...prereqs.recommended];
    const fulfilled = allPrereqs.filter(p => isPrerequisiteFulfilled(p));
    const unfulfilled = allPrereqs.filter(p => !isPrerequisiteFulfilled(p));

    return {
      fulfilled,
      unfulfilled,
      hasUnfulfilled: unfulfilled.length > 0,
      requiredUnfulfilled: prereqs.required.filter(p => !isPrerequisiteFulfilled(p)),
    };
  };

  // Run research mutation
  const runResearchMutation = useMutation({
    mutationFn: ({ tool, params }: { tool: string; params?: Record<string, any> }) =>
      researchApi.run({
        projectId: projectId!,
        clientId: clientId!,
        tool,
        params: params || {},
      }),
    onSuccess: (data, variables) => {
      setResults(new Map(results).set(variables.tool, data));

      // Extract metrics from research outputs
      const metrics = extractResearchMetrics(data.outputs);

      // Show success notification
      notifyResearchSuccess({
        toolName: variables.tool,
        toolLabel: TOOL_LABELS[variables.tool],
        summary: metrics.summary,
        metrics: {
          count: metrics.count,
        },
      });

      // Invalidate history query to refresh the list
      historyQuery.refetch();
    },
    onError: (error, variables) => {
      const errorMessage = getApiErrorMessage(error);

      // Show error notification
      notifyResearchError({
        toolName: variables.tool,
        toolLabel: TOOL_LABELS[variables.tool],
        error: errorMessage,
        actionMessage: 'Please check your input and try again',
        onRetry: () => {
          // Re-trigger the same tool with same params
          runResearchMutation.mutate({ tool: variables.tool, params: variables.params });
        },
      });
    },
  });

  const toggleTool = (toolName: string) => {
    const newSelected = new Set(selected);
    if (newSelected.has(toolName)) {
      // Deselecting a tool
      newSelected.delete(toolName);
    } else {
      // Selecting a tool - auto-add required prerequisites
      newSelected.add(toolName);

      // Auto-suggest: Add required prerequisites if not already completed
      const prereqs = TOOL_PREREQUISITES[toolName];
      if (prereqs && prereqs.required.length > 0) {
        const missingRequired = prereqs.required.filter(
          prereqTool => !completedTools.has(prereqTool) && !newSelected.has(prereqTool)
        );

        if (missingRequired.length > 0) {
          // Auto-add required prerequisites
          missingRequired.forEach(prereqTool => newSelected.add(prereqTool));

          // Show notification
          const prereqNames = missingRequired.map(p => TOOL_LABELS[p] || p).join(', ');
        }
      }
    }
    setSelected(newSelected);
  };

  const selectByCategory = (category: string) => {
    const categoryTools = tools.filter((t) => t.category === category && t.status === 'available');
    const newSelected = new Set(selected);
    categoryTools.forEach((t) => newSelected.add(t.name));
    setSelected(newSelected);
  };

  const selectAvailable = () => {
    const available = tools.filter((t) => t.status === 'available');
    setSelected(new Set(available.map((t) => t.name)));
  };

  const clearAll = () => {
    setSelected(new Set());
  };

  const handleContinueFromSelection = () => {
    if (selected.size === 0) {
      // Skip research entirely
      if (onContinue) {
        onContinue();
      }
      return;
    }

    // Block execution: Check for missing required prerequisites
    const toolsWithMissingPrereqs: Array<{ tool: string; missing: string[] }> = [];

    for (const toolName of selected) {
      const prereqStatus = getPrerequisiteStatus(toolName);
      if (prereqStatus.requiredUnfulfilled.length > 0) {
        toolsWithMissingPrereqs.push({
          tool: toolName,
          missing: prereqStatus.requiredUnfulfilled,
        });
      }
    }

    // If any tools have missing required prerequisites, block and show error
    if (toolsWithMissingPrereqs.length > 0) {
      const errorMessages = toolsWithMissingPrereqs.map(({ tool, missing }) => {
        const toolLabel = TOOL_LABELS[tool] || tool;
        const missingLabels = missing.map(p => TOOL_LABELS[p] || p).join(', ');
        return `• ${toolLabel} requires: ${missingLabels}`;
      }).join('\n');

      alert(
        `Cannot proceed - some tools have missing required prerequisites:\n\n${errorMessages}\n\nPlease select the required prerequisites or remove these tools from your selection.`
      );
      return;
    }

    // All prerequisites met - move to data collection
    setStep('data-collection');
  };

  const handleDataCollected = (data: Record<string, any>) => {
    setCollectedData(data);
    setStep('executing');
    runSelectedResearch(data);
  };

  const runSelectedResearch = async (params: Record<string, any>) => {
    if (!projectId || !clientId) {
      alert('Project and client must be selected first');
      return;
    }

    // Reset execution state
    setExecutionState({
      currentTool: null,
      completed: [],
      failed: [],
      isComplete: false,
    });

    const completed: string[] = [];
    const failed: Array<{ tool: string; error: string }> = [];

    // Feature 3: Get optimal execution order from backend
    let executionOrder: string[];
    try {
      const orderResult = await researchApi.getExecutionOrder(Array.from(selected));
      executionOrder = orderResult.executionOrder;
    } catch (error) {
      console.error('Failed to get execution order, using selection order as fallback', error);
      // Fallback to original selection order if API fails
      executionOrder = Array.from(selected);
    }

    // Execute tools in dependency order (prerequisites first)
    for (const tool of executionOrder) {
      // Update current tool being executed
      setExecutionState(prev => ({ ...prev, currentTool: tool }));

      const toolParams = params[tool] || params;
      try {
        // Add 5 minute timeout per tool
        const timeoutPromise = new Promise((_, reject) =>
          setTimeout(() => reject(new Error('Tool execution timed out after 5 minutes')), 5 * 60 * 1000)
        );

        const executionPromise = runResearchMutation.mutateAsync({ tool, params: toolParams });

        await Promise.race([executionPromise, timeoutPromise]);

        completed.push(tool);
        setExecutionState(prev => ({
          ...prev,
          completed: [...prev.completed, tool],
          currentTool: null,
        }));
      } catch (error) {
        // Tool failed - record error and continue
        const errorMsg = error instanceof Error ? error.message : getApiErrorMessage(error);
        failed.push({ tool, error: errorMsg });
        setExecutionState(prev => ({
          ...prev,
          failed: [...prev.failed, { tool, error: errorMsg }],
          currentTool: null,
        }));
      }
    }

    // Mark execution as complete
    setExecutionState(prev => ({ ...prev, isComplete: true }));

    // Don't auto-advance if there are failures - let user review
    if (failed.length === 0 && onContinue) {
      clearExecutionState(); // Clear persisted state on successful completion
      onContinue();
    }
  };

  const handleRetryFailed = () => {
    // Retry only the failed tools
    const failedTools = new Set(executionState.failed.map(f => f.tool));
    setSelected(failedTools);
    setStep('data-collection');
  };

  const handleCancelExecution = () => {
    clearExecutionState(); // Clear persisted state on cancel
    // Go back to selection
    setStep('selection');
    setExecutionState({
      currentTool: null,
      completed: [],
      failed: [],
      isComplete: false,
    });
  };

  const handleContinueAfterExecution = () => {
    clearExecutionState(); // Clear persisted state when continuing after execution
    if (onContinue) {
      onContinue();
    }
  };


  const formatLastRun = (date: Date | undefined): { text: string; variant: 'fresh' | 'stale' | 'never' } => {
    if (!date) return { text: 'Never run', variant: 'never' };

    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return { text: 'Today', variant: 'fresh' };
    if (diffDays === 1) return { text: 'Yesterday', variant: 'fresh' };
    if (diffDays < 7) return { text: `${diffDays} days ago`, variant: 'fresh' };
    if (diffDays < 30) return { text: `${Math.floor(diffDays / 7)} weeks ago`, variant: 'fresh' };
    if (diffDays < 365) return { text: `${Math.floor(diffDays / 30)} months ago`, variant: 'stale' };
    return { text: 'Over a year ago', variant: 'stale' };
  };

  const getStatusBadge = (status?: string) => {
    if (status === 'coming_soon') {
      return (
        <span className="inline-block rounded-md bg-slate-100 dark:bg-slate-700 px-2 py-1 text-xs font-medium text-slate-600 dark:text-slate-300">
          Coming Soon
        </span>
      );
    }
    if (status === 'experimental') {
      return (
        <span className="inline-block rounded-md bg-amber-100 dark:bg-amber-900/30 px-2 py-1 text-xs font-medium text-amber-700 dark:text-amber-400">
          Experimental
        </span>
      );
    }
    return (
      <span className="inline-block rounded-md bg-emerald-100 dark:bg-emerald-900/30 px-2 py-1 text-xs font-medium text-emerald-700 dark:text-emerald-400">
        Available
      </span>
    );
  };

  const getCategoryTools = (category: string) => {
    return tools.filter((t) => t.category === category);
  };

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

  const categories = [
    { name: 'foundation', label: 'Client Foundation', description: 'Build foundational understanding' },
    { name: 'seo', label: 'SEO & Competition', description: 'Research keywords and competitors' },
    { name: 'market', label: 'Market Intelligence', description: 'Track trends and opportunities' },
    { name: 'strategy', label: 'Strategy & Planning', description: 'Plan content strategy' },
    { name: 'workshop', label: 'Workshop Assistants', description: 'Guided discovery sessions' },
  ];

  const totalCredits = Array.from(selected).reduce((sum, toolName) => {
    const tool = tools.find((t) => t.name === toolName);
    return sum + (tool?.credits || 0);
  }, 0);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-neutral-800 p-12 shadow-sm">
        <Loader2 className="h-6 w-6 animate-spin text-blue-600 dark:text-blue-400" />
        <span className="ml-2 text-sm text-slate-600 dark:text-neutral-400">Loading research tools...</span>
      </div>
    );
  }

  // Show data collection step
  if (step === 'data-collection') {
    return (
      <ResearchDataCollectionPanel
        selectedTools={Array.from(selected)}
        clientData={clientData || null}
        projectId={projectId}
        onContinue={handleDataCollected}
        onBack={() => setStep('selection')}
      />
    );
  }

  // Show executing step
  if (step === 'executing') {
    const { currentTool, completed, failed, isComplete } = executionState;
    const totalTools = selected.size;
    const successCount = completed.length;
    const failedCount = failed.length;
    const inProgress = !isComplete && currentTool !== null;

    return (
      <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-neutral-900 p-8 shadow-sm">
        <div className="flex flex-col items-center justify-center space-y-4">
          {/* Status Icon */}
          {inProgress && <Loader2 className="h-12 w-12 animate-spin text-blue-600 dark:text-blue-400" />}
          {isComplete && failedCount === 0 && (
            <CheckCircle2 className="h-12 w-12 text-emerald-600 dark:text-emerald-400" />
          )}
          {isComplete && failedCount > 0 && failedCount < totalTools && (
            <AlertCircle className="h-12 w-12 text-amber-600 dark:text-amber-400" />
          )}
          {isComplete && failedCount === totalTools && (
            <AlertCircle className="h-12 w-12 text-red-600 dark:text-red-400" />
          )}

          {/* Status Message */}
          <div className="text-center">
            <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-2">
              {inProgress && 'Running Research Tools'}
              {isComplete && failedCount === 0 && 'All Tools Completed Successfully'}
              {isComplete && failedCount > 0 && failedCount < totalTools && 'Completed with Some Failures'}
              {isComplete && failedCount === totalTools && 'All Tools Failed'}
            </h3>
            {inProgress && (
              <p className="text-sm text-neutral-600 dark:text-neutral-400">
                Currently executing: <span className="font-medium">{TOOL_LABELS[currentTool] || currentTool}</span>
              </p>
            )}
          </div>

          {/* Progress Summary */}
          <div className="mt-4 rounded-lg bg-neutral-50 dark:bg-neutral-800 px-4 py-3 max-w-md w-full">
            <div className="flex items-center justify-between text-sm mb-2">
              <span className="text-neutral-600 dark:text-neutral-400">Progress:</span>
              <span className="font-medium text-neutral-900 dark:text-neutral-100">
                {successCount + failedCount} of {totalTools}
              </span>
            </div>
            {successCount > 0 && (
              <div className="flex items-center justify-between text-sm text-emerald-600 dark:text-emerald-400">
                <span>✓ Completed:</span>
                <span className="font-medium">{successCount}</span>
              </div>
            )}
            {failedCount > 0 && (
              <div className="flex items-center justify-between text-sm text-red-600 dark:text-red-400">
                <span>✗ Failed:</span>
                <span className="font-medium">{failedCount}</span>
              </div>
            )}
          </div>

          {/* Failed Tools Details */}
          {failed.length > 0 && (
            <div className="mt-4 w-full max-w-2xl rounded-lg border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 p-4">
              <h4 className="font-medium text-red-900 dark:text-red-100 mb-2 flex items-center gap-2">
                <AlertCircle className="h-4 w-4" />
                Failed Tools
              </h4>
              <div className="space-y-2">
                {failed.map(({ tool, error }) => (
                  <div key={tool} className="text-sm">
                    <p className="font-medium text-red-800 dark:text-red-200">
                      {TOOL_LABELS[tool] || tool}
                    </p>
                    <p className="text-red-700 dark:text-red-300 text-xs mt-1">{error}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Action Buttons */}
          {isComplete && (
            <div className="flex gap-3 mt-6">
              {failedCount > 0 && (
                <button
                  onClick={handleRetryFailed}
                  className="rounded-lg bg-amber-600 dark:bg-amber-500 px-4 py-2 text-sm font-medium text-white hover:bg-amber-700 dark:hover:bg-amber-600"
                >
                  Retry Failed Tools
                </button>
              )}
              <button
                onClick={handleCancelExecution}
                className="rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 px-4 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700"
              >
                Back to Selection
              </button>
              {successCount > 0 && (
                <button
                  onClick={handleContinueAfterExecution}
                  className="rounded-lg bg-emerald-600 dark:bg-emerald-500 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 dark:hover:bg-emerald-600"
                >
                  Continue with {successCount} {successCount === 1 ? 'Result' : 'Results'}
                </button>
              )}
            </div>
          )}

          {/* Cancel Button while executing */}
          {!isComplete && (
            <button
              onClick={handleCancelExecution}
              className="mt-4 text-sm text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100 underline"
            >
              Cancel Execution
            </button>
          )}
        </div>
      </div>
    );
  }

  // Show tool selection step
  return (
    <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-neutral-800 p-6 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FlaskConical className="h-5 w-5 text-blue-600 dark:text-blue-400" />
          <h3 className="text-lg font-semibold text-slate-900 dark:text-neutral-100">Research Tools</h3>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={selectAvailable}
            className="rounded-md border border-blue-600 dark:border-blue-500 bg-blue-50 dark:bg-blue-900/20 px-3 py-1.5 text-sm font-medium text-blue-700 dark:text-blue-300 hover:bg-blue-100 dark:hover:bg-blue-900/30"
          >
            Select All Available
          </button>
          <button
            onClick={clearAll}
            className="rounded-md border border-slate-200 dark:border-slate-600 px-3 py-1.5 text-sm font-medium text-slate-700 dark:text-neutral-300 hover:bg-slate-50 dark:hover:bg-neutral-700"
          >
            Clear
          </button>
        </div>
      </div>

      <p className="mb-4 text-sm text-slate-600 dark:text-neutral-400">
        Select research tools to run for this project. Research adds depth to content generation and helps identify
        opportunities.
      </p>

      {/* Dependency Legend */}
      <div className="mb-6 rounded-lg border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/20 p-4">
        <div className="flex items-start gap-3">
          <div className="rounded-full bg-blue-100 dark:bg-blue-900/40 p-1.5">
            <Link2 className="h-4 w-4 text-blue-600 dark:text-blue-400" />
          </div>
          <div className="flex-1 space-y-2">
            <h4 className="text-sm font-semibold text-blue-900 dark:text-blue-200">Tool Dependencies</h4>
            <p className="text-xs text-blue-800 dark:text-blue-300">
              Some tools require data from other tools to function. Dependency badges show which prerequisites are needed:
            </p>
            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 text-xs font-semibold bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400">
                  <Link2 className="h-2.5 w-2.5" />
                  Tool Name
                </span>
                <span className="text-xs text-blue-700 dark:text-blue-300">= Required & Completed</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 text-xs font-semibold bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400">
                  <Link2 className="h-2.5 w-2.5" />
                  Tool Name
                </span>
                <span className="text-xs text-blue-700 dark:text-blue-300">= Required & Not Completed</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 text-xs font-normal bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400">
                  <Link2 className="h-2.5 w-2.5" />
                  Tool Name
                </span>
                <span className="text-xs text-blue-700 dark:text-blue-300">= Recommended & Completed</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 text-xs font-normal bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400">
                  <Link2 className="h-2.5 w-2.5" />
                  Tool Name
                </span>
                <span className="text-xs text-blue-700 dark:text-blue-300">= Recommended & Not Completed</span>
              </div>
            </div>
            <p className="mt-2 text-xs text-blue-700 dark:text-blue-300">
              <strong>Tip:</strong> Tools with unfulfilled required dependencies may not produce optimal results.
            </p>
          </div>
        </div>
      </div>

      {totalCredits > 0 && (
        <div className="mb-4 rounded-md bg-blue-50 dark:bg-blue-900/20 px-4 py-3 text-sm text-blue-800 dark:text-blue-200">
          <div className="flex items-center justify-between">
            <div>
              <strong>{selected.size} tools selected</strong>
              {selected.size > 0 && ` (${Array.from(selected).join(', ')})`}
            </div>
            <div className="flex items-center gap-1 font-semibold">
              <Coins className="h-4 w-4" />
              {totalCredits} credits
            </div>
          </div>
          <div className="text-xs text-blue-600 dark:text-blue-300 mt-1">
            ≈ ${(totalCredits * 0.1).toFixed(2)} at $0.10/credit
          </div>
        </div>
      )}

      <div className="space-y-6">
        {categories.map((category) => {
          const categoryTools = getCategoryTools(category.name);
          if (categoryTools.length === 0) return null;

          return (
            <div key={category.name} className="rounded-lg border border-slate-200 dark:border-slate-700 p-4">
              <div className="mb-3 flex items-center justify-between">
                <div className="flex-1">
                  <h4 className="text-sm font-semibold text-slate-900 dark:text-neutral-100">{category.label}</h4>
                  <p className="text-xs text-slate-600 dark:text-neutral-400">{category.description}</p>
                  {category.name === 'seo' && clientData && clientData.keywords && clientData.keywords.length >= 5 && (
                    <div className="mt-2 rounded-md bg-emerald-50 dark:bg-emerald-900/20 px-3 py-2 border border-emerald-200 dark:border-emerald-800">
                      <p className="text-xs text-emerald-800 dark:text-emerald-200 font-medium">
                        ✓ Client has {clientData.keywords.length} keywords — SEO Keyword Research is optional
                      </p>
                    </div>
                  )}
                </div>
                <button
                  onClick={() => selectByCategory(category.name)}
                  className="text-xs font-medium text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300"
                >
                  Select All
                </button>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                {categoryTools.map((tool) => {
                  const isSelected = selected.has(tool.name);
                  const isAvailable = tool.status === 'available';
                  const hasResult = results.has(tool.name);
                  const { enabled: integrationEnabled, missingIntegrations } = isToolEnabled(tool);
                  const canSelect = isAvailable && integrationEnabled;

                  return (
                    <button
                      key={tool.name}
                      onClick={() => canSelect && toggleTool(tool.name)}
                      disabled={!canSelect}
                      className={`group relative rounded-lg border-2 p-3 text-left transition-all ${
                        isSelected
                          ? 'border-blue-600 dark:border-blue-500 bg-blue-50 dark:bg-blue-900/20 shadow-md'
                          : 'border-slate-200 dark:border-slate-700 bg-white dark:bg-neutral-800 hover:border-slate-300 dark:hover:border-slate-600 hover:shadow-sm'
                      } ${!canSelect && 'cursor-not-allowed opacity-60'}`}
                    >
                      <div className="flex items-start gap-2">
                        {isSelected ? (
                          <CheckCircle2 className="h-5 w-5 flex-shrink-0 text-blue-600 dark:text-blue-400" />
                        ) : (
                          <Circle className="h-5 w-5 flex-shrink-0 text-slate-300 dark:text-slate-600 group-hover:text-slate-400 dark:group-hover:text-slate-500" />
                        )}
                        <div className="flex-1 min-w-0">
                          <h5 className={`text-sm font-semibold ${isSelected ? 'text-blue-900 dark:text-blue-200' : 'text-slate-900 dark:text-neutral-100'}`}>
                            {tool.label}
                          </h5>
                          {tool.description && <p className="mt-1 text-xs text-slate-600 dark:text-neutral-400">{tool.description}</p>}
                          <div className="mt-2 flex items-center justify-between gap-2">
                            {getStatusBadge(tool.status)}
                            {tool.credits && (
                              <span className="text-xs font-medium text-slate-700 dark:text-neutral-300 flex items-center gap-1">
                                <Coins className="h-3 w-3" />
                                {tool.credits} credits
                              </span>
                            )}
                          </div>
                          {(() => {
                            const lastRunDate = toolHistory.get(tool.name);
                            const lastRun = formatLastRun(lastRunDate);
                            const colorClass = lastRun.variant === 'fresh'
                              ? 'text-emerald-600 dark:text-emerald-400'
                              : lastRun.variant === 'stale'
                              ? 'text-amber-600 dark:text-amber-400'
                              : 'text-slate-500 dark:text-slate-400';

                            return (
                              <div className={`mt-2 flex items-center gap-1 text-xs ${colorClass}`}>
                                <Clock className="h-3 w-3" />
                                <span>Last run: {lastRun.text}</span>
                              </div>
                            );
                          })()}
                          {(() => {
                            const prereqs = TOOL_PREREQUISITES[tool.name];
                            if (!prereqs || (prereqs.required.length === 0 && prereqs.recommended.length === 0)) {
                              return null;
                            }

                            const status = getPrerequisiteStatus(tool.name);

                            return (
                              <div className="mt-2 space-y-1">
                                {status.requiredUnfulfilled.length > 0 && (
                                  <div className="flex items-start gap-1 text-xs text-amber-700 dark:text-amber-400">
                                    <AlertCircle className="h-3 w-3 flex-shrink-0 mt-0.5" />
                                    <span className="font-medium">Requires: {status.requiredUnfulfilled.map(p => TOOL_LABELS[p] || p).join(', ')}</span>
                                  </div>
                                )}
                                {(status.fulfilled.length > 0 || status.unfulfilled.length > 0) && (
                                  <div className="flex flex-wrap gap-1">
                                    {prereqs.required.map(prereqToolName => {
                                      const isFulfilled = isPrerequisiteFulfilled(prereqToolName);
                                      return (
                                        <span
                                          key={prereqToolName}
                                          className={`inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 text-xs font-semibold ${
                                            isFulfilled
                                              ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400'
                                              : 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400'
                                          }`}
                                        >
                                          <Link2 className="h-2.5 w-2.5" />
                                          {TOOL_LABELS[prereqToolName] || prereqToolName}
                                        </span>
                                      );
                                    })}
                                    {prereqs.recommended.map(prereqToolName => {
                                      const isFulfilled = isPrerequisiteFulfilled(prereqToolName);
                                      return (
                                        <span
                                          key={prereqToolName}
                                          className={`inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 text-xs font-normal ${
                                            isFulfilled
                                              ? 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400'
                                              : 'bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400'
                                          }`}
                                        >
                                          <Link2 className="h-2.5 w-2.5" />
                                          {TOOL_LABELS[prereqToolName] || prereqToolName}
                                        </span>
                                      );
                                    })}
                                  </div>
                                )}
                              </div>
                            );
                          })()}
                          {missingIntegrations.length > 0 && (
                            <div className="mt-2 rounded-md bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 px-2 py-1.5 text-xs text-red-700 dark:text-red-400">
                              <div className="flex items-start gap-1.5">
                                <Settings className="h-3.5 w-3.5 flex-shrink-0 mt-0.5" />
                                <div>
                                  <p className="font-semibold">Integration Required</p>
                                  <p className="mt-0.5">{missingIntegrations.join(', ')}</p>
                                  <a
                                    href="/dashboard/settings?tab=integrations"
                                    onClick={(e) => e.stopPropagation()}
                                    className="mt-1 inline-block text-red-600 dark:text-red-400 underline hover:text-red-800 dark:hover:text-red-300"
                                  >
                                    Configure in Settings →
                                  </a>
                                </div>
                              </div>
                            </div>
                          )}
                          {hasResult && (
                            <div className="mt-2 rounded bg-emerald-50 dark:bg-emerald-900/20 px-2 py-1 text-xs text-emerald-700 dark:text-emerald-400">
                              ✓ Research completed
                            </div>
                          )}
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-6 flex items-center justify-between border-t border-slate-200 dark:border-slate-700 pt-4">
        <div className="text-sm text-slate-600 dark:text-neutral-400">
          {selected.size === 0 && 'Research is optional - you can skip this step'}
          {selected.size > 0 && 'Click "Continue" to provide required data and run research'}
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleContinueFromSelection}
            disabled={!projectId || !clientId}
            className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {selected.size === 0 ? 'Skip Research' : 'Continue'}
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
});
