#!/usr/bin/env python
"""Shēmas HTML → PNG ar Chromium (aizstāj rokas Playwright soli).

Lietošana:
    .venv/Scripts/python.exe scripts/render_shema.py IN.html OUT.png [--width 1600 --height 900]

Atradumam OUT = `output/images/analizes/<slug>.png` (+ `-light.png`, ja ir
gaišā versija); izmēru variantus renders izveido pats (`_ensure_image_variants`).
Fonti tiek gaidīti (`document.fonts.ready`), citādi PNG var iznākt ar
rezerves fontu.
"""

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("html", type=Path)
    ap.add_argument("png", type=Path)
    ap.add_argument("--width", type=int, default=1600)
    ap.add_argument("--height", type=int, default=900)
    args = ap.parse_args()
    if not args.html.is_file():
        raise SystemExit(f"Nav faila: {args.html}")
    args.png.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": args.width, "height": args.height})
        page.goto(args.html.resolve().as_uri(), wait_until="networkidle")
        page.evaluate("document.fonts.ready.then(() => true)")
        fonts = page.evaluate(
            "[...document.fonts].map(f => f.family + ':' + f.status)")
        if any(f.endswith(":error") for f in fonts):
            browser.close()
            raise SystemExit(f"Fonts neielādējās {sorted(set(fonts))} — "
                             "pārbaudi @font-face ceļus; PNG netika rakstīts")
        page.screenshot(path=str(args.png), full_page=False)
        browser.close()
    print(f"{args.png} ({args.width}×{args.height}); fonti: {sorted(set(fonts))}")


if __name__ == "__main__":
    main()
