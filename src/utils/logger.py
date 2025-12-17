"""Logging configuration using Rich for beautiful console output"""

import logging
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme

# Custom theme for logs
custom_theme = Theme(
    {
        "info": "cyan",
        "warning": "yellow",
        "error": "bold red",
        "critical": "bold white on red",
    }
)

# Force UTF-8 encoding for Windows compatibility
# Use legacy_windows=True to avoid emoji encoding issues on Windows
import platform

is_windows = platform.system() == "Windows"
console = Console(
    theme=custom_theme, force_terminal=True, legacy_windows=is_windows, no_color=False
)


def setup_logger(
    name: str = "content_jumpstart",
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
) -> logging.Logger:
    """
    Set up logger with Rich handler for console output

    Args:
        name: Logger name
        level: Logging level (default: INFO)
        log_file: Optional file path for file logging

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Rich console handler
    console_handler = RichHandler(
        console=console,
        show_time=True,
        show_path=False,
        markup=True,
        rich_tracebacks=True,
        tracebacks_show_locals=True,
    )
    console_handler.setLevel(level)
    logger.addHandler(console_handler)

    # Optional file handler
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


# Default logger instance
logger = setup_logger()


def log_client_start(client_name: str) -> None:
    """Log start of client content generation"""
    console.print(
        f"\n[bold cyan]=== Starting Content Generation for {client_name} ===[/bold cyan]\n"
    )


def log_client_complete(client_name: str, post_count: int, duration_seconds: float) -> None:
    """Log completion of client content generation"""
    console.print(
        f"\n[bold green]OK Completed {post_count} posts for {client_name} "
        f"in {duration_seconds:.1f}s[/bold green]\n"
    )


def log_template_selection(template_count: int, total_available: int) -> None:
    """Log template selection"""
    logger.info(f"Selected {template_count} templates from {total_available} available")


def log_post_generated(post_number: int, template_name: str, word_count: int) -> None:
    """Log individual post generation"""
    logger.debug(f"Post {post_number}: {template_name} ({word_count} words)")


def log_api_call(model: str, tokens_estimate: int) -> None:
    """Log Anthropic API call"""
    logger.debug(f"API call: {model} (~{tokens_estimate} tokens)")


def log_error(error_msg: str, exc_info: bool = False) -> None:
    """Log error with optional exception info"""
    logger.error(error_msg, exc_info=exc_info)


def log_warning(warning_msg: str) -> None:
    """Log warning"""
    logger.warning(warning_msg)
