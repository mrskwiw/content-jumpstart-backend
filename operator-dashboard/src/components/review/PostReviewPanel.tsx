import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  CheckCircle2,
  XCircle,
  Clock,
  Send,
  Trash2,
  MessageSquare,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import { toast } from 'sonner';
import { reviewApi } from '@/api/review';
import { teamsApi } from '@/api/teams';
import { useAuth } from '@/contexts/AuthContext';
import type { ApprovalStatus, PostApproval, PostComment } from '@/types/review';

function errorDetail(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
  return typeof detail === 'string' ? detail : fallback;
}

function statusBadge(status: ApprovalStatus) {
  switch (status) {
    case 'approved':
      return {
        cls: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300',
        icon: <CheckCircle2 className="h-3.5 w-3.5" />,
        label: 'Approved',
      };
    case 'rejected':
      return {
        cls: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
        icon: <XCircle className="h-3.5 w-3.5" />,
        label: 'Changes requested',
      };
    default:
      return {
        cls: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
        icon: <Clock className="h-3.5 w-3.5" />,
        label: 'Pending review',
      };
  }
}

/**
 * Team review controls for a single post (COLLAB-01, GAP-UI-03): the approval gate
 * plus a comment thread. Control visibility mirrors the backend's team-scoped rules
 * (a solo/legacy user is treated as the manager of their own content); any residual
 * 403/400 still surfaces as a toast.
 */
export default function PostReviewPanel({ postId }: { postId: string }) {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [commentBody, setCommentBody] = useState('');
  // Deferred by default: on a review page that can render hundreds of posts, fetching
  // approval + comments for every card up front is a network fan-out. The panel only
  // loads its state when the reviewer opens it (queries are `enabled: expanded`).
  const [expanded, setExpanded] = useState(false);

  const approvalKey = ['approval', postId] as const;
  const commentsKey = ['comments', postId] as const;

  // The team lookup shares one query key across every mounted panel, so React Query
  // dedupes it to a single request regardless of how many posts are on the page.
  const { data: team } = useQuery({
    queryKey: ['team', 'me'],
    queryFn: () => teamsApi.getMyTeam(),
    enabled: expanded,
  });
  const { data: approval } = useQuery<PostApproval | null>({
    queryKey: approvalKey,
    queryFn: () => reviewApi.getApproval(postId),
    enabled: expanded,
  });
  const { data: comments = [] } = useQuery<PostComment[]>({
    queryKey: commentsKey,
    queryFn: () => reviewApi.listComments(postId),
    enabled: expanded,
  });

  // Solo/legacy users (no team) are the manager of their own content per the backend
  // creator fallback; otherwise owner/admin manage and viewers are read-only.
  const myRole = team?.team?.my_role ?? null;
  const canManage = myRole === null || myRole === 'owner' || myRole === 'admin';
  const canSubmit = myRole !== 'viewer';

  const onError = (fallback: string) => (err: unknown) => toast.error(errorDetail(err, fallback));
  const invalidateApproval = () => queryClient.invalidateQueries({ queryKey: approvalKey });

  const submit = useMutation({
    mutationFn: () => reviewApi.submitForApproval(postId),
    onSuccess: () => {
      invalidateApproval();
      toast.success('Submitted for review');
    },
    onError: onError('Failed to submit for review'),
  });
  const approve = useMutation({
    mutationFn: () => reviewApi.approve(postId),
    onSuccess: () => {
      invalidateApproval();
      toast.success('Post approved');
    },
    onError: onError('Failed to approve'),
  });
  const reject = useMutation({
    mutationFn: () => reviewApi.reject(postId),
    onSuccess: () => {
      invalidateApproval();
      toast.success('Changes requested');
    },
    onError: onError('Failed to reject'),
  });
  const addComment = useMutation({
    mutationFn: (body: string) => reviewApi.addComment(postId, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: commentsKey });
      setCommentBody('');
    },
    onError: onError('Failed to add comment'),
  });
  const deleteComment = useMutation({
    mutationFn: (commentId: string) => reviewApi.deleteComment(commentId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: commentsKey }),
    onError: onError('Failed to delete comment'),
  });

  const status = approval?.status ?? null;
  const badge = status ? statusBadge(status) : null;
  const isPending = submit.isPending || approve.isPending || reject.isPending;

  return (
    <div className="rounded-lg border border-neutral-200 bg-neutral-50/60 dark:border-neutral-700 dark:bg-neutral-800/40">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
        className="flex w-full items-center gap-1.5 px-4 py-2.5 text-left text-sm font-medium text-neutral-700 hover:bg-neutral-100/60 dark:text-neutral-200 dark:hover:bg-neutral-700/30"
      >
        {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        <MessageSquare className="h-4 w-4" /> Review &amp; comments
      </button>

      {expanded && (
        <div className="space-y-4 border-t border-neutral-200 p-4 dark:border-neutral-700">
          {/* Approval gate */}
          <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm font-medium text-neutral-700 dark:text-neutral-200">
          Review status
          {badge ? (
            <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${badge.cls}`}>
              {badge.icon}
              {badge.label}
            </span>
          ) : (
            <span className="text-xs text-neutral-500 dark:text-neutral-400">Not submitted</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {canSubmit && status !== 'pending' && (
            <button
              type="button"
              onClick={() => submit.mutate()}
              disabled={isPending}
              className="inline-flex items-center gap-1 rounded-md bg-primary-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-primary-700 disabled:opacity-50"
            >
              <Send className="h-3.5 w-3.5" /> Submit for review
            </button>
          )}
          {canManage && status === 'pending' && (
            <>
              <button
                type="button"
                onClick={() => approve.mutate()}
                disabled={isPending}
                className="inline-flex items-center gap-1 rounded-md bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
              >
                <CheckCircle2 className="h-3.5 w-3.5" /> Approve
              </button>
              <button
                type="button"
                onClick={() => reject.mutate()}
                disabled={isPending}
                className="inline-flex items-center gap-1 rounded-md border border-red-300 px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-50 disabled:opacity-50 dark:border-red-700 dark:text-red-400 dark:hover:bg-red-900/20"
              >
                <XCircle className="h-3.5 w-3.5" /> Request changes
              </button>
            </>
          )}
        </div>
      </div>

      {/* Comments */}
      <div className="space-y-3 border-t border-neutral-200 pt-3 dark:border-neutral-700">
        <div className="flex items-center gap-1.5 text-sm font-medium text-neutral-700 dark:text-neutral-200">
          <MessageSquare className="h-4 w-4" /> Comments
          <span className="text-xs font-normal text-neutral-400">({comments.length})</span>
        </div>

        <ul className="space-y-2">
          {comments.map((c) => (
            <li
              key={c.id}
              className="group flex items-start justify-between gap-2 rounded-md bg-white px-3 py-2 text-sm dark:bg-neutral-900"
            >
              <div>
                <div className="text-xs text-neutral-500 dark:text-neutral-400">
                  {c.author_email ?? 'Unknown'}
                </div>
                <div className="whitespace-pre-wrap text-neutral-800 dark:text-neutral-100">{c.body}</div>
              </div>
              {(c.author_user_id === user?.id || canManage) && (
                <button
                  type="button"
                  aria-label="Delete comment"
                  onClick={() => deleteComment.mutate(c.id)}
                  disabled={deleteComment.isPending}
                  className="text-neutral-400 opacity-0 transition hover:text-red-600 group-hover:opacity-100 disabled:opacity-50 dark:hover:text-red-400"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              )}
            </li>
          ))}
          {comments.length === 0 && (
            <li className="text-xs text-neutral-400 dark:text-neutral-500">No comments yet.</li>
          )}
        </ul>

        <form
          className="flex items-start gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            const body = commentBody.trim();
            if (body) addComment.mutate(body);
          }}
        >
          <textarea
            value={commentBody}
            onChange={(e) => setCommentBody(e.target.value)}
            placeholder="Leave a comment…"
            rows={2}
            className="flex-1 rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 dark:border-neutral-600 dark:bg-neutral-800 dark:text-neutral-100"
          />
          <button
            type="submit"
            disabled={addComment.isPending || !commentBody.trim()}
            className="rounded-md bg-primary-600 px-3 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
          >
            Post
          </button>
        </form>
          </div>
        </div>
      )}
    </div>
  );
}
