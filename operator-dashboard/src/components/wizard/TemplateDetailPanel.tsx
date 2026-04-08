import { X, CheckCircle2, AlertCircle, Minus, Plus } from 'lucide-react';
import type { Client } from '@/types/domain';

export interface TemplatePrereqs {
  requiredFields: string[];
  recommendedFields: string[];
  requiredTools: string[];
  recommendedTools: string[];
}

interface Template {
  id: number;
  name: string;
  description: string;
  bestFor: string;
  difficulty: 'fast' | 'medium' | 'slow';
}

interface ValidationResult {
  blocked: boolean;
  warning: string | null;
  error: string | null;
}

interface Props {
  template: Template;
  prereqs: TemplatePrereqs;
  clientData: Client | undefined;
  completedTools: Set<string>;
  storyCounts: Record<string, number>;
  storySlug: string | undefined;
  quantity: number;
  onQuantityChange: (delta: number) => void;
  onClose: () => void;
  onEditClient: (() => void) | undefined;
  onNavigateToResearch: (() => void) | undefined;
  validationResult: ValidationResult | undefined;
}

interface FieldDisplay {
  label: string;
  getValue: (client: Client) => string | string[] | null | undefined;
}

const CLIENT_FIELD_DISPLAY: Record<string, FieldDisplay> = {
  business_description: {
    label: 'Business Description',
    getValue: (c) => c.businessDescription,
  },
  ideal_customer: {
    label: 'Ideal Customer',
    getValue: (c) => c.idealCustomer,
  },
  customer_pain_points: {
    label: 'Customer Pain Points',
    getValue: (c) => c.customerPainPoints,
  },
  industry: {
    label: 'Industry',
    getValue: (c) => c.industry,
  },
  main_problem_solved: {
    label: 'Main Problem Solved',
    getValue: (c) => c.mainProblemSolved,
  },
  customer_questions: {
    label: 'Customer Questions',
    getValue: (c) => c.customerQuestions,
  },
};

const TOOL_LABELS: Record<string, string> = {
  audience_research: 'Audience Research',
  seo_keyword_research: 'SEO Keywords',
  competitive_analysis: 'Competitive Analysis',
  determine_competitors: 'Determine Competitors',
  market_trends_research: 'Market Trends',
  story_mining: 'Story Mining',
  brand_archetype: 'Brand Archetype',
  icp_workshop: 'ICP Workshop',
  content_gap_analysis: 'Content Gap',
  voice_analysis: 'Voice Analysis',
  platform_strategy: 'Platform Strategy',
  content_calendar_strategy: 'Content Calendar',
  content_audit: 'Content Audit',
};

function isFieldSatisfied(value: string | string[] | null | undefined): boolean {
  if (value == null) return false;
  if (Array.isArray(value)) return value.length > 0;
  return value.trim().length > 0;
}

function getFieldPreview(value: string | string[] | null | undefined): string {
  if (value == null) return '';
  if (Array.isArray(value)) {
    const preview = value.slice(0, 2).join(', ');
    return value.length > 2 ? `${preview}, +${value.length - 2} more` : preview;
  }
  return value.length > 90 ? `${value.slice(0, 90)}…` : value;
}

function getDifficultyLabel(difficulty: Template['difficulty']): string {
  switch (difficulty) {
    case 'fast': return '⚡ Fast (5 min)';
    case 'medium': return '⏱️ Medium (7–8 min)';
    case 'slow': return '🕐 Slow (10 min)';
  }
}

function getDifficultyClasses(difficulty: Template['difficulty']): string {
  switch (difficulty) {
    case 'fast': return 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300';
    case 'medium': return 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300';
    case 'slow': return 'bg-rose-100 dark:bg-rose-900/40 text-rose-700 dark:text-rose-300';
  }
}

// ── Field row ────────────────────────────────────────────────────────────────

function FieldRow({
  fieldKey,
  required,
  clientData,
  onEditClient,
}: {
  fieldKey: string;
  required: boolean;
  clientData: Client | undefined;
  onEditClient: (() => void) | undefined;
}) {
  const display = CLIENT_FIELD_DISPLAY[fieldKey];
  if (!display) return null;

  const raw = clientData ? display.getValue(clientData) : undefined;
  const satisfied = isFieldSatisfied(raw);
  const preview = getFieldPreview(raw);

  return (
    <div className="flex items-start gap-3 py-2.5 border-b border-neutral-100 dark:border-neutral-800 last:border-0">
      <div className="mt-0.5 flex-shrink-0">
        {!clientData ? (
          <div className="h-4 w-4 rounded-full border-2 border-neutral-300 dark:border-neutral-600" />
        ) : satisfied ? (
          <CheckCircle2 className="h-4 w-4 text-emerald-500" />
        ) : required ? (
          <AlertCircle className="h-4 w-4 text-red-500" />
        ) : (
          <AlertCircle className="h-4 w-4 text-amber-400" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
            {display.label}
          </span>
          {required && !satisfied && (
            <span className="text-xs font-semibold text-red-500 uppercase tracking-wide">required</span>
          )}
        </div>
        {!clientData ? (
          <p className="text-xs italic text-neutral-400 mt-0.5">No client selected</p>
        ) : satisfied ? (
          <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5 break-words">{preview}</p>
        ) : (
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-xs italic text-neutral-400">Not set</span>
            {onEditClient && (
              <button
                type="button"
                onClick={onEditClient}
                className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
              >
                Edit Profile →
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Tool row ─────────────────────────────────────────────────────────────────

function ToolRow({
  toolName,
  completedTools,
  onNavigateToResearch,
}: {
  toolName: string;
  completedTools: Set<string>;
  onNavigateToResearch: (() => void) | undefined;
}) {
  const label = TOOL_LABELS[toolName] ?? toolName;
  const done = completedTools.has(toolName);

  return (
    <div className="flex items-center gap-3 py-2.5 border-b border-neutral-100 dark:border-neutral-800 last:border-0">
      <div className="flex-shrink-0">
        {done ? (
          <CheckCircle2 className="h-4 w-4 text-emerald-500" />
        ) : (
          <AlertCircle className="h-4 w-4 text-amber-400" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <span className="text-sm text-neutral-900 dark:text-neutral-100">{label}</span>
        {!done && (
          <span className="ml-2 text-xs text-amber-500 dark:text-amber-400">Not yet run</span>
        )}
      </div>
      {!done && onNavigateToResearch && (
        <button
          type="button"
          onClick={onNavigateToResearch}
          className="flex-shrink-0 text-xs text-blue-600 dark:text-blue-400 hover:underline"
        >
          Go to Research →
        </button>
      )}
    </div>
  );
}

// ── Main panel ────────────────────────────────────────────────────────────────

export function TemplateDetailPanel({
  template,
  prereqs,
  clientData,
  completedTools,
  storyCounts,
  storySlug,
  quantity,
  onQuantityChange,
  onClose,
  onEditClient,
  onNavigateToResearch,
  validationResult,
}: Props) {
  const storyCount = storySlug !== undefined ? (storyCounts[storySlug] ?? undefined) : undefined;
  const isStoryTemplate = storySlug !== undefined;
  const noStories = storyCount === 0;

  const hasRequiredFields = prereqs.requiredFields.length > 0;
  const hasRecommendedFields = prereqs.recommendedFields.length > 0;
  const hasRequiredTools = prereqs.requiredTools.length > 0;
  const hasRecommendedTools = prereqs.recommendedTools.length > 0;

  return (
    <div className="flex flex-col h-full bg-white dark:bg-neutral-900 overflow-y-auto">

      {/* Header */}
      <div className="sticky top-0 z-10 bg-white dark:bg-neutral-900 border-b border-neutral-200 dark:border-neutral-700 px-5 py-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-neutral-400 dark:text-neutral-500 uppercase tracking-wide mb-1">
              Template #{template.id}
            </p>
            <h3 className="text-base font-semibold text-neutral-900 dark:text-neutral-100 leading-snug">
              {template.name}
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex-shrink-0 rounded-md p-1.5 text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-800 hover:text-neutral-700 dark:hover:text-neutral-300"
            aria-label="Close panel"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Difficulty + best for */}
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <span className={`inline-block rounded-md px-2 py-0.5 text-xs font-medium ${getDifficultyClasses(template.difficulty)}`}>
            {getDifficultyLabel(template.difficulty)}
          </span>
        </div>
        <p className="mt-2 text-sm text-neutral-600 dark:text-neutral-400">{template.description}</p>
        <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-500">
          <span className="font-medium">Best for:</span> {template.bestFor}
        </p>
      </div>

      {/* Body */}
      <div className="flex-1 px-5 py-4 space-y-5">

        {/* Validation alert */}
        {validationResult?.blocked && (
          <div className="rounded-lg border border-red-300 dark:border-red-700 bg-red-50 dark:bg-red-900/20 p-3 flex items-start gap-2">
            <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-red-800 dark:text-red-200">{validationResult.error}</p>
          </div>
        )}
        {validationResult?.warning && !validationResult.blocked && (
          <div className="rounded-lg border border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/20 p-3 flex items-start gap-2">
            <AlertCircle className="h-4 w-4 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-amber-800 dark:text-amber-200">{validationResult.warning}</p>
          </div>
        )}

        {/* Required client fields */}
        {hasRequiredFields && (
          <section>
            <h4 className="text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400 mb-1">
              Required Fields
            </h4>
            <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 divide-y divide-neutral-100 dark:divide-neutral-800 overflow-hidden">
              {prereqs.requiredFields.map((f) => (
                <FieldRow
                  key={f}
                  fieldKey={f}
                  required={true}
                  clientData={clientData}
                  onEditClient={onEditClient}
                />
              ))}
            </div>
          </section>
        )}

        {/* Recommended client fields */}
        {hasRecommendedFields && (
          <section>
            <h4 className="text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400 mb-1">
              Recommended Fields
            </h4>
            <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 divide-y divide-neutral-100 dark:divide-neutral-800 overflow-hidden">
              {prereqs.recommendedFields.map((f) => (
                <FieldRow
                  key={f}
                  fieldKey={f}
                  required={false}
                  clientData={clientData}
                  onEditClient={onEditClient}
                />
              ))}
            </div>
          </section>
        )}

        {/* Required research tools */}
        {hasRequiredTools && (
          <section>
            <h4 className="text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400 mb-1">
              Required Research
            </h4>
            <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 divide-y divide-neutral-100 dark:divide-neutral-800 overflow-hidden">
              {prereqs.requiredTools.map((t) => (
                <ToolRow
                  key={t}
                  toolName={t}
                  completedTools={completedTools}
                  onNavigateToResearch={onNavigateToResearch}
                />
              ))}
            </div>
          </section>
        )}

        {/* Recommended research tools */}
        {hasRecommendedTools && (
          <section>
            <h4 className="text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400 mb-1">
              Recommended Research
            </h4>
            <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 divide-y divide-neutral-100 dark:divide-neutral-800 overflow-hidden">
              {prereqs.recommendedTools.map((t) => (
                <ToolRow
                  key={t}
                  toolName={t}
                  completedTools={completedTools}
                  onNavigateToResearch={onNavigateToResearch}
                />
              ))}
            </div>
          </section>
        )}

        {/* Story section */}
        {isStoryTemplate && (
          <section>
            <h4 className="text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400 mb-1">
              Stories
            </h4>
            <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 p-3 flex items-center gap-3">
              {storyCount === undefined ? (
                <span className="text-sm text-neutral-400 italic">Story count unavailable — select a quantity to check</span>
              ) : noStories ? (
                <>
                  <AlertCircle className="h-4 w-4 text-red-500 flex-shrink-0" />
                  <div className="flex-1">
                    <span className="text-sm text-red-700 dark:text-red-300 font-medium">0 stories available</span>
                    <p className="text-xs text-red-600 dark:text-red-400 mt-0.5">Run Story Mining to generate authentic content</p>
                  </div>
                  {onNavigateToResearch && (
                    <button
                      type="button"
                      onClick={onNavigateToResearch}
                      className="flex-shrink-0 text-xs text-blue-600 dark:text-blue-400 hover:underline"
                    >
                      Run Story Mining →
                    </button>
                  )}
                </>
              ) : (
                <>
                  <CheckCircle2 className="h-4 w-4 text-emerald-500 flex-shrink-0" />
                  <span className="text-sm text-emerald-700 dark:text-emerald-300 font-medium">
                    {storyCount} {storyCount === 1 ? 'story' : 'stories'} available
                  </span>
                </>
              )}
            </div>
          </section>
        )}

        {/* No requirements at all */}
        {!hasRequiredFields && !hasRecommendedFields && !hasRequiredTools && !hasRecommendedTools && !isStoryTemplate && (
          <div className="rounded-lg border border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-900/20 p-3 flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-500 flex-shrink-0" />
            <p className="text-sm text-emerald-700 dark:text-emerald-300">No prerequisites — ready to generate</p>
          </div>
        )}
      </div>

      {/* Footer — quantity controls */}
      <div className="sticky bottom-0 bg-white dark:bg-neutral-900 border-t border-neutral-200 dark:border-neutral-700 px-5 py-4">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-neutral-700 dark:text-neutral-300">Quantity</span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => onQuantityChange(-1)}
              disabled={quantity === 0}
              className="flex h-8 w-8 items-center justify-center rounded-md border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700 disabled:cursor-not-allowed disabled:opacity-40"
              aria-label="Decrease quantity"
            >
              <Minus className="h-4 w-4" />
            </button>
            <span className="w-10 text-center text-sm font-semibold text-neutral-900 dark:text-neutral-100 tabular-nums">
              {quantity}
            </span>
            <button
              type="button"
              onClick={() => onQuantityChange(1)}
              disabled={noStories}
              className="flex h-8 w-8 items-center justify-center rounded-md border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700 disabled:cursor-not-allowed disabled:opacity-40"
              aria-label="Increase quantity"
            >
              <Plus className="h-4 w-4" />
            </button>
          </div>
        </div>
        {quantity > 0 && (
          <p className="mt-1 text-xs text-neutral-400 text-right">
            {quantity * 20} credits for this template
          </p>
        )}
      </div>
    </div>
  );
}
