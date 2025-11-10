"""Tests for history service."""

import pytest

from nlp_service.services.history_service import InMemoryHistoryService


class TestHistoryService:
    """Tests for InMemoryHistoryService."""

    def test_record_and_retrieve(self, history_service: InMemoryHistoryService) -> None:
        """Test recording and retrieving action."""
        history_service.record_action(
            user_id=1,
            action_normalized="сходил в зал",
            time_minutes=90
        )
        
        avg_time = history_service.get_average_time(1, "сходил в зал")
        assert avg_time == 90

    def test_incremental_average(self, history_service: InMemoryHistoryService) -> None:
        """Test incremental average calculation."""
        history_service.record_action(1, "читал книгу", 60)
        history_service.record_action(1, "читал книгу", 120)
        
        avg_time = history_service.get_average_time(1, "читал книгу")
        assert avg_time == 90  # (60 + 120) / 2

    def test_multiple_users(self, history_service: InMemoryHistoryService) -> None:
        """Test data isolation between users."""
        history_service.record_action(1, "тренировка", 60)
        history_service.record_action(2, "тренировка", 120)
        
        assert history_service.get_average_time(1, "тренировка") == 60
        assert history_service.get_average_time(2, "тренировка") == 120

    def test_nonexistent_action(self, history_service: InMemoryHistoryService) -> None:
        """Test retrieving nonexistent action."""
        result = history_service.get_average_time(1, "несуществующее действие")
        assert result is None

    def test_global_templates(self, history_service: InMemoryHistoryService) -> None:
        """Test global templates (user_id = 0)."""
        history_service.record_action(0, "базовое действие", 30)
        
        # Should be available for any user
        result = history_service.get_average_time(999, "базовое действие")
        assert result == 30

    def test_user_override_global(self, history_service: InMemoryHistoryService) -> None:
        """Test that user-specific overrides global."""
        history_service.record_action(0, "действие", 30)
        history_service.record_action(1, "действие", 60)
        
        # User 1 should get their specific value
        assert history_service.get_average_time(1, "действие") == 60
        
        # Other users should get global value
        assert history_service.get_average_time(2, "действие") == 30
