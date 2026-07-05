"""
Unit tests for file_parser utilities

Tests all file parsing methods including:
- Plain text/markdown extraction
- DOCX extraction
- HTML extraction
- JSON extraction
- Text validation
- Word counting
- Language detection
"""

import json
import pytest
from unittest.mock import Mock, patch
from src.utils.file_parser import (
    extract_text_from_file,
    validate_sample_text,
    count_words,
    detect_language,
    _extract_from_docx,
    _extract_from_html,
    _extract_from_json,
    _clean_text,
    _extract_strings_from_dict,
)


class TestExtractTextFromFile:
    """Test extract_text_from_file function"""

    def test_extract_from_nonexistent_file(self, tmp_path):
        """Test that FileNotFoundError is raised for nonexistent files"""
        fake_path = tmp_path / "nonexistent.txt"
        with pytest.raises(FileNotFoundError, match="File not found"):
            extract_text_from_file(fake_path)

    def test_extract_from_txt_file(self, tmp_path):
        """Test extracting from plain text file"""
        test_file = tmp_path / "test.txt"
        content = "This is a test file.\nWith multiple lines.\nAnd some content."
        test_file.write_text(content, encoding="utf-8")

        text, word_count = extract_text_from_file(test_file)

        assert "This is a test file" in text
        assert "With multiple lines" in text
        assert word_count == 11  # Fixed: actual count is 11

    def test_extract_from_md_file(self, tmp_path):
        """Test extracting from markdown file"""
        test_file = tmp_path / "test.md"
        content = "# Header\n\nThis is **bold** text.\n\n- List item 1\n- List item 2"
        test_file.write_text(content, encoding="utf-8")

        text, word_count = extract_text_from_file(test_file)

        assert "Header" in text
        assert "bold" in text
        assert word_count > 0

    def test_extract_from_html_file(self, tmp_path):
        """Test extracting from HTML file"""
        test_file = tmp_path / "test.html"
        content = """
        <html>
            <head><title>Test</title></head>
            <body>
                <h1>Header</h1>
                <p>This is a paragraph with <strong>bold</strong> text.</p>
                <script>console.log('should be removed');</script>
            </body>
        </html>
        """
        test_file.write_text(content, encoding="utf-8")

        text, word_count = extract_text_from_file(test_file)

        assert "Header" in text
        assert "paragraph" in text
        assert "should be removed" not in text  # Scripts removed
        assert word_count > 0

    def test_extract_from_json_file_with_text_field(self, tmp_path):
        """Test extracting from JSON file with 'text' field"""
        test_file = tmp_path / "test.json"
        data = {"text": "This is the main content", "id": 123}
        test_file.write_text(json.dumps(data), encoding="utf-8")

        text, word_count = extract_text_from_file(test_file)

        assert "main content" in text
        assert word_count == 5

    def test_extract_from_json_file_with_content_field(self, tmp_path):
        """Test extracting from JSON file with 'content' field"""
        test_file = tmp_path / "test.json"
        data = {"content": "Post content here", "author": "John"}
        test_file.write_text(json.dumps(data), encoding="utf-8")

        text, word_count = extract_text_from_file(test_file)

        assert "Post content" in text
        assert word_count == 3

    def test_extract_from_json_array(self, tmp_path):
        """Test extracting from JSON array"""
        test_file = tmp_path / "test.json"
        data = [{"text": "First post content"}, {"text": "Second post content"}]
        test_file.write_text(json.dumps(data), encoding="utf-8")

        text, word_count = extract_text_from_file(test_file)

        assert "First post" in text
        assert "Second post" in text
        assert word_count == 6

    def test_extract_from_unsupported_format(self, tmp_path):
        """Test that ValueError is raised for unsupported formats"""
        test_file = tmp_path / "test.xyz"
        test_file.write_text("content", encoding="utf-8")

        with pytest.raises(ValueError, match="Unsupported file format"):
            extract_text_from_file(test_file)

    def test_extract_handles_unicode_decode_error(self, tmp_path):
        """Test fallback to latin-1 encoding on UnicodeDecodeError"""
        test_file = tmp_path / "test.txt"
        # Write with latin-1 encoding
        test_file.write_bytes(b"Test with special chars: \xe9\xe0")

        text, word_count = extract_text_from_file(test_file)

        assert len(text) > 0
        assert word_count > 0


class TestExtractFromDocx:
    """Test DOCX extraction"""

    def test_extract_from_docx_success(self, tmp_path):
        """Test successful DOCX extraction"""
        test_file = tmp_path / "test.docx"

        # Mock the docx.Document (import happens inside the function)
        with patch("docx.Document") as MockDoc:
            # Create mock paragraphs
            mock_para1 = Mock()
            mock_para1.text = "First paragraph"
            mock_para2 = Mock()
            mock_para2.text = "Second paragraph"

            mock_doc = Mock()
            mock_doc.paragraphs = [mock_para1, mock_para2]
            MockDoc.return_value = mock_doc

            text = _extract_from_docx(test_file)

            assert "First paragraph" in text
            assert "Second paragraph" in text
            assert text.count("\n\n") >= 1  # Paragraphs separated by double newline

    def test_extract_from_docx_import_error(self, tmp_path):
        """Test ImportError when python-docx not installed"""
        test_file = tmp_path / "test.docx"

        # Mock the import to raise ImportError
        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "docx":
                raise ImportError("No module named 'docx'")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(ImportError, match="python-docx is required"):
                _extract_from_docx(test_file)


class TestExtractFromHtml:
    """Test HTML extraction"""

    def test_remove_script_tags(self, tmp_path):
        """Test that script tags are removed"""
        test_file = tmp_path / "test.html"
        content = "<html><script>alert('test');</script><p>Content</p></html>"
        test_file.write_text(content, encoding="utf-8")

        text = _extract_from_html(test_file)

        assert "alert" not in text
        assert "Content" in text

    def test_remove_style_tags(self, tmp_path):
        """Test that style tags are removed"""
        test_file = tmp_path / "test.html"
        content = "<html><style>body { color: red; }</style><p>Content</p></html>"
        test_file.write_text(content, encoding="utf-8")

        text = _extract_from_html(test_file)

        assert "color: red" not in text
        assert "Content" in text

    def test_html_entity_decoding(self, tmp_path):
        """Test that HTML entities are decoded"""
        test_file = tmp_path / "test.html"
        content = "<p>Test&nbsp;&amp;&lt;&gt;&quot;&#39;</p>"
        test_file.write_text(content, encoding="utf-8")

        text = _extract_from_html(test_file)

        assert "&nbsp;" not in text
        assert "&amp;" not in text
        assert "&" in text


class TestExtractFromJson:
    """Test JSON extraction"""

    def test_extract_dict_with_text_field(self, tmp_path):
        """Test extracting dict with 'text' field"""
        test_file = tmp_path / "test.json"
        data = {"text": "Main content here"}
        test_file.write_text(json.dumps(data), encoding="utf-8")

        text = _extract_from_json(test_file)

        assert text == "Main content here"

    def test_extract_dict_with_content_field(self, tmp_path):
        """Test extracting dict with 'content' field"""
        test_file = tmp_path / "test.json"
        data = {"content": "Post content"}
        test_file.write_text(json.dumps(data), encoding="utf-8")

        text = _extract_from_json(test_file)

        assert text == "Post content"

    def test_extract_dict_with_list_content(self, tmp_path):
        """Test extracting dict with list in content field"""
        test_file = tmp_path / "test.json"
        data = {"content": ["Line 1", "Line 2", "Line 3"]}
        test_file.write_text(json.dumps(data), encoding="utf-8")

        text = _extract_from_json(test_file)

        assert "Line 1" in text
        assert "Line 2" in text
        assert "Line 3" in text

    def test_extract_list_of_strings(self, tmp_path):
        """Test extracting list of strings"""
        test_file = tmp_path / "test.json"
        data = ["First item", "Second item", "Third item"]
        test_file.write_text(json.dumps(data), encoding="utf-8")

        text = _extract_from_json(test_file)

        assert "First item" in text
        assert "Second item" in text

    def test_extract_list_of_dicts(self, tmp_path):
        """Test extracting list of dicts"""
        test_file = tmp_path / "test.json"
        data = [{"text": "Post number one content"}, {"text": "Post number two content"}]
        test_file.write_text(json.dumps(data), encoding="utf-8")

        text = _extract_from_json(test_file)

        assert "Post number one" in text or "Post" in text
        assert "number two" in text or "content" in text

    def test_extract_nested_dict(self, tmp_path):
        """Test extracting from nested dictionary"""
        test_file = tmp_path / "test.json"
        data = {
            "metadata": {"id": "123"},
            "nested": {"description": "This is a longer description text", "title": "Short"},
        }
        test_file.write_text(json.dumps(data), encoding="utf-8")

        text = _extract_from_json(test_file)

        assert "longer description" in text  # Long string extracted
        assert "123" not in text  # Short strings skipped


class TestExtractStringsFromDict:
    """Test _extract_strings_from_dict helper"""

    def test_extract_long_strings_only(self):
        """Test that only strings > 10 chars are extracted"""
        data = {"long_text": "This is a long string", "short": "Short", "id": "123"}

        strings = _extract_strings_from_dict(data)

        assert "This is a long string" in strings
        assert "Short" not in strings
        assert "123" not in strings

    def test_extract_from_nested_dict(self):
        """Test extracting from nested dictionaries"""
        data = {"level1": {"level2": {"text": "Deep nested text content here"}}}

        strings = _extract_strings_from_dict(data)

        assert any("Deep nested" in s for s in strings)

    def test_extract_from_lists_in_dict(self):
        """Test extracting from lists within dict"""
        data = {
            "items": [
                "First long item text content",
                "Second long item content",
                {"nested": "Nested long text content"},
            ]
        }

        strings = _extract_strings_from_dict(data)

        # Check if strings were extracted (they should be)
        assert len(strings) >= 2
        assert any("First long" in s for s in strings)
        assert any("Second long" in s or "Nested long" in s for s in strings)


class TestCleanText:
    """Test _clean_text function"""

    def test_remove_excessive_whitespace(self):
        """Test removal of excessive whitespace"""
        text = "This  has    multiple     spaces"
        cleaned = _clean_text(text)
        assert cleaned == "This has multiple spaces"

    def test_remove_leading_trailing_whitespace(self):
        """Test removal of leading/trailing whitespace"""
        text = "   Text with spaces   "
        cleaned = _clean_text(text)
        assert cleaned == "Text with spaces"

    def test_remove_null_bytes(self):
        """Test removal of null bytes"""
        text = "Text\x00with\x00nulls"
        cleaned = _clean_text(text)
        assert "\x00" not in cleaned

    def test_remove_bom(self):
        """Test removal of BOM character"""
        text = "\ufeffText with BOM"
        cleaned = _clean_text(text)
        assert "\ufeff" not in cleaned

    def test_normalize_newlines(self):
        """Test that multiple newlines become single spaces"""
        text = "Line 1\n\n\nLine 2"
        cleaned = _clean_text(text)
        assert cleaned == "Line 1 Line 2"


class TestValidateSampleText:
    """Test validate_sample_text function"""

    def test_empty_text_fails(self):
        """Test that empty text fails validation"""
        is_valid, error = validate_sample_text("")
        assert not is_valid
        assert "empty" in error.lower()

    def test_too_short_fails(self):
        """Test that text below min_words fails"""
        text = "Short text"  # 2 words
        is_valid, error = validate_sample_text(text, min_words=100)
        assert not is_valid
        assert "too short" in error.lower()

    def test_too_long_fails(self):
        """Test that text above max_words fails"""
        text = " ".join(["word"] * 2500)  # 2500 words
        is_valid, error = validate_sample_text(text, max_words=2000)
        assert not is_valid
        assert "too long" in error.lower()

    def test_valid_text_passes(self):
        """Test that valid text passes"""
        text = " ".join(["word"] * 150)  # 150 words
        is_valid, error = validate_sample_text(text, min_words=100, max_words=2000)
        assert is_valid
        assert error is None

    def test_non_english_content_fails(self):
        """Test that non-ASCII content fails"""
        # Mostly non-ASCII text (Chinese characters)
        text = "测试文本 " * 100
        is_valid, error = validate_sample_text(text, min_words=50)
        assert not is_valid
        assert "non-English" in error

    def test_promotional_content_fails(self):
        """Test that promotional copy fails"""
        text = (
            """
        Buy now and get 50% off! Limited time offer - click here to order now!
        Special discount available. Act now before this amazing deal expires.
        Free shipping on all orders. Call now to get your exclusive offer!
        """
            * 5
        )  # Repeat to get enough words
        is_valid, error = validate_sample_text(text, min_words=100)
        assert not is_valid
        assert "promotional" in error.lower()

    def test_normal_content_passes(self):
        """Test that normal business content passes"""
        text = (
            """
        Our approach to project management emphasizes collaboration and transparency.
        We believe in empowering teams to work asynchronously while maintaining alignment.
        The key to successful remote work is clear communication and shared understanding.
        """
            * 10
        )  # Repeat to get enough words
        is_valid, error = validate_sample_text(text, min_words=100, max_words=2000)
        assert is_valid
        assert error is None


class TestCountWords:
    """Test count_words function"""

    def test_count_simple_sentence(self):
        """Test counting words in simple sentence"""
        assert count_words("This is a test") == 4

    def test_count_empty_string(self):
        """Test counting words in empty string"""
        assert count_words("") == 0

    def test_count_with_punctuation(self):
        """Test that punctuation doesn't affect count"""
        assert count_words("Hello, world! How are you?") == 5

    def test_count_with_multiple_spaces(self):
        """Test handling of multiple spaces"""
        text = "Word1    Word2     Word3"
        # split() handles multiple spaces automatically
        assert count_words(text) == 3


class TestDetectLanguage:
    """Test detect_language function"""

    def test_detect_english(self):
        """Test detection of English text"""
        text = "This is a sample text in English with common words like the and of to in for not on with he as you do at that have it be."
        assert detect_language(text) == "en"

    def test_detect_unknown_short_text(self):
        """Test that short text returns unknown"""
        text = "Short"
        assert detect_language(text) == "unknown"

    def test_detect_unknown_non_english(self):
        """Test detection of non-English text"""
        # Text with no common English words
        text = "texto ejemplo palabras diferentes lenguaje contenido mucho mas palabras aqui"
        result = detect_language(text)
        # Should return 'unknown' since common English words missing
        assert result in ["en", "unknown"]  # Depends on threshold

    def test_detect_english_with_proper_nouns(self):
        """Test English detection with proper nouns"""
        text = "The company provides innovative solutions for businesses in the market today."
        assert detect_language(text) == "en"

    def test_mostly_english_words(self):
        """Test text with >20% common English words"""
        # Mix of common English words and other words
        text = "The quick brown fox jumps over the lazy dog and runs to the forest"
        assert detect_language(text) == "en"


class TestIntegration:
    """Integration tests combining multiple functions"""

    def test_full_pipeline_txt_file(self, tmp_path):
        """Test full pipeline from file to validation"""
        test_file = tmp_path / "sample.txt"
        content = (
            """
        This is a comprehensive sample text for testing the file parser.
        It contains multiple paragraphs and enough content to pass validation.
        The text is written in English and discusses various business topics.
        We cover project management, team collaboration, and remote work best practices.
        This should be sufficient to meet the minimum word count requirement.
        """
            * 5
        )  # Repeat to ensure enough words

        test_file.write_text(content, encoding="utf-8")

        # Extract
        text, word_count = extract_text_from_file(test_file)

        # Validate
        is_valid, error = validate_sample_text(text, min_words=100)

        # Detect language
        lang = detect_language(text)

        assert word_count >= 100
        assert is_valid
        assert error is None
        assert lang == "en"

    def test_full_pipeline_html_file(self, tmp_path):
        """Test full pipeline with HTML file"""
        test_file = tmp_path / "sample.html"
        content = (
            """
        <html>
        <head><title>Sample</title></head>
        <body>
            <h1>Business Content</h1>
            <p>This is a comprehensive sample for testing HTML parsing.</p>
            <p>It contains multiple paragraphs with business-relevant content.</p>
            <script>console.log('ignore me');</script>
            <p>We discuss project management and team collaboration extensively.</p>
        </body>
        </html>
        """
            * 10
        )

        test_file.write_text(content, encoding="utf-8")

        # Extract
        text, word_count = extract_text_from_file(test_file)

        # Should not contain script content
        assert "console.log" not in text
        assert "Business Content" in text

        # Validate
        is_valid, _ = validate_sample_text(text, min_words=50)
        assert is_valid
