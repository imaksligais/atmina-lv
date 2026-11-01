"""Phase 1C — /likumi.html base-law index page."""
import os
import sqlite3
import tempfile
from pathlib import Path

import pytest

from src.db import init_db, get_db
from src.saeima import init_saeima_tables, init_saeima_bills, load_laws_index
from src.render import generate_public_site
from src.render.laws import _fetch_law_index_page


@pytest.fixture
def laws_dir() -> Path:
    """Use the real wiki/laws/ — index page reads it directly."""
    return Path("wiki/laws")


@pytest.fixture
def db_with_one_bill(laws_dir):
    """Fresh DB with saeima_bills + 1 row attached to a wiki/laws/ slug."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    init_saeima_tables(path)
    init_saeima_bills(path)
    db = get_db(path)
    db.execute("""
        INSERT INTO saeima_bills (document_nr, bill_type, title, topic, base_law_slug,
                                  current_stage, current_status, first_seen_at,
                                  last_updated_at)
        VALUES ('1288/Lp14', 'Lp14', 'Grozījums Saeimas vēlēšanu likumā',
                'Tieslietas', 'saeimas-velesanu-likums',
                '1.lasījums', 'procesā', '2026-04-01 10:00:00', '2026-04-15 14:00:00')
    """)
    db.commit()
    yield path
    db.close()
    try:
        os.unlink(path)
    except PermissionError:
        pass


def test_includes_all_wiki_laws(db_with_one_bill, laws_dir):
    db = get_db(db_with_one_bill)
    rows = _fetch_law_index_page(db, laws_dir=laws_dir)
    db.close()
    # load_laws_index expects wiki root (it appends /laws internally)
    assert len(rows) == len(load_laws_index(laws_dir.parent))
    assert all("slug" in r and "title" in r for r in rows)


def test_law_with_attached_bills_has_count(db_with_one_bill, laws_dir):
    db = get_db(db_with_one_bill)
    rows = _fetch_law_index_page(db, laws_dir=laws_dir)
    db.close()
    sv = next(r for r in rows if r["slug"] == "saeimas-velesanu-likums")
    assert sv["bill_count"] == 1
    assert sv["topic"] == "Tieslietas"  # derived from saeima_bills.topic


def test_law_without_bills_renders_zero_and_empty_topic(db_with_one_bill, laws_dir):
    db = get_db(db_with_one_bill)
    rows = _fetch_law_index_page(db, laws_dir=laws_dir)
    db.close()
    no_bills = [r for r in rows if r["bill_count"] == 0]
    assert len(no_bills) > 0  # most laws in wiki/laws/ have no attached bill in this fixture
    assert all(r["topic"] == "" for r in no_bills)


def test_rows_sorted_alphabetically_by_title(db_with_one_bill, laws_dir):
    db = get_db(db_with_one_bill)
    rows = _fetch_law_index_page(db, laws_dir=laws_dir)
    db.close()
    titles = [r["title"] for r in rows]
    assert titles == sorted(titles, key=str.casefold)


def test_likumi_index_html_generated_by_full_pipeline(db_with_one_bill, tmp_path, monkeypatch):
    """Smoke test: generate_public_site() emits /likumi.html with expected content.

    Renders the likumi + bills domains against the seeded one-bill fixture DB
    (not the live, gitignored data/atmina.db) into a temp output dir, so this runs
    in CI. chdir to repo root so wiki/laws/ (the base-law source) resolves; network
    asset downloads are stubbed.
    """
    import src.render._orchestrator as orch

    monkeypatch.chdir(Path(__file__).resolve().parent.parent)
    monkeypatch.setattr(orch, "_download_chart_js", lambda *a, **k: None)
    monkeypatch.setattr(orch, "_download_annotation_plugin", lambda *a, **k: None)

    out = tmp_path / "out"
    generate_public_site(db_path=db_with_one_bill, output_dir=str(out), only={"likumi", "bills"})
    site = out / "atmina"
    assert (site / "likumi.html").exists(), "/likumi.html was not generated"
    content = (site / "likumi.html").read_text(encoding="utf-8")
    assert "Pamatlikumi" in content
    assert 'href="likumi/saeimas-velesanu-likums.html"' in content
    # Sadaļas josla abās lapās (Task 2).
    assert '<a href="likumi.html" aria-current="page">Pamatlikumi (' in content
    assert '<a href="likumprojekti.html">Likumprojekti (1)</a>' in content
    bills_page = (site / "likumprojekti.html").read_text(encoding="utf-8")
    assert '<a href="likumprojekti.html" aria-current="page">Likumprojekti (1)</a>' in bills_page


def test_likumi_filters_in_browser(db_with_one_bill, tmp_path, monkeypatch):
    """Lapa kā likumprojekti.html (2026-10-20): skaits «Rāda N no M», filtrs
    «Ar likumprojektiem», meklēšana — pārlūkā skaits seko redzamajām kartītēm."""
    sync_api = pytest.importorskip("playwright.sync_api")
    import functools
    import threading
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

    import src.render._orchestrator as orch

    monkeypatch.chdir(Path(__file__).resolve().parent.parent)
    monkeypatch.setattr(orch, "_download_chart_js", lambda *a, **k: None)
    monkeypatch.setattr(orch, "_download_annotation_plugin", lambda *a, **k: None)
    out = tmp_path / "out"
    generate_public_site(db_path=db_with_one_bill, output_dir=str(out), only={"likumi", "bills", "static"})
    site = out / "atmina"
    total = len(load_laws_index(Path("wiki")))
    html = (site / "likumi.html").read_text(encoding="utf-8")
    assert f"Rāda {total} no {total}" in html
    assert "1 likumprojekts" in html  # vienskaitlis, ne «1 likumproj.»

    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(site)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with sync_api.sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except Exception as exc:  # pragma: no cover
                pytest.skip(f"Chromium nav pieejams: {exc}")
            page = browser.new_page()
            page.goto(f"http://127.0.0.1:{server.server_address[1]}/likumi.html")
            page.click('.likumi-has-bills .link-filter-btn[data-has="yes"]')
            assert page.get_attribute('.likumi-has-bills .link-filter-btn[data-has="yes"]', "aria-pressed") == "true"
            assert page.inner_text("#laws-count") == f"Rāda 1 no {total}"
            page.click('.likumi-has-bills .link-filter-btn[data-has=""]')
            page.fill("#law-search", "vēlēšanu")
            visible = page.evaluate("[...document.querySelectorAll('#laws-grid .bill-card')].filter(c => c.style.display !== 'none').length")
            assert page.inner_text("#laws-count") == f"Rāda {visible} no {total}"
            assert 0 < visible < total
            page.fill("#law-search", "")

            # Tēmu filtrs tikai ar tastatūru (Enter atver, ↓ uz opciju, Enter
            # izvēlas, Esc aizver un atdod fokusu trigerim) — sargā pāreju no
            # lkv1 paša multi-select koda uz kopīgo assets/msv1.js.
            trigger = "#law-topic-trigger"
            first = "#law-topic-select .multi-select-option >> nth=0"
            topic = page.get_attribute(first, "data-value")
            in_topic = page.evaluate(
                "t => [...document.querySelectorAll('#laws-grid .bill-card')]"
                ".filter(c => c.dataset.topic === t).length", topic)
            assert 0 < in_topic < total, f"tēmā «{topic}» {in_topic} no {total} — vārti nevar krist"
            page.focus(trigger)
            page.keyboard.press("Enter")
            assert page.get_attribute(trigger, "aria-expanded") == "true"
            page.wait_for_function("document.activeElement.classList.contains('multi-select-search')")
            page.keyboard.press("ArrowDown")
            page.keyboard.press("Enter")
            assert page.get_attribute(first, "aria-selected") == "true"
            assert page.inner_text(f"{trigger} span >> nth=0") == topic
            assert page.inner_text("#laws-count") == f"Rāda {in_topic} no {total}"
            page.keyboard.press("Escape")
            assert page.get_attribute(trigger, "aria-expanded") == "false"
            assert page.evaluate("document.activeElement.id") == "law-topic-trigger"
            browser.close()
    finally:
        server.shutdown()
