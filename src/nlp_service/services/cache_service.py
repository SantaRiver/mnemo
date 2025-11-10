"""Cache service implementations."""

import hashlib
import json
from typing import Optional

import redis


class RedisCacheService:
    """Redis-based cache service."""

    def __init__(self, redis_url: str, ttl: int = 604800) -> None:
        """Initialize Redis cache.
        
        Args:
            redis_url: Redis connection URL
            ttl: Default TTL in seconds (default 7 days)
        """
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.default_ttl = ttl

    def get(self, key: str) -> Optional[str]:
        """Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        try:
            return self.redis_client.get(key)
        except redis.RedisError:
            return None

    def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        """Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: TTL in seconds (uses default if None)
        """
        try:
            ttl = ttl or self.default_ttl
            self.redis_client.setex(key, ttl, value)
        except redis.RedisError:
            pass

    def delete(self, key: str) -> None:
        """Delete value from cache.
        
        Args:
            key: Cache key
        """
        try:
            self.redis_client.delete(key)
        except redis.RedisError:
            pass

    def generate_cache_key(self, user_id: int, text: str) -> str:
        """Generate cache key for text analysis.
        
        Args:
            user_id: User ID
            text: Normalized text
            
        Returns:
            Cache key
        """
        # Create hash of user_id + text
        combined = f"{user_id}:{text}"
        hash_key = hashlib.sha256(combined.encode()).hexdigest()
        return f"nlp:analysis:{hash_key}"


class InMemoryCacheService:
    """In-memory cache for testing."""

    def __init__(self, ttl: int = 604800) -> None:
        """Initialize in-memory cache.
        
        Args:
            ttl: Default TTL in seconds (not enforced in memory)
        """
        self.cache: dict[str, str] = {}
        self.default_ttl = ttl

    def get(self, key: str) -> Optional[str]:
        """Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        return self.cache.get(key)

    def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        """Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: TTL (ignored in memory implementation)
        """
        self.cache[key] = value

    def delete(self, key: str) -> None:
        """Delete value from cache.
        
        Args:
            key: Cache key
        """
        self.cache.pop(key, None)

    def generate_cache_key(self, user_id: int, text: str) -> str:
        """Generate cache key for text analysis.
        
        Args:
            user_id: User ID
            text: Normalized text
            
        Returns:
            Cache key
        """
        combined = f"{user_id}:{text}"
        hash_key = hashlib.sha256(combined.encode()).hexdigest()
        return f"nlp:analysis:{hash_key}"

    def clear(self) -> None:
        """Clear all cache (for testing)."""
        self.cache.clear()
