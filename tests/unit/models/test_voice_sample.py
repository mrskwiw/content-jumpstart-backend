"""Unit tests for Voice Sample models"""

import pytest
from datetime import datetime
from pydantic import ValidationError
from src.models.voice_sample import (
    VoiceSampleUpload,
    VoiceMatchComponentScore,
    VoiceMatchReport,
    VoiceSampleBatch,
)


class TestVoiceSampleUpload:
    """Test suite for VoiceSampleUpload model"""

    @pytest.fixture
    def valid_sample_data(self):
        """Valid sample upload data"""
        return {
            "client_name": "Test Client",
            "sample_text": "This is a test sample with enough words to meet the minimum requirement. "
            * 20,
            "sample_source": "linkedin",
            "word_count": 150,
            "file_name": "sample1.txt",
        }

    def test_voice_sample_upload_initialization(self, valid_sample_data):
        """Test voice sample can be initialized with valid data"""
        sample = VoiceSampleUpload(**valid_sample_data)

        assert sample.client_name == "Test Client"
        assert sample.sample_source == "linkedin"
        assert sample.word_count == 150
        assert sample.file_name == "sample1.txt"
        assert isinstance(sample.upload_date, datetime)

    def test_default_upload_date(self, valid_sample_data):
        """Test upload_date defaults to current timestamp"""
        sample = VoiceSampleUpload(**valid_sample_data)

        assert isinstance(sample.upload_date, datetime)
        time_diff = (datetime.now() - sample.upload_date).total_seconds()
        assert time_diff < 60  # Within last minute

    def test_validate_source_lowercase(self, valid_sample_data):
        """Test sample_source is converted to lowercase"""
        valid_sample_data["sample_source"] = "LINKEDIN"
        sample = VoiceSampleUpload(**valid_sample_data)

        assert sample.sample_source == "linkedin"

    def test_validate_source_allowed_values(self, valid_sample_data):
        """Test all allowed source values"""
        allowed_sources = ["linkedin", "blog", "twitter", "email", "mixed", "other"]

        for source in allowed_sources:
            valid_sample_data["sample_source"] = source
            sample = VoiceSampleUpload(**valid_sample_data)
            assert sample.sample_source == source

    def test_validate_source_invalid_value(self, valid_sample_data):
        """Test invalid source raises ValidationError"""
        valid_sample_data["sample_source"] = "invalid_source"

        with pytest.raises(ValidationError) as exc_info:
            VoiceSampleUpload(**valid_sample_data)

        assert "Invalid source" in str(exc_info.value)

    def test_validate_word_count_minimum(self, valid_sample_data):
        """Test word count below minimum raises error"""
        valid_sample_data["word_count"] = 50

        with pytest.raises(ValidationError) as exc_info:
            VoiceSampleUpload(**valid_sample_data)

        assert "at least 100 words" in str(exc_info.value)

    def test_validate_word_count_maximum(self, valid_sample_data):
        """Test word count above maximum raises error"""
        valid_sample_data["word_count"] = 2500

        with pytest.raises(ValidationError) as exc_info:
            VoiceSampleUpload(**valid_sample_data)

        assert "exceeds maximum 2,000 words" in str(exc_info.value)

    def test_validate_word_count_boundary_values(self, valid_sample_data):
        """Test boundary values for word count"""
        # Minimum boundary
        valid_sample_data["word_count"] = 100
        sample = VoiceSampleUpload(**valid_sample_data)
        assert sample.word_count == 100

        # Maximum boundary
        valid_sample_data["word_count"] = 2000
        sample = VoiceSampleUpload(**valid_sample_data)
        assert sample.word_count == 2000

    def test_preview_short_text(self):
        """Test preview for text shorter than 200 chars"""
        sample = VoiceSampleUpload(
            client_name="Test",
            sample_text="Short text",
            sample_source="linkedin",
            word_count=100,
            file_name="test.txt",
        )

        assert sample.preview == "Short text"

    def test_preview_long_text(self):
        """Test preview truncates long text"""
        long_text = "A" * 300
        sample = VoiceSampleUpload(
            client_name="Test",
            sample_text=long_text,
            sample_source="linkedin",
            word_count=100,
            file_name="test.txt",
        )

        assert len(sample.preview) == 203  # 200 chars + "..."
        assert sample.preview.endswith("...")
        assert sample.preview.startswith("AAA")

    def test_to_dict(self, valid_sample_data):
        """Test conversion to dictionary"""
        sample = VoiceSampleUpload(**valid_sample_data)
        data = sample.to_dict()

        assert data["client_name"] == "Test Client"
        assert data["sample_source"] == "linkedin"
        assert data["word_count"] == 150
        assert isinstance(data["upload_date"], str)  # Should be ISO format

    def test_from_dict(self, valid_sample_data):
        """Test creation from dictionary"""
        sample = VoiceSampleUpload(**valid_sample_data)
        data = sample.to_dict()

        # Create new sample from dict
        new_sample = VoiceSampleUpload.from_dict(data)

        assert new_sample.client_name == sample.client_name
        assert new_sample.sample_source == sample.sample_source
        assert new_sample.word_count == sample.word_count
        assert isinstance(new_sample.upload_date, datetime)

    def test_roundtrip_to_dict_from_dict(self, valid_sample_data):
        """Test to_dict -> from_dict roundtrip preserves data"""
        original = VoiceSampleUpload(**valid_sample_data)
        roundtrip = VoiceSampleUpload.from_dict(original.to_dict())

        assert original.client_name == roundtrip.client_name
        assert original.sample_text == roundtrip.sample_text
        assert original.sample_source == roundtrip.sample_source
        assert original.word_count == roundtrip.word_count
        assert original.file_name == roundtrip.file_name


class TestVoiceMatchComponentScore:
    """Test suite for VoiceMatchComponentScore model"""

    def test_component_score_initialization(self):
        """Test component score basic initialization"""
        score = VoiceMatchComponentScore(
            component="readability",
            score=0.85,
        )

        assert score.component == "readability"
        assert score.score == 0.85
        assert score.target_value is None
        assert score.actual_value is None
        assert score.difference is None

    def test_component_score_with_values(self):
        """Test component score with target/actual values"""
        score = VoiceMatchComponentScore(
            component="word_count",
            score=0.92,
            target_value=200.0,
            actual_value=210.0,
            difference=10.0,
        )

        assert score.target_value == 200.0
        assert score.actual_value == 210.0
        assert score.difference == 10.0


class TestVoiceMatchReport:
    """Test suite for VoiceMatchReport model"""

    @pytest.fixture
    def sample_component_scores(self):
        """Sample component scores"""
        return {
            "readability": VoiceMatchComponentScore(
                component="readability",
                score=0.88,
                target_value=65.0,
                actual_value=68.0,
                difference=3.0,
            ),
            "word_count": VoiceMatchComponentScore(
                component="word_count",
                score=0.95,
                target_value=200.0,
                actual_value=205.0,
                difference=5.0,
            ),
            "archetype": VoiceMatchComponentScore(
                component="archetype",
                score=0.92,
            ),
            "phrase_usage": VoiceMatchComponentScore(
                component="phrase_usage",
                score=0.85,
            ),
        }

    def test_voice_match_report_initialization(self, sample_component_scores):
        """Test voice match report initialization"""
        report = VoiceMatchReport(
            client_name="Test Client",
            match_score=0.90,
            readability_score=sample_component_scores["readability"],
            word_count_score=sample_component_scores["word_count"],
            archetype_score=sample_component_scores["archetype"],
            phrase_usage_score=sample_component_scores["phrase_usage"],
        )

        assert report.client_name == "Test Client"
        assert report.match_score == 0.90
        assert report.readability_score is not None
        assert isinstance(report.generated_at, datetime)

    def test_match_quality_excellent(self):
        """Test match quality interpretation - Excellent"""
        report = VoiceMatchReport(
            client_name="Test",
            match_score=0.95,
        )
        assert report.match_quality == "Excellent"
        assert report.match_quality_emoji == "🟢"

    def test_match_quality_good(self):
        """Test match quality interpretation - Good"""
        report = VoiceMatchReport(
            client_name="Test",
            match_score=0.85,
        )
        assert report.match_quality == "Good"
        assert report.match_quality_emoji == "🟡"

    def test_match_quality_acceptable(self):
        """Test match quality interpretation - Acceptable"""
        report = VoiceMatchReport(
            client_name="Test",
            match_score=0.75,
        )
        assert report.match_quality == "Acceptable"
        assert report.match_quality_emoji == "🟠"

    def test_match_quality_weak(self):
        """Test match quality interpretation - Weak"""
        report = VoiceMatchReport(
            client_name="Test",
            match_score=0.65,
        )
        assert report.match_quality == "Weak"
        assert report.match_quality_emoji == "🔴"

    def test_match_quality_poor(self):
        """Test match quality interpretation - Poor"""
        report = VoiceMatchReport(
            client_name="Test",
            match_score=0.45,
        )
        assert report.match_quality == "Poor"
        assert report.match_quality_emoji == "🔴"

    def test_match_quality_boundary_90(self):
        """Test boundary at 0.9"""
        report = VoiceMatchReport(client_name="Test", match_score=0.90)
        assert report.match_quality == "Excellent"

        report2 = VoiceMatchReport(client_name="Test", match_score=0.89)
        assert report2.match_quality == "Good"

    def test_to_markdown_basic(self):
        """Test markdown generation with basic report"""
        report = VoiceMatchReport(
            client_name="Test Client",
            match_score=0.88,
        )
        markdown = report.to_markdown()

        assert "# Voice Match Report: Test Client" in markdown
        assert "**Overall Match Score:** 0.88 / 1.00 🟡 (Good)" in markdown
        assert "## Component Scores" in markdown

    def test_to_markdown_with_component_scores(self, sample_component_scores):
        """Test markdown includes component score details"""
        report = VoiceMatchReport(
            client_name="Test Client",
            match_score=0.90,
            readability_score=sample_component_scores["readability"],
            word_count_score=sample_component_scores["word_count"],
        )
        markdown = report.to_markdown()

        assert "### Readability" in markdown
        assert "**Score:** 0.88 / 1.00" in markdown
        assert "- Target: 65.0" in markdown
        assert "- Actual: 68.0" in markdown
        assert "- Difference: 3.0" in markdown

        assert "### Word Count" in markdown
        assert "**Score:** 0.95 / 1.00" in markdown

    def test_to_markdown_with_strengths(self):
        """Test markdown includes strengths section"""
        report = VoiceMatchReport(
            client_name="Test",
            match_score=0.90,
            strengths=[
                "Excellent readability match",
                "Consistent brand archetype",
            ],
        )
        markdown = report.to_markdown()

        assert "## Strengths ✓" in markdown
        assert "- Excellent readability match" in markdown
        assert "- Consistent brand archetype" in markdown

    def test_to_markdown_with_weaknesses(self):
        """Test markdown includes weaknesses section"""
        report = VoiceMatchReport(
            client_name="Test",
            match_score=0.75,
            weaknesses=[
                "Word count slightly high",
                "Some phrase usage mismatches",
            ],
        )
        markdown = report.to_markdown()

        assert "## Areas for Improvement" in markdown
        assert "- Word count slightly high" in markdown
        assert "- Some phrase usage mismatches" in markdown

    def test_to_markdown_with_improvements(self):
        """Test markdown includes recommendations section"""
        report = VoiceMatchReport(
            client_name="Test",
            match_score=0.75,
            improvements=[
                "Reduce average word count by 10%",
                "Use more signature phrases from samples",
            ],
        )
        markdown = report.to_markdown()

        assert "## Recommendations" in markdown
        assert "- Reduce average word count by 10%" in markdown
        assert "- Use more signature phrases from samples" in markdown

    def test_to_markdown_interpretation_guide(self):
        """Test markdown always includes interpretation guide"""
        report = VoiceMatchReport(
            client_name="Test",
            match_score=0.85,
        )
        markdown = report.to_markdown()

        assert "## Match Score Interpretation" in markdown
        assert "**0.9-1.0 (Excellent):**" in markdown
        assert "**0.8-0.89 (Good):**" in markdown
        assert "**0.7-0.79 (Acceptable):**" in markdown
        assert "**<0.6 (Poor):**" in markdown

    def test_to_dict(self, sample_component_scores):
        """Test conversion to dictionary"""
        report = VoiceMatchReport(
            client_name="Test Client",
            project_id="proj_123",
            match_score=0.90,
            readability_score=sample_component_scores["readability"],
            strengths=["Good match"],
            weaknesses=["Minor issues"],
            improvements=["Adjust tone"],
        )
        data = report.to_dict()

        assert data["client_name"] == "Test Client"
        assert data["project_id"] == "proj_123"
        assert data["match_score"] == 0.90
        assert isinstance(data["generated_at"], str)
        assert data["readability_score"]["score"] == 0.88
        assert data["strengths"] == ["Good match"]


class TestVoiceSampleBatch:
    """Test suite for VoiceSampleBatch model"""

    @pytest.fixture
    def sample_uploads(self):
        """Create sample uploads for batch testing"""
        return [
            VoiceSampleUpload(
                client_name="Test",
                sample_text="Sample 1 " * 30,
                sample_source="linkedin",
                word_count=150,
                file_name="sample1.txt",
            ),
            VoiceSampleUpload(
                client_name="Test",
                sample_text="Sample 2 " * 40,
                sample_source="blog",
                word_count=200,
                file_name="sample2.txt",
            ),
            VoiceSampleUpload(
                client_name="Test",
                sample_text="Sample 3 " * 35,
                sample_source="twitter",
                word_count=175,
                file_name="sample3.txt",
            ),
        ]

    def test_batch_initialization(self, sample_uploads):
        """Test batch initialization calculates total words"""
        batch = VoiceSampleBatch(
            client_name="Test Client",
            samples=sample_uploads,
        )

        assert batch.client_name == "Test Client"
        assert batch.total_words == 525  # 150 + 200 + 175
        assert isinstance(batch.upload_date, datetime)

    def test_sample_count_property(self, sample_uploads):
        """Test sample_count property"""
        batch = VoiceSampleBatch(
            client_name="Test",
            samples=sample_uploads,
        )
        assert batch.sample_count == 3

    def test_average_word_count_property(self, sample_uploads):
        """Test average_word_count property"""
        batch = VoiceSampleBatch(
            client_name="Test",
            samples=sample_uploads,
        )
        assert batch.average_word_count == 175.0  # 525 / 3

    def test_average_word_count_empty_batch(self):
        """Test average_word_count with no samples"""
        batch = VoiceSampleBatch(
            client_name="Test",
            samples=[],
        )
        assert batch.average_word_count == 0.0

    def test_sources_property(self, sample_uploads):
        """Test sources property returns unique sources"""
        batch = VoiceSampleBatch(
            client_name="Test",
            samples=sample_uploads,
        )
        sources = batch.sources
        assert len(sources) == 3
        assert "linkedin" in sources
        assert "blog" in sources
        assert "twitter" in sources

    def test_sources_property_duplicates(self):
        """Test sources property deduplicates"""
        samples = [
            VoiceSampleUpload(
                client_name="Test",
                sample_text="A" * 100,
                sample_source="linkedin",
                word_count=100,
                file_name="sample1.txt",
            ),
            VoiceSampleUpload(
                client_name="Test",
                sample_text="B" * 100,
                sample_source="linkedin",
                word_count=100,
                file_name="sample2.txt",
            ),
        ]
        batch = VoiceSampleBatch(client_name="Test", samples=samples)
        assert batch.sources == ["linkedin"]

    def test_is_valid_minimum_words(self):
        """Test is_valid checks minimum total words"""
        samples = [
            VoiceSampleUpload(
                client_name="Test",
                sample_text="A" * 100,
                sample_source="linkedin",
                word_count=250,
                file_name="sample1.txt",
            ),
        ]
        batch = VoiceSampleBatch(client_name="Test", samples=samples)
        assert batch.is_valid() is False  # Below 500 words

    def test_is_valid_maximum_samples(self):
        """Test is_valid checks maximum sample count"""
        samples = [
            VoiceSampleUpload(
                client_name="Test",
                sample_text="A" * 100,
                sample_source="linkedin",
                word_count=100,
                file_name=f"sample{i}.txt",
            )
            for i in range(12)  # 12 samples > 10 max
        ]
        batch = VoiceSampleBatch(client_name="Test", samples=samples)
        assert batch.is_valid() is False

    def test_is_valid_passing(self, sample_uploads):
        """Test is_valid returns True for valid batch"""
        batch = VoiceSampleBatch(
            client_name="Test",
            samples=sample_uploads,
        )
        assert batch.is_valid() is True

    def test_validation_errors_below_minimum(self):
        """Test validation_errors for below minimum words"""
        samples = [
            VoiceSampleUpload(
                client_name="Test",
                sample_text="A" * 100,
                sample_source="linkedin",
                word_count=250,
                file_name="sample1.txt",
            ),
        ]
        batch = VoiceSampleBatch(client_name="Test", samples=samples)
        errors = batch.validation_errors()

        assert len(errors) == 1
        assert "below minimum 500 words" in errors[0]
        assert "250" in errors[0]

    def test_validation_errors_too_many_samples(self):
        """Test validation_errors for too many samples"""
        samples = [
            VoiceSampleUpload(
                client_name="Test",
                sample_text="A" * 100,
                sample_source="linkedin",
                word_count=100,
                file_name=f"sample{i}.txt",
            )
            for i in range(12)
        ]
        batch = VoiceSampleBatch(client_name="Test", samples=samples)
        errors = batch.validation_errors()

        assert any("Too many samples" in err for err in errors)
        assert any("12" in err for err in errors)

    def test_validation_errors_no_samples(self):
        """Test validation_errors for empty batch"""
        batch = VoiceSampleBatch(client_name="Test", samples=[])
        errors = batch.validation_errors()

        assert "No samples provided" in errors
        assert any("below minimum 500 words" in err for err in errors)  # Also fails word count

    def test_validation_errors_valid_batch(self, sample_uploads):
        """Test validation_errors returns empty list for valid batch"""
        batch = VoiceSampleBatch(client_name="Test", samples=sample_uploads)
        errors = batch.validation_errors()
        assert errors == []
