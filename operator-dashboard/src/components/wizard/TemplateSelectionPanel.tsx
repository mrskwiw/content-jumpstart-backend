import { useState, memo } from 'react';
import { CheckCircle2, Circle, FileText, ArrowRight } from 'lucide-react';

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

interface Props {
  initialSelection?: number[];
  onContinue?: (selectedIds: number[]) => void;
}

// Memoized to prevent re-renders when parent updates (Performance optimization - December 25, 2025)
export const TemplateSelectionPanel = memo(function TemplateSelectionPanel({ initialSelection = [], onContinue }: Props) {
  const [selected, setSelected] = useState<Set<number>>(new Set(initialSelection));

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
        return 'bg-emerald-100 text-emerald-700';
      case 'medium':
        return 'bg-amber-100 text-amber-700';
      case 'slow':
        return 'bg-rose-100 text-rose-700';
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

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText className="h-5 w-5 text-blue-600" />
          <h3 className="text-lg font-semibold text-slate-900">Template Selection</h3>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={selectRecommended}
            className="rounded-md border border-blue-600 bg-blue-50 px-3 py-1.5 text-sm font-medium text-blue-700 hover:bg-blue-100"
          >
            Recommended (7)
          </button>
          <button
            onClick={selectAll}
            className="rounded-md border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Select All
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
        Select templates to use for content generation. Typically 7-10 templates are selected for a 30-post package (2
        posts per template).
      </p>

      <div className="mb-4 rounded-md bg-blue-50 px-4 py-3 text-sm text-blue-800">
        <strong>{selected.size} templates selected</strong>
        {selected.size > 0 && ` → ${selected.size * 2} posts (2 per template)`}
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {TEMPLATES.map((template) => {
          const isSelected = selected.has(template.id);
          return (
            <button
              key={template.id}
              onClick={() => toggleTemplate(template.id)}
              className={`group relative rounded-lg border-2 p-4 text-left transition-all ${
                isSelected
                  ? 'border-blue-600 bg-blue-50 shadow-md'
                  : 'border-slate-200 bg-white hover:border-slate-300 hover:shadow-sm'
              }`}
            >
              <div className="mb-2 flex items-start justify-between">
                <div className="flex-1">
                  <div className="mb-1 flex items-center gap-2">
                    {isSelected ? (
                      <CheckCircle2 className="h-5 w-5 flex-shrink-0 text-blue-600" />
                    ) : (
                      <Circle className="h-5 w-5 flex-shrink-0 text-slate-300 group-hover:text-slate-400" />
                    )}
                    <h4 className={`text-sm font-semibold ${isSelected ? 'text-blue-900' : 'text-slate-900'}`}>
                      #{template.id}. {template.name}
                    </h4>
                  </div>
                  <p className="ml-7 text-xs text-slate-600">{template.description}</p>
                </div>
              </div>

              <div className="ml-7 mt-3 space-y-1">
                <div className="text-xs text-slate-700">
                  <strong>Best for:</strong> {template.bestFor}
                </div>
                <div>
                  <span className={`inline-block rounded-md px-2 py-1 text-xs font-medium ${getDifficultyColor(template.difficulty)}`}>
                    {getDifficultyLabel(template.difficulty)}
                  </span>
                </div>
              </div>
            </button>
          );
        })}
      </div>

      <div className="mt-6 flex items-center justify-between border-t border-slate-200 pt-4">
        <div className="text-sm text-slate-600">
          {selected.size === 0 && 'Select at least one template to continue'}
          {selected.size > 0 && selected.size < 5 && 'Consider selecting 7-10 templates for variety'}
          {selected.size >= 5 && selected.size <= 12 && '✓ Good selection'}
          {selected.size > 12 && 'You have selected many templates - generation may take longer'}
        </div>
        <button
          onClick={() => onContinue?.(Array.from(selected))}
          disabled={selected.size === 0}
          className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Continue to Generation
          <ArrowRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
});
