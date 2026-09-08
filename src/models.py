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
    # Required key, nullable value — mirrors ``db.store_claim``'s signature.
    # `saeima_vote` claims legitimately carry NULL (their provenance runs
    # through saeima_individual_votes → saeima_votes.url, not a document); every
    # other claim_type requires a real document_id, and that rule is enforced in
    # ``db.store_claim`` because it is the only layer that sees `claim_type` —
    # this model deliberately does not carry it. Declaring this `int` until
    # 2026-08-01 meant the model REJECTED a legal vote claim, so the
    # `tools.store_claim` path raised ValidationError while `db.store_claim`
    # accepted the identical row.
    document_id: Optional[int]
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
