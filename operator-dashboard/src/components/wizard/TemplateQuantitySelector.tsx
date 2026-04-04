import { useState, useMemo, memo, useEffect } from 'react';
import { Plus, Minus, Coins, FileText, Calculator, TrendingUp, HelpCircle, AlertCircle, X, CheckCircle2, Sparkles, Link2 } from 'lucide-react';
import { PlatformSelector } from './PlatformSelector';
import { generatorApi, type TemplateDependencies } from '@/api/generator';
import { researchApi, type ResearchResultListResponse } from '@/api/research';

interface Template {
  id: number;
  name: string;
  description: string;
  bestFor: string;
  difficulty: 'fast' | 'medium' | 'slow';
}

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

// Static prerequisite display data — mirrors backend TEMPLATE_PREREQUISITES
// Shown on every template card before selection so users see requirements upfront
const FIELD_LABELS: Record<string, string> = {
  business_description: 'business description',
  ideal_customer: 'ideal customer',
  industry: 'industry',
  main_problem_solved: 'main problem solved',
  customer_pain_points: 'pain points',
  customer_questions: 'customer questions',
};

// Story-dependent templates: template ID → story count slug from validation.story_counts
const STORY_TEMPLATE_SLUGS: Record<number, string> = {
  6: 'personal_story',
  8: 'things_i_got_wrong',
  12: 'inside_look',
  15: 'milestone',
};

const TEMPLATE_STATIC_PREREQS: Record<number, { fields: string[]; tools: string[] }> = {
  1:  { fields: ['customer_pain_points', 'ideal_customer'], tools: [] },
  2:  { fields: ['industry', 'business_description'], tools: [] },
  3:  { fields: ['industry'], tools: [] },
  4:  { fields: ['industry'], tools: [] },
  5:  { fields: ['ideal_customer'], tools: [] },
  6:  { fields: ['business_description'], tools: ['story_mining'] },
  7:  { fields: ['industry'], tools: [] },
  8:  { fields: ['business_description'], tools: ['story_mining'] },
  9:  { fields: ['business_description', 'main_problem_solved'], tools: [] },
  10: { fields: ['industry'], tools: [] },
  11: { fields: ['business_description'], tools: [] },
  12: { fields: ['business_description'], tools: ['story_mining'] },
  13: { fields: ['industry', 'business_description'], tools: [] },
  14: { fields: ['customer_questions'], tools: [] },
  15: { fields: ['business_description'], tools: ['story_mining'] },
};

interface Props {
  initialQuantities?: Record<number, number>;
  initialIncludeResearch?: boolean;
  initialTopics?: string[];  // NEW: custom topics for generation
  initialTargetPlatform?: string;  // NEW: target platform
  projectId?: string;  // NEW: for fetching research results
  clientId?: string;  // NEW: for fetching research results
  onNavigateToResearch?: () => void;  // NEW: navigate to research step
  onContinue?: (
    quantities: Record<number, number>,
    includeResearch: boolean,
    totalPrice: number,
    customTopics: string[],
    targetPlatform: string
  ) => void;
  onEditClient?: () => void;  // Navigate to client edit
}

const CREDITS_PER_POST = 20;  // $40/post ÷ $2/credit = 20 credits
// const RESEARCH_PRICE_PER_POST = 15.0; // DEPRECATED: Research now handled by granular tools

export const TemplateQuantitySelector = memo(function TemplateQuantitySelector({
  initialQuantities = {},
  initialIncludeResearch = false,
  initialTopics = [],  // NEW
  initialTargetPlatform = 'generic',  // NEW
  projectId,  // NEW
  clientId,  // NEW
  onNavigateToResearch,  // NEW
  onContinue,
  onEditClient,
}: Props) {
  const [quantities, setQuantities] = useState<Record<number, number>>(initialQuantities);
  const [includeResearch, setIncludeResearch] = useState(initialIncludeResearch);
  const [customTopics, setCustomTopics] = useState<string[]>(initialTopics);  // NEW: topic override state
  const [targetPlatform, setTargetPlatform] = useState<string>(initialTargetPlatform);  // NEW: target platform state
  const [dependencies, setDependencies] = useState<Map<number, TemplateDependencies>>(new Map());
  const [completedTools, setCompletedTools] = useState<Set<string>>(new Set());
  const [loadingDeps, setLoadingDeps] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [storyCounts, setStoryCounts] = useState<Record<string, number>>({});
  const [validationResults, setValidationResults] = useState<Map<number, {
    blocked: boolean;
    warning: string | null;
    error: string | null;
    missingFields: string[];
    missingTools: string[];
  }>>(new Map());

  // Fetch completed research tools — union of current project + client history
  useEffect(() => {
    if (!projectId) return;

    const fetchCompletedResearch = async () => {
      try {
        const emptyList: ResearchResultListResponse = { results: [], total: 0 };
        const [projectRes, clientRes] = await Promise.all([
          researchApi.getProjectResearchResults(projectId),
          clientId
            ? researchApi.getClientResearchResults(clientId)
            : Promise.resolve(emptyList),
        ]);
        const toolNames = new Set([
          ...projectRes.results.filter((r) => r.status === 'completed').map((r) => r.toolName),
          ...clientRes.results.filter((r) => r.status === 'completed').map((r) => r.toolName),
        ]);
        setCompletedTools(toolNames);
      } catch (error) {
        console.error('Failed to fetch research results:', error);
      }
    };

    fetchCompletedResearch();
  }, [projectId, clientId]);

  // Fetch dependencies for all templates on mount so prerequisites are visible before selection
  useEffect(() => {
    const fetchDependencies = async () => {
      setLoadingDeps(true);
      const newDeps = new Map<number, TemplateDependencies>();

      try {
        await Promise.all(
          TEMPLATES.map(async (template) => {
            try {
              const response = await generatorApi.getTemplateDependencies(template.id);
              newDeps.set(template.id, response.research_dependencies);
            } catch (error) {
              console.error(`Failed to fetch dependencies for template ${template.id}:`, error);
            }
          })
        );

        setDependencies(newDeps);
      } finally {
        setLoadingDeps(false);
      }
    };

    fetchDependencies();
  }, []);
  // Validate templates when quantities change
  useEffect(() => {
    const templatesWithQuantity = Object.keys(quantities)
      .map(Number)
      .filter((id) => quantities[id] > 0);

    if (templatesWithQuantity.length === 0 || !clientId) {
      setValidationResults(new Map());
      return;
    }

    const validateTemplates = async () => {
      setIsValidating(true);
      try {
        const templateQuantities: Record<string, number> = {};
        templatesWithQuantity.forEach((id) => {
          templateQuantities[id.toString()] = quantities[id];
        });

        const validation = await generatorApi.validateTemplates(
          clientId,
          templateQuantities,
          projectId
        );

        const results = new Map();

        // Mark blocked templates
        validation.blocked_templates.forEach((blocked) => {
          const templateId = parseInt(blocked.template_id);
          results.set(templateId, {
            blocked: true,
            warning: null,
            error: blocked.error_message,
            missingFields: blocked.missing_fields,
            missingTools: blocked.missing_tools ?? [],
          });
        });

        // Mark warnings
        validation.warnings.forEach((warning) => {
          const templateId = parseInt(warning.template_id);
          if (!results.has(templateId)) {
            results.set(templateId, {
              blocked: false,
              warning: warning.warning_message,
              error: null,
              missingFields: warning.missing_recommended_fields,
            });
          }
        });

        setValidationResults(results);
        setStoryCounts(validation.story_counts ?? {});
      } catch (error) {
        console.error('Failed to validate templates:', error);
      } finally {
        setIsValidating(false);
      }
    };

    validateTemplates();
  }, [quantities, clientId]);

  // Auto-cap story template quantities when story counts are known
  useEffect(() => {
    if (Object.keys(storyCounts).length === 0) return;
    setQuantities((prev) => {
      let changed = false;
      const updated = { ...prev };
      Object.entries(STORY_TEMPLATE_SLUGS).forEach(([idStr, slug]) => {
        const id = Number(idStr);
        const limit = storyCounts[slug] ?? 0;
        if ((updated[id] ?? 0) > limit) {
          if (limit === 0) {
            delete updated[id];
          } else {
            updated[id] = limit;
          }
          changed = true;
        }
      });
      return changed ? updated : prev;
    });
  }, [storyCounts]);

  // Calculate totals
  const { totalPosts, totalCredits, creditsPerPost } = useMemo(() => {
    const total = Object.values(quantities).reduce((sum, qty) => sum + qty, 0);
    const baseCredits = CREDITS_PER_POST;
    // Research costs handled separately by research tools, not per-post
    const perPost = baseCredits;
    return {
      totalPosts: total,
      creditsPerPost: perPost,
      totalCredits: total * perPost,
    };
  }, [quantities, includeResearch]);

  const updateQuantity = (templateId: number, delta: number) => {
    const slug = STORY_TEMPLATE_SLUGS[templateId];
    const storyLimit = slug !== undefined ? (storyCounts[slug] ?? undefined) : undefined;
    setQuantities((prev) => {
      const current = prev[templateId] || 0;
      let newValue = Math.max(0, current + delta);
      if (storyLimit !== undefined) newValue = Math.min(newValue, storyLimit);

      if (newValue === 0) {
        const { [templateId]: _, ...rest } = prev;
        return rest;
      }
      return { ...prev, [templateId]: newValue };
    });
  };

  const setQuantity = (templateId: number, value: number) => {
    const newValue = Math.max(0, Math.min(100, value));
    setQuantities((prev) => {
      if (newValue === 0) {
        const { [templateId]: _, ...rest } = prev;
        return rest;
      }
      return { ...prev, [templateId]: newValue };
    });
  };

  const clearAll = () => {
    setQuantities({});
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

  // Calculate aggregate research requirements for selected templates
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


  // Check if any templates are blocked
  const hasBlockedTemplates = useMemo(() => {
    return Array.from(validationResults.values()).some((v) => v.blocked);
  }, [validationResults]);

  return (
    <div className="space-y-8">
      {/* Platform Selector */}
      <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6 shadow-sm">
        <PlatformSelector
          selected={targetPlatform}
          onChange={setTargetPlatform}
        />
      </div>

      {/* Template Quantity Selection */}
      <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6 shadow-sm">
        {/* Header */}
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Calculator className="h-5 w-5 text-blue-600" />
          <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">Custom Template Quantities</h3>
        </div>
        <button
          onClick={clearAll}
          className="rounded-md border border-neutral-200 dark:border-neutral-700 px-3 py-1.5 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800"
        >
          Clear All
        </button>
      </div>

      <p className="mb-6 text-sm text-neutral-600 dark:text-neutral-400">
        Specify exact quantities for each template. Cost is 20 credits per post. Research tools are available in the Research step (100-300 credits each).
      </p>

      {/* Pricing Summary Card */}
      <div className="mb-6 rounded-lg border-2 border-blue-200 dark:border-blue-800 bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 p-4">
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="flex items-center gap-3">
            <div className="rounded-full bg-blue-100 dark:bg-blue-900/40 p-2">
              <FileText className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <div className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">{totalPosts}</div>
              <div className="text-xs text-neutral-600 dark:text-neutral-400">Total Posts</div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="rounded-full bg-emerald-100 dark:bg-emerald-900/40 p-2">
              <TrendingUp className="h-5 w-5 text-emerald-600" />
            </div>
            <div>
              <div className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">{creditsPerPost}</div>
              <div className="text-xs text-neutral-600 dark:text-neutral-400">Per Post</div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="rounded-full bg-purple-100 dark:bg-purple-900/40 p-2">
              <Coins className="h-5 w-5 text-purple-600" />
            </div>
            <div>
              <div className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">{totalCredits.toLocaleString()}</div>
              <div className="text-xs text-neutral-600 dark:text-neutral-400">Total Credits</div>
            </div>
          </div>
        </div>

        {/* REMOVED (Bug #43): Deprecated $15/post topic research checkbox */}
        {/* Topic research is now handled by granular research tools in Research step ($300-$600 each) */}

        {/* Topic Override Section */}
        <div className="mt-4 rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20 p-4">
          <div className="flex items-center gap-2 mb-2">
            <AlertCircle className="h-4 w-4 text-amber-600" />
            <label className="text-sm font-medium text-amber-900 dark:text-amber-100">
              Custom Topics (Optional)
            </label>
          </div>
          <p className="text-xs text-amber-700 dark:text-amber-300 mb-3">
            Specify topics to guide content generation. Leave empty to use research results or AI suggestions. Separate with commas.
          </p>
          <textarea
            value={customTopics.join(', ')}
            onChange={(e) => setCustomTopics(
              e.target.value.split(',').map(s => s.trim()).filter(Boolean)
            )}
            placeholder="e.g., customer retention, churn prediction, product analytics"
            className="w-full rounded-md border-amber-300 dark:border-amber-700 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 px-3 py-2 text-sm focus:border-amber-500 dark:focus:border-amber-400 focus:ring-2 focus:ring-amber-500 dark:focus:ring-amber-400"
            rows={2}
          />
          {customTopics.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-2">
              {customTopics.map((topic, i) => (
                <span key={i} className="inline-flex items-center gap-1 rounded-full bg-amber-100 dark:bg-amber-900/40 px-2.5 py-1 text-xs font-medium text-amber-800 dark:text-amber-200">
                  {topic}
                  <X
                    className="h-3 w-3 cursor-pointer hover:text-amber-900 dark:hover:text-amber-100"
                    onClick={() => setCustomTopics(prev => prev.filter((_, idx) => idx !== i))}
                  />
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Research Dependencies Warning */}
      {totalPosts > 0 && !loadingDeps && missingRequired.length > 0 && (
        <div className="mb-4 rounded-md bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 px-4 py-3">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h4 className="text-sm font-semibold text-amber-900 dark:text-amber-100 mb-2">
                Missing Required Research
              </h4>
              <p className="text-sm text-amber-800 dark:text-amber-200 mb-3">
                Selected templates require {missingRequired.length} research{' '}
                {missingRequired.length === 1 ? 'tool' : 'tools'} that have not been run yet. Running these tools will
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
      {totalPosts > 0 && !loadingDeps && missingRecommended.length > 0 && missingRequired.length === 0 && (
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
      {totalPosts > 0 &&
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
      {/* Legend / Key */}
      <div className="mb-3 rounded-md border border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800/50 px-4 py-3">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400">Legend</p>
        <div className="flex flex-wrap gap-x-5 gap-y-2 text-xs text-neutral-600 dark:text-neutral-400">
          <div className="flex items-center gap-2">
            <span className="rounded-full bg-emerald-100 dark:bg-emerald-900/40 px-2 py-0.5 text-xs font-medium text-emerald-700 dark:text-emerald-300">⚡ Fast</span>
            <span className="rounded-full bg-amber-100 dark:bg-amber-900/40 px-2 py-0.5 text-xs font-medium text-amber-700 dark:text-amber-300">⏱️ Medium</span>
            <span className="rounded-full bg-rose-100 dark:bg-rose-900/40 px-2 py-0.5 text-xs font-medium text-rose-700 dark:text-rose-300">🕐 Slow</span>
            <span className="text-neutral-400">— AI generation time</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="rounded-md bg-amber-100 dark:bg-amber-900/40 px-2 py-0.5 text-xs font-medium text-amber-800 dark:text-amber-200">Field</span>
            <span className="text-neutral-400">— required client profile field</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="rounded-md bg-violet-100 dark:bg-violet-900/40 px-2 py-0.5 text-xs font-medium text-violet-800 dark:text-violet-200">Tool</span>
            <span className="text-neutral-400">— required research tool</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="rounded-md bg-emerald-100 dark:bg-emerald-900/40 px-2 py-0.5 text-xs font-medium text-emerald-800 dark:text-emerald-200">3 stories</span>
            <span className="text-neutral-400">— available mined stories (green = ok, red = none)</span>
          </div>
        </div>
      </div>

      {/* Template Grid */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {TEMPLATES.map((template) => {
          const quantity = quantities[template.id] || 0;
          const hasQuantity = quantity > 0;
          const templateDeps = dependencies.get(template.id);
          const validation = validationResults.get(template.id);
          const hasRequiredDeps = templateDeps?.required && templateDeps.required.length > 0;
          const hasRecommendedDeps = templateDeps?.recommended && templateDeps.recommended.length > 0;
          const storySlug = STORY_TEMPLATE_SLUGS[template.id];
          const storyCount = storySlug !== undefined ? storyCounts[storySlug] : undefined;
          const noStories = storyCount === 0;
          const storyLimitReached = storyCount !== undefined && quantity >= storyCount;

          return (
            <div
              key={template.id}
              className={`group relative rounded-lg border-2 p-4 transition-all ${
                hasQuantity
                  ? 'border-blue-600 bg-blue-50 dark:bg-blue-900/20 shadow-md'
                  : 'border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 hover:border-neutral-300 dark:hover:border-neutral-600'
              }`}
            >
              {/* Template Header */}
              <div className="mb-3">
                <div className="mb-1 flex items-center justify-between">
                  <h4 className={`text-sm font-semibold ${hasQuantity ? 'text-blue-900 dark:text-blue-100' : 'text-neutral-900 dark:text-neutral-100'}`}>
                    #{template.id}. {template.name}
                  </h4>
                  <div className="flex items-center gap-1">
                    {hasQuantity && (
                      <span className="rounded-full bg-blue-600 px-2 py-0.5 text-xs font-bold text-white">
                        {quantity}
                      </span>
                    )}
                    {(() => {
                      const slug = STORY_TEMPLATE_SLUGS[template.id];
                      if (!slug) return null;
                      const count = storyCounts[slug];
                      if (count === undefined) return null;
                      return (
                        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${count > 0 ? 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300' : 'bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300'}`}>
                          {count} {count === 1 ? 'story' : 'stories'}
                        </span>
                      );
                    })()}
                  </div>
                </div>
                <p className="text-xs text-neutral-600 dark:text-neutral-400">{template.description}</p>
              </div>

              {/* Static Prerequisites Chip — always visible before selection */}
              {(() => {
                const sp = TEMPLATE_STATIC_PREREQS[template.id];
                if (!sp) return null;
                const fieldLabels = sp.fields.map((f) => FIELD_LABELS[f] ?? f);
                const toolLabels = sp.tools.map((t) => TOOL_LABELS[t] ?? t);
                const allLabels = [...fieldLabels, ...toolLabels];
                if (allLabels.length === 0) return null;
                return (
                  <div className="mb-2 flex flex-wrap gap-1">
                    {allLabels.map((label) => (
                      <span
                        key={label}
                        className="inline-flex items-center rounded-full bg-neutral-100 dark:bg-neutral-800 border border-neutral-300 dark:border-neutral-600 px-2 py-0.5 text-xs text-neutral-600 dark:text-neutral-400"
                      >
                        {label}
                      </span>
                    ))}
                  </div>
                );
              })()}

              {/* Validation Badges */}
              {validation?.blocked && (
                <div className="mb-3 p-2 bg-red-100 dark:bg-red-900/30 border border-red-300 dark:border-red-700 rounded flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <p className="text-xs font-medium text-red-800 dark:text-red-200">
                      Cannot Generate: Required Data Missing
                    </p>
                    <p className="text-xs text-red-700 dark:text-red-300 mt-0.5">
                      {validation.error}
                    </p>
                    {validation.missingFields.length > 0 && (
                      <p className="text-xs text-red-600 dark:text-red-400 mt-1">
                        Missing fields: {validation.missingFields.join(', ')}
                      </p>
                    )}
                    {(validation.missingTools?.length ?? 0) > 0 && (
                      <p className="text-xs text-red-600 dark:text-red-400 mt-1">
                        Run first: {(validation.missingTools ?? []).map((t) => TOOL_LABELS[t] ?? t).join(', ')}
                      </p>
                    )}
                    {validation.missingFields.length > 0 && onEditClient && (
                      <button
                        type="button"
                        onClick={onEditClient}
                        className="mt-1.5 text-xs font-medium text-red-700 dark:text-red-300 underline hover:text-red-900 dark:hover:text-red-100"
                      >
                        Edit Client Profile →
                      </button>
                    )}
                    {(validation.missingTools?.length ?? 0) > 0 && onNavigateToResearch && (
                      <button
                        type="button"
                        onClick={onNavigateToResearch}
                        className="mt-1.5 ml-2 text-xs font-medium text-red-700 dark:text-red-300 underline hover:text-red-900 dark:hover:text-red-100"
                      >
                        Go to Research →
                      </button>
                    )}
                  </div>
                </div>
              )}

              {validation?.warning && !validation.blocked && (
                <div className="mb-3 p-2 bg-yellow-100 dark:bg-yellow-900/30 border border-yellow-300 dark:border-yellow-700 rounded flex items-start gap-2">
                  <HelpCircle className="w-4 h-4 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <p className="text-xs text-yellow-800 dark:text-yellow-200">
                      {validation.warning}
                    </p>
                  </div>
                </div>
              )}

              {/* Template Details */}
              <div className="mb-3 space-y-1">
                <div className="text-xs text-neutral-700 dark:text-neutral-300">
                  <strong>Best for:</strong> {template.bestFor}
                </div>
                <div>
                  <span className={`inline-block rounded-md px-2 py-1 text-xs font-medium ${getDifficultyColor(template.difficulty)}`}>
                    {getDifficultyLabel(template.difficulty)}
                  </span>
                </div>
              </div>

              {/* Research Dependencies for this template — always visible so users see requirements before selecting */}
              {templateDeps && (hasRequiredDeps || hasRecommendedDeps) && (
                <div className="mb-3 pt-2 border-t border-neutral-200 dark:border-neutral-700 space-y-1">
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

              {/* Story count warning */}
              {noStories && (
                <div className="mb-2 rounded p-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 flex items-center gap-2">
                  <AlertCircle className="h-3.5 w-3.5 text-red-600 dark:text-red-400 flex-shrink-0" />
                  <p className="text-xs text-red-700 dark:text-red-300">
                    No stories available — run Story Mining first.
                  </p>
                </div>
              )}

              {/* Quantity Controls */}
              <div className="flex items-center gap-2">
                <button
                  onClick={() => updateQuantity(template.id, -1)}
                  disabled={quantity === 0}
                  className="flex h-8 w-8 items-center justify-center rounded-md border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-40"
                  aria-label="Decrease quantity"
                >
                  <Minus className="h-4 w-4" />
                </button>

                <input
                  type="number"
                  min="0"
                  max={storyCount !== undefined ? storyCount : 100}
                  value={quantity}
                  disabled={noStories}
                  onChange={(e) => setQuantity(template.id, parseInt(e.target.value) || 0)}
                  className="h-8 w-16 rounded-md border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 text-center text-sm font-semibold text-neutral-900 dark:text-neutral-100 focus:border-blue-500 dark:focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 disabled:opacity-40 disabled:cursor-not-allowed"
                />

                <button
                  onClick={() => updateQuantity(template.id, 1)}
                  disabled={noStories || storyLimitReached}
                  className="flex h-8 w-8 items-center justify-center rounded-md border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-40"
                  aria-label="Increase quantity"
                >
                  <Plus className="h-4 w-4" />
                </button>

                {hasQuantity && (
                  <div className="ml-auto text-xs font-semibold text-neutral-600 dark:text-neutral-400">
                    {(quantity * creditsPerPost).toLocaleString()} credits
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Footer */}
      <div className="mt-6 flex items-center justify-between border-t border-neutral-200 dark:border-neutral-700 pt-4">
        <div className="text-sm text-neutral-600 dark:text-neutral-400">
          {totalPosts === 0 && 'Add at least one post to continue'}
          {totalPosts > 0 && totalPosts < 10 && 'Consider adding more posts for better content variety'}
          {totalPosts >= 10 && totalPosts <= 50 && '✓ Good quantity selection'}
          {totalPosts > 50 && 'Large order - generation may take longer'}
        </div>
        {/* Blocked Templates Summary */}
        {hasBlockedTemplates && (
          <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <h4 className="font-semibold text-red-900 dark:text-red-100 mb-2">
                  Cannot Start Generation
                </h4>
                <p className="text-sm text-red-800 dark:text-red-200 mb-3">
                  Some selected templates require additional client data before generation can proceed.
                  Please update the client profile or remove these templates:
                </p>
                <ul className="list-disc list-inside space-y-1">
                  {Array.from(validationResults.entries())
                    .filter(([_, v]) => v.blocked)
                    .map(([templateId, validation]) => {
                      const template = TEMPLATES.find((t) => t.id === templateId);
                      return (
                        <li key={templateId} className="text-sm text-red-700 dark:text-red-300">
                          <strong>{template?.name}:</strong> {validation.error}
                        </li>
                      );
                    })}
                </ul>
                {onEditClient && (
                  <button
                    type="button"
                    onClick={onEditClient}
                    className="mt-3 text-sm font-medium text-red-700 dark:text-red-300 underline hover:text-red-900 dark:hover:text-red-100"
                  >
                    Edit Client Profile →
                  </button>
                )}
              </div>
            </div>
          </div>
        )}

        <button
          onClick={() => onContinue?.(quantities, includeResearch, totalCredits, customTopics, targetPlatform)}
          disabled={totalPosts === 0 || hasBlockedTemplates || isValidating}
          className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 dark:hover:bg-blue-800 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Continue to Generation
          <span className="text-xs opacity-75">({totalCredits.toLocaleString()} credits)</span>
        </button>
      </div>
      </div>
    </div>
  );
});
