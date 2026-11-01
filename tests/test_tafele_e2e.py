"""Izpētes tāfele — lietotāja skats (Playwright). Dati: izdomāts fixture."""
from __future__ import annotations

import shutil
import functools
import http.server
import threading
from pathlib import Path

import pytest
from playwright import sync_api

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "tafele_min.yaml"


@pytest.fixture(scope="module")
def page_path(tmp_path_factory):
    from scripts.preview_tafele import build_preview
    out = tmp_path_factory.mktemp("tf")
    arts = out / "_articles"
    arts.mkdir()
    (arts / "testa-raksts.md").write_text(
        "---\ntitle: T\ndate: 2026-01-01\ndraft: true\n---\n\n## A\nTeksts\n## B\nTeksts\n## C\nTeksts\n",
        encoding="utf-8")
    return build_preview(FIX, out, articles_dir=arts, extra_persons={"anna"})


def test_no_js_ledger_is_complete(page_path):
    with sync_api.sync_playwright() as pw:
        b = pw.chromium.launch()
        ctx = b.new_context(java_script_enabled=False)
        pg = ctx.new_page()
        pg.goto(page_path.as_uri())
        assert pg.locator(".tf-ledger .tf-link").count() == 4
        assert pg.locator(".tf-link[data-link='l1'] a.tf-src").get_attribute("href") == "https://example.org/ur"
        assert "nav pierādīts" in pg.locator(".tf-link[data-link='l4']").inner_text()
        assert pg.locator("main").count() == 1
        assert pg.locator(".tf-zone-note").inner_text() == "Reģistrētā adrese."
        assert pg.locator(".tf-facts .tf-art").get_attribute("href") == "testa-raksts.html#a"
        assert pg.locator(".tf-book").is_visible()
        b.close()


def test_page_has_no_inline_script(page_path):
    html = page_path.read_text(encoding="utf-8")
    assert "<script>" not in html and " onclick=" not in html


@pytest.fixture(scope="module")
def page_url(page_path):
    from scripts.preview_tafele import _CSPHandler, _csp
    handler = functools.partial(_CSPHandler, directory=str(page_path.parent.parent))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}/analizes/{page_path.name}"
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


def test_preview_serves_production_csp(page_url):
    from scripts.preview_tafele import _csp
    with sync_api.sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        violations = []
        page.on("console", lambda msg: violations.append(msg.text) if
                "content security policy" in msg.text.lower() else None)
        response = page.goto(page_url)
        assert response.headers["content-security-policy"] == _csp()
        assert page.locator(".tf-link").count() == 4
        # Vienīgais ārējais skripts ir vietnes kopīgā analītika (CSP allowlist).
        external = page.locator("script[src^='https://']").evaluate_all("els => els.map(e => e.src)")
        assert all(src.startswith("https://cloud.umami.is/") for src in external), external
        assert violations == []
        browser.close()


def test_preview_renders_referenced_draft_article(page_path):
    with sync_api.sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(page_path.as_uri())
        page.locator(".tf-facts .tf-art").click()
        assert page.url.endswith("testa-raksts.html#a")
        assert page.locator("h2#a").inner_text() == "A"
        browser.close()


def test_loader_preview_options_preserve_default_gate(tmp_path):
    from src.render.analyses import _load_analyses
    for name, draft in [("draft", True), ("published", False), ("unrelated", False)]:
        (tmp_path / f"{name}.md").write_text(
            f"---\ntitle: T\ndraft: {str(draft).lower()}\n---\nTeksts", encoding="utf-8")
    assert {a["slug"] for a in _load_analyses(articles_dir=tmp_path)} == {"published", "unrelated"}
    assert {a["slug"] for a in _load_analyses(
        articles_dir=tmp_path, include_drafts=True, slugs={"draft", "published"}
    )} == {"draft", "published"}


def test_preview_refuses_production_output():
    from scripts.preview_tafele import build_preview
    from src.tafele.model import BoardError
    with pytest.raises(BoardError, match="output"):
        build_preview(FIX, ROOT / "output", extra_persons={"anna"})


def _open(pw, page_path, width=1440, hash_=""):
    b = pw.chromium.launch()
    pg = b.new_page(viewport={"width": width, "height": 900})
    pg.set_default_timeout(2500)
    pg.goto(page_path.as_uri() + hash_)
    return b, pg


def test_click_person_shows_only_her_threads_and_source(page_path):
    with sync_api.sync_playwright() as pw:
        b, pg = _open(pw, page_path)
        assert pg.locator(".tf-threads path").count() == 0
        pg.click(".tf-pin[data-entity='anna']")
        on = pg.locator(".tf-threads path.is-on")
        assert sorted(on.evaluate_all("ps => ps.map(p => p.dataset.link)")) == ["l1", "l2", "l4"]
        assert pg.locator("#tf-panel a.tf-src").first.get_attribute("href").startswith("https://")
        assert "e=anna" in pg.url
        b.close()


@pytest.mark.parametrize("width,height", [(1440, 900), (1280, 800)])
def test_laptop_selection_panel_stays_beside_board_in_view(page_path, width, height):
    with sync_api.sync_playwright() as pw:
        b, pg = _open(pw, page_path, width=width)
        pg.set_viewport_size({"width": width, "height": height})
        pg.click(".tf-pin[data-entity='anna']")
        board = pg.locator(".tf-board").bounding_box()
        panel = pg.locator("#tf-panel").bounding_box()
        assert panel["y"] < height and panel["y"] + panel["height"] > 0, panel
        assert panel["x"] < width and panel["x"] + panel["width"] > 0, panel
        assert panel["x"] >= board["x"] + board["width"], (board, panel)
        b.close()


def test_click_card_and_thread_open_panel(page_path):
    with sync_api.sync_playwright() as pw:
        b, pg = _open(pw, page_path)
        pg.click(".tf-card[data-entity='sia-a']")
        assert "Apgrozījums 0\u00a0€" in pg.locator("#tf-panel").inner_text()
        assert sorted(pg.locator(".tf-threads path").evaluate_all(
            "ps => ps.map(p => p.dataset.link)")) == ["l1", "l3"]
        pg.locator(".tf-board").scroll_into_view_if_needed()
        x, y = pg.locator(".tf-threads path[data-link='l1']").evaluate("""p => {
            const pt = p.getPointAtLength(p.getTotalLength() * 0.5);
            const r = p.ownerSVGElement.getBoundingClientRect();
            return [r.left + pt.x, r.top + pt.y];
        }""")
        pg.mouse.click(x, y)
        assert "valdes priekšsēdētāja" in pg.locator("#tf-panel").inner_text()
        assert "l=l1" in pg.url
        b.close()


def test_deeplink_and_back(page_path):
    with sync_api.sync_playwright() as pw:
        b, pg = _open(pw, page_path, hash_="#e=sia-b")
        assert pg.locator(".tf-card[data-entity='sia-b']").get_attribute("class").count("is-sel") == 1
        pg.click(".tf-pin[data-entity='anna']")
        pg.go_back()
        assert "e=sia-b" in pg.url
        assert "SIA «Beta»" in pg.locator("#tf-panel").inner_text()
        pg.goto(page_path.as_uri() + "#sia-a")          # grāmatas enkurs bez «=»
        assert "is-sel" in pg.locator(".tf-card[data-entity='sia-a']").get_attribute("class")
        b.close()


def test_unknown_hash_is_ignored(page_path):
    with sync_api.sync_playwright() as pw:
        b, pg = _open(pw, page_path)
        pg.click(".tf-pin[data-entity='anna']")
        assert pg.locator(".tf-threads path").count() == 3
        pg.goto(page_path.as_uri() + "#e=nav-tada")
        assert pg.locator(".tf-threads path").count() == 0
        assert "undefined" not in pg.locator("#tf-panel").inner_text()
        b.close()


@pytest.mark.parametrize("hash_", ["#%", "#e=%25", "#e=anna%26l%3Dl1"])
def test_malformed_or_encoded_hash_does_not_crash(page_path, hash_):
    with sync_api.sync_playwright() as pw:
        b, pg = _open(pw, page_path, hash_=hash_)
        errors = []
        pg.on("pageerror", lambda error: errors.append(str(error)))
        assert pg.locator(".tf-threads path").count() == 0
        pg.click(".tf-pin[data-entity='anna']")
        assert pg.locator(".tf-threads path").count() == 3
        assert errors == []
        b.close()


def test_panel_selection_preserves_external_focus_and_unique_ids(page_path):
    with sync_api.sync_playwright() as pw:
        b, pg = _open(pw, page_path)
        pg.focus(".tf-pin[data-entity='anna']")
        pg.keyboard.press("Enter")
        pg.focus("#tf-panel [data-select-link='l1']")
        pg.keyboard.press("Enter")
        assert pg.evaluate("document.activeElement.id") == "tf-panel"
        assert pg.locator("#tf-panel > ol > li").count() == 1
        assert pg.evaluate("""() => { const ids = [...document.querySelectorAll('[id]')].map(e => e.id);
            return new Set(ids).size === ids.length; }""")
        pg.keyboard.press("Escape")
        assert pg.evaluate("document.activeElement.dataset.entity") == "anna"
        b.close()


def test_zone_and_article_guide_select_direct_relationships(page_path):
    with sync_api.sync_playwright() as pw:
        b, pg = _open(pw, page_path)
        pg.click(".tf-zone")
        assert "Reģistrētā adrese" in pg.locator("#tf-panel").inner_text()
        assert pg.locator(".tf-threads path").count() == 0
        assert pg.locator("#tf-panel [data-entity]").count() == 2
        pg.click(".tf-guide")
        assert sorted(pg.locator(".tf-threads path").evaluate_all(
            "ps => ps.map(p => p.dataset.link)")) == ["l1", "l3"]
        assert pg.locator("#tf-panel a").first.get_attribute("href") == "testa-raksts.html"
        b.close()


def test_interaction_works_under_csp(page_url):
    with sync_api.sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page()
        errors = []
        pg.on("pageerror", lambda error: errors.append(str(error)))
        pg.goto(page_url)
        pg.click(".tf-pin[data-entity='anna']")
        assert pg.locator(".tf-threads path").count() == 3
        assert errors == []
        b.close()


def test_keyboard_select_and_escape(page_path):
    with sync_api.sync_playwright() as pw:
        b, pg = _open(pw, page_path)
        pg.focus(".tf-pin[data-entity='anna']")
        pg.keyboard.press("Enter")
        assert pg.locator(".tf-threads path.is-on").count() == 3
        pg.keyboard.press("Escape")
        assert pg.locator(".tf-threads path").count() == 0
        assert pg.evaluate("document.activeElement.dataset.entity") == "anna"
        pg.focus(".tf-book [data-select-link='l1']")
        pg.keyboard.press("Enter")
        assert "l=l1" in pg.url
        b.close()


def test_threads_follow_resize(page_path):
    with sync_api.sync_playwright() as pw:
        b, pg = _open(pw, page_path)
        pg.click(".tf-pin[data-entity='anna']")
        pg.set_viewport_size({"width": 1100, "height": 900})
        pg.wait_for_timeout(200)
        end = pg.evaluate("""() => {
          const p = document.querySelector(".tf-threads path[data-link='l1']");
          const pt = p.getPointAtLength(p.getTotalLength());
          const svg = p.ownerSVGElement.getBoundingClientRect();
          const c = document.querySelector(".tf-card[data-entity='sia-a']").getBoundingClientRect();
          return [svg.left + pt.x, svg.top + pt.y, c.left, c.right, c.top, c.bottom];
        }""")
        x, y, l, r, t, btm = end
        assert l - 2 <= x <= r + 2 and t - 2 <= y <= btm + 2
        b.close()


def test_show_all_with_tier_filter_counts(page_path):
    with sync_api.sync_playwright() as pw:
        b, pg = _open(pw, page_path)
        pg.click(".tf-showall")
        assert pg.locator(".tf-threads path").count() == 4
        assert pg.locator(".tf-threads path.is-on").count() == 0   # neitrāli, ne sarkani
        pg.uncheck("[data-filter-tier='2']")
        pg.uncheck("[data-filter-tier='3']")
        assert pg.locator(".tf-threads path").count() == 2
        assert "Rādīti 2 no 4" in pg.locator(".tf-count").inner_text()
        assert "t=1" in pg.url
        b.close()


def test_empty_filter_explains(page_path):
    with sync_api.sync_playwright() as pw:
        b, pg = _open(pw, page_path, hash_="#all=1&t=1&k=cits")
        assert pg.locator(".tf-threads path").count() == 0
        assert "Notīri kādu filtru" in pg.locator(".tf-count").inner_text()
        b.close()


@pytest.mark.parametrize("field", ["tier", "kind"])
def test_empty_filters_survive_reload_and_back(page_path, field):
    with sync_api.sync_playwright() as pw:
        b, pg = _open(pw, page_path)
        assert pg.locator(".tf-filters").is_hidden()
        pg.click(".tf-showall")
        assert pg.locator(".tf-threads path").count() == 4
        for control in pg.locator(f"[data-filter-{field}]").all():
            control.uncheck()
        assert pg.locator(".tf-threads path").count() == 0
        pg.reload()
        assert pg.locator(".tf-threads path").count() == 0
        assert pg.locator(f"[data-filter-{field}]:checked").count() == 0
        pg.locator(f"[data-filter-{field}]").first.check()
        assert pg.locator(".tf-threads path").count() > 0
        pg.go_back()
        assert pg.locator(".tf-threads path").count() == 0
        assert pg.locator(f"[data-filter-{field}]:checked").count() == 0
        pg.click(".tf-showall")
        assert pg.locator(".tf-filters").is_hidden()
        b.close()


def test_combined_filters_and_selection(page_path):
    with sync_api.sync_playwright() as pw:
        b, pg = _open(pw, page_path)
        pg.click(".tf-showall")
        pg.select_option("[data-filter-person]", "anna")
        assert pg.locator(".tf-threads path").count() == 3
        pg.uncheck("[data-filter-kind='cits']")
        assert pg.locator(".tf-threads path").count() == 2
        pg.uncheck("[data-filter-tier='2']")
        assert pg.locator(".tf-threads path").evaluate_all("ps => ps.map(p => p.dataset.link)") == ["l1"]
        assert "p=anna" in pg.url
        pg.click(".tf-pin[data-entity='anna']")
        assert pg.locator(".tf-threads path.is-on").count() == 3
        pg.uncheck("[data-filter-tier='1']")
        assert pg.locator(".tf-threads path").count() == 0
        assert "Notīri kādu filtru" in pg.locator(".tf-count").inner_text()
        b.close()


def test_phone_shows_closeup_first_and_switches_to_list(page_path):
    with sync_api.sync_playwright() as pw:
        b, pg = _open(pw, page_path, width=390)
        cu = pg.locator(".tf-closeup")
        assert cu.is_visible()
        assert cu.bounding_box()["y"] < 520          # tuvplāns sākas ekrāna augšdaļā
        assert cu.locator("[data-entity]").count() >= 2   # izvēlētais + kaimiņi
        cu.locator("[data-entity='sia-a']").click()
        assert "e=sia-a" in pg.url
        pg.click("[data-view='list']")
        assert pg.locator(".tf-book").is_visible()
        b.close()


def test_phone_no_horizontal_overflow(page_path):
    with sync_api.sync_playwright() as pw:
        b, pg = _open(pw, page_path, width=390, hash_="#e=anna")
        pg.locator(".tf-cu-focus h3").evaluate("el => el.textContent = 'Izdomāta pētniecības institūta valdes priekšsēdētāja ' + 'ĻotiGaršNosaukums'.repeat(12)")
        assert pg.evaluate("document.documentElement.scrollWidth") <= 390
        b.close()


def test_phone_overview_fit_and_desktop_resize(page_path):
    with sync_api.sync_playwright() as pw:
        b, pg = _open(pw, page_path, width=390)
        assert pg.locator(".tf").get_attribute("data-mode") == "phone"
        assert pg.locator("#tf-board").is_hidden()
        pg.click("[data-overview='open']")
        assert pg.locator("#tf-board").is_visible()
        assert pg.locator("#tf-board").bounding_box()["width"] >= 1100
        assert pg.evaluate("document.documentElement.scrollWidth") <= 390
        pg.click("[data-overview='fit']")
        assert pg.locator("#tf-board").bounding_box()["width"] <= 390
        pg.set_viewport_size({"width": 1440, "height": 900})
        sync_api.expect(pg.locator(".tf")).to_have_attribute("data-mode", "desktop")
        assert pg.locator(".tf-closeup").is_hidden()
        assert pg.locator("#tf-board").is_visible()
        b.close()


def test_phone_switch_keeps_selection_and_pressed_state(page_path):
    with sync_api.sync_playwright() as pw:
        b, pg = _open(pw, page_path, width=390, hash_="#e=sia-b")
        assert "SIA «Beta»" in pg.locator(".tf-cu-focus").inner_text()
        pg.click("[data-view='list']")
        assert pg.locator("[data-view='list']").get_attribute("aria-pressed") == "true"
        assert pg.locator("[data-view='board']").get_attribute("aria-pressed") == "false"
        assert pg.locator(".tf-closeup").is_hidden()
        assert pg.locator(".tf-book").is_visible()
        pg.click("[data-view='board']")
        assert "SIA «Beta»" in pg.locator(".tf-cu-focus").inner_text()
        assert "e=sia-b" in pg.url
        b.close()


def test_phone_neighbors_keep_tiers_sources_and_link_navigation(page_path):
    with sync_api.sync_playwright() as pw:
        b, pg = _open(pw, page_path, width=390)
        assert sorted(pg.locator(".tf-cu-neighbors > li").evaluate_all(
            "els => els.map(e => e.dataset.tier)")) == ["1", "2", "3"]
        assert pg.locator(".tf-closeup a.tf-src").count() == 3
        assert "nav pierādīts" in pg.locator(".tf-closeup").inner_text()
        pg.click(".tf-closeup [data-select-link='l2']")
        assert "l=l2" in pg.url
        assert "pēc uzņēmuma lapas" in pg.locator(".tf-closeup").inner_text()
        pg.go_back()
        assert pg.locator(".tf-cu-focus").is_visible()
        b.close()


def test_phone_without_js_keeps_full_book(page_path):
    with sync_api.sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 390, "height": 844}, java_script_enabled=False)
        pg.goto(page_path.as_uri())
        assert pg.locator(".tf-book").is_visible()
        assert pg.locator(".tf-book .tf-link").count() == 4
        assert pg.evaluate("document.documentElement.scrollWidth") <= 390
        b.close()


@pytest.mark.parametrize("width", [390, 900])
def test_no_js_phone_hides_squeezed_board_and_points_to_ledger(page_path, width):
    with sync_api.sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": width, "height": 844}, java_script_enabled=False)
        pg.goto(page_path.as_uri())
        assert pg.locator(".tf-board").is_hidden()
        assert pg.locator(".tf-ledger").is_visible()
        pg.locator(".tf-nojs a").click()
        assert pg.url.endswith("#tf-book-h")
        b.close()


def test_board_numbers_keep_thousands_and_units_together(page_path):
    with sync_api.sync_playwright() as pw:
        b, pg = _open(pw, page_path, hash_="#e=sia-a")
        assert "0\u00a0€" in pg.locator("#tf-panel .tf-facts").text_content()
        from src.render.tafeles import nonbreaking_numbers
        assert nonbreaking_numbers("21 akcionārs pa 50 000 €; 1 119 931 €; 100 %") == (
            "21 akcionārs pa 50\u00a0000\u00a0€; 1\u00a0119\u00a0931\u00a0€; 100\u00a0%")
        b.close()


def test_panel_and_phone_sources_have_no_dangling_text_separators(page_path):
    with sync_api.sync_playwright() as pw:
        b, pg = _open(pw, page_path, hash_="#e=anna")
        assert " · " not in pg.locator("#tf-panel .tf-ev").first.text_content()
        assert " · " not in pg.locator(".tf-book .tf-facts").first.text_content()
        pg.set_viewport_size({"width": 390, "height": 844})
        sync_api.expect(pg.locator(".tf")).to_have_attribute("data-mode", "phone")
        assert " · " not in pg.locator(".tf-cu-neighbors").text_content()
        b.close()


@pytest.mark.parametrize("width", [901, 1024])
def test_small_desktop_selection_stays_beside_readable_board(page_path, width):
    with sync_api.sync_playwright() as pw:
        b, pg = _open(pw, page_path, width=width)
        pg.click(".tf-pin[data-entity='anna']")
        board = pg.locator(".tf-board").bounding_box()
        panel = pg.locator("#tf-panel").bounding_box()
        assert panel["y"] < 900 and panel["y"] + panel["height"] > 0, panel
        assert panel["x"] >= board["x"] + board["width"], (board, panel)
        assert panel["x"] + panel["width"] <= width, panel
        assert pg.evaluate("document.documentElement.scrollWidth") <= width
        assert pg.locator(".tf-card, .tf-pin").evaluate_all("""cards => cards.every(c =>
            c.scrollWidth <= c.clientWidth + 1 && c.scrollHeight <= c.clientHeight + 1)
        """)
        b.close()


def test_selection_panel_sticks_below_header_while_board_scrolls(page_path):
    with sync_api.sync_playwright() as pw:
        b, pg = _open(pw, page_path)
        pg.click(".tf-pin[data-entity='anna']")
        stage_top = pg.locator(".tf-stage").bounding_box()["y"]
        pg.evaluate("y => scrollTo({top:y, behavior:'instant'})", stage_top + 100)
        panel = pg.locator("#tf-panel").bounding_box()
        nav = pg.locator(".nav").bounding_box()
        assert nav["y"] + nav["height"] <= panel["y"] <= nav["height"] + 40, (nav, panel)
        assert panel["y"] + panel["height"] <= 900, panel
        b.close()


def test_parallel_relationships_have_separate_clickable_threads(tmp_path):
    import yaml
    from scripts.preview_tafele import build_preview
    raw = yaml.safe_load(FIX.read_text(encoding="utf-8"))
    raw["links"].append(dict(raw["links"][0], id="parallel", verb="pārstāv uzņēmumu"))
    data = tmp_path / "board.yaml"
    data.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    articles = tmp_path / "articles"
    articles.mkdir()
    (articles / "testa-raksts.md").write_text("---\ntitle: T\n---\n## A\nTeksts", encoding="utf-8")
    path = build_preview(data, tmp_path / "preview", articles_dir=articles, extra_persons={"anna"})
    with sync_api.sync_playwright() as pw:
        b, pg = _open(pw, path)
        for link_id in ("l1", "parallel"):
            pg.click(".tf-pin[data-entity='anna']")
            first = pg.locator(".tf-threads path[data-link='l1']")
            second = pg.locator(".tf-threads path[data-link='parallel']")
            assert first.get_attribute("d") != second.get_attribute("d")
            pg.locator(".tf-board").scroll_into_view_if_needed()
            x, y = pg.locator(f".tf-threads path[data-link='{link_id}']").evaluate("""p => {
                const pt = p.getPointAtLength(p.getTotalLength() / 2);
                const r = p.ownerSVGElement.getBoundingClientRect();
                return [r.left + pt.x, r.top + pt.y];
            }""")
            pg.mouse.click(x, y)
            assert f"l={link_id}" in pg.url
        b.close()


def test_published_board_has_finding_card_and_listing_cover(tmp_path):
    # Fails if: the board gets the generic og-atmina.png (render_analyses skips
    # standalone pages) or its md lacks `image:`, so the listing card is bare.
    import re
    from src.render._common.assets import _render_page
    from src.render._orchestrator import _make_env
    from src.render.analyses import _load_analyses
    from src.render.tafeles import render_tafeles
    atmina = tmp_path / "atmina"
    env = _make_env()
    assert render_tafeles(env, atmina, data_dir=ROOT / "content" / "tafeles",
                          articles_dir=ROOT / "content" / "analizes") >= 1
    html = (atmina / "analizes" / "saites-visvanati-2026.html").read_text(encoding="utf-8")
    og = re.search(r'<meta property="og:image" content="([^"]+)"', html)[1]
    assert re.fullmatch(r"https://atmina\.lv/assets/og/atradumi/saites-visvanati-2026\.png\?v=[0-9a-f]{8}", og), og
    assert f'<meta name="twitter:image" content="{og}">' in html
    # conftest stubs Chromium: the PNG proves the job reached render_og_images.
    assert (atmina / "assets" / "og" / "atradumi" / "saites-visvanati-2026.png").exists()
    atradumi = [a for a in _load_analyses(articles_dir=ROOT / "content" / "analizes") if a["kind"] == "atradums"]
    _render_page(env, "analizes.html.j2", atmina / "analizes.html", {
        "analyses": [], "atradumi": atradumi, "syntheses": [], "posts": [], "trends_data": {},
        "context_notes": [], "metrics": {"daily": 0, "weekly": 0, "tematic": 0, "sintezes": 0}})
    listing = (atmina / "analizes.html").read_text(encoding="utf-8")
    assert 'href="analizes/saites-visvanati-2026.html" class="analysis-feat has-image"' in listing


def test_published_board_shows_wrapper_notes_and_article_count(tmp_path, monkeypatch):
    # Fails if: render_tafeles drops the wrapper md body (credit/caveats never
    # reach the page) or the description keeps a fixed article count.
    import yaml
    import src.tafele.model as model
    from src.render._orchestrator import _make_env
    from src.render.tafeles import render_tafeles
    monkeypatch.setattr(model, "PUBLIC_PERSONS", model.PUBLIC_PERSONS | {"anna"})
    raw = yaml.safe_load(FIX.read_text(encoding="utf-8"))
    raw["draft"] = False
    raw["articles"]["otrs-raksts"] = "Otrs raksts"
    data = tmp_path / "tafeles"
    data.mkdir()
    (data / "board.yaml").write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    arts = tmp_path / "analizes"
    arts.mkdir()
    (arts / "testa-raksts.md").write_text("---\ntitle: T\n---\n## A\nTeksts\n## B\nTeksts\n## C\nTeksts\n",
                                          encoding="utf-8")
    (arts / f"{raw['slug']}.md").write_text(
        "---\ntitle: Testa tāfele\nstandalone: true\n---\n\n# Testa tāfele\n\n"
        "## Izpētes norādes\n\nNorādi par saiti sniedza Testa Kreditētāja-Unikālā "
        "([avots](https://example.org/x), [otrs](https://example.net/y)).\n",
        encoding="utf-8")
    atmina = tmp_path / "atmina"
    assert render_tafeles(_make_env(), atmina, data_dir=data, articles_dir=arts) == 1
    with sync_api.sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page()
        pg.goto((atmina / "analizes" / f"{raw['slug']}.html").as_uri())
        notes = pg.locator(".tf-notes")
        assert "Testa Kreditētāja-Unikālā" in notes.inner_text()
        assert notes.locator("a[href='https://example.net/y']").count() == 1
        assert pg.locator("h1").count() == 1
        desc = pg.locator("meta[name='description']").get_attribute("content")
        assert desc.startswith("2 rakstu saites"), desc
        b.close()
