"""
Agent tools - wrappers for existing CLI commands and operations
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.project_db import ProjectDatabase


class AgentTools:
    """Tools available to the agent for executing operations"""

    def __init__(self):
        self.db = ProjectDatabase()
        self.project_dir = Path(__file__).parent.parent

    # ============================================================================
    # PROJECT MANAGEMENT TOOLS
    # ============================================================================

    async def generate_posts(
        self, client_name: str, brief_path: str, num_posts: int = 30, platform: str = "linkedin"
    ) -> Dict[str, Any]:
        """
        Generate posts for a client

        Wraps: python 03_post_generator.py generate [brief] -c [client] -n [num]
        """
        cmd = [
            sys.executable,
            str(self.project_dir / "03_post_generator.py"),
            "generate",
            brief_path,
            "-c",
            client_name,
            "-n",
            str(num_posts),
            "--platform",
            platform,
        ]

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(self.project_dir),
            )

            stdout, stderr = process.communicate()

            if process.returncode == 0:
                # Extract project ID from output
                project_id = self._extract_project_id(stdout)

                return {
                    "success": True,
                    "message": f"Generated {num_posts} posts for {client_name}",
                    "project_id": project_id,
                    "output": stdout,
                }
            else:
                return {"success": False, "error": stderr or stdout, "message": "Generation failed"}

        except Exception as e:
            return {"success": False, "error": str(e), "message": "Exception during generation"}

    def list_projects(self, client_name: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
        """
        List projects, optionally filtered by client

        Wraps: python 03_post_generator.py list-projects
        """
        try:
            projects = self.db.get_projects(limit=limit)

            if client_name:
                projects = [p for p in projects if p.get("client_name") == client_name]

            return {"success": True, "projects": projects, "count": len(projects)}

        except Exception as e:
            return {"success": False, "error": str(e), "projects": []}

    def get_project_status(self, project_id: str) -> Dict[str, Any]:
        """
        Get detailed status of a specific project

        Wraps: python 03_post_generator.py project-status [project_id]
        """
        try:
            project = self.db.get_project(project_id)

            if not project:
                return {"success": False, "error": f"Project {project_id} not found"}

            # Get additional stats
            feedback = self.db.get_post_feedback(project_id=project_id)
            satisfaction = self.db.get_client_satisfaction(project_id=project_id)

            return {
                "success": True,
                "project": project,
                "feedback_count": len(feedback),
                "has_satisfaction": len(satisfaction) > 0,
                "status": project.get("status", "unknown"),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    # ============================================================================
    # CLIENT MANAGEMENT TOOLS
    # ============================================================================

    def list_clients(self) -> Dict[str, Any]:
        """Query database for unique clients"""
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT DISTINCT client_name
                    FROM client_history
                    ORDER BY client_name
                """
                )

                clients = [row[0] for row in cursor.fetchall()]

                return {"success": True, "clients": clients, "count": len(clients)}

        except Exception as e:
            return {"success": False, "error": str(e), "clients": []}

    def get_client_history(self, client_name: str) -> Dict[str, Any]:
        """Get client's project history and statistics"""
        try:
            # Get projects
            projects = self.db.get_projects()
            client_projects = [p for p in projects if p.get("client_name") == client_name]

            # Get feedback summary
            feedback_summary = self.db.get_post_feedback_summary(client_name=client_name)

            # Get satisfaction summary
            satisfaction_records = self.db.get_client_satisfaction(client_name=client_name)

            return {
                "success": True,
                "client_name": client_name,
                "total_projects": len(client_projects),
                "projects": client_projects,
                "feedback_summary": feedback_summary,
                "satisfaction_records": satisfaction_records,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    # ============================================================================
    # FEEDBACK & SATISFACTION TOOLS
    # ============================================================================

    async def collect_feedback(self, client_name: str, project_id: str) -> Dict[str, Any]:
        """
        Collect post feedback from client

        Wraps: python 03_post_generator.py feedback [project_id]
        """
        cmd = [
            sys.executable,
            str(self.project_dir / "03_post_generator.py"),
            "feedback",
            project_id,
            "-c",
            client_name,
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(self.project_dir))

            return {
                "success": result.returncode == 0,
                "message": "Feedback collection initiated" if result.returncode == 0 else "Failed",
                "output": result.stdout,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def collect_satisfaction(self, client_name: str, project_id: str) -> Dict[str, Any]:
        """
        Collect satisfaction survey from client

        Wraps: python 03_post_generator.py satisfaction [project_id]
        """
        cmd = [
            sys.executable,
            str(self.project_dir / "03_post_generator.py"),
            "satisfaction",
            project_id,
            "-c",
            client_name,
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(self.project_dir))

            return {
                "success": result.returncode == 0,
                "message": "Satisfaction survey initiated" if result.returncode == 0 else "Failed",
                "output": result.stdout,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    # ============================================================================
    # VOICE SAMPLE TOOLS
    # ============================================================================

    async def upload_voice_samples(
        self, client_name: str, file_paths: List[str], source: str = "mixed"
    ) -> Dict[str, Any]:
        """
        Upload voice samples for a client

        Wraps: python 03_post_generator.py upload-voice-samples
        """
        cmd = [
            sys.executable,
            str(self.project_dir / "03_post_generator.py"),
            "upload-voice-samples",
            "--client",
            client_name,
            "--source",
            source,
        ]

        for file_path in file_paths:
            cmd.extend(["--file", file_path])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(self.project_dir))

            return {
                "success": result.returncode == 0,
                "message": f"Uploaded {len(file_paths)} voice samples"
                if result.returncode == 0
                else "Upload failed",
                "output": result.stdout,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    # ============================================================================
    # ANALYTICS TOOLS
    # ============================================================================

    async def show_dashboard(self, client_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Show analytics dashboard

        Wraps: python 03_post_generator.py dashboard
        """
        cmd = [sys.executable, str(self.project_dir / "03_post_generator.py"), "dashboard"]

        if client_name:
            cmd.extend(["-c", client_name])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(self.project_dir))

            return {"success": result.returncode == 0, "output": result.stdout}

        except Exception as e:
            return {"success": False, "error": str(e)}

    # ============================================================================
    # FILE OPERATIONS
    # ============================================================================

    def read_file(self, file_path: str) -> Dict[str, Any]:
        """Read a file (brief, feedback, etc.)"""
        try:
            path = Path(file_path)
            if not path.exists():
                return {"success": False, "error": f"File not found: {file_path}"}

            content = path.read_text(encoding="utf-8")

            return {
                "success": True,
                "content": content,
                "file_path": file_path,
                "size": len(content),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def search_files(self, pattern: str, directory: str = "data") -> Dict[str, Any]:
        """Search for files matching a pattern"""
        try:
            search_dir = self.project_dir / directory
            matches = list(search_dir.rglob(pattern))

            return {"success": True, "matches": [str(m) for m in matches], "count": len(matches)}

        except Exception as e:
            return {"success": False, "error": str(e), "matches": []}

    async def process_revision(
        self, client_name: str, project_id: str, revision_notes: str, regenerate_count: int = 5
    ) -> Dict[str, Any]:
        """
        Process revision request for a project

        Wraps: python 03_post_generator.py revision command
        """
        try:
            # Create revision notes file
            revision_file = self.project_dir / "data" / "revisions" / f"{project_id}_revision.txt"
            revision_file.parent.mkdir(parents=True, exist_ok=True)
            revision_file.write_text(revision_notes, encoding="utf-8")

            cmd = [
                sys.executable,
                str(self.project_dir / "03_post_generator.py"),
                "revision",
                project_id,
                str(revision_file),
                "-n",
                str(regenerate_count),
            ]

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(self.project_dir),
            )

            stdout, stderr = process.communicate(timeout=180)  # 3 minute timeout

            if process.returncode == 0:
                return {
                    "success": True,
                    "message": f"Revision processed for {client_name}",
                    "project_id": project_id,
                    "regenerated_posts": regenerate_count,
                    "output": stdout,
                }
            else:
                return {
                    "success": False,
                    "error": stderr or stdout,
                    "message": "Revision processing failed",
                }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Revision processing timed out (>3 minutes)"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def generate_analytics_report(
        self, client_name: Optional[str] = None, report_type: str = "summary"
    ) -> Dict[str, Any]:
        """
        Generate analytics report for client(s)

        Wraps: python 03_post_generator.py analytics command
        """
        try:
            cmd = [sys.executable, str(self.project_dir / "03_post_generator.py"), "analytics"]

            if client_name:
                cmd.extend(["-c", client_name])

            cmd.extend(["--format", report_type])

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(self.project_dir),
            )

            stdout, stderr = process.communicate(timeout=30)

            if process.returncode == 0:
                return {
                    "success": True,
                    "message": "Analytics report generated",
                    "client": client_name or "All clients",
                    "report_type": report_type,
                    "output": stdout,
                }
            else:
                return {"success": False, "error": stderr or stdout}

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Analytics generation timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_posting_schedule(
        self,
        client_name: str,
        project_id: str,
        posts_per_week: int = 4,
        start_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create posting schedule for a project

        Wraps: posting schedule generation functionality
        """
        try:
            from datetime import datetime

            from src.utils.schedule_generator import ScheduleGenerator

            # Get project posts
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM client_history
                    WHERE project_id = ?
                """,
                    (project_id,),
                )
                row = cursor.fetchone()
                total_posts = row[0] if row else 30

            # Generate schedule
            generator = ScheduleGenerator()
            schedule_start = datetime.fromisoformat(start_date) if start_date else datetime.now()

            schedule = generator.generate_schedule(
                total_posts=total_posts, posts_per_week=posts_per_week, start_date=schedule_start
            )

            # Save schedule to file
            schedule_file = self.project_dir / "data" / "schedules" / f"{project_id}_schedule.json"
            schedule_file.parent.mkdir(parents=True, exist_ok=True)

            import json

            schedule_file.write_text(
                json.dumps(
                    {
                        "client_name": client_name,
                        "project_id": project_id,
                        "posts_per_week": posts_per_week,
                        "start_date": schedule_start.isoformat(),
                        "schedule": [s.model_dump(mode="json") for s in schedule.posting_schedule],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            return {
                "success": True,
                "message": f"Posting schedule created for {client_name}",
                "project_id": project_id,
                "total_posts": total_posts,
                "posts_per_week": posts_per_week,
                "schedule_file": str(schedule_file),
                "duration_weeks": len(schedule.posting_schedule) // posts_per_week,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    # ============================================================================
    # HELPER METHODS
    # ============================================================================

    def _extract_project_id(self, output: str) -> Optional[str]:
        """Extract project ID from CLI output"""
        for line in output.split("\n"):
            if "Project ID:" in line or "project_id:" in line:
                parts = line.split(":")
                if len(parts) > 1:
                    return parts[1].strip()

        return None

    def get_available_tools(self) -> List[Dict[str, str]]:
        """Get list of available tools with descriptions"""
        return [
            {
                "name": "generate_posts",
                "description": "Generate 30 social media posts from a client brief",
                "parameters": "client_name, brief_path, num_posts (default 30), platform (default linkedin)",
            },
            {
                "name": "list_projects",
                "description": "List all projects, optionally filtered by client",
                "parameters": "client_name (optional), limit (default 10)",
            },
            {
                "name": "get_project_status",
                "description": "Get detailed status of a specific project",
                "parameters": "project_id",
            },
            {
                "name": "list_clients",
                "description": "Get list of all clients in the system",
                "parameters": "none",
            },
            {
                "name": "get_client_history",
                "description": "Get client's project history and statistics",
                "parameters": "client_name",
            },
            {
                "name": "collect_feedback",
                "description": "Collect post feedback from a client",
                "parameters": "client_name, project_id",
            },
            {
                "name": "collect_satisfaction",
                "description": "Collect satisfaction survey from a client",
                "parameters": "client_name, project_id",
            },
            {
                "name": "upload_voice_samples",
                "description": "Upload voice samples for better voice matching",
                "parameters": "client_name, file_paths (list), source (default mixed)",
            },
            {
                "name": "show_dashboard",
                "description": "Show analytics dashboard for all clients or specific client",
                "parameters": "client_name (optional)",
            },
            {
                "name": "read_file",
                "description": "Read content from a file (brief, feedback, etc.)",
                "parameters": "file_path",
            },
            {
                "name": "search_files",
                "description": "Search for files matching a pattern",
                "parameters": "pattern, directory (default data)",
            },
            {
                "name": "process_revision",
                "description": "Process revision request and regenerate posts based on client feedback",
                "parameters": "client_name, project_id, revision_notes, regenerate_count (default 5)",
            },
            {
                "name": "generate_analytics_report",
                "description": "Generate analytics report for client(s) showing performance metrics",
                "parameters": "client_name (optional), report_type (default summary)",
            },
            {
                "name": "create_posting_schedule",
                "description": "Create posting schedule for a project with specified frequency",
                "parameters": "client_name, project_id, posts_per_week (default 4), start_date (optional)",
            },
        ]
