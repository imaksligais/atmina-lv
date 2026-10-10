"""Tests for src/tools.py — JSON helpers and input validation."""

import json
import sqlite3
import os
import tempfile

import pytest

from src.tools import _json_success, _json_error


def _safe_unlink(path):
    try:
        os.unlink(path)
    except PermissionError:
        pass


@pytest.fixture
def tools_db(monkeypatch):
    """Temp DB + monkeypatch of src.tools.get_db so store_* functions hit it."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = sqlite3.connect(path)
    db.executescript("""
        CREATE TABLE context_notes (
            id INTEGER PRIMARY KEY,
            opponent_id INTEGER,
            topic TEXT,
            note_type TEXT,
            content TEXT,
            source TEXT,
            expires_at TEXT,
            created_at TEXT,
            visual_brief_json TEXT
        );
    """)
    db.commit()
    db.close()

    import src.tools as _tools_mod
    from src.db import get_db as _real_get_db
    monkeypatch.setattr(_tools_mod, "get_db", lambda p=None: _real_get_db(path))

    yield path
    _safe_unlink(path)


class TestJsonSuccess:
    def test_basic_success(self):
        result = json.loads(_json_success())
        assert result["status"] == "success"

    def test_success_with_data(self):
        result = json.loads(_json_success({"claim_id": 42}))
        assert result["status"] == "success"
        assert result["claim_id"] == 42

    def test_success_with_latvian_text(self):
        result = json.loads(_json_success({"msg": "Pozīcija saglabāta"}))
        assert "Pozīcija" in result["msg"]

    def test_success_returns_valid_json(self):
        raw = _json_success({"nested": {"key": "value"}})
        parsed = json.loads(raw)
        assert parsed["nested"]["key"] == "value"


class TestJsonError:
    def test_basic_error(self):
        result = json.loads(_json_error("Something went wrong"))
        assert result["status"] == "error"
        assert result["message"] == "Something went wrong"

    def test_error_with_latvian(self):
        result = json.loads(_json_error("Politiķis nav atrasts"))
        assert "nav atrasts" in result["message"]

    def test_error_returns_valid_json(self):
        raw = _json_error("test")
        json.loads(raw)  # should not raise


class TestStoreClaimValidation:
    """Test that store_claim validates via Pydantic before DB interaction."""

    def test_invalid_confidence_returns_error(self):
        from src.tools import store_claim
        result = json.loads(store_claim(
            opponent_id=1, document_id=1, topic="NATO",
            stance="test", confidence=2.0, reasoning="x", salience=0.5,
        ))
        assert result["status"] == "error"

    def test_invalid_salience_returns_error(self):
        from src.tools import store_claim
        result = json.loads(store_claim(
            opponent_id=1, document_id=1, topic="NATO",
            stance="test", confidence=0.5, reasoning="x", salience=-1.0,
        ))
        assert result["status"] == "error"


class TestStoreContradictionValidation:
    """Test that store_contradiction validates severity via Pydantic."""

    def test_invalid_severity_returns_error(self):
        from src.tools import store_contradiction
        result = json.loads(store_contradiction(
            opponent_id=1, old_claim_id=1, new_claim_id=2,
            topic="NATO", summary="test", severity="huge_change", salience=0.5,
        ))
        assert result["status"] == "error"

    def test_invalid_salience_returns_error(self):
        from src.tools import store_contradiction
        result = json.loads(store_contradiction(
            opponent_id=1, old_claim_id=1, new_claim_id=2,
            topic="NATO", summary="test", severity="reversal", salience=5.0,
        ))
        assert result["status"] == "error"


class TestStoreContextNoteUpsert:
    """Same-day daily_brief/weekly_brief must overwrite existing row, not
    accumulate duplicates (CLAUDE.md contract: 'Same-day briefs overwritten').
    Context-type notes remain INSERT-only (CLAUDE.md Pipeline Invariant #8)."""

    _VALID_BRIEF = (
        "# Dienas analīze — 2026-04-20\n\n"
        "## Galvenais\n\nNaratīvs.\n\n"
        "## Aktīvākie politiķi\n\n| Politiķis | Partija |\n|---|---|\n| Test | JV |\n\n"
        "## Galvenās tēmas\n\n### NATO\n\nTeksts.\n\n"
        "## Koalīcija vs Opozīcija\n\nSintēze.\n\n"
    )
    # pad to ≥4000 chars for validator (Latvian filler preserves diacritics)
    _VALID_BRIEF += "Šādi ietilpst vairāk latviešu teksta lai nokārtotu 4000 rakstzīmju slieksni. " * 50

    def test_daily_brief_second_call_overwrites(self, tools_db):
        from src.tools import store_context_note
        r1 = json.loads(store_context_note(
            topic="dienas pārskats 2026-04-20",
            note_type="daily_brief",
            content=self._VALID_BRIEF,
        ))
        assert r1["status"] == "success"

        r2 = json.loads(store_context_note(
            topic="dienas pārskats 2026-04-20",
            note_type="daily_brief",
            content=self._VALID_BRIEF + "\n\nPAPILDU SATURS",
        ))
        assert r2["status"] == "success"

        db = sqlite3.connect(tools_db)
        rows = db.execute(
            "SELECT id, content FROM context_notes "
            "WHERE note_type='daily_brief' AND topic='dienas pārskats 2026-04-20'"
        ).fetchall()
        db.close()
        assert len(rows) == 1, f"Expected 1 row after overwrite, got {len(rows)}"
        assert "PAPILDU SATURS" in rows[0][1]

    def test_daily_brief_overwrite_preserves_note_id(self, tools_db):
        """In-place UPDATE keeps id stable → preserves brief_images FK."""
        from src.tools import store_context_note
        r1 = json.loads(store_context_note(
            topic="dienas pārskats 2026-04-20",
            note_type="daily_brief",
            content=self._VALID_BRIEF,
        ))
        r2 = json.loads(store_context_note(
            topic="dienas pārskats 2026-04-20",
            note_type="daily_brief",
            content=self._VALID_BRIEF + "\nAtjauninājums",
        ))
        assert r1.get("note_id") == r2.get("note_id"), \
            "note_id must stay stable across overwrites"

    def test_context_note_still_inserts_new_rows(self, tools_db):
        """context_notes of type 'context' stay INSERT-only (CLAUDE.md Pipeline Invariant #8)."""
        from src.tools import store_context_note
        store_context_note(topic="Tēma", note_type="context", content="Pirmais")
        store_context_note(topic="Tēma", note_type="context", content="Otrais")
        db = sqlite3.connect(tools_db)
        rows = db.execute(
            "SELECT id FROM context_notes WHERE note_type='context' AND topic='Tēma'"
        ).fetchall()
        db.close()
        assert len(rows) == 2, "Context notes should accumulate, not overwrite"

    def test_daily_brief_different_topics_both_kept(self, tools_db):
        """Different dates should produce different rows."""
        from src.tools import store_context_note
        b1 = self._VALID_BRIEF
        b2 = self._VALID_BRIEF.replace("2026-04-20", "2026-04-21")
        store_context_note(topic="dienas pārskats 2026-04-20", note_type="daily_brief", content=b1)
        store_context_note(topic="dienas pārskats 2026-04-21", note_type="daily_brief", content=b2)
        db = sqlite3.connect(tools_db)
        rows = db.execute(
            "SELECT topic FROM context_notes WHERE note_type='daily_brief'"
        ).fetchall()
        db.close()
        assert len(rows) == 2


def test_weekly_validation_requires_new_sections():
    from src.tools import _validate_brief_structure
    good = ("# Nedēļas analīze — 2026-05-26 līdz 2026-06-01\n\n"
            "## Nedēļas stāsts\n" + ("proza " * 600) +
            "\n## Nedēļas galvenās tēmas\n- x\n## Vizuālais brief\n- **Tēma:** A\n")
    _validate_brief_structure(good, "weekly_brief")  # should not raise

    missing_story = good.replace("## Nedēļas stāsts", "## Kaut kas")
    with pytest.raises(ValueError) as e:
        _validate_brief_structure(missing_story, "weekly_brief")
    assert "Nedēļas stāsts" in str(e.value)


def test_search_similar_claims_forwards_speaker_scope(monkeypatch):
    """The agent-facing wrapper must forward speaker_scope to db.search_similar_claims
    (CLAUDE.md invariant #7) — previously it was unreachable through tools.py."""
    import src.tools as tools_mod

    captured = {}
    monkeypatch.setattr(tools_mod, "embed_text", lambda text: [0.0])

    def fake_db_search(query_vec, opponent_id, top_k=10, claim_type_filter=None,
                       speaker_scope="first_party"):
        captured["speaker_scope"] = speaker_scope
        return []

    monkeypatch.setattr(tools_mod, "db_search_similar_claims", fake_db_search)

    tools_mod.search_similar_claims(opponent_id=1, claim_text="x", speaker_scope="all")
    assert captured["speaker_scope"] == "all"

    tools_mod.search_similar_claims(opponent_id=1, claim_text="x")
    assert captured["speaker_scope"] == "first_party", "default must stay first_party"


def test_retrieve_context_query_branch_is_callable(monkeypatch):
    """`retrieve_context(query=...)` must actually reach db.search_similar.

    Regression gate for a defect that lived from 2026-04-09 to 2026-08-02: the call
    passed ``opponent_id=`` while ``db.search_similar`` names that parameter
    ``politician_id``, so EVERY call with ``query`` raised TypeError. Nothing in
    production calls this path, so nothing surfaced it — the only consumer is the
    documented example in ``wiki/operations/wiki-tools.md``.

    Hermetic on purpose: the real embedder and vector table are stubbed, so this
    exercises the wiring, not the model.
    """
    import inspect

    import src.db as db_mod
    import src.tools as tools_mod

    # The name really is politician_id — if db.py ever renames it, this test
    # must fail loudly rather than let tools.py drift out of sync again.
    params = inspect.signature(db_mod.search_similar).parameters
    assert "politician_id" in params
    assert "opponent_id" not in params

    captured = {}

    def fake_search_similar(query_embedding, top_k=10, politician_id=None, db_path=None):
        captured["politician_id"] = politician_id
        captured["top_k"] = top_k
        return []

    monkeypatch.setattr(tools_mod, "embed_text", lambda text: [0.0])
    monkeypatch.setattr(tools_mod, "db_search_similar", fake_search_similar)
    # get_db too: retrieve_context opens the default DB before the search, so
    # without this stub the test silently depends on a real data/atmina.db.
    # Locally that file exists; in hermetic CI a leftover 0-byte file trips the
    # get_db empty-DB guard (added 2026-08-04) and the search is never reached —
    # CI was red from 2026-08-04 17:54 to 2026-08-05 while local runs stayed
    # green. The query-path with an empty result set only needs connect+close.
    monkeypatch.setattr(
        tools_mod, "get_db", lambda db_path=None: sqlite3.connect(":memory:")
    )

    out = tools_mod.retrieve_context(opponent_id=42, query="nodokļu reforma", max_results=5)

    # retrieve_context wraps exceptions into a JSON error string, so a bad kwarg
    # shows up as "the search was never reached", not as a raised TypeError.
    assert "politician_id" in captured, (
        "db.search_similar was never reached — retrieve_context probably passes a "
        f"kwarg that does not exist in its signature. Returned: {out[:200]}"
    )
    assert captured["politician_id"] == 42, "opponent_id must map onto politician_id"
    assert captured["top_k"] == 5
    json.loads(out)  # must stay valid JSON
