import { useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Rocket, CheckCircle2, Clock, ArrowRight, Sparkles, Lock } from 'lucide-react';
import { Button } from '@/components/ui';
import {
  FEATURE_REGISTRY,
  getCompleteFeatures,
  getIncompleteFeatures,
  isNewlyCompleted,
  type FeatureCategory,
} from '@/config/featureRegistry';

const CATEGORY_LABELS: Record<FeatureCategory, string> = {
  app_feature: 'Platform Features',
  template: 'Post Templates',
  research_tool: 'Research Tools',
};

export default function PortfolioNotice() {
  const navigate = useNavigate();

  const complete = useMemo(() => getCompleteFeatures(), []);
  const incomplete = useMemo(() => getIncompleteFeatures(), []);
  const hasNewlyCompleted = useMemo(() => complete.some(isNewlyCompleted), [complete]);

  const completeByCategory = useMemo(() => {
    const order: FeatureCategory[] = ['app_feature', 'template', 'research_tool'];
    return order
      .map((cat) => ({ cat, items: complete.filter((f) => f.category === cat) }))
      .filter((g) => g.items.length > 0);
  }, [complete]);

  const incompleteByCategory = useMemo(() => {
    const order: FeatureCategory[] = ['app_feature', 'template', 'research_tool'];
    return order
      .map((cat) => ({ cat, items: incomplete.filter((f) => f.category === cat) }))
      .filter((g) => g.items.length > 0);
  }, [incomplete]);

  // Press any key or click to continue
  useEffect(() => {
    const handle = (e: KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === ' ' || e.key === 'Escape') {
        navigate('/dashboard', { replace: true });
      }
    };
    window.addEventListener('keydown', handle);
    return () => window.removeEventListener('keydown', handle);
  }, [navigate]);

  const handleContinue = () => navigate('/dashboard', { replace: true });

  return (
    <div className="min-h-screen bg-gradient-to-br from-neutral-50 via-blue-50 to-purple-50 dark:from-neutral-950 dark:via-blue-950 dark:to-purple-950 p-4 py-8">
      <div className="max-w-4xl mx-auto space-y-6">

        {/* Header */}
        <div className="text-center space-y-4">
          <div className="mx-auto h-16 w-16 rounded-2xl bg-gradient-to-br from-blue-500 to-purple-600 text-white flex items-center justify-center shadow-lg">
            <Rocket className="h-8 w-8" />
          </div>

          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-blue-100 dark:bg-blue-900/40 border border-blue-300 dark:border-blue-700">
            <Sparkles className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" />
            <span className="text-xs font-semibold text-blue-800 dark:text-blue-300 uppercase tracking-wide">
              Early Access
            </span>
          </div>

          <div>
            <h1 className="text-3xl md:text-4xl font-bold text-neutral-900 dark:text-neutral-100">
              30-Day Content Jumpstart
            </h1>
            <p className="mt-2 text-base text-neutral-600 dark:text-neutral-400 max-w-2xl mx-auto">
              You have early access to this tool and your feedback directly shapes what gets built next.
              Features marked <span className="font-medium text-neutral-700 dark:text-neutral-300">Coming Soon</span> are
              in active development — everything else is live and ready to use.
            </p>
          </div>

          {hasNewlyCompleted && (
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-200 text-sm font-medium">
              <Sparkles className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              New features released this week — see below
            </div>
          )}
        </div>

        {/* Two-column feature status */}
        <div className="grid gap-4 lg:grid-cols-2">

          {/* Working Now */}
          <div className="rounded-xl border border-emerald-200 dark:border-emerald-800 bg-white dark:bg-neutral-900 shadow-sm overflow-hidden">
            <div className="flex items-center gap-2 px-5 py-3 bg-emerald-50 dark:bg-emerald-900/30 border-b border-emerald-200 dark:border-emerald-800">
              <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              <h2 className="text-sm font-semibold text-emerald-900 dark:text-emerald-100">
                Working Now — {complete.length} features
              </h2>
            </div>
            <div className="p-4 space-y-5 max-h-[420px] overflow-y-auto">
              {completeByCategory.map(({ cat, items }) => (
                <div key={cat}>
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-400 dark:text-neutral-500">
                    {CATEGORY_LABELS[cat]}
                  </p>
                  <ul className="space-y-1.5">
                    {items.map((f) => (
                      <li key={f.id} className="flex items-start gap-2">
                        <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 dark:text-emerald-400 flex-shrink-0 mt-0.5" />
                        <div className="flex-1 min-w-0">
                          <span className="text-sm text-neutral-800 dark:text-neutral-200 font-medium">
                            {f.name}
                          </span>
                          {isNewlyCompleted(f) && (
                            <span className="ml-2 inline-flex items-center rounded-full bg-emerald-100 dark:bg-emerald-900/40 px-2 py-0.5 text-xs font-semibold text-emerald-700 dark:text-emerald-300">
                              New
                            </span>
                          )}
                          <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5 leading-snug">
                            {f.description}
                          </p>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>

          {/* Coming Soon */}
          <div className="rounded-xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 shadow-sm overflow-hidden">
            <div className="flex items-center gap-2 px-5 py-3 bg-neutral-50 dark:bg-neutral-800/60 border-b border-neutral-200 dark:border-neutral-700">
              <Clock className="h-4 w-4 text-neutral-500 dark:text-neutral-400" />
              <h2 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300">
                Coming Soon — {incomplete.length} features in development
              </h2>
            </div>
            <div className="p-4 space-y-5 max-h-[420px] overflow-y-auto">
              {incompleteByCategory.map(({ cat, items }) => (
                <div key={cat}>
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-400 dark:text-neutral-500">
                    {CATEGORY_LABELS[cat]}
                  </p>
                  <ul className="space-y-1.5">
                    {items.map((f) => (
                      <li key={f.id} className="flex items-start gap-2">
                        <Lock className="h-3.5 w-3.5 text-neutral-400 dark:text-neutral-500 flex-shrink-0 mt-0.5" />
                        <div className="flex-1 min-w-0">
                          <span className="text-sm text-neutral-500 dark:text-neutral-400 font-medium">
                            {f.name}
                          </span>
                          <p className="text-xs text-neutral-400 dark:text-neutral-500 mt-0.5 leading-snug">
                            {f.description}
                          </p>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Stats bar */}
        <div className="rounded-xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-6 py-4 shadow-sm">
          <div className="flex flex-wrap items-center justify-center gap-8 text-center">
            {[
              { label: 'Features Live', value: complete.filter(f => f.category === 'app_feature').length },
              { label: 'Post Templates', value: `${FEATURE_REGISTRY.filter(f => f.category === 'template' && f.status === 'complete').length} of ${FEATURE_REGISTRY.filter(f => f.category === 'template').length}` },
              { label: 'Research Tools', value: `${FEATURE_REGISTRY.filter(f => f.category === 'research_tool' && f.status === 'complete').length} of ${FEATURE_REGISTRY.filter(f => f.category === 'research_tool').length}` },
              { label: 'In Development', value: incomplete.length },
            ].map(({ label, value }) => (
              <div key={label}>
                <div className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">{value}</div>
                <div className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">{label}</div>
              </div>
            ))}
          </div>
        </div>

        {/* CTA */}
        <div className="text-center space-y-3">
          <Button onClick={handleContinue} variant="primary" className="group px-8">
            Enter Dashboard
            <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" />
          </Button>
          <p className="text-xs text-neutral-400 dark:text-neutral-500">
            Press Enter, Space, or Escape to continue
          </p>
        </div>

      </div>
    </div>
  );
}
