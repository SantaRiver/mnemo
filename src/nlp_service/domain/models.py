"""Core domain models for the NLP service."""

from datetime import date
from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator


class ActionType(str, Enum):
    """Type of action."""

    ACTIVITY = "activity"
    ACHIEVEMENT = "achievement"


class TimeSource(str, Enum):
    """Source of time estimation."""

    TEXT = "text"
    HISTORY = "history"
    MODEL = "model"
    DEFAULT = "default"


class Action(BaseModel):
    """Represents a single action extracted from text."""

    category: str = Field(..., description="Main category of the action")
    subcategory: Optional[str] = Field(None, description="Optional subcategory")
    action: str = Field(..., description="Description of the action")
    type: ActionType = Field(..., description="Type of action (activity or achievement)")
    estimated_time_minutes: int = Field(
        ..., ge=0, description="Estimated time in minutes"
    )
    time_source: TimeSource = Field(
        ..., description="Source of the time estimation"
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    achievement_weight: Optional[int] = Field(
        None, ge=0, description="Weight for achievements"
    )
    points: float = Field(..., ge=0.0, description="Calculated points")

    @field_validator("points", mode="before")
    @classmethod
    def calculate_points(cls, v: Any, info: Any) -> float:
        """Calculate points based on type."""
        if v is not None:
            return float(v)
        
        values = info.data
        action_type = values.get("type")
        
        if action_type == ActionType.ACHIEVEMENT:
            weight = values.get("achievement_weight", 10)
            return float(weight)
        else:
            time_minutes = values.get("estimated_time_minutes", 10)
            return float(time_minutes) / 10.0

    class Config:
        """Pydantic config."""

        use_enum_values = True


class AnalysisMeta(BaseModel):
    """Metadata about the analysis process."""

    used_heuristics: List[str] = Field(
        default_factory=list, description="List of heuristics used"
    )
    used_llm: bool = Field(False, description="Whether LLM was used")
    llm_latency_ms: Optional[int] = Field(None, description="LLM latency in milliseconds")
    heuristic_latency_ms: Optional[int] = Field(
        None, description="Heuristic latency in milliseconds"
    )
    errors: List[str] = Field(default_factory=list, description="Any errors encountered")


class AnalysisResult(BaseModel):
    """Complete analysis result."""

    user_id: int = Field(..., description="User ID")
    date: date = Field(..., description="Date of the entry")
    raw_text: Optional[str] = Field(None, description="Original text (optional)")
    actions: List[Action] = Field(default_factory=list, description="Extracted actions")
    meta: AnalysisMeta = Field(
        default_factory=AnalysisMeta, description="Analysis metadata"
    )


class RawAction(BaseModel):
    """Raw action before post-processing."""

    category: str
    subcategory: Optional[str] = None
    action: str
    type: ActionType
    estimated_time_minutes: Optional[int] = None
    confidence: float = Field(ge=0.0, le=1.0)
    achievement_weight: Optional[int] = None
    source: str = Field(default="unknown")  # heuristic, llm, etc.


class RawParseResult(BaseModel):
    """Result from a parser (heuristic or LLM)."""

    actions: List[RawAction] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    latency_ms: int = Field(default=0)
    errors: List[str] = Field(default_factory=list)


class LLMParseResult(RawParseResult):
    """Result specifically from LLM parser."""

    model_name: Optional[str] = None
    tokens_used: Optional[int] = None
