// Post review types (COLLAB-01, GAP-UI-03) — mirror the comments/approval backend contract.

/** A single review comment on a post. */
export interface PostComment {
  id: string;
  post_id: string;
  author_user_id: string;
  author_email: string | null;
  body: string;
  created_at: string;
}

export type ApprovalStatus = 'pending' | 'approved' | 'rejected';

/** A post's approval-gate state. `null` from the API means never submitted. */
export interface PostApproval {
  post_id: string;
  status: ApprovalStatus;
  submitted_by_user_id: string;
  decided_by_user_id: string | null;
  decided_at: string | null;
  note: string | null;
}
