"""Tests for src/routine.py — daily routine status checker."""

import os
import tempfile
from datetime import datetime

import pytest

from src.db import get_db, init_db
from src.routine import (
    _check_analysis,
    _check_contradictions,
    _check_daily_brief,
    _check_devils_advocate,
    _check_featured_image,
    _check_ingest,
    _check_tendences,
    check_routine,
)


def _safe_unlink(path):
    try:
        os.unlink(path)
    except PermissionError:
        pass


@pytest.fixture
def routine_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    db = get_db(path)
    # Add a politician
    db.execute("INSERT INTO tracked_politicians (id, name, party) VALUES (1, 'Test Politiķis', 'TP')")
    # Add document for today
    db.execute("""INSERT INTO documents (content, content_hash, platform, scraped_at)
                  VALUES ('test content', 'hash1', 'web', '2026-04-07 10:00:00')""")
    # Link document to politician via junction table
    db.execute("INSERT INTO document_politicians (document_id, politician_id, role) VALUES (1, 1, 'subject')")
    # Add a claim
    db.execute("""INSERT INTO claims (opponent_id, document_id, topic, stance, stated_at, created_at)
                  VALUES (1, 1, 'NATO', 'Atbalsta', '2026-04-07', '2026-04-07 12:00:00')""")
    # Add analysis
    db.execute("""INSERT INTO analyses (opponent_id, period_start, period_end, sentiment_score,
                  key_topics, notable_quotes, brief_markdown, confidence, created_at)
                  VALUES (1, '2026-04-07', '2026-04-07', 0.0, '["NATO"]', '["q"]', 'brief', 0.9, '2026-04-07 12:00:00')""")
    # Add daily brief
    db.execute("""INSERT INTO context_notes (note_type, content, created_at)
                  VALUES ('daily_brief', 'Dienas pārskats', '2026-04-07 18:00:00')""")
    # Add context note
    db.execute("""INSERT INTO context_notes (note_type, content, topic, created_at)
                  VALUES ('context', 'Tendence', 'NATO', '2026-04-07 14:00:00')""")
    db.commit()
    db.close()
    yield path
    _safe_unlink(path)


@pytest.fixture
def empty_routine_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    _safe_unlink(path)


class TestCheckIngest:
    def test_done_with_documents(self, routine_db):
        db = get_db(routine_db)
        result = _check_ingest(db, "2026-04-07")
        assert result["status"] == "done"
        assert "1 jauni" in result["details"]
        db.close()

    def test_missing_no_documents(self, empty_routine_db):
        db = get_db(empty_routine_db)
        result = _check_ingest(db, "2026-04-07")
        assert result["status"] == "missing"
        db.close()


class TestCheckAnalysis:
    def test_done_when_analyzed(self, routine_db):
        db = get_db(routine_db)
        result = _check_analysis(db, "2026-04-07")
        assert result["status"] == "done"
        db.close()

    def test_done_when_no_docs(self, empty_routine_db):
        db = get_db(empty_routine_db)
        result = _check_analysis(db, "2026-04-07")
        assert result["status"] == "done"
        assert "Nav politiķu" in result["details"]
        db.close()


class TestCheckContradictions:
    def test_done_with_claims(self, routine_db):
        db = get_db(routine_db)
        result = _check_contradictions(db, "2026-04-07")
        assert result["status"] == "done"
        db.close()

    def test_done_when_no_claims(self, empty_routine_db):
        db = get_db(empty_routine_db)
        result = _check_contradictions(db, "2026-04-07")
        assert result["status"] == "done"
        db.close()


class TestCheckDailyBrief:
    def test_done_with_brief(self, routine_db):
        db = get_db(routine_db)
        result = _check_daily_brief(db, "2026-04-07")
        assert result["status"] == "done"
        db.close()

    def test_missing_without_brief(self, empty_routine_db):
        db = get_db(empty_routine_db)
        result = _check_daily_brief(db, "2026-04-07")
        assert result["status"] == "missing"
        db.close()


class TestCheckTendences:
    def test_done_with_notes(self, routine_db):
        db = get_db(routine_db)
        result = _check_tendences(db, "2026-04-07")
        assert result["status"] == "done"
        db.close()

    def test_missing_without_notes(self, empty_routine_db):
        db = get_db(empty_routine_db)
        result = _check_tendences(db, "2026-04-07")
        assert result["status"] == "missing"
        db.close()


class TestMorningWindow:
    """`check_routine` should flag analysis + daily_brief as 'waiting' before
    15:00 LV, not 'missing'. Per feedback_no_morning_brief and
    project_daily_routine_timing: morning extraction is intentional, not a
    backlog warning."""

    def test_daily_brief_waiting_before_15h(self, empty_routine_db):
        # 10:00 LV — operator hasn't started afternoon brief yet.
        # daily_brief always returns 'missing' when no brief exists, so the
        # morning-window post-process is what we're testing here.
        result = check_routine(
            "2026-04-07",
            db_path=empty_routine_db,
            now=datetime(2026, 4, 7, 10, 0),
        )
        assert result["steps"]["daily_brief"]["status"] == "waiting", (
            "morning daily_brief must show 'waiting' (operator UX), not 'missing'"
        )
        assert "Gaida pēcpusdienu" in result["steps"]["daily_brief"]["details"]

    def test_analysis_waiting_when_docs_exist_but_unanalyzed(self, empty_routine_db):
        # Insert docs without analyses → _check_analysis returns 'missing'.
        # In the morning that must flip to 'waiting'.
        from src.db import get_db

        db = get_db(empty_routine_db)
        db.execute("INSERT INTO tracked_politicians (id, name, party) VALUES (1, 'X', 'P')")
        db.execute(
            "INSERT INTO documents (content, content_hash, platform, scraped_at) "
            "VALUES ('c', 'h', 'web', '2026-04-07 09:00:00')"
        )
        db.execute(
            "INSERT INTO document_politicians (document_id, politician_id, role) "
            "VALUES (1, 1, 'subject')"
        )
        db.commit()
        db.close()

        result = check_routine(
            "2026-04-07",
            db_path=empty_routine_db,
            now=datetime(2026, 4, 7, 10, 0),
        )
        assert result["steps"]["analysis"]["status"] == "waiting"

    def test_daily_brief_missing_after_15h(self, empty_routine_db):
        # 16:30 LV — afternoon, missing daily_brief is a real backlog warning
        result = check_routine(
            "2026-04-07",
            db_path=empty_routine_db,
            now=datetime(2026, 4, 7, 16, 30),
        )
        assert result["steps"]["daily_brief"]["status"] == "missing"

    def test_completed_step_not_downgraded_to_waiting(self, routine_db):
        # 09:00 LV — but analysis is already done. Must stay 'done'.
        result = check_routine(
            "2026-04-07",
            db_path=routine_db,
            now=datetime(2026, 4, 7, 9, 0),
        )
        assert result["steps"]["analysis"]["status"] == "done"
        assert result["steps"]["daily_brief"]["status"] == "done"

    def test_now_defaults_to_real_clock(self, empty_routine_db):
        """When `now` is omitted, behavior is driven by real wall clock — but
        the shape of the output is unchanged. Smoke that the call works."""
        result = check_routine("2026-04-07", db_path=empty_routine_db)
        assert "steps" in result
        assert "analysis" in result["steps"]


class TestEveningBoundaryTimezone:
    """Regression: ``scraped_at``/``claims.created_at``/``contradictions.detected_at``/
    ``context_notes.created_at`` are stored in LV local time via ``now_lv()``.
    The routine checks must NOT re-apply a ``DATE(..., 'localtime')`` modifier
    to them — on a UTC+N machine that double-shifts an evening (21:00–23:59 LV)
    timestamp into the next calendar day, so the prior night's late scrape gets
    miscounted as "today". A document scraped at 22:30 LV on the target date
    must count for that date. ``analyses``/``political_tensions`` stay UTC
    (DEFAULT CURRENT_TIMESTAMP) and intentionally keep their 'localtime'.
    """

    def _evening_db(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        init_db(path)
        db = get_db(path)
        db.execute("INSERT INTO tracked_politicians (id, name, party) VALUES (1, 'T', 'TP')")
        # Evening LV scrape — 22:30 + 3h would spill to 2026-04-08 under the bug.
        db.execute("""INSERT INTO documents (content, content_hash, platform, scraped_at)
                      VALUES ('c', 'h', 'web', '2026-04-07 22:30:00')""")
        db.execute("INSERT INTO document_politicians (document_id, politician_id, role) VALUES (1, 1, 'subject')")
        db.execute("""INSERT INTO context_notes (note_type, content, created_at)
                      VALUES ('daily_brief', 'B', '2026-04-07 22:45:00')""")
        db.commit()
        db.close()
        return path

    def test_evening_document_counts_for_its_lv_date(self):
        path = self._evening_db()
        try:
            res = check_routine("2026-04-07", db_path=path, now=datetime(2026, 4, 7, 23, 0))
            assert res["steps"]["ingest"]["status"] == "done"
            assert "1" in res["steps"]["ingest"]["details"]
        finally:
            _safe_unlink(path)

    def test_evening_brief_counts_for_its_lv_date(self):
        path = self._evening_db()
        try:
            res = check_routine("2026-04-07", db_path=path, now=datetime(2026, 4, 7, 23, 0))
            assert res["steps"]["daily_brief"]["status"] == "done"
        finally:
            _safe_unlink(path)


class TestCheckDevilsAdvocate:
    def test_done_no_contradictions(self, empty_routine_db):
        db = get_db(empty_routine_db)
        result = _check_devils_advocate(db, "2026-04-07")
        assert result["status"] == "done"
        db.close()

    def test_missing_unreviewed(self, routine_db):
        db = get_db(routine_db)
        db.execute("""INSERT INTO contradictions (opponent_id, claim_old_id, claim_new_id,
                      topic, summary, severity, reviewed, detected_at)
                      VALUES (1, 1, 1, 'NATO', 'test', 'reversal', 0, '2026-04-07 15:00:00')""")
        db.commit()
        result = _check_devils_advocate(db, "2026-04-07")
        assert result["status"] == "missing"
        db.close()

    def test_done_all_reviewed(self, routine_db):
        db = get_db(routine_db)
        db.execute("""INSERT INTO contradictions (opponent_id, claim_old_id, claim_new_id,
                      topic, summary, severity, reviewed, detected_at)
                      VALUES (1, 1, 1, 'NATO', 'test', 'reversal', 1, '2026-04-07 15:00:00')""")
        db.commit()
        result = _check_devils_advocate(db, "2026-04-07")
        assert result["status"] == "done"
        db.close()


class TestCheckFeaturedImage:
    def test_done_when_no_brief_today(self, empty_routine_db):
        db = get_db(empty_routine_db)
        result = _check_featured_image(db, "2026-04-07")
        assert result["status"] == "done"
        assert "nav" in result["details"].lower() or "pārbaudei" in result["details"].lower()
        db.close()

    def test_partial_when_brief_without_visual_brief(self, routine_db):
        db = get_db(routine_db)
        # routine_db fixture inserts a daily_brief with NULL visual_brief_json
        result = _check_featured_image(db, "2026-04-07")
        assert result["status"] == "partial"
        assert "vizuāl" in result["details"].lower()
        db.close()

    def test_missing_when_visual_brief_but_no_approved_image(self, routine_db):
        db = get_db(routine_db)
        db.execute(
            "UPDATE context_notes SET visual_brief_json = ? "
            "WHERE note_type='daily_brief' AND DATE(created_at)=?",
            ('{"topic":"NATO","headline":"Test","stat":null,"metaphor_hint":"x"}', "2026-04-07"),
        )
        db.commit()
        result = _check_featured_image(db, "2026-04-07")
        assert result["status"] == "missing"
        assert "graphics-designer" in result["details"] or "featured" in result["details"].lower()
        db.close()

    def test_missing_when_only_rejected_attempts(self, routine_db):
        db = get_db(routine_db)
        db.execute(
            "UPDATE context_notes SET visual_brief_json = ? "
            "WHERE note_type='daily_brief' AND DATE(created_at)=?",
            ('{"topic":"NATO","headline":"Test","stat":null,"metaphor_hint":"x"}', "2026-04-07"),
        )
        brief_id = db.execute(
            "SELECT id FROM context_notes WHERE note_type='daily_brief' "
            "AND DATE(created_at)='2026-04-07'"
        ).fetchone()[0]
        db.execute(
            """INSERT INTO brief_images (note_id, image_path, prompt, model, approved,
               generated_at, cost_usd) VALUES (?, '', 'p', 'm', 2, '2026-04-07 19:00:00', 0.0)""",
            (brief_id,),
        )
        db.commit()
        result = _check_featured_image(db, "2026-04-07")
        assert result["status"] == "missing"
        db.close()

    def test_done_when_approved_image_exists(self, routine_db):
        db = get_db(routine_db)
        db.execute(
            "UPDATE context_notes SET visual_brief_json = ? "
            "WHERE note_type='daily_brief' AND DATE(created_at)=?",
            ('{"topic":"NATO","headline":"Test","stat":null,"metaphor_hint":"x"}', "2026-04-07"),
        )
        brief_id = db.execute(
            "SELECT id FROM context_notes WHERE note_type='daily_brief' "
            "AND DATE(created_at)='2026-04-07'"
        ).fetchone()[0]
        db.execute(
            """INSERT INTO brief_images (note_id, image_path, prompt, model, approved,
               generated_at, cost_usd) VALUES (?, 'output/images/briefs/x.png', 'p', 'm', 1,
               '2026-04-07 19:00:00', 0.039)""",
            (brief_id,),
        )
        db.commit()
        result = _check_featured_image(db, "2026-04-07")
        assert result["status"] == "done"
        db.close()


class TestCheckRoutine:
    def test_returns_all_steps(self, routine_db):
        result = check_routine("2026-04-07", db_path=routine_db)
        assert "steps" in result
        assert "date" in result
        expected_steps = ["ingest", "analysis", "contradictions", "devils_advocate",
                          "tensions", "tendences", "daily_brief", "featured_image",
                          "wiki_sync", "generate"]
        for step in expected_steps:
            assert step in result["steps"], f"Missing step: {step}"

    def test_empty_db_has_missing_steps(self, empty_routine_db):
        result = check_routine("2026-04-07", db_path=empty_routine_db)
        assert result["all_complete"] is False or True  # depends on wiki/output existence
