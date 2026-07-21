"""Re-render the @atmina_lv intro thread — atmina palette + polished compositions.

Replaces the v1/v2/v3 PNGs that used an off-brand pink accent.
Output: data/social/drafts/intro_thread_v4_*.png (5 images, 1200x675).
"""
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "social" / "drafts"
OUT.mkdir(parents=True, exist_ok=True)

# atmina palette (mirrors assets/style.css :root)
BG       = "#0d1014"
SURFACE  = "#161a22"
SURFACE2 = "#242838"
BORDER   = "#2d3148"
TEXT     = "#e2e4e9"
MUTED    = "#8b8fa3"
ACCENT   = "#90A4AE"   # steel blue-grey
CRIMSON  = "#B71C1C"   # primary accent
ORANGE   = "#f97316"   # secondary accent
SLATE    = "#37474F"

# Party colors (from src/generate.py PARTY_COLORS)
PARTY = {
    "JV":  "#3b82f6",
    "NA":  "#22c55e",
    "ZZS": "#84cc16",
    "PRO": "#a855f7",
    "LPV": "#ef4444",
    "AS":  "#06b6d4",
    "MMN": "#f97316",
}

BASE_STYLE = f"""
  @font-face {{ font-family: 'fallback'; src: local('Georgia'); }}
  html, body {{ margin:0; padding:0; background:{BG}; color:{TEXT};
    font-family: Inter, system-ui, -apple-system, sans-serif; }}
  .card {{ width:1200px; height:675px; box-sizing:border-box;
    position:relative; overflow:hidden; }}
  .serif {{ font-family: Georgia, 'Times New Roman', serif; }}
  .brand {{ color:{CRIMSON}; font-weight:800; font-size:22px; letter-spacing:-0.3px; }}
  .muted {{ color:{MUTED}; }}
  .eyebrow {{ color:{CRIMSON}; font-size:13px; font-weight:700;
    text-transform:uppercase; letter-spacing:3px; }}
"""

# -------------------------------------------------------------------- Tweet 1
T1_HTML = f"""
<!DOCTYPE html><html lang="lv"><head><meta charset="UTF-8"><style>{BASE_STYLE}
  .card {{ padding:72px 80px; display:flex; flex-direction:column;
    justify-content:space-between; }}
  .ghost {{ position:absolute; right:-60px; top:-40px; font-weight:900;
    font-size:340px; color:{SURFACE2}; line-height:1; letter-spacing:-10px;
    opacity:0.5; z-index:0; font-family:Georgia, serif; }}
  .content {{ position:relative; z-index:1; }}
  h1 {{ font-size:62px; line-height:1.05; margin:0; font-weight:800;
    letter-spacing:-1.5px; }}
  h1 .line1 {{ color:{TEXT}; }}
  h1 .line2 {{ color:{CRIMSON}; display:block; }}
  .divider {{ margin:40px 0 32px; height:2px; width:80px;
    background:{CRIMSON}; }}
  .stats {{ display:grid; grid-template-columns:repeat(4, auto); gap:56px;
    align-items:start; }}
  .stat-num {{ font-family:Georgia, serif; font-size:48px; font-weight:800;
    color:{TEXT}; letter-spacing:-1.5px; line-height:1; }}
  .stat-label {{ margin-top:8px; font-size:11px; color:{MUTED};
    text-transform:uppercase; letter-spacing:2.5px; font-weight:600; }}
  .stat-sub {{ font-size:10px; color:{MUTED}; margin-top:3px;
    letter-spacing:1.5px; text-transform:uppercase; }}
  .foot {{ display:flex; justify-content:space-between; align-items:flex-end;
    color:{MUTED}; font-size:14px; letter-spacing:1.5px; text-transform:uppercase; }}
</style></head><body><div class="card">
  <div class="ghost">a</div>
  <div class="content">
    <div class="eyebrow">Politiskā atmiņa · 2026</div>
    <h1 class="serif" style="margin-top:22px">
      <span class="line1">Politiķi aizmirst, ko solīja.</span>
      <span class="line2">Mēs neaizmirstam.</span>
    </h1>
    <div class="divider"></div>
    <div class="stats">
      <div><div class="stat-num">148</div><div class="stat-label">Politiķi</div></div>
      <div><div class="stat-num">1 159</div><div class="stat-label">Pozīcijas</div>
        <div class="stat-sub">mediji · X</div></div>
      <div><div class="stat-num">104</div><div class="stat-label">Saeimas balsojumi</div>
        <div class="stat-sub">pilns deputātu sadalījums</div></div>
      <div><div class="stat-num">19 233</div><div class="stat-label">Raksti · tvīti</div>
        <div class="stat-sub">atjaunots katru dienu</div></div>
    </div>
  </div>
  <div class="foot">
    <span>🧵 Kas ir atmina.lv</span><span class="brand">atmina.lv</span>
  </div>
</div></body></html>
"""

# -------------------------------------------------------------------- Tweet 2
T2_HTML = f"""
<!DOCTYPE html><html lang="lv"><head><meta charset="UTF-8"><style>{BASE_STYLE}
  .card {{ padding:72px 80px; display:flex; flex-direction:column;
    justify-content:space-between; }}
  .head {{ display:flex; justify-content:space-between; align-items:baseline;
    gap:40px; margin-bottom:10px; }}
  .head h1 {{ font-size:52px; margin:0; font-weight:700; letter-spacing:-0.8px; }}
  .topic-pill {{ display:inline-block; background:rgba(183,28,28,0.12);
    color:{CRIMSON}; font-size:13px; font-weight:800; padding:8px 16px;
    border-radius:999px; letter-spacing:2px; text-transform:uppercase;
    border:1px solid rgba(183,28,28,0.35); }}
  .vs-label {{ margin:40px 0 16px; font-size:12px; letter-spacing:4px;
    color:{MUTED}; text-transform:uppercase; font-weight:700; }}
  .panel {{ padding:22px 28px; border-radius:10px; background:{SURFACE};
    border:1px solid {BORDER}; position:relative; }}
  .panel + .panel {{ margin-top:14px; }}
  .panel .badge {{ display:inline-block; font-size:11px; font-weight:800;
    letter-spacing:2.5px; text-transform:uppercase; padding:4px 10px;
    border-radius:4px; margin-bottom:10px; }}
  .panel p {{ margin:0; font-size:25px; line-height:1.4; color:{TEXT}; }}
  .panel .date {{ font-size:12px; color:{MUTED}; margin-left:8px;
    letter-spacing:1.5px; text-transform:uppercase; font-weight:600; }}
  .panel.words {{ border-left:5px solid {ACCENT}; }}
  .panel.words .badge {{ background:rgba(144,164,174,0.15); color:{ACCENT}; }}
  .panel.action {{ border-left:5px solid {CRIMSON}; background:#1a1217; }}
  .panel.action .badge {{ background:{CRIMSON}; color:#fff; }}
  .panel.action p {{ font-weight:600; }}
  .foot {{ display:flex; justify-content:space-between; align-items:center;
    color:{MUTED}; font-size:15px; margin-top:20px; }}
  .foot strong {{ color:{TEXT}; font-weight:700; }}
</style></head><body><div class="card">
  <div class="head">
    <h1 class="serif">Daiga Mieriņa</h1>
    <span class="topic-pill">Krievija · sankcijas</span>
  </div>
  <div class="vs-label">Vārdos → Darbos</div>
  <div>
    <div class="panel words">
      <span class="badge">Vārdos</span><span class="date">1. apr. · Bučas samits</span>
      <p>"Kara noziegumiem nav noilguma un Krievijas pastrādātās zvērības
        nedrīkst aizmirst."</p>
    </div>
    <div class="panel action">
      <span class="badge">Darbos</span><span class="date">26. mar. · Saeima</span>
      <p><strong>Atturējās</strong> balsojumā par to, lai publicētu sarakstu
        ar Latvijas uzņēmumiem, kas turpināja tirgoties ar Krieviju.</p>
    </div>
  </div>
  <div class="foot">
    <span><strong>Bučā nosoda.</strong> Saeimā atturas.</span><span class="brand">atmina.lv</span>
  </div>
</div></body></html>
"""

# -------------------------------------------------------------------- Tweet 3
# Party-colored bars. Data: ISO W16 (11–17 apr.) top 10 by position count.
BARS = [
    ("Evika Siliņa",      "JV",  32),
    ("Ansis Pūpols",      "NA",  25),
    ("Baiba Braže",       "JV",  19),
    ("Viktors Valainis",  "ZZS", 14),
    ("Alvis Hermanis",    "MMN", 13),
    ("Ē. Stendzenieks",   "LPV", 13),
    ("Māris Mežals",      "LPV", 10),
    ("V. Kleinbergs",     "PRO", 10),
    ("Andris Kulbergs",   "AS",   9),
    ("Andris Sprūds",     "PRO",  9),
]
MAX = max(n for _, _, n in BARS)


def bar_rows():
    rows = []
    for name, party, n in BARS:
        pct = (n / MAX) * 100
        color = PARTY.get(party, ACCENT)
        rows.append(f"""
          <div class="bar-row">
            <div class="bar-name">{name} <span class="bar-party">{party}</span></div>
            <div class="bar-track">
              <div class="bar-fill" style="width:{pct:.1f}%; background:{color}"></div>
              <span class="bar-num">{n}</span>
            </div>
          </div>
        """)
    return "".join(rows)


T3_HTML = f"""
<!DOCTYPE html><html lang="lv"><head><meta charset="UTF-8"><style>{BASE_STYLE}
  .card {{ padding:60px 80px; display:flex; flex-direction:column; }}
  .head h1 {{ font-size:44px; margin:0; font-weight:700; letter-spacing:-0.8px; }}
  .head .sub {{ margin-top:8px; font-size:14px; color:{MUTED};
    letter-spacing:2px; text-transform:uppercase; font-weight:600; }}
  .bars {{ margin-top:28px; display:flex; flex-direction:column; gap:12px; }}
  .bar-row {{ display:grid; grid-template-columns:230px 1fr; gap:20px;
    align-items:center; }}
  .bar-name {{ font-size:18px; color:{TEXT}; text-align:right;
    font-weight:500; }}
  .bar-party {{ font-size:11px; color:{MUTED}; margin-left:6px;
    letter-spacing:1.2px; text-transform:uppercase; font-weight:700; }}
  .bar-track {{ position:relative; height:28px; background:{SURFACE};
    border-radius:4px; overflow:visible; }}
  .bar-fill {{ height:100%; border-radius:4px; transition:width 0.3s; }}
  .bar-num {{ position:absolute; right:-44px; top:50%;
    transform:translateY(-50%); color:{TEXT}; font-weight:800;
    font-size:18px; font-family:Georgia, serif; letter-spacing:-0.5px; }}
  .foot {{ display:flex; justify-content:space-between; align-items:center;
    color:{MUTED}; font-size:14px; margin-top:auto; padding-top:14px; }}
</style></head><body><div class="card">
  <div class="head">
    <h1 class="serif">Aktīvākie politiķi šonedēļ</h1>
    <div class="sub">Pozīciju skaits · 11.–17. apr. · ISO W16</div>
  </div>
  <div class="bars">{bar_rows()}</div>
  <div class="foot">
    <span>Top 10. Pilns saraksts un vēsture: atmina.lv/statistika</span>
    <span class="brand">atmina.lv</span>
  </div>
</div></body></html>
"""

# -------------------------------------------------------------------- Tweet 4
T4_HTML = f"""
<!DOCTYPE html><html lang="lv"><head><meta charset="UTF-8"><style>{BASE_STYLE}
  .card {{ padding:72px 80px; display:flex; flex-direction:column;
    justify-content:space-between; }}
  .head h1 {{ font-size:52px; margin:0; font-weight:700; letter-spacing:-0.8px;
    line-height:1.05; }}
  .head .accent {{ color:{CRIMSON}; }}
  .head .sub {{ margin-top:12px; font-size:13px; color:{MUTED};
    letter-spacing:3px; text-transform:uppercase; font-weight:600; }}
  .flow {{ display:grid; grid-template-columns: 1fr auto 320px;
    gap:36px; align-items:center; margin-top:28px; }}
  .sources {{ display:grid; grid-template-columns:1fr 1fr; gap:10px; }}
  .src {{ padding:14px 20px; background:{SURFACE}; border-radius:8px;
    border-left:4px solid {CRIMSON}; display:flex;
    justify-content:space-between; align-items:center; gap:16px; }}
  .src .name {{ font-size:19px; font-weight:700; color:{TEXT}; }}
  .src .tag {{ font-size:10px; color:{MUTED}; text-transform:uppercase;
    letter-spacing:1.5px; text-align:right; font-weight:600; }}
  .src.official {{ grid-column: 1 / -1; border-left-color:{ORANGE};
    background:linear-gradient(90deg, rgba(249,115,22,0.08) 0%, {SURFACE} 100%); }}
  .src.official .name {{ font-size:21px; }}
  .arrow {{ color:{CRIMSON}; font-size:56px; line-height:1; font-weight:800;
    flex:0 0 auto; }}
  .verify {{ padding:22px 24px; background:{SURFACE}; border:1px solid {BORDER};
    border-radius:12px; }}
  .verify .top {{ display:flex; justify-content:space-between;
    align-items:center; margin-bottom:16px; }}
  .verify .pill {{ display:inline-block; font-size:11px; color:{CRIMSON};
    background:rgba(183,28,28,0.10); border:1px solid rgba(183,28,28,0.35);
    padding:4px 10px; border-radius:999px; letter-spacing:2px;
    text-transform:uppercase; font-weight:800; }}
  .verify .label {{ color:{MUTED}; font-size:10px; text-transform:uppercase;
    letter-spacing:2px; font-weight:700; }}
  .verify ul {{ list-style:none; margin:0; padding:0;
    display:flex; flex-direction:column; gap:10px; }}
  .verify li {{ display:flex; align-items:center; gap:12px;
    font-size:18px; font-weight:600; color:{TEXT}; }}
  .verify li::before {{ content:"✓"; color:{ORANGE}; font-weight:900;
    font-size:15px; width:22px; height:22px; display:inline-flex;
    align-items:center; justify-content:center;
    background:rgba(249,115,22,0.12);
    border:1px solid rgba(249,115,22,0.35);
    border-radius:5px; flex:0 0 auto; }}
  .foot {{ display:flex; justify-content:space-between; align-items:center;
    color:{MUTED}; font-size:16px; }}
</style></head><body><div class="card">
  <div>
    <div class="head"><h1 class="serif">Katram ierakstam — <span class="accent">avots</span>.</h1>
      <div class="sub">Kas · Kad · Kur · Ko teica vai balsoja</div></div>
    <div class="flow">
      <div class="sources">
        <div class="src"><span class="name">LSM</span><span class="tag">lsm.lv</span></div>
        <div class="src"><span class="name">Delfi</span><span class="tag">delfi.lv</span></div>
        <div class="src"><span class="name">Latvijas Avīze</span><span class="tag">la.lv</span></div>
        <div class="src"><span class="name">TVNet</span><span class="tag">tvnet.lv</span></div>
        <div class="src"><span class="name">NRA</span><span class="tag">nra.lv</span></div>
        <div class="src"><span class="name">X</span><span class="tag">@deputāti</span></div>
        <div class="src official"><span class="name">🏛 Saeima</span>
          <span class="tag">Oficiālais balsojumu arhīvs · titania.saeima.lv</span></div>
      </div>
      <div class="arrow">→</div>
      <div class="verify">
        <div class="top">
          <span class="pill">atmina.lv</span>
          <span class="label">Katrs ieraksts</span>
        </div>
        <ul><li>Politiķis</li><li>Datums</li><li>Avota links</li>
          <li>Citāts vai balsojums</li></ul>
      </div>
    </div>
  </div>
  <div class="foot">
    <span>Nekas nav izdomāts. Tu vari pārbaudīt pats.</span>
    <span class="brand">atmina.lv</span>
  </div>
</div></body></html>
"""

# -------------------------------------------------------------------- Tweet 5
T5_HTML = f"""
<!DOCTYPE html><html lang="lv"><head><meta charset="UTF-8"><style>{BASE_STYLE}
  .card {{ padding:80px 96px; display:flex; flex-direction:column;
    justify-content:space-between; }}
  .ghost {{ position:absolute; font-size:440px; font-weight:900; color:{SURFACE2};
    top:-40px; right:-130px; letter-spacing:-16px; line-height:1; z-index:0;
    font-family:Georgia, serif; opacity:0.55; user-select:none; }}
  .main {{ position:relative; z-index:1; }}
  .tagline {{ font-size:82px; font-weight:800; line-height:1.04;
    letter-spacing:-2.5px; margin-top:24px; max-width:960px; }}
  .tagline .accent {{ color:{CRIMSON}; }}
  .meta {{ display:flex; gap:48px; margin-top:44px;
    color:{MUTED}; font-size:17px; font-weight:500; }}
  .meta .dot {{ color:{ORANGE}; font-weight:900; margin-right:6px; }}
  .foot {{ display:flex; justify-content:space-between; align-items:flex-end;
    position:relative; z-index:1; }}
  .cta {{ font-size:46px; font-weight:900; color:{TEXT}; letter-spacing:-1.2px; }}
  .cta .accent {{ color:{CRIMSON}; }}
  .cta .arr {{ color:{CRIMSON}; margin-right:10px; }}
  .tag {{ color:{MUTED}; font-size:13px; text-transform:uppercase;
    letter-spacing:3px; font-weight:600; }}
</style></head><body><div class="card">
  <div class="ghost">atmiņa</div>
  <div class="main">
    <div class="eyebrow">Politiskā atmiņa · 2026</div>
    <div class="tagline serif">Atceries to,<br>ko viņi cer,<br>
      <span class="accent">ka tu aizmirsīsi.</span></div>
    <div class="meta">
      <div><span class="dot">•</span>Bez maksas</div>
      <div><span class="dot">•</span>Bez reģistrācijas</div>
      <div><span class="dot">•</span>Latviešu valodā</div>
    </div>
  </div>
  <div class="foot">
    <div class="cta"><span class="arr">→</span><span class="accent">atmina.lv</span></div>
    <div class="tag">Skaties · Salīdzini · Dalies</div>
  </div>
</div></body></html>
"""


def render(html, out_name):
    out_path = OUT / out_name
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page(viewport={"width": 1200, "height": 675})
        p.set_content(html, wait_until="domcontentloaded")
        p.screenshot(path=str(out_path),
                     clip={"x": 0, "y": 0, "width": 1200, "height": 675})
        b.close()
    return out_path


if __name__ == "__main__":
    for name, html in [
        ("intro_thread_v4_t1_hero.png",      T1_HTML),
        ("intro_thread_v4_t2_mierina.png",   T2_HTML),
        ("intro_thread_v4_t3_stats.png",     T3_HTML),
        ("intro_thread_v4_t4_avoti.png",     T4_HTML),
        ("intro_thread_v4_t5_cta.png",       T5_HTML),
    ]:
        print(f"rendering {name}...")
        render(html, name)
    print("all 5 v4 tweets rendered ->", OUT)
