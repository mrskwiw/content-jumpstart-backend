import { useMutation } from '@tanstack/react-query';
import { generatorApi } from '@/api/generator';
import type { GenerateAllInput, Run } from '@/types/domain';
import { Play, Loader2 } from 'lucide-react';

interface Props {
  projectId: string;
  clientId: string;
  onStarted?: (run: Run) => void;
}

export function GenerationPanel({ projectId, clientId, onStarted }: Props) {
  const generate = useMutation({
    mutationFn: (input: GenerateAllInput) => generatorApi.generateAll(input),
    onSuccess: (run) => {
      console.log('Generation started successfully:', run);
      onStarted?.(run);
    },
    onError: (error) => {
      console.error('Generation failed:', error);
      alert(`Failed to start generation: ${error instanceof Error ? error.message : 'Unknown error'}`);
    },
  });

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">Generate All</h3>
          <p className="text-xs text-slate-600">Run full batch generation for this project.</p>
        </div>
        <button
          disabled={generate.isPending}
          onClick={() =>
            generate.mutate({
              projectId,
              clientId,
              isBatch: true,
            })
          }
          className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-50"
        >
          {generate.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
          {generate.isPending ? 'Running...' : 'Generate All'}
        </button>
      </div>
      {generate.error && (
        <div className="mt-3 rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">
          {(generate.error as Error).message || 'Generation failed'}
        </div>
      )}
    </div>
  );
}
