"""Ģenerē 4 attēlus atmina.lv piespraustajam X ierakstam (2026-10): «Kā Atmiņa strādā», «Kas jauns», «Kas plānā», «Ko vēl varam uzbūvēt».
Katrs attēls ir savā tvītā, 16:9, telefonā ~600 px plats — tāpēc teksts ≥30 px, skaitļi ≥80 px (1600×900).
Stils pēc src/graphics/templates/izpete-shema.html + good-css + dataviz.
Palaišana: .venv/Scripts/python.exe scripts/oneoff-content/pinned_2026_10_viz.py
— raksta docs/tweet_bank/2026-10-19-pinned-<n>-<slug>.html un renderē output/images/threads/2026-10-19-pinned-<n>-<slug>.png."""
import subprocess
import sys
from pathlib import Path

# DB 2026-10-19: claims position=9815; contradictions confirmed=1 → 29, withdrawn (-1) → 3;
# tracked_politicians tracked=226; documents=124 575; saeima_votes=8 407;
# saeima_debate_speeches=9 304; saeima_questions=402
POSITIONS = 9815
CONTRADICTIONS_CONFIRMED = 29
CONTRADICTIONS_WITHDRAWN = 3
POLITICIANS = 226
DOCUMENTS = 124575
SAEIMA_VOTES = 8407
DEBATE_SPEECHES = 9304
QUESTIONS = 402

ROOT = Path(__file__).resolve().parents[2]
OUT_HTML = ROOT / "docs/tweet_bank"
OUT_PNG = ROOT / "output/images/threads"
DAY = "2026-10-19"
TOTAL = 4
F = "../../output/atmina/assets/fonts/"


def nb(n):  # 124 575 ar šauru nedalāmu atstarpi
    return f"{n:,}".replace(",", " ")


CSS = f"""
@font-face {{ font-family:'Source Serif 4'; src:url('{F}source-serif-4-normal-latin-ext.woff2') format('woff2'); font-weight:200 900; }}
@font-face {{ font-family:'Source Serif 4'; src:url('{F}source-serif-4-normal-latin.woff2') format('woff2'); font-weight:200 900; }}
@font-face {{ font-family:'Source Serif 4'; font-style:italic; src:url('{F}source-serif-4-italic-latin-ext.woff2') format('woff2'); font-weight:200 900; }}
@font-face {{ font-family:'Source Serif 4'; font-style:italic; src:url('{F}source-serif-4-italic-latin.woff2') format('woff2'); font-weight:200 900; }}
@font-face {{ font-family:'JetBrains Mono'; src:url('{F}jetbrains-mono-500-latin-ext.woff2') format('woff2'); font-weight:500; }}
@font-face {{ font-family:'JetBrains Mono'; src:url('{F}jetbrains-mono-500-latin.woff2') format('woff2'); font-weight:500; }}

*, *::before, *::after {{ box-sizing:border-box; min-width:0; margin:0; padding:0; }}
:root {{
  --paper: oklch(96.4% 0.015 90);
  --ink: oklch(22.4% 0.014 82);
  --ink-2: color-mix(in oklch, var(--ink) 80%, var(--paper));
  --night: oklch(27% 0.055 265);
  --muted: oklch(50.9% 0.035 88);
  --rule: oklch(83.7% 0.037 89);
  --red: oklch(50.2% 0.189 27);          /* sarkana — akcents: soļu numuri, svarīgais */
  --on-night: oklch(96% 0.015 90);
  --on-night-muted: color-mix(in oklch, var(--on-night) 68%, var(--night));
  --on-night-rule: color-mix(in oklch, var(--on-night) 20%, transparent);
  --serif: 'Source Serif 4', Georgia, serif;
  --mono: 'JetBrains Mono', ui-monospace, monospace;
  --sans: "Segoe UI", Roboto, sans-serif;
  font-synthesis: none; -webkit-font-smoothing: antialiased; text-wrap: pretty;
}}
body {{ inline-size:1600px; block-size:900px; background:var(--paper); color:var(--ink); font-family:var(--sans);
       display:grid; grid-template-columns:400px 1fr; overflow:clip; }}
.num {{ font-variant-numeric: lining-nums tabular-nums; }}

.lead {{ background:var(--night); color:var(--on-night); padding:48px 44px 44px; display:flex; flex-direction:column; gap:34px; }}
.brand {{ display:flex; align-items:center; gap:14px; font-family:var(--serif); font-weight:700; font-size:34px; }}
.brand svg {{ flex:none; inline-size:42px; block-size:42px; }}
.lead h1 {{ font-family:var(--serif); font-weight:700; font-size:68px; line-height:1.02; letter-spacing:-0.015em; text-wrap:balance; }}
.lead .dek {{ font-family:var(--serif); font-size:32px; line-height:1.3; color:var(--on-night-muted); }}
.lead .step {{ margin-block-start:auto; border-block-start:1px solid var(--on-night-rule); padding-block-start:22px;
              font-family:var(--mono); font-weight:500; font-size:30px; letter-spacing:0.08em; color:var(--on-night-muted); }}

.body {{ padding:56px 48px 48px 52px; display:flex; flex-direction:column; gap:40px; }}
"""

LOGO = ('<svg viewBox="0 0 64 64" aria-hidden="true"><circle cx="27" cy="27" r="17" fill="none" stroke="#f7f3e8" stroke-width="5.5"/>'
        '<line x1="40.5" y1="40.5" x2="52" y2="52" stroke="#f7f3e8" stroke-width="5.5" stroke-linecap="round"/>'
        '<circle cx="27" cy="27" r="6" fill="#EF5350"/></svg>')


def page(n, title, dek, body, css=""):
    dek_html = f'<p class="dek">{dek}</p>' if dek else ""
    return f"""<!doctype html>
<!-- atmina.lv piespraustais ieraksts, attēls {n}/{TOTAL}. Ģenerēts ar scripts/oneoff-content/pinned_2026_10_viz.py. -->
<html lang="lv"><head><meta charset="utf-8"><title>{title}</title><style>{CSS}{css}</style></head>
<body>
<section class="lead">
  <div class="brand">{LOGO}atmina.lv</div>
  <h1>{title}</h1>
  {dek_html}
  <div class="step num">{n} / {TOTAL}</div>
</section>
<section class="body">{body}</section>
</body></html>"""


pages = {}

# ---------------- 1. Kā Atmiņa strādā -----------------
STEPS = [
    ("Ievācam", "Ziņas, politiķu X konti, «Latvijas Vēstnesis», Saeimas balsojumi"),
    ("Izvelkam pozīciju", "Kas, par ko, ko tieši teica. Bez saites uz avotu neglabājam"),
    ("Salīdzinām", "Ar politiķa agrākajiem izteikumiem un balsojumiem"),
    ("Mēģinām apgāzt", "Katru iespējamo pretrunu pārbaudām. Lielākā daļa neiztur"),
    ("Cilvēks izlasa", "Automātiski nekas netiek publicēts"),
]
css1 = """
.flow { list-style:none; display:grid; grid-template-columns:repeat(5, 1fr); gap:30px; }
.flow li { display:flex; flex-direction:column; gap:16px; position:relative; }
.flow .n { inline-size:64px; block-size:64px; border-radius:50%; display:grid; place-items:center;
           background:var(--red); color:var(--paper); font-family:var(--mono); font-weight:500; font-size:34px; position:relative; z-index:1; }
.flow li:not(:last-child)::after { content:""; position:absolute; inset-block-start:31px; inset-inline:64px -30px;
           border-block-start:2px solid color-mix(in oklch, var(--red) 45%, var(--paper)); }
.flow h2 { font-family:var(--serif); font-weight:700; font-size:34px; line-height:1.08; }
.flow p { font-size:30px; line-height:1.28; color:var(--ink-2); hyphens:manual; text-wrap:balance; }
.funnel { margin-block-start:auto; border-block-start:2px solid var(--rule); padding-block-start:30px;
          display:grid; grid-template-columns:auto auto auto auto auto; justify-content:space-between; align-items:start; }
.funnel b { display:block; font-family:var(--serif); font-weight:600; font-size:88px; line-height:0.95; letter-spacing:-0.02em; }
.funnel span { display:block; margin-block-start:8px; font-size:30px; color:var(--ink-2); }
.funnel .end b { color:var(--red); }
.funnel .ar { font-family:var(--serif); font-size:64px; line-height:1.2; color:var(--muted); }
"""
items = "".join(f'<li><span class="n">{i}</span><h2>{t}</h2><p>{d}</p></li>' for i, (t, d) in enumerate(STEPS, 1))
body1 = f"""
<ol class="flow">{items}</ol>
<div class="funnel num">
  <div><b>{nb(DOCUMENTS)}</b><span>dokumenti</span></div>
  <div class="ar" aria-hidden="true">→</div>
  <div><b>{nb(POSITIONS)}</b><span>pozīcijas</span></div>
  <div class="ar" aria-hidden="true">→</div>
  <div class="end"><b>{CONTRADICTIONS_CONFIRMED}</b><span>apstiprinātas pretrunas</span></div>
</div>
"""
pages["1-ka-strada"] = page(1, "Kā Atmiņa strādā",
                            "Datums, pozīcija, saite uz avotu. Mēs nevērtējam — pierakstām secību.", body1, css1)

# ---------------- 2. Kas jauns -----------------
TILES = [
    (DEBATE_SPEECHES, "runas Saeimas debatēs"),
    (QUESTIONS, "jautājumi un pieprasījumi ministriem"),
    (POLITICIANS, "politiķi"),
    (SAEIMA_VOTES, "Saeimas balsojumi"),
]
NEWS = [
    "Deputātu profilos cilne «Saeimā»: amati, runas, jautājumi",
    "Profili visiem 15. Saeimā ievēlētajiem",
    "Vēlēšanu rezultāti pēc CVK datiem",
    "Faktu bloks: izglītība, darbavietas, amatu vēsture",
    f"Kļūdaini atzītu pretrunu neizdzēšam — paliek lapa ar paskaidrojumu (līdz&nbsp;šim&nbsp;{CONTRADICTIONS_WITHDRAWN})",
]
css2 = """
.tiles { display:grid; grid-template-columns:repeat(4, 1fr); gap:28px; }
.tiles div { border-block-start:4px solid var(--red); padding-block-start:16px; }
.tiles b { display:block; font-family:var(--serif); font-weight:600; font-size:88px; line-height:0.95; letter-spacing:-0.02em; }
.tiles span { display:block; margin-block-start:10px; font-size:30px; line-height:1.25; color:var(--ink-2); }
.news { list-style:none; display:grid; gap:24px; border-block-start:2px solid var(--rule); padding-block-start:30px; }
.news li { display:grid; grid-template-columns:22px 1fr; gap:18px; align-items:baseline; font-size:36px; line-height:1.25; }
.news li::before { content:""; inline-size:14px; block-size:14px; border-radius:50%; background:var(--red); transform:translateY(-3px); }
"""
tiles = "".join(f'<div><b class="num">{nb(v)}</b><span>{t}</span></div>' for v, t in TILES)
news = "".join(f"<li>{t}</li>" for t in NEWS)
body2 = f'<div class="tiles">{tiles}</div><ul class="news">{news}</ul>'
pages["2-jaunumi"] = page(2, "Kas jauns", "", body2, css2)

# ---------------- 3. Kas plānā -----------------
PLAN = [
    "Kad sanāks 15. Saeima — jauno deputātu balsojumi, amati, runas un jautājumi profilos",
    "Kad būs jaunā valdība — pārslēgsim koalīcijas un opozīcijas dalījumu",
    "Jaunās valdības solījumus salīdzināsim ar to, ko tie paši cilvēki teikuši un kā balsojuši agrāk",
]
css3 = """
.plan { list-style:none; display:grid; gap:44px; }
.plan li { display:grid; grid-template-columns:90px 1fr; gap:28px; align-items:start; }
.plan .n { font-family:var(--serif); font-weight:600; font-size:96px; line-height:0.8; color:var(--red); }
.plan p { font-family:var(--serif); font-size:46px; line-height:1.22; }
.foot { margin-block-start:auto; border-block-start:2px solid var(--rule); padding-block-start:26px;
        display:flex; justify-content:space-between; align-items:baseline; gap:32px; }
.foot p { font-size:32px; line-height:1.3; color:var(--ink-2); max-inline-size:44ch; }
.foot .url { font-family:var(--mono); font-weight:500; font-size:40px; color:var(--ink); white-space:nowrap; }
"""
plan = "".join(f'<li><span class="n num">{i}</span><p>{t}</p></li>' for i, t in enumerate(PLAN, 1))
body3 = f"""<ol class="plan">{plan}</ol>
<div class="foot"><p>Pamanījāt kļūdu? Rakstiet — izlabosim un pierakstīsim, ko labojām.</p><span class="url">atmina.lv</span></div>"""
pages["3-plans"] = page(3, "Kas plānā", "", body3, css3)

# ---------------- 4. Ko vēl varam uzbūvēt (→ Patreon) -----------------
MORE = [
    ("Pašvaldības", "Domju sēdes, balsojumi un deputātu solījumi&nbsp;— ne tikai Saeimā"),
    ("Video", "Interviju un debašu atšifrējumi, katrs izteikums ar laika atzīmi. Apstrāde mākoņpakalpojumos vai savos serveros"),
    ("Videopārskati", "Dienas un nedēļas svarīgākais īsā video"),
]
css4 = """
.more { list-style:none; display:grid; gap:0; }
.more li { display:grid; grid-template-columns:380px 1fr; gap:36px; align-items:baseline;
           border-block-start:2px solid var(--rule); padding-block:30px; }
.more li:first-child { border-block-start:4px solid var(--red); }
.more h2 { font-family:var(--serif); font-weight:700; font-size:50px; line-height:1.05; text-wrap:balance; }
.more p { font-size:34px; line-height:1.3; color:var(--ink-2); text-wrap:pretty; }
.foot { margin-block-start:auto; border-block-start:2px solid var(--rule); padding-block-start:26px;
        display:flex; justify-content:space-between; align-items:baseline; gap:32px; }
.foot p { font-family:var(--serif); font-size:38px; line-height:1.2; white-space:nowrap; }
.foot .url { font-family:var(--mono); font-weight:500; font-size:40px; color:var(--red); white-space:nowrap; }
"""
more = "".join(f"<li><h2>{t}</h2><p>{d}</p></li>" for t, d in MORE)
body4 = f"""<ul class="more">{more}</ul>
<div class="foot"><p>Bez maksas visiem. Kods ir atvērts.</p><span class="url">atbalsts.atmina.lv</span></div>"""
pages["4-atbalsts"] = page(4, "Ko vēl varam uzbūvēt", "Ja būs vairāk resursu", body4, css4)


def main():
    OUT_HTML.mkdir(parents=True, exist_ok=True)
    for slug, html in pages.items():
        h = OUT_HTML / f"{DAY}-pinned-{slug}.html"
        h.write_text(html, encoding="utf-8")
        png = OUT_PNG / f"{DAY}-pinned-{slug}.png"
        subprocess.run([sys.executable, str(ROOT / "scripts/render_shema.py"), str(h), str(png)], check=True)


if __name__ == "__main__":
    main()
