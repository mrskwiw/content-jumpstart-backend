// Deliverable download helpers (MEDIA-DELIVERABLE-SPLIT).

/** Deliverable.format values produced by the Phase-12 media pipeline. */
export const MEDIA_DELIVERABLE_FORMATS = new Set(['audio', 'video', 'image']);

export function isMediaDeliverable(format: string): boolean {
  return MEDIA_DELIVERABLE_FORMATS.has(format);
}

/**
 * The filename-extension hint passed to `deliverablesApi.download`. Document exports
 * carry a real file extension in `format` (txt/md/docx/pdf). Media deliverables carry a
 * media-family word (image/audio/video) that is NOT a usable extension — so a media
 * download would save as `deliverable.image`. Derive the true extension from the storage
 * key (`.../asset.png`) instead; fall back to `format` when no extension is present.
 */
export function downloadHint(format: string, path: string): string {
  if (!isMediaDeliverable(format)) return format;
  const lastSegment = (path || '').split('/').pop() ?? '';
  const dot = lastSegment.lastIndexOf('.');
  if (dot > -1 && dot < lastSegment.length - 1) {
    const ext = lastSegment.slice(dot + 1);
    if (/^[A-Za-z0-9]{1,5}$/.test(ext)) return ext.toLowerCase();
  }
  return format;
}
