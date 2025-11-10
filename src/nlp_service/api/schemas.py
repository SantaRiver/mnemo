"""API request and response schemas."""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    """Request schema for text analysis."""

    user_id: int = Field(..., description="User ID", gt=0)
    text: str = Field(..., description="Text to analyze", min_length=1, max_length=10000)
    date: Optional[date] = Field(None, description="Date of the entry (defaults to today)")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "user_id": 12345,
                "text": "Сходил в зал, пожал сотку, приготовил курочку",
                "date": "2025-11-10"
            }
        }


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(default="ok")
    version: str = Field(default="0.1.0")


class StatsResponse(BaseModel):
    """User statistics response."""

    user_id: int
    total_templates: int
    total_actions: int
