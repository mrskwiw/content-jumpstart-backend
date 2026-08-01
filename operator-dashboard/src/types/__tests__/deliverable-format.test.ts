import { describe, it, expect } from '@jest/globals';
import { DeliverableSchema } from '@/types/domain';

const base = {
  id: 'd1',
  projectId: 'p1',
  clientId: 'c1',
  path: 'media/x/y.png',
  createdAt: '2026-08-01T00:00:00Z',
  status: 'ready' as const,
};

describe('DeliverableSchema.format', () => {
  it('accepts document export formats', () => {
    for (const format of ['txt', 'md', 'docx', 'pdf']) {
      expect(DeliverableSchema.safeParse({ ...base, format }).success).toBe(true);
    }
  });

  it('accepts media-generation formats (audio/video/image)', () => {
    // Regression: the Phase-12 media path stores these; a closed txt/md/docx enum made
    // getDetails().parse() throw on any media deliverable (image surfaced the gap).
    for (const format of ['audio', 'video', 'image']) {
      expect(DeliverableSchema.safeParse({ ...base, format }).success).toBe(true);
    }
  });

  it('still rejects an unknown format', () => {
    expect(DeliverableSchema.safeParse({ ...base, format: 'exe' }).success).toBe(false);
  });
});
