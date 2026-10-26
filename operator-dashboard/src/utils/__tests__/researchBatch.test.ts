import { runResearchBatch, type BatchToolStatus } from '../researchBatch';

/** Axios-shaped rejection, as researchApi.run throws for a 4xx/5xx. */
const apiError = (status: number, detail: string) =>
  Object.assign(new Error(`Request failed with status code ${status}`), {
    response: { status, data: { detail } },
  });

describe('runResearchBatch (GAP-RESEARCH-01)', () => {
  it('runs every tool in order when all succeed', async () => {
    const runTool = jest.fn().mockResolvedValue({});
    const outcome = await runResearchBatch(['a', 'b', 'c'], runTool, jest.fn());

    expect(runTool.mock.calls.map(([t]) => t)).toEqual(['a', 'b', 'c']);
    expect(outcome).toEqual({ succeeded: ['a', 'b', 'c'], failed: [] });
  });

  it('continues past a failed tool instead of aborting the batch (F1)', async () => {
    const runTool = jest.fn(async (tool: string) => {
      if (tool === 'b') throw apiError(400, 'No web search API key found.');
      return {};
    });
    const outcome = await runResearchBatch(['a', 'b', 'c'], runTool, jest.fn());

    expect(runTool).toHaveBeenCalledTimes(3);
    expect(outcome.succeeded).toEqual(['a', 'c']);
    // The backend's reason is kept, not a generic "status code 400" (F3).
    expect(outcome.failed).toEqual([{ tool: 'b', error: 'No web search API key found.' }]);
  });

  it("still attempts a failed tool's dependent and records the backend's verdict", async () => {
    // Codex reviews of 7400c98/349dc5e: whether a dependent may run is the backend's
    // call (client-scoped history, project-scoped data, a status query that may still
    // be loading). The runner must not second-guess it — it attempts the tool and
    // reports whatever the backend decides.
    const runTool = jest.fn(async (tool: string) => {
      if (tool === 'determine_competitors') throw apiError(500, 'Upstream timeout');
      if (tool === 'competitive_analysis')
        throw apiError(400, 'Missing required prerequisite: determine_competitors');
      return {};
    });
    const outcome = await runResearchBatch(
      ['determine_competitors', 'competitive_analysis', 'audience_research'],
      runTool,
      jest.fn()
    );

    expect(runTool.mock.calls.map(([t]) => t)).toEqual([
      'determine_competitors',
      'competitive_analysis',
      'audience_research',
    ]);
    expect(outcome.succeeded).toEqual(['audience_research']);
    expect(outcome.failed).toEqual([
      { tool: 'determine_competitors', error: 'Upstream timeout' },
      { tool: 'competitive_analysis', error: 'Missing required prerequisite: determine_competitors' },
    ]);
  });

  it('reports running then the final status for each tool', async () => {
    const updates: Array<[string, BatchToolStatus, string | undefined]> = [];
    const runTool = jest.fn(async (tool: string) => {
      if (tool === 'a') throw new Error('boom');
      return {};
    });
    await runResearchBatch(['a', 'b'], runTool, (t, s, e) => updates.push([t, s, e]));
    expect(updates).toEqual([
      ['a', 'running', undefined],
      ['a', 'failed', 'boom'],
      ['b', 'running', undefined],
      ['b', 'complete', undefined],
    ]);
  });

  it('returns no successes when every tool fails, without throwing', async () => {
    const runTool = jest.fn().mockRejectedValue(apiError(503, 'down'));
    const outcome = await runResearchBatch(['a', 'b'], runTool, jest.fn());
    expect(outcome.succeeded).toEqual([]);
    expect(outcome.failed.map((f) => f.tool)).toEqual(['a', 'b']);
  });

  it('falls back to a generic reason when the error carries none', async () => {
    const runTool = jest.fn().mockRejectedValue({});
    const outcome = await runResearchBatch(['a'], runTool, jest.fn());
    expect(outcome.failed).toEqual([{ tool: 'a', error: 'Tool failed to run.' }]);
  });
});
