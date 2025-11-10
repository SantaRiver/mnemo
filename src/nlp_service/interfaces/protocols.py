"""Protocol definitions for dependency injection."""

from typing import Optional, Protocol

from nlp_service.domain.models import LLMParseResult, RawParseResult


class TranscriptionAdapter(Protocol):
    """Interface for transcription services."""

    def transcribe(self, audio_path: str) -> str:
        """Transcribe audio to text."""
        ...


class PreprocessorService(Protocol):
    """Interface for text preprocessing."""

    def preprocess(self, text: str) -> str:
        """Preprocess text (cleaning, PII redaction)."""
        ...


class Parser(Protocol):
    """Interface for parsing services."""

    def parse(self, user_id: int, text: str) -> RawParseResult:
        """Parse text and extract actions."""
        ...


class LLMParser(Protocol):
    """Interface for LLM-based parsing."""

    async def parse_with_llm(self, text: str) -> LLMParseResult:
        """Parse text using LLM."""
        ...


class HistoryLookupService(Protocol):
    """Interface for historical action lookup."""

    def get_average_time(self, user_id: int, action_normalized: str) -> Optional[int]:
        """Get average time for an action from history."""
        ...

    def record_action(
        self, user_id: int, action_normalized: str, time_minutes: int
    ) -> None:
        """Record an action for future reference."""
        ...


class CacheService(Protocol):
    """Interface for caching services."""

    def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        ...

    def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        """Set value in cache."""
        ...

    def delete(self, key: str) -> None:
        """Delete value from cache."""
        ...
