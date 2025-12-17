"""Base classes for research tools"""

import json
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from ..utils.logger import logger


@dataclass
class ResearchResult:
    """Result from research tool execution"""

    tool_name: str
    project_id: str
    executed_at: datetime
    success: bool
    outputs: Dict[str, Path]  # format -> file path
    metadata: Dict[str, Any]
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data["executed_at"] = self.executed_at.isoformat()
        data["outputs"] = {k: str(v) for k, v in self.outputs.items()}
        return data


class ResearchTool(ABC):
    """Base class for all research tools

    Each research tool:
    1. Validates inputs
    2. Executes analysis
    3. Generates reports (PDF, MD, JSON, XLSX)
    4. Logs execution for billing

    Subclasses must implement:
    - tool_name(): Return tool identifier
    - price(): Return add-on price
    - validate_inputs(): Check required inputs
    - run_analysis(): Execute research logic
    - generate_reports(): Create output files
    """

    def __init__(self, project_id: str, config: Optional[Dict[str, Any]] = None):
        """Initialize research tool

        Args:
            project_id: Unique project identifier
            config: Optional configuration overrides
        """
        self.project_id = project_id
        self.config = config or {}

        # Base directory for all research outputs
        self.base_output_dir = Path("data/research")

        logger.info(f"Initialized {self.tool_name} for project {project_id}")

    @property
    def output_dir(self) -> Path:
        """Get output directory for this tool and project"""
        path = self.base_output_dir / self.tool_name / self.project_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    @abstractmethod
    def tool_name(self) -> str:
        """Return tool identifier (e.g., 'voice_analysis')"""

    @property
    @abstractmethod
    def price(self) -> int:
        """Return add-on price in USD"""

    @abstractmethod
    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """Validate required inputs are provided

        Args:
            inputs: Input parameters

        Returns:
            True if inputs are valid

        Raises:
            ValueError: If inputs are invalid
        """

    @abstractmethod
    def run_analysis(self, inputs: Dict[str, Any]) -> Any:
        """Execute the main research logic

        Args:
            inputs: Validated input parameters

        Returns:
            Analysis result object (tool-specific)
        """

    @abstractmethod
    def generate_reports(self, analysis: Any) -> Dict[str, Path]:
        """Generate output reports

        Args:
            analysis: Result from run_analysis()

        Returns:
            Dictionary mapping format to file path
            Example: {'pdf': Path(...), 'json': Path(...), 'xlsx': Path(...)}
        """

    def execute(self, inputs: Dict[str, Any]) -> ResearchResult:
        """Main execution method

        Args:
            inputs: Input parameters for research

        Returns:
            ResearchResult with outputs and metadata
        """
        start_time = datetime.now()

        try:
            # Validate inputs
            logger.info(f"Validating inputs for {self.tool_name}")
            if not self.validate_inputs(inputs):
                raise ValueError(f"Invalid inputs for {self.tool_name}")

            # Run analysis
            logger.info(f"Running {self.tool_name} analysis")
            analysis = self.run_analysis(inputs)

            # Generate reports
            logger.info(f"Generating reports for {self.tool_name}")
            outputs = self.generate_reports(analysis)

            # Calculate duration
            duration = (datetime.now() - start_time).total_seconds()

            # Create result
            result = ResearchResult(
                tool_name=self.tool_name,
                project_id=self.project_id,
                executed_at=start_time,
                success=True,
                outputs=outputs,
                metadata={
                    "duration_seconds": duration,
                    "price": self.price,
                    "inputs_summary": self._summarize_inputs(inputs),
                },
            )

            # Log execution
            self._log_execution(result)

            logger.info(f"{self.tool_name} completed successfully in {duration:.1f}s")

            return result

        except Exception as e:
            logger.error(f"{self.tool_name} failed: {str(e)}", exc_info=True)

            duration = (datetime.now() - start_time).total_seconds()

            return ResearchResult(
                tool_name=self.tool_name,
                project_id=self.project_id,
                executed_at=start_time,
                success=False,
                outputs={},
                metadata={"duration_seconds": duration, "price": self.price},
                error=str(e),
            )

    def _summarize_inputs(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Create summary of inputs for logging

        Avoid logging large content, just metadata
        """
        summary = {}
        for key, value in inputs.items():
            if isinstance(value, (str, int, float, bool)):
                summary[key] = value
            elif isinstance(value, list):
                summary[key] = f"{len(value)} items"
            elif isinstance(value, dict):
                summary[key] = f"dict with {len(value)} keys"
            else:
                summary[key] = str(type(value).__name__)
        return summary

    def _log_execution(self, result: ResearchResult):
        """Log execution for billing and tracking

        Saves execution log to JSON file for later billing/analytics
        """
        log_file = self.output_dir / "execution_log.json"

        # Load existing logs
        logs = []
        if log_file.exists():
            try:
                with open(log_file, "r") as f:
                    logs = json.load(f)
            except:
                pass

        # Append new log
        logs.append(result.to_dict())

        # Save
        with open(log_file, "w") as f:
            json.dump(logs, f, indent=2)

        logger.debug(f"Logged execution to {log_file}")

    def _save_json(self, data: Any, filename: str) -> Path:
        """Save data as JSON

        Args:
            data: Data to save (must be JSON-serializable)
            filename: Output filename

        Returns:
            Path to saved file
        """
        output_path = self.output_dir / filename

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

        logger.debug(f"Saved JSON to {output_path}")
        return output_path

    def _save_markdown(self, content: str, filename: str) -> Path:
        """Save content as Markdown

        Args:
            content: Markdown content
            filename: Output filename

        Returns:
            Path to saved file
        """
        output_path = self.output_dir / filename

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.debug(f"Saved Markdown to {output_path}")
        return output_path

    def _save_text(self, content: str, filename: str) -> Path:
        """Save content as plain text

        Args:
            content: Text content
            filename: Output filename

        Returns:
            Path to saved file
        """
        output_path = self.output_dir / filename

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.debug(f"Saved text to {output_path}")
        return output_path
