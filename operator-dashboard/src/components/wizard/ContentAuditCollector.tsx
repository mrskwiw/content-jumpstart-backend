import { useState } from 'react';
import { Button, Input, Textarea, Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui';
import { Plus, X, Link as LinkIcon, FileText, AlertCircle } from 'lucide-react';

interface ContentPiece {
  title: string;
  url?: string;
  type: string;
  publishDate?: string;
}

interface ContentAuditCollectorProps {
  value: ContentPiece[];
  onChange: (pieces: ContentPiece[]) => void;
  error?: string;
}

const CONTENT_TYPES = [
  { value: 'blog_post', label: 'Blog Post' },
  { value: 'social_post', label: 'Social Post' },
  { value: 'email', label: 'Email' },
  { value: 'landing_page', label: 'Landing Page' },
  { value: 'guide', label: 'Guide/Ebook' },
  { value: 'case_study', label: 'Case Study' },
  { value: 'video', label: 'Video' },
  { value: 'webinar', label: 'Webinar' },
  { value: 'other', label: 'Other' },
];

// Auto-detect content type from URL
function detectContentType(url: string): string {
  const urlLower = url.toLowerCase();

  if (urlLower.includes('linkedin.com') || urlLower.includes('twitter.com') || urlLower.includes('facebook.com')) {
    return 'social_post';
  }
  if (urlLower.includes('youtube.com') || urlLower.includes('vimeo.com') || urlLower.includes('/video')) {
    return 'video';
  }
  if (urlLower.includes('/blog/') || urlLower.includes('/post/') || urlLower.includes('/article/')) {
    return 'blog_post';
  }
  if (urlLower.includes('/case-stud') || urlLower.includes('/success-stor')) {
    return 'case_study';
  }
  if (urlLower.includes('/guide/') || urlLower.includes('/ebook/') || urlLower.includes('.pdf')) {
    return 'guide';
  }
  if (urlLower.includes('/webinar')) {
    return 'webinar';
  }
  if (urlLower.includes('/landing') || urlLower.includes('/lp/')) {
    return 'landing_page';
  }

  return 'blog_post'; // Default
}

// Extract title from URL
function extractTitleFromUrl(url: string): string {
  try {
    const urlObj = new URL(url);
    const pathname = urlObj.pathname;

    // Get last segment of path
    const segments = pathname.split('/').filter(s => s.length > 0);
    if (segments.length === 0) return '';

    const lastSegment = segments[segments.length - 1];

    // Remove file extension
    const withoutExt = lastSegment.replace(/\.(html|php|aspx)$/i, '');

    // Convert hyphens/underscores to spaces and title case
    return withoutExt
      .replace(/[-_]/g, ' ')
      .split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  } catch {
    return '';
  }
}

export function ContentAuditCollector({ value, onChange, error }: ContentAuditCollectorProps) {
  const [urlListText, setUrlListText] = useState('');
  const [showManualEntry, setShowManualEntry] = useState(false);
  const [manualEntry, setManualEntry] = useState<ContentPiece>({ title: '', url: '', type: 'blog_post', publishDate: '' });

  const handleUrlListParse = () => {
    const urls = urlListText
      .split('\n')
      .map(line => line.trim())
      .filter(line => line.length > 0 && (line.startsWith('http://') || line.startsWith('https://')));

    if (urls.length === 0) {
      return;
    }

    const newPieces: ContentPiece[] = urls.map(url => ({
      title: extractTitleFromUrl(url) || 'Untitled',
      url,
      type: detectContentType(url),
      publishDate: undefined,
    }));

    onChange([...value, ...newPieces]);
    setUrlListText('');
  };

  const handleManualAdd = () => {
    if (!manualEntry.title.trim()) {
      return;
    }

    onChange([...value, { ...manualEntry }]);
    setManualEntry({ title: '', url: '', type: 'blog_post', publishDate: '' });
    setShowManualEntry(false);
  };

  const handleRemove = (index: number) => {
    onChange(value.filter((_, i) => i !== index));
  };

  const count = value.length;

  return (
    <div className="space-y-4">
      {/* URL List Input */}
      <div>
        <label className="mb-2 flex items-center gap-2 text-sm font-medium text-neutral-800 dark:text-neutral-200">
          <LinkIcon className="h-4 w-4" />
          Paste Content URLs (Quick Method)
        </label>
        <Textarea
          value={urlListText}
          onChange={(e) => setUrlListText(e.target.value)}
          placeholder="https://blog.client.com/article-1&#10;https://blog.client.com/article-2&#10;https://linkedin.com/posts/abc123"
          rows={5}
          className="font-mono text-sm"
        />
        <div className="mt-2 flex items-center justify-between">
          <p className="text-xs text-neutral-500">
            One URL per line. We'll auto-detect title and type.
          </p>
          <Button
            variant="secondary"
            size="sm"
            onClick={handleUrlListParse}
            disabled={!urlListText.trim()}
          >
            <Plus className="h-4 w-4 mr-1" />
            Add URLs
          </Button>
        </div>
      </div>

      {/* Manual Entry */}
      <div className="border-t border-neutral-200 dark:border-neutral-700 pt-4">
        {!showManualEntry ? (
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowManualEntry(true)}
            className="w-full"
          >
            <Plus className="h-4 w-4 mr-2" />
            Add Content Manually (for non-URL content)
          </Button>
        ) : (
          <div className="space-y-3 rounded-lg border border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800 p-4">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium text-neutral-800 dark:text-neutral-200">
                Manual Entry
              </label>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowManualEntry(false)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            <div>
              <label className="mb-1 block text-xs font-medium text-neutral-700 dark:text-neutral-300">
                Title <span className="text-rose-500">*</span>
              </label>
              <Input
                value={manualEntry.title}
                onChange={(e) => setManualEntry({ ...manualEntry, title: e.target.value })}
                placeholder="How to Scale Your Startup in 2024"
              />
            </div>

            <div>
              <label className="mb-1 block text-xs font-medium text-neutral-700 dark:text-neutral-300">
                Content Type <span className="text-rose-500">*</span>
              </label>
              <Select
                value={manualEntry.type}
                onValueChange={(type) => setManualEntry({ ...manualEntry, type })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CONTENT_TYPES.map(type => (
                    <SelectItem key={type.value} value={type.value}>
                      {type.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-neutral-700 dark:text-neutral-300">
                  URL (optional)
                </label>
                <Input
                  value={manualEntry.url}
                  onChange={(e) => setManualEntry({ ...manualEntry, url: e.target.value })}
                  placeholder="https://..."
                />
              </div>

              <div>
                <label className="mb-1 block text-xs font-medium text-neutral-700 dark:text-neutral-300">
                  Publish Date (optional)
                </label>
                <Input
                  type="date"
                  value={manualEntry.publishDate}
                  onChange={(e) => setManualEntry({ ...manualEntry, publishDate: e.target.value })}
                />
              </div>
            </div>

            <Button
              variant="primary"
              size="sm"
              onClick={handleManualAdd}
              disabled={!manualEntry.title.trim()}
              className="w-full"
            >
              <Plus className="h-4 w-4 mr-1" />
              Add Content Piece
            </Button>
          </div>
        )}
      </div>

      {/* Content List */}
      {count > 0 && (
        <div className="border-t border-neutral-200 dark:border-neutral-700 pt-4">
          <div className="mb-3 flex items-center justify-between">
            <label className="flex items-center gap-2 text-sm font-medium text-neutral-800 dark:text-neutral-200">
              <FileText className="h-4 w-4" />
              Content Inventory ({count}/100)
            </label>
            {count > 100 && (
              <span className="text-xs text-rose-600 dark:text-rose-400">
                Maximum 100 pieces
              </span>
            )}
          </div>

          <div className="space-y-2 max-h-96 overflow-y-auto">
            {value.map((piece, index) => (
              <div
                key={index}
                className="flex items-start gap-3 rounded-md border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-3 text-sm"
              >
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-neutral-900 dark:text-neutral-100 truncate">
                    {piece.title}
                  </div>
                  <div className="mt-1 flex items-center gap-3 text-xs text-neutral-500 dark:text-neutral-400">
                    <span className="rounded bg-neutral-100 dark:bg-neutral-800 px-2 py-0.5">
                      {CONTENT_TYPES.find(t => t.value === piece.type)?.label || piece.type}
                    </span>
                    {piece.url && (
                      <a
                        href={piece.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="truncate hover:text-blue-600 dark:hover:text-blue-400 max-w-xs"
                      >
                        {piece.url}
                      </a>
                    )}
                    {piece.publishDate && <span>{piece.publishDate}</span>}
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleRemove(index)}
                  className="flex-shrink-0"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="flex items-center gap-2 rounded-md border border-rose-200 bg-rose-50 dark:border-rose-900 dark:bg-rose-950 p-3 text-sm text-rose-700 dark:text-rose-300">
          <AlertCircle className="h-4 w-4 flex-shrink-0" />
          {error}
        </div>
      )}

      {/* Helper Text */}
      <p className="text-xs text-neutral-500 dark:text-neutral-400">
        Provide 1-100 content pieces to audit. URLs are auto-analyzed for type and title. For content without URLs (like internal docs), use manual entry.
      </p>
    </div>
  );
}
