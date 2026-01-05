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
      <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex items-center gap-2">
          {hasFlags ? (
            <AlertTriangle className="h-5 w-5 text-amber-600" />
          ) : (
            <ShieldCheck className="h-5 w-5 text-emerald-600" />
          )}
          <div>
            <h3 className="text-sm font-semibold text-slate-900">Quality Gate</h3>
            <p className="text-xs text-slate-600">
              Review all posts, edit inline, or regenerate flagged items before export.
            </p>
          </div>
        </div>

        {/* Summary Stats */}
        <div className="mt-3 flex gap-3 text-xs">
          <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-1">
            <span className="font-semibold text-slate-700">Total: </span>
            <span className="text-slate-900">{posts.length}</span>
          </div>
          {hasFlags && (
            <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-1">
              <span className="font-semibold text-amber-700">Flagged: </span>
              <span className="text-amber-900">{flagged.length}</span>
            </div>
          )}
          <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-1">
            <span className="font-semibold text-emerald-700">Approved: </span>
            <span className="text-emerald-900">{approved.length}</span>
          </div>
        </div>

        {/* Flagged Posts Section */}
        {hasFlags && (
          <div className="mt-4">
            <h4 className="mb-2 text-xs font-semibold text-amber-900">Flagged Posts ({flagged.length})</h4>
            <div className="space-y-2">
              {flagged.map((post) => (
                <div key={post.id} className="rounded-md border border-amber-200 bg-amber-50 p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1">
                      <div className="mb-1 flex items-center gap-2">
                        <span className="text-xs font-semibold text-amber-900">Post {post.id}</span>
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
                      <p className="line-clamp-2 text-xs text-amber-800">{post.content}</p>
                      <div className="mt-1 flex gap-3 text-xs text-amber-700">
                        {post.length && <span>{post.length} words</span>}
                        {post.readabilityScore !== undefined && (
                          <span>Readability: {post.readabilityScore.toFixed(1)}</span>
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
                className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-50"
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
            <h4 className="mb-2 text-xs font-semibold text-emerald-900">
              Approved Posts ({approved.length})
            </h4>
            <div className="space-y-2">
              {approved.map((post) => (
                <div key={post.id} className="rounded-md border border-slate-200 bg-white p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1">
                      <div className="mb-1 flex items-center gap-2">
                        <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                        <span className="text-xs font-semibold text-slate-900">Post {post.id}</span>
                      </div>
                      <p className="line-clamp-2 text-xs text-slate-700">{post.content}</p>
                      <div className="mt-1 flex gap-3 text-xs text-slate-500">
                        {post.length && <span>{post.length} words</span>}
                        {post.readabilityScore !== undefined && (
                          <span>Readability: {post.readabilityScore.toFixed(1)}</span>
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
          </div>
        )}

        {regen.error && (
          <div className="mt-3 rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">
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
              <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
                <div className="flex gap-4">
                  {editingPost.length && <span>Original: {editingPost.length} words</span>}
                  {editingPost.readabilityScore !== undefined && (
                    <span>Readability: {editingPost.readabilityScore.toFixed(1)}</span>
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
              <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">
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
