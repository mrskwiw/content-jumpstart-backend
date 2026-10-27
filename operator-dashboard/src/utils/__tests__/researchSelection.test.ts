import { runnableSelection } from '../researchSelection';
import type { ResearchTool } from '@/api/research';

const t = (name: string, status: ResearchTool['status'] = 'available'): ResearchTool => ({
  name,
  label: name,
  status,
});

describe('runnableSelection', () => {
  it('keeps available tools in selection order', () => {
    expect(runnableSelection(['b', 'a'], [t('a'), t('b')])).toEqual(['b', 'a']);
  });

  // Codex review of ec987d8: a tool selected while available that then becomes
  // coming-soon (tools refetch, or the feature registry disables it) must drop out of
  // what is displayed, priced and submitted — not just stop accepting new clicks.
  it('drops a selected tool that is now coming soon', () => {
    expect(runnableSelection(['a', 'b'], [t('a'), t('b', 'coming_soon')])).toEqual(['a']);
  });

  it('keeps a selected tool the tool list does not mention (e.g. still loading)', () => {
    // Unknown is not the same as unavailable; the backend still validates it.
    expect(runnableSelection(['a'], [])).toEqual(['a']);
  });

  it('treats experimental tools as runnable', () => {
    expect(runnableSelection(['x'], [t('x', 'experimental')])).toEqual(['x']);
  });
});
