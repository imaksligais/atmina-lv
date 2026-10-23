"""«Atradumi» — content/analizes/*.md ar kind: atradums (plāns 2026-10-16)."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.render import analyses

VALID_BODY = (
    "Teksts ar [avots A](https://www.lsm.lv/a) un [avots B](https://titania.saeima.lv/b).\n\n"
    "## Ko mēs neapgalvojam\n\nNeapgalvojam pārkāpumu.\n"
)


def _write(
    d, name, *, kind="atradums", draft=False, body=VALID_BODY, politicians=None,
    date="2026-10-17", title=None, image=None, extra_fm="",
):
    fm = [f"title: {title or f'Vai {name}?'}", f"date: {date}", "description: Apraksts"]
    if image:
        fm.append(f"image: {image}")
    if kind:
        fm.append(f"kind: {kind}")
    if draft:
        fm.append("draft: true")
    if politicians:
        fm.append("politicians: [" + ", ".join(politicians) + "]")
    if extra_fm:
        fm.append(extra_fm.strip("\n"))
    (d / f"{name}.md").write_text("---\n" + "\n".join(fm) + "\n---\n\n" + body, encoding="utf-8")


@pytest.fixture
def fixture_db(tmp_path):
    from src.db import get_db, init_db
    from src.saeima.schema import init_saeima_bills, init_saeima_tables
    from tests.fixture_sql import load_render_fixture_sql

    db_path = str(tmp_path / "fixture.db")
    init_db(db_path)
    init_saeima_tables(db_path)
    init_saeima_bills(db_path)
    conn = get_db(db_path)
    for ddl in (
        "ALTER TABLE tracked_politicians ADD COLUMN x_handle TEXT",
        "ALTER TABLE documents ADD COLUMN is_paywall BOOLEAN DEFAULT FALSE",
        "ALTER TABLE documents ADD COLUMN summary TEXT",
    ):
        try:
            conn.execute(ddl)
        except Exception:  # noqa: BLE001 — kolonna jau ir
            pass
    conn.executescript(load_render_fixture_sql())
    conn.commit()
    conn.close()
    return db_path


def _render_site(tmp_path, monkeypatch, db_path, *, only):
    """Renderē fixture DB šaurajā `only` tvērumā; atgriež `<out>/atmina`.
    `analizes_dir` fixture jau novirzījis analyses.CONTENT_DIR uz tmp."""
    import src.render._orchestrator as orch
    from src.render import generate_public_site

    def _stub(dest, *a, **k):
        Path(dest).write_text("/* stub */", encoding="utf-8")

    for name in ("_download_chart_js", "_download_annotation_plugin", "_download_d3"):
        if hasattr(orch, name):
            monkeypatch.setattr(orch, name, _stub)
    out = tmp_path / "site"
    generate_public_site(db_path=db_path, output_dir=str(out), only=set(only))
    return out / "atmina"


@pytest.fixture
def analizes_dir(tmp_path, monkeypatch):
    d = tmp_path / "analizes"
    d.mkdir()
    monkeypatch.setattr(analyses, "CONTENT_DIR", tmp_path)
    return d


def test_kind_and_politicians_are_loaded(analizes_dir):
    _write(analizes_dir, "a1", politicians=["kulbergs"])
    _write(analizes_dir, "vecs", kind=None)
    by = {a["slug"]: a for a in analyses._load_analyses()}
    assert by["a1"]["kind"] == "atradums" and by["a1"]["politicians"] == ["kulbergs"]
    assert by["vecs"]["kind"] == "analysis" and by["vecs"]["politicians"] == []


def test_atradums_without_disclaimer_section_stops_render(analizes_dir):
    _write(analizes_dir, "bez", body="[a](https://a.lv/x) [b](https://b.lv/y)\n")
    with pytest.raises(ValueError, match="bez.md.*Ko mēs neapgalvojam"):
        analyses._load_analyses()


def test_atradums_with_one_source_stops_render(analizes_dir):
    _write(analizes_dir, "viens", body="[a](https://a.lv/x)\n\n## Ko mēs neapgalvojam\n\nx\n")
    with pytest.raises(ValueError, match="viens.md.*avot"):
        analyses._load_analyses()


def test_draft_atradums_is_not_validated_and_not_listed(analizes_dir):
    _write(analizes_dir, "melnraksts", draft=True, body="tikai sākums\n")
    assert analyses._load_analyses() == []


def test_bom_draft_atradums_is_not_listed(analizes_dir):
    # Windows redaktors saglabā UTF-8 ar BOM; `startswith("---")` tad krīt,
    # frontmatter pazūd un melnraksts aizietu live bez vārtiem.
    (analizes_dir / "bom.md").write_text(
        "---\ntitle: Vai bom?\nkind: atradums\ndraft: true\n---\n\ntikai sākums\n",
        encoding="utf-8-sig",
    )
    assert analyses._load_analyses() == []


def test_own_site_links_are_not_sources(analizes_dir):
    body = (
        "[viens](https://atmina.lv/politiki/a.html) un "
        "[divi](https://www.atmina.lv/analizes/b.html)\n\n## Ko mēs neapgalvojam\n\nx\n"
    )
    _write(analizes_dir, "pasu", body=body)
    with pytest.raises(ValueError, match="pasu.md.*avot"):
        analyses._load_analyses()


def test_unknown_kind_stops_render(analizes_dir):
    # Drukas kļūda `kind: atradum` nedrīkst klusi kļūt par tematisko analīzi.
    _write(analizes_dir, "typo", kind="atradum")
    with pytest.raises(ValueError, match="typo.md.*kind"):
        analyses._load_analyses()


def test_unparseable_frontmatter_stops_render(analizes_dir):
    # Nepēdiņots kols virsrakstā salauž YAML; parsētājs atgriež {} un melnraksts
    # citādi klusi publicētos kā parasta analīze, apejot vārtus.
    (analizes_dir / "kols.md").write_text(
        "---\ntitle: Vai a: b?\nkind: atradums\ndraft: true\n---\n\ntikai sākums\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="kols.md.*frontmatter"):
        analyses._load_analyses()


def test_image_and_code_block_links_are_not_sources(analizes_dir):
    body = (
        "[raksts](https://www.lsm.lv/a)\n\n![attēls](https://atmina.lv/img.png)\n\n"
        "```\n[piemērs](https://example.com/kods)\n```\n\n"
        "## Ko mēs neapgalvojam\n\nx\n"
    )
    _write(analizes_dir, "attels", body=body)
    with pytest.raises(ValueError, match="attels.md.*avot"):
        analyses._load_analyses()


def test_atradums_has_own_tab_card_and_label(tmp_path, monkeypatch, fixture_db, analizes_dir):
    _write(analizes_dir, "a1")
    _write(analizes_dir, "a0")  # tas pats datums → arī sākumlapas «Vairāk analīžu» ir atradums
    _write(analizes_dir, "vecs", kind=None, body="Vecā analīze.\n", date="2026-10-01")
    out = _render_site(
        tmp_path, monkeypatch, fixture_db, only={"analizes", "dashboard", "blog"}
    )
    listing = (out / "analizes.html").read_text(encoding="utf-8")
    panel = listing.split('id="anal-atradumi"', 1)[1].split('<div id="anal-', 1)[0]
    assert "analizes/a1.html" in panel and "analizes/vecs.html" not in panel
    tematic = listing.split('id="anal-tematic"', 1)[1].split('<div id="anal-', 1)[0]
    assert "analizes/vecs.html" in tematic and "analizes/a1.html" not in tematic
    page = (out / "analizes" / "a1.html").read_text(encoding="utf-8")
    assert "Atradums" in page and "analizes.html#atradumi" in page
    assert '<meta property="og:description" content="Apraksts">' in page
    home = (out / "index.html").read_text(encoding="utf-8")
    assert 'class="brief-featured-type">Atradums</span>' in home  # josla «Jaunākais»
    assert 'class="analysis-feat-kicker">Atradums</a>' in home
    assert "Lasīt atradumu" in home
    old = (out / "analizes" / "vecs.html").read_text(encoding="utf-8")
    assert "Tematiskā analīze" in old and "analizes.html#tematic" in old
    assert "Atradums" not in old
    # Pārskata lapas «jaunākā analīze» saite: jaunākais ir atradums → tā iezīme.
    brief = next((out / "blog").glob("*.html")).read_text(encoding="utf-8")
    related = brief.split('class="post-related-analysis"', 1)[1].split("</a>", 1)[0]
    assert "Jaunākais atradums" in related and "Lasīt atradumu" in related
    assert "tematiskā analīze" not in related


def test_atradumi_hash_opens_tab(tmp_path, monkeypatch, fixture_db, analizes_dir):
    # Saite analizes.html#atradumi tiks dalīta sociālajos tīklos — tai jāatver
    # pareizā cilne īstā pārlūkā, ne tikai jābūt minētai anv1.js.
    sync_api = pytest.importorskip("playwright.sync_api")
    _write(analizes_dir, "a1")
    out = _render_site(tmp_path, monkeypatch, fixture_db, only={"analizes", "dashboard"})
    url = (out / "analizes.html").as_uri() + "#atradumi"
    with sync_api.sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            page = browser.new_page()
            errors: list[str] = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(url)
            sync_api.expect(page.locator("#anal-atradumi")).to_be_visible(timeout=5000)
            sync_api.expect(page.locator("#tab-atradumi")).to_have_attribute(
                "aria-selected", "true", timeout=5000
            )
            assert page.locator("#anal-daily").is_hidden()
            assert errors == []
        finally:
            browser.close()


def _pick_politician_and_namesakes(db_path):
    """Kulbergs (id 10) fixture DB + ievietots vārdabrālis ar to pašu uzvārdu,
    lai uzvārds viens pats atbilstu diviem aktīviem politiķiem."""
    import sqlite3

    from src.render.politicians import _slugify

    conn = sqlite3.connect(db_path)
    name = conn.execute("SELECT name FROM tracked_politicians WHERE id = 10").fetchone()[0]
    conn.execute(
        "INSERT INTO tracked_politicians (name, name_forms, keywords, relationship_type) "
        "VALUES ('Pēteris Kulbergs', '[]', '[]', 'tracked')"
    )
    conn.commit()
    conn.close()
    return _slugify(name), [_slugify("Pēteris Kulbergs")]


def test_profile_lists_atradums_and_ambiguous_token_links_nobody(
    tmp_path, monkeypatch, fixture_db, analizes_dir, capsys
):
    slug, other_slugs = _pick_politician_and_namesakes(fixture_db)
    _write(analizes_dir, "a1", politicians=[slug])
    _write(analizes_dir, "a2", politicians=[slug.rsplit("-", 1)[-1]])  # kopīgs uzvārds
    out = _render_site(tmp_path, monkeypatch, fixture_db, only={"politiki"})
    prof = (out / "politiki" / f"{slug}.html").read_text(encoding="utf-8")
    assert "../analizes/a1.html" in prof and "../analizes/a2.html" not in prof
    assert "Vai a1?" in prof and "17.10.2026" in prof
    for other in other_slugs:
        namesake = (out / "politiki" / f"{other}.html").read_text(encoding="utf-8")
        assert "../analizes/a2.html" not in namesake
    assert "] a2:" in capsys.readouterr().err


def test_unmatched_politician_token_is_reported(
    tmp_path, monkeypatch, fixture_db, analizes_dir, capsys
):
    _write(analizes_dir, "a3", politicians=["nav-tada-politika"])
    _render_site(tmp_path, monkeypatch, fixture_db, only={"politiki"})
    err = capsys.readouterr().err
    assert "a3: politiķu vērtība 'nav-tada-politika' neatbilst nevienam" in err


def test_atradums_og_is_house_card_and_old_analysis_keeps_its_image(
    tmp_path, monkeypatch, fixture_db, analizes_dir
):
    """Atraduma og:image = mūsu sepijas kartīte assets/og/atradumi/<slug>.png
    (ne apgriezta shēma); vecā analīze bez `kind` paliek ar savu -og.jpg.
    Playwright aizstāts kā tests/test_og_cards.py — PNG apskate: atskaite 5b."""
    import re

    from src.render._common import og_render

    shots: dict[Path, str] = {}

    def _fake_shoot(todo):
        for out_path, html in todo:
            Path(out_path).write_bytes(b"png")
            shots[Path(out_path)] = html
            yield out_path

    monkeypatch.setattr(og_render, "_shoot", _fake_shoot)
    _write(analizes_dir, "a1", image="/images/analizes/a1.png")
    _write(analizes_dir, "vecs", kind=None, body="Vecā analīze.\n", date="2026-10-01",
           image="/images/analizes/vecs.png")
    out = _render_site(tmp_path, monkeypatch, fixture_db, only={"analizes", "dashboard"})

    def og(page):
        html = (out / "analizes" / f"{page}.html").read_text(encoding="utf-8")
        img = re.search(r'<meta property="og:image" content="([^"]+)"', html).group(1)
        assert f'<meta name="twitter:image" content="{img}">' in html
        return img

    # ?v=<hash>: X kešo kartīti pēc URL — jauns zīmējums = jauna adrese.
    assert re.fullmatch(r"https://atmina\.lv/assets/og/atradumi/a1\.png\?v=[0-9a-f]{8}", og("a1"))
    png = out / "assets" / "og" / "atradumi" / "a1.png"
    assert png.exists()
    card = shots[png]
    for text in ("Atradums", "Vai a1?", "2026. gada 17. oktobrī", "atmina.lv/analizes/a1",
                 "Fakti no publiskiem reģistriem — ar saitēm uz avotiem"):
        assert text in card, text
    assert og("vecs") == "https://atmina.lv/images/analizes/vecs-og.jpg"
    assert list(shots) == [png], "vecajai analīzei kartīti neveido"


OG_FACTS = """og:
  stamps:
    - {label: "2023 · 91 : 0", note: "pirmais likums"}
    - {label: "2026 · 69 : 6 : 8", note: "otrais likums"}
  gap: "3 gadi"
  stats:
    - {value: "21 × 50 000 €", note: "akcijas bez balsstiesībām"}
    - {value: "0 €", note: "apgrozījums"}
"""


def test_atradums_og_facts_draw_stamps_and_stats_and_change_the_url(
    tmp_path, monkeypatch, fixture_db, analizes_dir
):
    """Frontmatter `og:` → kartītē divi zīmogi, starplaiks un skaitļi kā
    pretrunu kartītē; cits saturs → cits ?v= (X citādi rāda veco kartīti)."""
    import re

    from src.render._common import og_render

    shots: dict[Path, str] = {}

    def _fake_shoot(todo):
        for out_path, html in todo:
            Path(out_path).write_bytes(b"png")
            shots[Path(out_path)] = html
            yield out_path

    monkeypatch.setattr(og_render, "_shoot", _fake_shoot)

    def render(extra):
        _write(analizes_dir, "a1", extra_fm=extra)
        out = _render_site(tmp_path, monkeypatch, fixture_db, only={"analizes"})
        html = (out / "analizes" / "a1.html").read_text(encoding="utf-8")
        return re.search(r'<meta property="og:image" content="([^"]+)"', html).group(1)

    plain = render("")
    rich = render(OG_FACTS)
    assert plain != rich
    card = shots[tmp_path / "site" / "atmina" / "assets" / "og" / "atradumi" / "a1.png"]
    for text in ("2023 · 91 : 0", "pirmais likums", "2026 · 69 : 6 : 8", "otrais likums",
                 "3 gadi", "21 × 50 000 €", "akcijas bez balsstiesībām", "0 €", "Vai a1?"):
        assert text in card, text


def test_atradums_og_facts_with_one_stamp_stops_render(analizes_dir):
    """Puse laika līnijas = salauzta kartīte; STOP, ne klusa atkāpe."""
    _write(analizes_dir, "a1", extra_fm='og:\n  stamps:\n    - {label: "2023", note: "x"}\n')
    with pytest.raises(ValueError, match="og"):
        analyses._load_analyses()
