"""Tendences → Konteksts: _clean_context_note helper + _fetch_context_notes filter.

Covers the 2026-06-04 fix (spec/plan under docs/superpowers/): bare claim-ID
stripping, markdown rendering, and exclusion of JSON audit rows + 'polling'
from the public Konteksts grid.
"""

import sqlite3

from src.render._common import _clean_context_note
from src.render.blog import _fetch_context_notes


# ── _clean_context_note ──────────────────────────────────────────────

def test_strips_bare_claim_ids():
    out = _clean_context_note("Švinka ierosina pārbaudi (claim #208) un kritizē #6757 projektu.")
    assert "#208" not in out
    assert "#6757" not in out
    assert "claim" not in out  # "claim " prefiks notverts kopā ar ID
    assert "Švinka ierosina pārbaudi" in out


def test_strips_parenthesised_claim_ids():
    out = _clean_context_note("Naratīvs trim mērķiem (#14411) un (#20534).")
    assert "#14411" not in out
    assert "#20534" not in out
    assert "()" not in out  # nepaliek tukšas iekavas


def test_renders_markdown_bold():
    out = _clean_context_note("**Tendence:** libertārisms paplašinās.")
    assert "<strong>" in out
    assert "**" not in out


def test_preserves_paragraph_breaks():
    out = _clean_context_note("Pirmā rindkopa.\n\nOtrā rindkopa.")
    # Newlines must survive ID-collapse so markdown makes two paragraphs.
    assert out.count("<p>") == 2


def test_empty_and_none_safe():
    assert _clean_context_note("") == ""
    assert _clean_context_note(None) == ""


# ── _fetch_context_notes ─────────────────────────────────────────────

def _seed_db():
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute("""
        CREATE TABLE context_notes (
            id INTEGER PRIMARY KEY, opponent_id INTEGER, topic TEXT,
            note_type TEXT, content TEXT, created_at TEXT
        )
    """)
    db.executemany(
        "INSERT INTO context_notes (topic, note_type, content, created_at) VALUES (?,?,?,?)",
        [
            ("Rail Baltica", "context", "**Tendence:** kritika (claim #208).", "2026-06-02 10:00:00"),
            (None, "context", '{"kind": "synthesis_featured_image", "slug": "x"}', "2026-06-03 10:00:00"),
            (None, "polling", "Aptauja 42%.", "2026-06-01 10:00:00"),
        ],
    )
    db.commit()
    return db


def test_fetch_excludes_json_and_polling():
    db = _seed_db()
    notes = _fetch_context_notes(db)
    assert len(notes) == 1
    assert notes[0]["topic"] == "Rail Baltica"


def test_fetch_adds_clean_content_html():
    db = _seed_db()
    note = _fetch_context_notes(db)[0]
    assert "content_html" in note
    assert "<strong>" in note["content_html"]
    assert "#208" not in note["content_html"]
