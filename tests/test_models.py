"""Tests for src/models.py — Pydantic model validation."""

import pytest
from datetime import date
from pydantic import ValidationError
from src.models import (
    AnalysisResult,
    Claim,
    Contradiction,
    ContextNote,
)


class TestClaim:
    def test_valid_claim(self):
        c = Claim(
            opponent_id=1,
            document_id=100,
            topic="NATO",
            stance="Atbalsta NATO",
            confidence=0.85,
            reasoning="Clear statement",
            salience=0.7,
            source_url="https://example.com",
        )
        assert c.confidence == 0.85

    def test_confidence_out_of_range(self):
        with pytest.raises(ValidationError):
            Claim(
                opponent_id=1, document_id=100, topic="x",
                stance="x", confidence=1.5, reasoning="x", salience=0.5,
            )

    def test_salience_out_of_range(self):
        with pytest.raises(ValidationError):
            Claim(
                opponent_id=1, document_id=100, topic="x",
                stance="x", confidence=0.5, reasoning="x", salience=-0.1,
            )

    def test_optional_fields_default_none(self):
        c = Claim(
            opponent_id=1, document_id=100, topic="x",
            stance="x", confidence=0.5, reasoning="x", salience=0.5,
        )
        assert c.quote is None
        assert c.source_url is None
        assert c.stated_at is None


class TestContradiction:
    def test_valid_contradiction(self):
        c = Contradiction(
            opponent_id=1,
            claim_old_id=10,
            claim_new_id=55,
            topic="pārvaldība",
            summary="Said X before, now says Y",
            severity="reversal",
            salience=0.8,
        )
        assert c.severity == "reversal"

    def test_invalid_severity(self):
        with pytest.raises(ValidationError):
            Contradiction(
                opponent_id=1, claim_old_id=10, claim_new_id=55,
                topic="x", summary="x", severity="big_change", salience=0.5,
            )

    def test_all_severity_types_valid(self):
        for sev in ["minor_shift", "reversal", "direct_contradiction"]:
            c = Contradiction(
                opponent_id=1, claim_old_id=1, claim_new_id=2,
                topic="x", summary="x", severity=sev, salience=0.5,
            )
            assert c.severity == sev


class TestContextNote:
    def test_valid_note(self):
        n = ContextNote(
            topic="Imigrācija",
            note_type="context",
            content="Some trend",
            source="https://example.com",
        )
        assert n.note_type == "context"

    def test_all_note_types(self):
        for nt in ["polling", "event", "tip", "context", "correction", "daily_brief", "weekly_brief"]:
            n = ContextNote(note_type=nt, content="test")
            assert n.note_type == nt

    def test_invalid_note_type(self):
        with pytest.raises(ValidationError):
            ContextNote(note_type="invalid", content="test")

    def test_optional_fields(self):
        n = ContextNote(note_type="context", content="test")
        assert n.opponent_id is None
        assert n.topic is None
        assert n.source is None
        assert n.expires_at is None


class TestAnalysisResult:
    def test_valid_analysis(self):
        a = AnalysisResult(
            opponent_id=1,
            period_start=date(2026, 4, 1),
            period_end=date(2026, 4, 7),
            sentiment_score=0.0,
            key_topics=["NATO"],
            notable_quotes=["quote"],
            brief_markdown="Analysis text",
            confidence=0.9,
        )
        assert a.sentiment_score == 0.0

    def test_sentiment_out_of_range(self):
        with pytest.raises(ValidationError):
            AnalysisResult(
                opponent_id=1,
                period_start=date(2026, 4, 1),
                period_end=date(2026, 4, 7),
                sentiment_score=1.5,
                key_topics=[],
                notable_quotes=[],
                brief_markdown="x",
                confidence=0.5,
            )
