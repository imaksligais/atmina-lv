"""Pydantic v2 models for video_ingest JSON contracts."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class Metadata(BaseModel):
    url: str
    title: str
    published_at: str  # ISO 8601 date or datetime
    language: str = "lv"
    duration_seconds: int
    source_domain: str
    uploader: str | None = None


class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str
    words: list[dict[str, Any]] = Field(default_factory=list)


class DiarizedSegment(BaseModel):
    start: float
    end: float
    speaker: str  # "A" / "SPEAKER_05" depending on pyannote raw output


class AlignedSegment(BaseModel):
    start: float
    end: float
    speaker: str
    text: str


class SpeakerMapping(BaseModel):
    pid: int | None
    handle: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: str


class ContextCue(BaseModel):
    speaker: str
    cue_type: Literal[
        "addressed_by_name",
        "self_introduction",
        "formal_phrase",
        "first_speaker_greeting",
        "saeima_role",
    ]
    text: str
    at_seconds: float
    matched_pid: int | None = None  # if cue resolves to specific politician
