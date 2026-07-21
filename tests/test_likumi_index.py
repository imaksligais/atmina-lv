"""Phase 1C — /likumi.html base-law index page."""
import os
import sqlite3
import tempfile
from pathlib import Path

import pytest

from src.db import init_db, get_db
from src.saeima import init_saeima_tables, init_saeima_bills, load_laws_index
from src.generate import _fetch_law_index_page, generate_public_site


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

    Renders the likumi + balsojumi domains against the seeded one-bill fixture DB
    (not the live, gitignored data/atmina.db) into a temp output dir, so this runs
    in CI. chdir to repo root so wiki/laws/ (the base-law source) resolves; network
    asset downloads are stubbed.
    """
    import src.render._orchestrator as orch

    monkeypatch.chdir(Path(__file__).resolve().parent.parent)
    monkeypatch.setattr(orch, "_download_chart_js", lambda *a, **k: None)
    monkeypatch.setattr(orch, "_download_annotation_plugin", lambda *a, **k: None)

    out = tmp_path / "out"
    generate_public_site(db_path=db_with_one_bill, output_dir=str(out), only={"likumi", "balsojumi"})
    site = out / "atmina"
    assert (site / "likumi.html").exists(), "/likumi.html was not generated"
    content = (site / "likumi.html").read_text(encoding="utf-8")
    assert "Pamatlikumi" in content
    assert 'href="likumi/saeimas-velesanu-likums.html"' in content
    # Footer link from /balsojumi.html
    balsojumi = (site / "balsojumi.html").read_text(encoding="utf-8")
    assert 'href="likumi.html"' in balsojumi
    assert "Visi pamatlikumi" in balsojumi
