"""Tests for fusion service."""

import pytest

from nlp_service.config.settings import Settings
from nlp_service.domain.models import ActionType, RawAction, TimeSource
from nlp_service.services.fusion_service import FusionService
from nlp_service.services.history_service import InMemoryHistoryService


class TestFusionService:
    """Tests for FusionService."""

    @pytest.fixture
    def fusion_service(
        self,
        history_service: InMemoryHistoryService,
        test_settings: Settings
    ) -> FusionService:
        """Create fusion service.
        
        Returns:
            FusionService instance
        """
        return FusionService(history_service, test_settings)

    def test_fuse_llm_preferred(
        self,
        fusion_service: FusionService
    ) -> None:
        """Test that LLM results are preferred."""
        heuristic_actions = [
            RawAction(
                category="спорт",
                action="в зал",
                type=ActionType.ACTIVITY,
                confidence=0.7
            )
        ]
        
        llm_actions = [
            RawAction(
                category="спорт",
                action="сходил в зал",
                type=ActionType.ACTIVITY,
                confidence=0.9,
                estimated_time_minutes=90
            )
        ]
        
        result = fusion_service.fuse_results(
            user_id=1,
            heuristic_actions=heuristic_actions,
            llm_actions=llm_actions,
            heuristic_latency_ms=100,
            llm_latency_ms=500
        )
        
        assert len(result) == 1
        assert result[0].action == "сходил в зал"

    def test_time_source_priority_text(
        self,
        fusion_service: FusionService
    ) -> None:
        """Test text source has highest priority."""
        raw_action = RawAction(
            category="учёба",
            action="читал книгу",
            type=ActionType.ACTIVITY,
            confidence=0.9,
            estimated_time_minutes=120
        )
        
        action = fusion_service._enrich_action(1, raw_action)
        
        assert action.time_source == TimeSource.TEXT
        assert action.estimated_time_minutes == 120

    def test_time_source_priority_history(
        self,
        fusion_service: FusionService,
        history_service: InMemoryHistoryService
    ) -> None:
        """Test history source priority."""
        # Add history
        history_service.record_action(1, "тренировка", 90)
        
        raw_action = RawAction(
            category="спорт",
            action="тренировка",
            type=ActionType.ACTIVITY,
            confidence=0.6,  # Low confidence, won't use text
            estimated_time_minutes=60
        )
        
        action = fusion_service._enrich_action(1, raw_action)
        
        assert action.time_source == TimeSource.HISTORY
        assert action.estimated_time_minutes == 90

    def test_time_source_default(
        self,
        fusion_service: FusionService
    ) -> None:
        """Test default time source."""
        raw_action = RawAction(
            category="работа",
            action="встреча",
            type=ActionType.ACTIVITY,
            confidence=0.5
        )
        
        action = fusion_service._enrich_action(1, raw_action)
        
        assert action.time_source == TimeSource.DEFAULT
        assert action.estimated_time_minutes == 10  # default

    def test_achievement_weight(
        self,
        fusion_service: FusionService
    ) -> None:
        """Test achievement weight handling."""
        raw_action = RawAction(
            category="спорт",
            action="побил рекорд",
            type=ActionType.ACHIEVEMENT,
            confidence=0.9,
            achievement_weight=25
        )
        
        action = fusion_service._enrich_action(1, raw_action)
        
        assert action.points == 25.0

    def test_points_calculation_activity(
        self,
        fusion_service: FusionService
    ) -> None:
        """Test points calculation for activity."""
        raw_action = RawAction(
            category="учёба",
            action="учил",
            type=ActionType.ACTIVITY,
            confidence=0.9,
            estimated_time_minutes=100
        )
        
        action = fusion_service._enrich_action(1, raw_action)
        
        assert action.points == 10.0  # 100 / 10

    def test_should_use_llm_no_actions(
        self,
        fusion_service: FusionService
    ) -> None:
        """Test LLM should be used when no heuristic actions."""
        should_use = fusion_service.should_use_llm(
            heuristic_confidence=0.0,
            heuristic_action_count=0
        )
        assert should_use is True

    def test_should_use_llm_low_confidence(
        self,
        fusion_service: FusionService
    ) -> None:
        """Test LLM should be used for low confidence."""
        should_use = fusion_service.should_use_llm(
            heuristic_confidence=0.5,
            heuristic_action_count=1
        )
        assert should_use is True

    def test_should_skip_llm_high_confidence(
        self,
        fusion_service: FusionService
    ) -> None:
        """Test LLM should be skipped for high confidence."""
        should_use = fusion_service.should_use_llm(
            heuristic_confidence=0.9,
            heuristic_action_count=2
        )
        assert should_use is False
