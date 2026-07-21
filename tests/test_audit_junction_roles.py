"""Tests for scripts.audit_junction_roles — junction sweep for mis-attributed role='subject' rows."""

import sqlite3

import pytest

import src.db as db_mod
import src.ingest as ing_mod
import src.matcher as matcher_mod
from src.db import insert_document
from src.matcher import _clear_politician_cache


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """Isolated DB per test. Redirects get_db to the tmp path and resets
    matcher-module caches so tracked_politicians mutations take effect."""
    db_path = str(tmp_path / "atmina_test.db")
    db_mod.init_db(db_path)

    orig_get_db = db_mod.get_db

    def _redirected_get_db(db_path_arg: str = db_path) -> sqlite3.Connection:
        return orig_get_db(db_path)

    monkeypatch.setattr(db_mod, "get_db", _redirected_get_db)
    monkeypatch.setattr(ing_mod, "get_db", _redirected_get_db)
    monkeypatch.setattr(matcher_mod, "get_db", _redirected_get_db)
    monkeypatch.setattr(db_mod, "DB_PATH", db_path)

    _clear_politician_cache()

    conn = orig_get_db(db_path)
    yield conn
    conn.close()


def test_audit_finds_mismatched_subject_rows(tmp_db):
    from scripts.audit_junction_roles import find_mismatched_rows

    tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms) VALUES (45, 'Mārtiņš Krusts', '[]')"
    )
    tmp_db.execute(
        "INSERT INTO social_accounts (opponent_id, platform, handle) VALUES (45, 'twitter', 'krusts')"
    )
    tmp_db.commit()

    doc_id = insert_document(
        content="Some content about Krusts.",
        source_id=None,
        platform="twitter",
        language="lv",
        source_url="https://x.com/KasparsH/status/2045853390337405314",
        politician_links=[(45, "subject")],
    )

    mismatches = find_mismatched_rows(tmp_db)
    assert len(mismatches) == 1
    assert mismatches[0]["document_id"] == doc_id
    assert mismatches[0]["politician_id"] == 45
    assert mismatches[0]["current_role"] == "subject"
    assert mismatches[0]["proposed_role"] == "mentioned"
    assert mismatches[0]["url_author"] == "kasparsh"
    assert "krusts" in mismatches[0]["politician_handles"]


def test_audit_ignores_correctly_attributed_rows(tmp_db):
    from scripts.audit_junction_roles import find_mismatched_rows

    tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms) VALUES (45, 'Mārtiņš Krusts', '[]')"
    )
    tmp_db.execute(
        "INSERT INTO social_accounts (opponent_id, platform, handle) VALUES (45, 'twitter', 'krusts')"
    )
    tmp_db.commit()

    insert_document(
        content="Own tweet.",
        source_id=None,
        platform="twitter",
        language="lv",
        source_url="https://x.com/krusts/status/12345",
        politician_links=[(45, "subject")],
    )

    mismatches = find_mismatched_rows(tmp_db)
    assert mismatches == []


def test_audit_ignores_non_twitter_platforms(tmp_db):
    from scripts.audit_junction_roles import find_mismatched_rows

    tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms) VALUES (146, 'Andris Bērziņš', '[]')"
    )
    tmp_db.commit()

    insert_document(
        content="Par bijušo prezidentu.",
        source_id=None,
        platform="web",
        language="lv",
        source_url="https://www.la.lv/par-partiku-maksasim",
        politician_links=[(146, "subject")],
    )

    mismatches = find_mismatched_rows(tmp_db)
    assert mismatches == []


def test_audit_flags_x_mention_subject_as_mention_target(tmp_db):
    from scripts.audit_junction_roles import find_mismatched_rows

    tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms) VALUES (60, 'Ēriks Stendzenieks', '[]')"
    )
    tmp_db.execute(
        "INSERT INTO social_accounts (opponent_id, platform, handle) VALUES (60, 'twitter', 'stendzenieks')"
    )
    tmp_db.commit()

    insert_document(
        content="Attack on Stendzenieks.",
        source_id=None,
        platform="x_mention",
        language="lv",
        source_url="https://x.com/BensLatkovskis/status/2045830485486535043",
        politician_links=[(60, "subject")],
    )

    mismatches = find_mismatched_rows(tmp_db)
    assert len(mismatches) == 1
    assert mismatches[0]["proposed_role"] == "mention_target"


def test_apply_fixes_replaces_subject_with_proposed_role(tmp_db):
    from scripts.audit_junction_roles import apply_fixes, find_mismatched_rows

    tmp_db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms) VALUES (45, 'Mārtiņš Krusts', '[]')"
    )
    tmp_db.execute(
        "INSERT INTO social_accounts (opponent_id, platform, handle) VALUES (45, 'twitter', 'krusts')"
    )
    tmp_db.commit()

    doc_id = insert_document(
        content="Mention of Krusts by a third party.",
        source_id=None,
        platform="twitter",
        language="lv",
        source_url="https://x.com/KasparsH/status/2045853390337405314",
        politician_links=[(45, "subject")],
    )

    mismatches = find_mismatched_rows(tmp_db)
    n = apply_fixes(tmp_db, mismatches)
    assert n == 1

    rows = tmp_db.execute(
        "SELECT role FROM document_politicians WHERE document_id=? AND politician_id=45",
        (doc_id,),
    ).fetchall()
    roles = {r["role"] for r in rows}
    assert roles == {"mentioned"}, f"expected {{mentioned}}, got {roles}"
