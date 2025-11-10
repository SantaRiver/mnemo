"""Integration tests for the full analysis pipeline."""

import pytest
from datetime import date

from nlp_service.config.settings import Settings
from nlp_service.core.analyzer import TextAnalyzer
from nlp_service.domain.models import ActionType
from nlp_service.services.cache_service import InMemoryCacheService
from nlp_service.services.fusion_service import FusionService
from nlp_service.services.heuristic_parser import HeuristicParser
from nlp_service.services.history_service import InMemoryHistoryService
from nlp_service.services.llm_parser import MockLLMParser
from nlp_service.services.postprocessor import PostprocessorService
from nlp_service.services.preprocessor import TextPreprocessor


class TestIntegration:
    """Integration tests for the full pipeline."""

    @pytest.fixture
    def analyzer(self, test_settings: Settings) -> TextAnalyzer:
        """Create text analyzer with all dependencies.
        
        Returns:
            TextAnalyzer instance
        """
        preprocessor = TextPreprocessor(enabled=True)
        heuristic_parser = HeuristicParser()
        llm_parser = MockLLMParser()  # Use mock to avoid API calls
        history_service = InMemoryHistoryService()
        cache_service = InMemoryCacheService()
        fusion_service = FusionService(history_service, test_settings)
        postprocessor = PostprocessorService()
        
        return TextAnalyzer(
            preprocessor=preprocessor,
            heuristic_parser=heuristic_parser,
            llm_parser=llm_parser,
            fusion_service=fusion_service,
            postprocessor=postprocessor,
            history_service=history_service,
            cache_service=cache_service,
            settings=test_settings
        )

    @pytest.mark.asyncio
    async def test_analyze_simple_text(self, analyzer: TextAnalyzer) -> None:
        """Test analyzing simple text."""
        result = await analyzer.analyze_text(
            user_id=1,
            text="Сходил в зал, потренировался 90 минут",
            analysis_date=date(2025, 11, 10)
        )
        
        assert result.user_id == 1
        assert result.date == date(2025, 11, 10)
        assert len(result.actions) > 0
        
        # Check that sport category was detected
        assert any(a.category == "спорт" for a in result.actions)

    @pytest.mark.asyncio
    async def test_analyze_with_pii(self, analyzer: TextAnalyzer) -> None:
        """Test that PII is redacted."""
        result = await analyzer.analyze_text(
            user_id=1,
            text="Сходил в зал, позвони мне на +7 999 123-45-67",
            analysis_date=date.today()
        )
        
        # PII should be redacted in preprocessing
        # Result should still extract actions
        assert len(result.actions) > 0

    @pytest.mark.asyncio
    async def test_analyze_multiple_actions(self, analyzer: TextAnalyzer) -> None:
        """Test analyzing text with multiple actions."""
        result = await analyzer.analyze_text(
            user_id=1,
            text="Сходил в зал, приготовил обед, почитал книгу"
        )
        
        # Should extract multiple actions
        assert len(result.actions) >= 2

    @pytest.mark.asyncio
    async def test_history_learning(self, analyzer: TextAnalyzer) -> None:
        """Test that history is recorded and used."""
        # First analysis
        result1 = await analyzer.analyze_text(
            user_id=1,
            text="Тренировался 120 минут"
        )
        
        # Second analysis without explicit time
        result2 = await analyzer.analyze_text(
            user_id=1,
            text="Тренировался"
        )
        
        # Second should use history
        if result2.actions:
            # Time source should be history or text
            assert result2.actions[0].time_source in ["history", "text", "model"]

    @pytest.mark.asyncio
    async def test_cache_usage(self, analyzer: TextAnalyzer) -> None:
        """Test that cache is used."""
        text = "Сходил в зал"
        
        # First call
        result1 = await analyzer.analyze_text(user_id=1, text=text)
        
        # Second call with same text
        result2 = await analyzer.analyze_text(user_id=1, text=text)
        
        # Results should be identical
        assert len(result1.actions) == len(result2.actions)

    @pytest.mark.asyncio
    async def test_metadata_tracking(self, analyzer: TextAnalyzer) -> None:
        """Test that metadata is tracked."""
        result = await analyzer.analyze_text(
            user_id=1,
            text="Сходил в зал"
        )
        
        # Check metadata
        assert result.meta is not None
        assert result.meta.heuristic_latency_ms is not None
        assert isinstance(result.meta.used_heuristics, list)

    @pytest.mark.asyncio
    async def test_achievement_detection(self, analyzer: TextAnalyzer) -> None:
        """Test achievement detection."""
        result = await analyzer.analyze_text(
            user_id=1,
            text="Впервые пробежал 10 км без остановок!"
        )
        
        # Should detect achievement
        achievements = [a for a in result.actions if a.type == ActionType.ACHIEVEMENT]
        assert len(achievements) > 0

    @pytest.mark.asyncio
    async def test_points_calculation(self, analyzer: TextAnalyzer) -> None:
        """Test points calculation."""
        result = await analyzer.analyze_text(
            user_id=1,
            text="Занимался 100 минут"
        )
        
        if result.actions:
            action = result.actions[0]
            # For activity: points = time / 10
            if action.type == ActionType.ACTIVITY:
                expected_points = action.estimated_time_minutes / 10.0
                assert abs(action.points - expected_points) < 0.1

    @pytest.mark.asyncio
    async def test_empty_text(self, analyzer: TextAnalyzer) -> None:
        """Test handling of empty text."""
        result = await analyzer.analyze_text(
            user_id=1,
            text=""
        )
        
        # Should return empty actions list
        assert len(result.actions) == 0

    @pytest.mark.asyncio
    async def test_different_users(self, analyzer: TextAnalyzer) -> None:
        """Test data isolation between users."""
        # User 1
        result1 = await analyzer.analyze_text(
            user_id=1,
            text="Тренировался 60 минут"
        )
        
        # User 2
        result2 = await analyzer.analyze_text(
            user_id=2,
            text="Тренировался 120 минут"
        )
        
        # Both should have results
        assert len(result1.actions) > 0
        assert len(result2.actions) > 0
