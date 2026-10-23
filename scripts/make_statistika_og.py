"""Ģenerē statistikas lapas OG attēlu (1200×630) no DZĪVAJIEM `data/csp.db` datiem.

Kāpēc Playwright, ne PIL: vienīgais veids, kā attēls izskatās tieši kā vietne, ir
lietot vietnes pašas fontus un CSS. `_generate_og_image()` orchestratorā zīmē ar
PIL un tāpēc paļaujas uz `C:/Windows/Fonts/arial.ttf` — mašīnatkarīgi un ne mūsu
tipogrāfija. Šeit karti uzbūvē kā HTML ar iegultu JetBrains Mono (tas pats woff2,
ko lieto vietne) un nofotografē.

Kāpēc no csp.db, ne statisks fails: skaitļi kartē noveco. Pēc katra
`python -m src.csp --apply` palaid arī šo, un OG attēls atkal ir patiess.

    .venv/Scripts/python.exe scripts/make_statistika_og.py

Raksta `assets/statistika-og.png`. `generate_public_site()` kopē visu `assets/`
uz `output/atmina/assets/`, bet `generate_statistika()` to NEDARA — pēc šī
skripta izpildes kopē failu rokā vai palaid pilno renderu (sk. commands.md).
"""
from __future__ import annotations

import base64
import sqlite3
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.csp.tables import TABLES  # noqa: E402

CSP_DB = ROOT / "data" / "csp.db"
FONTS_DIR = ROOT / "assets" / "fonts"
# ABAS apakškopas katram svaram. Ar tikai `latin-ext` daļa latviešu burtu krita
# atpakaļ uz sistēmas fontu, un virs "A" parādījās sveša kombinējošā zīme —
# vietne pati ielādē abas, tāpēc arī šeit vajag abas.
FONT_FILES = [
    ("jetbrains-mono-400-latin.woff2", 400),
    ("jetbrains-mono-400-latin-ext.woff2", 400),
    ("jetbrains-mono-500-latin.woff2", 500),
    ("jetbrains-mono-500-latin-ext.woff2", 500),
]
DEST = ROOT / "assets" / "statistika-og.png"

# Tumšā tēma — tā pati, ko lieto vietnes esošais og-image.png, lai plūsmā
# abi izskatītos kā viena zīmola attēli.
BG = "#0d1014"
TEXT = "#e2e4e9"
MUTED = "#8b8fa3"
HIGHLIGHT = "#B71C1C"
DOMAIN = {
    "economy": "#90A4AE",
    "social": "#B388C7",
    "prices": "#f97316",
    "state": "#22c55e",
}
ORDER = ["NVA011m", "PCI021m", "DSV010m", "IRS010m", "VFV050",
         "IKP010", "ISP010c", "KRE020m", "IBE010", "NNI030"]


def series(db, table_id):
    return [r[0] for r in db.execute(
        "SELECT value FROM csp_data WHERE table_id=? ORDER BY period", (table_id,))]


def sparkline(vals, w=190, h=42):
    """Pēdējie ~60 punkti kā SVG polilīnija. Plakana sērija → taisna līnija vidū."""
    pts = vals[-60:] if len(vals) > 60 else vals
    if len(pts) < 2:
        return ""
    lo, hi = min(pts), max(pts)
    span = (hi - lo) or 1
    step = w / (len(pts) - 1)
    coords = " ".join(
        f"{i * step:.1f},{h - (v - lo) / span * (h - 4) - 2:.1f}" for i, v in enumerate(pts)
    )
    return f'<polyline points="{coords}" fill="none" stroke-width="2" vector-effect="non-scaling-stroke"/>'


def font_faces() -> str:
    out = []
    for name, weight in FONT_FILES:
        path = FONTS_DIR / name
        b64 = base64.b64encode(path.read_bytes()).decode()
        out.append(f"@font-face{{font-family:'JB';font-weight:{weight};font-style:normal;"
                   f"src:url(data:font/woff2;base64,{b64}) format('woff2');}}")
    return "".join(out)


def build_html(cards, updated: str) -> str:
    tiles = "".join(
        f"""<div class="t" style="--c:{c['color']}">
              <div class="lbl">{c['label']}</div>
              <div class="val">{c['value']}</div>
              <svg class="spark" viewBox="0 0 190 42" preserveAspectRatio="none">{c['spark']}</svg>
            </div>"""
        for c in cards
    )
    return f"""<!doctype html><meta charset="utf-8"><style>
{font_faces()}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:1200px;height:630px;background:{BG};color:{TEXT};
     font-family:'JB',ui-monospace,monospace;overflow:hidden;
     display:flex;flex-direction:column;padding:44px 52px 30px}}
.bar{{position:absolute;left:0;right:0;bottom:0;height:12px;background:{HIGHLIGHT}}}
.eyebrow{{font-size:17px;letter-spacing:.22em;color:{MUTED};text-transform:uppercase;
         display:flex;align-items:center;gap:14px}}
.eyebrow:before{{content:"";width:34px;height:2px;background:{HIGHLIGHT}}}
h1{{font-size:52px;font-weight:500;letter-spacing:-.02em;margin:14px 0 6px}}
.sub{{font-size:19px;color:{MUTED};margin-bottom:26px}}
.grid{{display:grid;grid-template-columns:repeat(5,1fr);
      grid-template-rows:1fr 1fr;gap:14px;flex:1;min-height:0}}
.t{{border:1px solid #262b33;border-left:3px solid var(--c);border-radius:7px;
   padding:14px 15px 10px;background:#12161c;
   display:flex;flex-direction:column}}
.lbl{{font-size:11.5px;letter-spacing:.1em;color:{MUTED};text-transform:uppercase;
     line-height:1.35;min-height:31px}}
.val{{font-size:27px;font-weight:500;margin-top:5px;color:var(--c)}}
.spark{{width:100%;height:30px;margin-top:auto;stroke:var(--c);opacity:.72}}
.foot{{margin-top:22px;font-size:16px;color:{MUTED};
      display:flex;justify-content:space-between;align-items:baseline}}
.foot b{{color:{TEXT};font-weight:500}}
</style>
<div class="eyebrow">atmina.lv · statistika</div>
<h1>Latvijas ekonomiskā realitāte</h1>
<div class="sub">Desmit rādītāji no Centrālās statistikas pārvaldes, sasaistīti ar politiskajiem notikumiem</div>
<div class="grid">{tiles}</div>
<div class="foot"><span>Līdz 30 gadu vēsture · notikumi uz līknes</span><span>Atjaunots <b>{updated}</b></span></div>
<div class="bar"></div>"""


def main() -> int:
    db = sqlite3.connect(CSP_DB)
    updated = db.execute("SELECT MAX(DATE(last_sync)) FROM csp_metadata").fetchone()[0]
    cards = []
    for tid in ORDER:
        cfg = TABLES[tid]
        vals = series(db, tid)
        if not vals:
            print(f"IZLAISTS {tid}: nav datu")
            continue
        cards.append({
            "label": cfg["label"],
            "value": cfg["format_short"](vals[-1]),
            "color": DOMAIN.get(cfg["domain"], "#90A4AE"),
            "spark": sparkline(vals),
        })
    db.close()
    if len(cards) != len(ORDER):
        print(f"BRĪDINĀJUMS: gaidītas {len(ORDER)} kartītes, sanāca {len(cards)}")

    html = build_html(cards, updated)
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": 1200, "height": 630}, device_scale_factor=1)
        page.set_content(html, wait_until="networkidle")
        page.wait_for_timeout(500)
        DEST.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(DEST))
        b.close()

    kb = DEST.stat().st_size / 1024
    print(f"{DEST.relative_to(ROOT)} · {len(cards)} rādītāji · atjaunots {updated} · {kb:.0f} KB")
    return 0 if len(cards) == len(ORDER) else 1


if __name__ == "__main__":
    raise SystemExit(main())
