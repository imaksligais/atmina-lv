"""Patreon vāka varianti v3–v5 (2026-10-19), salīdzinājumam ar v2 (patreon_cover_2026_10.py) un Astras variantu.

v3 «pusloks» (advisor ideja): 15. Saeimas 100 sēdvietas tajā pašā secībā un ģeometrijā kā saeima.html
   (src.render.saeima._build_context); sēdvietas gaišums ~ √(pozīcijas 90 dienās), sarkana = deputātam ir pretruna.
   Bez vārdiem un frakciju krāsām.
v4 «vārdi / darbi»: pēdējās 60 rutīnas dienas — pozīcijas virs ass, Saeimas balsojumi zem ass.
v5 «tēmu žurnāls»: pēdējās 7 rutīnas dienas, katrai — biežākās tēmas (33 kanoniskās grupas), izgaist uz labo.

Apgriešanas zonas — sk. patreon_cover_2026_10.py. Raksta output/images/patreon/cover-v{3,4,5}.{html,png} + -crop-{desktop,mobile}.png.
Palaišana: .venv/Scripts/python.exe scripts/oneoff-content/patreon_cover_variants_2026_10.py"""
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
from src.render.saeima import ELECTED_PATH, RESULTS_PATH, _build_context  # noqa: E402

OUT = ROOT / "output/images/patreon"
W, H = 2500, 1000
SAFE_Y = (200, 800)
MOBILE_X = (750, 1750)
END = date(2026, 10, 19)
F = "../../atmina/assets/fonts/"

HEAD = f"""@font-face {{ font-family:'Source Serif 4'; src:url('{F}source-serif-4-normal-latin-ext.woff2') format('woff2'); font-weight:200 900; }}
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
  --serif: 'Source Serif 4', Georgia, serif;
  --mono: 'JetBrains Mono', ui-monospace, monospace;
  font-synthesis:none; -webkit-font-smoothing:antialiased;
}}
body {{ inline-size:{W}px; block-size:{H}px; overflow:clip; position:relative; color:var(--paper);
       background: radial-gradient(120% 90% at 50% 0%, color-mix(in oklch, var(--night) 82%, var(--paper)) 0%, var(--night) 60%); }}
svg.full {{ position:absolute; inset:0; }}
.lbl {{ font-family:var(--mono); font-weight:500; font-size:30px; letter-spacing:.12em; fill:var(--dim); }}
"""


def page(n, css, body):
    return f"""<!doctype html>
<!-- atmina.lv Patreon vāks v{n}. Ģenerēts ar scripts/oneoff-content/patreon_cover_variants_2026_10.py. -->
<html lang="lv"><head><meta charset="utf-8"><style>{HEAD}{css}</style></head><body>{body}</body></html>"""


def routine_days(db, n):
    start = END - timedelta(days=n - 1)
    days = [start + timedelta(days=i) for i in range(n)]
    # LV kolonnas; rutīnas diena sākas 05:00 (src.briefs.routine_day_window) → nobīde −5 h
    pos = dict(db.execute("SELECT date(created_at,'-5 hours'), count(*) FROM claims WHERE claim_type='position' "
                          "AND date(created_at,'-5 hours') BETWEEN ? AND ? GROUP BY 1", (str(start), str(END))))
    votes = dict(db.execute("SELECT vote_date, count(*) FROM saeima_votes WHERE vote_date BETWEEN ? AND ? GROUP BY 1",
                            (str(start), str(END))))
    return days, pos, votes


# ---------------- v3 pusloks -----------------
def v3(db):
    ctx = _build_context(db, ELECTED_PATH, RESULTS_PATH)
    seats = ctx["seats"]
    assert len(seats) == 100, len(seats)
    peak = max((s["pos90"] or 0) for s in seats) or 1
    # saeima.py koordinātas: x ∈ [-200, 200], y ∈ [-200, 0] → mērogs 1,9, centrs (1250, 610); virsraksts zem pusloka
    k, cx, cy = 1.9, 1250, 610
    dots = []
    for s in seats:
        x, y = cx + s["x"] * k, cy + s["y"] * k
        if s["ctr"]:
            dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="18" class="red"/>')
        else:
            op = 0.12 + 0.88 * math.sqrt((s["pos90"] or 0) / peak)
            dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="18" fill="var(--paper)" fill-opacity="{op:.2f}"/>')
    css = """
.red { fill:var(--red); }
.head { position:absolute; inset-block-start:645px; inset-inline:0; text-align:center; font-family:var(--serif); }
.head p { font-weight:700; font-size:68px; line-height:1.05; letter-spacing:-.01em; }
.head p + p { margin-block-start:6px; font-weight:400; font-style:italic; font-size:50px; color:var(--dim); }
"""
    body = (f'<svg class="full" viewBox="0 0 {W} {H}" aria-hidden="true">{"".join(dots)}</svg>'
            '<div class="head"><p>Katrs vārds. Katrs balsojums.</p><p>Pierakstīts.</p></div>')
    print(f"v3: sēdvietas={len(seats)}, ar pretrunu={sum(1 for s in seats if s['ctr'])}, max pos90={peak}")
    return page(3, css, body)


# ---------------- v4 vārdi / darbi -----------------
def v4(db):
    days, pos, votes = routine_days(db, 60)
    x0, x1, y = 1080, 2340, 520
    step = (x1 - x0) / (len(days) - 1)
    pmax, vmax = max(pos.values()), max(votes.values())
    bw = step * 0.62
    parts = [f'<line x1="{x0 - 40}" y1="{y}" x2="{x1 + 40}" y2="{y}" class="ax"/>']
    for i, d in enumerate(days):
        x = x0 + i * step - bw / 2
        p, v = pos.get(str(d), 0), votes.get(str(d), 0)
        if p:
            h = 6 + 230 * math.sqrt(p / pmax)
            parts.append(f'<rect x="{x:.1f}" y="{y - 8 - h:.1f}" width="{bw:.1f}" height="{h:.1f}" rx="{bw / 2:.1f}" class="up"/>')
        if v:
            h = 6 + 230 * math.sqrt(v / vmax)
            parts.append(f'<rect x="{x:.1f}" y="{y + 8:.1f}" width="{bw:.1f}" height="{h:.1f}" rx="{bw / 2:.1f}" class="down"/>')
    css = """
.ax { stroke:var(--paper); stroke-opacity:.25; stroke-width:3; }
.up { fill:var(--paper); fill-opacity:.55; }
.down { fill:var(--red); fill-opacity:.9; }
.word { position:absolute; font-family:var(--serif); font-weight:700; font-size:96px; line-height:1; }
.word small { display:block; margin-block-start:10px; font-family:var(--mono); font-weight:500; font-size:28px; letter-spacing:.1em; color:var(--dim); }
.w1 { inset-block-start:330px; inset-inline-start:780px; }
.w2 { inset-block-start:560px; inset-inline-start:780px; color:var(--red); }
"""
    # vārdi pa kreisi virs ass, darbi pa kreisi zem ass — abi mobilajā joslā (x ≥ 750)
    body = (f'<svg class="full" viewBox="0 0 {W} {H}" aria-hidden="true">{"".join(parts)}</svg>'
            '<div class="word w1">Vārdi<small>POZĪCIJAS</small></div>'
            '<div class="word w2">Darbi<small>BALSOJUMI</small></div>')
    print(f"v4: dienas={len(days)}, pozīcijas={sum(pos.values())}, balsojumi={sum(votes.values())}")
    return page(4, css, body)


# ---------------- v5 tēmu žurnāls -----------------
def v5(db):
    end = END
    rows = []
    d = end
    while len(rows) < 6:
        lo = str(d)
        topics = [t for t, _ in db.execute(
            "SELECT topic, count(*) n FROM claims WHERE claim_type='position' AND date(created_at,'-5 hours') = ? "
            "AND topic IS NOT NULL GROUP BY topic ORDER BY n DESC, topic LIMIT 6", (lo,))]
        if topics:
            rows.append((d, topics))
        d -= timedelta(days=1)
    lines = []
    for i, (d, topics) in enumerate(rows):
        frag = "".join(f'<span style="opacity:{max(0.12, 1 - j * 0.17):.2f}">{t}</span>' for j, t in enumerate(topics))
        lines.append(f'<li><time>{d.day:02d}.{d.month:02d}.</time><p>{frag}</p></li>')
    css = """
.log { position:absolute; inset-block-start:250px; inset-inline-start:760px; inset-inline-end:0; list-style:none; display:grid; gap:20px; }
.log li { display:grid; grid-template-columns:150px 1fr; gap:32px; align-items:baseline; white-space:nowrap; }
.log time { font-family:var(--mono); font-weight:500; font-size:34px; letter-spacing:.06em; color:var(--red); }
.log p { font-family:var(--serif); font-size:52px; line-height:1.1; overflow:clip; }
.log span + span::before { content:"·"; margin-inline:.45em; color:var(--dim); }
.log li:first-child p { font-weight:700; }
.cap { position:absolute; inset-block-start:735px; inset-inline-start:760px; font-family:var(--mono); font-weight:500; font-size:30px; letter-spacing:.12em; color:var(--dim); }
.fade { position:absolute; inset-block:0; inset-inline-end:0; inline-size:900px;
        background:linear-gradient(to right, transparent, var(--night) 85%); }
"""
    body = (f'<ol class="log">{"".join(lines)}</ol><div class="fade"></div>'
            '<p class="cap">PAR KO RUNĀ POLITIĶI · KATRU DIENU · ATMINA.LV</p>')
    print(f"v5: dienas={len(rows)}")
    return page(5, css, body)


# ---------------- līmeņa attēls (460×200, renderē 2×) -----------------
def tier(db):
    ctx = _build_context(db, ELECTED_PATH, RESULTS_PATH)
    seats = ctx["seats"]
    assert len(seats) == 100, len(seats)
    peak = max((s["pos90"] or 0) for s in seats) or 1
    k, cx, cy = 0.82, 700, 300  # pusloks labajā pusē
    dots = []
    for s in seats:
        x, y = cx + s["x"] * k, cy + s["y"] * k
        if s["ctr"]:
            dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="8" class="red"/>')
        else:
            op = 0.14 + 0.86 * math.sqrt((s["pos90"] or 0) / peak)
            dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="8" fill="var(--paper)" fill-opacity="{op:.2f}"/>')
    css = """
body { inline-size:920px; block-size:400px; }
.red { fill:var(--red); }
.t { position:absolute; inset-block-start:118px; inset-inline-start:56px; font-family:var(--serif); }
.t p { font-weight:700; font-size:64px; line-height:1; letter-spacing:-.01em; }
.t p + p { margin-block-start:16px; font-weight:400; font-style:italic; font-size:32px; line-height:1.2; color:var(--dim); }
.rule { position:absolute; inset-block-start:96px; inset-inline-start:58px; inline-size:72px; block-size:5px; background:var(--red); border-radius:3px; }
"""
    body = (f'<svg class="full" viewBox="0 0 920 400" aria-hidden="true">{"".join(dots)}</svg>'
            '<div class="rule"></div><div class="t"><p>Atbalstītājs</p><p>Uztur Atmiņu<br>brīvi pieejamu visiem.</p></div>')
    return page("-tier", css, body)


def main():
    db = sqlite3.connect(PRODUCTION_DB_PATH)
    db.row_factory = sqlite3.Row
    for n, fn in [(3, v3), (4, v4), (5, v5)]:
        src, png = OUT / f"cover-v{n}.html", OUT / f"cover-v{n}.png"
        src.write_text(fn(db), encoding="utf-8")
        subprocess.run([sys.executable, str(ROOT / "scripts/render_shema.py"), str(src), str(png),
                        "--width", str(W), "--height", str(H)], check=True, stdout=subprocess.DEVNULL)
        im = Image.open(png)
        im.crop((0, SAFE_Y[0], W, SAFE_Y[1])).save(OUT / f"cover-v{n}-crop-desktop.png")
        im.crop((MOBILE_X[0], 0, MOBILE_X[1], H)).save(OUT / f"cover-v{n}-crop-mobile.png")
    src = OUT / "tier-v3.html"
    src.write_text(tier(db), encoding="utf-8")
    subprocess.run([sys.executable, str(ROOT / "scripts/render_shema.py"), str(src), str(OUT / "tier-v3.png"),
                    "--width", "920", "--height", "400"], check=True, stdout=subprocess.DEVNULL)


if __name__ == "__main__":
    main()
