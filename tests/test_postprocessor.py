"""Tests for postprocessor service."""

import pytest

from nlp_service.domain.models import Action, ActionType, TimeSource
from nlp_service.services.postprocessor import PostprocessorService


class TestPostprocessorService:
    """Tests for PostprocessorService."""

    @pytest.fixture
    def postprocessor(self) -> PostprocessorService:
        """Create postprocessor.
        
        Returns:
            PostprocessorService instance
        """
        return PostprocessorService()

    def test_normalize_actions(self, postprocessor: PostprocessorService) -> None:
        """Test action normalization."""
        actions = [
            Action(
                category="спорт",
                action="  сходил в зал  ",
                type=ActionType.ACTIVITY,
                estimated_time_minutes=90,
                time_source=TimeSource.MODEL,
                confidence=0.9,
                points=9.0
            )
        ]
        
        result = postprocessor.process(actions)
        
        assert result[0].action == "сходил в зал"

    def test_deduplicate_similar_actions(
        self,
        postprocessor: PostprocessorService
    ) -> None:
        """Test deduplication of similar actions."""
        actions = [
            Action(
                category="спорт",
                action="сходил в зал",
                type=ActionType.ACTIVITY,
                estimated_time_minutes=90,
                time_source=TimeSource.TEXT,
                confidence=0.9,
                points=9.0
            ),
            Action(
                category="спорт",
                action="сходил в зал",
                type=ActionType.ACTIVITY,
                estimated_time_minutes=60,
                time_source=TimeSource.MODEL,
                confidence=0.8,
                points=6.0
            )
        ]
        
        result = postprocessor.process(actions)
        
        # Should merge into one action
        assert len(result) == 1
        
        # Should prefer TEXT time source
        assert result[0].time_source == TimeSource.TEXT
        assert result[0].estimated_time_minutes == 90

    def test_validate_negative_time(self, postprocessor: PostprocessorService) -> None:
        """Test validation of negative time."""
        actions = [
            Action(
                category="работа",
                action="встреча",
                type=ActionType.ACTIVITY,
                estimated_time_minutes=-10,
                time_source=TimeSource.DEFAULT,
                confidence=0.5,
                points=0.0
            )
        ]
        
        result = postprocessor.process(actions)
        
        assert result[0].estimated_time_minutes >= 0

    def test_validate_confidence_range(
        self,
        postprocessor: PostprocessorService
    ) -> None:
        """Test confidence validation."""
        actions = [
            Action(
                category="учёба",
                action="читал",
                type=ActionType.ACTIVITY,
                estimated_time_minutes=60,
                time_source=TimeSource.MODEL,
                confidence=1.5,  # Invalid
                points=6.0
            )
        ]
        
        result = postprocessor.process(actions)
        
        assert 0.0 <= result[0].confidence <= 1.0

    def test_no_deduplication_different_categories(
        self,
        postprocessor: PostprocessorService
    ) -> None:
        """Test that different categories are not deduplicated."""
        actions = [
            Action(
                category="спорт",
                action="тренировка",
                type=ActionType.ACTIVITY,
                estimated_time_minutes=90,
                time_source=TimeSource.TEXT,
                confidence=0.9,
                points=9.0
            ),
            Action(
                category="работа",
                action="тренировка",
                type=ActionType.ACTIVITY,
                estimated_time_minutes=60,
                time_source=TimeSource.MODEL,
                confidence=0.8,
                points=6.0
            )
        ]
        
        result = postprocessor.process(actions)
        
        # Should keep both
        assert len(result) == 2

    def test_merge_priority(self, postprocessor: PostprocessorService) -> None:
        """Test merge priority for time sources."""
        actions = [
            Action(
                category="спорт",
                action="зал",
                type=ActionType.ACTIVITY,
                estimated_time_minutes=90,
                time_source=TimeSource.TEXT,
                confidence=0.8,
                points=9.0
            ),
            Action(
                category="спорт",
                action="зал",
                type=ActionType.ACTIVITY,
                estimated_time_minutes=120,
                time_source=TimeSource.HISTORY,
                confidence=0.9,
                points=12.0
            )
        ]
        
        result = postprocessor.process(actions)
        
        assert len(result) == 1
        # TEXT has higher priority than HISTORY
        assert result[0].time_source == TimeSource.TEXT
        # But confidence should be the higher one
        assert result[0].confidence == 0.9
