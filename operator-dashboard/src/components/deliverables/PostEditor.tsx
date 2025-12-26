import { useState, useEffect, useMemo } from 'react';
import { ArrowLeft, Save, RotateCcw, Loader2, AlertCircle } from 'lucide-react';
import type { Post } from '@/types/domain';
import { Button, Textarea, Badge } from '@/components/ui';

interface PostEditorProps {
  post: Post;
  onSave: (content: string) => Promise<void> | Promise<Post>;
  onCancel: () => void;
  onRegenerate?: () => void;
  totalPosts: number;
  currentIndex: number;
}

// Simple word count function
function countWords(text: string): number {
  return text.trim().split(/\s+/).filter(word => word.length > 0).length;
}

// Simple readability score (Flesch Reading Ease approximation)
function calculateReadability(text: string): number {
  const words = countWords(text);
  const sentences = text.split(/[.!?]+/).filter(s => s.trim().length > 0).length;
  const syllables = text.split(/\s+/).reduce((count, word) => {
    // Simple syllable count approximation
    return count + Math.max(1, word.toLowerCase().replace(/[^a-z]/g, '').length / 3);
  }, 0);

  if (words === 0 || sentences === 0) return 0;

  const avgWordsPerSentence = words / sentences;
  const avgSyllablesPerWord = syllables / words;

  // Flesch Reading Ease formula
  const score = 206.835 - 1.015 * avgWordsPerSentence - 84.6 * avgSyllablesPerWord;
  return Math.max(0, Math.min(100, Math.round(score)));
}

export function PostEditor({
  post,
  onSave,
  onCancel,
  onRegenerate,
  totalPosts,
  currentIndex,
}: PostEditorProps) {
  const [content, setContent] = useState(post.content);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset content when post changes
  useEffect(() => {
    setContent(post.content);
    setError(null);
  }, [post.id, post.content]);

  // Calculate live metrics
  const metrics = useMemo(() => {
    const wordCount = countWords(content);
    const readability = calculateReadability(content);
    const hasChanges = content !== post.content;

    return { wordCount, readability, hasChanges };
  }, [content, post.content]);

  const handleSave = async () => {
    if (!metrics.hasChanges) {
      onCancel();
      return;
    }

    try {
      setIsSaving(true);
      setError(null);
      await onSave(content);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save post');
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    if (metrics.hasChanges) {
      if (window.confirm('You have unsaved changes. Are you sure you want to cancel?')) {
        onCancel();
      }
    } else {
      onCancel();
    }
  };

  const getReadabilityColor = (score: number) => {
    if (score >= 60) return 'text-green-600 dark:text-green-400';
    if (score >= 50) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-red-600 dark:text-red-400';
  };

  const getWordCountColor = (count: number) => {
    if (count >= 75 && count <= 350) return 'text-green-600 dark:text-green-400';
    if (count >= 50 && count <= 400) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-red-600 dark:text-red-400';
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b border-slate-200 dark:border-neutral-700 px-6 py-4">
        <div className="flex items-center justify-between mb-2">
          <button
            onClick={handleCancel}
            className="flex items-center gap-2 text-sm text-slate-600 dark:text-neutral-400 hover:text-slate-900 dark:hover:text-neutral-100 transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Posts
          </button>
          <span className="text-sm text-slate-500 dark:text-neutral-500">
            Post {currentIndex + 1} of {totalPosts}
          </span>
        </div>

        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-neutral-100">
              Edit Post
            </h3>
            {post.templateName && (
              <p className="text-sm text-slate-600 dark:text-neutral-400 mt-0.5">
                Template: {post.templateName}
              </p>
            )}
          </div>
          {metrics.hasChanges && (
            <Badge variant="warning">Unsaved Changes</Badge>
          )}
        </div>
      </div>

      {/* Metrics */}
      <div className="border-b border-slate-200 dark:border-neutral-700 px-6 py-3 bg-slate-50 dark:bg-neutral-900">
        <div className="flex items-center gap-6 text-sm">
          <div>
            <span className="text-slate-600 dark:text-neutral-400">Word Count: </span>
            <span className={`font-semibold ${getWordCountColor(metrics.wordCount)}`}>
              {metrics.wordCount}
            </span>
            <span className="text-xs text-slate-500 dark:text-neutral-500 ml-1">
              (target: 75-350)
            </span>
          </div>
          <div>
            <span className="text-slate-600 dark:text-neutral-400">Readability: </span>
            <span className={`font-semibold ${getReadabilityColor(metrics.readability)}`}>
              {metrics.readability}
            </span>
            <span className="text-xs text-slate-500 dark:text-neutral-500 ml-1">
              (target: 60+)
            </span>
          </div>
          {post.status && (
            <div>
              <span className="text-slate-600 dark:text-neutral-400">Status: </span>
              <Badge variant={post.status === 'approved' ? 'success' : 'default'}>
                {post.status}
              </Badge>
            </div>
          )}
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="mx-6 mt-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3 flex items-start gap-2">
          <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm font-medium text-red-800 dark:text-red-200">Error saving post</p>
            <p className="text-xs text-red-600 dark:text-red-300 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Content Editor */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        <Textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          rows={20}
          className="font-mono text-sm resize-none h-full"
          placeholder="Enter post content..."
          disabled={isSaving}
        />
      </div>

      {/* Actions */}
      <div className="border-t border-slate-200 dark:border-neutral-700 px-6 py-4 bg-slate-50 dark:bg-neutral-900">
        <div className="flex items-center justify-between gap-3">
          <div className="flex gap-2">
            <Button
              variant="secondary"
              onClick={handleCancel}
              disabled={isSaving}
            >
              Cancel
            </Button>
            {onRegenerate && (
              <Button
                variant="outline"
                onClick={onRegenerate}
                disabled={isSaving}
              >
                <RotateCcw className="h-4 w-4" />
                Regenerate
              </Button>
            )}
          </div>
          <Button
            variant="primary"
            onClick={handleSave}
            disabled={!metrics.hasChanges || isSaving}
          >
            {isSaving ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="h-4 w-4" />
                Save Changes
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
