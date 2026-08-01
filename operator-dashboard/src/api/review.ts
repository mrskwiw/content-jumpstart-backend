/**
 * Post review API client (COLLAB-01, GAP-UI-03) — comments + approval gate.
 *
 * The backend enforces team-scoped authorization; the UI surfaces any 403/400 via the
 * caller's error handler rather than gating controls preemptively.
 */
import apiClient from './client';
import type { PostApproval, PostComment } from '@/types/review';

export const reviewApi = {
  // ── Comments ───────────────────────────────────────────────────────────────
  /** List a post's review comments (any team member). */
  async listComments(postId: string): Promise<PostComment[]> {
    const { data } = await apiClient.get<PostComment[]>(`/api/posts/${postId}/comments`);
    return data;
  },

  /** Add a comment to a post (any team member). */
  async addComment(postId: string, body: string): Promise<PostComment> {
    const { data } = await apiClient.post<PostComment>(`/api/posts/${postId}/comments`, { body });
    return data;
  },

  /** Delete a comment (its author, a team manager, or a superuser). */
  async deleteComment(commentId: string): Promise<void> {
    await apiClient.delete(`/api/comments/${commentId}`);
  },

  // ── Approval gate ──────────────────────────────────────────────────────────
  /** The post's approval state, or `null` if it was never submitted. */
  async getApproval(postId: string): Promise<PostApproval | null> {
    const { data } = await apiClient.get<PostApproval | null>(`/api/posts/${postId}/approval`);
    return data;
  },

  /** Submit a post for team review (editor+ → pending). */
  async submitForApproval(postId: string): Promise<PostApproval> {
    const { data } = await apiClient.post<PostApproval>(`/api/posts/${postId}/approval/submit`);
    return data;
  },

  /** Approve a pending post (owner/admin only). */
  async approve(postId: string, note?: string): Promise<PostApproval> {
    const { data } = await apiClient.post<PostApproval>(`/api/posts/${postId}/approval/approve`, {
      note: note ?? null,
    });
    return data;
  },

  /** Reject a pending post (owner/admin only). */
  async reject(postId: string, note?: string): Promise<PostApproval> {
    const { data } = await apiClient.post<PostApproval>(`/api/posts/${postId}/approval/reject`, {
      note: note ?? null,
    });
    return data;
  },
};
