"""
File parser utilities for extracting text from various file formats

Supports:
- Plain text (.txt)
- Markdown (.md)
- Word documents (.docx)
- HTML files (.html)
- JSON files (.json)
"""

import json
import re
from pathlib import Path
from typing import Optional, Tuple


def extract_text_from_file(file_path: Path) -> Tuple[str, int]:
    """
    Extract text content from a file based on its extension

    Args:
        file_path: Path to the file

    Returns:
        Tuple of (text_content, word_count)

    Raises:
        ValueError: If file format not supported
        FileNotFoundError: If file doesn't exist
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    suffix = file_path.suffix.lower()

    if suffix in [".txt", ".md"]:
        text = _extract_from_text(file_path)
    elif suffix == ".docx":
        text = _extract_from_docx(file_path)
    elif suffix in [".html", ".htm"]:
        text = _extract_from_html(file_path)
    elif suffix == ".json":
        text = _extract_from_json(file_path)
    else:
        raise ValueError(f"Unsupported file format: {suffix}")

    # Clean and count words
    text = _clean_text(text)
    word_count = len(text.split())

    return text, word_count


def _extract_from_text(file_path: Path) -> str:
    """Extract text from plain text or markdown file"""
    try:
        return file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Try with different encoding
        return file_path.read_text(encoding="latin-1")


def _extract_from_docx(file_path: Path) -> str:
    """Extract text from Word document"""
    try:
        from docx import Document
    except ImportError:
        raise ImportError(
            "python-docx is required to parse .docx files. "
            "Install it with: pip install python-docx"
        )

    doc = Document(file_path)
    paragraphs = [paragraph.text for paragraph in doc.paragraphs]
    return "\n\n".join(paragraphs)


def _extract_from_html(file_path: Path) -> str:
    """Extract text from HTML file"""
    html_content = file_path.read_text(encoding="utf-8")

    # Remove script and style elements
    html_content = re.sub(r"<script[^>]*>.*?</script>", "", html_content, flags=re.DOTALL)
    html_content = re.sub(r"<style[^>]*>.*?</style>", "", html_content, flags=re.DOTALL)

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", html_content)

    # Decode HTML entities
    text = text.replace("&nbsp;", " ")
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&quot;", '"')
    text = text.replace("&#39;", "'")

    return text


def _extract_from_json(file_path: Path) -> str:
    """Extract text from JSON file"""
    data = json.loads(file_path.read_text(encoding="utf-8"))

    # Handle different JSON structures
    if isinstance(data, dict):
        # Look for common text fields
        text_fields = ["text", "content", "body", "description", "post", "message"]

        for field in text_fields:
            if field in data:
                if isinstance(data[field], str):
                    return data[field]
                elif isinstance(data[field], list):
                    return "\n\n".join(str(item) for item in data[field])

        # If no text field found, extract all string values
        texts = _extract_strings_from_dict(data)
        return "\n\n".join(texts)

    elif isinstance(data, list):
        # Assume list of posts/items
        texts = []
        for item in data:
            if isinstance(item, str):
                texts.append(item)
            elif isinstance(item, dict):
                item_texts = _extract_strings_from_dict(item)
                texts.extend(item_texts)
        return "\n\n".join(texts)

    else:
        return str(data)


def _extract_strings_from_dict(data: dict) -> list:
    """Recursively extract string values from a dictionary"""
    strings = []

    for key, value in data.items():
        if isinstance(value, str) and len(value) > 10:  # Skip short strings like IDs
            strings.append(value)
        elif isinstance(value, dict):
            strings.extend(_extract_strings_from_dict(value))
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str) and len(item) > 10:
                    strings.append(item)
                elif isinstance(item, dict):
                    strings.extend(_extract_strings_from_dict(item))

    return strings


def _clean_text(text: str) -> str:
    """Clean extracted text"""
    # Remove excessive whitespace
    text = re.sub(r"\s+", " ", text)

    # Remove leading/trailing whitespace
    text = text.strip()

    # Remove common artifacts
    text = text.replace("\x00", "")  # Null bytes
    text = text.replace("\ufeff", "")  # BOM

    return text


def validate_sample_text(
    text: str, min_words: int = 100, max_words: int = 2000
) -> Tuple[bool, Optional[str]]:
    """
    Validate that sample text meets requirements

    Args:
        text: Text content to validate
        min_words: Minimum word count (default: 100)
        max_words: Maximum word count (default: 2000)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not text or len(text.strip()) == 0:
        return False, "Sample text is empty"

    word_count = len(text.split())

    if word_count < min_words:
        return False, f"Sample too short ({word_count} words). Minimum is {min_words} words"

    if word_count > max_words:
        return False, f"Sample too long ({word_count} words). Maximum is {max_words} words"

    # Check if text is mostly ASCII (English content)
    ascii_ratio = sum(1 for c in text if ord(c) < 128) / len(text)
    if ascii_ratio < 0.8:
        return False, "Sample appears to contain non-English content"

    # Check if text is mostly promotional/sales copy (simple heuristic)
    promotional_words = [
        "buy now",
        "click here",
        "limited time",
        "act now",
        "special offer",
        "discount",
        "% off",
        "free shipping",
        "order now",
        "call now",
    ]
    text_lower = text.lower()
    promo_count = sum(1 for word in promotional_words if word in text_lower)

    if promo_count >= 3:
        return False, "Sample appears to be promotional/sales copy, not authentic voice"

    return True, None


def count_words(text: str) -> int:
    """Count words in text"""
    return len(text.split())


def detect_language(text: str) -> str:
    """
    Simple language detection (English vs other)

    Returns:
        'en' for English, 'unknown' for other
    """
    # Simple heuristic: check for common English words
    common_english_words = [
        "the",
        "be",
        "to",
        "of",
        "and",
        "a",
        "in",
        "that",
        "have",
        "i",
        "it",
        "for",
        "not",
        "on",
        "with",
        "he",
        "as",
        "you",
        "do",
        "at",
    ]

    text_lower = text.lower()
    words = text_lower.split()

    if len(words) < 10:
        return "unknown"

    # Count how many common English words appear
    english_word_count = sum(1 for word in words if word in common_english_words)

    # If >20% of words are common English words, assume English
    if english_word_count / len(words) > 0.2:
        return "en"

    return "unknown"
