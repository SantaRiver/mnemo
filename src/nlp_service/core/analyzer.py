"""Main analysis service orchestrating the entire pipeline."""

import json
from datetime import date
from typing import Optional

from nlp_service.config.settings import Settings
from nlp_service.domain.models import AnalysisMeta, AnalysisResult
from nlp_service.interfaces.protocols import CacheService, LLMParser, Parser
from nlp_service.services.fusion_service import FusionService
from nlp_service.services.history_service import SQLiteHistoryService
from nlp_service.services.postprocessor import PostprocessorService
from nlp_service.services.preprocessor import TextPreprocessor


class TextAnalyzer:
    """Main text analysis service."""

    def __init__(
        self,
        preprocessor: TextPreprocessor,
        heuristic_parser: Parser,
        llm_parser: LLMParser,
        fusion_service: FusionService,
        postprocessor: PostprocessorService,
        history_service: SQLiteHistoryService,
        cache_service: Optional[CacheService],
        settings: Settings
    ) -> None:
        """Initialize text analyzer.
        
        Args:
            preprocessor: Text preprocessing service
            heuristic_parser: Heuristic parser
            llm_parser: LLM parser
            fusion_service: Fusion service
            postprocessor: Postprocessor service
            history_service: History lookup service
            cache_service: Cache service (optional)
            settings: Application settings
        """
        self.preprocessor = preprocessor
        self.heuristic_parser = heuristic_parser
        self.llm_parser = llm_parser
        self.fusion_service = fusion_service
        self.postprocessor = postprocessor
        self.history_service = history_service
        self.cache_service = cache_service
        self.settings = settings

    async def analyze_text(
        self,
        user_id: int,
        text: str,
        analysis_date: Optional[date] = None
    ) -> AnalysisResult:
        """Analyze text and extract actions.
        
        Args:
            user_id: User ID
            text: Raw text input
            analysis_date: Date of the entry (defaults to today)
            
        Returns:
            AnalysisResult with extracted actions
        """
        if analysis_date is None:
            analysis_date = date.today()
        
        # Check cache
        if self.cache_service and self.settings.cache_enabled:
            cached = await self._get_cached_result(user_id, text, analysis_date)
            if cached:
                return cached
        
        # Preprocess text
        processed_text = self.preprocessor.preprocess(text)
        
        # Initialize metadata
        meta = AnalysisMeta()
        
        # Step 1: Run heuristic parser
        heuristic_result = self.heuristic_parser.parse(user_id, processed_text)
        meta.heuristic_latency_ms = heuristic_result.latency_ms
        meta.used_heuristics = ["keyword_match", "time_extraction", "category_detection"]
        
        # Step 2: Decide if LLM is needed
        use_llm = self.fusion_service.should_use_llm(
            heuristic_result.confidence,
            len(heuristic_result.actions)
        )
        
        llm_result = None
        if use_llm and self.settings.use_llm_fallback:
            llm_result = await self.llm_parser.parse_with_llm(processed_text)
            meta.used_llm = True
            meta.llm_latency_ms = llm_result.latency_ms
            
            if llm_result.errors:
                meta.errors.extend(llm_result.errors)
        
        # Step 3: Fuse results
        if llm_result:
            fused_actions = self.fusion_service.fuse_results(
                user_id,
                heuristic_result.actions,
                llm_result.actions,
                heuristic_result.latency_ms,
                llm_result.latency_ms
            )
        else:
            fused_actions = self.fusion_service.fuse_results(
                user_id,
                heuristic_result.actions,
                [],
                heuristic_result.latency_ms,
                0
            )
        
        # Step 4: Postprocess (normalize, deduplicate)
        final_actions = self.postprocessor.process(fused_actions)
        
        # Step 5: Record actions in history
        for action in final_actions:
            if action.estimated_time_minutes > 0:
                self.history_service.record_action(
                    user_id,
                    action.action,
                    action.estimated_time_minutes
                )
        
        # Create result
        result = AnalysisResult(
            user_id=user_id,
            date=analysis_date,
            raw_text=None,  # Don't include raw text in response for privacy
            actions=final_actions,
            meta=meta
        )
        
        # Cache result
        if self.cache_service and self.settings.cache_enabled:
            await self._cache_result(user_id, text, result)
        
        return result

    async def _get_cached_result(
        self,
        user_id: int,
        text: str,
        analysis_date: date
    ) -> Optional[AnalysisResult]:
        """Get cached analysis result.
        
        Args:
            user_id: User ID
            text: Input text
            analysis_date: Analysis date
            
        Returns:
            Cached result or None
        """
        if not self.cache_service:
            return None
        
        normalized_text = self.preprocessor.normalize_text(text)
        cache_key = self.cache_service.generate_cache_key(user_id, normalized_text)
        
        cached_json = self.cache_service.get(cache_key)
        if cached_json:
            try:
                data = json.loads(cached_json)
                return AnalysisResult(**data)
            except Exception:
                return None
        
        return None

    async def _cache_result(
        self,
        user_id: int,
        text: str,
        result: AnalysisResult
    ) -> None:
        """Cache analysis result.
        
        Args:
            user_id: User ID
            text: Input text
            result: Analysis result
        """
        if not self.cache_service:
            return
        
        normalized_text = self.preprocessor.normalize_text(text)
        cache_key = self.cache_service.generate_cache_key(user_id, normalized_text)
        
        try:
            result_json = result.model_dump_json()
            self.cache_service.set(
                cache_key,
                result_json,
                ttl=self.settings.cache_ttl_seconds
            )
        except Exception:
            pass  # Fail silently on cache errors
