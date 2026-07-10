  import { useState, useEffect, memo } from 'react';
  import { CheckCircle2, Circle, FileText, ArrowRight, AlertTriangle, Link2, Sparkles } from 'lucide-react';
  import { PlatformSelector } from './PlatformSelector';
  import { generatorApi, type TemplateDependencies } from '@/api/generator';
  import { researchApi } from '@/api/research';

  interface Template {
    id: number;
    name: string;
    description: string;
    bestFor: string;
    difficulty: 'fast' | 'medium' | 'slow';
  }

  const TEMPLATES: Template[] = [
    {
      id: 1,
      name: 'Problem Recognition',
      description: 'Hook problem → Validate feeling → Hint at solution',
      bestFor: 'Building awareness, getting engagement',
      difficulty: 'fast',
    },
    {
      id: 2,
      name: 'Statistic + Insight',
      description: 'Stat → What it means → Unexpected angle',
      bestFor: 'Credibility, thought leadership',
      difficulty: 'fast',
    },
    {
      id: 3,
      name: 'Contrarian Take',
      description: 'Challenge conventional wisdom → Show why → Give nuance',
      bestFor: 'Differentiation, starting conversations',
      difficulty: 'medium',
    },
    {
      id: 4,
      name: 'What Changed',
      description: 'Old way → What changed → New results',
      bestFor: 'Authority, sharing lessons',
      difficulty: 'medium',
    },
    {
      id: 5,
      name: 'Question Post',
      description: 'Thought-provoking question with context',
      bestFor: 'Engagement magnet',
      difficulty: 'fast',
    },
    {
      id: 6,
      name: 'Personal Story',
      description: 'Vulnerable narrative with lesson learned',
      bestFor: 'Connection, vulnerability',
      difficulty: 'slow',
    },
    {
      id: 7,
      name: 'Myth Busting',
      description: 'Common belief → Why it is wrong → What is true',
      bestFor: 'Education, correction',
      difficulty: 'medium',
    },
    {
      id: 8,
      name: 'Things I Got Wrong',
      description: 'Past mistakes and lessons learned',
      bestFor: 'Credibility, humility',
      difficulty: 'slow',
    },
    {
      id: 9,
      name: 'How-To',
      description: 'Step-by-step actionable guide',
      bestFor: 'Actionable value',
      difficulty: 'fast',
    },
    {
      id: 10,
      name: 'Comparison',
      description: 'Option A vs Option B breakdown',
      bestFor: 'Decision-making',
      difficulty: 'fast',
    },
    {
      id: 11,
      name: 'What I Learned From',
      description: 'Lessons from books, events, or experiences',
      bestFor: 'Cultural relevance',
      difficulty: 'medium',
    },
    {
      id: 12,
      name: 'Inside Look',
      description: 'Behind-the-scenes process reveal',
      bestFor: 'Transparency, trust',
      difficulty: 'slow',
    },
    {
      id: 13,
      name: 'Future Thinking',
      description: 'Predictions and forward-looking insights',
      bestFor: 'Thought leadership',
      difficulty: 'medium',
    },
    {
      id: 14,
      name: 'Reader Q Response',
      description: 'Answer common customer questions',
      bestFor: 'Community building',
      difficulty: 'medium',
    },
    {
      id: 15,
      name: 'Milestone',
      description: 'Celebrate achievements and progress',
      bestFor: 'Celebration',
      difficulty: 'slow',
    },
  ];

  // Tool name to display label mapping
  const TOOL_LABELS: Record<string, string> = {
    audience_research: 'Audience Research',
    seo_keyword_research: 'SEO Keywords',
    competitive_analysis: 'Competitive Analysis',
    market_trends: 'Market Trends',
    story_mining: 'Story Mining',
    brand_archetype: 'Brand Archetype',
    icp_workshop: 'ICP Workshop',
    content_gap_analysis: 'Content Gap',
    voice_analysis: 'Voice Analysis',
    platform_strategy: 'Platform Strategy',
    content_calendar: 'Content Calendar',
    content_audit: 'Content Audit',
  };

  interface Props {
    initialSelection?: number[];
    targetPlatform?: string;
    clientId?: string;
    projectId?: string;
    onPlatformChange?: (platform: string) => void;
    onContinue?: (selectedIds: number[]) => void;
    onNavigateToResearch?: () => void;
  }

  // Memoized to prevent re-renders when parent updates (Performance optimization - December 25, 2025)
  export const TemplateSelectionPanel = memo(function TemplateSelectionPanel({
    initialSelection = [],
    targetPlatform = 'generic',
    projectId,
    onPlatformChange = () => {},
    onContinue,
    onNavigateToResearch,
  }: Props) {
    const [selected, setSelected] = useState<Set<number>>(new Set(initialSelection));
    const [dependencies, setDependencies] = useState<Map<number, TemplateDependencies>>(new Map());
    const [completedTools, setCompletedTools] = useState<Set<string>>(new Set());
    const [loadingDeps, setLoadingDeps] = useState(false);

    // Fetch completed research tools
    useEffect(() => {
      if (!projectId) return;

      const fetchCompletedResearch = async () => {
        try {
          const response = await researchApi.getProjectResearchResults(projectId);
          const toolNames = new Set(response.results.map((r) => r.toolName));
          setCompletedTools(toolNames);
        } catch (error) {
          console.error('Failed to fetch research results:', error);
        }
      };

      fetchCompletedResearch();
    }, [projectId]);

    // Fetch dependencies for selected templates
    useEffect(() => {
      if (selected.size === 0) {
        setDependencies(new Map());
        return;
      }

      const fetchDependencies = async () => {
        setLoadingDeps(true);
        const newDeps = new Map<number, TemplateDependencies>();

        try {
          await Promise.all(
            Array.from(selected).map(async (templateId) => {
              try {
                const response = await generatorApi.getTemplateDependencies(templateId);
                newDeps.set(templateId, response.research_dependencies);
              } catch (error) {
                console.error(`Failed to fetch dependencies for template ${templateId}:`, error);
              }
            })
          );

          setDependencies(newDeps);
        } finally {
          setLoadingDeps(false);
        }
      };

      fetchDependencies();
    }, [selected]);

    const toggleTemplate = (id: number) => {
      const newSelected = new Set(selected);
      if (newSelected.has(id)) {
        newSelected.delete(id);
      } else {
        newSelected.add(id);
      }
      setSelected(newSelected);
    };

    const selectAll = () => {
      setSelected(new Set(TEMPLATES.map((t) => t.id)));
    };

    const clearAll = () => {
      setSelected(new Set());
    };

    const selectRecommended = () => {
      // Fast templates: 1, 2, 5, 9, 10 (good for quick wins)
      setSelected(new Set([1, 2, 3, 4, 5, 9, 10]));
    };

    const getDifficultyColor = (difficulty: Template['difficulty']) => {
      switch (difficulty) {
        case 'fast':
          return 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300';
        case 'medium':
          return 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300';
        case 'slow':
          return 'bg-rose-100 dark:bg-rose-900/40 text-rose-700 dark:text-rose-300';
      }
    };

    const getDifficultyLabel = (difficulty: Template['difficulty']) => {
      switch (difficulty) {
        case 'fast':
          return '⚡ Fast (5 min)';
        case 'medium':
          return '⏱️ Medium (7-8 min)';
        case 'slow':
          return '🕐 Slow (10 min)';
      }
    };

    // Calculate aggregate research requirements
    const aggregateDependencies = () => {
      const allRequired = new Set<string>();
      const allRecommended = new Set<string>();

      dependencies.forEach((deps) => {
        deps.required.forEach((tool) => allRequired.add(tool));
        deps.recommended.forEach((tool) => allRecommended.add(tool));
      });

      return { allRequired, allRecommended };
    };

    const { allRequired, allRecommended } = aggregateDependencies();
    const missingRequired = Array.from(allRequired).filter((tool) => !completedTools.has(tool));
    const missingRecommended = Array.from(allRecommended).filter(
      (tool) => !completedTools.has(tool) && !allRequired.has(tool)
    );

    return (
      <div className="space-y-8">
        {/* Platform Selector */}
        <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6 shadow-sm">
          <PlatformSelector selected={targetPlatform} onChange={onPlatformChange} />
        </div>

        {/* Template Selection */}
        <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-blue-600" />
              <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">Template Selection</h3>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={selectRecommended}
                className="rounded-md border border-blue-600 bg-blue-50 dark:bg-blue-900/20 px-3 py-1.5 text-sm font-medium text-blue-700 dark:text-blue-300 hover:bg-blue-100 dark:hover:bg-blue-900/30"
              >
                Recommended (7)
              </button>
              <button
                onClick={selectAll}
                className="rounded-md border border-neutral-200 dark:border-neutral-700 px-3 py-1.5 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800"
              >
                Select All
              </button>
              <button
                onClick={clearAll}
                className="rounded-md border border-neutral-200 dark:border-neutral-700 px-3 py-1.5 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800"
              >
                Clear
              </button>
            </div>
          </div>

          <p className="mb-6 text-sm text-neutral-600 dark:text-neutral-400">
            Select templates to use for content generation. Typically 7-10 templates are selected for a 30-post package (2
            posts per template).
          </p>

          <div className="mb-4 rounded-md bg-blue-50 dark:bg-blue-900/20 px-4 py-3 text-sm text-blue-800 dark:text-blue-200">
            <strong>{selected.size} templates selected</strong>
            {selected.size > 0 && ` → ${selected.size * 2} posts (2 per template)`}
          </div>

          {/* Research Dependencies Warning */}
          {selected.size > 0 && !loadingDeps && missingRequired.length > 0 && (
            <div className="mb-4 rounded-md bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 px-4 py-3">
              <div className="flex items-start gap-3">
                <AlertTriangle className="h-5 w-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <h4 className="text-sm font-semibold text-amber-900 dark:text-amber-100 mb-2">
                    Missing Required Research
                  </h4>
                  <p className="text-sm text-amber-800 dark:text-amber-200 mb-3">
                    Selected templates require {missingRequired.length} research{' '}
                    {missingRequired.length === 1 ? 'tool' : 'tools'} that haven't been run yet. Running these tools will
                    improve content quality.
                  </p>
                  <div className="flex flex-wrap gap-2 mb-3">
                    {missingRequired.map((tool) => (
                      <span
                        key={tool}
                        className="inline-flex items-center gap-1 rounded-md bg-amber-100 dark:bg-amber-900/40 px-2 py-1 text-xs font-medium text-amber-800 dark:text-amber-200"
                      >
                        <Link2 className="h-3 w-3" />
                        {TOOL_LABELS[tool] || tool}
                      </span>
                    ))}
                  </div>
                  {onNavigateToResearch && (
                    <button
                      onClick={onNavigateToResearch}
                      className="inline-flex items-center gap-2 rounded-md bg-amber-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-amber-700"
                    >
                      <Sparkles className="h-4 w-4" />
                      Run Required Research
                    </button>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Recommended Research Info */}
          {selected.size > 0 && !loadingDeps && missingRecommended.length > 0 && missingRequired.length === 0 && (
            <div className="mb-4 rounded-md bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 px-4 py-3">
              <div className="flex items-start gap-3">
                <Sparkles className="h-5 w-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <h4 className="text-sm font-semibold text-blue-900 dark:text-blue-100 mb-2">
                    Recommended Research Available
                  </h4>
                  <p className="text-sm text-blue-800 dark:text-blue-200 mb-2">
                    Consider running these optional research tools for enhanced content:
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {missingRecommended.map((tool) => (
                      <span
                        key={tool}
                        className="inline-flex items-center gap-1 rounded-md bg-blue-100 dark:bg-blue-900/40 px-2 py-1 text-xs font-medium text-blue-800 dark:text-blue-200"
                      >
                        <Link2 className="h-3 w-3" />
                        {TOOL_LABELS[tool] || tool}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* All Research Complete */}
          {selected.size > 0 &&
            !loadingDeps &&
            missingRequired.length === 0 &&
            (allRequired.size > 0 || allRecommended.size > 0) && (
              <div className="mb-4 rounded-md bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 px-4 py-3">
                <div className="flex items-start gap-3">
                  <CheckCircle2 className="h-5 w-5 text-emerald-600 dark:text-emerald-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <h4 className="text-sm font-semibold text-emerald-900 dark:text-emerald-100 mb-1">
                      All Required Research Complete
                    </h4>
                    <p className="text-sm text-emerald-800 dark:text-emerald-200">
                      You have all the research needed for optimal content generation with selected templates.
                    </p>
                  </div>
                </div>
              </div>
            )}

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {TEMPLATES.map((template) => {
              const isSelected = selected.has(template.id);
              const templateDeps = dependencies.get(template.id);
              const hasRequiredDeps = templateDeps?.required && templateDeps.required.length > 0;
              const hasRecommendedDeps = templateDeps?.recommended && templateDeps.recommended.length > 0;

              return (
                <button
                  key={template.id}
                  onClick={() => toggleTemplate(template.id)}
                  className={`group relative rounded-lg border-2 p-4 text-left transition-all ${
                    isSelected
                      ? 'border-blue-600 bg-blue-50 dark:bg-blue-900/20 shadow-md'
                      : 'border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 hover:border-neutral-300 dark:hover:border-neutral-600 hover:shadow-sm'
                  }`}
                >
                  <div className="mb-2 flex items-start justify-between">
                    <div className="flex-1">
                      <div className="mb-1 flex items-center gap-2">
                        {isSelected ? (
                          <CheckCircle2 className="h-5 w-5 flex-shrink-0 text-blue-600" />
                        ) : (
                          <Circle className="h-5 w-5 flex-shrink-0 text-neutral-300 dark:text-neutral-600 group-hover:text-neutral-400 dark:group-hover:text-neutral-500" />
                        )}
                        <h4
                          className={`text-sm font-semibold ${isSelected ? 'text-blue-900 dark:text-blue-100' : 'text-neutral-900 dark:text-neutral-100'}`}
                        >
                          #{template.id}. {template.name}
                        </h4>
                      </div>
                      <p className="ml-7 text-xs text-neutral-600 dark:text-neutral-400">{template.description}</p>
                    </div>
                  </div>

                  <div className="ml-7 mt-3 space-y-2">
                    <div className="text-xs text-neutral-700 dark:text-neutral-300">
                      <strong>Best for:</strong> {template.bestFor}
                    </div>
                    <div>
                      <span className={`inline-block rounded-md px-2 py-1 text-xs font-medium ${getDifficultyColor(template.difficulty)}`}>
                        {getDifficultyLabel(template.difficulty)}
                      </span>
                    </div>

                    {/* Research Dependencies for this template */}
                    {isSelected && templateDeps && (hasRequiredDeps || hasRecommendedDeps) && (
                      <div className="mt-2 pt-2 border-t border-neutral-200 dark:border-neutral-700 space-y-1">
                        {hasRequiredDeps && (
                          <div className="text-xs">
                            <span className="font-semibold text-neutral-700 dark:text-neutral-300">Required:</span>
                            <div className="flex flex-wrap gap-1 mt-1">
                              {templateDeps.required.map((tool) => (
                                <span
                                  key={tool}
                                  className={`inline-block rounded px-1.5 py-0.5 text-xs ${
                                    completedTools.has(tool)
                                      ? 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300'
                                      : 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300'
                                  }`}
                                >
                                  {completedTools.has(tool) ? '✓' : '⚠'} {TOOL_LABELS[tool] || tool}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                        {hasRecommendedDeps && (
                          <div className="text-xs">
                            <span className="font-semibold text-neutral-700 dark:text-neutral-300">Recommended:</span>
                            <div className="flex flex-wrap gap-1 mt-1">
                              {templateDeps.recommended.map((tool) => (
                                <span
                                  key={tool}
                                  className={`inline-block rounded px-1.5 py-0.5 text-xs ${
                                    completedTools.has(tool)
                                      ? 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300'
                                      : 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300'
                                  }`}
                                >
                                  {completedTools.has(tool) ? '✓' : '○'} {TOOL_LABELS[tool] || tool}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </button>
              );
            })}
          </div>

          <div className="mt-6 flex items-center justify-between border-t border-neutral-200 dark:border-neutral-700 pt-4">
            <div className="text-sm text-neutral-600 dark:text-neutral-400">
              {selected.size === 0 && 'Select at least one template to continue'}
              {selected.size > 0 && selected.size < 5 && 'Consider selecting 7-10 templates for variety'}
              {selected.size >= 5 && selected.size <= 12 && '✓ Good selection'}
              {selected.size > 12 && 'You have selected many templates - generation may take longer'}
            </div>
            <button
              onClick={() => onContinue?.(Array.from(selected))}
              disabled={selected.size === 0}
              className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 dark:hover:bg-blue-800 disabled:cursor-not-allowed
  disabled:opacity-50"
            >
              Continue to Generation
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    );
  });
