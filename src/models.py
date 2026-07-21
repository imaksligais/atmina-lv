from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class AnalysisResult(BaseModel):
    opponent_id: int
    period_start: date
    period_end: date
    sentiment_score: float = Field(ge=-1.0, le=1.0)
    key_topics: list[str]
    notable_quotes: list[str]
    position_shifts: Optional[dict] = None
    brief_markdown: str
    confidence: float = Field(ge=0.0, le=1.0)


class Claim(BaseModel):
    opponent_id: int
    document_id: int
    topic: str
    stance: str
    quote: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    salience: float = Field(ge=0.0, le=1.0)
    source_url: Optional[str] = None
    stated_at: Optional[datetime] = None


class Contradiction(BaseModel):
    opponent_id: int
    claim_old_id: int
    claim_new_id: int
    topic: str
    summary: str
    severity: Literal["minor_shift", "reversal", "direct_contradiction"]
    salience: float = Field(ge=0.0, le=1.0)


class ContextNote(BaseModel):
    opponent_id: Optional[int] = None
    topic: Optional[str] = None
    note_type: Literal["polling", "event", "tip", "context", "correction", "daily_brief", "weekly_brief"]
    content: str
    source: Optional[str] = None
    expires_at: Optional[date] = None
