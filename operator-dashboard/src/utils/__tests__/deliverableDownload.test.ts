import { describe, it, expect } from '@jest/globals';
import { downloadHint, isMediaDeliverable } from '../deliverableDownload';

describe('isMediaDeliverable', () => {
  it('recognizes media families', () => {
    for (const f of ['audio', 'video', 'image']) expect(isMediaDeliverable(f)).toBe(true);
    for (const f of ['txt', 'md', 'docx', 'pdf']) expect(isMediaDeliverable(f)).toBe(false);
  });
});

describe('downloadHint', () => {
  it('uses the document format directly for export deliverables', () => {
    expect(downloadHint('docx', 'data/outputs/Acme/report.docx')).toBe('docx');
    expect(downloadHint('md', 'anything')).toBe('md');
  });

  it('derives the real extension from the storage key for media deliverables', () => {
    // Would otherwise save as `deliverable.image` — use the key's real extension.
    expect(downloadHint('image', 'media/u/j/asset-1.png')).toBe('png');
    expect(downloadHint('video', 'media/u/j/clip.MP4')).toBe('mp4');
    expect(downloadHint('audio', 'media/u/j/voice.mp3')).toBe('mp3');
  });

  it('falls back to the format word when the key has no usable extension', () => {
    expect(downloadHint('image', 'media/u/j/noext')).toBe('image');
    expect(downloadHint('image', '')).toBe('image');
    // A path segment that only looks like an extension but is too long is ignored.
    expect(downloadHint('image', 'media/u/j/x.superlongext')).toBe('image');
  });
});
