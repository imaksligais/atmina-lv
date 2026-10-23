"""Patreon vāks v2 (2026-10-19): virsraksts + īsta laika ass — pēdējo 60 rutīnas dienu pozīcijas (punkta laukums ~ skaits),
sarkanie punkti = dienas, kad publicēta pretruna. Aizstāj tukšo v1 vāku (patreon_assets_2026_10.py).

Patreon apgriež vāku (izmērīts 2026-10-19 jaunajā izkārtojumā /cw/atmina): datorā redzama josla y≈200–800,
telefonā — vidusdaļa x≈750–1750; profila aplis sedz apakšējo kreiso stūri (x≈300–540, y>850).
Nosaukums un apraksts tagad ir ZEM vāka, tāpēc teksts vākā ir atļauts.

Palaišana: .venv/Scripts/python.exe scripts/oneoff-content/patreon_cover_2026_10.py
— raksta output/images/patreon/cover-v2.{html,png} + apgriezumu priekšskatījumus cover-v2-crop-{desktop,mobile}.png."""
import math
import sqlite3
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.db import PRODUCTION_DB_PATH  # noqa: E402

OUT = ROOT / "output/images/patreon"
W, H = 2500, 1000
SAFE_Y = (200, 800)
MOBILE_X = (750, 1750)
END = date(2026, 10, 19)
DAYS = 60
F = "../../atmina/assets/fonts/"


def daily_counts():
    start = END - timedelta(days=DAYS - 1)
    # LV kolonnas; rutīnas diena sākas 05:00 (src.briefs.routine_day_window) → nobīde −5 h
    c = sqlite3.connect(PRODUCTION_DB_PATH)
    pos = dict(c.execute("SELECT date(created_at,'-5 hours'), count(*) FROM claims WHERE claim_type='position' "
                         "AND date(created_at,'-5 hours') BETWEEN ? AND ? GROUP BY 1", (str(start), str(END))))
    con = dict(c.execute("SELECT date(detected_at,'-5 hours'), count(*) FROM contradictions WHERE confirmed=1 "
                         "AND date(detected_at,'-5 hours') BETWEEN ? AND ? GROUP BY 1", (str(start), str(END))))
    return [(start + timedelta(days=i), pos.get(str(start + timedelta(days=i)), 0),
             con.get(str(start + timedelta(days=i)), 0)) for i in range(DAYS)]


def svg_axis(days):
    x0, x1, y = 160, 2340, 660
    step = (x1 - x0) / (DAYS - 1)
    peak = max(n for _, n, _ in days) or 1
    parts = [f'<line x1="{x0 - 60}" y1="{y}" x2="{x1 + 60}" y2="{y}" class="ax"/>']
    for i, (d, n, k) in enumerate(days):
        x = x0 + i * step
        r = 4 + 34 * math.sqrt(n / peak)  # laukums ~ skaits
        if n:
            parts.append(f'<circle cx="{x:.1f}" cy="{y}" r="{r:.1f}" class="dot"/>')
        if k:
            parts.append(f'<circle cx="{x:.1f}" cy="{y}" r="{max(r, 14) + 10:.1f}" class="ring"/>'
                         f'<circle cx="{x:.1f}" cy="{y}" r="11" class="red"/>')
        if d.day == 1:
            label = {9: "1. SEPT", 10: "1. OKT"}[d.month]
            parts.append(f'<line x1="{x:.1f}" y1="{y + 52}" x2="{x:.1f}" y2="{y + 70}" class="tick"/>'
                         f'<text x="{x:.1f}" y="{y + 108}" class="lbl">{label}</text>')
    return f'<svg class="axis" viewBox="0 0 {W} {H}" aria-hidden="true">{"".join(parts)}</svg>'


def html(days):
    return f"""<!doctype html>
<!-- atmina.lv Patreon vāks v2. Ģenerēts ar scripts/oneoff-content/patreon_cover_2026_10.py. -->
<html lang="lv"><head><meta charset="utf-8"><style>
@font-face {{ font-family:'Source Serif 4'; src:url('{F}source-serif-4-normal-latin-ext.woff2') format('woff2'); font-weight:200 900; }}
@font-face {{ font-family:'Source Serif 4'; src:url('{F}source-serif-4-normal-latin.woff2') format('woff2'); font-weight:200 900; }}
@font-face {{ font-family:'Source Serif 4'; font-style:italic; src:url('{F}source-serif-4-italic-latin-ext.woff2') format('woff2'); font-weight:200 900; }}
@font-face {{ font-family:'Source Serif 4'; font-style:italic; src:url('{F}source-serif-4-italic-latin.woff2') format('woff2'); font-weight:200 900; }}
@font-face {{ font-family:'JetBrains Mono'; src:url('{F}jetbrains-mono-500-latin-ext.woff2') format('woff2'); font-weight:500; }}
@font-face {{ font-family:'JetBrains Mono'; src:url('{F}jetbrains-mono-500-latin.woff2') format('woff2'); font-weight:500; }}
*, *::before, *::after {{ box-sizing:border-box; margin:0; padding:0; }}
:root {{
  --night: oklch(27% 0.055 265);
  --paper: oklch(96.4% 0.015 90);
  --red: oklch(64.6% 0.19 25);
  --dim: color-mix(in oklch, var(--paper) 72%, var(--night));
  font-synthesis:none; -webkit-font-smoothing:antialiased;
}}
body {{ inline-size:{W}px; block-size:{H}px; overflow:clip; position:relative; color:var(--paper);
       background: radial-gradient(120% 90% at 50% 0%, color-mix(in oklch, var(--night) 82%, var(--paper)) 0%, var(--night) 60%); }}
.axis {{ position:absolute; inset:0; }}
.ax {{ stroke:var(--paper); stroke-opacity:.18; stroke-width:3; }}
.dot {{ fill:var(--paper); fill-opacity:.32; }}
.ring {{ fill:none; stroke:var(--red); stroke-opacity:.45; stroke-width:3; }}
.red {{ fill:var(--red); }}
.tick {{ stroke:var(--paper); stroke-opacity:.35; stroke-width:3; }}
.lbl {{ font-family:'JetBrains Mono', monospace; font-weight:500; font-size:30px; letter-spacing:.12em; fill:var(--dim); text-anchor:middle; }}
.head {{ position:absolute; inset-block-start:230px; inset-inline:0; margin-inline:auto; max-inline-size:1000px; text-align:center; font-family:'Source Serif 4', Georgia, serif; }}
.head p {{ font-weight:700; font-size:104px; line-height:1.04; letter-spacing:-.015em; }}
.head p + p {{ margin-block-start:14px; font-weight:400; font-style:italic; font-size:66px; color:var(--dim); letter-spacing:0; }}
.head em {{ font-style:italic; color:var(--red); }}
</style></head><body>
{svg_axis(days)}
<div class="head"><p>Pierakstām secību.</p><p>Parādām, kad vārdi<br><em>nesakrīt</em> ar darbiem.</p></div>
</body></html>"""


def main():
    days = daily_counts()
    print(f"dienas={DAYS}, pozīcijas={sum(n for _, n, _ in days)}, pretrunu dienas={sum(1 for *_, k in days if k)}")
    src, png = OUT / "cover-v2.html", OUT / "cover-v2.png"
    src.write_text(html(days), encoding="utf-8")
    subprocess.run([sys.executable, str(ROOT / "scripts/render_shema.py"), str(src), str(png),
                    "--width", str(W), "--height", str(H)], check=True)
    im = Image.open(png)
    im.crop((0, SAFE_Y[0], W, SAFE_Y[1])).save(OUT / "cover-v2-crop-desktop.png")
    im.crop((MOBILE_X[0], 0, MOBILE_X[1], H)).save(OUT / "cover-v2-crop-mobile.png")


if __name__ == "__main__":
    main()
