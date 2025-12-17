"""
Integration tests for Phase 8C: Voice Sample Upload & Matching
"""
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from src.agents.voice_analyzer import VoiceAnalyzer
from src.database.project_db import ProjectDatabase
from src.models.post import Post
from src.models.voice_sample import VoiceSampleBatch, VoiceSampleUpload
from src.utils.file_parser import extract_text_from_file, validate_sample_text
from src.utils.voice_matcher import VoiceMatcher


class TestVoiceSampleUpload:
    """Test voice sample upload functionality"""

    def setup_method(self):
        """Setup test database"""
        self.db = ProjectDatabase()
        self.test_client = f"TestClient_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def test_voice_sample_model_validation(self):
        """Test VoiceSampleUpload model validation"""
        # Valid sample
        sample = VoiceSampleUpload(
            client_name="Test Client",
            sample_text="This is a test sample. " * 30,  # ~150 words
            sample_source="linkedin",
            word_count=150,
            file_name="test.txt",
        )
        assert sample.client_name == "Test Client"
        assert sample.word_count == 150

        # Invalid word count (too short)
        with pytest.raises(ValueError):
            VoiceSampleUpload(
                client_name="Test",
                sample_text="Too short",
                sample_source="linkedin",
                word_count=50,  # < 100
                file_name="test.txt",
            )

        # Invalid word count (too long)
        with pytest.raises(ValueError):
            VoiceSampleUpload(
                client_name="Test",
                sample_text="Too long " * 500,
                sample_source="linkedin",
                word_count=3000,  # > 2000
                file_name="test.txt",
            )

    def test_voice_sample_batch_validation(self):
        """Test VoiceSampleBatch validation"""
        samples = [
            VoiceSampleUpload(
                client_name="Test",
                sample_text="Sample text. " * 50,
                sample_source="linkedin",
                word_count=200,
                file_name="sample1.txt",
            ),
            VoiceSampleUpload(
                client_name="Test",
                sample_text="Sample text. " * 50,
                sample_source="blog",
                word_count=300,
                file_name="sample2.txt",
            ),
        ]

        batch = VoiceSampleBatch(client_name="Test", samples=samples, total_words=500)

        assert batch.is_valid()  # 500 words >= 500 minimum
        assert len(batch.samples) == 2

    def test_store_and_retrieve_voice_samples(self):
        """Test storing and retrieving voice samples from database"""
        # Create sample
        sample = VoiceSampleUpload(
            client_name=self.test_client,
            sample_text="This is a test voice sample for integration testing. " * 20,
            sample_source="linkedin",
            word_count=200,
            file_name="test_sample.txt",
        )

        # Store sample
        sample_id = self.db.store_voice_sample_upload(sample)
        assert sample_id > 0

        # Retrieve samples
        retrieved = self.db.get_voice_sample_uploads(self.test_client)
        assert len(retrieved) == 1
        assert retrieved[0].client_name == self.test_client
        assert retrieved[0].word_count == 200

        # Get stats
        stats = self.db.get_voice_sample_upload_stats(self.test_client)
        assert stats["sample_count"] == 1
        assert stats["total_words"] == 200

    def test_delete_voice_samples(self):
        """Test deleting voice samples"""
        # Create and store sample
        sample = VoiceSampleUpload(
            client_name=self.test_client,
            sample_text="Test " * 50,
            sample_source="blog",
            word_count=150,
            file_name="delete_test.txt",
        )
        self.db.store_voice_sample_upload(sample)

        # Verify exists
        stats = self.db.get_voice_sample_upload_stats(self.test_client)
        assert stats["sample_count"] == 1

        # Delete
        count = self.db.delete_voice_sample_uploads(self.test_client)
        assert count == 1

        # Verify deleted
        stats = self.db.get_voice_sample_upload_stats(self.test_client)
        assert stats["sample_count"] == 0


class TestFileParser:
    """Test file parsing utilities"""

    def test_validate_sample_text(self):
        """Test sample text validation"""
        # Valid sample
        valid_text = "This is a valid sample text. " * 50  # ~250 words
        is_valid, error = validate_sample_text(valid_text)
        assert is_valid
        assert error is None

        # Too short
        short_text = "Too short"
        is_valid, error = validate_sample_text(short_text)
        assert not is_valid
        assert "too short" in error.lower()

        # Empty
        is_valid, error = validate_sample_text("")
        assert not is_valid
        assert "empty" in error.lower()

    def test_extract_text_from_file(self):
        """Test extracting text from various file formats"""
        # Test with temporary text file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            test_text = "This is test content. " * 50
            f.write(test_text)
            temp_path = Path(f.name)

        try:
            text, word_count = extract_text_from_file(temp_path)
            assert len(text) > 0
            assert word_count >= 100
        finally:
            temp_path.unlink()


class TestVoiceMatcher:
    """Test voice matching functionality"""

    def test_voice_match_calculation(self):
        """Test voice match score calculation"""
        matcher = VoiceMatcher()
        analyzer = VoiceAnalyzer()

        # Create reference voice guide from samples
        reference_samples = [
            "This is professional business content with clear structure. " * 10,
            "We help companies achieve their goals through innovative solutions. " * 10,
        ]

        reference_voice = analyzer.analyze_voice_samples(
            samples=reference_samples, client_name="Test Client", source="linkedin"
        )

        # Create generated posts (similar style)
        generated_posts = [
            Post(
                content="Our platform helps businesses streamline their operations. " * 8,
                template_id=1,
                template_name="Test",
                variant=1,
                client_name="Test Client",
            )
        ]

        # Calculate match
        match_report = matcher.calculate_match_score(
            generated_posts=generated_posts, reference_voice_guide=reference_voice
        )

        assert match_report is not None
        assert 0.0 <= match_report.match_score <= 1.0
        assert match_report.readability_score is not None
        assert match_report.word_count_score is not None

    def test_voice_match_components(self):
        """Test individual voice match components"""
        matcher = VoiceMatcher()

        # Test readability comparison
        from src.models.voice_guide import EnhancedVoiceGuide

        voice_guide = EnhancedVoiceGuide(
            company_name="Test",
            generated_from_posts=1,
            average_readability_score=70.0,
            average_word_count=200,
            voice_archetype="Expert",
        )

        posts = [
            Post(
                content="Professional content with similar readability. " * 20,
                template_id=1,
                template_name="Test",
                variant=1,
                client_name="Test",
            )
        ]

        score = matcher._compare_readability(posts, 70.0)
        assert score.component == "Readability"
        assert 0.0 <= score.score <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
