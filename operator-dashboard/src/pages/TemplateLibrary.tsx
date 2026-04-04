import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  FileText,
  Search,
  Filter,
  Clock,
  BookOpen,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Info,
  X,
  ChevronRight,
} from 'lucide-react';
import apiClient from '@/api/client';
import { clientsApi } from '@/api';
import { researchApi } from '@/api';

// Shape returned by GET /api/generator/templates
interface Template {
  id: number;
  name: string;
  description: string;
  bestFor: string;
  difficulty: 'fast' | 'medium' | 'slow';
  required: string[];     // P0 — blocks generation
  recommended: string[];  // P1 — recommended
  optional: string[];     // P2 — optional
}

// Templates that require mined stories to generate authentic content
const STORY_REQUIRED_TEMPLATES = new Set([6, 8]);       // personal_story, things_i_got_wrong
const STORY_RECOMMENDED_TEMPLATES = new Set([11, 15]);  // what_i_learned, milestone

// Human-readable labels for research tool IDs
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

const DIFFICULTY_LABELS: Record<string, string> = {
  fast: 'Fast',
  medium: 'Medium',
  slow: 'Slow',
};

const DIFFICULTY_STYLES: Record<string, string> = {
  fast: 'bg-emerald-100 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-700',
  medium: 'bg-amber-100 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-700',
  slow: 'bg-orange-100 dark:bg-orange-900/20 text-orange-700 dark:text-orange-300 border-orange-200 dark:border-orange-700',
};

export default function TemplateLibrary() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [difficultyFilter, setDifficultyFilter] = useState<string>('');
  const [storyFilter, setStoryFilter] = useState<string>('');
  const [prereqFilter, setPrereqFilter] = useState<string>('');
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null);
  const [clientPrereqMode, setClientPrereqMode] = useState(false);
  const [selectedClientId, setSelectedClientId] = useState<string | null>(null);

  // Real API data
  const { data: templates = [], isLoading } = useQuery<Template[]>({
    queryKey: ['templates'],
    queryFn: async () => {
      const { data } = await apiClient.get('/api/generator/templates');
      return data;
    },
  });

  const { data: clients = [] } = useQuery({
    queryKey: ['clients'],
    queryFn: () => clientsApi.list(),
  });

  // Client's completed research tools
  const { data: clientPrerequisites } = useQuery({
    queryKey: ['client-prerequisites', selectedClientId],
    queryFn: () => researchApi.getClientPrerequisites(selectedClientId as string),
    enabled: clientPrereqMode && selectedClientId !== null,
  });
  const completedTools: string[] = clientPrerequisites?.completedTools ?? [];

  // Client's available stories
  const { data: storyData } = useQuery({
    queryKey: ['client-stories', selectedClientId],
    queryFn: async () => {
      const { data } = await apiClient.get(
        `/api/stories/client/${selectedClientId}?limit=100`
      );
      return data as { stories: unknown[]; total: number };
    },
    enabled: clientPrereqMode && selectedClientId !== null,
  });
  const availableStories = storyData?.total ?? null;

  // Filtered list
  const filteredTemplates = templates.filter(t => {
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      if (!t.name.toLowerCase().includes(q) && !t.description.toLowerCase().includes(q)) {
        return false;
      }
    }
    if (difficultyFilter && t.difficulty !== difficultyFilter) return false;
    if (storyFilter === 'required' && !STORY_REQUIRED_TEMPLATES.has(t.id)) return false;
    if (storyFilter === 'none' && STORY_REQUIRED_TEMPLATES.has(t.id)) return false;
    if (prereqFilter === 'none' && (t.required.length > 0 || t.recommended.length > 0)) return false;
    if (prereqFilter === 'has' && t.required.length === 0 && t.recommended.length === 0) return false;
    return true;
  });

  const hasFilters = searchQuery || difficultyFilter || storyFilter || prereqFilter;

  const clearFilters = () => {
    setSearchQuery('');
    setDifficultyFilter('');
    setStoryFilter('');
    setPrereqFilter('');
  };

  const handleUseInWizard = (template: Template) => {
    sessionStorage.setItem(
      'wizard_preselected_template',
      JSON.stringify({ id: String(template.id), name: template.name })
    );
    navigate('/dashboard/wizard?step=templates');
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">
            Template Library
          </h1>
          <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">
            {templates.length} content templates — select one to use in a project
          </p>
        </div>
      </div>

      {/* Client context toggle */}
      <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-4">
        <div className="flex flex-wrap items-center gap-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={clientPrereqMode}
              onChange={e => {
                setClientPrereqMode(e.target.checked);
                if (!e.target.checked) setSelectedClientId(null);
              }}
              className="h-4 w-4 rounded border-neutral-300 text-primary-600 focus:ring-primary-500"
            />
            <span className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
              Show client prerequisite status
            </span>
          </label>

          {clientPrereqMode && (
            <select
              value={selectedClientId ?? ''}
              onChange={e => setSelectedClientId(e.target.value || null)}
              className="rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 px-3 py-1.5 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            >
              <option value="">Select a client…</option>
              {(clients as any[]).map((c: any) => (
                <option key={c.id} value={c.id}>
                  {c.companyName ?? c.name}
                </option>
              ))}
            </select>
          )}

          {clientPrereqMode && selectedClientId && (
            <span className="text-sm text-neutral-500 dark:text-neutral-400">
              <span className="font-medium text-neutral-900 dark:text-neutral-100">
                {completedTools.length}
              </span>{' '}
              tools completed ·{' '}
              <span className="font-medium text-neutral-900 dark:text-neutral-100">
                {availableStories ?? '…'}
              </span>{' '}
              stories available
            </span>
          )}
        </div>
      </div>

      {/* Prerequisites legend */}
      <div className="rounded-lg border border-primary-200 dark:border-primary-800 bg-primary-50 dark:bg-primary-900/20 p-4">
        <div className="flex items-start gap-3">
          <Info className="h-4 w-4 text-primary-600 dark:text-primary-400 flex-shrink-0 mt-0.5" />
          <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
            <span className="flex items-center gap-1.5">
              <span className="inline-flex rounded-full bg-rose-100 dark:bg-rose-900/30 px-2 py-0.5 text-xs font-medium text-rose-700 dark:text-rose-400">P0 Required</span>
              <span className="text-primary-800 dark:text-primary-200">Blocks generation if missing</span>
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-flex rounded-full bg-amber-100 dark:bg-amber-900/30 px-2 py-0.5 text-xs font-medium text-amber-700 dark:text-amber-400">P1 Recommended</span>
              <span className="text-primary-800 dark:text-primary-200">Improves output quality</span>
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-flex rounded-full bg-neutral-100 dark:bg-neutral-800 px-2 py-0.5 text-xs font-medium text-neutral-600 dark:text-neutral-400">P2 Optional</span>
              <span className="text-primary-800 dark:text-primary-200">Adds extra context</span>
            </span>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-4">
        <div className="flex flex-col sm:flex-row gap-3">
          {/* Search */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400" />
            <input
              type="text"
              placeholder="Search templates…"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 pl-10 pr-4 py-2 text-sm placeholder-neutral-400 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
          </div>

          {/* Difficulty */}
          <div className="relative sm:w-44">
            <Filter className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400" />
            <select
              value={difficultyFilter}
              onChange={e => setDifficultyFilter(e.target.value)}
              className="w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 pl-10 pr-4 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 appearance-none"
            >
              <option value="">All difficulties</option>
              <option value="fast">Fast</option>
              <option value="medium">Medium</option>
              <option value="slow">Slow</option>
            </select>
          </div>

          {/* Story filter */}
          <div className="sm:w-44">
            <select
              value={storyFilter}
              onChange={e => setStoryFilter(e.target.value)}
              className="w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 px-4 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 appearance-none"
            >
              <option value="">All story types</option>
              <option value="required">Needs story</option>
              <option value="none">No story needed</option>
            </select>
          </div>

          {/* Prerequisites filter */}
          <div className="sm:w-44">
            <select
              value={prereqFilter}
              onChange={e => setPrereqFilter(e.target.value)}
              className="w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 px-4 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 appearance-none"
            >
              <option value="">All prerequisites</option>
              <option value="none">No prerequisites</option>
              <option value="has">Has prerequisites</option>
            </select>
          </div>

          {hasFilters && (
            <button
              onClick={clearFilters}
              className="text-sm text-primary-600 dark:text-primary-400 hover:text-primary-700 font-medium whitespace-nowrap self-center"
            >
              Clear
            </button>
          )}
        </div>

        {hasFilters && (
          <p className="mt-3 text-sm text-neutral-500 dark:text-neutral-400">
            Showing{' '}
            <strong className="text-neutral-900 dark:text-neutral-100">
              {filteredTemplates.length}
            </strong>{' '}
            of {templates.length} templates
          </p>
        )}
      </div>

      {/* Template grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {filteredTemplates.map(template => (
          <TemplateCard
            key={template.id}
            template={template}
            completedTools={completedTools}
            availableStories={availableStories}
            clientSelected={clientPrereqMode && selectedClientId !== null}
            onClick={() => setSelectedTemplate(template)}
          />
        ))}
      </div>

      {/* Empty state */}
      {filteredTemplates.length === 0 && (
        <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-12 text-center">
          <FileText className="h-12 w-12 text-neutral-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-2">
            No templates match your filters
          </h3>
          <button
            onClick={clearFilters}
            className="mt-4 inline-flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
          >
            Clear filters
          </button>
        </div>
      )}

      {/* Detail side panel */}
      {selectedTemplate && (
        <>
          <div
            className="fixed inset-0 z-40 bg-neutral-900/40 dark:bg-neutral-950/60"
            onClick={() => setSelectedTemplate(null)}
          />
          <div className="fixed inset-y-0 right-0 z-50 w-full max-w-lg bg-white dark:bg-neutral-900 border-l border-neutral-200 dark:border-neutral-700 shadow-xl overflow-y-auto">
            <div className="p-6 space-y-6">
              {/* Panel header */}
              <div className="flex items-start justify-between">
                <div className="flex-1 pr-4">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-medium text-neutral-500 dark:text-neutral-400">
                      Template {selectedTemplate.id}
                    </span>
                    <span
                      className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs font-medium ${DIFFICULTY_STYLES[selectedTemplate.difficulty]}`}
                    >
                      <Clock className="h-3 w-3" />
                      {DIFFICULTY_LABELS[selectedTemplate.difficulty]}
                    </span>
                  </div>
                  <h2 className="text-xl font-bold text-neutral-900 dark:text-neutral-100">
                    {selectedTemplate.name}
                  </h2>
                </div>
                <button
                  onClick={() => setSelectedTemplate(null)}
                  className="rounded-lg p-2 text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              {/* Description / structure */}
              {selectedTemplate.description && (
                <div>
                  <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100 mb-2">
                    Structure
                  </h3>
                  <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800 p-3">
                    <p className="text-sm text-neutral-700 dark:text-neutral-300 font-mono whitespace-pre-wrap">
                      {selectedTemplate.description}
                    </p>
                  </div>
                </div>
              )}

              {/* Best for */}
              {selectedTemplate.bestFor && (
                <div>
                  <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100 mb-2">
                    Best for
                  </h3>
                  <p className="text-sm text-neutral-600 dark:text-neutral-400">
                    {selectedTemplate.bestFor}
                  </p>
                </div>
              )}

              {/* Story requirement */}
              <div>
                <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100 mb-2">
                  Story requirement
                </h3>
                {STORY_REQUIRED_TEMPLATES.has(selectedTemplate.id) ? (
                  <div className="flex items-start gap-2 rounded-lg border border-rose-200 dark:border-rose-800 bg-rose-50 dark:bg-rose-900/20 p-3">
                    <AlertTriangle className="h-4 w-4 text-rose-600 dark:text-rose-400 flex-shrink-0 mt-0.5" />
                    <div className="text-sm">
                      <p className="font-medium text-rose-800 dark:text-rose-200">
                        Requires a mined story
                      </p>
                      {availableStories !== null && (
                        <p className="text-rose-700 dark:text-rose-300 mt-0.5">
                          {availableStories} stories available for this client
                        </p>
                      )}
                      <p className="text-rose-600 dark:text-rose-400 mt-1">
                        Run Story Mining before generating this template.
                      </p>
                    </div>
                  </div>
                ) : STORY_RECOMMENDED_TEMPLATES.has(selectedTemplate.id) ? (
                  <div className="flex items-start gap-2 rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20 p-3">
                    <Info className="h-4 w-4 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
                    <p className="text-sm text-amber-800 dark:text-amber-200">
                      Better with a mined story — can generate without one.
                    </p>
                  </div>
                ) : (
                  <div className="flex items-center gap-2 text-sm text-neutral-600 dark:text-neutral-400">
                    <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                    No story required
                  </div>
                )}
              </div>

              {/* Prerequisites */}
              {(selectedTemplate.required.length > 0 ||
                selectedTemplate.recommended.length > 0 ||
                selectedTemplate.optional.length > 0) && (
                <div>
                  <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100 mb-3">
                    Research prerequisites
                  </h3>
                  <div className="space-y-2">
                    {selectedTemplate.required.map(tool => {
                      const done = completedTools.includes(tool);
                      return (
                        <PrereqRow
                          key={tool}
                          tool={tool}
                          level="P0"
                          label="Required"
                          levelStyle="bg-rose-100 dark:bg-rose-900/30 text-rose-700 dark:text-rose-400"
                          done={done}
                          clientSelected={clientPrereqMode && selectedClientId !== null}
                        />
                      );
                    })}
                    {selectedTemplate.recommended.map(tool => {
                      const done = completedTools.includes(tool);
                      return (
                        <PrereqRow
                          key={tool}
                          tool={tool}
                          level="P1"
                          label="Recommended"
                          levelStyle="bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400"
                          done={done}
                          clientSelected={clientPrereqMode && selectedClientId !== null}
                        />
                      );
                    })}
                    {selectedTemplate.optional.map(tool => {
                      const done = completedTools.includes(tool);
                      return (
                        <PrereqRow
                          key={tool}
                          tool={tool}
                          level="P2"
                          label="Optional"
                          levelStyle="bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400"
                          done={done}
                          clientSelected={clientPrereqMode && selectedClientId !== null}
                        />
                      );
                    })}
                  </div>
                </div>
              )}

              {selectedTemplate.required.length === 0 &&
                selectedTemplate.recommended.length === 0 &&
                selectedTemplate.optional.length === 0 && (
                  <div>
                    <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100 mb-2">
                      Research prerequisites
                    </h3>
                    <div className="flex items-center gap-2 text-sm text-neutral-600 dark:text-neutral-400">
                      <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                      No research tools required
                    </div>
                  </div>
                )}

              {/* CTA */}
              <div className="flex gap-3 pt-2 border-t border-neutral-200 dark:border-neutral-700">
                <button
                  onClick={() => setSelectedTemplate(null)}
                  className="flex-1 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 px-4 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800"
                >
                  Close
                </button>
                <button
                  onClick={() => handleUseInWizard(selectedTemplate)}
                  className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg bg-primary-600 dark:bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 dark:hover:bg-primary-600"
                >
                  Use in Wizard
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// ── Sub-components ──────────────────────────────────────────────────────────

interface TemplateCardProps {
  template: Template;
  completedTools: string[];
  availableStories: number | null;
  clientSelected: boolean;
  onClick: () => void;
}

function TemplateCard({
  template,
  completedTools,
  availableStories,
  clientSelected,
  onClick,
}: TemplateCardProps) {
  const storyRequired = STORY_REQUIRED_TEMPLATES.has(template.id);
  const storyRecommended = STORY_RECOMMENDED_TEMPLATES.has(template.id);
  const missingRequired = template.required.filter(t => !completedTools.includes(t));
  const hasBlocker = clientSelected && (missingRequired.length > 0 || (storyRequired && availableStories === 0));

  return (
    <button
      onClick={onClick}
      className={`text-left rounded-lg border bg-white dark:bg-neutral-900 p-5 hover:shadow-md transition-all w-full ${
        hasBlocker
          ? 'border-rose-200 dark:border-rose-800'
          : 'border-neutral-200 dark:border-neutral-700 hover:border-primary-300 dark:hover:border-primary-600'
      }`}
    >
      {/* Header row */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1 pr-3">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs text-neutral-400 dark:text-neutral-500 font-medium">
              #{template.id}
            </span>
            <span
              className={`inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-xs font-medium ${DIFFICULTY_STYLES[template.difficulty]}`}
            >
              <Clock className="h-3 w-3" />
              {DIFFICULTY_LABELS[template.difficulty]}
            </span>
          </div>
          <h3 className="text-base font-semibold text-neutral-900 dark:text-neutral-100">
            {template.name}
          </h3>
        </div>
        <BookOpen className="h-5 w-5 text-neutral-300 dark:text-neutral-600 flex-shrink-0 mt-1" />
      </div>

      {/* Tags row */}
      <div className="flex flex-wrap gap-1.5 mb-3">
        {/* P0 prerequisites */}
        {template.required.map(tool => {
          const done = clientSelected && completedTools.includes(tool);
          const missing = clientSelected && !done;
          return (
            <span
              key={tool}
              className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${
                missing
                  ? 'bg-rose-100 dark:bg-rose-900/30 text-rose-700 dark:text-rose-400'
                  : done
                  ? 'bg-emerald-100 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300'
                  : 'bg-rose-50 dark:bg-rose-900/20 text-rose-600 dark:text-rose-500'
              }`}
            >
              {done ? <CheckCircle2 className="h-3 w-3" /> : missing ? <XCircle className="h-3 w-3" /> : null}
              {TOOL_LABELS[tool] ?? tool}
            </span>
          );
        })}

        {/* P1 prerequisites */}
        {template.recommended.map(tool => {
          const done = clientSelected && completedTools.includes(tool);
          return (
            <span
              key={tool}
              className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${
                done
                  ? 'bg-emerald-100 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300'
                  : 'bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-500'
              }`}
            >
              {done && <CheckCircle2 className="h-3 w-3" />}
              {TOOL_LABELS[tool] ?? tool}
            </span>
          );
        })}

        {/* Story badge */}
        {storyRequired && (
          <span
            className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${
              clientSelected && availableStories === 0
                ? 'bg-rose-100 dark:bg-rose-900/30 text-rose-700 dark:text-rose-400'
                : clientSelected && availableStories !== null && availableStories > 0
                ? 'bg-emerald-100 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300'
                : 'bg-purple-100 dark:bg-purple-900/20 text-purple-700 dark:text-purple-300'
            }`}
          >
            <FileText className="h-3 w-3" />
            {clientSelected && availableStories !== null
              ? `Story (${availableStories} available)`
              : 'Needs Story'}
          </span>
        )}

        {storyRecommended && !storyRequired && (
          <span className="inline-flex items-center gap-1 rounded-full bg-purple-50 dark:bg-purple-900/10 px-2 py-0.5 text-xs font-medium text-purple-600 dark:text-purple-400">
            <FileText className="h-3 w-3" />
            Story recommended
          </span>
        )}

        {/* No prerequisites */}
        {template.required.length === 0 &&
          template.recommended.length === 0 &&
          !storyRequired &&
          !storyRecommended && (
            <span className="inline-flex items-center gap-1 rounded-full bg-neutral-100 dark:bg-neutral-800 px-2 py-0.5 text-xs font-medium text-neutral-500 dark:text-neutral-400">
              <CheckCircle2 className="h-3 w-3 text-emerald-500" />
              No prerequisites
            </span>
          )}
      </div>

      {/* Best for */}
      {template.bestFor && (
        <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-2 line-clamp-2">
          {template.bestFor}
        </p>
      )}
    </button>
  );
}

interface PrereqRowProps {
  tool: string;
  level: 'P0' | 'P1' | 'P2';
  label: string;
  levelStyle: string;
  done: boolean;
  clientSelected: boolean;
}

function PrereqRow({ tool, level, label, levelStyle, done, clientSelected }: PrereqRowProps) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800 px-3 py-2">
      <div className="flex items-center gap-2">
        <span className={`inline-flex rounded-full px-1.5 py-0.5 text-xs font-medium ${levelStyle}`}>
          {level}
        </span>
        <span className="text-sm text-neutral-700 dark:text-neutral-300">
          {TOOL_LABELS[tool] ?? tool}
        </span>
        <span className="text-xs text-neutral-400 dark:text-neutral-500">{label}</span>
      </div>
      {clientSelected && (
        done
          ? <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400 flex-shrink-0" />
          : <XCircle className="h-4 w-4 text-rose-500 dark:text-rose-400 flex-shrink-0" />
      )}
    </div>
  );
}
