import { useMutation } from '@tanstack/react-query';
import { generatorApi } from '@/api/generator';
import type { PostDraft } from '@/types/domain';
import { AlertTriangle, RotateCw, ShieldCheck } from 'lucide-react';

interface Props {
  posts: PostDraft[];
  projectId: string;
  onRegenerated?: () => void;
}

export function QualityGatePanel({ posts, projectId, onRegenerated }: Props) {
  const flagged = posts.filter((p) => p.status === 'flagged' || (p.flags && p.flags.length > 0));

  const regen = useMutation({
    mutationFn: (postIds: string[]) =>
      generatorApi.regenerate({
        projectId,
        postIds,
        reason: 'quality_gate_flags',
      }),
    onSuccess: () => onRegenerated?.(),
  });

  const hasFlags = flagged.length > 0;

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center gap-2">
        {hasFlags ? (
          <AlertTriangle className="h-5 w-5 text-amber-600" />
        ) : (
          <ShieldCheck className="h-5 w-5 text-emerald-600" />
        )}
        <div>
          <h3 className="text-sm font-semibold text-slate-900">Quality Gate</h3>
          <p className="text-xs text-slate-600">
            Flags for length/readability/CTA/platform. Regenerate flagged posts before export.
          </p>
        </div>
      </div>

      <div className="mt-3 space-y-2">
        {hasFlags ? (
          flagged.map((post) => (
            <div key={post.id} className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
              <div className="font-semibold text-amber-900">Post {post.id}</div>
              <div>{post.flags?.join(', ') || 'Flagged'}</div>
            </div>
          ))
        ) : (
          <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-800">
            No flags detected. Ready for export.
          </div>
        )}
      </div>

      {hasFlags && (
        <div className="mt-3 flex justify-end">
          <button
            disabled={regen.isPending}
            onClick={() => regen.mutate(flagged.map((f) => f.id))}
            className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-50"
          >
            <RotateCw className="h-4 w-4" />
            {regen.isPending ? 'Regenerating...' : 'Regenerate flagged'}
          </button>
        </div>
      )}
      {regen.error && (
        <div className="mt-3 rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">
          {(regen.error as Error).message || 'Regeneration failed'}
        </div>
      )}
    </div>
  );
}
