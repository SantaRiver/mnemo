"""Tests for cache service."""

import pytest

from nlp_service.services.cache_service import InMemoryCacheService


class TestCacheService:
    """Tests for InMemoryCacheService."""

    def test_set_and_get(self, cache_service: InMemoryCacheService) -> None:
        """Test setting and getting value."""
        cache_service.set("key1", "value1")
        result = cache_service.get("key1")
        assert result == "value1"

    def test_get_nonexistent(self, cache_service: InMemoryCacheService) -> None:
        """Test getting nonexistent key."""
        result = cache_service.get("nonexistent")
        assert result is None

    def test_delete(self, cache_service: InMemoryCacheService) -> None:
        """Test deleting value."""
        cache_service.set("key1", "value1")
        cache_service.delete("key1")
        result = cache_service.get("key1")
        assert result is None

    def test_overwrite(self, cache_service: InMemoryCacheService) -> None:
        """Test overwriting value."""
        cache_service.set("key1", "value1")
        cache_service.set("key1", "value2")
        result = cache_service.get("key1")
        assert result == "value2"

    def test_generate_cache_key(self, cache_service: InMemoryCacheService) -> None:
        """Test cache key generation."""
        key1 = cache_service.generate_cache_key(1, "text1")
        key2 = cache_service.generate_cache_key(1, "text1")
        key3 = cache_service.generate_cache_key(1, "text2")
        key4 = cache_service.generate_cache_key(2, "text1")
        
        # Same inputs should generate same key
        assert key1 == key2
        
        # Different inputs should generate different keys
        assert key1 != key3
        assert key1 != key4

    def test_clear(self, cache_service: InMemoryCacheService) -> None:
        """Test clearing cache."""
        cache_service.set("key1", "value1")
        cache_service.set("key2", "value2")
        
        cache_service.clear()
        
        assert cache_service.get("key1") is None
        assert cache_service.get("key2") is None
