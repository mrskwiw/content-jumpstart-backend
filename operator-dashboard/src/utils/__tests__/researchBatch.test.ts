import { runResearchBatch, BLOCKED_ERROR, type BatchToolStatus } from '../researchBatch';

/** Axios-shaped rejection, as researchApi.run throws for a 4xx/5xx. */
const apiError = (status: number, detail: string) =>
  Object.assign(new Error(`Request failed with status code ${status}`), {
    response: { status, data: { detail } },
  });

const prereqs =
  (map: Record<string, string[]>) =>
  (tool: string): readonly string[] =>
    map[tool] ?? [];

describe('runResearchBatch (GAP-RESEARCH-01)', () => {
  it('runs every tool in order when all succeed', async () => {
    const runTool = jest.fn().mockResolvedValue({});
    const outcome = await runResearchBatch(['a', 'b', 'c'], prereqs({}), runTool, jest.fn());

    expect(runTool.mock.calls.map(([t]) => t)).toEqual(['a', 'b', 'c']);
    expect(outcome).toEqual({ succeeded: ['a', 'b', 'c'], failed: [] });
  });

  it('continues past a failed tool instead of aborting the batch (F1)', async () => {
    const runTool = jest.fn(async (tool: string) => {
      if (tool === 'b') throw apiError(400, 'No web search API key found.');
      return {};
    });
    const outcome = await runResearchBatch(['a', 'b', 'c'], prereqs({}), runTool, jest.fn());

    expect(runTool).toHaveBeenCalledTimes(3);
    expect(outcome.succeeded).toEqual(['a', 'c']);
    // The backend's reason is kept, not a generic "status code 400" (F3).
    expect(outcome.failed).toEqual([
      { tool: 'b', status: 'failed', error: 'No web search API key found.' },
    ]);
  });

  it('blocks — without calling — a tool whose in-run prerequisite failed, transitively', async () => {
    const runTool = jest.fn(async (tool: string) => {
      if (tool === 'determine_competitors') throw apiError(500, 'Upstream timeout');
      return {};
    });
    const outcome = await runResearchBatch(
      ['determine_competitors', 'competitive_analysis', 'content_gap_analysis', 'audience_research'],
      prereqs({
        competitive_analysis: ['determine_competitors'],
        content_gap_analysis: ['competitive_analysis'],
      }),
      runTool,
      jest.fn()
    );

    expect(runTool.mock.calls.map(([t]) => t)).toEqual(['determine_competitors', 'audience_research']);
    expect(outcome.succeeded).toEqual(['audience_research']);
    expect(outcome.failed).toEqual([
      { tool: 'determine_competitors', status: 'failed', error: 'Upstream timeout' },
      { tool: 'competitive_analysis', status: 'blocked', error: BLOCKED_ERROR },
      { tool: 'content_gap_analysis', status: 'blocked', error: BLOCKED_ERROR },
    ]);
  });

  it('does not block on a prerequisite that is not part of this run', async () => {
    // e.g. completed in an earlier session — the backend checks that, not us.
    const runTool = jest.fn().mockResolvedValue({});
    const outcome = await runResearchBatch(
      ['competitive_analysis'],
      prereqs({ competitive_analysis: ['determine_competitors'] }),
      runTool,
      jest.fn()
    );
    expect(runTool).toHaveBeenCalledWith('competitive_analysis');
    expect(outcome.succeeded).toEqual(['competitive_analysis']);
  });

  it('reports each status change, and blocked tools never enter running', async () => {
    const updates: Array<[string, BatchToolStatus, string | undefined]> = [];
    const runTool = jest.fn(async (tool: string) => {
      if (tool === 'a') throw new Error('boom');
      return {};
    });
    await runResearchBatch(['a', 'b'], prereqs({ b: ['a'] }), runTool, (t, s, e) =>
      updates.push([t, s, e])
    );
    expect(updates).toEqual([
      ['a', 'running', undefined],
      ['a', 'failed', 'boom'],
      ['b', 'blocked', BLOCKED_ERROR],
    ]);
  });

  it('returns no successes when every tool fails, without throwing', async () => {
    const runTool = jest.fn().mockRejectedValue(apiError(503, 'down'));
    const outcome = await runResearchBatch(['a', 'b'], prereqs({}), runTool, jest.fn());
    expect(outcome.succeeded).toEqual([]);
    expect(outcome.failed.map((f) => f.status)).toEqual(['failed', 'failed']);
  });
});
