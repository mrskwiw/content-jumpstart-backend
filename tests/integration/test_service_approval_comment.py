"""Direct service-layer tests for approval_service + comment_service (AUDIT-01 T1).

COLLAB-01's approval/comment services previously had only router-level (HTTP) coverage —
nothing exercised the service functions directly, including the resubmit-reopens-review
transition (Decision #215) and the not-awaiting-approval guard. These call the services
straight, with a real DB session and a real Post (access checks live in the router, so they
are out of scope here).
"""

import pytest

from backend.models.post_approval import APPROVAL_APPROVED, APPROVAL_PENDING, APPROVAL_REJECTED
from backend.services import approval_service, comment_service

# Reuse the proven client→project→run→post + user setup rather than duplicate it.
from tests.integration.test_collab_approvals import _mk_post, _mk_user


# ── approval_service ──────────────────────────────────────────────────────────


def test_submit_creates_a_pending_approval(db_session):
    owner = _mk_user(db_session, "svc-ap-1", "svcap1@example.com")
    post = _mk_post(db_session, owner)

    assert approval_service.get_approval(db_session, post.id) is None
    approval = approval_service.submit_for_approval(db_session, post.id, owner.id)

    assert approval.status == APPROVAL_PENDING
    assert approval.submitted_by_user_id == owner.id
    assert approval.decided_by_user_id is None
    assert approval.decided_at is None


def test_decide_approve_records_the_decider_and_note(db_session):
    owner = _mk_user(db_session, "svc-ap-2", "svcap2@example.com")
    post = _mk_post(db_session, owner)
    approval_service.submit_for_approval(db_session, post.id, owner.id)

    decided = approval_service.decide(db_session, post.id, owner.id, approve=True, note="LGTM")
    assert decided.status == APPROVAL_APPROVED
    assert decided.decided_by_user_id == owner.id
    assert decided.decided_at is not None
    assert decided.note == "LGTM"


def test_decide_reject_sets_rejected_with_note(db_session):
    owner = _mk_user(db_session, "svc-ap-3", "svcap3@example.com")
    post = _mk_post(db_session, owner)
    approval_service.submit_for_approval(db_session, post.id, owner.id)

    decided = approval_service.decide(
        db_session, post.id, owner.id, approve=False, note="tighten the hook"
    )
    assert decided.status == APPROVAL_REJECTED
    assert decided.note == "tighten the hook"


def test_resubmit_after_reject_reopens_review(db_session):
    owner = _mk_user(db_session, "svc-ap-4", "svcap4@example.com")
    editor = _mk_user(db_session, "svc-ap-4e", "svcap4e@example.com")
    post = _mk_post(db_session, owner)
    approval_service.submit_for_approval(db_session, post.id, owner.id)
    approval_service.decide(db_session, post.id, owner.id, approve=False, note="no")

    reopened = approval_service.submit_for_approval(db_session, post.id, editor.id)
    assert reopened.status == APPROVAL_PENDING
    assert reopened.submitted_by_user_id == editor.id
    assert reopened.decided_by_user_id is None  # decision cleared
    assert reopened.note is None


def test_resubmit_after_approve_reopens_review_decision_215(db_session):
    # Decision #215 mechanism: submitting an already-APPROVED post reopens review, so approval
    # cannot outlive a content change. This is the SERVICE contract the review workflow relies
    # on — resubmit after an edit is driven by that workflow calling submit_for_approval; the
    # backend edit path does not itself auto-reopen (by design), so this tests the reopen
    # mechanism, not an edit trigger.
    owner = _mk_user(db_session, "svc-ap-5", "svcap5@example.com")
    post = _mk_post(db_session, owner)
    approval_service.submit_for_approval(db_session, post.id, owner.id)
    approval_service.decide(db_session, post.id, owner.id, approve=True)

    reopened = approval_service.submit_for_approval(db_session, post.id, owner.id)
    assert reopened.status == APPROVAL_PENDING
    assert reopened.decided_at is None


def test_decide_rejects_a_post_not_awaiting_approval(db_session):
    owner = _mk_user(db_session, "svc-ap-6", "svcap6@example.com")
    post = _mk_post(db_session, owner)

    # No approval record yet → cannot decide.
    with pytest.raises(approval_service.ApprovalError):
        approval_service.decide(db_session, post.id, owner.id, approve=True)

    # Already decided (approved) → not pending → cannot decide again without a resubmit.
    approval_service.submit_for_approval(db_session, post.id, owner.id)
    approval_service.decide(db_session, post.id, owner.id, approve=True)
    with pytest.raises(approval_service.ApprovalError):
        approval_service.decide(db_session, post.id, owner.id, approve=False)


# ── comment_service ───────────────────────────────────────────────────────────


def test_add_and_list_comments_ordered_by_created_at(db_session):
    from datetime import datetime, timedelta, timezone

    owner = _mk_user(db_session, "svc-cm-1", "svccm1@example.com")
    post = _mk_post(db_session, owner)

    assert comment_service.list_comments(db_session, post.id) == []
    c1 = comment_service.add_comment(db_session, post.id, owner.id, "first")
    c2 = comment_service.add_comment(db_session, post.id, owner.id, "second")

    # add_comment persists a real creation time (the model default fires on the write path).
    assert c1.created_at is not None and c2.created_at is not None

    # Seed DISTINCT timestamps so the created_at ordering is deterministic regardless of the
    # backend's clock resolution — SQLite's CURRENT_TIMESTAMP is only second-precision, so two
    # back-to-back inserts can collide and make a strict insertion-order assertion flaky.
    base = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    c1.created_at = base
    c2.created_at = base + timedelta(minutes=1)
    db_session.commit()

    listed = comment_service.list_comments(db_session, post.id)
    assert [c.id for c in listed] == [c1.id, c2.id]  # ascending by created_at
    assert listed[0].body == "first" and listed[0].author_user_id == owner.id

    # Ordering follows created_at, not insertion: make c2 the earlier row and it leads.
    c2.created_at = base - timedelta(minutes=1)
    db_session.commit()
    assert [c.id for c in comment_service.list_comments(db_session, post.id)] == [c2.id, c1.id]


def test_get_and_delete_comment(db_session):
    owner = _mk_user(db_session, "svc-cm-2", "svccm2@example.com")
    post = _mk_post(db_session, owner)
    comment = comment_service.add_comment(db_session, post.id, owner.id, "to be removed")

    assert comment_service.get_comment(db_session, comment.id).id == comment.id
    comment_service.delete_comment(db_session, comment)
    assert comment_service.get_comment(db_session, comment.id) is None
    assert comment_service.list_comments(db_session, post.id) == []
