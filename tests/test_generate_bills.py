"""Phase 1B-i — _fetch_bills, _fetch_bill_detail, _generate_bill_pages."""

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
def db_with_bills(tmp_path):
    """SQLite ar 2 Lp14 + 1 Lm14 + 1 P14 fixture bills, kuriem ir stages."""
    fd, path = tempfile.mkstemp(suffix=".db", dir=str(tmp_path))
    os.close(fd)
    init_db(path)
    init_saeima_tables(path)
    init_saeima_bills(path)
    # Bill 1: Lp14, full lifecycle (4 stages)
    bid1 = upsert_bill(path, "1315/Lp14", "Grozījumi Aizsardzības likumā", "Lp14",
                       institutional_submitter="Ministru kabinets", topic="Aizsardzība un drošība")
    append_bill_stage(path, bid1, "iesniegts", None, "2026-02-10")
    append_bill_stage(path, bid1, "1.lasījums", "pieņemts", "2026-03-05")
    append_bill_stage(path, bid1, "2.lasījums", "pieņemts", "2026-04-01")
    append_bill_stage(path, bid1, "3.lasījums", "pieņemts", "2026-04-23")
    # Bill 2: Lp14, only 2 stages (jaunāks)
    bid2 = upsert_bill(path, "1098/Lp14", "Iepirkumu vienkāršošana", "Lp14",
                       topic="Valsts pārvalde")
    append_bill_stage(path, bid2, "iesniegts", None, "2026-04-15")
    append_bill_stage(path, bid2, "1.lasījums", "noraidīts", "2026-04-25")
    # Bill 3: Lm14
    bid3 = upsert_bill(path, "952/Lm14", "Tiesneša iecelšana — Anna Bērziņa", "Lm14")
    append_bill_stage(path, bid3, "tiesneša_amats", "pieņemts", "2026-04-20")
    # Bill 4: P14 — paziņojums
    bid4 = upsert_bill(path, "127/P14", "Paziņojums par dronu uzbrukumiem", "P14")
    append_bill_stage(path, bid4, "iesniegts", None, "2026-04-22")
    append_bill_stage(path, bid4, "paziņojuma_balsojums", "pieņemts", "2026-04-25")
    yield path
    _safe_unlink(path)


def test_fetch_bills_shape(db_with_bills):
    from src.generate import _fetch_bills
    db = get_db(db_with_bills)
    bills = _fetch_bills(db)
    db.close()
    assert len(bills) == 4
    b1 = next(b for b in bills if b["document_nr"] == "1315/Lp14")
    assert b1["slug"] == "1315-lp14"
    assert b1["bill_type"] == "Lp14"
    assert b1["title"] == "Grozījumi Aizsardzības likumā"
    assert b1["topic"] == "Aizsardzība un drošība"
    assert b1["current_stage"] == "3.lasījums"
    assert b1["current_status"] == "pieņemts"
    assert b1["stage_count"] == 4
    assert b1["institutional_submitter"] == "Ministru kabinets"
    assert b1["submitter_count"] == 0  # nekāda junction rinda fixture'ā


def test_fetch_bills_sort_by_last_updated_desc(db_with_bills):
    from src.generate import _fetch_bills
    db = get_db(db_with_bills)
    bills = _fetch_bills(db)
    db.close()
    timestamps = [b["last_updated_at"] for b in bills]
    assert timestamps == sorted(timestamps, reverse=True), \
        f"Bills must be ordered newest-first; got {timestamps}"


def test_fetch_bill_detail_full_lp14(db_with_bills):
    from src.generate import _fetch_bills, _fetch_bill_detail
    db = get_db(db_with_bills)
    bills = _fetch_bills(db)
    bid = next(b["id"] for b in bills if b["document_nr"] == "1315/Lp14")
    detail = _fetch_bill_detail(db, bid)
    db.close()
    assert detail["document_nr"] == "1315/Lp14"
    assert detail["slug"] == "1315-lp14"
    assert len(detail["stages"]) == 4
    assert detail["stages"][0]["stage_name"] == "iesniegts"
    assert detail["stages"][-1]["stage_name"] == "3.lasījums"
    assert detail["stages"][-1]["stage_result"] == "pieņemts"
    assert detail["submitters_individual"] == []  # fixture'ā nav junction
    assert detail["amendment_authors"] == []
    assert detail["external_document_url"] is None


def test_fetch_bill_detail_handles_missing_summary(db_with_bills):
    from src.generate import _fetch_bills, _fetch_bill_detail
    db = get_db(db_with_bills)
    bills = _fetch_bills(db)
    bid = next(b["id"] for b in bills if b["document_nr"] == "1098/Lp14")
    detail = _fetch_bill_detail(db, bid)
    db.close()
    assert detail["summary"] is None
    assert len(detail["stages"]) == 2


def test_fetch_bill_detail_returns_none_for_missing_id(db_with_bills):
    from src.generate import _fetch_bill_detail
    db = get_db(db_with_bills)
    detail = _fetch_bill_detail(db, 99999)
    db.close()
    assert detail is None


def test_fetch_bill_with_individual_submitter(db_with_bills):
    from src.generate import _fetch_bills, _fetch_bill_detail, _slugify
    db = get_db(db_with_bills)
    # Add politician
    db.execute("""
        INSERT INTO tracked_politicians (name, party)
        VALUES (?, ?)
    """, ("Maija Armaņeva", "Progresīvie"))
    pid = db.execute("SELECT id FROM tracked_politicians WHERE name=?",
                     ("Maija Armaņeva",)).fetchone()["id"]
    # Find bill 1315/Lp14
    bid = db.execute("SELECT id FROM saeima_bills WHERE document_nr='1315/Lp14'").fetchone()["id"]
    # Link via junction
    db.execute("""
        INSERT INTO saeima_bill_politicians (bill_id, politician_id, role)
        VALUES (?, ?, ?)
    """, (bid, pid, "submitter"))
    db.commit()

    # Verify count surfaces
    bills = _fetch_bills(db)
    target = next(b for b in bills if b["id"] == bid)
    assert target["submitter_count"] == 1

    # Verify detail shape
    detail = _fetch_bill_detail(db, bid)
    db.close()
    assert len(detail["submitters_individual"]) == 1
    s = detail["submitters_individual"][0]
    assert s["name"] == "Maija Armaņeva"
    assert s["party"] == "Progresīvie"
    assert s["slug"] == _slugify("Maija Armaņeva")


def test_likumprojekts_template_renders_lp14(db_with_bills):
    from jinja2 import Environment, FileSystemLoader
    from src.generate import _fetch_bills, _fetch_bill_detail, _safe_url_filter

    db = get_db(db_with_bills)
    bid = next(b["id"] for b in _fetch_bills(db) if b["document_nr"] == "1315/Lp14")
    bill = _fetch_bill_detail(db, bid)
    db.close()

    env = Environment(loader=FileSystemLoader("templates"))
    env.filters["safe_url"] = _safe_url_filter
    env.filters["lv_date"] = lambda s: s  # naive pass-through testam
    template = env.get_template("likumprojekts.html.j2")
    html = template.render(bill=bill)

    assert "1315/Lp14" in html
    assert "Grozījumi Aizsardzības likumā" in html
    assert "14. Saeima · Likumprojekts" in html  # pagehead-kicker conditional
    assert "1.lasījums" in html
    assert "3.lasījums" in html
    assert "Ministru kabinets" in html
    assert 'class="bill-detail-timeline"' in html


def test_likumprojekts_template_renders_lm14(db_with_bills):
    from jinja2 import Environment, FileSystemLoader
    from src.generate import _fetch_bills, _fetch_bill_detail, _safe_url_filter

    db = get_db(db_with_bills)
    bid = next(b["id"] for b in _fetch_bills(db) if b["document_nr"] == "952/Lm14")
    bill = _fetch_bill_detail(db, bid)
    db.close()

    env = Environment(loader=FileSystemLoader("templates"))
    env.filters["safe_url"] = _safe_url_filter
    env.filters["lv_date"] = lambda s: s
    template = env.get_template("likumprojekts.html.j2")
    html = template.render(bill=bill)

    assert "14. Saeima · Lēmuma projekts" in html
    assert "tiesneša_amats" in html
    assert "1.lasījums" not in html  # Lm14 doesn't use lasījumi


def test_likumprojekts_template_renders_p14(db_with_bills):
    from jinja2 import Environment, FileSystemLoader
    from src.generate import _fetch_bills, _fetch_bill_detail, _safe_url_filter

    db = get_db(db_with_bills)
    bid = next(b["id"] for b in _fetch_bills(db) if b["document_nr"] == "127/P14")
    bill = _fetch_bill_detail(db, bid)
    db.close()

    env = Environment(loader=FileSystemLoader("templates"))
    env.filters["safe_url"] = _safe_url_filter
    env.filters["lv_date"] = lambda s: s
    template = env.get_template("likumprojekts.html.j2")
    html = template.render(bill=bill)

    assert "14. Saeima · Paziņojums" in html
    assert "iesniegts" in html
    assert "paziņojuma_balsojums" in html
    assert "1.lasījums" not in html


def test_likumprojekts_template_empty_submitters_state(db_with_bills):
    """Bill bez iesniedzējiem renders 'Iesniedzējs nav reģistrēts' empty state."""
    from jinja2 import Environment, FileSystemLoader
    from src.generate import _fetch_bills, _fetch_bill_detail, _safe_url_filter

    db = get_db(db_with_bills)
    # Bill 1098/Lp14 fixture has no institutional_submitter and no individual submitters
    bid = next(b["id"] for b in _fetch_bills(db) if b["document_nr"] == "1098/Lp14")
    bill = _fetch_bill_detail(db, bid)
    db.close()

    # Sanity check fixture state
    assert bill["institutional_submitter"] is None
    assert bill["submitters_individual"] == []

    env = Environment(loader=FileSystemLoader("templates"))
    env.filters["safe_url"] = _safe_url_filter
    env.filters["lv_date"] = lambda s: s
    template = env.get_template("likumprojekts.html.j2")
    html = template.render(bill=bill)

    assert "Iesniedzējs nav reģistrēts" in html


def test_likumprojekts_template_empty_stages_state(db_with_bills):
    """Bill bez stadijām renders 'Stadiju nav reģistrētas' empty state."""
    from jinja2 import Environment, FileSystemLoader
    from src.generate import _fetch_bills, _fetch_bill_detail, _safe_url_filter
    from src.saeima import upsert_bill

    # Add a brand-new bill with NO stages to the fixture
    db = get_db(db_with_bills)
    upsert_bill(db_with_bills, "999/Lp14", "Tests bez stadijām", "Lp14")
    bid = db.execute("SELECT id FROM saeima_bills WHERE document_nr=?", ("999/Lp14",)).fetchone()["id"]
    bill = _fetch_bill_detail(db, bid)
    db.close()

    # Sanity check fixture state
    assert bill["stages"] == []

    env = Environment(loader=FileSystemLoader("templates"))
    env.filters["safe_url"] = _safe_url_filter
    env.filters["lv_date"] = lambda s: s
    template = env.get_template("likumprojekts.html.j2")
    html = template.render(bill=bill)

    assert "Stadiju nav reģistrētas" in html


def test_fetch_votes_includes_bill_slug_when_linked(db_with_bills, tmp_path):
    """_fetch_votes patch — votes ar bill_id iegūst bill_slug; bez bill_id → None."""
    from src.generate import _fetch_bills, _fetch_votes
    db = get_db(db_with_bills)
    bills = _fetch_bills(db)
    bid = next(b["id"] for b in bills if b["document_nr"] == "1315/Lp14")
    db.execute("""
        INSERT INTO saeima_votes (motif, vote_date, result, document_nr, bill_id)
        VALUES (?, ?, ?, ?, ?)
    """, ("Test motif (1315/Lp14)", "2026-03-05", "Pieņemts", "1315/Lp14", bid))
    db.execute("""
        INSERT INTO saeima_votes (motif, vote_date, result, document_nr)
        VALUES (?, ?, ?, ?)
    """, ("Procedurāls", "2026-04-01", "Pieņemts", None))
    db.commit()
    db.close()

    db = get_db(db_with_bills)
    votes = _fetch_votes(db)
    db.close()
    linked = next(v for v in votes if v["motif"] == "Test motif (1315/Lp14)")
    proc = next(v for v in votes if v["motif"] == "Procedurāls")
    assert linked["bill_slug"] == "1315-lp14"
    assert proc["bill_slug"] is None


def test_bill_card_macro_renders_required_elements(db_with_bills):
    from jinja2 import Environment, FileSystemLoader
    from src.generate import _fetch_bills, _safe_url_filter

    db = get_db(db_with_bills)
    bills = _fetch_bills(db)
    db.close()
    bill = next(b for b in bills if b["document_nr"] == "1315/Lp14")

    env = Environment(loader=FileSystemLoader("templates"))
    env.filters["safe_url"] = _safe_url_filter
    template_str = """
    {% from "_bill_card.html.j2" import bill_card %}
    {{ bill_card(bill) }}
    """
    html = env.from_string(template_str).render(bill=bill)
    assert "1315/Lp14" in html
    assert "Grozījumi Aizsardzības likumā" in html
    assert 'class="bill-card"' in html
    assert 'href="likumprojekti/1315-lp14.html"' in html
    assert 'data-topic="Aizsardzība un drošība"' in html
    assert 'data-bill-type="Lp14"' in html
    assert 'data-status="pieņemts"' in html


def test_balsojumi_renders_bills_subtab(db_with_bills, tmp_path):
    """Balsojumi.html ietver 3. subtab + bills-list-tab div + #bills-list grid."""
    from jinja2 import Environment, FileSystemLoader
    from src.generate import _fetch_bills, _safe_url_filter, _safe_json_filter

    db = get_db(db_with_bills)
    bills = _fetch_bills(db)
    db.close()

    env = Environment(loader=FileSystemLoader("templates"))
    env.filters["safe_url"] = _safe_url_filter
    env.filters["lv_date"] = lambda s: s
    env.filters["safe_json"] = _safe_json_filter
    template = env.get_template("balsojumi.html.j2")
    html = template.render(
        votes=[], deputies=[], vote_topics=[], vote_sessions=[],
        metrics={"total": 0, "last_week": 0, "accepted_pct": 0},
        matrix_data=None, matrix_json=None,
        bills=bills, bill_topics=["Aizsardzība un drošība", "Valsts pārvalde"],
    )
    assert 'data-tab="bills-list"' in html
    assert 'id="bills-list-tab"' in html
    assert 'class="bill-card-grid"' in html
    assert "1315/Lp14" in html  # bill ir grid'ā
    assert "952/Lm14" in html


def test_vote_card_bill_link_rendered_client_side():
    """The vote-card → likumprojekti/<slug>.html internal link.

    Option-2 (2026-07-17) deleted the SSR vote cards; the vote list is now
    rendered entirely client-side by assets/bmv1.js::archiveBuildCard, which
    emits the bill link from the compact matrix JSON's `bsl` (bill slug) field.
    The template no longer carries this link, so coverage moves to bmv1.js.
    """
    from pathlib import Path

    js = Path("assets/bmv1.js").read_text(encoding="utf-8")
    # archiveBuildCard builds the internal bill link when a vote carries a slug.
    assert '"likumprojekti/' in js or "'likumprojekti/" in js


def test_generate_bill_pages_emits_correct_count(db_with_bills, tmp_path):
    from jinja2 import Environment, FileSystemLoader
    from src.generate import _generate_bill_pages, _safe_url_filter, _safe_json_filter

    env = Environment(loader=FileSystemLoader("templates"))
    env.filters["safe_url"] = _safe_url_filter
    env.filters["lv_date"] = lambda s: s
    env.filters["safe_json"] = _safe_json_filter
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    db = get_db(db_with_bills)
    _generate_bill_pages(db, env, output_dir)
    db.close()

    bills_dir = output_dir / "likumprojekti"
    files = sorted(p.name for p in bills_dir.iterdir())
    # Fixture: 4 bills (1315/Lp14, 1098/Lp14, 952/Lm14, 127/P14)
    assert files == ["1098-lp14.html", "127-p14.html", "1315-lp14.html", "952-lm14.html"]


def test_generate_bill_pages_uses_slug_filename(db_with_bills, tmp_path):
    from jinja2 import Environment, FileSystemLoader
    from src.generate import _generate_bill_pages, _safe_url_filter, _safe_json_filter

    env = Environment(loader=FileSystemLoader("templates"))
    env.filters["safe_url"] = _safe_url_filter
    env.filters["lv_date"] = lambda s: s
    env.filters["safe_json"] = _safe_json_filter
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    db = get_db(db_with_bills)
    _generate_bill_pages(db, env, output_dir)
    db.close()

    target = output_dir / "likumprojekti" / "1315-lp14.html"
    assert target.exists()
    content = target.read_text(encoding="utf-8")
    assert "1315/Lp14" in content
    assert "Grozījumi Aizsardzības likumā" in content


def test_sitemap_includes_bills_urls(db_with_bills, tmp_path):
    from src.generate import _fetch_bills, _generate_sitemap

    db = get_db(db_with_bills)
    bills = _fetch_bills(db)
    db.close()

    output_dir = tmp_path / "out"
    output_dir.mkdir()

    _generate_sitemap(
        atmina_dir=output_dir,
        politicians=[],
        parties=[],
        blog_posts=[],
        analyses=[],
        bills=bills,
    )

    sitemap = (output_dir / "sitemap.xml").read_text(encoding="utf-8")
    assert "likumprojekti/1315-lp14.html" in sitemap
    assert "likumprojekti/952-lm14.html" in sitemap
    assert "likumprojekti/127-p14.html" in sitemap
