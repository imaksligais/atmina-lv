"""`scripts/audit_vector_staleness.py` — /audit-integrity check 13 runner.

Why this exists: 2026-08-04 found the same defect class twice in one day —
167 of 167 surviving 06-13 topic-migration rows and 14 of 54 hand-edited rows
carried vectors built from PRE-edit text, because a bare `UPDATE claims SET
topic/stance` raises nothing and `search_similar_claims` keeps ranking the row
by what it used to say. The method (byte-compare stored vector against
embed(f"{topic}: {stance}")) lived only in throwaway scratchpad scripts; this
locks it as a repeatable, self-verifying tool.

The control-set semantics are the load-bearing part: a broken compare reports
EVERYTHING stale — an inverted gate-that-cannot-fail — so the tool must prove
it can see a match before its "stale" means anything.

Tests use a plain-table `claim_vectors` stand-in (the script's SQL is
identical over vec0 and a regular table) and a deterministic fake embed, so
they are hermetic — no model, no native extension.
"""

import hashlib
import os
import sqlite3
import tempfile

from scripts.audit_vector_staleness import (
    extract_fix_file_ids,
    run_audit,
)
from src.db import _float_list_to_bytes


def fake_embed(text: str) -> list[float]:
    return [float(b) for b in hashlib.sha256(text.encode("utf-8")).digest()[:8]]


def _mkdb(rows):
    """rows: list of (id, topic, stance, embedded_text_or_None).

    embedded_text None -> no vector row; otherwise the stored vector is
    fake_embed(embedded_text), so passing the CURRENT text makes it match and
    any other text makes it stale.
    """
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE claims (id INTEGER PRIMARY KEY, topic TEXT, stance TEXT)")
    db.execute(
        "CREATE TABLE claim_vectors (claim_id INTEGER PRIMARY KEY, embedding BLOB)"
    )
    for cid, topic, stance, embedded in rows:
        db.execute("INSERT INTO claims VALUES (?, ?, ?)", (cid, topic, stance))
        if embedded is not None:
            db.execute(
                "INSERT INTO claim_vectors VALUES (?, ?)",
                (cid, _float_list_to_bytes(fake_embed(embedded))),
            )
    db.commit()
    db.close()
    return path


def _unlink(path):
    try:
        os.unlink(path)
    except (PermissionError, FileNotFoundError):
        pass


def test_extract_ids_only_from_embedded_field_updates(tmp_path):
    """`reasoning` is not embedded — editing it cannot stale a vector, so its
    UPDATEs must stay out of the candidate set. Both WHERE forms (`= N` and
    bulk `IN (…)`) must be covered — the old fixture only wrote the form the
    regex already matched, so it was circular against the single-form
    assumption (candidates #5/#6, 2026-08-19)."""
    (tmp_path / "fix_a_2026-01-01.sql").write_text(
        "UPDATE claims SET stance = 'x' WHERE id = 11;\n"
        "UPDATE claims SET topic = 'y' WHERE id = 12;\n"
        "UPDATE claims SET quote = 'z' WHERE id = 13;\n"
        "UPDATE claims SET topic = 'w' WHERE id IN (21, 22, 23);\n"
        "UPDATE claims SET reasoning = 'r' WHERE id = 14;\n",
        encoding="utf-8",
    )
    (tmp_path / "rollback_a_2026-01-01.sql").write_text(
        "UPDATE claims SET stance = 'old' WHERE id = 99;\n", encoding="utf-8"
    )
    ids = extract_fix_file_ids(tmp_path)
    # 14 (reasoning) and 99 (rollback file) excluded; IN-form ids included
    assert ids == [11, 12, 13, 21, 22, 23]


def test_extract_ids_from_multiline_in_clause(tmp_path):
    """Real bulk fix files (e.g. data/fix_drone_topic_boundary_2026-06-10.sql)
    split the IN list across lines with a trailing AND clause — the parser must
    collect every id, not just the first on the opening line."""
    (tmp_path / "fix_b_2026-01-01.sql").write_text(
        "UPDATE claims SET topic = 'Droni'\n"
        "WHERE id IN (7304, 11205, 14541, 17851, 17914,\n"
        "             18006, 18390, 20181, 20424)\n"
        "  AND topic = 'Aizsardzība un drošība';\n",
        encoding="utf-8",
    )
    ids = extract_fix_file_ids(tmp_path)
    assert ids == [7304, 11205, 14541, 17851, 17914, 18006, 18390, 20181, 20424]


def test_stale_and_match_and_missing_classified():
    path = _mkdb([
        (1, "NATO", "Atbalsta", "NATO: Atbalsta"),          # match
        (2, "NATO", "Jaunā nostāja", "NATO: Vecā nostāja"),  # stale
        (3, "NATO", "Bez vektora", None),                    # missing
    ])
    try:
        rep = run_audit(path, [1, 2, 3], embed_fn=fake_embed)
        assert (rep["checked"], rep["match"], rep["stale"], rep["missing"]) == (3, 1, 1, 1)
        assert rep["stale_ids"] == [2]
    finally:
        _unlink(path)


def test_deleted_rows_reported_separately_not_checked():
    path = _mkdb([(1, "NATO", "Atbalsta", "NATO: Atbalsta")])
    try:
        rep = run_audit(path, [1, 777], embed_fn=fake_embed)
        assert rep["candidates"] == 2
        assert rep["alive"] == 1
        assert rep["checked"] == 1
    finally:
        _unlink(path)


def test_passing_control_makes_all_stale_a_finding():
    """The 06-13 case: EVERY surviving row stale is a legitimate result —
    but only because the control proved the compare can see a match."""
    path = _mkdb([
        (1, "A", "s1", "A: OLD s1"),
        (2, "B", "s2", "B: OLD s2"),
        (10, "C", "labi", "C: labi"),  # control row, freshly embedded
    ])
    try:
        rep = run_audit(path, [1, 2], control_ids=[10], embed_fn=fake_embed)
        assert rep["stale"] == 2
        assert rep["control"] == {
            "checked": 1, "match": 1, "stale": 0, "stale_ids": [], "missing": 0,
        }
        assert rep["method_ok"] is True
    finally:
        _unlink(path)


def test_failing_control_marks_run_as_method_artifact():
    path = _mkdb([
        (1, "A", "s1", "A: OLD s1"),
        (10, "C", "labi", "C: KAS CITS"),  # control row does NOT match
    ])
    try:
        rep = run_audit(path, [1], control_ids=[10], embed_fn=fake_embed)
        assert rep["method_ok"] is False
        assert rep["note"]  # names the problem
    finally:
        _unlink(path)


def test_zero_matches_without_control_is_not_trusted():
    """Without a control, 'everything stale' is indistinguishable from a
    broken compare — the inverted gate-that-cannot-fail."""
    path = _mkdb([(1, "A", "s1", "A: OLD"), (2, "B", "s2", "B: OLD")])
    try:
        rep = run_audit(path, [1, 2], control_ids=[], embed_fn=fake_embed)
        assert rep["stale"] == 2
        assert rep["method_ok"] is False
        assert "control" in rep["note"] or "kontrol" in rep["note"]
    finally:
        _unlink(path)
