"""
Unit tests for new story service methods:
- get_available_stories_for_template
- mark_story_used_for_template
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, UTC

from backend.models import MinedStory, StoryUsage
from backend.services.story_service import story_service


def _make_story(story_id, client_id, eligible_templates=None):
    s = MagicMock(spec=MinedStory)
    s.id = story_id
    s.client_id = client_id
    s.eligible_templates = eligible_templates
    s.created_at = datetime(2025, 1, 1, tzinfo=UTC)
    return s


def _build_db(all_stories, used_ids_for_template):
    """
    Build a mock db where:
    - db.query(MinedStory).filter(...).order_by(...).all() -> all_stories
    - db.query(StoryUsage.story_id).filter(...).distinct().all() -> [(id,), ...]
    """
    db = MagicMock()

    stories_q = MagicMock()
    stories_q.filter.return_value = stories_q
    stories_q.order_by.return_value = stories_q
    stories_q.all.return_value = all_stories

    used_q = MagicMock()
    used_q.filter.return_value = used_q
    used_q.distinct.return_value = used_q
    used_q.all.return_value = [(sid,) for sid in used_ids_for_template]

    call_count = [0]

    def query_side_effect(arg):
        # First call is always MinedStory class; second is StoryUsage.story_id column
        call_count[0] += 1
        if call_count[0] == 1:
            return stories_q
        return used_q

    db.query.side_effect = query_side_effect
    return db


class TestGetAvailableStoriesForTemplate:
    """Tests for get_available_stories_for_template."""

    def test_returns_eligible_stories_not_yet_used(self):
        s1 = _make_story("s1", "c1", ["personal_story", "milestone"])
        s2 = _make_story("s2", "c1", ["personal_story"])
        db = _build_db([s1, s2], [])

        result = story_service.get_available_stories_for_template(
            db, "c1", "personal_story", "proj-1"
        )

        assert len(result) == 2

    def test_excludes_stories_already_used_for_template_and_project(self):
        s1 = _make_story("s1", "c1", ["personal_story"])
        s2 = _make_story("s2", "c1", ["personal_story"])
        db = _build_db([s1, s2], ["s1"])

        result = story_service.get_available_stories_for_template(
            db, "c1", "personal_story", "proj-1"
        )

        assert len(result) == 1
        assert s2 in result
        assert s1 not in result

    def test_does_not_exclude_story_used_for_different_template(self):
        """A usage for "milestone" should not block "personal_story"."""
        s1 = _make_story("s1", "c1", ["personal_story", "milestone"])
        # The service queries only usages matching the requested template_name,
        # so passing an empty used_ids list here mimics a query that returns nothing
        db = _build_db([s1], [])

        result = story_service.get_available_stories_for_template(
            db, "c1", "personal_story", "proj-1"
        )

        assert len(result) == 1

    def test_excludes_stories_without_eligible_templates(self):
        s1 = _make_story("s1", "c1", None)
        s2 = _make_story("s2", "c1", [])
        db = _build_db([s1, s2], [])

        result = story_service.get_available_stories_for_template(
            db, "c1", "personal_story", "proj-1"
        )

        assert result == []

    def test_excludes_stories_not_eligible_for_requested_template(self):
        s1 = _make_story("s1", "c1", ["milestone"])
        db = _build_db([s1], [])

        result = story_service.get_available_stories_for_template(
            db, "c1", "personal_story", "proj-1"
        )

        assert result == []

    def test_respects_limit(self):
        stories = [_make_story(f"s{i}", "c1", ["personal_story"]) for i in range(10)]
        db = _build_db(stories, [])

        result = story_service.get_available_stories_for_template(
            db, "c1", "personal_story", "proj-1", limit=3
        )

        assert len(result) == 3

    def test_returns_empty_when_no_stories(self):
        db = _build_db([], [])
        result = story_service.get_available_stories_for_template(
            db, "c1", "personal_story", "proj-1"
        )
        assert result == []


class TestMarkStoryUsedForTemplate:
    """Tests for mark_story_used_for_template."""

    def test_creates_usage_record(self):
        db = MagicMock()

        result = story_service.mark_story_used_for_template(
            db, story_id="s1", template_name="personal_story", project_id="proj-1"
        )

        db.add.assert_called_once()
        db.commit.assert_called_once()

    def test_idempotent_on_duplicate(self):
        from sqlalchemy.exc import IntegrityError

        db = MagicMock()
        db.commit.side_effect = IntegrityError("UNIQUE", {}, None)
        db.rollback = MagicMock()

        result = story_service.mark_story_used_for_template(
            db, story_id="s1", template_name="personal_story", project_id="proj-1"
        )

        assert result is None
        db.rollback.assert_called_once()
