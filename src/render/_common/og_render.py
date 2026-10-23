"""Shared 1200×630 OG card renderer (Playwright, incremental).

Every card type (pretruna, landing, profile, partija, tēma) hands over a list
of ``(out_path, html)`` jobs, where ``html`` is the rendered card WITHOUT
fonts. A job is skipped when its PNG exists and the sha256 of ``html`` matches
the single manifest ``<output>/og-hashes.json`` (keyed by the PNG path
relative to ``<output>/atmina``). The manifest lives outside the deploy tree.
Fonts (Source Serif 4, base64) are injected here, read once per process.
"""

from __future__ import annotations

import base64
import functools
import hashlib
import json
from pathlib import Path

from src.render._common.constants import ASSETS_DIR
from src.render._common.filters import _lv_number

_FONT_FILES = {
    "normal": ("source-serif-4-normal-latin-ext.woff2", "source-serif-4-normal-latin.woff2"),
    "italic": ("source-serif-4-italic-latin-ext.woff2", "source-serif-4-italic-latin.woff2"),
}


@functools.cache
def _font_css() -> str:
    """@font-face bloks ar base64 fontiem — vienreiz procesā."""
    faces = []
    for style, files in _FONT_FILES.items():
        srcs = ", ".join(
            "url('data:font/woff2;base64,"
            + base64.b64encode((ASSETS_DIR / "fonts" / f).read_bytes()).decode()
            + "') format('woff2')"
            for f in files
        )
        faces.append(
            f"@font-face {{ font-family: 'SS4'; font-style: {style}; "
            f"font-weight: 200 900; src: {srcs}; }}"
        )
    return "<style>" + "\n".join(faces) + "</style>"


def og_role_line(role: str | None, party: str | None, limit: int = 75) -> str:
    """«Amats, «Partija»»; pārāk garam amatam paliek tikai pirmais posms."""
    party = (party or "").strip().strip('«»"')
    party_label = f"«{party}»" if party else ""
    role = role or ""
    line = ", ".join(x for x in (role, party_label) if x)
    if len(line) > limit:  # garš amats → tikai pirmais posms, ne «prezi…»
        role = role.split(",")[0]
        line = ", ".join(x for x in (role, party_label) if x)
    if len(line) > limit and role:  # joprojām garš → nogriež pie vārda, partija paliek
        room = max(limit - len(party_label) - 3, 20)
        cut = role[:room].rsplit(" ", 1)[0]
        if cut.count("(") > cut.count(")"):  # neatstāj vaļēju iekavu
            cut = cut[:cut.rindex("(")]
        line = ", ".join(x for x in (cut.rstrip(" ,;:—–-") + "…", party_label) if x)
    return line


def og_stat(n: int, one: str, many: str) -> dict[str, str]:
    """Kartītes skaitlis: «9 644» (nedalāma atstarpe) + LV forma (1, 21 → vsk.)."""
    return {"value": _lv_number(n), "label": one if n % 10 == 1 and n % 100 != 11 else many}


def og_name_size(name: str, steps: tuple[tuple[int, int], ...]) -> int:
    """Burta izmērs pēc garuma: pirmais (max_garums, izmērs), kurā ietilpst."""
    for max_len, size in steps:
        if len(name) <= max_len:
            return size
    return steps[-1][1]


def section_card(kind: str, name: str, lead: str, stats: list[dict[str, str]],
                 url: str) -> dict[str, object]:
    """Sadaļas (partija/tēma) kartītes konteksts; virsraksts 1080px platumā,
    garam nosaukumam mazāks burts (līdz 2 rindām)."""
    return {
        "kind": kind, "name": name, "lead": lead, "stats": stats, "url": url,
        "name_size": og_name_size(name, ((22, 96), (29, 76), (37, 60), (999, 50))),
    }


def _load_manifest(path: Path) -> dict[str, str]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    # Līdz 2026-10-15 atslēga bija pretrunas id («13») — pārnes uz ceļu.
    return {
        (f"assets/og/pretruna-{k}.png" if k.isdigit() else k): v for k, v in raw.items()
    }


def _shoot(todo: list[tuple[Path, str]]):
    """Uzzīmē katru (ceļš, pilns HTML) PNG'ā ar vienu Chromium lapu; atdod
    ceļu uzreiz pēc katra kadra, lai kļūmes gadījumā jau uzzīmētais paliek."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": 1200, "height": 630}, device_scale_factor=2,
        )
        page = context.new_page()
        try:
            for out_path, html in todo:
                page.set_content(html, wait_until="networkidle")
                page.evaluate("() => document.fonts.ready")
                page.screenshot(path=str(out_path), full_page=False, type="png")
                yield out_path
        finally:
            browser.close()


def render_og_images(jobs: list[tuple[Path, str]], site_dir: Path) -> int:
    """Render changed/missing cards; return how many PNGs were drawn.

    ``site_dir`` is the deploy tree (``output/atmina``); every ``out_path`` sits
    under it, and the manifest lives one level up, outside the deploy.
    """
    manifest_path = site_dir.parent / "og-hashes.json"
    manifest = _load_manifest(manifest_path)
    todo = []
    for out_path, html in jobs:
        key = out_path.relative_to(site_dir).as_posix()
        digest = hashlib.sha256(html.encode()).hexdigest()
        if out_path.exists() and manifest.get(key) == digest:
            continue
        todo.append((out_path, html, key, digest))
    if not todo:
        return 0

    fonts = _font_css()
    digests = {out_path: (key, digest) for out_path, _, key, digest in todo}
    done = 0
    try:
        for out_path, *_ in todo:
            out_path.parent.mkdir(parents=True, exist_ok=True)
        full = [(o, h.replace("</head>", fonts + "</head>", 1)) for o, h, _, _ in todo]
        for out_path in _shoot(full):
            key, digest = digests[out_path]
            manifest[key] = digest
            done += 1
    finally:
        # Arī pēc kļūmes — jau uzzīmētās kartītes nākamreiz neatkārto.
        manifest_path.write_text(json.dumps(manifest, indent=0, sort_keys=True), encoding="utf-8")
    return done
