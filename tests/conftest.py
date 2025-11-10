"""Pytest configuration and shared fixtures."""

import pytest

from nlp_service.config.settings import Settings
from nlp_service.services.cache_service import InMemoryCacheService
from nlp_service.services.history_service import InMemoryHistoryService
from nlp_service.services.preprocessor import TextPreprocessor


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings.
    
    Returns:
        Test settings
    """
    return Settings(
        openai_api_key="test-key",
        redis_url="redis://localhost:6379/0",
        cache_enabled=False,
        pii_redaction_enabled=True,
        use_llm_fallback=False,
        database_url="sqlite:///:memory:",
        metrics_enabled=False
    )


@pytest.fixture
def preprocessor() -> TextPreprocessor:
    """Create text preprocessor.
    
    Returns:
        TextPreprocessor instance
    """
    return TextPreprocessor(enabled=True)


@pytest.fixture
def history_service() -> InMemoryHistoryService:
    """Create in-memory history service.
    
    Returns:
        InMemoryHistoryService instance
    """
    return InMemoryHistoryService()


@pytest.fixture
def cache_service() -> InMemoryCacheService:
    """Create in-memory cache service.
    
    Returns:
        InMemoryCacheService instance
    """
    return InMemoryCacheService()
