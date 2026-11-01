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
    # politician_id now writes a real junction row — the pid must resolve
    # against tracked_politicians (FK), so seed it.
    db = get_db(tmp_db)
    db.execute("INSERT INTO tracked_politicians (id, name) VALUES (7, 'Tests Politiķis')")
    db.commit()
    db.close()

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


# --- --politician-id: subject link ---------------------------------------------
#
# Regression cover for the doc-111520 role inversion (backlog/dati-db.md):
# ingest_one accepted `politician_id` but never passed it to insert_document,
# so roles came ONLY from the text matcher — the Šlesers interview stored the
# interviewee as 'mentioned' and the quoted critic as 'subject'. The parameter
# means "this politician is the SUBJECT (speaker)", and a later matcher rescan
# must not add a conflicting 'mentioned' row beside the asserted 'subject'.

PID_SUBJECT = 10  # "Jānis Tests" — the --politician-id target
PID_OTHER = 11    # "Pēteris Zeltiņš" — more name forms in the text, ranks first

# Zeltiņš matches two forms ("Pēteris Zeltiņš" + "Zeltiņš"), Tests only the bare
# surname → the matcher ranks Tests second, i.e. derives 'mentioned' for him.
_INTERVIEW_TEXT = (
    "Debatēs Pēteris Zeltiņš kritizēja valdības plānu un Zeltiņš "
    "piebilda, ka budžets jāpārskata pavasara sesijā. Par priekšlikumu "
    "runāja arī Tests un citi komisijas locekļi, diskusija ilga stundas."
)


@pytest.fixture
def pol_db(tmp_path, monkeypatch):
    """tmp DB seeded with two tracked politicians; the real matcher resolves
    src.db.DB_PATH at call time, so point it here and reset the forms cache
    (same pattern as tests/test_junction_suspect_flags.py)."""
    import src.db as db_mod
    import src.matcher as matcher_mod

    db_path = str(tmp_path / "t.db")
    init_db(db_path=db_path)
    db = get_db(db_path)
    db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms, relationship_type) "
        "VALUES (?, ?, ?, ?)",
        (PID_SUBJECT, "Jānis Tests", '["Jānis Tests", "Tests"]', "tracked"),
    )
    db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms, relationship_type) "
        "VALUES (?, ?, ?, ?)",
        (PID_OTHER, "Pēteris Zeltiņš", '["Pēteris Zeltiņš", "Zeltiņš"]', "tracked"),
    )
    db.commit()
    db.close()
    monkeypatch.setattr(db_mod, "DB_PATH", db_path)
    matcher_mod._clear_politician_cache()
    yield db_path
    matcher_mod._clear_politician_cache()


def _roles(db_path, doc_id):
    db = get_db(db_path)
    rows = db.execute(
        "SELECT politician_id, role FROM document_politicians "
        "WHERE document_id = ? ORDER BY politician_id, role",
        (doc_id,),
    ).fetchall()
    db.close()
    return [(r["politician_id"], r["role"]) for r in rows]


def test_ingest_one_politician_id_writes_subject_link(pol_db):
    """--politician-id X means "X is the SUBJECT (speaker)": the stored doc
    must carry a (X, 'subject') junction, not rely on the matcher."""
    res = iu.ingest_one(
        "https://lsm.lv/raksts/intervija.a1",
        politician_id=PID_SUBJECT,
        fetch_fn=_fetch_ok(text=_INTERVIEW_TEXT),
        db_path=pol_db,
    )
    assert res["status"] == "ingested"
    assert (PID_SUBJECT, "subject") in _roles(pol_db, res["doc_id"])


def test_politician_id_subject_survives_matcher_rescan(pol_db):
    """ingest_manifest ends with the real matcher rescan (rescan_all=True): a
    matcher-derived 'mentioned' for the SAME pid must not land beside the
    asserted 'subject' — one role per (doc, pid). Other names still link."""
    summary = iu.ingest_manifest(
        [{"url": "https://lsm.lv/raksts/intervija.a2", "politician_id": PID_SUBJECT}],
        fetch_fn=_fetch_ok(text=_INTERVIEW_TEXT),
        db_path=pol_db,
    )
    doc_id = summary["results"][0]["doc_id"]
    roles = _roles(pol_db, doc_id)
    assert (PID_SUBJECT, "subject") in roles
    assert (PID_SUBJECT, "mentioned") not in roles
    assert (PID_OTHER, "subject") in roles


def test_no_politician_id_roles_come_from_matcher(pol_db):
    """Without --politician-id nothing changes: roles are whatever the matcher
    derives — here 'Tests' ranks below 'Zeltiņš' → 'mentioned'."""
    summary = iu.ingest_manifest(
        [{"url": "https://lsm.lv/raksts/intervija.a3"}],
        fetch_fn=_fetch_ok(text=_INTERVIEW_TEXT),
        db_path=pol_db,
    )
    doc_id = summary["results"][0]["doc_id"]
    assert _roles(pol_db, doc_id) == [
        (PID_SUBJECT, "mentioned"),
        (PID_OTHER, "subject"),
    ]


# --- _extract_article_text fallback ladder --------------------------------------


def test_extract_fallback_triggers_only_when_default_is_thin(monkeypatch):
    """D1 P1: noklusējums 0 z. (SV-AJ/ST klase) → recall variants; strādājošs
    noklusējums recallu NEizsauc. Mutācija: recall vienmēr tukšs → thin paliek."""
    import trafilatura

    calls = []

    def _fake_extract(html_text, **kw):
        calls.append(kw.get("favor_recall", False))
        if kw.get("favor_recall"):
            return "r" * 400
        return "too short"

    monkeypatch.setattr(trafilatura, "extract", _fake_extract)
    text, variant = iu._extract_article_text("<html>...</html>")
    assert variant == "recall" and len(text) == 400
    assert calls == [False, True]


def test_extract_default_wins_when_rich(monkeypatch):
    import trafilatura

    def _fake_extract(html_text, **kw):
        assert not kw.get("favor_recall"), "recall nedrīkst saukt pie zaļa noklusējuma"
        return "w" * 500

    monkeypatch.setattr(trafilatura, "extract", _fake_extract)
    text, variant = iu._extract_article_text("<html>...</html>")
    assert (variant, len(text)) == ("default", 500)


def test_extract_both_thin_stays_default(monkeypatch):
    import trafilatura

    monkeypatch.setattr(trafilatura, "extract", lambda *a, **k: "short")
    text, variant = iu._extract_article_text("<html>...</html>")
    assert (text, variant) == ("short", "default")


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


# --- _LAST_FETCH_ERROR --------------------------------------------------------
#
# _default_fetch returns None for every failure class, so a caller that needs
# the distinction (the truncated-doc backfill separates soft-404 from plain
# fetch errors in its denominator report) reads _LAST_FETCH_ERROR afterwards —
# same convention as _LAST_INGESTED_IDS above.


class _FakeResp:
    def __init__(self, text="", url="", headers=None, content=b""):
        self.text = text
        self.url = url
        self.headers = headers or {}
        self.content = content

    def raise_for_status(self):
        pass


class _FakeClient:
    def __init__(self, resp=None, exc=None, **kw):
        self._resp = resp
        self._exc = exc

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get(self, url):
        if self._exc:
            raise self._exc
        return self._resp


def test_last_fetch_error_http(monkeypatch):
    import httpx

    monkeypatch.setattr(
        httpx, "Client",
        lambda **kw: _FakeClient(exc=RuntimeError("conn reset")),
    )
    assert iu._default_fetch("https://a.lv/x.a1") is None
    assert iu._LAST_FETCH_ERROR.startswith("http:")


def test_last_fetch_error_soft_404(monkeypatch):
    """An article-path fetch landing on the site root is a soft-404, and the
    reason must be visible to the caller — not just a stderr line."""
    import httpx

    resp = _FakeResp(
        text="<html><title>LSM.lv - Uzticamas ziņas</title></html>",
        url="https://www.lsm.lv/",  # dead article id redirected to root
    )
    monkeypatch.setattr(httpx, "Client", lambda **kw: _FakeClient(resp=resp))
    out = iu._default_fetch("https://www.lsm.lv/raksts/zinas/dead.a999")
    assert out is None
    assert iu._LAST_FETCH_ERROR.startswith("soft_404:")


def test_last_fetch_error_cleared_on_success(monkeypatch):
    import httpx

    monkeypatch.setattr(
        httpx, "Client",
        lambda **kw: _FakeClient(exc=RuntimeError("boom")),
    )
    iu._default_fetch("https://a.lv/fail.a1")
    assert iu._LAST_FETCH_ERROR is not None

    resp = _FakeResp(text="<html><body>raksts</body></html>",
                     url="https://a.lv/ok.a2")
    monkeypatch.setattr(httpx, "Client", lambda **kw: _FakeClient(resp=resp))
    iu._default_fetch("https://a.lv/ok.a2")
    assert iu._LAST_FETCH_ERROR is None
