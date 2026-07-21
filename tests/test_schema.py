"""Tests for the src/schema.sql extraction in Phase 2 of
refactor-plan-2026-04-29.md.

Three invariants:
  1. init_db() on an empty file path creates every table the codebase
     expects (PRAGMA-driven roster check).
  2. init_db() is idempotent — calling it twice does not error and does
     not duplicate / drop existing data.
  3. After-refactor schema is semantically identical to the captured
     pre-refactor baseline (`docs/refactor/schema-dump-pre-f2.sql`).
     Comparison is whitespace-normalized because SQLite stores
     CREATE TABLE SQL exactly as written and the schema.sql cleanup
     re-indented inline columns. Column types, defaults, and constraints
     remain byte-identical post-normalization.
"""

from __future__ import annotations

import gc
import os
import re
import sqlite3
import tempfile
from pathlib import Path

import pytest

from src.db import init_db

BASELINE_DUMP = Path(__file__).parent.parent / "docs" / "refactor" / "schema-dump-pre-f2.sql"


def _safe_unlink(path: str) -> None:
    try:
        os.unlink(path)
    except (PermissionError, FileNotFoundError):
        pass


@pytest.fixture
def fresh_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    gc.collect()  # release any pending sqlite_vec handles on Windows
    _safe_unlink(path)


# Tables the codebase expects from a clean install. Adding a new CREATE
# TABLE to schema.sql means adding it here too.
EXPECTED_TABLES = {
    # Static DDL in src/schema.sql
    "tracked_politicians",
    "sources",
    "social_accounts",
    "documents",
    "document_politicians",
    "document_chunks",
    "analyses",
    "claims",
    "contradictions",
    "political_tensions",
    "social_drafts",
    "oppo_briefs",
    "context_notes",
    "logs",
    "metadata",
    "mention_classifications",
    "knab_donors",
    "knab_donations",
    "knab_declarations",
    "knab_alerts",
    "parties",
    # Created by Python migration blocks in init_db() (not yet promoted
    # to schema.sql — left as-is in Phase 2 to keep the move tightly
    # scoped; future phases can flatten these into schema.sql).
    "brief_images",
    "external_profiles",
    # vec0 virtual tables
    "document_vectors",
    "claim_vectors",
}


def test_init_db_on_empty_creates_all_tables(fresh_db):
    """Roster check: every table EXPECTED_TABLES lists exists after init."""
    con = sqlite3.connect(fresh_db)
    rows = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    con.close()
    found = {r[0] for r in rows}
    missing = EXPECTED_TABLES - found
    # vec0 internals (claim_vectors_chunks, document_vectors_rowids etc) are
    # implementation tables; ignore them in the diff.
    extra = found - EXPECTED_TABLES
    extra = {n for n in extra if not (n.startswith("claim_vectors_") or n.startswith("document_vectors_"))}
    assert not missing, f"missing tables: {sorted(missing)}"
    assert not extra, f"unexpected new tables (add to EXPECTED_TABLES?): {sorted(extra)}"


# Indexes on `claims` a clean install must have. Live prod (data/atmina.db)
# carries all of these; schema.sql + the db.py speaker_id ALTER migration must
# reproduce the full set on a fresh DB. Missing indexes => slow first render /
# perf surprises for fresh + OSS installs. Adding a claims index means adding
# it here too.
EXPECTED_CLAIMS_INDEXES = {
    "idx_claims_opponent_topic",
    "idx_claims_stated_at",
    "idx_claims_compound",
    "idx_claims_document_id",
    "idx_claims_claim_type",
    "idx_claims_opp_type_topic",
    "idx_claims_speaker",
    "idx_claims_opponent_speaker",
}


def test_init_db_creates_all_claims_indexes(fresh_db):
    """Fresh init_db() DB must carry every claims index prod has.

    Regression guard for schema.sql / db.py drift: the speaker_id indexes
    (idx_claims_speaker, idx_claims_opponent_speaker) lived only as a db.py
    ALTER migration and were absent from schema.sql, so a DB built from
    schema.sql alone lacked them.
    """
    con = sqlite3.connect(fresh_db)
    rows = con.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='index' AND tbl_name='claims'"
    ).fetchall()
    con.close()
    gc.collect()
    found = {r[0] for r in rows}
    missing = EXPECTED_CLAIMS_INDEXES - found
    assert not missing, f"fresh DB missing claims indexes: {sorted(missing)}"


def test_init_db_on_existing_db_idempotent(fresh_db):
    """init_db() called twice must not error or duplicate tables / rows.

    Inserts a tracked_politician between the two init_db() calls so we
    verify the second call is non-destructive (data still present).
    """
    con = sqlite3.connect(fresh_db)
    con.execute(
        "INSERT INTO tracked_politicians (name, party) VALUES ('Idempotency Probe', 'TEST')"
    )
    con.commit()
    rows_before = con.execute("SELECT COUNT(*) FROM tracked_politicians").fetchone()[0]
    con.close()
    gc.collect()

    init_db(fresh_db)  # second call — must not raise

    con = sqlite3.connect(fresh_db)
    rows_after = con.execute("SELECT COUNT(*) FROM tracked_politicians").fetchone()[0]
    name = con.execute(
        "SELECT name FROM tracked_politicians WHERE name = 'Idempotency Probe'"
    ).fetchone()
    con.close()
    gc.collect()
    assert rows_after == rows_before, (
        f"row count changed across init_db calls: {rows_before} -> {rows_after}"
    )
    assert name is not None, "data inserted between init_db calls was destroyed"


def test_schema_sql_matches_pre_refactor_dump(fresh_db):
    """Whitespace-normalized DDL after the schema.sql refactor must match
    the captured pre-refactor baseline. Whitespace is normalized because
    SQLite stores CREATE TABLE SQL verbatim, and reindenting inline columns
    in schema.sql is a cosmetic cleanup that doesn't change column types,
    defaults, constraints, or PK / FK declarations.

    Regenerate the baseline when intentionally adding/removing DDL (new
    CREATE TABLE in src/schema.sql, new ALTER TABLE in src/db.py):

        REGEN=1 .venv/Scripts/python.exe -m pytest tests/test_schema.py

    The REGEN block preserves the file's header comment block and rewrites
    the body from a fresh init_db() dump.
    """

    def _normalize(sql: str) -> str:
        return re.sub(r"\s+", " ", sql).strip()

    con = sqlite3.connect(fresh_db)
    rows = con.execute(
        "SELECT sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY type, name"
    ).fetchall()
    con.close()
    gc.collect()

    if os.environ.get("REGEN") == "1":
        existing = BASELINE_DUMP.read_text(encoding="utf-8")
        header_end = existing.find("byte-identically.\n\n") + len("byte-identically.\n\n")
        header = existing[:header_end]
        body = ";\n".join(r[0] for r in rows) + ";\n"
        BASELINE_DUMP.write_text(header + body, encoding="utf-8", newline="\n")
        pytest.skip("Regenerated baseline — re-run without REGEN to assert.")

    actual = "\n".join(_normalize(r[0]) for r in rows)

    baseline_text = BASELINE_DUMP.read_text(encoding="utf-8")
    # The baseline file has 4 header comment lines + a blank line, then
    # the dump body. Split on the marker at the end of the header.
    body = baseline_text.split("byte-identically.\n\n", 1)[1]
    expected = "\n".join(
        _normalize(stmt.rstrip(";").strip())
        for stmt in body.split(";\n")
        if stmt.strip()
    )
    assert actual == expected, (
        "schema diverged from pre-F2 baseline. Either run "
        "`REGEN=1 pytest tests/test_schema.py` to refresh the baseline "
        "(intentional DDL change), or revert the divergent edit. "
        "First 1000 chars of diff:\n"
        + actual[:500] + "\n--- vs ---\n" + expected[:500]
    )
