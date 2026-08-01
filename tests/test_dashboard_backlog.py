"""Task 1.6 — extraction backlog panel."""
from __future__ import annotations

import os
import sqlite3
import tempfile

import pytest

from src.db import init_db


@pytest.fixture(autouse=True)
def _reset_backlog_cache():
    from src.dashboard.views import backlog

    backlog._CACHE.clear()
    backlog._CACHE.update({"key": None, "ts": None, "result": None})
    yield
    backlog._CACHE.clear()
    backlog._CACHE.update({"key": None, "ts": None, "result": None})


@pytest.fixture
def backlog_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    try:
        os.unlink(path)
    except PermissionError:
        pass


def _seed_doc(db, *, doc_id: int, platform: str, scraped_at: str,
              reviewed: bool, politician_id: int | None = None):
    db.execute(
        "INSERT INTO documents (id, content, content_hash, platform, scraped_at, reviewed_at) "
        "VALUES (?, 'c', ?, ?, ?, ?)",
        (doc_id, f"h{doc_id}", platform, scraped_at, "2026-01-01" if reviewed else None),
    )
    if politician_id is not None:
        db.execute(
            "INSERT INTO document_politicians (document_id, politician_id, role) VALUES (?, ?, 'subject')",
            (doc_id, politician_id),
        )


def _seed_pol(db, *, pid: int, name: str, party: str = "TP",
              relationship_type: str = "tracked"):
    db.execute(
        "INSERT INTO tracked_politicians (id, name, party, relationship_type) VALUES (?, ?, ?, ?)",
        (pid, name, party, relationship_type),
    )


def test_backlog_aggregates_unreviewed_by_platform(backlog_db):
    from src.dashboard.views.backlog import get_backlog_context

    db = sqlite3.connect(backlog_db)
    _seed_doc(db, doc_id=1, platform="web", scraped_at="2026-04-07 09:00:00", reviewed=False)
    _seed_doc(db, doc_id=2, platform="web", scraped_at="2026-04-07 10:00:00", reviewed=False)
    _seed_doc(db, doc_id=3, platform="twitter", scraped_at="2026-04-07 11:00:00", reviewed=False)
    _seed_doc(db, doc_id=4, platform="web", scraped_at="2026-04-07 12:00:00", reviewed=True)  # excluded
    db.commit()
    db.close()

    ctx = get_backlog_context(date="2026-04-07", db_path=backlog_db)
    by_platform = {p["platform"]: p for p in ctx["platforms"]}
    assert by_platform["web"]["today"] == 2
    assert by_platform["twitter"]["today"] == 1
    assert ctx["today_unreviewed"] == 3
    assert ctx["total_unreviewed"] == 3  # nothing outside today


def test_backlog_top_pids_excludes_inactive(backlog_db):
    from src.dashboard.views.backlog import get_backlog_context

    db = sqlite3.connect(backlog_db)
    _seed_pol(db, pid=1, name="Aktīvais", relationship_type="tracked")
    _seed_pol(db, pid=2, name="Pasīvais", relationship_type="inactive")
    _seed_doc(db, doc_id=10, platform="web", scraped_at="2026-04-07", reviewed=False, politician_id=1)
    _seed_doc(db, doc_id=11, platform="web", scraped_at="2026-04-07", reviewed=False, politician_id=1)
    _seed_doc(db, doc_id=12, platform="web", scraped_at="2026-04-07", reviewed=False, politician_id=2)
    db.commit()
    db.close()

    ctx = get_backlog_context(date="2026-04-07", db_path=backlog_db)
    pid_names = {p["name"] for p in ctx["top_pids"]}
    assert "Pasīvais" not in pid_names, "relationship_type='inactive' must be excluded"
    assert "Aktīvais" in pid_names


def test_backlog_top_pids_returns_at_most_5(backlog_db):
    from src.dashboard.views.backlog import get_backlog_context

    db = sqlite3.connect(backlog_db)
    for i in range(1, 8):  # 7 politicians, each with 1 doc
        _seed_pol(db, pid=i, name=f"Pol{i}")
        _seed_doc(db, doc_id=100 + i, platform="web", scraped_at="2026-04-07",
                  reviewed=False, politician_id=i)
    db.commit()
    db.close()

    ctx = get_backlog_context(date="2026-04-07", db_path=backlog_db)
    assert len(ctx["top_pids"]) <= 5


def test_backlog_uses_30s_cache(backlog_db, monkeypatch):
    from src.dashboard.views import backlog

    counter = {"n": 0}
    real_compute = backlog._compute_backlog

    def counting_compute(*args, **kwargs):
        counter["n"] += 1
        return real_compute(*args, **kwargs)

    monkeypatch.setattr(backlog, "_compute_backlog", counting_compute)

    backlog.get_backlog_context(date="2026-04-07", db_path=backlog_db)
    backlog.get_backlog_context(date="2026-04-07", db_path=backlog_db)
    backlog.get_backlog_context(date="2026-04-07", db_path=backlog_db)
    assert counter["n"] == 1, "cache must absorb repeated reads within 30s"


def test_backlog_day_boundary_is_the_lv_day(backlog_db):
    """`documents.scraped_at` ir LV kolonna — 22:00 doks pieder TAJAI dienai.

    Līdz 2026-08-01 abi paneļa vaicājumi lika tai virsū `'localtime'`, kas LV
    laiku pārvērš vēlreiz: vakardienas 21:00–24:00 partija ieskaitījās šodienā,
    bet šodienas vakara partija — tā, no kuras operators gatavojas ekstraģēt —
    pazuda. Mērīts pret dzīvo DB 2026-08-01: panelis 558, `routine.py` 295.

    Pārējie šī faila testi sēj tikai 09:00–12:00, tāpēc ±3 h nekad nešķērsoja
    pusnakti un suite bija pret šo akla.

    **Skaitīt nepietiek — jāpārbauda piederība.** Kļūdainais vaicājums šajā
    kopā atdotu tikpat rindu (2), tikai citas, tāpēc katram dokumentam šeit ir
    sava `platform`, un apgalvojums ir par sadalījumu.

    Šis tests noķer kļūdu tikai tur, kur mašīnas lokālā zona atšķiras no UTC
    (operatora Windows = Europe/Riga; CI = UTC). Zonas ziņā neatkarīgie vārti
    šai klasei ir `tests/test_timestamp_timezone_gate.py`.
    """
    from src.dashboard.views.backlog import get_backlog_context

    db = sqlite3.connect(backlog_db)
    # iepriekšējā LV diena, vēls vakars — NEDRĪKST ieskaitīties
    _seed_doc(db, doc_id=1, platform="web", scraped_at="2026-04-06 22:00:00", reviewed=False)
    # mērķa LV diena, tūlīt pēc pusnakts
    _seed_doc(db, doc_id=2, platform="twitter", scraped_at="2026-04-07 00:30:00", reviewed=False)
    # mērķa LV diena, vēls vakars — tieši tā partija, ko kļūda noslēpa
    _seed_doc(db, doc_id=3, platform="x_mention", scraped_at="2026-04-07 22:00:00", reviewed=False)
    # nākamā LV diena — NEDRĪKST ieskaitīties
    _seed_doc(db, doc_id=4, platform="vestnesis", scraped_at="2026-04-08 00:30:00", reviewed=False)
    db.commit()
    db.close()

    ctx = get_backlog_context(date="2026-04-07", db_path=backlog_db)
    today = {p["platform"]: p["today"] for p in ctx["platforms"]}

    assert today.get("x_mention") == 1, "22:00 LV doks pieder savai LV dienai"
    assert today.get("twitter") == 1, "00:30 LV doks pieder savai LV dienai"
    assert today.get("web") == 0, "iepriekšējās dienas 22:00 doks nedrīkst ieskaitīties"
    assert today.get("vestnesis") == 0, "nākamās dienas 00:30 doks nedrīkst ieskaitīties"
    assert ctx["today_unreviewed"] == 2
    assert ctx["total_unreviewed"] == 4


def test_backlog_empty_state_on_clean_db(backlog_db):
    from src.dashboard.views.backlog import get_backlog_context

    ctx = get_backlog_context(date="2026-04-07", db_path=backlog_db)
    assert ctx["today_unreviewed"] == 0
    assert ctx["total_unreviewed"] == 0
    assert ctx["platforms"] == []
    assert ctx["top_pids"] == []


def test_index_renders_backlog_panel_empty_state(backlog_db):
    from src.dashboard.server import create_app

    app = create_app(db_path=backlog_db)
    html = app.test_client().get("/").get_data(as_text=True)
    assert 'id="backlog-panel"' in html
    # Empty-state copy must be the friendly LV one, not "no data found"
    assert "Nav neapstrādātu" in html or "nesarķistītu" in html.lower() or "🌱" in html
