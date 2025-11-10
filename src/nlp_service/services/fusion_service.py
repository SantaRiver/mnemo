"""Fusion service for combining heuristic and LLM results."""

from typing import List, Optional

from nlp_service.config.settings import Settings
from nlp_service.domain.models import (
    Action,
    ActionType,
    AnalysisMeta,
    AnalysisResult,
    RawAction,
    TimeSource,
)
from nlp_service.interfaces.protocols import HistoryLookupService
from nlp_service.services.preprocessor import TextPreprocessor


class FusionService:
    """Service for fusing heuristic and LLM results with time estimation."""

    def __init__(
        self,
        history_service: HistoryLookupService,
        settings: Settings
    ) -> None:
        """Initialize fusion service.
        
        Args:
            history_service: History lookup service
            settings: Application settings
        """
        self.history_service = history_service
        self.settings = settings
        self.preprocessor = TextPreprocessor(enabled=False)

    def fuse_results(
        self,
        user_id: int,
        heuristic_actions: List[RawAction],
        llm_actions: List[RawAction],
        heuristic_latency_ms: int,
        llm_latency_ms: int
    ) -> List[Action]:
        """Fuse heuristic and LLM results into final actions.
        
        Args:
            user_id: User ID
            heuristic_actions: Actions from heuristic parser
            llm_actions: Actions from LLM parser
            heuristic_latency_ms: Heuristic processing time
            llm_latency_ms: LLM processing time
            
        Returns:
            List of final Action objects
        """
        # Merge actions (prefer LLM for duplicates)
        merged_actions = self._merge_actions(heuristic_actions, llm_actions)
        
        # Enrich with time estimation
        final_actions = []
        for raw_action in merged_actions:
            action = self._enrich_action(user_id, raw_action)
            final_actions.append(action)
        
        return final_actions

    def _merge_actions(
        self,
        heuristic_actions: List[RawAction],
        llm_actions: List[RawAction]
    ) -> List[RawAction]:
        """Merge heuristic and LLM actions, removing duplicates.
        
        Args:
            heuristic_actions: Actions from heuristic parser
            llm_actions: Actions from LLM parser
            
        Returns:
            Merged list of actions
        """
        # If LLM has results, prefer those
        if llm_actions:
            return llm_actions
        
        # Otherwise use heuristic results
        return heuristic_actions

    def _enrich_action(self, user_id: int, raw_action: RawAction) -> Action:
        """Enrich raw action with time estimation and calculate points.
        
        Args:
            user_id: User ID
            raw_action: Raw action to enrich
            
        Returns:
            Enriched Action object
        """
        # Determine time and source using priority: text > history > model > default
        time_minutes, time_source = self._determine_time(user_id, raw_action)
        
        # Ensure achievement weight
        achievement_weight = raw_action.achievement_weight
        if raw_action.type == ActionType.ACHIEVEMENT and achievement_weight is None:
            achievement_weight = self.settings.achievement_default_weight
        
        # Calculate points
        if raw_action.type == ActionType.ACHIEVEMENT:
            points = float(achievement_weight or self.settings.achievement_default_weight)
        else:
            points = float(time_minutes) / 10.0
        
        return Action(
            category=raw_action.category,
            subcategory=raw_action.subcategory,
            action=raw_action.action,
            type=raw_action.type,
            estimated_time_minutes=time_minutes,
            time_source=time_source,
            confidence=raw_action.confidence,
            achievement_weight=achievement_weight,
            points=points
        )

    def _determine_time(
        self,
        user_id: int,
        raw_action: RawAction
    ) -> tuple[int, TimeSource]:
        """Determine time and source using priority rules.
        
        Priority: text > history > model > default
        
        Args:
            user_id: User ID
            raw_action: Raw action
            
        Returns:
            Tuple of (time_minutes, time_source)
        """
        # 1. Text: if time is explicitly provided and confidence is high
        if raw_action.estimated_time_minutes is not None and raw_action.confidence >= 0.7:
            return raw_action.estimated_time_minutes, TimeSource.TEXT
        
        # 2. History: check historical data
        normalized_action = self.preprocessor.normalize_text(raw_action.action)
        history_time = self.history_service.get_average_time(user_id, normalized_action)
        
        if history_time is not None:
            return history_time, TimeSource.HISTORY
        
        # 3. Model: use LLM/heuristic estimate if available
        if raw_action.estimated_time_minutes is not None:
            return raw_action.estimated_time_minutes, TimeSource.MODEL
        
        # 4. Default: fallback to default time
        return self.settings.default_time_minutes, TimeSource.DEFAULT

    def should_use_llm(
        self,
        heuristic_confidence: float,
        heuristic_action_count: int
    ) -> bool:
        """Determine if LLM should be called based on heuristic results.
        
        Args:
            heuristic_confidence: Confidence from heuristic parser
            heuristic_action_count: Number of actions found by heuristic
            
        Returns:
            True if LLM should be called
        """
        # Use LLM if heuristics found nothing
        if heuristic_action_count == 0:
            return True
        
        # Use LLM if heuristic confidence is low
        if heuristic_confidence < self.settings.heuristic_confidence_threshold:
            return True
        
        # Skip LLM if heuristics are confident
        return False
