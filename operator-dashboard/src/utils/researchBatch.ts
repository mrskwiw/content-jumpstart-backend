/**
 * Sequential research-batch runner with per-tool resilience (GAP-RESEARCH-01).
 *
 * The Research Library used to `throw` on the first failed tool, which aborted every
 * remaining tool and discarded the reason behind a generic message. This runner keeps
 * going past a failed tool, records the backend's reason, and reports each status
 * change so the UI can render progress.
 *
 * It deliberately makes no prerequisite decisions of its own. Whether a dependent may
 * run depends on backend state the client can't see reliably (client-scoped history,
 * project-scoped prerequisite data, a status query that may still be loading), so each
 * tool is attempted and the backend's verdict — including a prerequisite rejection,
 * which is refunded — is what gets recorded.
 *
 * Tools run in the order given, which the caller has already sorted so that
 * prerequisites come first.
 */
import { getApiErrorMessage } from '@/utils/apiError';

export type BatchToolStatus = 'running' | 'complete' | 'failed';

export interface BatchToolFailure {
  tool: string;
  error: string;
}

export interface BatchOutcome {
  /** Tools that completed, in run order. */
  succeeded: string[];
  /** Tools that failed, in run order, with the backend's reason. */
  failed: BatchToolFailure[];
}

/**
 * Run `orderedTools` one at a time without letting one failure abort the batch.
 *
 * @param orderedTools - tools to run, prerequisites first
 * @param runTool - executes one tool; a rejection marks it failed
 * @param onUpdate - called on every status change, with the reason for a failure
 * @returns which tools succeeded and which failed, with reasons
 */
export async function runResearchBatch(
  orderedTools: readonly string[],
  runTool: (tool: string) => Promise<unknown>,
  onUpdate: (tool: string, status: BatchToolStatus, error?: string) => void
): Promise<BatchOutcome> {
  const succeeded: string[] = [];
  const failed: BatchToolFailure[] = [];

  for (const tool of orderedTools) {
    onUpdate(tool, 'running');
    try {
      await runTool(tool);
      succeeded.push(tool);
      onUpdate(tool, 'complete');
    } catch (err) {
      const error = getApiErrorMessage(err, 'Tool failed to run.');
      failed.push({ tool, error });
      onUpdate(tool, 'failed', error);
    }
  }

  return { succeeded, failed };
}
