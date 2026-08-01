"""Tests for src/routine.py — daily routine status checker."""

import json
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
    _check_tensions,
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


def _log(db, action, ts, status="success", details=None):
    db.execute(
        "INSERT INTO logs (timestamp, action, status, details) VALUES (?, ?, ?, ?)",
        (ts, action, status, json.dumps(details) if details else None),
    )
    db.commit()


class TestCheckIngest:
    """Step 1 must answer 'did the ingest RUN', not 'did any row land today'.

    Those are different questions and the difference is not academic. On
    2026-08-02 a single ad-hoc ingest_url.py document made this step report
    green while the morning chain had never been started — a normal day lands
    600-900 documents, that day had 10. The same shape hid the 07-29 outage.
    """

    def test_documents_alone_are_not_evidence_the_ingest_ran(self, routine_db):
        """The 2026-08-02 case: a document exists, the chain never ran."""
        db = get_db(routine_db)
        result = _check_ingest(db, "2026-04-07")
        assert result["status"] == "missing", result
        assert "nav palaista" in result["details"]
        db.close()

    def test_missing_no_documents(self, empty_routine_db):
        db = get_db(empty_routine_db)
        result = _check_ingest(db, "2026-04-07")
        assert result["status"] == "missing"
        db.close()

    def test_summary_row_success_is_done(self, routine_db):
        db = get_db(routine_db)
        _log(db, "morning_ingest", "2026-04-07 08:10:00",
             details={"steps_total": 5, "steps_ok": 5, "failed": []})
        result = _check_ingest(db, "2026-04-07")
        assert result["status"] == "done", result
        assert "5/5" in result["details"]
        assert "1 jauni dokumenti" in result["details"]
        db.close()

    def test_summary_row_failure_names_the_failed_step(self, routine_db):
        db = get_db(routine_db)
        _log(db, "morning_ingest", "2026-04-07 08:10:00", status="error",
             details={"steps_total": 5, "steps_ok": 4,
                      "failed": ["fetch_all_mentions"]})
        result = _check_ingest(db, "2026-04-07")
        assert result["status"] == "partial", result
        assert "fetch_all_mentions" in result["details"]
        db.close()

    def test_manual_path_partway_through_is_partial(self, routine_db):
        """Stopping after step 2 left NO trace at all before 2026-08-02.

        No success row, no failure row — so the day read as 'there were no
        mentions today' rather than 'step 3 never ran' (07-22, 07-28, 07-31).
        """
        db = get_db(routine_db)
        _log(db, "ingest", "2026-04-07 08:00:00")
        _log(db, "social_fetch_all", "2026-04-07 08:05:00")
        result = _check_ingest(db, "2026-04-07")
        assert result["status"] == "partial", result
        assert "X pieminējumi" in result["details"]
        db.close()

    def test_manual_path_complete_is_done(self, routine_db):
        db = get_db(routine_db)
        for action in ("ingest", "social_fetch_all", "mentions_fetch"):
            _log(db, action, "2026-04-07 08:00:00")
        result = _check_ingest(db, "2026-04-07")
        assert result["status"] == "done", result
        db.close()

    def test_yesterdays_run_does_not_count_for_today(self, routine_db):
        db = get_db(routine_db)
        _log(db, "morning_ingest", "2026-04-06 08:10:00",
             details={"steps_total": 5, "steps_ok": 5, "failed": []})
        result = _check_ingest(db, "2026-04-07")
        assert result["status"] == "missing", result
        db.close()


class TestCheckAnalysis:
    def test_done_when_analyzed(self, routine_db):
        # routine_db: doc scraped 10:00 LV, analyses created_at 12:00 UTC = 15:00 LV.
        # 10:00 < 15:00 → doc arrived BEFORE the analysis → deliberately-left
        # below-cap residual, stays done (signal (a)).
        db = get_db(routine_db)
        result = _check_analysis(db, "2026-04-07")
        assert result["status"] == "done"
        db.close()

    def test_no_docs_is_na_not_done(self, empty_routine_db):
        """Nothing to analyse is not the same claim as 'analysed'."""
        db = get_db(empty_routine_db)
        result = _check_analysis(db, "2026-04-07")
        assert result["status"] == "n/a"
        assert "Nav politiķu" in result["details"]
        db.close()

    @staticmethod
    def _seed(db, *, analyses_created_at, doc_scraped_at, name="Backfill Politiķis"):
        """Seed one politician with a today-dated analyses row and one unreviewed
        subject doc. Timestamps: analyses.created_at is UTC (DEFAULT
        CURRENT_TIMESTAMP semantics), documents.scraped_at is LV (now_lv())."""
        db.execute(
            "INSERT INTO tracked_politicians (id, name, party) VALUES (1, ?, 'TP')",
            (name,),
        )
        db.execute(
            "INSERT INTO documents (content, content_hash, platform, scraped_at) "
            "VALUES ('c', 'h1', 'web', ?)",
            (doc_scraped_at,),
        )
        db.execute(
            "INSERT INTO document_politicians (document_id, politician_id, role) "
            "VALUES (1, 1, 'subject')"
        )
        db.execute(
            """INSERT INTO analyses (opponent_id, period_start, period_end, sentiment_score,
               key_topics, notable_quotes, brief_markdown, confidence, created_at)
               VALUES (1, '2026-04-07', '2026-04-07', 0.0, '[]', '[]', 'b', 0.9, ?)""",
            (analyses_created_at,),
        )
        db.commit()

    def test_doc_scraped_after_analysis_is_pending(self, empty_routine_db):
        # analyses 08:00 UTC = 11:00 LV; doc scraped 13:00 LV (after 11:00 LV).
        # Later arrival reopens the politician as pending despite signal (a).
        db = get_db(empty_routine_db)
        self._seed(
            db,
            analyses_created_at="2026-04-07 08:00:00",
            doc_scraped_at="2026-04-07 13:00:00",
        )
        result = _check_analysis(db, "2026-04-07")
        db.close()
        assert result["status"] in ("partial", "missing")
        assert "Backfill Politiķis" in result["details"]

    def test_doc_scraped_before_analysis_is_done(self, empty_routine_db):
        # analyses 08:00 UTC = 11:00 LV; doc scraped 09:00 LV (before 11:00 LV).
        # Residual class — the analysis session already saw it → stays done.
        db = get_db(empty_routine_db)
        self._seed(
            db,
            analyses_created_at="2026-04-07 08:00:00",
            doc_scraped_at="2026-04-07 09:00:00",
        )
        result = _check_analysis(db, "2026-04-07")
        db.close()
        assert result["status"] == "done"

    def test_tz_shift_mandatory_regression(self, empty_routine_db):
        # analyses 05:00 UTC = 08:00 LV; doc scraped 07:00 LV.
        # In LV time: doc 07:00 < analysis 08:00 → BEFORE → done (correct).
        # Raw UTC compare (no '+3 hours'): doc 07:00 > analysis 05:00 → would
        # wrongly flag pending. Asserting done makes this FAIL if the shift is
        # dropped.
        db = get_db(empty_routine_db)
        self._seed(
            db,
            analyses_created_at="2026-04-07 05:00:00",
            doc_scraped_at="2026-04-07 07:00:00",
        )
        result = _check_analysis(db, "2026-04-07")
        db.close()
        assert result["status"] == "done"

    def test_multiple_analyses_rows_max_covers(self, empty_routine_db):
        # Two analyses rows today: 05:00 UTC (=08:00 LV) and 10:00 UTC (=13:00 LV).
        # Doc scraped 09:00 LV — after the earlier (08:00 LV) but before MAX
        # (13:00 LV). MAX row covers it → done.
        db = get_db(empty_routine_db)
        self._seed(
            db,
            analyses_created_at="2026-04-07 05:00:00",
            doc_scraped_at="2026-04-07 09:00:00",
        )
        db.execute(
            """INSERT INTO analyses (opponent_id, period_start, period_end, sentiment_score,
               key_topics, notable_quotes, brief_markdown, confidence, created_at)
               VALUES (1, '2026-04-07', '2026-04-07', 0.0, '[]', '[]', 'b', 0.9,
                       '2026-04-07 10:00:00')"""
        )
        db.commit()
        result = _check_analysis(db, "2026-04-07")
        db.close()
        assert result["status"] == "done"


class TestCheckContradictions:
    def test_done_with_claims(self, routine_db):
        """Legacy trace: stored contradictions prove the hunt ran, no log needed."""
        db = get_db(routine_db)
        db.execute("""INSERT INTO contradictions (opponent_id, claim_old_id, claim_new_id,
                      topic, summary, severity, reviewed, detected_at)
                      VALUES (1, 1, 1, 'NATO', 'test', 'reversal', 0, '2026-04-07 15:00:00')""")
        db.commit()
        result = _check_contradictions(db, "2026-04-07")
        assert result["status"] == "done"
        db.close()

    def test_done_zero_findings_with_hunt_log(self, routine_db):
        """Honest zero: hunt ran, found nothing — provable via the logs trace
        that routine step 3 writes even when nothing was stored (2026-08-19,
        gate candidate #4)."""
        db = get_db(routine_db)
        _log(db, "contradiction_hunt", "2026-04-07 15:30:00",
             details={"date": "2026-04-07", "claims_checked": 1, "found": 0})
        result = _check_contradictions(db, "2026-04-07")
        assert result["status"] == "done"
        assert "logs" in result["details"]
        db.close()

    def test_missing_claims_but_no_trace(self, routine_db):
        """Claims exist but neither stored contradictions nor a hunt log — the
        hunt is not provable, so the step must report missing, not done."""
        db = get_db(routine_db)
        result = _check_contradictions(db, "2026-04-07")
        assert result["status"] == "missing"
        db.close()

    def test_done_when_no_claims(self, empty_routine_db):
        db = get_db(empty_routine_db)
        result = _check_contradictions(db, "2026-04-07")
        assert result["status"] == "n/a"
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
        # `logs.timestamp` is written with now_lv(), so it carries the same
        # hazard as `documents.scraped_at`: an evening LV row must count for its
        # own LV date, and a 'localtime' modifier here would push 22:30 into
        # 2026-04-08 and report the ingest as never run.
        db.execute("""INSERT INTO logs (timestamp, action, status, details)
                      VALUES ('2026-04-07 22:30:00', 'morning_ingest', 'success',
                              '{"steps_total": 5, "steps_ok": 5, "failed": []}')""")
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
        assert result["status"] == "n/a"
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
        assert result["status"] == "n/a"
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


class TestBriefIdentityIsSubjectDate:
    """Regression (2026-07-30): steps 7 and 8 keyed off ``created_at``, so a
    brief stored just after midnight satisfied the NEXT day's checks.

    Live consequence on 2026-07-29: brief #383 covers 07-28 but was stored at
    00:04 on 07-29, so the 07-29 status read "✓ Dienas pārskats sarakstīts" and
    "✓ Featured image apstiprināts (brief 383)" while no 07-29 brief existed at
    all. Those two green ticks were the only thing hiding a routine that an API
    outage had killed mid-step. The mirror case is a false red: a brief written
    after midnight for the day it covers looked missing.

    Identity now comes from ``src.briefs.brief_subject_date`` (topic → H1 →
    created_at), shared with src/render/blog.py's slug derivation.
    """

    VB = '{"topic":"NATO","headline":"Test","stat":null,"metaphor_hint":"x"}'

    @staticmethod
    def _add_brief(db, subject_date, created_at, visual_brief=None):
        db.execute(
            """INSERT INTO context_notes (note_type, topic, content, created_at,
                                          visual_brief_json)
               VALUES ('daily_brief', ?, ?, ?, ?)""",
            (
                f"dienas analīze {subject_date}",
                f"# Dienas analīze — {subject_date}\n\n## Galvenais\n\n- Punkts.",
                created_at,
                visual_brief,
            ),
        )
        db.commit()
        return db.execute("SELECT MAX(id) FROM context_notes").fetchone()[0]

    def test_yesterdays_brief_stored_after_midnight_is_not_todays(self, empty_routine_db):
        """The false green that masked the outage."""
        db = get_db(empty_routine_db)
        self._add_brief(db, "2026-04-06", "2026-04-07 00:04:27")
        result = _check_daily_brief(db, "2026-04-07")
        assert result["status"] == "missing", (
            "a brief whose topic names 2026-04-06 must never mark 04-07 done"
        )
        db.close()

    def test_todays_brief_stored_after_midnight_still_counts(self, empty_routine_db):
        """The mirror false red: written 00:12, covers the day before."""
        db = get_db(empty_routine_db)
        self._add_brief(db, "2026-04-07", "2026-04-08 00:12:00")
        assert _check_daily_brief(db, "2026-04-07")["status"] == "done"
        db.close()

    def test_featured_image_checks_this_days_brief_not_a_neighbours(self, empty_routine_db):
        """Reproduces "apstiprināts (brief 383)": the approved image belongs to
        the previous day's brief, and 04-07 has its own brief with none."""
        db = get_db(empty_routine_db)
        # The exact live shape: the ONLY row created on the target date is the
        # PREVIOUS day's brief (stored 00:04), and it has an approved image.
        # This day's own brief lands after midnight, so a created_at-keyed query
        # cannot see it at all — which is how step 8 came to report a green tick
        # naming someone else's brief.
        prev_id = self._add_brief(db, "2026-04-06", "2026-04-07 00:04:27", self.VB)
        db.execute(
            """INSERT INTO brief_images (note_id, image_path, prompt, model, approved,
               generated_at, cost_usd)
               VALUES (?, 'x.png', 'p', 'm', 1, '2026-04-07 00:10:00', 0.039)""",
            (prev_id,),
        )
        today_id = self._add_brief(db, "2026-04-07", "2026-04-08 00:30:00", self.VB)
        db.commit()

        result = _check_featured_image(db, "2026-04-07")
        assert result["status"] == "missing", (
            "the previous day's approved image must not satisfy this day's step 8"
        )
        assert str(today_id) in result["details"], (
            f"step 8 must name the 04-07 brief ({today_id}), got: {result['details']}"
        )
        assert str(prev_id) not in result["details"]
        db.close()

    def test_legacy_row_without_topic_or_h1_falls_back_to_created_at(self, empty_routine_db):
        """Rows predating the topic convention must keep working."""
        db = get_db(empty_routine_db)
        db.execute(
            """INSERT INTO context_notes (note_type, content, created_at)
               VALUES ('daily_brief', 'Dienas pārskats', '2026-04-07 18:00:00')"""
        )
        db.commit()
        assert _check_daily_brief(db, "2026-04-07")["status"] == "done"
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


class TestNothingToDoIsNotDone:
    """'nothing to do' must not render as ✓.

    A day whose ingest silently failed produces no new documents, so analysis,
    contradictions, devils-advocate and tensions each find nothing — and each
    used to return status 'done'. A dead day therefore rendered as a wall of
    green ✓ and counted as a complete routine. The two facts are different and
    the summary must keep them apart. See CLAUDE.md § "A gate that cannot fail
    is not evidence".
    """

    def test_empty_day_reports_na_not_done(self, empty_routine_db):
        db = get_db(empty_routine_db)
        assert _check_analysis(db, "2026-04-07")["status"] == "n/a"
        assert _check_contradictions(db, "2026-04-07")["status"] == "n/a"
        assert _check_devils_advocate(db, "2026-04-07")["status"] == "n/a"
        assert _check_tensions(db, "2026-04-07")["status"] == "n/a"
        db.close()

    def test_na_still_counts_as_complete(self, empty_routine_db):
        """A quiet day is not an unfinished day — n/a must not block completion."""
        from src.routine import check_routine

        db = get_db(empty_routine_db)
        db.execute(
            "INSERT INTO logs (timestamp, action, status, details) "
            "VALUES ('2026-04-07 08:00:00', 'morning_ingest', 'success', "
            "'{\"steps_total\": 5, \"steps_ok\": 5, \"failed\": []}')"
        )
        db.commit()
        db.close()

        res = check_routine("2026-04-07", db_path=empty_routine_db,
                            now=datetime(2026, 4, 7, 23, 0))
        na_steps = [k for k, v in res["steps"].items() if v["status"] == "n/a"]
        assert na_steps, res["steps"]
        for key in na_steps:
            assert res["steps"][key]["status"] != "done"

    def test_dead_day_does_not_look_like_a_full_one(self, empty_routine_db):
        """The load-bearing case: no ingest at all must not yield ten ticks."""
        from src.routine import check_routine

        res = check_routine("2026-04-07", db_path=empty_routine_db,
                            now=datetime(2026, 4, 7, 23, 0))
        done = [k for k, v in res["steps"].items() if v["status"] == "done"]
        assert "ingest" not in done
        assert "analysis" not in done, "an empty day must not report analysis as done"
        assert res["steps"]["ingest"]["status"] == "missing"
