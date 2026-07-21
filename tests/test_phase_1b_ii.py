"""Phase 1B-ii — base_law_slug backfill, wiki/laws auto-render, profile section."""

import os
import sqlite3
import tempfile
from pathlib import Path

import pytest

from src.db import init_db, get_db
from src.saeima import init_saeima_bills, init_saeima_tables, upsert_bill, append_bill_stage


def _safe_unlink(path):
    try:
        os.unlink(path)
    except PermissionError:
        pass


@pytest.fixture
def db_with_bills_for_backfill(tmp_path):
    """SQLite ar 3 bills, kuriem visiem base_law_slug=NULL."""
    fd, path = tempfile.mkstemp(suffix=".db", dir=str(tmp_path))
    os.close(fd)
    init_db(path)
    init_saeima_tables(path)
    init_saeima_bills(path)
    # Bill 1: title satur "Imigrācijas likumā" — vajadzētu match
    upsert_bill(path, "1315/Lp14", "Grozījumi Imigrācijas likumā", "Lp14")
    # Bill 2: title satur "Farmācijas likumā"
    upsert_bill(path, "1098/Lp14", "Grozījumi Farmācijas likumā", "Lp14")
    # Bill 3: nav atbilstoša wiki/laws — paliks NULL
    upsert_bill(path, "127/P14", "Paziņojums par dronu uzbrukumiem", "P14")
    # Ensure all base_law_slug values are NULL (upsert_bill passes None → no auto-resolve)
    db = get_db(path)
    db.execute("UPDATE saeima_bills SET base_law_slug = NULL")
    db.commit()
    db.close()
    yield path
    _safe_unlink(path)


@pytest.fixture
def wiki_with_laws(tmp_path):
    """Synthetic wiki/laws/ with 2 laws — Imigrācijas + Farmācijas."""
    wiki_dir = tmp_path / "wiki"
    laws_dir = wiki_dir / "laws"
    laws_dir.mkdir(parents=True)
    (laws_dir / "imigracijas-likums.md").write_text(
        "# Imigrācijas likums\n\nApraksts.\n", encoding="utf-8"
    )
    (laws_dir / "farmacijas-likums.md").write_text(
        "# Farmācijas likums\n\nApraksts.\n", encoding="utf-8"
    )
    # likumi.md indekss should also exist (gets skipped)
    (laws_dir / "likumi.md").write_text("# Indekss\n", encoding="utf-8")
    yield wiki_dir


def test_backfill_base_law_slug_matches_known_law(db_with_bills_for_backfill, wiki_with_laws):
    from scripts.backfill_base_law_slug import backfill_base_law_slug

    db = get_db(db_with_bills_for_backfill)
    null_count = db.execute("SELECT COUNT(*) FROM saeima_bills WHERE base_law_slug IS NULL").fetchone()[0]
    db.close()
    assert null_count == 3

    result = backfill_base_law_slug(db_with_bills_for_backfill, wiki_dir=wiki_with_laws)

    db = get_db(db_with_bills_for_backfill)
    rows = {r["document_nr"]: r["base_law_slug"] for r in db.execute("SELECT document_nr, base_law_slug FROM saeima_bills").fetchall()}
    db.close()

    assert rows["1315/Lp14"] == "imigracijas-likums"
    assert rows["1098/Lp14"] == "farmacijas-likums"
    assert rows["127/P14"] is None
    assert result["matched"] == 2
    assert result["unmatched"] == 1
    # 2 of 3 bills got base_law_slug populated → 66.7%
    assert result["coverage_pct"] > 60.0


def test_backfill_base_law_slug_idempotent(db_with_bills_for_backfill, wiki_with_laws):
    from scripts.backfill_base_law_slug import backfill_base_law_slug

    result1 = backfill_base_law_slug(db_with_bills_for_backfill, wiki_dir=wiki_with_laws)
    result2 = backfill_base_law_slug(db_with_bills_for_backfill, wiki_dir=wiki_with_laws)

    assert result1["matched"] == 2
    assert result2["matched"] == 0  # nekas vairs nav NULL match-able
    assert result2["unmatched"] == 1  # 127/P14 paliek NULL
    assert result1["coverage_pct"] == result2["coverage_pct"]  # global stable


def test_upsert_bill_resolves_base_law_slug_for_new_bill(tmp_path, wiki_with_laws):
    """upsert_bill auto-populates base_law_slug when title matches a known law."""
    fd, db_path = tempfile.mkstemp(suffix=".db", dir=str(tmp_path))
    os.close(fd)
    from src.db import init_db
    init_db(db_path)
    init_saeima_tables(db_path)
    init_saeima_bills(db_path)

    bid = upsert_bill(db_path, "9999/Lp14", "Grozījumi Imigrācijas likumā par sezonāliem darbiniekiem", "Lp14",
                      wiki_dir=wiki_with_laws)

    db = get_db(db_path)
    slug = db.execute("SELECT base_law_slug FROM saeima_bills WHERE id=?", (bid,)).fetchone()[0]
    db.close()
    _safe_unlink(db_path)

    assert slug == "imigracijas-likums"


def test_upsert_bill_preserves_existing_base_law_slug_on_re_call(tmp_path, wiki_with_laws):
    """Re-calling upsert_bill with different title should NOT overwrite existing base_law_slug."""
    fd, db_path = tempfile.mkstemp(suffix=".db", dir=str(tmp_path))
    os.close(fd)
    from src.db import init_db
    init_db(db_path)
    init_saeima_tables(db_path)
    init_saeima_bills(db_path)

    bid1 = upsert_bill(db_path, "9999/Lp14", "Grozījumi Imigrācijas likumā", "Lp14", wiki_dir=wiki_with_laws)
    db = get_db(db_path)
    slug_after_first = db.execute("SELECT base_law_slug FROM saeima_bills WHERE id=?", (bid1,)).fetchone()[0]
    db.close()
    assert slug_after_first == "imigracijas-likums"

    # Re-call with title that would resolve differently
    bid2 = upsert_bill(db_path, "9999/Lp14", "Grozījumi Farmācijas likumā", "Lp14", wiki_dir=wiki_with_laws)
    assert bid2 == bid1

    db = get_db(db_path)
    slug_after_second = db.execute("SELECT base_law_slug FROM saeima_bills WHERE id=?", (bid1,)).fetchone()[0]
    db.close()
    _safe_unlink(db_path)

    # Should still be the first match
    assert slug_after_second == "imigracijas-likums"


def test_render_law_bills_block_with_bills(tmp_path, db_with_bills_for_backfill, wiki_with_laws):
    """Likumam ar bills atbilstošu base_law_slug → marker bloks ar tabulas rindām."""
    from src.wiki import _render_law_bills_block
    from scripts.backfill_base_law_slug import backfill_base_law_slug

    # Backfill so bills get base_law_slug populated
    backfill_base_law_slug(db_with_bills_for_backfill, wiki_dir=wiki_with_laws)

    md_path = wiki_with_laws / "laws" / "imigracijas-likums.md"
    # Pre-condition: file already exists from fixture, has H1 and content but no BILLS-SYNC marker
    initial_content = md_path.read_text(encoding="utf-8")
    assert "<!-- BILLS-SYNC-AUTO -->" not in initial_content

    db = get_db(db_with_bills_for_backfill)
    changed = _render_law_bills_block(slug="imigracijas-likums", db=db, md_path=md_path)
    db.close()

    assert changed is True
    content = md_path.read_text(encoding="utf-8")
    assert "<!-- BILLS-SYNC-AUTO -->" in content
    assert "<!-- /BILLS-SYNC-AUTO -->" in content
    assert "Aktuālie likumprojekti šajā likumā" in content
    assert "1315/Lp14" in content
    assert "Grozījumi Imigrācijas likumā" in content


def test_render_law_bills_block_empty_state(tmp_path, db_with_bills_for_backfill, wiki_with_laws):
    """Likumam BEZ saistītu bills → marker bloks ar 'nav aktīvu' tekstu."""
    from src.wiki import _render_law_bills_block

    # Don't run backfill — bills have no base_law_slug, so query returns 0 rows for any slug
    md_path = wiki_with_laws / "laws" / "farmacijas-likums.md"

    db = get_db(db_with_bills_for_backfill)
    changed = _render_law_bills_block(slug="farmacijas-likums", db=db, md_path=md_path)
    db.close()

    assert changed is True
    content = md_path.read_text(encoding="utf-8")
    assert "nav aktīvu likumprojektu Saeimā" in content
    assert "<!-- BILLS-SYNC-AUTO -->" in content


def test_render_law_bills_block_idempotent(tmp_path, db_with_bills_for_backfill, wiki_with_laws):
    """Re-call ar tādu pašu state nemaina failu (returns False)."""
    from src.wiki import _render_law_bills_block
    from scripts.backfill_base_law_slug import backfill_base_law_slug

    backfill_base_law_slug(db_with_bills_for_backfill, wiki_dir=wiki_with_laws)
    md_path = wiki_with_laws / "laws" / "imigracijas-likums.md"

    db = get_db(db_with_bills_for_backfill)
    changed_first = _render_law_bills_block("imigracijas-likums", db, md_path)
    content_after_first = md_path.read_text(encoding="utf-8")
    changed_second = _render_law_bills_block("imigracijas-likums", db, md_path)
    content_after_second = md_path.read_text(encoding="utf-8")
    db.close()

    assert changed_first is True
    assert changed_second is False
    assert content_after_first == content_after_second


def test_render_law_bills_block_appends_when_marker_missing(tmp_path):
    """Fails bez BILLS-SYNC-AUTO marķiera → bloks pievieno faila beigās."""
    from src.wiki import _render_law_bills_block

    md_path = tmp_path / "test-likums.md"
    md_path.write_text("# Test likums\n\nDaži apraksti.\n", encoding="utf-8")

    fd, db_path = tempfile.mkstemp(suffix=".db", dir=str(tmp_path))
    os.close(fd)
    init_db(db_path)
    init_saeima_tables(db_path)
    init_saeima_bills(db_path)
    db = get_db(db_path)

    _render_law_bills_block("test-likums", db, md_path)
    db.close()
    _safe_unlink(db_path)

    content = md_path.read_text(encoding="utf-8")
    assert "Daži apraksti." in content
    assert "<!-- BILLS-SYNC-AUTO -->" in content
    assert content.index("Daži apraksti.") < content.index("<!-- BILLS-SYNC-AUTO -->")


# ---------------------------------------------------------------------------
# Task 4: _fetch_law_pages, likums.html.j2, _generate_law_pages
# ---------------------------------------------------------------------------

def test_fetch_law_pages_shape(tmp_path):
    """_fetch_law_pages atgriež struktūru ar slug, title, body_html, likumi_lv_url, bills."""
    from src.generate import _fetch_law_pages

    laws_dir = tmp_path / "wiki" / "laws"
    laws_dir.mkdir(parents=True)
    (laws_dir / "test-likums.md").write_text(
        "# Test likums\n\n"
        "**Pieņemts:** 2020-01-01\n"
        "**Likumi.lv:** https://likumi.lv/ta/id/12345-test-likums\n\n"
        "## Mērķis\n\nTestēšanas mērķim.\n",
        encoding="utf-8"
    )

    fd, db_path = tempfile.mkstemp(suffix=".db", dir=str(tmp_path))
    os.close(fd)
    init_db(db_path)
    init_saeima_tables(db_path)
    init_saeima_bills(db_path)
    db = get_db(db_path)

    pages = _fetch_law_pages(db, laws_dir=laws_dir)
    db.close()
    _safe_unlink(db_path)

    assert len(pages) == 1
    p = pages[0]
    assert p["slug"] == "test-likums"
    assert p["title"] == "Test likums"
    assert p["likumi_lv_url"] == "https://likumi.lv/ta/id/12345-test-likums"
    assert "Testēšanas mērķim" in p["body_html"]
    assert p["bills_count"] == 0
    # H1 should NOT be in body_html (it's in pagehead via title)
    assert "<h1>Test likums</h1>" not in p["body_html"]
    # Metadata lines should NOT be in body_html
    assert "Likumi.lv:" not in p["body_html"]
    assert "Pieņemts:" not in p["body_html"]


def test_likums_template_renders(tmp_path, db_with_bills_for_backfill):
    from jinja2 import Environment, FileSystemLoader
    from src.generate import _fetch_law_pages, _safe_url_filter
    from scripts.backfill_base_law_slug import backfill_base_law_slug

    laws_dir = tmp_path / "wiki" / "laws"
    laws_dir.mkdir(parents=True)
    (laws_dir / "imigracijas-likums.md").write_text(
        "# Imigrācijas likums\n\n"
        "**Likumi.lv:** https://likumi.lv/ta/id/68522\n\n"
        "## Mērķis\n\nLikuma apraksts.\n",
        encoding="utf-8"
    )
    backfill_base_law_slug(db_with_bills_for_backfill, wiki_dir=tmp_path / "wiki")

    db = get_db(db_with_bills_for_backfill)
    pages = _fetch_law_pages(db, laws_dir=laws_dir)
    db.close()
    law = pages[0]

    env = Environment(loader=FileSystemLoader("templates"))
    env.filters["safe_url"] = _safe_url_filter
    template = env.get_template("likums.html.j2")
    html = template.render(law=law)

    assert "Imigrācijas likums" in html
    assert "likumi.lv" in html
    assert 'href="https://likumi.lv/ta/id/68522"' in html
    assert "Likuma apraksts" in html
    assert 'class="pagehead-section"' in html


def test_generate_law_pages_emits_files(tmp_path, db_with_bills_for_backfill):
    from jinja2 import Environment, FileSystemLoader
    from src.generate import _generate_law_pages, _safe_url_filter

    laws_dir = tmp_path / "wiki" / "laws"
    laws_dir.mkdir(parents=True)
    (laws_dir / "test1.md").write_text("# Test 1\n\nA.\n", encoding="utf-8")
    (laws_dir / "test2.md").write_text("# Test 2\n\nB.\n", encoding="utf-8")
    (laws_dir / "likumi.md").write_text("# Indekss\n", encoding="utf-8")  # SKIP

    output_dir = tmp_path / "out"
    output_dir.mkdir()

    env = Environment(loader=FileSystemLoader("templates"))
    env.filters["safe_url"] = _safe_url_filter

    db = get_db(db_with_bills_for_backfill)
    count = _generate_law_pages(db, env, output_dir, laws_dir=laws_dir)
    db.close()

    assert count == 2
    assert (output_dir / "likumi" / "test1.html").exists()
    assert (output_dir / "likumi" / "test2.html").exists()
    assert not (output_dir / "likumi" / "likumi.html").exists()


# ---------------------------------------------------------------------------
# Task 5: _fetch_bill_detail base_law fields + template render
# ---------------------------------------------------------------------------

def test_fetch_bill_detail_returns_base_law_fields(db_with_bills_for_backfill, wiki_with_laws):
    """_fetch_bill_detail iekļauj base_law_slug + base_law_title."""
    from src.generate import _fetch_bills, _fetch_bill_detail
    from scripts.backfill_base_law_slug import backfill_base_law_slug

    backfill_base_law_slug(db_with_bills_for_backfill, wiki_dir=wiki_with_laws)

    db = get_db(db_with_bills_for_backfill)
    bills = _fetch_bills(db)
    bid = next(b["id"] for b in bills if b["document_nr"] == "1315/Lp14")
    detail = _fetch_bill_detail(db, bid, wiki_dir=wiki_with_laws)
    db.close()

    assert detail["base_law_slug"] == "imigracijas-likums"
    assert detail["base_law_title"]


def test_likumprojekts_template_renders_base_law_section(db_with_bills_for_backfill, wiki_with_laws):
    from jinja2 import Environment, FileSystemLoader
    from src.generate import _fetch_bills, _fetch_bill_detail, _safe_url_filter
    from scripts.backfill_base_law_slug import backfill_base_law_slug

    backfill_base_law_slug(db_with_bills_for_backfill, wiki_dir=wiki_with_laws)

    db = get_db(db_with_bills_for_backfill)
    bid = next(b["id"] for b in _fetch_bills(db) if b["document_nr"] == "1315/Lp14")
    bill = _fetch_bill_detail(db, bid, wiki_dir=wiki_with_laws)
    db.close()

    env = Environment(loader=FileSystemLoader("templates"))
    env.filters["safe_url"] = _safe_url_filter
    env.filters["lv_date"] = lambda s: s
    template = env.get_template("likumprojekts.html.j2")
    html = template.render(bill=bill)

    assert "Saistītais bāzes likums" in html
    assert 'href="../likumi/imigracijas-likums.html"' in html


def test_likumprojekts_template_no_base_law_when_null(db_with_bills_for_backfill):
    from jinja2 import Environment, FileSystemLoader
    from src.generate import _fetch_bills, _fetch_bill_detail, _safe_url_filter

    db = get_db(db_with_bills_for_backfill)
    # Bill 127/P14 has no base_law (paziņojums) — stays NULL
    bid = next(b["id"] for b in _fetch_bills(db) if b["document_nr"] == "127/P14")
    bill = _fetch_bill_detail(db, bid)
    db.close()

    env = Environment(loader=FileSystemLoader("templates"))
    env.filters["safe_url"] = _safe_url_filter
    env.filters["lv_date"] = lambda s: s
    template = env.get_template("likumprojekts.html.j2")
    html = template.render(bill=bill)

    assert "Saistītais bāzes likums" not in html


# ---------------------------------------------------------------------------
# Task 6: politiķa profila "Likumprojekti" sekcija (conditional render)
# ---------------------------------------------------------------------------

def test_politician_profile_no_likumprojekti_section_when_empty(tmp_path):
    """Junction empty for politiķa → sekcija + butons absent no DOM."""
    from jinja2 import Environment, FileSystemLoader
    from src.generate import _fetch_politician_detail, _safe_url_filter, _safe_json_filter

    fd, db_path = tempfile.mkstemp(suffix=".db", dir=str(tmp_path))
    os.close(fd)
    init_db(db_path)
    init_saeima_tables(db_path)
    init_saeima_bills(db_path)
    db = get_db(db_path)
    # x_handle column is live in production but predates init_db schema
    try:
        db.execute("ALTER TABLE tracked_politicians ADD COLUMN x_handle TEXT")
    except Exception:
        pass
    db.execute("INSERT INTO tracked_politicians (name, party) VALUES (?, ?)", ("Ieva Tests", "JV"))
    pid = db.execute("SELECT id FROM tracked_politicians WHERE name='Ieva Tests'").fetchone()["id"]
    db.commit()

    detail = _fetch_politician_detail(db, pid)
    db.close()
    _safe_unlink(db_path)
    assert detail["bills_involved"] == []

    env = Environment(loader=FileSystemLoader("templates"))
    env.filters["safe_url"] = _safe_url_filter
    env.filters["safe_json"] = _safe_json_filter
    env.filters["lv_date"] = lambda s: s
    template = env.get_template("politician.html.j2")
    html = template.render(
        politician={"id": pid, "name": "Ieva Tests", "slug": "ieva-tests", "party": "JV", "x_handle": None, "role": None},
        tab_set=detail["tab_set"],
        saites_data=detail["saites_data"],
        bills_involved=detail["bills_involved"],
        timeline=[], positions=[], contradictions=[], votes=[], tensions=[],
        x_posts=[], news=[], commentary_about=[], external_profiles=[], syntheses=[],
        wiki_profile=None, has_photo=False, party_meta=None, claim_topics=[],
    )
    assert 'id="tab-likumprojekti"' not in html
    assert 'data-tab="likumprojekti"' not in html


def test_politician_profile_likumprojekti_section_when_data_present(tmp_path, db_with_bills_for_backfill):
    from jinja2 import Environment, FileSystemLoader
    from src.generate import _fetch_politician_detail, _safe_url_filter, _safe_json_filter

    db = get_db(db_with_bills_for_backfill)
    # x_handle column is live in production but predates init_db schema
    try:
        db.execute("ALTER TABLE tracked_politicians ADD COLUMN x_handle TEXT")
    except Exception:
        pass
    db.execute("INSERT INTO tracked_politicians (name, party) VALUES (?, ?)", ("Maija Armaņeva", "Progresīvie"))
    pid = db.execute("SELECT id FROM tracked_politicians WHERE name=?", ("Maija Armaņeva",)).fetchone()["id"]
    bid = db.execute("SELECT id FROM saeima_bills WHERE document_nr='1315/Lp14'").fetchone()["id"]
    db.execute("INSERT INTO saeima_bill_politicians (bill_id, politician_id, role) VALUES (?, ?, 'submitter')", (bid, pid))
    db.commit()

    # Force profile_kind='deputy' so the new Saeimā tab (which now hosts
    # the Likumprojekti section after the role-aware tab refactor) is
    # included. The test fixture creates a synthetic politician with no
    # votes and no role, which would otherwise classify as 'politician'
    # and hide the saeima tab — but the assertion is about bill data
    # plumbing, not classification.
    detail = _fetch_politician_detail(db, pid, profile_kind="deputy")
    db.close()
    assert len(detail["bills_involved"]) == 1
    assert detail["bills_involved"][0]["document_nr"] == "1315/Lp14"

    env = Environment(loader=FileSystemLoader("templates"))
    env.filters["safe_url"] = _safe_url_filter
    env.filters["safe_json"] = _safe_json_filter
    env.filters["lv_date"] = lambda s: s
    template = env.get_template("politician.html.j2")
    html = template.render(
        politician={"id": pid, "name": "Maija Armaņeva", "slug": "maija-armaneva", "party": "Progresīvie", "x_handle": None, "role": None, "profile_kind": "deputy"},
        bills_involved=detail["bills_involved"],
        tab_set=detail["tab_set"],
        saites_data=detail["saites_data"],
        commentary_by=detail["commentary_by"],
        timeline=[], positions=[], contradictions=[], votes=[], tensions=[],
        x_posts=[], news=[], commentary_about=[], external_profiles=[], syntheses=[],
        wiki_profile=None, has_photo=False, party_meta=None, claim_topics=[],
    )
    # Bills are now hosted inside tab-saeima after the role-aware refactor
    # (was tab-likumprojekti pre-2026-05-01). Assert the bill data still
    # reaches the page.
    assert 'id="tab-saeima"' in html
    assert 'data-tab="saeima"' in html
    assert "1315/Lp14" in html
    # Bill card hrefs on a profile (depth 1, assets_prefix="../") must be
    # prefixed so they resolve to ../likumprojekti/... not politiki/likumprojekti/...
    assert 'href="../likumprojekti/1315-lp14.html"' in html
    assert 'href="likumprojekti/1315-lp14.html"' not in html
    # "Balsojumu matrica" link must also carry the depth prefix
    assert 'href="politiki/balsojumi.html"' not in html
