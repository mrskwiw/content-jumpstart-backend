/**
 * Pure helpers for the ContentReview page (kept out of the component file so React Fast
 * Refresh works — a component module must only export components).
 */

// A compact badge for a post's team-review state (COLLAB-01), or null when it was never
// submitted for review (so an unreviewed post isn't implied to have been reviewed).
export function approvalBadge(status?: string | null): { label: string; cls: string } | null {
  switch (status) {
    case 'approved':
      return { label: 'Review: approved', cls: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300' };
    case 'pending':
      return { label: 'Review: pending', cls: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300' };
    case 'rejected':
      return { label: 'Review: rejected', cls: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300' };
    default:
      return null;
  }
}
