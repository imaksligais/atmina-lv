"""`src/scope.py` — the extraction queue's politician-side scope, read once.

Regression harness for the 2026-08-02 drift. Commit `83033c02` removed the 11
relay news accounts from the extraction queue (`src/analyze.py`) but not from
the routine status denominator (`src/routine.py`) or the published backlog
figure (`src/wiki.py`), because all three had typed the predicate out
separately. Nothing failed — the queue quietly got smaller than the two numbers
that describe it.

The behavioural test below is the one that would have caught it: it asserts the
queue and the status answer the SAME question on the SAME database. The gate
test is the one that keeps it caught — it fails the moment a fourth caller
types the predicate inline instead of importing it.
"""

import os
import re
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.analyze import get_pending_politicians
from src.db import get_db, init_db, now_lv
from src.routine import _check_analysis
from src.scope import queue_politician_sql

REPO = Path(__file__).resolve().parent.parent
# The fixture day must sit inside get_pending_politicians(days=1)'s rolling
# window at RUN time — a hardcoded date passes in the morning and fails the
# same evening once the 24h cutoff slides past the fixture's scraped_at
# (exactly the wall-clock test class BACKLOG § timestamp saime warns about;
# this line was "2026-08-02" and went red the evening of 08-03).
DAY = now_lv()[:10]


def _safe_unlink(path):
    try:
        os.unlink(path)
    except PermissionError:
        pass


@pytest.fixture
def scope_db():
    """One politician of each scope class, each with a same-day subject doc.

    id=1 tracked      → real work, must appear everywhere
    id=2 relay org    → organization + feed_type='relay' (the LETA class)
    id=3 inactive     → sentinel / retired
    id=4 first_party org → LDDK/NBS/Valsts kontrole class; MUST stay in scope,
                           this is what the narrow AND protects
    """
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    db = get_db(path)
    rows = [
        (1, "Tracked Politiķis", "tracked"),
        (2, "LETA", "organization"),
        (3, "Pensionēts Deputāts", "inactive"),
        (4, "Valsts kontrole", "organization"),
    ]
    for pid, name, rel in rows:
        db.execute(
            "INSERT INTO tracked_politicians (id, name, relationship_type) VALUES (?, ?, ?)",
            (pid, name, rel),
        )
    # Only id=2 is a relay feed. id=4 is an organization too — it must survive.
    db.execute(
        "INSERT INTO social_accounts (opponent_id, platform, handle, feed_type) "
        "VALUES (2, 'twitter', 'letanewslv', 'relay')"
    )
    db.execute(
        "INSERT INTO social_accounts (opponent_id, platform, handle, feed_type) "
        "VALUES (4, 'twitter', 'valstskontrole', 'first_party')"
    )
    for pid, _, _ in rows:
        db.execute(
            "INSERT INTO documents (id, content, content_hash, platform, scraped_at, reviewed_at) "
            "VALUES (?, ?, ?, 'web', ?, NULL)",
            (pid, f"saturs {pid}", f"hash{pid}", f"{DAY} 10:00:00"),
        )
        db.execute(
            "INSERT INTO document_politicians (document_id, politician_id, role) "
            "VALUES (?, ?, 'subject')",
            (pid, pid),
        )
    db.commit()
    db.close()
    yield path
    _safe_unlink(path)


IN_SCOPE = {"Tracked Politiķis", "Valsts kontrole"}
OUT_OF_SCOPE = {"LETA", "Pensionēts Deputāts"}


class TestQueueAndStatusAgree:
    """The 2026-08-02 regression, both directions."""

    def test_queue_excludes_relay_and_inactive_keeps_first_party_org(self, scope_db):
        with patch("src.analyze.get_db", lambda: get_db(scope_db)):
            names = {p["name"] for p in get_pending_politicians(days=1)}
        assert names == IN_SCOPE, names

    def test_status_denominator_excludes_relay_and_inactive(self, scope_db):
        db = get_db(scope_db)
        result = _check_analysis(db, DAY)
        db.close()
        # Denominator is "N politiķi" / "0/N analizēti" — it must be 2, not 4.
        assert "/2 " in result["details"], result
        for name in OUT_OF_SCOPE:
            assert name not in result["details"], result

    def test_both_entry_points_answer_the_same_question(self, scope_db):
        """The single assertion that would have failed on 2026-08-02."""
        with patch("src.analyze.get_db", lambda: get_db(scope_db)):
            queue = {p["name"] for p in get_pending_politicians(days=1)}
        db = get_db(scope_db)
        status = _check_analysis(db, DAY)
        db.close()
        # Every politician the queue offers must be inside the status
        # denominator, and the status must name no one the queue will not offer.
        assert f"0/{len(queue)} " in status["details"], (queue, status)
        for name in queue:
            assert name in status["details"], (name, status)


class TestPublishedBacklogUsesQueueSemantics:
    """`wiki/index.md` is what CLAUDE.md tells every session to read first.

    Measured on the live DB before the fix: the published figure was 577 while
    the queue-semantics backlog was 232 — 58 docs on inactive politicians and
    287 on relay accounts, i.e. 60% of the headline number was work that does
    not exist.
    """

    def test_backlog_counts_only_documents_an_extractor_could_be_offered(self, scope_db):
        db = get_db(scope_db)
        counted = db.execute(
            f"""SELECT COUNT(DISTINCT d.id)
                FROM documents d
                JOIN document_politicians dp ON dp.document_id = d.id
                WHERE d.reviewed_at IS NULL
                  AND d.platform = 'web'
                  AND dp.role = 'subject'
                  AND {queue_politician_sql()}"""
        ).fetchone()[0]
        unscoped = db.execute(
            """SELECT COUNT(DISTINCT d.id)
               FROM documents d
               JOIN document_politicians dp ON dp.document_id = d.id
               WHERE d.reviewed_at IS NULL
                 AND d.platform = 'web'
                 AND dp.role = 'subject'"""
        ).fetchone()[0]
        db.close()
        assert unscoped == 4, unscoped
        assert counted == 2, counted


class TestScopeIsDefinedOnce:
    """A fourth inline copy is the failure mode; this is the gate against it."""

    # Modules that ask the queue question and must therefore import the scope.
    QUEUE_MODULES = ["src/analyze.py", "src/routine.py", "src/wiki.py"]

    # Display semantics — a politician's OWN posts. A relay outlet's feed is
    # legitimately rendered here; applying the queue predicate would blank real
    # content. Listed explicitly so the boundary is a decision, not an omission.
    DISPLAY_MODULES = ["src/render/politicians.py", "src/render/x.py"]

    _RELAY_LITERAL = re.compile(r"feed_type\s*=\s*'relay'")

    def test_queue_modules_import_the_shared_scope(self):
        for rel in self.QUEUE_MODULES:
            src = (REPO / rel).read_text(encoding="utf-8")
            assert "queue_politician_sql" in src, (
                f"{rel} asks the queue question but does not read src/scope.py"
            )

    def test_no_queue_module_carries_its_own_copy(self):
        """The literal may exist in exactly one place: src/scope.py."""
        offenders = [
            rel
            for rel in self.QUEUE_MODULES + self.DISPLAY_MODULES
            if self._RELAY_LITERAL.search((REPO / rel).read_text(encoding="utf-8"))
        ]
        assert offenders == [], (
            f"inline relay predicate outside src/scope.py: {offenders}"
        )

    def test_scope_module_is_the_one_definition(self):
        """Count the EXECUTABLE definition, not prose.

        `src/scope.py` names the predicate in its docstring too; that is
        documentation, not a second source of truth. Asserting against the file
        text would make this gate fail on a comment — a checker that fires on
        its own documentation teaches people to loosen it.
        """
        from src.scope import _QUEUE_POLITICIAN_TEMPLATE

        assert len(self._RELAY_LITERAL.findall(_QUEUE_POLITICIAN_TEMPLATE)) == 1

    def test_display_modules_are_deliberately_out_of_scope(self):
        """Render surfaces must NOT adopt the queue predicate (see scope.py)."""
        for rel in self.DISPLAY_MODULES:
            src = (REPO / rel).read_text(encoding="utf-8")
            assert "queue_politician_sql" not in src, (
                f"{rel} renders a politician's own posts — the queue predicate "
                f"would blank legitimate relay content"
            )


class TestPredicateShape:
    def test_accepts_a_caller_supplied_id_expression(self):
        assert "x.pid" in queue_politician_sql("x.pid")

    def test_default_targets_the_junction_alias(self):
        assert "dp.politician_id" in queue_politician_sql()

    def test_subquery_aliases_cannot_collide_with_callers(self):
        """Callers use dp/tp/d/sa/c — the predicate must not reuse those."""
        sql = queue_politician_sql()
        for alias in (" dp ", " tp ", " sa ", " c ", " d "):
            assert alias not in sql, (alias, sql)
