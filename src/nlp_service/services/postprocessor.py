"""Postprocessing service for action normalization and deduplication."""

from typing import List, Optional

from rapidfuzz import fuzz

from nlp_service.domain.models import Action, TimeSource
from nlp_service.services.preprocessor import TextPreprocessor


class PostprocessorService:
    """Service for postprocessing actions."""

    def __init__(self, similarity_threshold: float = 0.85) -> None:
        """Initialize postprocessor.
        
        Args:
            similarity_threshold: Threshold for considering actions as duplicates
        """
        self.similarity_threshold = similarity_threshold
        self.preprocessor = TextPreprocessor(enabled=False)

    def process(self, actions: List[Action]) -> List[Action]:
        """Process actions: normalize, deduplicate, and validate.
        
        Args:
            actions: List of actions to process
            
        Returns:
            Processed list of actions
        """
        if not actions:
            return []
        
        # Normalize action texts
        actions = self._normalize_actions(actions)
        
        # Deduplicate similar actions
        actions = self._deduplicate_actions(actions)
        
        # Validate and fix any issues
        actions = self._validate_actions(actions)
        
        return actions

    def _normalize_actions(self, actions: List[Action]) -> List[Action]:
        """Normalize action texts.
        
        Args:
            actions: List of actions
            
        Returns:
            Actions with normalized texts
        """
        normalized = []
        
        for action in actions:
            # Clean up action text
            normalized_text = action.action.strip()
            
            # Apply synonyms/lemmatization if needed
            normalized_text = self._apply_synonyms(normalized_text)
            
            # Create new action with normalized text
            normalized_action = action.model_copy(
                update={"action": normalized_text}
            )
            normalized.append(normalized_action)
        
        return normalized

    def _apply_synonyms(self, text: str) -> str:
        """Apply synonym replacement.
        
        Args:
            text: Input text
            
        Returns:
            Text with synonyms replaced
        """
        # Simple synonym mapping
        synonyms = {
            "зале": "зал",
            "спортзале": "зал",
            "качалке": "зал",
            "gym": "зал",
            "книжку": "книгу",
            "учебник": "книгу",
        }
        
        text_lower = text.lower()
        for old, new in synonyms.items():
            if old in text_lower:
                text = text.replace(old, new)
                text = text.replace(old.capitalize(), new.capitalize())
        
        return text

    def _deduplicate_actions(self, actions: List[Action]) -> List[Action]:
        """Remove duplicate actions based on similarity.
        
        Args:
            actions: List of actions
            
        Returns:
            Deduplicated list of actions
        """
        if len(actions) <= 1:
            return actions
        
        unique_actions: List[Action] = []
        
        for action in actions:
            # Check if similar action already exists
            is_duplicate = False
            
            for existing in unique_actions:
                if self._are_similar(action, existing):
                    is_duplicate = True
                    # Merge with existing (keep the one with better time source)
                    merged = self._merge_actions(existing, action)
                    # Replace existing with merged
                    idx = unique_actions.index(existing)
                    unique_actions[idx] = merged
                    break
            
            if not is_duplicate:
                unique_actions.append(action)
        
        return unique_actions

    def _are_similar(self, action1: Action, action2: Action) -> bool:
        """Check if two actions are similar.
        
        Args:
            action1: First action
            action2: Second action
            
        Returns:
            True if actions are similar
        """
        # Must be same category and type
        if action1.category != action2.category:
            return False
        
        if action1.type != action2.type:
            return False
        
        # Check text similarity
        similarity = fuzz.ratio(
            action1.action.lower(),
            action2.action.lower()
        ) / 100.0
        
        return similarity >= self.similarity_threshold

    def _merge_actions(self, action1: Action, action2: Action) -> Action:
        """Merge two similar actions.
        
        Priority: text > history > model > default for time source
        Higher confidence wins for other fields
        
        Args:
            action1: First action
            action2: Second action
            
        Returns:
            Merged action
        """
        # Determine which action has better time source
        time_priority = {
            TimeSource.TEXT: 4,
            TimeSource.HISTORY: 3,
            TimeSource.MODEL: 2,
            TimeSource.DEFAULT: 1
        }
        
        if time_priority[action1.time_source] >= time_priority[action2.time_source]:
            better_time_action = action1
        else:
            better_time_action = action2
        
        # Use action with higher confidence for other fields
        better_confidence_action = action1 if action1.confidence >= action2.confidence else action2
        
        # Merge: use better time source for time, better confidence for rest
        return Action(
            category=better_confidence_action.category,
            subcategory=better_confidence_action.subcategory or better_time_action.subcategory,
            action=better_confidence_action.action,
            type=better_confidence_action.type,
            estimated_time_minutes=better_time_action.estimated_time_minutes,
            time_source=better_time_action.time_source,
            confidence=max(action1.confidence, action2.confidence),
            achievement_weight=better_confidence_action.achievement_weight,
            points=better_time_action.points
        )

    def _validate_actions(self, actions: List[Action]) -> List[Action]:
        """Validate and fix any issues in actions.
        
        Args:
            actions: List of actions
            
        Returns:
            Validated actions
        """
        validated = []
        
        for action in actions:
            # Ensure time is positive
            if action.estimated_time_minutes < 0:
                action = action.model_copy(
                    update={"estimated_time_minutes": 10}
                )
            
            # Ensure confidence is in range
            if action.confidence < 0.0:
                action = action.model_copy(update={"confidence": 0.0})
            elif action.confidence > 1.0:
                action = action.model_copy(update={"confidence": 1.0})
            
            # Recalculate points to ensure consistency
            if action.type.value == "achievement":
                correct_points = float(action.achievement_weight or 10)
            else:
                correct_points = float(action.estimated_time_minutes) / 10.0
            
            if abs(action.points - correct_points) > 0.01:
                action = action.model_copy(update={"points": correct_points})
            
            validated.append(action)
        
        return validated
