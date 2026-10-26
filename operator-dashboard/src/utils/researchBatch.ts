/**
 * Sequential research-batch runner with per-tool resilience (GAP-RESEARCH-01).
 *
 * The Research Library used to `throw` on the first failed tool, which aborted every
 * remaining tool and discarded the reason behind a generic message. This runner:
 * - keeps going past a failed tool, recording the backend's reason;
 * - marks a tool `blocked` — and never calls it — when one of its required
 *   prerequisites in the same run failed or was itself blocked (calling it would
 *   only earn a 400 and a deduct-then-refund round trip);
 * - reports each status change so the UI can render progress.
 *
 * Tools run in the order given, which the caller has already sorted so that
 * prerequisites come first.
 */
import { getApiErrorMessage } from '@/utils/apiError';

/** Same wording the wizard uses (ResearchPanel.tsx), so both surfaces read alike. */
export const BLOCKED_ERROR = 'Blocked: a required prerequisite tool failed';

export type BatchToolStatus = 'running' | 'complete' | 'failed' | 'blocked';

export interface BatchToolFailure {
  tool: string;
  status: 'failed' | 'blocked';
  error: string;
}

export interface BatchOutcome {
  /** Tools that completed, in run order. */
  succeeded: string[];
  /** Tools that failed or were blocked, in run order. */
  failed: BatchToolFailure[];
}

/**
 * Run `orderedTools` one at a time without letting one failure abort the batch.
 *
 * @param orderedTools - tools to run, prerequisites first
 * @param requiredPrereqs - a tool's REQUIRED prerequisites; only those that are part of
 *   this run can block it (earlier-session results are the backend's to check)
 * @param runTool - executes one tool; a rejection marks it failed
 * @param onUpdate - called on every status change, with the error for failed/blocked
 * @returns which tools succeeded and which failed or were blocked, with reasons
 */
export async function runResearchBatch(
  orderedTools: readonly string[],
  requiredPrereqs: (tool: string) => readonly string[],
  runTool: (tool: string) => Promise<unknown>,
  onUpdate: (tool: string, status: BatchToolStatus, error?: string) => void
): Promise<BatchOutcome> {
  const inRun = new Set(orderedTools);
  const notSucceeded = new Set<string>();
  const succeeded: string[] = [];
  const failed: BatchToolFailure[] = [];

  for (const tool of orderedTools) {
    const blocked = requiredPrereqs(tool).some((dep) => inRun.has(dep) && notSucceeded.has(dep));
    if (blocked) {
      notSucceeded.add(tool);
      failed.push({ tool, status: 'blocked', error: BLOCKED_ERROR });
      onUpdate(tool, 'blocked', BLOCKED_ERROR);
      continue;
    }

    onUpdate(tool, 'running');
    try {
      await runTool(tool);
      succeeded.push(tool);
      onUpdate(tool, 'complete');
    } catch (err) {
      const error = getApiErrorMessage(err, 'Tool failed to run.');
      notSucceeded.add(tool);
      failed.push({ tool, status: 'failed', error });
      onUpdate(tool, 'failed', error);
    }
  }

  return { succeeded, failed };
}
