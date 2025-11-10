"""Heuristic-based parser for extracting actions from text."""

import re
import time
from typing import Dict, List, Optional, Set, Tuple

from nlp_service.domain.models import ActionType, RawAction, RawParseResult


class HeuristicParser:
    """Parser using local heuristics, keywords, and regex patterns."""

    def __init__(self) -> None:
        """Initialize heuristic parser with keyword dictionaries."""
        self._category_keywords = self._build_category_keywords()
        self._activity_patterns = self._build_activity_patterns()
        self._achievement_keywords = self._build_achievement_keywords()
        self._time_pattern = self._build_time_pattern()

    def parse(self, user_id: int, text: str) -> RawParseResult:
        """Parse text using heuristic rules.
        
        Args:
            user_id: User ID (for context, not used in heuristics)
            text: Preprocessed text
            
        Returns:
            RawParseResult with extracted actions
        """
        start_time = time.time()
        actions: List[RawAction] = []
        
        # Split into potential action segments
        segments = self._segment_text(text)
        
        for segment in segments:
            # Try to extract action from segment
            action = self._extract_action_from_segment(segment)
            if action:
                actions.append(action)
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Calculate overall confidence
        confidence = self._calculate_confidence(actions)
        
        return RawParseResult(
            actions=actions,
            confidence=confidence,
            latency_ms=latency_ms
        )

    def _segment_text(self, text: str) -> List[str]:
        """Split text into segments (potential actions).
        
        Args:
            text: Input text
            
        Returns:
            List of text segments
        """
        # Split on common delimiters: commas, semicolons, "and", "also"
        segments = re.split(
            r'[,;]|\s+и\s+|\s+а\s+|\s+также\s+|\s+потом\s+',
            text,
            flags=re.IGNORECASE
        )
        
        # Clean and filter
        segments = [s.strip() for s in segments if s.strip()]
        
        return segments

    def _extract_action_from_segment(self, segment: str) -> Optional[RawAction]:
        """Extract action from a text segment.
        
        Args:
            segment: Text segment
            
        Returns:
            RawAction if found, None otherwise
        """
        # Detect category
        category, subcategory = self._detect_category(segment)
        
        if not category:
            return None
        
        # Detect if achievement
        is_achievement, achievement_weight = self._detect_achievement(segment)
        action_type = ActionType.ACHIEVEMENT if is_achievement else ActionType.ACTIVITY
        
        # Extract time
        time_minutes = self._extract_time(segment)
        
        # Calculate confidence
        confidence = self._calculate_action_confidence(
            category, time_minutes, is_achievement
        )
        
        # Clean action text
        action_text = self._clean_action_text(segment)
        
        return RawAction(
            category=category,
            subcategory=subcategory,
            action=action_text,
            type=action_type,
            estimated_time_minutes=time_minutes,
            confidence=confidence,
            achievement_weight=achievement_weight,
            source="heuristic"
        )

    def _detect_category(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """Detect category and subcategory from text.
        
        Args:
            text: Input text
            
        Returns:
            Tuple of (category, subcategory)
        """
        text_lower = text.lower()
        
        for category, data in self._category_keywords.items():
            keywords = data.get("keywords", [])
            subcategories = data.get("subcategories", {})
            
            # Check main category keywords
            for keyword in keywords:
                if keyword in text_lower:
                    # Check for subcategory
                    for subcat, subcat_keywords in subcategories.items():
                        for subcat_kw in subcat_keywords:
                            if subcat_kw in text_lower:
                                return category, subcat
                    return category, None
        
        return None, None

    def _detect_achievement(self, text: str) -> Tuple[bool, Optional[int]]:
        """Detect if text describes an achievement.
        
        Args:
            text: Input text
            
        Returns:
            Tuple of (is_achievement, weight)
        """
        text_lower = text.lower()
        
        for keyword, weight in self._achievement_keywords.items():
            if keyword in text_lower:
                return True, weight
        
        return False, None

    def _extract_time(self, text: str) -> Optional[int]:
        """Extract time duration from text.
        
        Args:
            text: Input text
            
        Returns:
            Time in minutes or None
        """
        match = self._time_pattern.search(text)
        
        if not match:
            return None
        
        value = int(match.group(1))
        unit = match.group(2).lower()
        
        # Convert to minutes
        if 'ч' in unit or 'hour' in unit:
            return value * 60
        elif 'мин' in unit or 'min' in unit:
            return value
        elif 'сек' in unit or 'sec' in unit:
            return max(1, value // 60)
        
        return None

    def _calculate_action_confidence(
        self,
        category: Optional[str],
        time_minutes: Optional[int],
        is_achievement: bool
    ) -> float:
        """Calculate confidence for extracted action.
        
        Args:
            category: Detected category
            time_minutes: Extracted time
            is_achievement: Whether it's an achievement
            
        Returns:
            Confidence score
        """
        confidence = 0.5  # Base confidence
        
        if category:
            confidence += 0.2
        
        if time_minutes is not None:
            confidence += 0.2
        
        if is_achievement:
            confidence += 0.1
        
        return min(confidence, 1.0)

    def _calculate_confidence(self, actions: List[RawAction]) -> float:
        """Calculate overall parsing confidence.
        
        Args:
            actions: List of extracted actions
            
        Returns:
            Overall confidence
        """
        if not actions:
            return 0.0
        
        avg_confidence = sum(a.confidence for a in actions) / len(actions)
        return avg_confidence

    def _clean_action_text(self, text: str) -> str:
        """Clean action text.
        
        Args:
            text: Raw action text
            
        Returns:
            Cleaned text
        """
        # Remove time expressions
        text = self._time_pattern.sub('', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()

    def _build_category_keywords(self) -> Dict[str, Dict[str, any]]:
        """Build category keyword dictionary.
        
        Returns:
            Dictionary mapping categories to keywords and subcategories
        """
        return {
            "спорт": {
                "keywords": [
                    "зал", "тренир", "спорт", "бег", "качал", "пресс",
                    "отжим", "подтяг", "присед", "кардио", "йога", "пилатес",
                    "бассейн", "плав", "велосипед", "фитнес"
                ],
                "subcategories": {
                    "бодибилдинг": ["качал", "пожал", "жим", "присед", "становая"],
                    "кардио": ["бег", "бежал", "кардио", "велосипед"],
                    "йога": ["йога", "медитац"]
                }
            },
            "учёба": {
                "keywords": [
                    "учи", "читал", "книг", "курс", "лекци", "учёб",
                    "урок", "задач", "домашк", "экзамен", "конспект",
                    "изуча", "разбир", "математ", "програм", "учебник"
                ],
                "subcategories": {
                    "математика": ["математ", "алгебр", "геометр", "матан"],
                    "программирование": ["програм", "код", "python", "java", "алгоритм"],
                    "языки": ["английск", "немецк", "французск", "язык"]
                }
            },
            "готовка": {
                "keywords": [
                    "готов", "приготов", "сварил", "пожарил", "испёк",
                    "кухн", "рецепт", "еда", "обед", "ужин", "завтрак"
                ],
                "subcategories": {}
            },
            "работа": {
                "keywords": [
                    "работ", "проект", "задач", "встреч", "созвон",
                    "деплой", "фича", "баг", "код ревью", "митинг"
                ],
                "subcategories": {}
            },
            "творчество": {
                "keywords": [
                    "рисов", "писал", "музык", "игра на", "сочин",
                    "творч", "художеств", "стих", "песн", "картин"
                ],
                "subcategories": {
                    "музыка": ["музык", "гитар", "пиани", "играл на"],
                    "рисование": ["рисов", "нарисов", "художеств", "картин"]
                }
            },
            "саморазвитие": {
                "keywords": [
                    "медитиров", "размышл", "психолог", "личностн",
                    "саморазв", "цели", "планиров", "дневник"
                ],
                "subcategories": {}
            },
            "социальное": {
                "keywords": [
                    "встреч", "друзья", "семья", "общен", "позвон",
                    "гости", "компан", "тусовк", "свидан"
                ],
                "subcategories": {}
            },
            "дом": {
                "keywords": [
                    "убир", "уборк", "помыл", "постир", "почист",
                    "порядок", "быт"
                ],
                "subcategories": {}
            }
        }

    def _build_activity_patterns(self) -> List[str]:
        """Build list of activity verb patterns.
        
        Returns:
            List of regex patterns
        """
        return [
            r'сходил',
            r'сделал',
            r'прочитал',
            r'посмотрел',
            r'послушал',
            r'поговорил',
            r'позанимался',
            r'потренировался',
            r'приготовил'
        ]

    def _build_achievement_keywords(self) -> Dict[str, int]:
        """Build achievement keyword dictionary with weights.
        
        Returns:
            Dictionary mapping keywords to weights
        """
        return {
            "впервые": 20,
            "первый раз": 20,
            "рекорд": 25,
            "побил рекорд": 25,
            "личный рекорд": 25,
            "достижени": 15,
            "смог": 10,
            "получилось": 10,
            "наконец": 8,
            "завершил": 12,
            "окончил": 15,
            "сдал экзамен": 20,
            "защитил": 20
        }

    def _build_time_pattern(self) -> re.Pattern[str]:
        """Build regex pattern for time extraction.
        
        Returns:
            Compiled regex pattern
        """
        return re.compile(
            r'(\d+)\s*'
            r'(час(?:а|ов)?|ч\.?|'
            r'минут(?:а|ы|)?|мин\.?|'
            r'секунд(?:а|ы|)?|сек\.?)',
            re.IGNORECASE
        )
