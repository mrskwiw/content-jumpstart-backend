import { useState, memo } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { CheckCircle2, Circle, FlaskConical, ArrowRight, Loader2, DollarSign } from 'lucide-react';
import { researchApi, ResearchTool } from '@/api/research';
import { ResearchDataCollectionPanel } from './ResearchDataCollectionPanel';

interface Props {
  projectId?: string;
  clientId?: string;
  onContinue?: () => void;
}

type Step = 'selection' | 'data-collection' | 'executing';

// Memoized to prevent re-renders when parent updates (Performance optimization - December 25, 2025)
export const ResearchPanel = memo(function ResearchPanel({ projectId, clientId, onContinue }: Props) {
  const [step, setStep] = useState<Step>('selection');
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [collectedData, setCollectedData] = useState<Record<string, any>>({});
  const [results, setResults] = useState<Map<string, any>>(new Map());

  // Fetch available research tools
  const { data: tools = [], isLoading } = useQuery({
    queryKey: ['research', 'tools'],
    queryFn: () => researchApi.listTools(),
  });

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
      console.log(`Research tool "${variables.tool}" completed successfully`);
    },
    onError: (error, variables) => {
      console.error(`Research tool "${variables.tool}" failed:`, error);
      alert(`Failed to run research tool "${variables.tool}": ${error instanceof Error ? error.message : 'Unknown error'}`);
    },
  });

  const toggleTool = (toolName: string) => {
    const newSelected = new Set(selected);
    if (newSelected.has(toolName)) {
      newSelected.delete(toolName);
    } else {
      newSelected.add(toolName);
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
    } else {
      // Move to data collection step
      setStep('data-collection');
    }
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

    for (const tool of selected) {
      // Get tool-specific params if they exist
      const toolParams = params[tool] || params;
      await runResearchMutation.mutateAsync({ tool, params: toolParams });
    }

    // Automatically advance to next step after research completes
    if (onContinue) {
      onContinue();
    }
  };

  const getStatusBadge = (status?: string) => {
    if (status === 'coming_soon') {
      return (
        <span className="inline-block rounded-md bg-slate-100 px-2 py-1 text-xs font-medium text-slate-600">
          Coming Soon
        </span>
      );
    }
    return (
      <span className="inline-block rounded-md bg-emerald-100 px-2 py-1 text-xs font-medium text-emerald-700">
        Available
      </span>
    );
  };

  const getCategoryTools = (category: string) => {
    return tools.filter((t) => t.category === category);
  };

  const categories = [
    { name: 'foundation', label: 'Client Foundation', description: 'Build foundational understanding' },
    { name: 'seo', label: 'SEO & Competition', description: 'Research keywords and competitors' },
    { name: 'market', label: 'Market Intelligence', description: 'Track trends and opportunities' },
    { name: 'strategy', label: 'Strategy & Planning', description: 'Plan content strategy' },
    { name: 'workshop', label: 'Workshop Assistants', description: 'Guided discovery sessions' },
  ];

  const totalPrice = Array.from(selected).reduce((sum, toolName) => {
    const tool = tools.find((t) => t.name === toolName);
    return sum + (tool?.price || 0);
  }, 0);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center rounded-lg border border-slate-200 bg-white p-12 shadow-sm">
        <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
        <span className="ml-2 text-sm text-slate-600">Loading research tools...</span>
      </div>
    );
  }

  // Show data collection step
  if (step === 'data-collection') {
    return (
      <ResearchDataCollectionPanel
        selectedTools={Array.from(selected)}
        onContinue={handleDataCollected}
        onBack={() => setStep('selection')}
      />
    );
  }

  // Show executing step
  if (step === 'executing') {
    return (
      <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-neutral-900 p-8 shadow-sm">
        <div className="flex flex-col items-center justify-center space-y-4">
          <Loader2 className="h-12 w-12 animate-spin text-blue-600 dark:text-blue-400" />
          <div className="text-center">
            <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-2">
              Running Research Tools
            </h3>
            <p className="text-sm text-neutral-600 dark:text-neutral-400">
              Executing {selected.size} research {selected.size === 1 ? 'tool' : 'tools'}...
            </p>
            <p className="text-xs text-neutral-500 dark:text-neutral-500 mt-2">
              Tools: {Array.from(selected).join(', ')}
            </p>
          </div>
          <div className="mt-4 rounded-lg bg-blue-50 dark:bg-blue-900/20 px-4 py-3 max-w-md">
            <p className="text-sm text-blue-800 dark:text-blue-300">
              {results.size} of {selected.size} completed
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Show tool selection step
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FlaskConical className="h-5 w-5 text-blue-600" />
          <h3 className="text-lg font-semibold text-slate-900">Research Tools</h3>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={selectAvailable}
            className="rounded-md border border-blue-600 bg-blue-50 px-3 py-1.5 text-sm font-medium text-blue-700 hover:bg-blue-100"
          >
            Select All Available
          </button>
          <button
            onClick={clearAll}
            className="rounded-md border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Clear
          </button>
        </div>
      </div>

      <p className="mb-6 text-sm text-slate-600">
        Select research tools to run for this project. Research adds depth to content generation and helps identify
        opportunities.
      </p>

      {totalPrice > 0 && (
        <div className="mb-4 rounded-md bg-blue-50 px-4 py-3 text-sm text-blue-800">
          <div className="flex items-center justify-between">
            <div>
              <strong>{selected.size} tools selected</strong>
              {selected.size > 0 && ` (${Array.from(selected).join(', ')})`}
            </div>
            <div className="flex items-center gap-1 font-semibold">
              <DollarSign className="h-4 w-4" />
              {totalPrice.toFixed(2)}
            </div>
          </div>
        </div>
      )}

      <div className="space-y-6">
        {categories.map((category) => {
          const categoryTools = getCategoryTools(category.name);
          if (categoryTools.length === 0) return null;

          return (
            <div key={category.name} className="rounded-lg border border-slate-200 p-4">
              <div className="mb-3 flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-semibold text-slate-900">{category.label}</h4>
                  <p className="text-xs text-slate-600">{category.description}</p>
                </div>
                <button
                  onClick={() => selectByCategory(category.name)}
                  className="text-xs font-medium text-blue-600 hover:text-blue-700"
                >
                  Select All
                </button>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                {categoryTools.map((tool) => {
                  const isSelected = selected.has(tool.name);
                  const isAvailable = tool.status === 'available';
                  const hasResult = results.has(tool.name);

                  return (
                    <button
                      key={tool.name}
                      onClick={() => isAvailable && toggleTool(tool.name)}
                      disabled={!isAvailable}
                      className={`group relative rounded-lg border-2 p-3 text-left transition-all ${
                        isSelected
                          ? 'border-blue-600 bg-blue-50 shadow-md'
                          : 'border-slate-200 bg-white hover:border-slate-300 hover:shadow-sm'
                      } ${!isAvailable && 'cursor-not-allowed opacity-60'}`}
                    >
                      <div className="flex items-start gap-2">
                        {isSelected ? (
                          <CheckCircle2 className="h-5 w-5 flex-shrink-0 text-blue-600" />
                        ) : (
                          <Circle className="h-5 w-5 flex-shrink-0 text-slate-300 group-hover:text-slate-400" />
                        )}
                        <div className="flex-1 min-w-0">
                          <h5 className={`text-sm font-semibold ${isSelected ? 'text-blue-900' : 'text-slate-900'}`}>
                            {tool.label}
                          </h5>
                          {tool.description && <p className="mt-1 text-xs text-slate-600">{tool.description}</p>}
                          <div className="mt-2 flex items-center justify-between gap-2">
                            {getStatusBadge(tool.status)}
                            {tool.price && (
                              <span className="text-xs font-medium text-slate-700">${tool.price.toFixed(2)}</span>
                            )}
                          </div>
                          {hasResult && (
                            <div className="mt-2 rounded bg-emerald-50 px-2 py-1 text-xs text-emerald-700">
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

      <div className="mt-6 flex items-center justify-between border-t border-slate-200 pt-4">
        <div className="text-sm text-slate-600">
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
