"""Tests for scripts/backfill_truncated_docs.py — truncated web doc re-fetch.

Network (fetch_fn) and the write call (insert_fn) are injected; the DB is a
temp file built by init_db. No real HTTP, no live-DB writes.

The contract under test (backlog/avoti.md § truncated backfill + T19):
dry-run writes nothing, --apply requires a rollback file that is written and
fsynced BEFORE the first UPDATE, a re-fetched doc is accepted only when it is
provably the same story AND meaningfully longer, and every doc lands in a
named class so the summary denominator is honest.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import get_db, init_db, insert_document, now_lv  # noqa: E402
import scripts.backfill_truncated_docs as bf  # noqa: E402


@pytest.fixture
def tmp_db(tmp_path) -> str:
    db_path = str(tmp_path / "t.db")
    init_db(db_path=db_path)
    return db_path


PID = 7


def _seed_politician(db_path, pid=PID, name="Tests Politiķis"):
    db = get_db(db_path)
    db.execute(
        "INSERT INTO tracked_politicians (id, name, name_forms, relationship_type) "
        "VALUES (?, ?, ?, ?)",
        (pid, name, json.dumps([name, name.split()[-1]]), "tracked"),
    )
    db.commit()
    db.close()


def _seed_doc(db_path, url, n_words, *, tag, platform="web", paywall=0,
              scraped_at="2020-01-01 00:00:00",
              reviewed_at="2020-06-01 00:00:00",
              published_at="2020-01-01", title="Vecais virsraksts",
              with_url=True):
    """Insert a 'truncated' doc through the real write path, then backdate."""
    content = " ".join([tag] + [f"w{i}" for i in range(n_words - 1)])
    doc_id = insert_document(
        content=content, source_id=None, platform=platform,
        source_url=url if with_url else None, title=title, db_path=db_path,
    )
    db = get_db(db_path)
    db.execute(
        "UPDATE documents SET scraped_at=?, reviewed_at=?, is_paywall=?, "
        "published_at=? WHERE id=?",
        (scraped_at, reviewed_at, paywall, published_at, doc_id),
    )
    db.commit()
    db.close()
    return doc_id


def _add_claim(db_path, doc_id, pid=PID):
    db = get_db(db_path)
    db.execute(
        "INSERT INTO claims (opponent_id, document_id, topic, stance) "
        "VALUES (?, ?, 'Tēma', 'nostāja')",
        (pid, doc_id),
    )
    db.commit()
    db.close()


def _add_junction(db_path, doc_id, pid=PID, role="subject"):
    db = get_db(db_path)
    db.execute(
        "INSERT INTO document_politicians (document_id, politician_id, role) "
        "VALUES (?, ?, ?)",
        (doc_id, pid, role),
    )
    db.commit()
    db.close()


def _longer_same_story(db_path, doc_id, extra_words=60):
    """Fetch-able text: the stored content verbatim + extra words appended."""
    db = get_db(db_path)
    content = db.execute(
        "SELECT content FROM documents WHERE id=?", (doc_id,)
    ).fetchone()["content"]
    db.close()
    return content + " " + " ".join(f"papildu{i}" for i in range(extra_words))


def _fetch_text(text, title="Jaunais virsraksts", published_at="2020-01-02"):
    return lambda url: {"text": text, "title": title, "published_at": published_at}


def _dump(db_path, table):
    db = get_db(db_path)
    rows = db.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall()
    db.close()
    return [tuple(r) for r in rows]


def _full_dump(db_path):
    """Row dump of every table (iterdump chokes on the vec0 virtual tables)."""
    db = get_db(db_path)
    # vec0 virtual tables cannot be SELECTed without the extension loaded.
    tables = [r[0] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND sql NOT LIKE 'CREATE VIRTUAL%' ORDER BY name"
    )]
    parts = []
    for t in tables:
        rows = db.execute(f"SELECT * FROM {t}").fetchall()
        parts.append(f"{t}:" + repr([tuple(r) for r in rows]))
    db.close()
    return "\n".join(parts)


def _run(db_path, fetch_fn, **kw):
    kw.setdefault("sleep_fn", lambda s: None)
    return bf.run_backfill(db_path=db_path, fetch_fn=fetch_fn, **kw)


# --- selection ------------------------------------------------------------


def test_select_orders_claims_first_then_id(tmp_db):
    _seed_politician(tmp_db)
    d1 = _seed_doc(tmp_db, "https://www.lsm.lv/raksts/a1.a1", 30, tag="viens")
    d2 = _seed_doc(tmp_db, "https://www.lsm.lv/raksts/a2.a2", 30, tag="divi")
    d3 = _seed_doc(tmp_db, "https://www.lsm.lv/raksts/a3.a3", 30, tag="tris")
    _add_claim(tmp_db, d3)

    db = get_db(tmp_db)
    rows = bf.select_candidates(db, max_words=90)
    db.close()
    assert [r["id"] for r in rows] == [d3, d1, d2]
    assert rows[0]["had_claims"] == 1


def test_select_filters_platform_word_count_and_url(tmp_db):
    keep = _seed_doc(tmp_db, "https://a.lv/1.a1", 30, tag="web")
    _seed_doc(tmp_db, "https://x.com/u/status/1", 30, tag="tw", platform="twitter")
    _seed_doc(tmp_db, "https://a.lv/2.a2", 200, tag="gars")
    _seed_doc(tmp_db, "https://a.lv/3.a3", 30, tag="beza", with_url=False)

    db = get_db(tmp_db)
    rows = bf.select_candidates(db, max_words=90)
    db.close()
    assert [r["id"] for r in rows] == [keep]


def test_select_domain_filter_normalizes_www(tmp_db):
    a = _seed_doc(tmp_db, "https://www.lsm.lv/raksts/a.a1", 30, tag="lsm")
    _seed_doc(tmp_db, "https://tvnet.lv/12345/b", 30, tag="tvn")

    db = get_db(tmp_db)
    rows = bf.select_candidates(db, max_words=90, domain="lsm.lv")
    db.close()
    assert [r["id"] for r in rows] == [a]


def test_select_ids_from_restricts_set(tmp_db):
    a = _seed_doc(tmp_db, "https://a.lv/1.a1", 30, tag="viens")
    _seed_doc(tmp_db, "https://a.lv/2.a2", 30, tag="divi")

    db = get_db(tmp_db)
    rows = bf.select_candidates(db, max_words=90, ids=[a])
    db.close()
    assert [r["id"] for r in rows] == [a]


def test_select_limit(tmp_db):
    _seed_doc(tmp_db, "https://a.lv/1.a1", 30, tag="viens")
    _seed_doc(tmp_db, "https://a.lv/2.a2", 30, tag="divi")

    db = get_db(tmp_db)
    rows = bf.select_candidates(db, max_words=90, limit=1)
    db.close()
    assert len(rows) == 1


def test_paywall_excluded_by_default(tmp_db):
    _seed_doc(tmp_db, "https://a.lv/1.a1", 30, tag="free")
    pay = _seed_doc(tmp_db, "https://a.lv/2.a2", 30, tag="pay", paywall=1)

    db = get_db(tmp_db)
    default = bf.select_candidates(db, max_words=90)
    included = bf.select_candidates(db, max_words=90, include_paywall=True)
    db.close()
    assert pay not in [r["id"] for r in default]
    assert pay in [r["id"] for r in included]


# --- classification (dry-run) ----------------------------------------------


def test_fetch_error_class(tmp_db):
    _seed_doc(tmp_db, "https://a.lv/1.a1", 30, tag="x")
    summary = _run(tmp_db, lambda url: None)
    rec = summary["records"][0]
    assert rec["class"] == "fetch_error"
    assert summary["fetch_error"] == 1 and summary["fetched_ok"] == 0


def test_fetch_exception_never_raises(tmp_db):
    _seed_doc(tmp_db, "https://a.lv/1.a1", 30, tag="x")

    def _boom(url):
        raise RuntimeError("connection reset")

    summary = _run(tmp_db, _boom)
    assert summary["records"][0]["class"] == "fetch_error"


def test_soft_404_class(tmp_db):
    _seed_doc(tmp_db, "https://www.lsm.lv/raksts/dead.a1", 30, tag="x")
    summary = _run(tmp_db, lambda url: {"soft_404": "redirected to site root"})
    rec = summary["records"][0]
    assert rec["class"] == "soft_404"
    assert summary["soft_404"] == 1 and summary["fetched_ok"] == 0


def test_not_longer_class(tmp_db):
    doc_id = _seed_doc(tmp_db, "https://a.lv/1.a1", 30, tag="x")
    # +10 words: neither >1.5x nor >= old+40
    text = _longer_same_story(tmp_db, doc_id, extra_words=10)
    summary = _run(tmp_db, _fetch_text(text))
    assert summary["records"][0]["class"] == "not_longer"
    assert summary["fetched_ok"] == 1


def test_different_story_class(tmp_db):
    _seed_doc(tmp_db, "https://a.lv/1.a1", 30, tag="x")
    # Longer, but none of the stored lead survives — doc-72446 class.
    text = " ".join(f"cits{i}" for i in range(200))
    summary = _run(tmp_db, _fetch_text(text))
    assert summary["records"][0]["class"] == "different_story"


def test_would_update_class(tmp_db):
    doc_id = _seed_doc(tmp_db, "https://a.lv/1.a1", 30, tag="x")
    text = _longer_same_story(tmp_db, doc_id, extra_words=60)
    summary = _run(tmp_db, _fetch_text(text))
    rec = summary["records"][0]
    assert rec["class"] == "would_update"
    assert rec["new_words"] == len(text.split())
    assert summary["would_update"] == 1


def test_dry_run_leaves_db_byte_identical(tmp_db):
    _seed_politician(tmp_db)
    doc_id = _seed_doc(tmp_db, "https://a.lv/1.a1", 30, tag="x")
    _add_claim(tmp_db, doc_id)
    _add_junction(tmp_db, doc_id)
    before = _full_dump(tmp_db)

    text = _longer_same_story(tmp_db, doc_id, extra_words=60)
    summary = _run(tmp_db, _fetch_text(text))

    assert summary["would_update"] == 1
    assert _full_dump(tmp_db) == before


# --- rate limiting ----------------------------------------------------------


def test_rate_limit_sleeps_between_same_domain_fetches(tmp_db):
    _seed_doc(tmp_db, "https://a.lv/1.a1", 30, tag="viens")
    _seed_doc(tmp_db, "https://a.lv/2.a2", 30, tag="divi")
    sleeps = []
    _run(tmp_db, lambda url: None, sleep_fn=sleeps.append)
    assert len(sleeps) == 1
    assert 0.9 < sleeps[0] <= 1.0 + 1e-6


def test_rate_limit_not_across_domains(tmp_db):
    _seed_doc(tmp_db, "https://a.lv/1.a1", 30, tag="viens")
    _seed_doc(tmp_db, "https://b.lv/2.b2", 30, tag="divi")
    _seed_doc(tmp_db, "https://www.a.lv/3.a3", 30, tag="tris")  # www ≈ same domain
    sleeps = []
    _run(tmp_db, lambda url: None, sleep_fn=sleeps.append)
    # a.lv → b.lv free; a.lv again (www.) → one sleep
    assert len(sleeps) == 1


# --- apply ------------------------------------------------------------------


def _apply_args(tmp_path):
    return {"apply": True, "rollback_path": str(tmp_path / "rollback.sql")}


def test_apply_requires_rollback_path(tmp_db):
    doc_id = _seed_doc(tmp_db, "https://a.lv/1.a1", 30, tag="x")
    text = _longer_same_story(tmp_db, doc_id, extra_words=60)
    with pytest.raises((ValueError, SystemExit)):
        _run(tmp_db, _fetch_text(text), apply=True, rollback_path=None)


def test_apply_updates_row_and_preserves_scraped_at(tmp_db, tmp_path):
    doc_id = _seed_doc(tmp_db, "https://a.lv/1.a1", 30, tag="x")
    old_scraped = "2020-01-01 00:00:00"
    text = _longer_same_story(tmp_db, doc_id, extra_words=60)

    summary = _run(tmp_db, _fetch_text(text), **_apply_args(tmp_path))

    rec = summary["records"][0]
    assert rec["class"] == "updated"
    assert summary["updated"] == 1

    db = get_db(tmp_db)
    row = db.execute(
        "SELECT content, word_count, scraped_at, reviewed_at, title "
        "FROM documents WHERE id=?", (doc_id,),
    ).fetchone()
    db.close()
    assert row["content"] == text
    assert row["word_count"] == len(text.split())
    assert row["scraped_at"] == old_scraped, "historic doc must not redate"
    assert row["reviewed_at"] is None, "new text re-enters extraction queue"
    assert row["title"] == "Jaunais virsraksts"


def test_rollback_written_before_first_update(tmp_db, tmp_path):
    doc_id = _seed_doc(tmp_db, "https://a.lv/1.a1", 30, tag="x")
    text = _longer_same_story(tmp_db, doc_id, extra_words=60)
    rollback_path = tmp_path / "rollback.sql"
    seen = {}

    def spy_insert(**kw):
        seen["sql"] = (
            rollback_path.read_text(encoding="utf-8")
            if rollback_path.exists() else None
        )
        return insert_document(**kw)

    _run(tmp_db, _fetch_text(text), apply=True,
         rollback_path=str(rollback_path), insert_fn=spy_insert)

    assert seen["sql"], "rollback file must exist before the first UPDATE"
    assert f"WHERE id = {doc_id}" in seen["sql"]


def test_rollback_restores_rows(tmp_db, tmp_path):
    _seed_politician(tmp_db)
    doc_id = _seed_doc(tmp_db, "https://a.lv/1.a1", 30, tag="x")
    _add_junction(tmp_db, doc_id)  # name absent from new text → flagged
    before_docs = _dump(tmp_db, "documents")
    before_junction = _dump(tmp_db, "document_politicians")

    text = _longer_same_story(tmp_db, doc_id, extra_words=60)
    rb = tmp_path / "rollback.sql"
    summary = _run(tmp_db, _fetch_text(text), apply=True, rollback_path=str(rb))
    assert summary["updated"] == 1

    db = get_db(tmp_db)
    db.executescript(rb.read_text(encoding="utf-8"))
    db.close()
    assert _dump(tmp_db, "documents") == before_docs
    assert _dump(tmp_db, "document_politicians") == before_junction


def test_rollback_covers_suspect_at_flag(tmp_db, tmp_path):
    """The junction flag written by the UPDATE must be in the rollback."""
    _seed_politician(tmp_db)
    doc_id = _seed_doc(tmp_db, "https://a.lv/1.a1", 30, tag="x")
    _add_junction(tmp_db, doc_id)
    text = _longer_same_story(tmp_db, doc_id, extra_words=60)
    rb = tmp_path / "rollback.sql"

    summary = _run(tmp_db, _fetch_text(text), apply=True, rollback_path=str(rb))
    rec = summary["records"][0]
    assert rec["class"] == "updated"
    assert rec["suspects_flagged"] == 1

    sql = rb.read_text(encoding="utf-8")
    assert "document_politicians" in sql
    assert f"document_id = {doc_id}" in sql


def test_update_failed_is_reported_not_silent(tmp_db, tmp_path):
    doc_id = _seed_doc(tmp_db, "https://a.lv/1.a1", 30, tag="x")
    text = _longer_same_story(tmp_db, doc_id, extra_words=60)

    summary = _run(
        tmp_db, _fetch_text(text),
        insert_fn=lambda **kw: None,  # write silently refused
        **_apply_args(tmp_path),
    )
    assert summary["records"][0]["class"] == "update_failed"
    assert summary["update_failed"] == 1 and summary["updated"] == 0


def test_updated_docs_with_claims_are_listed(tmp_db, tmp_path):
    _seed_politician(tmp_db)
    doc_id = _seed_doc(tmp_db, "https://a.lv/1.a1", 30, tag="x")
    _add_claim(tmp_db, doc_id)
    other = _seed_doc(tmp_db, "https://a.lv/2.a2", 30, tag="y")

    texts = {
        "https://a.lv/1.a1": _longer_same_story(tmp_db, doc_id, extra_words=60),
        "https://a.lv/2.a2": _longer_same_story(tmp_db, other, extra_words=60),
    }
    summary = _run(
        tmp_db, lambda url: {"text": texts[url], "title": None, "published_at": None},
        **_apply_args(tmp_path),
    )
    assert summary["claims_docs"] == [doc_id]


# --- report + main ----------------------------------------------------------


def test_report_jsonl_written(tmp_db, tmp_path):
    doc_id = _seed_doc(tmp_db, "https://a.lv/1.a1", 30, tag="x")
    report = tmp_path / "r.jsonl"
    text = _longer_same_story(tmp_db, doc_id, extra_words=60)
    _run(tmp_db, _fetch_text(text), report_path=str(report))

    lines = report.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    for key in ("doc_id", "url", "domain", "old_words", "new_words",
                "class", "had_claims", "suspects_flagged"):
        assert key in rec, key
    assert rec["doc_id"] == doc_id and rec["domain"] == "a.lv"
    assert rec["old_words"] == 30 and rec["class"] == "would_update"


def test_main_dry_run_exit_0(tmp_db, tmp_path, capsys, monkeypatch):
    _seed_doc(tmp_db, "https://a.lv/1.a1", 30, tag="x")
    # No real HTTP in tests — stub the module-level default fetch.
    monkeypatch.setattr(bf, "_default_backfill_fetch", lambda url: None)
    rc = bf.main([
        "--db", tmp_db, "--report", str(tmp_path / "r.jsonl"),
        "--limit", "5",
    ])
    out = capsys.readouterr().out
    assert rc == 0
    assert "examined=1" in out


def test_main_empty_selection_exit_2(tmp_db, tmp_path):
    rc = bf.main(["--db", tmp_db, "--report", str(tmp_path / "r.jsonl")])
    assert rc == 2


def test_main_apply_without_rollback_out_exit_2(tmp_db, tmp_path):
    _seed_doc(tmp_db, "https://a.lv/1.a1", 30, tag="x")
    rc = bf.main([
        "--db", tmp_db, "--report", str(tmp_path / "r.jsonl"), "--apply",
    ])
    assert rc == 2


def test_ids_from_file(tmp_db, tmp_path):
    a = _seed_doc(tmp_db, "https://a.lv/1.a1", 30, tag="viens")
    _seed_doc(tmp_db, "https://a.lv/2.a2", 30, tag="divi")
    ids_file = tmp_path / "ids.txt"
    ids_file.write_text(f"{a}\n# komentārs\nnav-skaitlis\n", encoding="utf-8")

    summary = _run(
        tmp_db, lambda url: None,
        ids=bf.read_ids_file(str(ids_file)),
    )
    assert summary["examined"] == 1
    assert summary["records"][0]["doc_id"] == a


# ── Virsraksta pierādījums + ievada saglabāšana (2026-09-23 dry-run) ─────
# Dzīvais sausais palaidiens: 49 no 50 → different_story, jo trafilatura uz
# lsm.lv/diena.lv NOMET ievadu — glabātais «virsraksts — ievads» jaunajā
# tekstā nav. 45 no tiem sakrita pēc virsraksta. Aizstāšana izdzēstu ievadu.


def _seed_stub(db_path, url, *, head="Ministrs: jāsamazina akcīze",
               lede_words=40, title=None):
    lede = " ".join(f"ievads{i}" for i in range(lede_words))
    doc_id = insert_document(
        content=f"{head} — {lede}", source_id=None, platform="web",
        source_url=url, title=title if title is not None else head,
        db_path=db_path,
    )
    return doc_id, f"{head} — {lede}"


def test_title_proof_accepts_when_trafilatura_dropped_the_lede(tmp_db):
    _seed_stub(tmp_db, "https://www.diena.lv/raksts/1")
    body = " ".join(f"kermenis{i}" for i in range(300))
    summary = _run(tmp_db, _fetch_text(body, title="Ministrs: jāsamazina akcīze — Diena"))
    rec = summary["records"][0]
    assert rec["class"] == "would_update"
    assert rec["proof"] == "title"


def test_title_proof_keeps_stub_in_front_of_body_on_apply(tmp_db, tmp_path):
    doc_id, stub = _seed_stub(tmp_db, "https://www.lsm.lv/raksts/x.a1/")
    body = " ".join(f"kermenis{i}" for i in range(300))
    _run(tmp_db, _fetch_text(body, title="Ministrs: jāsamazina akcīze / Raksts"),
         apply=True, rollback_path=str(tmp_path / "rb.sql"))
    db = get_db(tmp_db)
    content = db.execute("SELECT content FROM documents WHERE id=?", (doc_id,)).fetchone()[0]
    db.close()
    assert content == stub + "\n\n" + body, "ievads pazuda — aizstāts, ne papildināts"


def test_rewritten_headline_without_lede_is_different_story(tmp_db):
    """Rosļikovs 13779: «pametis partiju» → «pamet … amatu» = cits fakts."""
    _seed_stub(tmp_db, "https://www.lsm.lv/raksts/r.a2/",
               head="Rosļikovs pametis partiju «Stabilitātei!»")
    body = " ".join(f"kermenis{i}" for i in range(300))
    summary = _run(tmp_db, _fetch_text(
        body, title="Rosļikovs pamet partijas «Stabilitātei!» valdes priekšsēdētāja amatu"))
    assert summary["records"][0]["class"] == "different_story"


def test_html_entities_in_stored_title_do_not_break_title_proof(tmp_db):
    _seed_stub(tmp_db, "https://www.diena.lv/raksts/2",
               head='Mieriņa nedomā, ka jādemisionē "airBaltic" dēļ',
               title='Mieriņa nedomā, ka jādemisionē &quot;airBaltic&quot; dēļ')
    body = " ".join(f"kermenis{i}" for i in range(300))
    summary = _run(tmp_db, _fetch_text(
        body, title='Mieriņa nedomā, ka jādemisionē "airBaltic" dēļ — Diena'))
    assert summary["records"][0]["proof"] == "title"


# --- relink after rewrite (2026-09-23) --------------------------------------
# The UPDATE branch only merges the caller's politician_links, and this script
# passes none; the morning backstop scans only docs with NO junction rows. So a
# politician named only in the re-fetched full text was never linked: batch 2
# left 24 speaker↔document pairs unlinked. After the rewrite the matcher must
# run over exactly the updated docs, and every junction it adds must be in the
# rollback.

OTHER = 8


def _spy_link(tmp_db, calls, new_rows):
    def link(doc_ids):
        calls.append(list(doc_ids))
        db = get_db(tmp_db)
        for did in doc_ids:
            for pid, role in new_rows:
                db.execute(
                    "INSERT OR IGNORE INTO document_politicians "
                    "(document_id, politician_id, role) VALUES (?, ?, ?)",
                    (did, pid, role),
                )
        db.commit()
        db.close()
        return {did: [p for p, _ in new_rows] for did in doc_ids}
    return link


def test_apply_relinks_exactly_the_updated_docs(tmp_db, tmp_path):
    _seed_politician(tmp_db)
    _seed_politician(tmp_db, pid=OTHER, name="Otrs Politiķis")
    upd = _seed_doc(tmp_db, "https://a.lv/1.a1", 30, tag="x")
    short = _seed_doc(tmp_db, "https://a.lv/2.a2", 30, tag="y")
    texts = {"https://a.lv/1.a1": _longer_same_story(tmp_db, upd, 60),
             "https://a.lv/2.a2": _longer_same_story(tmp_db, short, 1)}
    calls: list = []
    summary = _run(
        tmp_db,
        lambda url: {"text": texts[url], "title": "t", "published_at": "2020-01-02"},
        apply=True, rollback_path=str(tmp_path / "rb.sql"),
        link_fn=_spy_link(tmp_db, calls, [(OTHER, "mentioned")]),
    )
    assert summary["updated"] == 1
    assert calls == [[upd]]
    assert summary["junctions_added"] == 1


def test_rollback_deletes_junctions_added_by_relink(tmp_db, tmp_path):
    _seed_politician(tmp_db)
    _seed_politician(tmp_db, pid=OTHER, name="Otrs Politiķis")
    doc_id = _seed_doc(tmp_db, "https://a.lv/1.a1", 30, tag="x")
    _add_junction(tmp_db, doc_id)
    before_junction = _dump(tmp_db, "document_politicians")
    before_docs = _dump(tmp_db, "documents")
    rb = tmp_path / "rb.sql"
    _run(tmp_db, _fetch_text(_longer_same_story(tmp_db, doc_id, 60)),
         apply=True, rollback_path=str(rb),
         link_fn=_spy_link(tmp_db, [], [(OTHER, "mentioned")]))
    assert len(_dump(tmp_db, "document_politicians")) == len(before_junction) + 1

    db = get_db(tmp_db)
    db.executescript(rb.read_text(encoding="utf-8"))
    db.close()
    assert _dump(tmp_db, "document_politicians") == before_junction
    assert _dump(tmp_db, "documents") == before_docs


def test_dry_run_never_relinks(tmp_db):
    _seed_politician(tmp_db)
    doc_id = _seed_doc(tmp_db, "https://a.lv/1.a1", 30, tag="x")
    calls: list = []
    _run(tmp_db, _fetch_text(_longer_same_story(tmp_db, doc_id, 60)),
         link_fn=_spy_link(tmp_db, calls, [(OTHER, "mentioned")]))
    assert calls == []


def test_default_link_fn_is_the_matcher_only_on_the_live_db():
    from src.matcher import link_politicians_to_documents
    fn = bf._resolve_link_fn(bf.DB_PATH, None)
    assert fn is not None
    assert getattr(fn, "__wrapped_matcher__", None) is link_politicians_to_documents
    # A temp DB must never be relinked through the production matcher.
    assert bf._resolve_link_fn("/tmp/other.db", None) is None


def test_relink_never_adds_a_second_subject(tmp_db, tmp_path):
    """A doc that already has a subject gets new pids only as 'mentioned' —
    a subject role needs speaker evidence, and a full text that merely NAMES a
    politician is not that (2026-09-23: 82 such rows from one relink)."""
    _seed_politician(tmp_db)
    _seed_politician(tmp_db, pid=OTHER, name="Otrs Politiķis")
    doc_id = _seed_doc(tmp_db, "https://a.lv/1.a1", 30, tag="x")
    _add_junction(tmp_db, doc_id)  # PID is the existing subject
    _run(tmp_db, _fetch_text(_longer_same_story(tmp_db, doc_id, 60)),
         apply=True, rollback_path=str(tmp_path / "rb.sql"),
         link_fn=_spy_link(tmp_db, [], [(OTHER, "subject")]))
    db = get_db(tmp_db)
    role = db.execute(
        "SELECT role FROM document_politicians WHERE document_id=? AND politician_id=?",
        (doc_id, OTHER)).fetchone()["role"]
    db.close()
    assert role == "mentioned"


def test_relink_keeps_subject_when_doc_had_none(tmp_db, tmp_path):
    _seed_politician(tmp_db, pid=OTHER, name="Otrs Politiķis")
    doc_id = _seed_doc(tmp_db, "https://a.lv/1.a1", 30, tag="x")
    _run(tmp_db, _fetch_text(_longer_same_story(tmp_db, doc_id, 60)),
         apply=True, rollback_path=str(tmp_path / "rb.sql"),
         link_fn=_spy_link(tmp_db, [], [(OTHER, "subject")]))
    db = get_db(tmp_db)
    role = db.execute(
        "SELECT role FROM document_politicians WHERE document_id=? AND politician_id=?",
        (doc_id, OTHER)).fetchone()["role"]
    db.close()
    assert role == "subject"
