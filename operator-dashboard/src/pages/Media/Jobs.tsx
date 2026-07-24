import { useMemo } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { toast } from 'sonner';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge, BadgeProps } from '@/components/ui/Badge';
import { mediaApi, MediaJob } from '@/api/media';
import { distributionApi } from '@/api/distribution';

const STATUS: Record<string, BadgeProps['variant']> = {
  queued: 'secondary',
  processing: 'warning',
  awaiting_dependency: 'default',
  done: 'success',
  failed: 'danger',
  canceled: 'default',
};
const ACTIVE = new Set(['queued', 'processing', 'awaiting_dependency']);
const usd = (c: number) => `$${(c / 100).toFixed(2)}`;

export default function MediaJobs() {
  const qc = useQueryClient();
  const [params] = useSearchParams();
  const runFilter = params.get('run') || undefined;

  const jobs = useQuery({
    queryKey: ['media', 'jobs', runFilter],
    queryFn: () => mediaApi.jobs(runFilter ? { run_id: runFilter } : undefined),
    // Poll while anything is still rendering.
    refetchInterval: (q) =>
      (q.state.data ?? []).some((j: MediaJob) => ACTIVE.has(j.status)) ? 4000 : false,
  });

  const cancelRun = useMutation({
    mutationFn: (runId: string) => mediaApi.cancelRun(runId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['media', 'jobs'] }),
  });

  const download = useMutation({
    mutationFn: (assetId: string) => mediaApi.assetUrl(assetId),
    onSuccess: (url) => window.open(url, '_blank', 'noopener'),
    onError: () => toast.error('Could not get the asset URL'),
  });

  const sendToQueue = useMutation({
    mutationFn: async (assetId: string) => {
      const url = await mediaApi.assetUrl(assetId);
      return distributionApi.schedule({
        platform: 'stub',
        content: 'Media from generation pipeline',
        scheduled_for: new Date().toISOString(),
        media_url: url,
      });
    },
    onSuccess: () => toast.success('Added to the publishing queue (as a draft to the stub target)'),
    onError: () => toast.error('Could not add to the queue'),
  });

  // Group stages by pipeline run, newest first.
  const runs = useMemo(() => {
    const byRun = new Map<string, MediaJob[]>();
    for (const j of jobs.data ?? []) {
      const key = j.pipeline_run_id ?? j.id;
      (byRun.get(key) ?? byRun.set(key, []).get(key)!).push(j);
    }
    return [...byRun.entries()].map(([runId, stages]) => ({
      runId,
      stages: stages.sort((a, b) => a.stage_index - b.stage_index),
    }));
  }, [jobs.data]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100">Media jobs</h1>
        <p className="text-sm text-slate-600 dark:text-slate-400">
          Live status of your renders. Finished assets can be downloaded or sent to the publishing queue.
        </p>
      </div>

      {jobs.isLoading ? (
        <p className="text-sm text-slate-500">Loading…</p>
      ) : runs.length === 0 ? (
        <p className="text-sm text-slate-500">
          No media jobs yet. Start one on the <span className="font-medium">Generate</span> page.
        </p>
      ) : (
        runs.map(({ runId, stages }) => {
          const pipeline = stages[0]?.pipeline ?? 'pipeline';
          const anyActive = stages.some((s) => ACTIVE.has(s.status));
          const totalCents = stages.reduce((sum, s) => sum + (s.cost_cents ?? 0), 0);
          return (
            <Card key={runId}>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-base">
                  {pipeline}{' '}
                  <span className="text-xs font-normal text-slate-400">
                    · {stages.length} stage{stages.length > 1 ? 's' : ''} · {usd(totalCents)}
                  </span>
                </CardTitle>
                {anyActive && (
                  <Button
                    size="sm"
                    variant="secondary"
                    loading={cancelRun.isPending}
                    onClick={() => cancelRun.mutate(runId)}
                  >
                    Cancel run
                  </Button>
                )}
              </CardHeader>
              <CardContent>
                <ul className="divide-y divide-neutral-200 dark:divide-neutral-800">
                  {stages.map((s) => (
                    <li key={s.id} className="flex items-center justify-between gap-4 py-2.5">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <Badge variant={STATUS[s.status] ?? 'default'}>{s.status}</Badge>
                          <span className="text-sm text-slate-700 dark:text-slate-300">{s.kind}</span>
                          <span className="text-xs text-slate-400">· {s.provider}</span>
                        </div>
                        {s.error_message && (
                          <p className="mt-1 truncate text-xs text-red-600 dark:text-red-400">
                            {s.error_message}
                          </p>
                        )}
                      </div>
                      {s.status === 'done' && s.output_asset_id && (
                        <div className="flex shrink-0 gap-2">
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => download.mutate(s.output_asset_id!)}
                          >
                            Download
                          </Button>
                          <Button size="sm" onClick={() => sendToQueue.mutate(s.output_asset_id!)}>
                            Send to queue
                          </Button>
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          );
        })
      )}
    </div>
  );
}
