"""Divi attēli Patreon oktobra pārskatam (2026-10): «Oktobris skaitļos» un «Kur aiziet atbalsts».
Stils un fonti — no pinned_2026_10_viz.py (tumšais panelis + krēmkrāsas papīrs), 1600×900.
Palaišana: .venv/Scripts/python.exe scripts/oneoff-content/patreon_2026_10_viz.py
— raksta docs/funding/patreon-2026-10-<n>-<slug>.html un renderē output/images/patreon/2026-10-<n>-<slug>.png."""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pinned_2026_10_viz as base  # noqa: E402

# DB 2026-10-19, created_at/detected_at/vote_date ≥ 2026-10-01: claims position=2044;
# context_notes daily_brief=18; saeima_votes=202; contradictions confirmed=1 → 3; tracked (≠inactive)=255
POSITIONS = 2044
BRIEFS = 18
VOTES = 202
CONTRADICTIONS = 3
POLITICIANS = 255

ROOT = base.ROOT
OUT_HTML = ROOT / "docs/funding"
OUT_PNG = ROOT / "output/images/patreon"
TOTAL = 2
nb = base.nb


def page(n, title, dek, body, css=""):
    # Fontu ceļi pinned skriptā ir relatīvi pret docs/tweet_bank — docs/funding ir tajā pašā dziļumā.
    return f"""<!doctype html>
<!-- atmina.lv Patreon oktobra pārskats, attēls {n}/{TOTAL}. Ģenerēts ar scripts/oneoff-content/patreon_2026_10_viz.py. -->
<html lang="lv"><head><meta charset="utf-8"><title>{title}</title><style>{base.CSS}{css}</style></head>
<body>
<section class="lead">
  <div class="brand">{base.LOGO}atmina.lv</div>
  <h1>{title}</h1>
  <p class="dek">{dek}</p>
  <div class="step num">{n} / {TOTAL}</div>
</section>
<section class="body">{body}</section>
</body></html>"""


pages = {}

# ---------------- 1. Oktobris skaitļos -----------------
TILES = [
    (POSITIONS, "politiķu pozīcijas ar saiti uz avotu"),
    (VOTES, "Saeimas balsojumi"),
    (BRIEFS, "dienas pārskati"),
    (CONTRADICTIONS, "publicētas pretrunas"),
]
NEW = [
    "Sadaļa «Balsojumi»: meklēšana un 100 sēdvietu attēls",
    "Katram likumprojektam sava lapa",
    "Pirmais «Atradums» — padziļināta izpēte",
]
css1 = """
.tiles { display:grid; grid-template-columns:repeat(4, 1fr); gap:28px; }
.tiles div { border-block-start:4px solid var(--red); padding-block-start:16px; }
.tiles b { display:block; font-family:var(--serif); font-weight:600; font-size:96px; line-height:0.95; letter-spacing:-0.02em; }
.tiles span { display:block; margin-block-start:12px; font-size:30px; line-height:1.25; color:var(--ink-2); }
.news { list-style:none; display:grid; gap:24px; border-block-start:2px solid var(--rule); padding-block-start:30px; }
.news h2 { font-family:var(--mono); font-weight:500; font-size:28px; letter-spacing:0.08em; color:var(--muted); }
.news li { display:grid; grid-template-columns:22px 1fr; gap:18px; align-items:baseline; font-family:var(--serif); font-size:40px; line-height:1.2; }
.news li::before { content:""; inline-size:14px; block-size:14px; border-radius:50%; background:var(--red); transform:translateY(-4px); }
.foot { margin-block-start:auto; display:flex; justify-content:space-between; align-items:baseline; gap:32px;
        font-size:30px; color:var(--ink-2); }
"""
tiles = "".join(f'<div><b class="num">{nb(v)}</b><span>{t}</span></div>' for v, t in TILES)
news = "".join(f"<li>{t}</li>" for t in NEW)
body1 = f"""<div class="tiles">{tiles}</div>
<ul class="news"><h2>JAUNS VIETNĒ</h2>{news}</ul>
<div class="foot"><span>Izsekojam <b class="num">{POLITICIANS}</b> politiķus</span><span>1.–19. oktobris</span></div>"""
pages["1-skaitli"] = page(1, "Oktobris skaitļos", "Kas paveikts mēneša pirmajās trīs nedēļās.", body1, css1)

# ---------------- 2. Kur aiziet atbalsts -----------------
COSTS = [
    ("Mākslīgā intelekta rīki", "Claude un Codex abonementi. Ar tiem katru dienu apstrādājam rakstus, tvītus un balsojumus un uzlabojam vietni.",
     "lielākā daļa", True),
    ("Domēns", "atmina.lv", "~12 € gadā", False),
    ("Hostings", "Cloudflare", "0 €", False),
]
css2 = """
.costs { list-style:none; display:grid; }
.costs li { display:grid; grid-template-columns:1fr auto; gap:12px 40px; align-items:baseline;
            border-block-start:2px solid var(--rule); padding-block:30px; }
.costs li.main { border-block-start:4px solid var(--red); }
.costs h2 { font-family:var(--serif); font-weight:700; font-size:50px; line-height:1.05; }
.costs p { grid-column:1; font-size:32px; line-height:1.3; color:var(--ink-2); max-inline-size:40ch; }
.costs .v { grid-column:2; grid-row:1 / span 2; align-self:center; font-family:var(--mono); font-weight:500; font-size:44px; white-space:nowrap; }
.costs .main .v { color:var(--red); }
.foot { margin-block-start:auto; border-block-start:2px solid var(--rule); padding-block-start:26px;
        display:flex; justify-content:space-between; align-items:baseline; gap:32px; }
.foot p { font-family:var(--serif); font-size:38px; line-height:1.2; }
.foot .url { font-family:var(--mono); font-weight:500; font-size:40px; color:var(--red); white-space:nowrap; }
"""
costs = "".join(
    f'<li class="{"main" if m else ""}"><h2>{t}</h2><span class="v num">{v}</span><p>{d}</p></li>'
    for t, d, v, m in COSTS)
body2 = f"""<ul class="costs">{costs}</ul>
<div class="foot"><p>Viss saturs bez maksas visiem.</p><span class="url">atbalsts.atmina.lv</span></div>"""
pages["2-izmaksas"] = page(2, "Kur aiziet atbalsts", "Atbalsts sedz izmaksas, nevis pērk saturu.", body2, css2)


def main():
    OUT_HTML.mkdir(parents=True, exist_ok=True)
    for slug, html in pages.items():
        h = OUT_HTML / f"patreon-2026-10-{slug}.html"
        h.write_text(html, encoding="utf-8")
        png = OUT_PNG / f"2026-10-{slug}.png"
        subprocess.run([sys.executable, str(ROOT / "scripts/render_shema.py"), str(h), str(png)], check=True)


if __name__ == "__main__":
    main()
