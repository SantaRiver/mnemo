"""LLM-based parser using OpenAI API."""

import json
import time
from typing import Any, Dict, List, Optional

import httpx
from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from nlp_service.config.settings import Settings
from nlp_service.domain.models import ActionType, LLMParseResult, RawAction


class LLMActionSchema(BaseModel):
    """Schema for LLM response action."""

    category: str
    subcategory: Optional[str] = None
    action: str
    type: str  # will be validated to ActionType
    estimated_time_minutes: int
    confidence: float
    achievement_weight: Optional[int] = None


class LLMResponseSchema(BaseModel):
    """Schema for LLM response."""

    actions: List[LLMActionSchema]


class OpenAILLMParser:
    """LLM parser using OpenAI API."""

    def __init__(self, settings: Settings) -> None:
        """Initialize LLM parser.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            timeout=settings.llm_timeout_seconds
        )
        self.system_prompt = self._build_system_prompt()
        self.examples = self._build_examples()

    async def parse_with_llm(self, text: str) -> LLMParseResult:
        """Parse text using LLM.
        
        Args:
            text: Input text
            
        Returns:
            LLMParseResult with extracted actions
        """
        start_time = time.time()
        
        try:
            response = await self._call_llm_with_retry(text)
            actions = self._parse_response(response)
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Calculate confidence
            confidence = self._calculate_confidence(actions)
            
            # Extract token usage
            tokens_used = response.usage.total_tokens if response.usage else None
            
            return LLMParseResult(
                actions=actions,
                confidence=confidence,
                latency_ms=latency_ms,
                model_name=self.settings.openai_model,
                tokens_used=tokens_used
            )
            
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            return LLMParseResult(
                actions=[],
                confidence=0.0,
                latency_ms=latency_ms,
                errors=[f"LLM parsing failed: {str(e)}"]
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=2),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPError))
    )
    async def _call_llm_with_retry(self, text: str) -> Any:
        """Call LLM with retry logic.
        
        Args:
            text: Input text
            
        Returns:
            LLM response
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": self._build_user_prompt(text)}
        ]
        
        response = await self.client.chat.completions.create(
            model=self.settings.openai_model,
            messages=messages,
            temperature=self.settings.openai_temperature,
            max_tokens=self.settings.openai_max_tokens,
            response_format={"type": "json_object"}
        )
        
        return response

    def _parse_response(self, response: Any) -> List[RawAction]:
        """Parse LLM response into RawActions.
        
        Args:
            response: LLM API response
            
        Returns:
            List of RawAction objects
        """
        try:
            content = response.choices[0].message.content
            data = json.loads(content)
            
            # Validate with pydantic
            parsed = LLMResponseSchema(**data)
            
            # Convert to RawAction
            actions = []
            for llm_action in parsed.actions:
                # Validate and convert type
                try:
                    action_type = ActionType(llm_action.type)
                except ValueError:
                    # Default to activity if invalid
                    action_type = ActionType.ACTIVITY
                
                action = RawAction(
                    category=llm_action.category,
                    subcategory=llm_action.subcategory,
                    action=llm_action.action,
                    type=action_type,
                    estimated_time_minutes=llm_action.estimated_time_minutes,
                    confidence=min(max(llm_action.confidence, 0.0), 1.0),
                    achievement_weight=llm_action.achievement_weight,
                    source="llm"
                )
                actions.append(action)
            
            return actions
            
        except (json.JSONDecodeError, ValidationError) as e:
            # Try to retry with clarifying prompt
            raise ValueError(f"Invalid LLM response format: {str(e)}")

    def _calculate_confidence(self, actions: List[RawAction]) -> float:
        """Calculate overall confidence.
        
        Args:
            actions: List of actions
            
        Returns:
            Average confidence
        """
        if not actions:
            return 0.0
        
        return sum(a.confidence for a in actions) / len(actions)

    def _build_system_prompt(self) -> str:
        """Build system prompt for LLM.
        
        Returns:
            System prompt string
        """
        return """You are an assistant that extracts structured activities and achievements from a user's daily diary entry in Russian.

Your task:
1. Identify all activities and achievements mentioned in the text
2. For each action, determine:
   - category (e.g., спорт, учёба, готовка, работа, творчество, саморазвитие, социальное, дом)
   - subcategory (optional, e.g., бодибилдинг, математика, программирование)
   - action (short description of what was done)
   - type: "activity" (regular action) or "achievement" (significant accomplishment)
   - estimated_time_minutes (conservative estimate)
   - confidence (0.0 to 1.0, how certain you are)
   - achievement_weight (only for achievements, 5-25 based on significance)

Guidelines:
- Be conservative with time estimates
- Mark as achievement only if it's a significant accomplishment (first time, record, completion, etc.)
- Use confidence < 0.5 for ambiguous items
- Always output valid JSON following the schema
- Do not add extra commentary

Output format (JSON only):
{
  "actions": [
    {
      "category": "string",
      "subcategory": "string or null",
      "action": "string",
      "type": "activity or achievement",
      "estimated_time_minutes": number,
      "confidence": number (0.0-1.0),
      "achievement_weight": number or null (5-25 for achievements)
    }
  ]
}"""

    def _build_user_prompt(self, text: str) -> str:
        """Build user prompt with examples and text.
        
        Args:
            text: User's diary entry
            
        Returns:
            User prompt string
        """
        examples_str = "\n\n".join([
            f"Example {i+1}:\nInput: {ex['input']}\nOutput: {json.dumps(ex['output'], ensure_ascii=False)}"
            for i, ex in enumerate(self.examples[:3])
        ])
        
        return f"""{examples_str}

Now analyze this diary entry:
Input: {text}
Output:"""

    def _build_examples(self) -> List[Dict[str, Any]]:
        """Build example inputs and outputs.
        
        Returns:
            List of example dictionaries
        """
        return [
            {
                "input": "Сходил в зал, пожал сотку, приготовил курочку",
                "output": {
                    "actions": [
                        {
                            "category": "спорт",
                            "subcategory": None,
                            "action": "сходил в зал",
                            "type": "activity",
                            "estimated_time_minutes": 90,
                            "confidence": 0.95,
                            "achievement_weight": None
                        },
                        {
                            "category": "спорт",
                            "subcategory": "бодибилдинг",
                            "action": "пожал сотку",
                            "type": "achievement",
                            "estimated_time_minutes": 5,
                            "confidence": 0.9,
                            "achievement_weight": 15
                        },
                        {
                            "category": "готовка",
                            "subcategory": None,
                            "action": "приготовил курочку",
                            "type": "activity",
                            "estimated_time_minutes": 40,
                            "confidence": 0.9,
                            "achievement_weight": None
                        }
                    ]
                }
            },
            {
                "input": "Читал 2 часа по линейной алгебре, сделал домашку",
                "output": {
                    "actions": [
                        {
                            "category": "учёба",
                            "subcategory": "математика",
                            "action": "читал по линейной алгебре",
                            "type": "activity",
                            "estimated_time_minutes": 120,
                            "confidence": 0.95,
                            "achievement_weight": None
                        },
                        {
                            "category": "учёба",
                            "subcategory": None,
                            "action": "сделал домашку",
                            "type": "activity",
                            "estimated_time_minutes": 60,
                            "confidence": 0.85,
                            "achievement_weight": None
                        }
                    ]
                }
            },
            {
                "input": "Впервые пробежал 10 км без остановок!",
                "output": {
                    "actions": [
                        {
                            "category": "спорт",
                            "subcategory": "кардио",
                            "action": "пробежал 10 км без остановок",
                            "type": "achievement",
                            "estimated_time_minutes": 60,
                            "confidence": 0.95,
                            "achievement_weight": 20
                        }
                    ]
                }
            },
            {
                "input": "Убрался дома, помыл посуду, постирал",
                "output": {
                    "actions": [
                        {
                            "category": "дом",
                            "subcategory": None,
                            "action": "убрался дома",
                            "type": "activity",
                            "estimated_time_minutes": 60,
                            "confidence": 0.9,
                            "achievement_weight": None
                        },
                        {
                            "category": "дом",
                            "subcategory": None,
                            "action": "помыл посуду",
                            "type": "activity",
                            "estimated_time_minutes": 15,
                            "confidence": 0.9,
                            "achievement_weight": None
                        },
                        {
                            "category": "дом",
                            "subcategory": None,
                            "action": "постирал",
                            "type": "activity",
                            "estimated_time_minutes": 30,
                            "confidence": 0.85,
                            "achievement_weight": None
                        }
                    ]
                }
            },
            {
                "input": "Встретился с друзьями, поговорили о жизни",
                "output": {
                    "actions": [
                        {
                            "category": "социальное",
                            "subcategory": None,
                            "action": "встретился с друзьями",
                            "type": "activity",
                            "estimated_time_minutes": 120,
                            "confidence": 0.9,
                            "achievement_weight": None
                        }
                    ]
                }
            }
        ]


class MockLLMParser:
    """Mock LLM parser for testing."""

    async def parse_with_llm(self, text: str) -> LLMParseResult:
        """Mock parse method.
        
        Args:
            text: Input text
            
        Returns:
            Empty LLMParseResult
        """
        return LLMParseResult(
            actions=[],
            confidence=0.0,
            latency_ms=10,
            model_name="mock"
        )
