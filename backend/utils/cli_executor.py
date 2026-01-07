"""
CLI Executor - Execute Python CLI scripts and parse output

Handles subprocess execution of run_jumpstart.py and other CLI tools
Uses asyncio.create_subprocess_exec (safe, no shell injection)
"""
import asyncio
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from backend.utils.logger import logger


class CLIExecutor:
    """Execute CLI scripts and parse their output"""

    def __init__(self):
        # Get project root (backend's parent directory)
        self.project_root = Path(__file__).parent.parent.parent
        self.python_exe = "python"  # Could be made configurable

    async def run_content_generation(
        self,
        brief_path: str,
        client_name: str,
        num_posts: int = 30,
        platform: Optional[str] = None,
        voice_samples: Optional[List[str]] = None,
    ) -> Dict[str, any]:
        """
        Run run_jumpstart.py to generate content

        Args:
            brief_path: Path to client brief file
            client_name: Client name for file organization
            num_posts: Number of posts to generate
            platform: Target platform (linkedin, twitter, etc.)
            voice_samples: Optional list of voice sample file paths

        Returns:
            Dict with:
                - success: bool
                - output_dir: Path to generated files
                - files: Dict[str, Path] of generated files
                - posts: List[Dict] of post data
                - error: Optional error message
        """
        logger.info(f"Executing content generation for {client_name}")

        # Build command (safe: arguments as list, not shell string)
        cmd = [
            self.python_exe,
            str(self.project_root / "run_jumpstart.py"),
            brief_path,
            "-n", str(num_posts),
        ]

        if platform:
            cmd.extend(["-p", platform])

        if voice_samples:
            cmd.extend(["--voice-samples"] + voice_samples)

        logger.info(f"Command: {' '.join(cmd)}")

        try:
            # Execute subprocess (SECURE: create_subprocess_exec, not shell)
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.project_root),
            )

            stdout, stderr = await process.communicate()

            stdout_text = stdout.decode('utf-8', errors='replace')
            stderr_text = stderr.decode('utf-8', errors='replace')

            logger.info(f"Process exit code: {process.returncode}")

            if process.returncode != 0:
                logger.error(f"CLI execution failed:\n{stderr_text}")
                return {
                    "success": False,
                    "error": f"Generation failed: {stderr_text[:500]}",
                    "stdout": stdout_text,
                    "stderr": stderr_text,
                }

            # Parse output to find generated files
            output_dir, files = self._parse_output_files(stdout_text)

            # Load posts from generated JSON file if available
            posts = []
            if "posts_json" in files:
                posts = self._load_posts_from_json(files["posts_json"])

            logger.info(f"Successfully generated {len(posts)} posts")
            logger.info(f"Output directory: {output_dir}")

            return {
                "success": True,
                "output_dir": str(output_dir),
                "files": {k: str(v) for k, v in files.items()},
                "posts": posts,
                "stdout": stdout_text,
            }

        except Exception as e:
            logger.error(f"CLI execution error: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
            }

    async def run_research_tool(
        self,
        tool_name: str,
        brief_path: str,
        project_id: str,
        client_id: str,
    ) -> Dict[str, any]:
        """
        Run a research tool

        Args:
            tool_name: Name of research tool to execute
            brief_path: Path to client brief
            project_id: Project ID
            client_id: Client ID

        Returns:
            Dict with:
                - success: bool
                - outputs: Dict[str, str] of output file paths
                - metadata: Dict with research metadata
                - error: Optional error message
        """
        logger.info(f"Executing research tool: {tool_name}")

        # TODO: Implement actual research tool execution
        # For now, return stub response

        output_dir = self.project_root / "data" / "research" / tool_name / project_id

        return {
            "success": True,
            "outputs": {
                "json": str(output_dir / "analysis.json"),
                "markdown": str(output_dir / "report.md"),
                "text": str(output_dir / "summary.txt"),
            },
            "metadata": {
                "status": "completed",
                "tool": tool_name,
                "project_id": project_id,
                "client_id": client_id,
            },
        }

    def _parse_output_files(self, stdout: str) -> Tuple[Path, Dict[str, Path]]:
        """Parse stdout to find generated file paths"""
        output_dir = None
        files = {}

        # Find output directory
        dir_match = re.search(r'Deliverables saved to:\s*(.+?)$', stdout, re.MULTILINE)
        if dir_match:
            output_dir = Path(dir_match.group(1).strip())

        # If we found output dir, scan it for files
        if output_dir and output_dir.exists():
            file_patterns = {
                "deliverable": "*_deliverable.md",
                "posts_txt": "*_posts.txt",
                "posts_json": "*_posts.json",
                "brand_voice": "*_brand_voice.md",
                "qa_report": "*_qa_report.md",
            }

            for key, pattern in file_patterns.items():
                matches = list(output_dir.glob(pattern))
                if matches:
                    files[key] = max(matches, key=lambda p: p.stat().st_mtime)

        return output_dir or Path("data/outputs/unknown"), files

    def _load_posts_from_json(self, json_path: Path) -> List[Dict]:
        """Load posts from generated JSON file"""
        try:
            if not json_path.exists():
                logger.warning(f"Posts JSON file not found: {json_path}")
                return []

            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "posts" in data:
                return data["posts"]
            else:
                logger.warning(f"Unexpected JSON structure")
                return []

        except Exception as e:
            logger.error(f"Failed to load posts from JSON: {str(e)}")
            return []


# Global instance
cli_executor = CLIExecutor()
