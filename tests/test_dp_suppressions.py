"""A junction link a human removed does not come back (D2, plan
docs/superpowers/plans/archive/2026-10-14-saisu-apspiesana.md).

Failure named first: a deleted (doc, pid) link was re-added by the next
same-URL re-fetch (`insert_document`) or matcher rescan, silently undoing the
fix (audit docs/audits/2026-10-14-datu-kvalitate/D2-saites-atgriezas.md: 9 rows).

* The E2E drives the real writers: delete the only link by SQL, re-ingest the
  same URL with changed text and a different proposed role, rescan with the
  matcher -> the link stays absent, each refusal is logged, an unrelated new
  link is still added, and a legacy rollback INSERT restores the link.
* The trigger cases pin how DELETE / role UPDATE / INSERT record and lift a
  suppression, and the `dp_suppression_mode='off'` switch.
* The structural test keeps every writer on `link_document_politicians`.
"""

import json
import re
from pathlib import Path

import pytest

import src.db as db_mod
import src.matcher as matcher_mod
from src.db import get_db, init_db, insert_document

URL = "https://www.lsm.lv/raksts/zinas/latvija/d2-suppression.a000001/"
PID_A = 10  # "Jānis Tests"
PID_B = 12  # "Alvis Hermanis"

TEXT_V1 = "Saeimas debatēs Jānis Tests kritizēja valdības plānus. " * 5
TEXT_V2 = (
    "Saeimas debatēs Jānis Tests kritizēja valdības plānus, "
    "bet Alvis Hermanis viņam iebilda. " * 5
)


@pytest.fixture
def pol_db(tmp_path, monkeypatch):
    path = str(tmp_path / "atmina_test.db")
    init_db(path)
    seed = get_db(path)
    for pid, name, forms in (
        (PID_A, "Jānis Tests", ["Jānis Tests", "Tests"]),
        (PID_B, "Alvis Hermanis", ["Alvis Hermanis", "Hermanis"]),
    ):
        seed.execute(
            "INSERT INTO tracked_politicians (id, name, name_forms, relationship_type) "
            "VALUES (?, ?, ?, 'tracked')",
            (pid, name, json.dumps(forms)),
        )
    seed.commit()
    seed.close()
    monkeypatch.setattr(db_mod, "DB_PATH", path)
    matcher_mod._clear_politician_cache()
    yield path
    matcher_mod._clear_politician_cache()


def _links(path, doc_id):
    db = get_db(path)
    rows = {(r[0], r[1]) for r in db.execute(
        "SELECT politician_id, role FROM document_politicians WHERE document_id = ?",
        (doc_id,))}
    db.close()
    return rows


def _active(db, doc_id):
    """Un-lifted suppressions as {(pid, role): scope}."""
    return {(r[0], r[1]): r[2] for r in db.execute(
        "SELECT politician_id, role, scope FROM document_politician_suppressions "
        "WHERE document_id = ? AND lifted_at IS NULL", (doc_id,))}


def test_deleted_link_does_not_return_via_ingest_or_rescan(pol_db):
    doc_id = insert_document(
        content=TEXT_V1, source_id=None, platform="web", source_url=URL,
        politician_links=[(PID_A, "subject")], db_path=pol_db,
    )
    db = get_db(pol_db)
    db.execute("DELETE FROM document_politicians WHERE document_id = ? AND politician_id = ?",
               (doc_id, PID_A))
    db.commit()
    db.close()

    # Path A: same-URL re-fetch, changed text, a DIFFERENT proposed role for A.
    again = insert_document(
        content=TEXT_V2, source_id=None, platform="web", source_url=URL,
        politician_links=[(PID_A, "mentioned"), (PID_B, "subject")], db_path=pol_db,
    )
    assert again == doc_id
    # Path B: targeted matcher rescan (text names A in full).
    result = matcher_mod.link_politicians_to_documents(doc_ids=[doc_id])

    links = _links(pol_db, doc_id)
    assert not any(pid == PID_A for pid, _ in links), links
    assert (PID_B, "subject") in links  # unrelated new link still added
    assert result.suppressed >= 1

    db = get_db(pol_db)
    logged = [json.loads(r[0]) for r in db.execute(
        "SELECT details FROM logs WHERE action = 'dp_suppressed'")]
    db.close()
    assert {(d["document_id"], d["politician_id"]) for d in logged} == {(doc_id, PID_A)}
    assert {d["source"] for d in logged} >= {"insert_document", "matcher"}

    # A legacy rollback file (raw INSERT) restores the link and it stays.
    db = get_db(pol_db)
    db.execute("INSERT INTO document_politicians (document_id, politician_id, role) "
               "VALUES (?, ?, 'subject')", (doc_id, PID_A))
    db.commit()
    db.close()
    matcher_mod.link_politicians_to_documents(doc_ids=[doc_id])
    assert (PID_A, "subject") in _links(pol_db, doc_id)


@pytest.fixture
def doc(pol_db):
    """(db, doc_id) with A as subject; db is a raw connection, caller commits."""
    doc_id = insert_document(
        content=TEXT_V1, source_id=None, platform="web", source_url=URL,
        politician_links=[(PID_A, "subject")], db_path=pol_db,
    )
    db = get_db(pol_db)
    yield db, doc_id
    db.close()


def test_role_update_there_and_back(doc):
    db, d = doc
    db.execute("UPDATE document_politicians SET role = 'mentioned' WHERE document_id = ?", (d,))
    assert _active(db, d) == {(PID_A, "subject"): "role"}
    db.execute("UPDATE document_politicians SET role = 'subject' WHERE document_id = ?", (d,))
    assert _active(db, d) == {(PID_A, "mentioned"): "role"}


def test_set_role_to_itself_records_nothing(doc):
    db, d = doc
    db.execute("UPDATE document_politicians SET role = role WHERE document_id = ?", (d,))
    assert _active(db, d) == {}


def test_update_or_ignore_collision_records_nothing(doc):
    db, d = doc
    db.execute("INSERT INTO document_politicians (document_id, politician_id, role) "
               "VALUES (?, ?, 'mentioned')", (d, PID_A))
    db.execute("UPDATE OR IGNORE document_politicians SET role = 'mentioned' "
               "WHERE document_id = ? AND role = 'subject'", (d,))
    assert _active(db, d) == {}
    assert db.execute("SELECT COUNT(*) FROM document_politicians WHERE document_id = ?",
                      (d,)).fetchone()[0] == 2


def test_delete_subject_then_insert_mentioned_suppresses_only_subject(doc):
    db, d = doc
    db.execute("DELETE FROM document_politicians WHERE document_id = ?", (d,))
    assert _active(db, d) == {(PID_A, "subject"): "pair"}
    db.execute("INSERT INTO document_politicians (document_id, politician_id, role) "
               "VALUES (?, ?, 'mentioned')", (d, PID_A))
    assert _active(db, d) == {(PID_A, "subject"): "role"}
    # Re-suppressing a lifted row re-activates it.
    db.execute("INSERT INTO document_politicians (document_id, politician_id, role) "
               "VALUES (?, ?, 'subject')", (d, PID_A))
    assert _active(db, d) == {}
    db.execute("DELETE FROM document_politicians WHERE document_id = ? AND role = 'subject'", (d,))
    assert _active(db, d) == {(PID_A, "subject"): "role"}


def test_document_delete_cascades(doc):
    db, d = doc
    db.execute("DELETE FROM document_politicians WHERE document_id = ?", (d,))
    db.execute("INSERT INTO document_politicians (document_id, politician_id, role) "
               "VALUES (?, ?, 'mentioned')", (d, PID_A))
    db.execute("DELETE FROM documents WHERE id = ?", (d,))  # must not raise
    db.commit()
    assert db.execute("SELECT COUNT(*) FROM document_politician_suppressions").fetchone()[0] == 0


def test_mode_off_records_nothing(doc):
    db, d = doc
    db.execute("UPDATE dp_suppression_mode SET mode = 'off'")
    db.execute("UPDATE document_politicians SET role = 'mentioned' WHERE document_id = ?", (d,))
    db.execute("DELETE FROM document_politicians WHERE document_id = ?", (d,))
    assert _active(db, d) == {}


# Files allowed to INSERT into document_politicians directly. src/db.py holds
# the helper and the manual override `link_politician_to_document`; the rest
# are one-off migrations and fix/rollback generators whose SQL a human reviews.
_JUNCTION_INSERT_ALLOWLIST = {
    "src/db.py": 2,
    "scripts/migrate_db.py": None,
    "scripts/fix_sweep_junctions_2026-10-05.py": None,
    "scripts/fix_links_2026-10-05b.py": None,
    "scripts/_fix_open_questions_2026-10-01.py": None,
    "scripts/fix_berzins_talsu_2026_09_29.py": None,
    "scripts/fix_operator_verdicts_2026-09-23.py": None,
    "scripts/audit_dp_readds.py": None,  # writes only its own :memory: copy (audit check 23)
}
_INSERT_RE = re.compile(r"INSERT(\s+OR\s+\w+)?\s+INTO\s+document_politicians\b", re.I)


def test_junction_inserts_only_in_helper_and_allowlist():
    root = Path(__file__).resolve().parents[1]
    files = [*root.glob("src/**/*.py"), *root.glob("scripts/**/*.py"), *root.glob("data/**/*.py")]
    assert len(files) > 100  # the scan really saw the tree
    found = {}
    for f in files:
        n = len(_INSERT_RE.findall(f.read_text(encoding="utf-8")))
        if n:
            found[f.relative_to(root).as_posix()] = n
    stray = sorted(set(found) - set(_JUNCTION_INSERT_ALLOWLIST))
    assert not stray, f"route these through src.db.link_document_politicians: {stray}"
    assert found.get("src/db.py") == _JUNCTION_INSERT_ALLOWLIST["src/db.py"]
