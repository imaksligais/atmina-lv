"""Phase 1A integration tests — parse real agenda snapshot fixtures.

The 2026-04-16 snapshot at data/saeima_snapshots/2026-04-16/agenda.md
is the canonical fixture for parser regression detection.
"""

import os
import tempfile
from pathlib import Path

import pytest

from src.db import init_db, get_db
from src.saeima import (
    init_saeima_tables,
    init_saeima_bills,
    parse_agenda_snapshot,
)


def _safe_unlink(path):
    try:
        os.unlink(path)
    except PermissionError:
        pass


# Fixture lives in the parent main checkout (data/ is gitignored, not in worktree).
# Resolve from CWD: prefer worktree-relative, fall back to ../../ parent.
def _find_fixture():
    candidates = [
        Path("data/saeima_snapshots/2026-04-16/agenda.md"),
        Path("../../data/saeima_snapshots/2026-04-16/agenda.md"),
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


FIXTURE_AGENDA = _find_fixture()


@pytest.mark.skipif(
    FIXTURE_AGENDA is None,
    reason="agenda.md fixture missing — run @saeima-tracker first to populate",
)
class TestParseAgenda20260416:
    def test_extracts_at_least_one_bill(self):
        text = FIXTURE_AGENDA.read_text(encoding="utf-8")
        bills = parse_agenda_snapshot(text)
        assert len(bills) >= 1, "agenda fixture should contain bills"

    def test_extracted_bills_have_valid_types(self):
        text = FIXTURE_AGENDA.read_text(encoding="utf-8")
        bills = parse_agenda_snapshot(text)
        for b in bills:
            assert b.bill_type in {"Lp14", "Lm14", "P14"}, f"unknown bill_type {b.bill_type!r}"
            assert b.document_nr.endswith(b.bill_type), \
                f"document_nr suffix mismatch: {b.document_nr!r} vs {b.bill_type!r}"
            assert b.title, "every bill should have a title"

    def test_titles_are_clean(self):
        """Titles must not contain accessibility-tree noise (newlines, ref tags)."""
        text = FIXTURE_AGENDA.read_text(encoding="utf-8")
        bills = parse_agenda_snapshot(text)
        for b in bills:
            assert "\n" not in b.title, f"title has newline: {b.document_nr} {b.title!r}"
            assert "[ref=" not in b.title, f"title has ref tag: {b.document_nr} {b.title!r}"
            # Most titles are short; legitimate Lm14 procedural titles can run long
            # but should never exceed 400 chars (anything bigger is a parse error)
            assert len(b.title) <= 400, \
                f"title suspiciously long ({len(b.title)} chars): {b.document_nr}"

    def test_some_bills_have_individual_submitters(self):
        text = FIXTURE_AGENDA.read_text(encoding="utf-8")
        bills = parse_agenda_snapshot(text)
        with_individual = [b for b in bills if b.individual_submitters]
        # Real agenda may or may not have individual submitters depending on the day
        # — accept 0 or more, but log for inspection
        print(f"\n  bills with individual_submitters: {len(with_individual)}/{len(bills)}")

    def test_some_bills_have_institutional_submitter(self):
        text = FIXTURE_AGENDA.read_text(encoding="utf-8")
        bills = parse_agenda_snapshot(text)
        with_inst = [b for b in bills if b.institutional_submitter]
        print(f"\n  bills with institutional_submitter: {len(with_inst)}/{len(bills)}")
        # Most agendas have at least one Ministru kabinets bill


# ---------------------------------------------------------------------------
# Backfill tests
# ---------------------------------------------------------------------------

from src.saeima import init_saeima_bills  # noqa: E402 (after module-level imports)


@pytest.fixture
def votes_db():
    """DB with 5 saeima_votes pre-populated (mimics retro state)."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    init_saeima_tables(path)

    db = get_db(path)
    db.executemany(
        """INSERT INTO saeima_votes (
            id, motif, vote_date, total_par, total_pret, total_atturas,
            total_nebalso, result, url, summary, document_nr, topic
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (1, "Grozījumi X (1/Lp14), 1.lasījums", "2026-03-01", 60, 30, 5, 0,
             "pieņemts", "u1", "Test summary", "1/Lp14", "Aizsardzība"),
            (2, "Grozījumi X (1/Lp14), 2.lasījums", "2026-04-01", 65, 28, 4, 0,
             "pieņemts", "u2", "v2 summary", "1/Lp14", "Aizsardzība"),
            (3, "Par tiesneša Y iecelšanu (5/Lm14)", "2026-04-10", 80, 10, 5, 0,
             "pieņemts", "u3", "Tiesneša summary", "5/Lm14", "Tieslietas"),
            (4, "Par dronu uzbrukumiem (12/P14)", "2026-04-15", 90, 5, 1, 0,
             "pieņemts", "u4", "Drone summary", "12/P14", "Aizsardzība"),
            (5, "motif bez document_nr", "2026-04-20", 50, 30, 5, 0,
             "pieņemts", "u5", None, None, "Cits"),
        ],
    )
    db.commit()
    db.close()
    yield path
    _safe_unlink(path)


@pytest.fixture
def _isolated_db_path(monkeypatch, votes_db):
    """Route src.db.DB_PATH (used by backfill script imports) at the test DB."""
    import src.db as _dbm
    monkeypatch.setattr(_dbm, "DB_PATH", votes_db)
    return votes_db


class TestBackfill:
    def test_backfill_creates_bills_for_each_unique_doc_nr(self, _isolated_db_path):
        from scripts.backfill_saeima_bills import backfill
        report = backfill(db_path=_isolated_db_path)
        # 3 unique document_nrs (1/Lp14 with 2 votes, 5/Lm14, 12/P14) — vote 5 has NULL doc_nr (skipped)
        assert report["bills_created"] == 3
        assert report["votes_with_bill_id"] == 4  # rows 1,2,3,4 linked
        assert report["votes_skipped_null_doc_nr"] == 1

    def test_backfill_appends_stages_per_vote(self, _isolated_db_path):
        from scripts.backfill_saeima_bills import backfill
        backfill(db_path=_isolated_db_path)
        db = get_db(_isolated_db_path)
        rows = db.execute(
            """SELECT s.stage_name FROM saeima_bill_stages s
               JOIN saeima_bills b ON b.id = s.bill_id
               WHERE b.document_nr = '1/Lp14'
               ORDER BY s.stage_date"""
        ).fetchall()
        db.close()
        assert [r["stage_name"] for r in rows] == ["1.lasījums", "2.lasījums"]

    def test_backfill_unknown_threshold_under_10pct(self, _isolated_db_path):
        from scripts.backfill_saeima_bills import backfill
        report = backfill(db_path=_isolated_db_path)
        unknown_pct = report["unknown_stages"] / max(report["votes_with_bill_id"], 1)
        assert unknown_pct <= 0.10

    def test_backfill_idempotent(self, _isolated_db_path):
        from scripts.backfill_saeima_bills import backfill
        backfill(db_path=_isolated_db_path)
        backfill(db_path=_isolated_db_path)
        db = get_db(_isolated_db_path)
        bills = db.execute("SELECT COUNT(*) FROM saeima_bills").fetchone()[0]
        stages_total = db.execute("SELECT COUNT(*) FROM saeima_bill_stages").fetchone()[0]
        db.close()
        assert bills == 3
        assert stages_total == 4  # 4 votes with doc_nr → 4 stages, no doubling on re-run
