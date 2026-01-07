"""Project Database Layer

Handles all database operations for projects, revisions, and scope tracking.
Uses SQLite for local storage with future option for PostgreSQL.
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ..models.client_memory import ClientMemory, FeedbackTheme, VoiceSample
from ..models.project import (
    Project,
    ProjectStatus,
    Revision,
    RevisionPost,
    RevisionScope,
    RevisionStatus,
)
from ..models.voice_sample import VoiceSampleUpload


class ProjectDatabase:
    """Database operations for project and revision management"""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize database connection

        Args:
            db_path: Path to SQLite database file. Defaults to data/projects.db
        """
        if db_path is None:
            # Use current working directory as base
            db_path = Path.cwd() / "data" / "projects.db"

        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database schema
        self._init_schema()

    def _init_schema(self):
        """Initialize database schema from schema.sql"""
        schema_path = Path(__file__).parent / "schema.sql"

        with self._get_connection() as conn:
            with open(schema_path, "r", encoding="utf-8") as f:
                schema_sql = f.read()
                conn.executescript(schema_sql)
            conn.commit()

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        try:
            yield conn
        finally:
            conn.close()

    # ============================================================================
    # PROJECT OPERATIONS
    # ============================================================================

    def create_project(self, project: Project) -> bool:
        """Create a new project

        Args:
            project: Project instance

        Returns:
            True if created successfully
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    INSERT INTO projects (
                        project_id, client_name, created_at, deliverable_path,
                        brief_path, num_posts, quality_profile_name, status, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        project.project_id,
                        project.client_name,
                        project.created_at.isoformat(),
                        project.deliverable_path,
                        project.brief_path,
                        project.num_posts,
                        project.quality_profile_name,
                        project.status.value,
                        project.notes,
                    ),
                )

                # Initialize revision scope
                scope = RevisionScope(project_id=project.project_id)
                cursor.execute(
                    """
                    INSERT INTO revision_scope (
                        project_id, allowed_revisions, used_revisions,
                        remaining_revisions, scope_exceeded, upsell_offered, upsell_accepted
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        scope.project_id,
                        scope.allowed_revisions,
                        scope.used_revisions,
                        scope.remaining_revisions,
                        scope.scope_exceeded,
                        scope.upsell_offered,
                        scope.upsell_accepted,
                    ),
                )

                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def get_project(self, project_id: str) -> Optional[Project]:
        """Get project by ID

        Args:
            project_id: Project identifier

        Returns:
            Project instance or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects WHERE project_id = ?", (project_id,))
            row = cursor.fetchone()

            if row:
                return Project.from_dict(dict(row))
            return None

    def get_projects_by_client(self, client_name: str) -> List[Project]:
        """Get all projects for a client

        Args:
            client_name: Client name

        Returns:
            List of Project instances
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM projects WHERE client_name = ? ORDER BY created_at DESC",
                (client_name,),
            )
            rows = cursor.fetchall()
            return [Project.from_dict(dict(row)) for row in rows]

    def get_projects(self, limit: int = 100) -> List[Dict]:
        """Get all projects with optional limit

        Args:
            limit: Maximum number of projects to return

        Returns:
            List of project dictionaries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM projects ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def update_project_status(self, project_id: str, status: ProjectStatus) -> bool:
        """Update project status

        Args:
            project_id: Project identifier
            status: New status

        Returns:
            True if updated successfully
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE projects SET status = ? WHERE project_id = ?", (status.value, project_id)
            )
            conn.commit()
            return cursor.rowcount > 0

    # ============================================================================
    # REVISION OPERATIONS
    # ============================================================================

    def create_revision(self, revision: Revision) -> bool:
        """Create a new revision request

        Args:
            revision: Revision instance

        Returns:
            True if created successfully
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                # Insert revision
                cursor.execute(
                    """
                    INSERT INTO revisions (
                        revision_id, project_id, attempt_number, status,
                        feedback, created_at, completed_at, cost
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        revision.revision_id,
                        revision.project_id,
                        revision.attempt_number,
                        revision.status.value,
                        revision.feedback,
                        revision.created_at.isoformat(),
                        revision.completed_at.isoformat() if revision.completed_at else None,
                        revision.cost,
                    ),
                )

                # Update revision scope
                cursor.execute(
                    """
                    UPDATE revision_scope
                    SET used_revisions = used_revisions + 1,
                        remaining_revisions = allowed_revisions - (used_revisions + 1),
                        scope_exceeded = CASE
                            WHEN (used_revisions + 1) > allowed_revisions THEN 1
                            ELSE 0
                        END
                    WHERE project_id = ?
                """,
                    (revision.project_id,),
                )

                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def get_revision(self, revision_id: str) -> Optional[Revision]:
        """Get revision by ID

        Args:
            revision_id: Revision identifier

        Returns:
            Revision instance or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM revisions WHERE revision_id = ?", (revision_id,))
            row = cursor.fetchone()

            if row:
                revision = Revision.from_dict(dict(row))

                # Load revision posts
                cursor.execute("SELECT * FROM revision_posts WHERE revision_id = ?", (revision_id,))
                post_rows = cursor.fetchall()
                revision.posts = [self._row_to_revision_post(dict(r)) for r in post_rows]

                return revision
            return None

    def get_revisions_by_project(self, project_id: str) -> List[Revision]:
        """Get all revisions for a project

        Args:
            project_id: Project identifier

        Returns:
            List of Revision instances
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM revisions WHERE project_id = ? ORDER BY attempt_number",
                (project_id,),
            )
            rows = cursor.fetchall()
            revisions = []
            for row in rows:
                revision = Revision.from_dict(dict(row))

                # Load posts for this revision
                cursor.execute(
                    "SELECT * FROM revision_posts WHERE revision_id = ?", (revision.revision_id,)
                )
                post_rows = cursor.fetchall()
                revision.posts = [self._row_to_revision_post(dict(r)) for r in post_rows]

                revisions.append(revision)

            return revisions

    def update_revision_status(
        self, revision_id: str, status: RevisionStatus, completed_at: Optional[datetime] = None
    ) -> bool:
        """Update revision status

        Args:
            revision_id: Revision identifier
            status: New status
            completed_at: Completion timestamp (defaults to now if status is completed)

        Returns:
            True if updated successfully
        """
        if status in [RevisionStatus.COMPLETED, RevisionStatus.FAILED] and completed_at is None:
            completed_at = datetime.now()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE revisions
                SET status = ?, completed_at = ?
                WHERE revision_id = ?
            """,
                (status.value, completed_at.isoformat() if completed_at else None, revision_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_revision_posts(self, revision_id: str) -> List[Dict]:
        """Get posts for a specific revision

        Args:
            revision_id: Revision ID

        Returns:
            List of revision post dictionaries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM revision_posts
                WHERE revision_id = ?
                ORDER BY post_index
            """,
                (revision_id,),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def save_revision_posts(self, revision_id: str, posts: List[RevisionPost]) -> bool:
        """Save revised posts

        Args:
            revision_id: Revision identifier
            posts: List of RevisionPost instances

        Returns:
            True if saved successfully
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for post in posts:
                cursor.execute(
                    """
                    INSERT INTO revision_posts (
                        revision_id, post_index, template_id, template_name,
                        original_content, original_word_count,
                        revised_content, revised_word_count, changes_summary
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        revision_id,
                        post.post_index,
                        post.template_id,
                        post.template_name,
                        post.original_content,
                        post.original_word_count,
                        post.revised_content,
                        post.revised_word_count,
                        post.changes_summary,
                    ),
                )
            conn.commit()
            return True

    # ============================================================================
    # REVISION SCOPE OPERATIONS
    # ============================================================================

    def get_revision_scope(self, project_id: str) -> Optional[RevisionScope]:
        """Get revision scope for a project

        Args:
            project_id: Project identifier

        Returns:
            RevisionScope instance or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM revision_scope WHERE project_id = ?", (project_id,))
            row = cursor.fetchone()

            if row:
                return RevisionScope.from_dict(dict(row))
            return None

    def update_revision_scope(self, scope: RevisionScope) -> bool:
        """Update revision scope

        Args:
            scope: RevisionScope instance

        Returns:
            True if updated successfully
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE revision_scope
                SET allowed_revisions = ?,
                    used_revisions = ?,
                    remaining_revisions = ?,
                    scope_exceeded = ?,
                    upsell_offered = ?,
                    upsell_accepted = ?
                WHERE project_id = ?
            """,
                (
                    scope.allowed_revisions,
                    scope.used_revisions,
                    scope.remaining_revisions,
                    scope.scope_exceeded,
                    scope.upsell_offered,
                    scope.upsell_accepted,
                    scope.project_id,
                ),
            )
            conn.commit()
            return cursor.rowcount > 0

    def mark_upsell_offered(self, project_id: str) -> bool:
        """Mark that upsell has been offered

        Args:
            project_id: Project identifier

        Returns:
            True if updated successfully
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE revision_scope SET upsell_offered = 1 WHERE project_id = ?", (project_id,)
            )
            conn.commit()
            return cursor.rowcount > 0

    def accept_upsell(self, project_id: str, additional_revisions: int = 5) -> bool:
        """Accept upsell and add more revisions

        Args:
            project_id: Project identifier
            additional_revisions: Number of revisions to add

        Returns:
            True if updated successfully
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE revision_scope
                SET allowed_revisions = allowed_revisions + ?,
                    remaining_revisions = (allowed_revisions + ?) - used_revisions,
                    upsell_accepted = 1,
                    scope_exceeded = 0
                WHERE project_id = ?
            """,
                (additional_revisions, additional_revisions, project_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    # ============================================================================
    # ANALYTICS & REPORTING
    # ============================================================================

    def get_client_stats(self, client_name: str) -> Dict:
        """Get statistics for a client

        Args:
            client_name: Client name

        Returns:
            Dictionary with client statistics
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Total projects
            cursor.execute(
                "SELECT COUNT(*) as count FROM projects WHERE client_name = ?", (client_name,)
            )
            total_projects = cursor.fetchone()["count"]

            # Total revisions
            cursor.execute(
                """
                SELECT COUNT(*) as count FROM revisions
                WHERE project_id IN (
                    SELECT project_id FROM projects WHERE client_name = ?
                )
            """,
                (client_name,),
            )
            total_revisions = cursor.fetchone()["count"]

            # Average revisions per project
            avg_revisions = total_revisions / total_projects if total_projects > 0 else 0

            # Scope exceeded count
            cursor.execute(
                """
                SELECT COUNT(*) as count FROM revision_scope
                WHERE project_id IN (
                    SELECT project_id FROM projects WHERE client_name = ?
                ) AND scope_exceeded = 1
            """,
                (client_name,),
            )
            scope_exceeded_count = cursor.fetchone()["count"]

            return {
                "client_name": client_name,
                "total_projects": total_projects,
                "total_revisions": total_revisions,
                "avg_revisions_per_project": round(avg_revisions, 2),
                "scope_exceeded_count": scope_exceeded_count,
            }

    def get_revision_summary(self) -> List[Dict]:
        """Get revision summary across all projects

        Returns:
            List of project revision summaries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM project_revision_status")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    # ============================================================================
    # CLIENT MEMORY OPERATIONS (Phase 8B)
    # ============================================================================

    def get_client_memory(self, client_name: str) -> Optional["ClientMemory"]:
        """Get client memory by name

        Args:
            client_name: Client name

        Returns:
            ClientMemory instance or None if not found
        """
        from ..models.client_memory import ClientMemory

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM client_history WHERE client_name = ?", (client_name,))
            row = cursor.fetchone()

            if row:
                return ClientMemory.from_dict(dict(row))
            return None

    def create_client_memory(self, memory: "ClientMemory") -> bool:
        """Create new client memory record

        Args:
            memory: ClientMemory instance

        Returns:
            True if created successfully
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                data = memory.to_dict()
                cursor.execute(
                    """
                    INSERT INTO client_history (
                        client_name, first_project_date, last_project_date,
                        total_projects, total_posts_generated, total_revisions,
                        lifetime_value, average_satisfaction, notes,
                        preferred_templates, avoided_templates, voice_adjustments,
                        optimal_word_count_min, optimal_word_count_max, preferred_cta_types,
                        voice_archetype, average_readability_score, signature_phrases,
                        custom_quality_profile_json, next_project_discount, last_updated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        data["client_name"],
                        data["first_project_date"],
                        data["last_project_date"],
                        data["total_projects"],
                        data["total_posts_generated"],
                        data["total_revisions"],
                        data["lifetime_value"],
                        data["average_satisfaction"],
                        data["notes"],
                        data["preferred_templates"],
                        data["avoided_templates"],
                        data["voice_adjustments"],
                        data["optimal_word_count_min"],
                        data["optimal_word_count_max"],
                        data["preferred_cta_types"],
                        data["voice_archetype"],
                        data["average_readability_score"],
                        data["signature_phrases"],
                        data["custom_quality_profile_json"],
                        data["next_project_discount"],
                        data["last_updated"],
                    ),
                )
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def update_client_memory(self, memory: "ClientMemory") -> bool:
        """Update existing client memory

        Args:
            memory: ClientMemory instance

        Returns:
            True if updated successfully
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            data = memory.to_dict()
            cursor.execute(
                """
                UPDATE client_history SET
                    first_project_date = ?,
                    last_project_date = ?,
                    total_projects = ?,
                    total_posts_generated = ?,
                    total_revisions = ?,
                    lifetime_value = ?,
                    average_satisfaction = ?,
                    notes = ?,
                    preferred_templates = ?,
                    avoided_templates = ?,
                    voice_adjustments = ?,
                    optimal_word_count_min = ?,
                    optimal_word_count_max = ?,
                    preferred_cta_types = ?,
                    voice_archetype = ?,
                    average_readability_score = ?,
                    signature_phrases = ?,
                    custom_quality_profile_json = ?,
                    next_project_discount = ?,
                    last_updated = ?
                WHERE client_name = ?
            """,
                (
                    data["first_project_date"],
                    data["last_project_date"],
                    data["total_projects"],
                    data["total_posts_generated"],
                    data["total_revisions"],
                    data["lifetime_value"],
                    data["average_satisfaction"],
                    data["notes"],
                    data["preferred_templates"],
                    data["avoided_templates"],
                    data["voice_adjustments"],
                    data["optimal_word_count_min"],
                    data["optimal_word_count_max"],
                    data["preferred_cta_types"],
                    data["voice_archetype"],
                    data["average_readability_score"],
                    data["signature_phrases"],
                    data["custom_quality_profile_json"],
                    data["next_project_discount"],
                    data["last_updated"],
                    data["client_name"],
                ),
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_or_create_client_memory(self, client_name: str) -> "ClientMemory":
        """Get existing client memory or create new one

        Args:
            client_name: Client name

        Returns:
            ClientMemory instance
        """
        from ..models.client_memory import ClientMemory

        memory = self.get_client_memory(client_name)
        if memory is None:
            memory = ClientMemory(client_name=client_name)
            self.create_client_memory(memory)
        return memory

    def store_voice_sample(self, voice_sample: "VoiceSample") -> bool:
        """Store voice analysis from a project

        Args:
            voice_sample: VoiceSample instance

        Returns:
            True if stored successfully
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            data = voice_sample.to_dict()
            cursor.execute(
                """
                INSERT INTO client_voice_samples (
                    client_name, project_id, generated_at,
                    average_readability, voice_archetype, dominant_tone,
                    average_word_count, question_usage_rate,
                    common_hooks, common_transitions, common_ctas, key_phrases
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    data["client_name"],
                    data["project_id"],
                    data["generated_at"],
                    data["average_readability"],
                    data["voice_archetype"],
                    data["dominant_tone"],
                    data["average_word_count"],
                    data["question_usage_rate"],
                    data["common_hooks"],
                    data["common_transitions"],
                    data["common_ctas"],
                    data["key_phrases"],
                ),
            )
            conn.commit()
            return True

    def get_voice_samples(self, client_name: str, limit: int = 5) -> List["VoiceSample"]:
        """Get recent voice samples for a client

        Args:
            client_name: Client name
            limit: Maximum number of samples to return

        Returns:
            List of VoiceSample instances (most recent first)
        """
        from ..models.client_memory import VoiceSample

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM client_voice_samples
                WHERE client_name = ?
                ORDER BY generated_at DESC
                LIMIT ?
            """,
                (client_name, limit),
            )
            rows = cursor.fetchall()
            return [VoiceSample.from_dict(dict(row)) for row in rows]

    # Phase 8C: Voice Sample Upload Methods

    def store_voice_sample_upload(self, voice_sample: "VoiceSampleUpload") -> int:
        """
        Store client-uploaded voice sample

        Args:
            voice_sample: VoiceSampleUpload instance

        Returns:
            ID of stored sample
        """

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO voice_sample_uploads (
                    client_name, sample_text, sample_source,
                    word_count, file_name
                ) VALUES (?, ?, ?, ?, ?)
            """,
                (
                    voice_sample.client_name,
                    voice_sample.sample_text,
                    voice_sample.sample_source,
                    voice_sample.word_count,
                    voice_sample.file_name,
                ),
            )
            conn.commit()

            # Update client_history to mark has_voice_samples
            cursor.execute(
                """
                UPDATE client_history
                SET has_voice_samples = 1,
                    voice_samples_upload_date = CURRENT_TIMESTAMP
                WHERE client_name = ?
            """,
                (voice_sample.client_name,),
            )
            conn.commit()

            return cursor.lastrowid

    def get_voice_sample_uploads(
        self, client_name: str, limit: Optional[int] = None
    ) -> List["VoiceSampleUpload"]:
        """
        Get client-uploaded voice samples

        Args:
            client_name: Client name
            limit: Maximum number of samples to return (None = all)

        Returns:
            List of VoiceSampleUpload instances
        """
        from ..models.voice_sample import VoiceSampleUpload

        with self._get_connection() as conn:
            cursor = conn.cursor()

            if limit:
                cursor.execute(
                    """
                    SELECT * FROM voice_sample_uploads
                    WHERE client_name = ?
                    ORDER BY upload_date DESC
                    LIMIT ?
                """,
                    (client_name, limit),
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM voice_sample_uploads
                    WHERE client_name = ?
                    ORDER BY upload_date DESC
                """,
                    (client_name,),
                )

            rows = cursor.fetchall()
            return [VoiceSampleUpload.from_dict(dict(row)) for row in rows]

    def delete_voice_sample_uploads(self, client_name: str) -> int:
        """
        Delete all voice sample uploads for a client

        Args:
            client_name: Client name

        Returns:
            Number of samples deleted
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Get count before deleting
            cursor.execute(
                """
                SELECT COUNT(*) FROM voice_sample_uploads
                WHERE client_name = ?
            """,
                (client_name,),
            )
            count = cursor.fetchone()[0]

            # Delete samples
            cursor.execute(
                """
                DELETE FROM voice_sample_uploads
                WHERE client_name = ?
            """,
                (client_name,),
            )

            # Update client_history
            cursor.execute(
                """
                UPDATE client_history
                SET has_voice_samples = 0,
                    voice_samples_upload_date = NULL
                WHERE client_name = ?
            """,
                (client_name,),
            )

            conn.commit()
            return count

    def get_voice_sample_upload_stats(self, client_name: str) -> dict:
        """
        Get statistics about client's uploaded voice samples

        Args:
            client_name: Client name

        Returns:
            Dictionary with stats (count, total_words, sources, upload_date)
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    COUNT(*) as sample_count,
                    SUM(word_count) as total_words,
                    GROUP_CONCAT(DISTINCT sample_source) as sources,
                    MAX(upload_date) as last_upload
                FROM voice_sample_uploads
                WHERE client_name = ?
            """,
                (client_name,),
            )

            row = cursor.fetchone()
            if row and row["sample_count"] > 0:
                return {
                    "sample_count": row["sample_count"],
                    "total_words": row["total_words"],
                    "sources": row["sources"].split(",") if row["sources"] else [],
                    "last_upload": row["last_upload"],
                }
            else:
                return {"sample_count": 0, "total_words": 0, "sources": [], "last_upload": None}

    def record_feedback_theme(self, client_name: str, theme: "FeedbackTheme") -> bool:
        """Record or update a feedback theme

        Args:
            client_name: Client name
            theme: FeedbackTheme instance

        Returns:
            True if recorded successfully
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Check if this theme already exists
            cursor.execute(
                """
                SELECT id, occurrence_count FROM client_feedback_themes
                WHERE client_name = ? AND theme_type = ? AND feedback_phrase = ?
            """,
                (client_name, theme.theme_type, theme.feedback_phrase),
            )

            existing = cursor.fetchone()

            if existing:
                # Update existing theme
                cursor.execute(
                    """
                    UPDATE client_feedback_themes
                    SET occurrence_count = occurrence_count + 1,
                        last_seen = ?
                    WHERE id = ?
                """,
                    (theme.last_seen.isoformat(), existing["id"]),
                )
            else:
                # Insert new theme
                data = theme.to_dict(client_name)
                cursor.execute(
                    """
                    INSERT INTO client_feedback_themes (
                        client_name, theme_type, feedback_phrase,
                        occurrence_count, first_seen, last_seen
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        data["client_name"],
                        data["theme_type"],
                        data["feedback_phrase"],
                        data["occurrence_count"],
                        data["first_seen"],
                        data["last_seen"],
                    ),
                )

            conn.commit()
            return True

    def get_feedback_themes(
        self, client_name: str, theme_type: Optional[str] = None
    ) -> List["FeedbackTheme"]:
        """Get feedback themes for a client

        Args:
            client_name: Client name
            theme_type: Optional filter by theme type

        Returns:
            List of FeedbackTheme instances
        """
        from ..models.client_memory import FeedbackTheme

        with self._get_connection() as conn:
            cursor = conn.cursor()

            if theme_type:
                cursor.execute(
                    """
                    SELECT * FROM client_feedback_themes
                    WHERE client_name = ? AND theme_type = ?
                    ORDER BY occurrence_count DESC
                """,
                    (client_name, theme_type),
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM client_feedback_themes
                    WHERE client_name = ?
                    ORDER BY occurrence_count DESC
                """,
                    (client_name,),
                )

            rows = cursor.fetchall()
            return [FeedbackTheme.from_dict(dict(row)) for row in rows]

    def update_template_performance(
        self, client_name: str, template_id: int, was_revised: bool, quality_score: float = 0.0
    ) -> bool:
        """Update template performance metrics

        Args:
            client_name: Client name
            template_id: Template ID
            was_revised: Whether this template was revised
            quality_score: Quality score for this usage (0.0-1.0)

        Returns:
            True if updated successfully
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Check if record exists
            cursor.execute(
                """
                SELECT usage_count, revision_count, average_quality_score, client_kept_count
                FROM template_performance
                WHERE client_name = ? AND template_id = ?
            """,
                (client_name, template_id),
            )

            existing = cursor.fetchone()

            if existing:
                # Update existing record
                new_usage = existing["usage_count"] + 1
                new_revisions = existing["revision_count"] + (1 if was_revised else 0)
                new_kept = existing["client_kept_count"] + (0 if was_revised else 1)
                new_revision_rate = new_revisions / new_usage if new_usage > 0 else 0.0

                # Running average for quality score
                old_avg = existing["average_quality_score"]
                old_count = existing["usage_count"]
                new_avg = (
                    ((old_avg * old_count) + quality_score) / new_usage if new_usage > 0 else 0.0
                )

                cursor.execute(
                    """
                    UPDATE template_performance SET
                        usage_count = ?,
                        revision_count = ?,
                        revision_rate = ?,
                        average_quality_score = ?,
                        client_kept_count = ?,
                        last_used = CURRENT_TIMESTAMP
                    WHERE client_name = ? AND template_id = ?
                """,
                    (
                        new_usage,
                        new_revisions,
                        new_revision_rate,
                        new_avg,
                        new_kept,
                        client_name,
                        template_id,
                    ),
                )
            else:
                # Insert new record
                revision_count = 1 if was_revised else 0
                kept_count = 0 if was_revised else 1
                revision_rate = 1.0 if was_revised else 0.0

                cursor.execute(
                    """
                    INSERT INTO template_performance (
                        client_name, template_id, usage_count, revision_count,
                        revision_rate, average_quality_score, client_kept_count, last_used
                    ) VALUES (?, ?, 1, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                    (
                        client_name,
                        template_id,
                        revision_count,
                        revision_rate,
                        quality_score,
                        kept_count,
                    ),
                )

            conn.commit()
            return True

    def get_template_performance(self, client_name: str, template_id: Optional[int] = None) -> Dict:
        """Get template performance for a client

        Args:
            client_name: Client name
            template_id: Optional specific template ID

        Returns:
            Dictionary of template performance data
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if template_id is not None:
                cursor.execute(
                    """
                    SELECT * FROM template_performance
                    WHERE client_name = ? AND template_id = ?
                """,
                    (client_name, template_id),
                )
                row = cursor.fetchone()
                return dict(row) if row else {}
            else:
                cursor.execute(
                    """
                    SELECT * FROM template_performance
                    WHERE client_name = ?
                    ORDER BY revision_rate ASC
                """,
                    (client_name,),
                )
                rows = cursor.fetchall()
                return {row["template_id"]: dict(row) for row in rows}

    def get_all_client_names(self) -> List[str]:
        """Get list of all client names with history

        Returns:
            List of client names
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT client_name FROM client_history ORDER BY last_updated DESC")
            rows = cursor.fetchall()
            return [row["client_name"] for row in rows]

    # ============================================================================
    # Phase 8D: Post Feedback Methods
    # ============================================================================

    def store_post_feedback(
        self,
        client_name: str,
        project_id: str,
        post_id: str,
        template_id: int,
        template_name: str,
        feedback_type: str,
        modification_notes: Optional[str] = None,
        engagement_data: Optional[dict] = None,
    ) -> int:
        """
        Store feedback for a delivered post

        Args:
            client_name: Client name
            project_id: Project identifier
            post_id: Post identifier (hash or index)
            template_id: Template ID used
            template_name: Template name
            feedback_type: 'kept', 'modified', 'rejected', 'loved'
            modification_notes: Optional notes about modifications
            engagement_data: Optional dict with likes, comments, shares, clicks

        Returns:
            Feedback record ID
        """
        import json

        with self._get_connection() as conn:
            cursor = conn.cursor()

            engagement_json = json.dumps(engagement_data) if engagement_data else None

            cursor.execute(
                """
                INSERT INTO post_feedback (
                    client_name, project_id, post_id, template_id, template_name,
                    feedback_type, modification_notes, engagement_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    client_name,
                    project_id,
                    post_id,
                    template_id,
                    template_name,
                    feedback_type,
                    modification_notes,
                    engagement_json,
                ),
            )

            feedback_id = cursor.lastrowid
            conn.commit()
            return feedback_id

    def get_post_feedback(
        self,
        client_name: Optional[str] = None,
        project_id: Optional[str] = None,
        feedback_type: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[dict]:
        """
        Get post feedback records with optional filtering

        Args:
            client_name: Filter by client
            project_id: Filter by project
            feedback_type: Filter by type (kept, modified, rejected, loved)
            limit: Maximum number of records

        Returns:
            List of feedback records
        """
        import json

        with self._get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM post_feedback WHERE 1=1"
            params = []

            if client_name:
                query += " AND client_name = ?"
                params.append(client_name)

            if project_id:
                query += " AND project_id = ?"
                params.append(project_id)

            if feedback_type:
                query += " AND feedback_type = ?"
                params.append(feedback_type)

            query += " ORDER BY feedback_date DESC"

            if limit:
                query += " LIMIT ?"
                params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            feedback_list = []
            for row in rows:
                feedback = {
                    "id": row[0],
                    "client_name": row[1],
                    "project_id": row[2],
                    "post_id": row[3],
                    "template_id": row[4],
                    "template_name": row[5],
                    "feedback_type": row[6],
                    "modification_notes": row[7],
                    "feedback_date": row[8],
                    "engagement_data": json.loads(row[9]) if row[9] else None,
                }
                feedback_list.append(feedback)

            return feedback_list

    def get_post_feedback_summary(self, client_name: Optional[str] = None) -> dict:
        """
        Get aggregated feedback statistics

        Args:
            client_name: Optional client to filter by

        Returns:
            Dictionary with feedback counts and percentages
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            query = """
                SELECT
                    feedback_type,
                    COUNT(*) as count
                FROM post_feedback
            """
            params = []

            if client_name:
                query += " WHERE client_name = ?"
                params.append(client_name)

            query += " GROUP BY feedback_type"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            # Calculate totals
            feedback_counts = {row[0]: row[1] for row in rows}
            total = sum(feedback_counts.values())

            return {
                "total_feedback": total,
                "kept": feedback_counts.get("kept", 0),
                "modified": feedback_counts.get("modified", 0),
                "rejected": feedback_counts.get("rejected", 0),
                "loved": feedback_counts.get("loved", 0),
                "kept_rate": feedback_counts.get("kept", 0) / total if total > 0 else 0.0,
                "modified_rate": feedback_counts.get("modified", 0) / total if total > 0 else 0.0,
                "rejected_rate": feedback_counts.get("rejected", 0) / total if total > 0 else 0.0,
                "loved_rate": feedback_counts.get("loved", 0) / total if total > 0 else 0.0,
            }

    # ============================================================================
    # Phase 8D: Client Satisfaction Methods
    # ============================================================================

    def store_client_satisfaction(
        self,
        client_name: str,
        project_id: str,
        satisfaction_score: int,
        quality_rating: int,
        voice_match_rating: int,
        would_recommend: bool,
        feedback_text: Optional[str] = None,
        strengths: Optional[str] = None,
        improvements: Optional[str] = None,
    ) -> int:
        """
        Store client satisfaction survey response

        Args:
            client_name: Client name
            project_id: Project identifier
            satisfaction_score: Overall satisfaction (1-5)
            quality_rating: Quality rating (1-5)
            voice_match_rating: Voice match rating (1-5)
            would_recommend: Would recommend to others
            feedback_text: Optional qualitative feedback
            strengths: What worked well
            improvements: What could be better

        Returns:
            Satisfaction record ID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO client_satisfaction (
                    client_name, project_id,
                    satisfaction_score, quality_rating, voice_match_rating,
                    would_recommend, feedback_text, strengths, improvements
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    client_name,
                    project_id,
                    satisfaction_score,
                    quality_rating,
                    voice_match_rating,
                    would_recommend,
                    feedback_text,
                    strengths,
                    improvements,
                ),
            )

            satisfaction_id = cursor.lastrowid
            conn.commit()

            # Update client_history with average satisfaction
            cursor.execute(
                """
                UPDATE client_history
                SET average_satisfaction = (
                    SELECT AVG(satisfaction_score)
                    FROM client_satisfaction
                    WHERE client_name = ?
                ),
                last_updated = CURRENT_TIMESTAMP
                WHERE client_name = ?
            """,
                (client_name, client_name),
            )

            conn.commit()
            return satisfaction_id

    def get_client_satisfaction(
        self,
        client_name: Optional[str] = None,
        project_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[dict]:
        """
        Get client satisfaction records

        Args:
            client_name: Filter by client
            project_id: Filter by project
            limit: Maximum number of records

        Returns:
            List of satisfaction records
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM client_satisfaction WHERE 1=1"
            params = []

            if client_name:
                query += " AND client_name = ?"
                params.append(client_name)

            if project_id:
                query += " AND project_id = ?"
                params.append(project_id)

            query += " ORDER BY collected_date DESC"

            if limit:
                query += " LIMIT ?"
                params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            satisfaction_list = []
            for row in rows:
                satisfaction = {
                    "id": row[0],
                    "client_name": row[1],
                    "project_id": row[2],
                    "satisfaction_score": row[3],
                    "quality_rating": row[4],
                    "voice_match_rating": row[5],
                    "would_recommend": bool(row[6]),
                    "feedback_text": row[7],
                    "strengths": row[8],
                    "improvements": row[9],
                    "collected_date": row[10],
                }
                satisfaction_list.append(satisfaction)

            return satisfaction_list

    def get_satisfaction_summary(self) -> dict:
        """
        Get aggregated satisfaction statistics

        Returns:
            Dictionary with average scores and recommendation rate
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    COUNT(*) as total_surveys,
                    AVG(satisfaction_score) as avg_satisfaction,
                    AVG(quality_rating) as avg_quality,
                    AVG(voice_match_rating) as avg_voice_match,
                    SUM(CASE WHEN would_recommend = 1 THEN 1 ELSE 0 END) as recommend_count
                FROM client_satisfaction
            """
            )

            row = cursor.fetchone()

            if not row or row[0] == 0:
                return {
                    "total_surveys": 0,
                    "avg_satisfaction": 0.0,
                    "avg_quality": 0.0,
                    "avg_voice_match": 0.0,
                    "recommendation_rate": 0.0,
                }

            total = row[0]
            return {
                "total_surveys": total,
                "avg_satisfaction": float(row[1]) if row[1] else 0.0,
                "avg_quality": float(row[2]) if row[2] else 0.0,
                "avg_voice_match": float(row[3]) if row[3] else 0.0,
                "recommendation_rate": float(row[4]) / total if total > 0 else 0.0,
            }

    # ============================================================================
    # Phase 8D: System Metrics Methods
    # ============================================================================

    def record_metric(
        self,
        metric_date: str,  # YYYY-MM-DD format
        metric_type: str,
        metric_name: str,
        metric_value: float,
        metadata: Optional[dict] = None,
    ) -> None:
        """
        Record a system metric (upserts if exists)

        Args:
            metric_date: Date in YYYY-MM-DD format
            metric_type: 'generation', 'quality', 'cost', 'client', 'template'
            metric_name: Metric name (e.g., 'avg_quality_score')
            metric_value: Numeric value
            metadata: Optional additional context
        """
        import json

        with self._get_connection() as conn:
            cursor = conn.cursor()

            metadata_json = json.dumps(metadata) if metadata else None

            cursor.execute(
                """
                INSERT INTO system_metrics (
                    metric_date, metric_type, metric_name, metric_value, metadata
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(metric_date, metric_type, metric_name)
                DO UPDATE SET
                    metric_value = excluded.metric_value,
                    metadata = excluded.metadata,
                    recorded_at = CURRENT_TIMESTAMP
            """,
                (metric_date, metric_type, metric_name, metric_value, metadata_json),
            )

            conn.commit()

    def get_metrics(
        self,
        metric_type: Optional[str] = None,
        metric_name: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[dict]:
        """
        Get system metrics with optional filtering

        Args:
            metric_type: Filter by type
            metric_name: Filter by name
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            limit: Maximum number of records

        Returns:
            List of metric records
        """
        import json

        with self._get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM system_metrics WHERE 1=1"
            params = []

            if metric_type:
                query += " AND metric_type = ?"
                params.append(metric_type)

            if metric_name:
                query += " AND metric_name = ?"
                params.append(metric_name)

            if start_date:
                query += " AND metric_date >= ?"
                params.append(start_date)

            if end_date:
                query += " AND metric_date <= ?"
                params.append(end_date)

            query += " ORDER BY metric_date DESC, metric_type, metric_name"

            if limit:
                query += " LIMIT ?"
                params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            metrics_list = []
            for row in rows:
                metric = {
                    "id": row[0],
                    "metric_date": row[1],
                    "metric_type": row[2],
                    "metric_name": row[3],
                    "metric_value": row[4],
                    "metadata": json.loads(row[5]) if row[5] else None,
                    "recorded_at": row[6],
                }
                metrics_list.append(metric)

            return metrics_list

    def get_metrics_summary(self, days: int = 30) -> dict:
        """
        Get summary of recent metrics

        Args:
            days: Number of days to look back

        Returns:
            Dictionary with metric summaries by type
        """
        from datetime import date, timedelta

        with self._get_connection() as conn:
            cursor = conn.cursor()

            start_date = (date.today() - timedelta(days=days)).isoformat()

            cursor.execute(
                """
                SELECT
                    metric_type,
                    metric_name,
                    AVG(metric_value) as avg_value,
                    MIN(metric_value) as min_value,
                    MAX(metric_value) as max_value,
                    COUNT(*) as data_points
                FROM system_metrics
                WHERE metric_date >= ?
                GROUP BY metric_type, metric_name
                ORDER BY metric_type, metric_name
            """,
                (start_date,),
            )

            rows = cursor.fetchall()

            # Group by metric type
            summary = {}
            for row in rows:
                metric_type = row[0]
                if metric_type not in summary:
                    summary[metric_type] = []

                summary[metric_type].append(
                    {
                        "metric_name": row[1],
                        "avg_value": float(row[2]) if row[2] else 0.0,
                        "min_value": float(row[3]) if row[3] else 0.0,
                        "max_value": float(row[4]) if row[4] else 0.0,
                        "data_points": row[5],
                    }
                )

            return summary

    # ============================================================================
    # HELPER METHODS
    # ============================================================================

    def _row_to_revision_post(self, row: Dict) -> RevisionPost:
        """Convert database row to RevisionPost"""
        return RevisionPost(
            post_index=row["post_index"],
            template_id=row["template_id"],
            template_name=row["template_name"],
            original_content=row["original_content"],
            original_word_count=row["original_word_count"],
            revised_content=row["revised_content"],
            revised_word_count=row["revised_word_count"],
            changes_summary=row.get("changes_summary"),
        )
