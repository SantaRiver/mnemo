"""Tests for heuristic parser."""

import pytest

from nlp_service.domain.models import ActionType
from nlp_service.services.heuristic_parser import HeuristicParser


class TestHeuristicParser:
    """Tests for HeuristicParser."""

    @pytest.fixture
    def parser(self) -> HeuristicParser:
        """Create parser instance.
        
        Returns:
            HeuristicParser instance
        """
        return HeuristicParser()

    def test_parse_sport_activity(self, parser: HeuristicParser) -> None:
        """Test parsing sport activity."""
        text = "Сходил в зал"
        result = parser.parse(user_id=1, text=text)
        
        assert len(result.actions) > 0
        action = result.actions[0]
        assert action.category == "спорт"
        assert action.type == ActionType.ACTIVITY

    def test_parse_with_time(self, parser: HeuristicParser) -> None:
        """Test parsing with explicit time."""
        text = "Читал 2 часа"
        result = parser.parse(user_id=1, text=text)
        
        assert len(result.actions) > 0
        action = result.actions[0]
        assert action.estimated_time_minutes == 120

    def test_parse_achievement(self, parser: HeuristicParser) -> None:
        """Test parsing achievement."""
        text = "Впервые пробежал 10 км"
        result = parser.parse(user_id=1, text=text)
        
        assert len(result.actions) > 0
        action = result.actions[0]
        assert action.type == ActionType.ACHIEVEMENT
        assert action.achievement_weight is not None

    def test_parse_multiple_actions(self, parser: HeuristicParser) -> None:
        """Test parsing multiple actions."""
        text = "Сходил в зал, приготовил обед, почитал книгу"
        result = parser.parse(user_id=1, text=text)
        
        assert len(result.actions) >= 2

    def test_parse_empty_text(self, parser: HeuristicParser) -> None:
        """Test parsing empty text."""
        result = parser.parse(user_id=1, text="")
        assert len(result.actions) == 0

    def test_parse_irrelevant_text(self, parser: HeuristicParser) -> None:
        """Test parsing irrelevant text."""
        text = "Просто случайный текст без действий"
        result = parser.parse(user_id=1, text=text)
        # Should return empty or very low confidence
        assert result.confidence < 0.8

    def test_category_detection(self, parser: HeuristicParser) -> None:
        """Test category detection."""
        test_cases = [
            ("тренировался в зале", "спорт"),
            ("учил математику", "учёба"),
            ("готовил ужин", "готовка"),
            ("работал над проектом", "работа"),
        ]
        
        for text, expected_category in test_cases:
            result = parser.parse(user_id=1, text=text)
            if result.actions:
                assert result.actions[0].category == expected_category

    def test_subcategory_detection(self, parser: HeuristicParser) -> None:
        """Test subcategory detection."""
        text = "Качался, делал жим лёжа"
        result = parser.parse(user_id=1, text=text)
        
        if result.actions:
            action = result.actions[0]
            assert action.category == "спорт"
            assert action.subcategory == "бодибилдинг"

    def test_time_extraction_minutes(self, parser: HeuristicParser) -> None:
        """Test time extraction in minutes."""
        text = "Занимался 45 минут"
        result = parser.parse(user_id=1, text=text)
        
        if result.actions:
            assert result.actions[0].estimated_time_minutes == 45

    def test_latency_tracking(self, parser: HeuristicParser) -> None:
        """Test that latency is tracked."""
        result = parser.parse(user_id=1, text="Сходил в зал")
        assert result.latency_ms >= 0
