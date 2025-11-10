"""Dependency injection container."""

from functools import lru_cache
from typing import Optional

from nlp_service.config.settings import Settings, get_settings
from nlp_service.core.analyzer import TextAnalyzer
from nlp_service.services.cache_service import InMemoryCacheService, RedisCacheService
from nlp_service.services.fusion_service import FusionService
from nlp_service.services.heuristic_parser import HeuristicParser
from nlp_service.services.history_service import SQLiteHistoryService
from nlp_service.services.llm_parser import MockLLMParser, OpenAILLMParser
from nlp_service.services.postprocessor import PostprocessorService
from nlp_service.services.preprocessor import TextPreprocessor


class Container:
    """Dependency injection container."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        """Initialize container.
        
        Args:
            settings: Application settings (optional)
        """
        self.settings = settings or get_settings()
        self._analyzer: Optional[TextAnalyzer] = None

    def get_analyzer(self) -> TextAnalyzer:
        """Get or create TextAnalyzer instance.
        
        Returns:
            TextAnalyzer instance
        """
        if self._analyzer is None:
            self._analyzer = self._create_analyzer()
        return self._analyzer

    def _create_analyzer(self) -> TextAnalyzer:
        """Create TextAnalyzer with all dependencies.
        
        Returns:
            Configured TextAnalyzer instance
        """
        # Create services
        preprocessor = TextPreprocessor(
            enabled=self.settings.pii_redaction_enabled
        )
        
        heuristic_parser = HeuristicParser()
        
        # Create LLM parser (mock if no API key)
        if self.settings.openai_api_key:
            llm_parser = OpenAILLMParser(self.settings)
        else:
            llm_parser = MockLLMParser()
        
        # Create history service
        history_service = SQLiteHistoryService(
            db_path=self.settings.database_url.replace("sqlite:///", "")
        )
        
        # Create cache service
        cache_service = None
        if self.settings.cache_enabled:
            try:
                cache_service = RedisCacheService(
                    redis_url=self.settings.redis_url,
                    ttl=self.settings.cache_ttl_seconds
                )
            except Exception:
                # Fallback to in-memory cache
                cache_service = InMemoryCacheService(
                    ttl=self.settings.cache_ttl_seconds
                )
        
        # Create fusion and postprocessor
        fusion_service = FusionService(history_service, self.settings)
        postprocessor = PostprocessorService()
        
        # Create analyzer
        return TextAnalyzer(
            preprocessor=preprocessor,
            heuristic_parser=heuristic_parser,
            llm_parser=llm_parser,
            fusion_service=fusion_service,
            postprocessor=postprocessor,
            history_service=history_service,
            cache_service=cache_service,
            settings=self.settings
        )


@lru_cache()
def get_container() -> Container:
    """Get singleton container instance.
    
    Returns:
        Container instance
    """
    return Container()


def get_analyzer() -> TextAnalyzer:
    """Dependency for FastAPI route handlers.
    
    Returns:
        TextAnalyzer instance
    """
    container = get_container()
    return container.get_analyzer()
