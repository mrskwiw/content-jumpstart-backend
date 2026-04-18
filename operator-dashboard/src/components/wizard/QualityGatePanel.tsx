import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { generatorApi } from '@/api/generator';
import { postsApi } from '@/api/posts';
import type { PostDraft } from '@/types/domain';
import { AlertTriangle, RotateCw, ShieldCheck, Edit, CheckCircle2 } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Button, Textarea } from '@/components/ui';
import { Badge } from '@/components/ui/Badge';

interface Props {
  posts: PostDraft[];
  projectId: string;
  onRegenerated?: () => void;
}

export function QualityGatePanel({ posts, projectId, onRegenerated }: Props) {
  const queryClient = useQueryClient();
  const [editingPost, setEditingPost] = useState<PostDraft | null>(null);
  const [editedContent, setEditedContent] = useState('');

  const flagged = posts.filter((p) => p.status === 'flagged' || (p.flags && p.flags.length > 0));
  const approved = posts.filter((p) => p.status === 'approved' || (!p.flags || p.flags.length === 0));

  const regen = useMutation({
    mutationFn: (postIds: string[]) =>
      generatorApi.regenerate({
        projectId,
        postIds,
        reason: 'quality_gate_flags',
      }),
    onSuccess: () => onRegenerated?.(),
  });

  const updatePost = useMutation({
    mutationFn: ({ postId, content }: { postId: string; content: string }) =>
      postsApi.update(postId, { content }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['posts'] });
      setEditingPost(null);
      onRegenerated?.();
    },
  });

  const handleEdit = (post: PostDraft) => {
    setEditingPost(post);
    setEditedContent(post.content);
  };

  const handleSave = () => {
    if (editingPost && editedContent.trim()) {
      updatePost.mutate({ postId: editingPost.id, content: editedContent });
    }
  };

  const handleCancel = () => {
    setEditingPost(null);
    setEditedContent('');
  };

  const hasFlags = flagged.length > 0;

  return (
    <>
      <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-4 shadow-sm">
        <div className="flex items-center gap-2">
          {hasFlags ? (
            <AlertTriangle className="h-5 w-5 text-amber-600" />
          ) : (
            <ShieldCheck className="h-5 w-5 text-emerald-600" />
          )}
          <div>
            <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">Quality Gate</h3>
            <p className="text-xs text-neutral-600 dark:text-neutral-400">
              Review all posts, edit inline, or regenerate flagged items before export.
            </p>
          </div>
        </div>

        {/* Summary Stats */}
        <div className="mt-3 flex gap-3 text-xs">
          <div className="rounded-md border border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800 px-3 py-1">
            <span className="font-semibold text-neutral-700 dark:text-neutral-300">Total: </span>
            <span className="text-neutral-900 dark:text-neutral-100">{posts.length}</span>
          </div>
          {hasFlags && (
            <div className="rounded-md border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20 px-3 py-1">
              <span className="font-semibold text-amber-700 dark:text-amber-300">Flagged: </span>
              <span className="text-amber-900 dark:text-amber-100">{flagged.length}</span>
            </div>
          )}
          <div className="rounded-md border border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-900/20 px-3 py-1">
            <span className="font-semibold text-emerald-700 dark:text-emerald-300">Approved: </span>
            <span className="text-emerald-900 dark:text-emerald-100">{approved.length}</span>
          </div>
        </div>

        {/* Flagged Posts Section */}
        {hasFlags && (
          <div className="mt-4">
            <h4 className="mb-2 text-xs font-semibold text-amber-900 dark:text-amber-100">Flagged Posts ({flagged.length})</h4>
            <div className="space-y-2">
              {flagged.map((post) => (
                <div key={post.id} className="rounded-md border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20 p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1">
                      <div className="mb-1 flex items-center gap-2">
                        <span className="text-xs font-semibold text-amber-900 dark:text-amber-100">Post {post.id}</span>
                        {post.flags && post.flags.length > 0 && (
                          <div className="flex flex-wrap gap-1">
                            {post.flags.map((flag, idx) => (
                              <Badge key={idx} variant="warning" className="text-xs">
                                {flag}
                              </Badge>
                            ))}
                          </div>
                        )}
                      </div>
                      <p className="line-clamp-4 text-xs text-amber-800 dark:text-amber-200">{post.content}</p>
                      <div className="mt-1 flex gap-3 text-xs text-amber-700 dark:text-amber-300">
                        {post.wordCount && <span>{post.wordCount} words</span>}
                        {post.targetPlatform && <span className="capitalize">{post.targetPlatform}</span>}
                        {post.readabilityScore !== undefined && (
                          <span>Readability: {(post?.readabilityScore ?? 0).toFixed(1)}</span>
                        )}
                      </div>
                    </div>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => handleEdit(post)}
                      className="flex-shrink-0"
                    >
                      <Edit className="h-3 w-3 mr-1" />
                      Edit
                    </Button>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-3 flex justify-end">
              <button
                disabled={regen.isPending}
                onClick={() => regen.mutate(flagged.map((f) => f.id))}
                className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 dark:hover:bg-blue-800 disabled:opacity-50"
              >
                <RotateCw className="h-4 w-4" />
                {regen.isPending ? 'Regenerating...' : 'Regenerate all flagged'}
              </button>
            </div>
          </div>
        )}

        {/* Approved Posts Section */}
        {approved.length > 0 && (
          <div className="mt-4">
            <h4 className="mb-2 text-xs font-semibold text-emerald-900 dark:text-emerald-100">
              Approved Posts ({approved.length})
            </h4>
            <div className="space-y-2">
              {approved.map((post) => (
                <div key={post.id} className="rounded-md border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1">
                      <div className="mb-1 flex items-center gap-2">
                        <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                        <span className="text-xs font-semibold text-neutral-900 dark:text-neutral-100">Post {post.id}</span>
                      </div>
                      <p className="line-clamp-4 text-xs text-neutral-700 dark:text-neutral-300">{post.content}</p>
                      <div className="mt-1 flex gap-3 text-xs text-neutral-500 dark:text-neutral-400">
                        {post.wordCount && <span>{post.wordCount} words</span>}
                        {post.targetPlatform && <span className="capitalize">{post.targetPlatform}</span>}
                        {post.readabilityScore !== undefined && (
                          <span>Readability: {(post?.readabilityScore ?? 0).toFixed(1)}</span>
                        )}
                      </div>
                      {post.twitterShareCopy && post.targetPlatform === 'blog' && (
                        <div className="mt-2 rounded bg-sky-50 dark:bg-sky-900/20 px-2 py-1.5">
                          <p className="mb-0.5 text-xs font-semibold text-sky-700 dark:text-sky-300">Twitter/X Share Copy</p>
                          <p className="text-xs text-sky-800 dark:text-sky-200 whitespace-pre-wrap">{post.twitterShareCopy}</p>
                        </div>
                      )}
                    </div>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => handleEdit(post)}
                      className="flex-shrink-0"
                    >
                      <Edit className="h-3 w-3 mr-1" />
                      Edit
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {regen.error && (
          <div className="mt-3 rounded-md bg-rose-50 dark:bg-rose-900/20 px-3 py-2 text-sm text-rose-700 dark:text-rose-300">
            {(regen.error as Error).message || 'Regeneration failed'}
          </div>
        )}
      </div>

      {/* Edit Dialog */}
      <Dialog open={!!editingPost} onOpenChange={(open) => !open && handleCancel()}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Post {editingPost?.id}</DialogTitle>
            <DialogDescription>
              Edit the post content below. Word count and readability will be recalculated on save.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3">
            <Textarea
              value={editedContent}
              onChange={(e) => setEditedContent(e.target.value)}
              rows={12}
              className="font-mono text-sm"
              placeholder="Enter post content..."
            />

            {editingPost && (
              <div className="rounded-md border border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800 p-3 text-xs text-neutral-600 dark:text-neutral-400">
                <div className="flex gap-4">
                  {editingPost.wordCount && <span>Original: {editingPost.wordCount} words</span>}
                  {editingPost.readabilityScore !== undefined && (
                    <span>Readability: {(editingPost?.readabilityScore ?? 0).toFixed(1)}</span>
                  )}
                </div>
                {editingPost.flags && editingPost.flags.length > 0 && (
                  <div className="mt-2">
                    <span className="font-semibold">Flags: </span>
                    {editingPost.flags.join(', ')}
                  </div>
                )}
              </div>
            )}

            {updatePost.error && (
              <div className="rounded-md bg-rose-50 dark:bg-rose-900/20 px-3 py-2 text-sm text-rose-700 dark:text-rose-300">
                {(updatePost.error as Error).message || 'Update failed'}
              </div>
            )}
          </div>

          <DialogFooter>
            <Button variant="secondary" onClick={handleCancel} disabled={updatePost.isPending}>
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleSave}
              disabled={updatePost.isPending || !editedContent.trim()}
            >
              {updatePost.isPending ? 'Saving...' : 'Save Changes'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
