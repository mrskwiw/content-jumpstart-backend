"""
File utility functions for deliverables.
"""
from pathlib import Path


def calculate_file_size(file_path: str) -> int:
    """
    Calculate actual file size in bytes.

    Args:
        file_path: Relative path to file from project root or absolute path

    Returns:
        File size in bytes, or 0 if file doesn't exist
    """
    try:
        # Convert to Path object
        path = Path(file_path)

        # If not absolute, make it relative to project root
        if not path.is_absolute():
            # Get project root (3 levels up from this file: utils/ -> backend/ -> project/)
            project_root = Path(__file__).parent.parent.parent
            path = project_root / file_path

        # Return size if file exists
        if path.exists() and path.is_file():
            return path.stat().st_size
        else:
            return 0

    except Exception:
        return 0


def format_file_size(size_bytes: int) -> str:
    """
    Format bytes to human-readable size.

    Args:
        size_bytes: File size in bytes

    Returns:
        Formatted string (e.g., "1.5 MB", "234 KB")
    """
    if size_bytes == 0:
        return "0 B"

    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0
    size = float(size_bytes)

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    # Format with appropriate precision
    if size < 10:
        return f"{size:.1f} {units[unit_index]}"
    else:
        return f"{size:.0f} {units[unit_index]}"
