"""Tests for scripts/ingest_url.py — generic historic-article ingest CLI.

Network (fetch_fn) and the matcher (link_fn) are injected; the DB is a temp file.
No real HTTP, no live-DB writes.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import get_db, init_db, insert_document  # noqa: E402
import scripts.ingest_url as iu  # noqa: E402


@pytest.fixture
def tmp_db(tmp_path) -> str:
    db_path = str(tmp_path / "t.db")
    init_db(db_path=db_path)
    return db_path


def _fetch_ok(text="x" * 400, title="Vēsturisks raksts", published_at="2021-03-01T10:00:00+03:00"):
    def _fn(url):
        return {"text": text, "title": title, "published_at": published_at}

    return _fn


# --- ingest_one ---------------------------------------------------------------


def test_ingest_one_backdates_published_at(tmp_db):
    res = iu.ingest_one(
        "https://lsm.lv/raksts/old.a1",
        politician_id=None,
        fetch_fn=_fetch_ok(),
        db_path=tmp_db,
    )
    assert res["status"] == "ingested"
    assert res["doc_id"] is not None
    row = get_db(tmp_db).execute(
        "SELECT published_at FROM documents WHERE id=?", (res["doc_id"],)
    ).fetchone()
    assert row["published_at"] == "2021-03-01T10:00:00+03:00"


def test_ingest_one_already_present(tmp_db):
    insert_document(
        content="y" * 400, source_id=None, platform="web", language="lv",
        source_url="https://lsm.lv/raksts/seen.a2", published_at=None,
        title="t", db_path=tmp_db,
    )

    def _boom(url):
        raise AssertionError("fetch_fn must not be called when already present")

    res = iu.ingest_one("https://lsm.lv/raksts/seen.a2", fetch_fn=_boom, db_path=tmp_db)
    assert res["status"] == "already_present"


def test_ingest_one_dupe_by_content(tmp_db):
    shared = "z" * 400
    insert_document(
        content=shared, source_id=None, platform="web", language="lv",
        source_url="https://a.lv/one.a1", published_at=None, title="t", db_path=tmp_db,
    )
    res = iu.ingest_one(
        "https://b.lv/two.a2", fetch_fn=_fetch_ok(text=shared), db_path=tmp_db
    )
    assert res["status"] == "dupe"


def test_ingest_one_thin(tmp_db):
    res = iu.ingest_one(
        "https://a.lv/thin.a3", fetch_fn=_fetch_ok(text="too short"), db_path=tmp_db
    )
    assert res["status"] == "thin"
    assert res["doc_id"] is None


def test_ingest_one_fetch_error(tmp_db):
    res = iu.ingest_one("https://a.lv/err.a4", fetch_fn=lambda u: None, db_path=tmp_db)
    assert res["status"] == "fetch_error"


def test_published_at_from_url():
    assert iu._published_at_from_url("https://x.lv/2021/03/15/foo") == "2021-03-15"
    assert iu._published_at_from_url("https://x.lv/2019/foo") == "2019-01-01"
    assert iu._published_at_from_url("https://lsm.lv/raksts/foo.a12345") is None


# --- parse_manifest / ingest_manifest -----------------------------------------


def test_parse_manifest_skips_bad_lines(tmp_path):
    p = tmp_path / "m.jsonl"
    p.write_text(
        '{"url": "https://a.lv/1.a1", "politician_id": 5}\n'
        "not json\n"
        '{"url": "https://a.lv/2.a2"}\n',
        encoding="utf-8",
    )
    items = iu.parse_manifest(str(p))
    assert [i["url"] for i in items] == ["https://a.lv/1.a1", "https://a.lv/2.a2"]
    assert items[0]["politician_id"] == 5
    assert items[1].get("politician_id") is None


def test_ingest_manifest_summary(tmp_db):
    items = [
        {"url": "https://a.lv/ok.a1", "politician_id": 7},
        {"url": "https://a.lv/thin.a2", "politician_id": 7},
    ]

    def _fetch(url):
        if "thin" in url:
            return {"text": "short", "title": None, "published_at": None}
        return {"text": "w" * 400, "title": "T", "published_at": "2020-05-05"}

    def _fake_link(days=1, rescan_all=False):
        # pretend the matcher linked the freshly-ingested docs to pid 7
        return {doc_id: [7] for doc_id in iu._LAST_INGESTED_IDS}

    summary = iu.ingest_manifest(
        items, fetch_fn=_fetch, link_fn=_fake_link, db_path=tmp_db
    )
    assert summary["ingested"] == 1
    assert summary["thin"] == 1
    assert 7 in summary["linked_to"]


# --- main ---------------------------------------------------------------------


def test_main_requires_url_or_manifest():
    rc = iu.main(["--politician-id", "5"])
    assert rc == 2


def test_main_single_url_invokes_ingest(monkeypatch, tmp_db):
    calls = {}

    def _fake_ingest_manifest(items, **kw):
        calls["items"] = items
        return {"ingested": len(items), "already_present": 0, "dupe": 0, "thin": 0,
                "fetch_error": 0, "dateless": [], "linked_to": {}, "results": []}

    monkeypatch.setattr(iu, "ingest_manifest", _fake_ingest_manifest)
    rc = iu.main(["--url", "https://a.lv/x.a1", "--politician-id", "9", "--db", tmp_db])
    assert rc == 0
    assert calls["items"] == [{"url": "https://a.lv/x.a1", "politician_id": 9}]
