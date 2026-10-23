"""Raksta attēli atveras pilnekrāna skatā (lbv1.js, 2026-10-18).

Kļūme, ko šis tests ķer: plata shēma (piem. `analizes/visvanati-pilsoniba-2026`)
raksta kolonnā ir par mazu, lai izlasītu tekstu, un to nevarēja palielināt.
Brauc īstu `blog-post.html.j2` lapu pārlūkā (Playwright, Chromium) ar īstajiem
`assets/style.css` + `assets/lbv1.js`: tastatūra atver dialogu, Esc aizver un
fokuss atgriežas pie attēla; attēls saitē paliek neskarts.
Inline-JS aizliegumu sargā `tests/test_no_inline_js.py` — šeit to neatkārto.
"""
import shutil
from pathlib import Path

import pytest

from tests.test_blog_brief_presentation import _daily_post, _template_env

sync_api = pytest.importorskip("playwright.sync_api")
Image = pytest.importorskip("PIL.Image")


def test_body_image_opens_in_lightbox_and_closes_back(tmp_path):
    shutil.copytree("assets", tmp_path / "assets")
    (tmp_path / "images").mkdir()
    Image.new("RGB", (1600, 900), (25, 37, 65)).save(tmp_path / "images" / "shema.png")
    html = _template_env().get_template("blog-post.html.j2").render(
        post=_daily_post(footer=None),
        content_html=(
            '<p><img alt="Shēma ar savienojumiem" src="../images/shema.png"></p>'
            '<p><a href="https://example.org"><img alt="saite" src="../images/shema.png"></a></p>'
        ),
        toc=None, prev_post=None, next_post=None, latest_analysis=None,
        BASE_URL="https://atmina.lv",
    )
    page_path = tmp_path / "analizes" / "raksts.html"
    page_path.parent.mkdir()
    page_path.write_text(html, encoding="utf-8")

    with sync_api.sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Exception as exc:  # pragma: no cover — nav instalēta pārlūka
            pytest.skip(f"Chromium nav pieejams: {exc}")
        page = browser.new_page(viewport={"width": 1280, "height": 800},
                                reduced_motion="reduce")
        page.goto(page_path.as_uri())
        zoomable = page.locator(".post-content img[role=button]")
        assert zoomable.count() == 1, "saitē ietītais attēls nedrīkst kļūt par pogu"

        zoomable.focus()
        page.keyboard.press("Enter")
        dialog = page.locator("dialog.lb")
        assert dialog.evaluate("d => d.open && d.matches(':modal')")
        assert dialog.locator("figcaption").inner_text() == "Shēma ar savienojumiem"
        assert page.evaluate(
            "getComputedStyle(document.documentElement).overflowY") == "hidden", \
            "lapa aiz dialoga nav bloķēta"

        page.keyboard.press("Escape")
        assert not dialog.evaluate("d => d.open")
        assert zoomable.evaluate("el => el === document.activeElement"), \
            "fokuss neatgriezās pie attēla"

        zoomable.click()
        page.locator("dialog.lb button[aria-label='Aizvērt']").click()
        assert not dialog.evaluate("d => d.open")
        browser.close()
