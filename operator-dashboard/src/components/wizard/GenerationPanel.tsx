import { useEffect, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { generatorApi } from '@/api/generator';
import { runsApi } from '@/api/runs';
import type { GenerateAllInput, Run } from '@/types/domain';
import { Play, Loader2, CheckCircle2, XCircle } from 'lucide-react';

interface Props {
  projectId: string;
  clientId: string;
  templateQuantities?: Record<number, number>;
  onStarted?: (run: Run) => void;
}

export function GenerationPanel({ projectId, clientId, templateQuantities, onStarted }: Props) {
  const [runId, setRunId] = useState<string | null>(null);
  const [pollingEnabled, setPollingEnabled] = useState(false);

  const generate = useMutation({
    mutationFn: (input: GenerateAllInput) => generatorApi.generateAll(input),
    onSuccess: (run) => {
      console.log('Generation queued successfully:', run);
      setRunId(run.id);
      setPollingEnabled(true);
    },
    onError: (error) => {
      console.error('Failed to queue generation:', error);
      alert(`Failed to start generation: ${error instanceof Error ? error.message : 'Unknown error'}`);
    },
  });

  // Poll for run status
  const { data: runStatus } = useQuery({
    queryKey: ['run-status', runId],
    queryFn: () => (runId ? runsApi.get(runId) : null),
    enabled: pollingEnabled && !!runId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      // Poll every 2 seconds while running, stop when succeeded/failed
      return status === 'running' || status === 'pending' ? 2000 : false;
    },
  });

  // Handle status changes
  useEffect(() => {
    if (runStatus?.status === 'succeeded') {
      setPollingEnabled(false);
      console.log('Generation completed successfully');
      onStarted?.(runStatus);
    } else if (runStatus?.status === 'failed') {
      setPollingEnabled(false);
      console.error('Generation failed:', runStatus.errorMessage);
    }
  }, [runStatus, onStarted]);

  const isGenerating = generate.isPending || pollingEnabled;
  const statusMessage = runStatus?.status === 'running'
    ? 'Generating posts...'
    : runStatus?.status === 'pending'
    ? 'Queued...'
    : generate.isPending
    ? 'Starting...'
    : null;

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">Generate All</h3>
          <p className="text-xs text-slate-600">
            {statusMessage || 'Run full batch generation for this project.'}
          </p>
        </div>
        <button
          disabled={isGenerating}
          onClick={() =>
            generate.mutate({
              projectId,
              clientId,
              isBatch: true,
              templateQuantities,
            })
          }
          className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-50"
        >
          {isGenerating ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : runStatus?.status === 'succeeded' ? (
            <CheckCircle2 className="h-4 w-4" />
          ) : runStatus?.status === 'failed' ? (
            <XCircle className="h-4 w-4" />
          ) : (
            <Play className="h-4 w-4" />
          )}
          {isGenerating ? statusMessage : runStatus?.status === 'succeeded' ? 'Complete' : 'Generate All'}
        </button>
      </div>
      {generate.error && (
        <div className="mt-3 rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">
          {(generate.error as Error).message || 'Failed to queue generation'}
        </div>
      )}
      {runStatus?.status === 'failed' && runStatus.errorMessage && (
        <div className="mt-3 rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">
          Generation failed: {runStatus.errorMessage}
        </div>
      )}
      {runStatus?.status === 'succeeded' && (
        <div className="mt-3 rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
          Generation completed successfully!
        </div>
      )}
    </div>
  );
}
