"""Ģenerē UR datu vizuāļu HTML failus (docs/tweet_bank/2026-10-19-ur-viz-*.html): 4 attēli 1600×900, to mobilās versijas
(*-mob, 1080 px plats, augstums pēc satura) un vāks (0-vaks). Skaitļi tikai no tua_investoru_valstis_2026_dati.json
(kopskaitļi, bez vārdiem). Palaišana: .venv/Scripts/python.exe scripts/oneoff-content/tua_investoru_valstis_2026_viz.py [--render]
— ar --render uzreiz renderē visus PNG (output/images/analizes/ + desktop arī output/images/threads/)."""
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = json.loads((ROOT / "scripts/oneoff-content/tua_investoru_valstis_2026_dati.json").read_text(encoding="utf-8"))
OUT = ROOT / "docs/tweet_bank"
F = "../../output/atmina/assets/fonts/"
SRC = "Avots: UR izraksti un atvērtie dati (17.10.2026.); atmina.lv aprēķins"


def nb(n):  # 50 000 ar nedalāmu atstarpi
    return f"{n:,}".replace(",", "\u202f")


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
  --ink-2: color-mix(in oklch, var(--ink) 78%, var(--paper));
  --night: oklch(27% 0.055 265);
  --muted: oklch(50.9% 0.035 88);
  --rule: oklch(83.7% 0.037 89);
  --cell: oklch(89% 0.03 88);
  --red: oklch(50.2% 0.189 27);
  /* datu krāsas (dataviz validators: PASS uz #f7f3e8) */
  --pase: oklch(55.9% 0.142 46);    /* oranža — ārvalstu pase */
  --kods: oklch(47.3% 0.124 259);   /* zila — jaunā parauga kods / SIA / organizatora modelis */
  --vecs: oklch(56.8% 0.102 172);   /* zaļganzila — vecā parauga kods / ģimenes uzņēmumi */
  --on-night: oklch(96% 0.015 90);
  --on-night-muted: color-mix(in oklch, var(--on-night) 64%, var(--night));
  --on-night-rule: color-mix(in oklch, var(--on-night) 20%, transparent);
  --serif: 'Source Serif 4', Georgia, serif;
  --mono: 'JetBrains Mono', ui-monospace, monospace;
  --sans: "Segoe UI", Roboto, sans-serif;
  font-synthesis: none; -webkit-font-smoothing: antialiased; text-wrap: pretty;
}}
body {{ inline-size:1600px; block-size:900px; background:var(--paper); color:var(--ink); font-family:var(--sans);
       display:grid; grid-template-columns:540px 1fr; overflow:clip; }}
.label {{ font-family:var(--mono); font-weight:500; font-size:13px; letter-spacing:0.14em; text-transform:uppercase; }}
.num {{ font-variant-numeric: lining-nums tabular-nums; }}

.lead {{ background:var(--night); color:var(--on-night); padding:46px 50px 40px; display:flex; flex-direction:column; gap:22px; position:relative; }}
.brand {{ display:flex; align-items:center; gap:10px; font-family:var(--serif); font-weight:700; font-size:22px; }}
.brand svg {{ flex:none; inline-size:28px; block-size:28px; }}
.brand .step {{ margin-inline-start:auto; font-family:var(--mono); font-weight:500; font-size:13px; letter-spacing:0.12em; color:var(--on-night-muted); }}
.lead .label {{ color:color-mix(in oklch, var(--red), white 38%); }}
.lead h1 {{ font-family:var(--serif); font-weight:700; font-size:44px; line-height:1.08; letter-spacing:-0.01em; text-wrap:balance; }}
.lead .dek {{ font-size:18px; line-height:1.5; color:var(--on-night-muted); max-inline-size:40ch; }}
.big {{ margin-block-start:auto; border-block-start:1px solid var(--on-night-rule); padding-block-start:22px; }}
.big .v {{ font-family:var(--serif); font-weight:600; font-size:92px; line-height:0.95; letter-spacing:-0.02em; font-variant-numeric:lining-nums; }}
.big .v span {{ font-size:40px; color:var(--on-night-muted); font-weight:500; letter-spacing:0; }}
.big p {{ margin-block-start:12px; font-size:18px; line-height:1.45; color:var(--on-night-muted); max-inline-size:40ch; }}
.big p b {{ color:var(--on-night); font-weight:600; }}

.body {{ padding:44px 48px 30px 56px; display:flex; flex-direction:column; gap:26px; }}
.body h2 {{ font-family:var(--serif); font-size:28px; font-weight:700; line-height:1.15; }}
.body h2 small {{ display:block; font-family:var(--sans); font-size:17px; font-weight:400; color:var(--muted); margin-block-start:6px; }}
.key {{ display:flex; flex-wrap:wrap; gap:8px 28px; font-size:17px; color:var(--ink-2); }}
.key span {{ display:inline-flex; align-items:center; gap:9px; }}
.sw {{ display:inline-block; inline-size:16px; block-size:16px; border-radius:3px; background:var(--c); flex:none; }}
.hatch {{ background:
   repeating-linear-gradient(45deg, var(--c) 0 2px, transparent 2px 6px),
   color-mix(in oklch, var(--c) 34%, var(--paper)); }}

.note {{ display:flex; align-items:baseline; gap:16px; border-inline-start:4px solid var(--red); padding-inline-start:16px; }}
.note .label {{ color:var(--red); flex:none; }}
.note p {{ font-family:var(--serif); font-size:19px; line-height:1.4; }}
.foot {{ margin-block-start:auto; display:grid; gap:14px; }}
.src {{ color:var(--muted); font-family:var(--mono); font-size:12px; letter-spacing:0.06em; }}
"""

LOGO = ('<svg viewBox="0 0 64 64" aria-hidden="true"><circle cx="27" cy="27" r="17" fill="none" stroke="#f7f3e8" stroke-width="5.5"/>'
        '<line x1="40.5" y1="40.5" x2="52" y2="52" stroke="#f7f3e8" stroke-width="5.5" stroke-linecap="round"/>'
        '<circle cx="27" cy="27" r="6" fill="#EF5350"/></svg>')


def page(n, kicker, h1, dek, big, body, css=""):
    return f"""<!doctype html>
<!-- UR investoru izpēte, vizuālis {n}/4. Ģenerēts ar scripts/oneoff-content/tua_investoru_valstis_2026_viz.py; stils pēc src/graphics/templates/izpete-shema.html + good-css + dataviz. -->
<html lang="lv"><head><meta charset="utf-8"><title>{h1}</title><style>{CSS}{css}</style></head>
<body>
<section class="lead">
  <div class="brand">{LOGO}atmina.lv<span class="step">{n} / 4</span></div>
  <div class="label">{kicker}</div>
  <h1>{h1}</h1>
  <p class="dek">{dek}</p>
  <div class="big">{big}</div>
</section>
<section class="body">{body}</section>
</body></html>"""


def foot(note_label, note):
    return f'<div class="foot"><div class="note"><span class="label">{note_label}</span><p>{note}</p></div><div class="src">{SRC}</div></div>'


K = D["kopa"]
KICK = "Izpēte · Uzņēmumu reģistrs"
DEK = (f"{K['uznemumi']} uzņēmumos vismaz trim cilvēkiem katram pieder daļas tieši par 50&nbsp;000&nbsp;€ vai 100&nbsp;000&nbsp;€. "
       "Ieguldījums uzņēmumā šādā apmērā ir viens no likumā paredzētajiem ceļiem uz termiņuzturēšanās atļauju (TUA).")

# ---------------- 1. kas-ir -----------------
JAUNS_TXT = "Kopš 2017. gada to saņem ikviens, kuru Latvijā reģistrē pirmo reizi, arī ārzemnieks bez TUA. Tāpēc šo cilvēku pilsonība nav zināma."
VECS_TXT = f"Tādus kodus piešķīra līdz 2017. gada 1. jūlijam. Šajā sarakstā tāds ir tikai {K['veca_parauga_kods']} cilvēkiem."
NAME_TXT = ("investoriem vārds Uzņēmumu reģistrā ierakstīts <strong>latviskā formā</strong>, kā raksta Latvijas pilsoņu un nepilsoņu vārdus. "
            "Ārzemnieku vārdus raksta kā pasē — arī tad, ja viņiem ir Latvijas personas kods.")
ROWS = 10
cells = []
order = [("pase", K["arvalstu_pase"]), ("kods", K["jauna_parauga_kods"]), ("vecs", K["veca_parauga_kodu"] if "veca_parauga_kodu" in K else K["veca_parauga_kods"])]
seq = [c for c, n in order for _ in range(n)]
cols = -(-len(seq) // ROWS)
for i, c in enumerate(seq):
    col, row = divmod(i, ROWS)
    cells.append(f'<i class="{c}" style="grid-column:{col+1};grid-row:{row+1}"></i>')
css1 = f"""
.waffle {{ display:grid; grid-template-columns:repeat({cols}, 21px); grid-auto-rows:21px; gap:2px; }}
.waffle i {{ border-radius:3px; background:var(--c); }}
.pase {{ --c:var(--pase); }} .kods {{ --c:var(--kods); }} .vecs {{ --c:var(--vecs); }}
.parts {{ display:grid; grid-template-columns: {K['arvalstu_pase']}fr {K['jauna_parauga_kods']}fr {K['veca_parauga_kods']*3}fr; gap:0 3px; inline-size:{cols*23-2}px; }}
.parts > div {{ border-block-start:2px solid var(--c); padding-block-start:10px; padding-inline-end:12px; }}
.parts b {{ display:block; font-family:var(--serif); font-size:44px; font-weight:600; line-height:1; font-variant-numeric:lining-nums; }}
.parts span {{ display:block; margin-block-start:6px; font-size:17px; line-height:1.35; color:var(--ink-2); }}
.parts .vecs {{ padding-inline-end:0; }}
.parts .vecs b {{ font-size:30px; }}
.parts .vecs span {{ font-size:14px; }}
.explain {{ display:grid; grid-template-columns:1fr 1fr; gap:28px; border-block-start:1px solid var(--rule); padding-block-start:18px; }}
.explain p {{ font-size:18px; line-height:1.5; color:var(--ink-2); }}
.namefact {{ display:flex; align-items:baseline; gap:18px; border-block-start:1px solid var(--rule); padding-block-start:16px; }}
.namefact b {{ font-family:var(--serif); font-size:40px; font-weight:600; line-height:1; white-space:nowrap; font-variant-numeric:lining-nums; }}
.namefact b span {{ font-size:22px; color:var(--ink-2); font-weight:400; }}
.namefact p {{ font-size:18px; line-height:1.45; color:var(--ink-2); max-inline-size:62ch; }}
.explain b {{ display:flex; align-items:center; gap:9px; font-family:var(--serif); font-size:19px; color:var(--ink); margin-block-end:4px; }}
"""
body1 = f"""
<h2>Katrs kvadrāts — viens cilvēks<small>Ko par viņiem atklāj Uzņēmumu reģistra izraksts</small></h2>
<div class="parts num">
  <div class="pase"><b>{K['arvalstu_pase']}</b><span>ar ārvalstu pasi — <br>pases valsts ir redzama</span></div>
  <div class="kods"><b>{K['jauna_parauga_kods']}</b><span>ar jaunā parauga Latvijas personas kodu — valsts nav zināma</span></div>
  <div class="vecs"><b>{K['veca_parauga_kods']}</b><span>ar vecā parauga kodu</span></div>
</div>
<div class="waffle" role="img" aria-label="410 kvadrāti: 165 oranži, 236 zili, 9 zaļganzili">{''.join(cells)}</div>
<div class="explain">
  <div><b><i class="sw kods"></i>Jaunā parauga kods</b><p>{JAUNS_TXT}</p></div>
  <div><b><i class="sw vecs"></i>Vecā parauga kods</b><p>{VECS_TXT}</p></div>
</div>
<div class="namefact num"><b>6<span> no 410</span></b><p>{NAME_TXT}</p></div>
{foot('Svarīgi', 'Jaunā parauga personas kods nenozīmē, ka cilvēks ir ārzemnieks vai ka viņam ir TUA.')}
"""
big1 = f'<div class="v">{K["arvalstu_pase"]}<span> no {K["investori"]}</span></div><p>investoriem reģistrā norādīta <b>ārvalstu pase</b>. Pārējiem ir Latvijas personas kods, un viņu valsts izrakstā nav redzama.</p>'
pages = {"1-kas-ir": page(1, KICK, f"Kas ir {K['investori']} cilvēki, kuriem katram pieder daļas par 50&nbsp;000 € vai 100&nbsp;000 €", DEK, big1, body1, css1)}

# ---------------- 2. valstis -----------------
rows = D["pases_valstis"]
mx = max(r[1] for r in rows)
CN_GROUP = 16  # «16 no tām vienā grupā (2023)» — no JSON piezīmes teksta
W = 560
bar_rows = []
for name, n, note in rows:
    agg = name.startswith("Citas")
    w = n / mx * W
    if name == "Ķīna":
        g = CN_GROUP / mx * W
        segs = f'<i class="seg grp" style="inline-size:{g:.1f}px"></i><i class="seg end" style="inline-size:{w-g-2:.1f}px"></i>'
        note = "16 no 21 — vienā uzņēmumu grupā (2023)"
    else:
        segs = f'<i class="seg end" style="inline-size:{w:.1f}px"></i>'
    if name == "Vjetnama":
        note = "3 savstarpēji nesaistītas struktūras"
    if agg:
        name = "Citas 18 valstis"
        note = "katrā 1–4"
    bar_rows.append(f'<div class="row{" agg" if agg else ""}"><span class="cn">{name}</span>'
                    f'<span class="track">{segs}<b class="num">{n}</b></span><span class="nt">{note}</span></div>')
css2 = """
.bars { display:grid; gap:6px; }
.row { display:grid; grid-template-columns:170px auto 1fr; align-items:center; gap:14px; block-size:34px; }
.row .cn { font-size:18px; text-align:end; color:var(--ink); }
.track { display:flex; align-items:center; gap:2px; }
.seg { display:block; block-size:26px; background:var(--pase); }
.seg:first-child { border-start-start-radius:0; }
.seg.end { border-start-end-radius:4px; border-end-end-radius:4px; }
.seg.grp { background:var(--kods); }
.track b { margin-inline-start:10px; font-family:var(--serif); font-size:21px; font-weight:600; }
.nt { font-size:15px; color:var(--muted); }
.row.agg { border-block-start:1px solid var(--rule); padding-block-start:8px; block-size:44px; }
.row.agg .seg { background:color-mix(in oklch, var(--pase) 45%, var(--paper)); }
.row.agg .cn { color:var(--ink-2); }
.iem { font-size:16px; line-height:1.45; color:var(--ink-2); max-inline-size:72ch; }
.iem b { font-weight:600; color:var(--ink); }
.key .sw.lt { background:color-mix(in oklch, var(--pase) 45%, var(--paper)); }
"""
iem = D["iem_salidzinajums"]
body2 = f"""
<h2>Pasu valstis — {K['arvalstu_pase']} investoriem<small>Pārējiem 245 ir Latvijas personas kods, viņu valsts nav zināma</small></h2>
<div class="key"><span><i class="sw" style="--c:var(--pase)"></i>investori ar šīs valsts pasi</span><span><i class="sw" style="--c:var(--kods)"></i>no tiem vienā uzņēmumu grupā</span></div>
<div class="bars">{''.join(bar_rows)}</div>
<p class="iem">Salīdzinājumam: Iekšlietu ministrijas (IeM) ziņojuma projektā (valdībā vēl nav izskatīts) 2025. gada 50&nbsp;000 € pieteikumos pirmās ir <b>Turcija ({iem['50k_cels_2025']['Turcija']})</b> un <b>Indija ({iem['50k_cels_2025']['Indija']})</b>.</p>
{foot('Svarīgi', 'Pases valsts nenozīmē, ka cilvēks saņēma termiņuzturēšanās atļauju (TUA), un ne vienmēr tā ir viņa vienīgā pilsonība.')}
"""
big2 = '<div class="v">16<span> no 21</span></div><p>investoru ar Ķīnas pasi ir <b>vienā uzņēmumu grupā</b> (2023.&nbsp;gadā). Investori ar Turcijas pasi turpretī ir 12 dažādos uzņēmumos.</p>'
pages["2-valstis"] = page(2, KICK, "No kurām valstīm ir investori ar ārvalstu pasi", "Reģistrā redzama tikai pases izdevējvalsts. Garums — cilvēku skaits.", big2, body2, css2)

# ---------------- 3. laiks -----------------
per = {p["periods"]: p for p in D["laiks_pusgadi"]}
slots = [f"{y} {h}" for y in range(2020, 2027) for h in ("I", "II")]
assert set(per) <= set(slots)
ymax = 200
PH = 400  # px plot height
SW = 66   # slot width
BW = 34
cols3 = []
for s in slots:
    p = per.get(s, {"SIA": 0, "AS": 0})
    sia, as_ = p["SIA"], p["AS"]
    tot = sia + as_
    hs, ha = sia / ymax * PH, as_ / ymax * PH
    inner = ""
    if tot:
        inner = (f'<i class="as hatch" style="block-size:{ha:.1f}px"></i>' if as_ else "") + f'<i class="sia" style="block-size:{hs:.1f}px"></i>'
    lab = f'<b class="num{" z" if not tot else ""}">{tot if tot else "0"}</b>'
    cols3.append(f'<div class="slot{" empty" if not tot else ""}">{lab}<div class="stack{" top-as" if as_ else ""}">{inner}</div></div>')


def xpos(dstr):
    d = date.fromisoformat(dstr)
    i = slots.index(f"{d.year} {'I' if d.month <= 6 else 'II'}")
    start = date(d.year, 1 if d.month <= 6 else 7, 1)
    end = date(d.year, 7, 1) if d.month <= 6 else date(d.year + 1, 1, 1)
    return (i + (d - start).days / (end - start).days) * SW


marks, keys = [], []
for k, (dstr, txt) in enumerate(D["likuma_atzimes"], 1):
    txt = txt.replace("KF/BY pilsoņiem jaunas TUA", "Krievijas un Baltkrievijas pilsoņiem jaunas termiņuzturēšanās atļaujas (TUA)")
    x = xpos(dstr)
    marks.append(f'<div class="mk" style="inset-inline-start:{x:.1f}px;--y:{26 if k == 4 else 0}px"><span class="num">{k}</span></div>')
    dd = date.fromisoformat(dstr).strftime("%d.%m.%Y.")
    keys.append(f'<li><span class="n num">{k}</span><span class="d num">{dd}</span>{txt}</li>')
years = "".join(f'<span style="grid-column:span 2">{y}</span>' for y in range(2020, 2027))
grid = "".join(f'<i style="inset-block-end:{v/ymax*PH:.1f}px"><em class="num">{v}</em></i>' for v in (50, 100, 150, 200))
css3 = f"""
.plotwrap {{ position:relative; padding-inline-start:44px; }}
.grid i {{ position:absolute; inset-inline:0; block-size:0; border-block-start:1px solid var(--rule); }}
.grid em {{ position:absolute; inset-inline-start:-44px; inline-size:36px; text-align:end; transform:translateY(-50%); font-style:normal; font-family:var(--mono); font-size:12px; color:var(--muted); }}
.plot {{ position:relative; display:grid; grid-template-columns:repeat({len(slots)}, {SW}px); grid-template-rows:{PH}px; block-size:{PH}px; align-items:end; }}
.grid {{ position:absolute; inset-block:0 auto; inset-inline:0; block-size:{PH}px; }}
.slot {{ display:flex; flex-direction:column; align-items:center; justify-content:end; gap:6px; block-size:100%; position:relative; z-index:1; overflow:visible; }}
.slot b {{ font-family:var(--serif); font-size:19px; font-weight:600; background:var(--paper); padding-inline:4px; line-height:1.15; }}
.slot .pt {{ order:-1; font-family:var(--mono); font-size:11px; color:var(--muted); white-space:nowrap; margin-block-end:-6px; }}
.slot b.z {{ color:var(--muted); font-weight:400; font-size:16px; }}
.stack {{ display:flex; flex-direction:column; gap:2px; inline-size:{BW}px; }}
.stack i {{ display:block; }}
.stack .sia {{ background:var(--kods); }}
.stack .as {{ --c:var(--kods); }}
.stack > i:first-child {{ border-start-start-radius:4px; border-start-end-radius:4px; }}
.slot.empty .stack {{ block-size:2px; background:var(--rule); }}
.slot.part::after {{ content:""; }}
.axis {{ display:grid; grid-template-columns:repeat({len(slots)}, {SW}px); border-block-start:1.5px solid var(--ink); margin-inline-start:44px; }}
.axis span {{ text-align:center; font-family:var(--mono); font-size:12px; color:var(--muted); padding-block-start:6px; }}
.years {{ display:grid; grid-template-columns:repeat({len(slots)}, {SW}px); margin-inline-start:44px; }}
.years span {{ text-align:center; font-family:var(--serif); font-size:18px; font-weight:600; border-inline-start:1px solid var(--rule); padding-block-start:2px; }}
.years span:first-child {{ border-inline-start:0; }}
.mks {{ position:absolute; inset-block:-30px 0; inset-inline-start:0; inline-size:{len(slots)*SW}px; pointer-events:none; z-index:0; }}
.mk {{ position:absolute; inset-block:0; border-inline-start:1.5px solid var(--red); }}
.mk span {{ position:absolute; inset-block-start:var(--y,0px); inset-inline-start:-11px; inline-size:22px; block-size:22px; border-radius:50%; background:var(--red); color:white; font-family:var(--mono); font-size:12px; display:grid; place-items:center; box-shadow:0 0 0 2px var(--paper); }}
.laws {{ list-style:none; display:grid; grid-template-columns:1fr 1fr; gap:8px 28px; font-size:16px; line-height:1.35; color:var(--ink-2); }}
.laws li {{ display:grid; grid-template-columns:auto auto 1fr; gap:10px; align-items:baseline; }}
.laws .n {{ inline-size:20px; block-size:20px; border-radius:50%; background:var(--red); color:white; font-family:var(--mono); font-size:11px; display:grid; place-items:center; align-self:start; }}
.laws .d {{ font-family:var(--mono); font-size:13px; color:var(--muted); }}
.partial {{ position:absolute; inset-inline-end:0; inset-block-start:-30px; font-family:var(--mono); font-size:12px; color:var(--muted); text-align:end; }}
"""
halves = "".join(f"<span>{s.split()[1]}{'*' if s == '2026 II' else ''}</span>" for s in slots)
body3 = f"""
<h2>Kad investori ierakstīti reģistrā<small>Cilvēku skaits pa pusgadiem; pusgadi bez neviena ieraksta atstāti tukši</small></h2>
<div class="key"><span><i class="sw" style="--c:var(--kods)"></i>SIA dalībnieki</span><span><i class="sw hatch" style="--c:var(--kods)"></i>AS akcionāri — datums var būt reģistra iesniegšanas datums, ne pirkuma datums</span></div>
<div class="plotwrap" style="margin-block-start:26px">
  <div class="plot">
    <div class="grid">{grid}</div>
    {''.join(cols3)}
    <div class="mks">{''.join(marks)}</div>
  </div>
</div>
<div style="margin-block-start:-26px"><div class="axis">{halves}</div><div class="years">{years}</div></div>
<ol class="laws">{''.join(keys)}</ol>
{foot('Svarīgi', '* 2026. gada otrais pusgads vēl nav beidzies: dati līdz 17.10.2026. Saraksts ietver visus 50 uzņēmumus ar šādu daļu struktūru atvērtajos datos, ne visus investorus.')}
"""
Y26 = [p for p in D["laiks_pusgadi"] if p["periods"].startswith("2026")]
N26, AS26 = sum(p["SIA"] + p["AS"] for p in Y26), sum(p["AS"] for p in Y26)
assert (N26, AS26) == (267, 40)
BIG3_TXT = (f"investoru ierakstīti reģistrā <b>2026. gadā</b> (līdz 17.&nbsp;oktobrim). {AS26} no viņiem ir AS akcionāri, "
            "kuru datums var būt dokumentu iesniegšanas datums.")
big3 = f'<div class="v">{N26}<span> no {K["investori"]}</span></div><p>{BIG3_TXT}</p>'
pages["3-laiks"] = page(3, KICK, "Divas trešdaļas investoru reģistrā ierakstītas 2026. gadā", "Pirms 2024. gada&nbsp;—&nbsp;40 cilvēki, 2024.–2025. gadā&nbsp;—&nbsp;103, 2026. gadā&nbsp;—&nbsp;267.", big3, body3, css3)

# ---------------- 4. divi-modeli -----------------
m = D["divi_modeli"]
A, B = m["investoru_partija"], m["ipasnieku_gimenes"]


def dots(n, cls):
    return f'<div class="dots {cls}">' + "<i></i>" * n + "</div>"


def cos(n, cls):
    return f'<div class="cos {cls}">' + "<i></i>" * n + "</div>"


css4 = """
.models { display:grid; grid-template-columns:1.12fr 1fr; gap:36px; }
.model { display:flex; flex-direction:column; gap:16px; border-block-start:3px solid var(--c); padding-block-start:16px; }
.model.a { --c:var(--kods); } .model.b { --c:var(--vecs); }
.model h3 { font-family:var(--serif); font-size:25px; white-space:nowrap; font-weight:700; line-height:1.1; display:flex; align-items:center; gap:10px; }
.model h3 .sw { inline-size:14px; block-size:14px; border-radius:50%; }
.model .desc { font-size:17px; line-height:1.45; color:var(--ink-2); }
.scheme { display:flex; gap:5px; align-items:stretch; }
.scheme div { border-radius:5px; display:grid; place-items:center; text-align:center; font-family:var(--mono); font-size:11px; letter-spacing:0.06em; text-transform:uppercase; line-height:1.3; }
.scheme .own { inline-size:112px; block-size:56px; background:var(--c); color:white; padding:4px; }
.scheme .inv { inline-size:28px; block-size:56px; background:var(--cell); }
.scheme .fam { inline-size:92px; block-size:56px; background:color-mix(in oklch, var(--c) 18%, var(--paper)); outline:2.5px solid var(--c); outline-offset:-2.5px; color:var(--ink); padding:4px; }
.scheme-cap { font-size:14px; color:var(--muted); margin-block-start:-8px; }
.stat { display:grid; grid-template-columns:auto 1fr; gap:12px 16px; align-items:center; }
.stat b { font-family:var(--serif); font-size:40px; font-weight:600; line-height:1; text-align:end; font-variant-numeric:lining-nums; }
.stat .l { font-size:15px; color:var(--ink-2); display:grid; gap:7px; }
.cos { display:flex; flex-wrap:wrap; gap:3px; }
.cos i { inline-size:14px; block-size:14px; border-radius:2px; background:var(--c); }
.dots { display:flex; flex-wrap:wrap; gap:3px; max-inline-size:442px; }
.dots i { inline-size:10px; block-size:10px; border-radius:50%; background:var(--c); }
.ex { list-style:none; display:grid; gap:6px; font-size:16px; line-height:1.4; color:var(--ink-2); }
.ex li { padding-inline-start:16px; position:relative; }
.ex li::before { content:""; position:absolute; inset-inline-start:0; inset-block-start:0.6em; inline-size:7px; block-size:7px; border-radius:50%; background:var(--c); }
.overlap { font-size:16px; line-height:1.45; color:var(--ink-2); border-block-start:1px solid var(--rule); padding-block-start:12px; }
"""
body4 = f"""
<h2>Divi atšķirīgi modeļi<small>Abi ietilpst {K['investori']} investoru kopskaitā, bet neaptver visus</small></h2>
<div class="models">
  <div class="model a">
    <h3><i class="sw"></i>Organizatora modelis</h3>
    <p class="desc">Organizators patur balsis, investori iegādājas bezbalsu daļas.</p>
    <div class="scheme"><div class="own">organizators<br>balsis</div><div class="inv"></div><div class="inv"></div><div class="inv"></div><div class="inv"></div><div class="inv"></div><div class="inv"></div><div class="inv"></div><div class="inv"></div></div>
    <p class="scheme-cap">Pelēkie — investoru daļas bez balsstiesībām</p>
    <div class="stat num">
      <b>{A['uznemumi']}</b><div class="l">uzņēmumi {cos(A['uznemumi'], '')}</div>
      <b>{A['investori']}</b><div class="l">investori {dots(A['investori'], '')}</div>
    </div>
  </div>
  <div class="model b">
    <h3><i class="sw"></i>Īpašnieku un ģimenes uzņēmumi</h3>
    <p class="desc">{B['apraksts']}.</p>
    <div class="scheme"><div class="fam">investors<br>valdē</div><div class="fam">investors<br>balsis</div><div class="fam">investors<br>PLG</div></div>
    <p class="scheme-cap">PLG — patiesais labuma guvējs</p>
    <div class="stat num">
      <b>{B['uznemumi']}</b><div class="l">uzņēmumi {cos(B['uznemumi'], '')}</div>
      <b>{B['investori']}</b><div class="l">investori {dots(B['investori'], '')}</div>
    </div>
    <ul class="ex">{''.join(f'<li>{e[0].upper() + e[1:]}</li>' for e in B['piemeri_bez_vardiem'])}</ul>
  </div>
</div>
<p class="overlap">Modeļi daļēji pārklājas, un vairāki uzņēmumi neietilpst ne vienā, ne otrā (16 uzņēmumos investoriem ir balsstiesības). Tāpēc kopā nesanāk 50 uzņēmumu un {K['investori']} investoru.</p>
{foot('Svarīgi', 'Likums abas struktūras pieļauj. Saraksts ietver visus 50 uzņēmumus ar šādu daļu struktūru UR atvērtajos datos 17.10.2026.')}
"""
big4 = f'<div class="v">{A["uznemumi"]}<span> no 50</span></div><p>uzņēmumos investoru daļām <b>nav balsstiesību</b> — lēmumus pieņem organizators. Tajos ir {A["investori"]} no {K["investori"]} investoriem.</p>'
pages["4-divi-modeli"] = page(4, KICK, "Organizatora modelis vai ģimenes uzņēmums", "Daļas par vienu un to pašu summu var nozīmēt ļoti atšķirīgus uzņēmumus.", big4, body4, css4)

# ================= MOBILĀS VERSIJAS (1080 px plats, rāda ~360 CSS px → teksts ≥ 40 px) =================
# Bez tumšā paneļa (raksts rāda virsrakstu virs attēla); augstumu mēra renderējot (--render).
MW = 1080
MPAD = 54
MC = MW - 2 * MPAD  # satura platums 972 px
MCSS = f"""
body.m {{ inline-size:{MW}px; block-size:auto; display:flex; flex-direction:column; gap:52px; padding:60px {MPAD}px 56px; font-size:40px; line-height:1.4; }}
.m .mbrand {{ display:flex; align-items:center; gap:14px; font-family:var(--serif); font-weight:700; font-size:36px; color:var(--night); }}
.m .mbrand svg {{ flex:none; inline-size:42px; block-size:42px; }}
.m .mbrand .step {{ margin-inline-start:auto; font-family:var(--mono); font-weight:500; font-size:28px; letter-spacing:0.1em; color:var(--muted); }}
.m h2 {{ font-family:var(--serif); font-size:60px; font-weight:700; line-height:1.1; text-wrap:balance; }}
.m h2 small {{ display:block; font-family:var(--sans); font-size:38px; font-weight:400; line-height:1.35; color:var(--muted); margin-block-start:14px; text-wrap:pretty; }}
.m .label {{ font-size:28px; }}
.m .key {{ display:grid; gap:14px; font-size:38px; line-height:1.3; }}
.m .key span {{ align-items:flex-start; gap:18px; }}
.m .sw {{ inline-size:36px; block-size:36px; border-radius:6px; margin-block-start:4px; }}
.m .hatch {{ background:
   repeating-linear-gradient(45deg, var(--c) 0 5px, transparent 5px 14px),
   color-mix(in oklch, var(--c) 34%, var(--paper)); }}
.m p {{ font-size:40px; line-height:1.42; color:var(--ink-2); }}
.m p b, .m p strong {{ color:var(--ink); font-weight:600; }}
.m .stat1 {{ border-block-start:3px solid var(--ink); padding-block-start:24px; }}
.m .stat1 .v {{ font-family:var(--serif); font-weight:600; font-size:128px; line-height:0.95; letter-spacing:-0.02em; font-variant-numeric:lining-nums; }}
.m .stat1 .v span {{ font-size:56px; color:var(--muted); font-weight:500; letter-spacing:0; }}
.m .stat1 p {{ margin-block-start:16px; }}
.m .mnote {{ display:grid; gap:10px; border-inline-start:8px solid var(--red); padding-inline-start:28px; }}
.m .mnote .label {{ color:var(--red); }}
.m .mnote p {{ font-family:var(--serif); font-size:42px; line-height:1.38; color:var(--ink); }}
.m .src {{ font-size:28px; line-height:1.45; letter-spacing:0.02em; }}
.m .mfoot {{ display:grid; gap:36px; border-block-start:1px solid var(--rule); padding-block-start:40px; }}
"""
LOGO_M = ('<svg viewBox="0 0 64 64" aria-hidden="true"><circle cx="27" cy="27" r="17" fill="none" stroke="currentColor" stroke-width="5.5"/>'
          '<line x1="40.5" y1="40.5" x2="52" y2="52" stroke="currentColor" stroke-width="5.5" stroke-linecap="round"/>'
          '<circle cx="27" cy="27" r="6" fill="#EF5350"/></svg>')
SRC_M = "Avots: UR izraksti un atvērtie dati (17.10.2026.); atmina.lv aprēķins"


def mpage(n, title, h2, body, css=""):
    return f"""<!doctype html>
<!-- UR investoru izpēte, vizuālis {n}/4, MOBILĀ versija (1080 px). Ģenerēts ar scripts/oneoff-content/tua_investoru_valstis_2026_viz.py. -->
<html lang="lv"><head><meta charset="utf-8"><title>{title}</title><style>{CSS}{MCSS}{css}</style></head>
<body class="m">
<div class="mbrand">{LOGO_M}atmina.lv<span class="step">{n} / 4</span></div>
<h2>{h2}</h2>
{body}
</body></html>"""


def mfoot(note):
    return f'<div class="mfoot"><div class="mnote"><span class="label">Svarīgi</span><p>{note}</p></div><div class="src">{SRC_M}</div></div>'


mpages = {}

# ---- 1m. kas-ir: vafele 25 kolonnās, rindu secībā ----
WC = 25
WG = 3
WS = (MC - (WC - 1) * WG) // WC  # 36 px
mcss1 = f"""
.mparts {{ display:grid; grid-template-columns:auto auto 1fr; gap:22px 22px; align-items:center; }}
.mparts b {{ font-family:var(--serif); font-size:92px; font-weight:600; line-height:1; text-align:end; font-variant-numeric:lining-nums tabular-nums; }}
.mparts span {{ font-size:40px; line-height:1.3; color:var(--ink-2); }}
.mparts .sw {{ margin:0; }}
.mwaffle {{ display:grid; grid-template-columns:repeat({WC}, {WS}px); grid-auto-rows:{WS}px; gap:{WG}px; }}
.mwaffle i {{ border-radius:5px; background:var(--c); }}
.pase {{ --c:var(--pase); }} .kods {{ --c:var(--kods); }} .vecs {{ --c:var(--vecs); }}
.mexp {{ display:grid; gap:12px; }}
.mexp b {{ display:flex; align-items:center; gap:18px; font-family:var(--serif); font-size:44px; color:var(--ink); }}
.mexp .sw {{ margin:0; }}
.mname {{ border-block-start:1px solid var(--rule); padding-block-start:36px; }}
.mname > b {{ display:block; font-family:var(--serif); font-size:92px; font-weight:600; line-height:1; font-variant-numeric:lining-nums; margin-block-end:12px; }}
.mname > b span {{ font-size:48px; color:var(--muted); font-weight:500; }}
"""
mbody1 = f"""
<div class="mparts">
  <i class="sw pase"></i><b>{K['arvalstu_pase']}</b><span>ar ārvalstu pasi — pases valsts ir redzama</span>
  <i class="sw kods"></i><b>{K['jauna_parauga_kods']}</b><span>ar jaunā parauga Latvijas personas kodu — valsts nav zināma</span>
  <i class="sw vecs"></i><b>{K['veca_parauga_kods']}</b><span>ar vecā parauga personas kodu</span>
</div>
<div class="mwaffle" role="img" aria-label="410 kvadrāti: 165 oranži, 236 zili, 9 zaļganzili">{''.join(f'<i class="{c}"></i>' for c in seq)}</div>
<div class="mexp"><b><i class="sw kods"></i>Jaunā parauga kods</b><p>{JAUNS_TXT}</p></div>
<div class="mexp"><b><i class="sw vecs"></i>Vecā parauga kods</b><p>{VECS_TXT}</p></div>
<div class="mname"><b>6<span> no {K['investori']}</span></b><p>{NAME_TXT}</p></div>
{mfoot('Jaunā parauga personas kods nenozīmē, ka cilvēks ir ārzemnieks vai ka viņam ir TUA.')}
"""
mpages["1-kas-ir-mob"] = mpage(1, "Kas ir 410 investori", "Katrs kvadrāts — viens cilvēks<small>Ko par viņiem atklāj Uzņēmumu reģistra izraksts</small>", mbody1, mcss1)

# ---- 2m. valstis: nosaukums + skaitlis rindā, josla pilnā platumā zem tā ----
mrows = []
for name, n, note in rows:
    agg = name.startswith("Citas")
    w = n / mx * MC
    if name == "Ķīna":
        g = CN_GROUP / mx * MC
        segs = f'<i class="seg grp" style="inline-size:{g:.1f}px"></i><i class="seg end" style="inline-size:{w-g-4:.1f}px"></i>'
        note = "16 no 21 — vienā uzņēmumu grupā (2023)"
    else:
        segs = f'<i class="seg end" style="inline-size:{w:.1f}px"></i>'
    if name == "Vjetnama":
        note = "3 savstarpēji nesaistītas struktūras"
    if agg:
        name, note = "Citas 18 valstis", "katrā 1–4"
    nt = f'<span class="nt">{note}</span>' if note else ""
    mrows.append(f'<div class="mrow{" agg" if agg else ""}"><div class="ml"><span class="cn">{name}</span><b class="num">{n}</b>{nt}</div>'
                 f'<div class="mtrack">{segs}</div></div>')
mcss2 = """
.mbars { display:grid; gap:26px; }
.mrow { display:grid; gap:8px; }
.ml { display:flex; flex-wrap:wrap; align-items:baseline; column-gap:18px; }
.ml .cn { font-size:40px; color:var(--ink); }
.ml b { font-family:var(--serif); font-size:46px; font-weight:600; }
.ml .nt { font-size:34px; color:var(--muted); inline-size:100%; line-height:1.25; }
.mtrack { display:flex; gap:4px; }
.mtrack .seg { display:block; block-size:34px; background:var(--pase); }
.mtrack .seg.end { border-start-end-radius:6px; border-end-end-radius:6px; }
.mtrack .seg.grp { background:var(--kods); }
.mrow.agg { border-block-start:1px solid var(--rule); padding-block-start:22px; }
.mrow.agg .seg { background:color-mix(in oklch, var(--pase) 45%, var(--paper)); }
.mrow.agg .cn { color:var(--ink-2); }
"""
mbody2 = f"""
<div class="key"><span><i class="sw" style="--c:var(--pase)"></i>investori ar šīs valsts pasi</span><span><i class="sw" style="--c:var(--kods)"></i>no tiem vienā uzņēmumu grupā</span></div>
<div class="mbars">{''.join(mrows)}</div>
<p>Salīdzinājumam: Iekšlietu ministrijas (IeM) ziņojuma projektā (valdībā vēl nav izskatīts) 2025. gada 50&nbsp;000 € pieteikumos pirmās ir <b>Turcija ({iem['50k_cels_2025']['Turcija']})</b> un <b>Indija ({iem['50k_cels_2025']['Indija']})</b>.</p>
{mfoot('Pases valsts nenozīmē, ka cilvēks saņēma termiņuzturēšanās atļauju (TUA), un ne vienmēr tā ir viņa vienīgā pilsonība.')}
"""
mpages["2-valstis-mob"] = mpage(2, "Pasu valstis", f"Pasu valstis — {K['arvalstu_pase']} investoriem<small>Pārējiem 245 ir Latvijas personas kods, viņu valsts nav zināma</small>", mbody2, mcss2)

# ---- 3m. laiks: horizontālas joslas pa pusgadiem, likuma notikumi kā rindas zem sava pusgada ----
TL = 196  # etiķetes kolonna
TW = MC - TL - 24 - 120  # joslas maksimums (vieta skaitlim)
tmax = max(p["SIA"] + p["AS"] for p in D["laiks_pusgadi"])
evs = {}
for dstr, txt in D["likuma_atzimes"]:
    d = date.fromisoformat(dstr)
    txt = txt.replace("KF/BY pilsoņiem jaunas TUA", "Krievijas un Baltkrievijas pilsoņiem jaunas termiņuzturēšanās atļaujas (TUA)")
    evs.setdefault(f"{d.year} {'I' if d.month <= 6 else 'II'}", []).append(f'<div class="ev"><span class="d num">{d.strftime("%d.%m.%Y.")}</span> {txt}</div>')
trows = []
for s in slots:
    p = per.get(s, {"SIA": 0, "AS": 0})
    tot = p["SIA"] + p["AS"]
    y, h = s.split()
    star = "*" if s == "2026 II" else ""
    lab = f'<span class="pl"><b class="num">{y}</b> <span>{h}{star}</span></span>'
    if tot:
        bar = f'<i class="sia" style="inline-size:{p["SIA"] / tmax * TW:.1f}px"></i>'
        if p["AS"]:
            bar += f'<i class="as hatch" style="inline-size:{p["AS"] / tmax * TW:.1f}px"></i>'
        bar += f'<b class="num">{tot}</b>'
    else:
        bar = '<i class="zero"></i><b class="num z">0</b>'
    trows.append(f'<div class="tr{" y0" if h == "I" else ""}">{lab}<div class="tt">{bar}</div></div>')
    trows.extend(evs.get(s, []))
mcss3 = f"""
.tl {{ display:grid; grid-template-columns:{TL}px 1fr; column-gap:24px; }}
.tr {{ display:contents; }}
.pl {{ grid-column:1; display:flex; align-items:baseline; justify-content:space-between; font-size:38px; padding-block:10px; }}
.pl b {{ font-family:var(--serif); font-weight:600; }}
.pl span {{ font-family:var(--mono); font-size:30px; color:var(--muted); }}
.tr:not(.y0) .pl b {{ visibility:hidden; }}
.tr.y0 .pl, .tr.y0 .tt {{ border-block-start:1px solid var(--rule); }}
.tt {{ grid-column:2; display:flex; align-items:center; gap:4px; padding-block:10px; }}
.tt i {{ display:block; block-size:40px; }}
.tt .sia {{ background:var(--kods); }}
.tt .as {{ --c:var(--kods); }}
.tt i:nth-last-of-type(1) {{ border-start-end-radius:6px; border-end-end-radius:6px; }}
.tt .zero {{ inline-size:4px; background:var(--rule); }}
.tt b {{ margin-inline-start:14px; font-family:var(--serif); font-size:44px; font-weight:600; }}
.tt b.z {{ color:var(--muted); font-weight:400; font-size:36px; }}
.ev {{ grid-column:2; border-inline-start:8px solid var(--red); padding:6px 0 6px 22px; margin-block:6px 12px; font-size:36px; line-height:1.3; color:var(--ink); }}
.ev .d {{ font-family:var(--mono); font-size:30px; color:var(--red); }}
"""
mbody3 = f"""
<div class="stat1"><div class="v">{N26}<span> no {K['investori']}</span></div><p>{BIG3_TXT}</p></div>
<div class="key"><span><i class="sw" style="--c:var(--kods)"></i>SIA dalībnieki</span><span><i class="sw hatch" style="--c:var(--kods)"></i>AS akcionāri — datums var būt reģistra iesniegšanas datums, ne pirkuma datums</span><span><i class="sw" style="--c:var(--red)"></i>likuma notikumi</span></div>
<div class="tl">{''.join(trows)}</div>
{mfoot('* 2026. gada otrais pusgads vēl nav beidzies: dati līdz 17.10.2026. Saraksts ietver visus 50 uzņēmumus ar šādu daļu struktūru atvērtajos datos, ne visus investorus.')}
"""
mpages["3-laiks-mob"] = mpage(3, "Kad investori ierakstīti reģistrā", "Kad investori ierakstīti reģistrā<small>Cilvēku skaits pa pusgadiem; arī pusgadi bez neviena ieraksta</small>", mbody3, mcss3)

# ---- 4m. divi modeļi, viens zem otra ----
mcss4 = """
.mmodel { display:flex; flex-direction:column; gap:28px; border-block-start:6px solid var(--c); padding-block-start:28px; }
.mmodel.a { --c:var(--kods); } .mmodel.b { --c:var(--vecs); }
.mmodel h3 { font-family:var(--serif); font-size:50px; font-weight:700; line-height:1.1; display:flex; align-items:center; gap:18px; }
.mmodel h3 .sw { inline-size:30px; block-size:30px; border-radius:50%; margin:0; }
.msch { display:flex; gap:8px; }
.msch div { border-radius:8px; display:grid; place-items:center; text-align:center; font-family:var(--mono); font-size:28px; letter-spacing:0.04em; text-transform:uppercase; line-height:1.25; block-size:120px; }
.msch .own { inline-size:290px; background:var(--c); color:white; }
.msch .inv { inline-size:60px; background:var(--cell); }
.msch .fam { flex:1; background:color-mix(in oklch, var(--c) 18%, var(--paper)); outline:4px solid var(--c); outline-offset:-4px; color:var(--ink); }
.mcap { font-size:34px !important; color:var(--muted) !important; margin-block-start:-14px; }
.mstat { display:grid; grid-template-columns:auto 1fr; gap:28px 26px; align-items:start; }
.mstat > b { font-family:var(--serif); font-size:96px; font-weight:600; line-height:0.9; text-align:end; font-variant-numeric:lining-nums tabular-nums; }
.mstat .l { font-size:38px; color:var(--ink-2); display:grid; gap:12px; line-height:1.1; }
.mstat .cos { display:flex; flex-wrap:wrap; gap:6px; }
.mstat .cos i { inline-size:30px; block-size:30px; border-radius:4px; background:var(--c); }
.mstat .dots { display:flex; flex-wrap:wrap; gap:6px; }
.mstat .dots i { inline-size:22px; block-size:22px; border-radius:50%; background:var(--c); }
.mex { list-style:none; display:grid; gap:14px; }
.mex li { padding-inline-start:36px; position:relative; font-size:38px; line-height:1.35; color:var(--ink-2); }
.mex li::before { content:""; position:absolute; inset-inline-start:0; inset-block-start:0.5em; inline-size:16px; block-size:16px; border-radius:50%; background:var(--c); }
"""
mbody4 = f"""
<div class="mmodel a">
  <h3><i class="sw"></i>Organizatora modelis</h3>
  <p>Organizators patur balsis, investori iegādājas bezbalsu daļas.</p>
  <div class="msch"><div class="own">organizators<br>balsis</div>{'<div class="inv"></div>' * 8}</div>
  <p class="mcap">Pelēkie — investoru daļas bez balsstiesībām</p>
  <div class="mstat">
    <b>{A['uznemumi']}</b><div class="l">uzņēmumi {cos(A['uznemumi'], '')}</div>
    <b>{A['investori']}</b><div class="l">investori {dots(A['investori'], '')}</div>
  </div>
</div>
<div class="mmodel b">
  <h3><i class="sw"></i>Īpašnieku un ģimenes uzņēmumi</h3>
  <p>{B['apraksts']}.</p>
  <div class="msch"><div class="fam">investors<br>valdē</div><div class="fam">investors<br>balsis</div><div class="fam">investors<br>PLG</div></div>
  <p class="mcap">PLG — patiesais labuma guvējs</p>
  <div class="mstat">
    <b>{B['uznemumi']}</b><div class="l">uzņēmumi {cos(B['uznemumi'], '')}</div>
    <b>{B['investori']}</b><div class="l">investori {dots(B['investori'], '')}</div>
  </div>
  <ul class="mex">{''.join(f'<li>{e[0].upper() + e[1:]}</li>' for e in B['piemeri_bez_vardiem'])}</ul>
</div>
<p>Modeļi daļēji pārklājas, un vairāki uzņēmumi neietilpst ne vienā, ne otrā (16 uzņēmumos investoriem ir balsstiesības). Tāpēc kopā nesanāk 50 uzņēmumu un {K['investori']} investoru.</p>
{mfoot('Likums abas struktūras pieļauj. Saraksts ietver visus 50 uzņēmumus ar šādu daļu struktūru UR atvērtajos datos 17.10.2026.')}
"""
mpages["4-divi-modeli-mob"] = mpage(4, "Divi modeļi", f"Divi atšķirīgi modeļi<small>Abi ietilpst {K['investori']} investoru kopskaitā, bet neaptver visus</small>", mbody4, mcss4)

# ================= VĀKS (1600×900, maz teksta — lasāms arī telefonā) =================
NOT_KNOWN = K["jauna_parauga_kods"] + K["veca_parauga_kods"]
assert NOT_KNOWN == K["investori"] - K["arvalstu_pase"] == 245
css0 = """
body.vaks { grid-template-columns:640px 1fr; }
.vaks .lead { padding:56px 60px; gap:30px; }
.vaks .brand { font-size:34px; } .vaks .brand svg { inline-size:42px; block-size:42px; }
.vaks .lead .label { font-size:22px; }
.vaks .lead h1 { font-size:104px; line-height:1.0; margin-block-start:auto; }
.vaks .body { padding:64px 72px 44px; gap:0; justify-content:center; }
.vrow { display:grid; grid-template-columns:300px 1fr; gap:32px; align-items:center; padding-block:22px; border-block-start:1px solid var(--rule); }
.vrow:first-child { border-block-start:0; }
.vrow b { font-family:var(--serif); font-size:128px; font-weight:600; line-height:0.85; letter-spacing:-0.02em; text-align:end; font-variant-numeric:lining-nums tabular-nums;
          border-inline-end:10px solid var(--c); padding-inline-end:28px; }
.vrow span { font-size:44px; line-height:1.2; color:var(--ink); }
.vaks .src { font-size:20px; margin-block-start:32px; }
.vsum { display:grid; grid-template-columns:300px 1fr; gap:32px; align-items:baseline; padding-block:14px 0; border-block-start:3px solid var(--ink); }
.vsum b { font-family:var(--serif); font-size:56px; font-weight:600; text-align:end; padding-inline-end:38px; font-variant-numeric:lining-nums tabular-nums; }
.vsum span { font-size:30px; color:var(--ink-2); }
.vnote { display:grid; grid-template-columns:300px 1fr; gap:32px; align-items:center; margin-block-start:44px; padding:22px 0; border:2px dashed var(--red); border-radius:10px; }
.vnote b { font-family:var(--serif); font-size:96px; font-weight:600; line-height:0.9; text-align:end; padding-inline-end:38px; color:var(--red); font-variant-numeric:lining-nums; }
.vnote span { font-size:34px; line-height:1.25; color:var(--ink); padding-inline-end:24px; }
"""
vrows = (f'<div class="vrow" style="--c:var(--pase)"><b>{K["arvalstu_pase"]}</b><span>ar ārvalstu pasi</span></div>'
         f'<div class="vrow" style="--c:var(--kods)"><b>{NOT_KNOWN}</b><span>ar Latvijas personas kodu, valsts nav zināma</span></div>'
         f'<div class="vsum"><b>{K["investori"]}</b><span>kopā</span></div>'
         f'<div class="vnote"><b>6</b><span>no visiem {K["investori"]} — tik daudziem vārds reģistrā ierakstīts latviskā formā</span></div>')
pages["0-vaks"] = f"""<!doctype html>
<!-- UR investoru izpēte, vāka attēls. Ģenerēts ar scripts/oneoff-content/tua_investoru_valstis_2026_viz.py. -->
<html lang="lv"><head><meta charset="utf-8"><title>410 investori, 50 uzņēmumi</title><style>{CSS}{css0}</style></head>
<body class="vaks">
<section class="lead">
  <div class="brand">{LOGO}atmina.lv</div>
  <div class="label">Izpēte · Uzņēmumu reģistrs</div>
  <h1>{K['investori']} investori, {K['uznemumi']} uzņēmumi</h1>
</section>
<section class="body">
  <div>{vrows}</div>
  <div class="src">{SRC}</div>
</section>
</body></html>"""

pages.update(mpages)
IMG_A = ROOT / "output/images/analizes"
IMG_T = ROOT / "output/images/threads"
jobs = []  # (html, [png...], platums, augstums vai None=mērīt)
for slug, html in pages.items():
    f = OUT / f"2026-10-19-ur-viz-{slug}.html"
    f.write_text(html, encoding="utf-8")
    print(f)
    if slug == "0-vaks":
        jobs.append((f, [IMG_A / "tua-investoru-valstis-2026-vaks.png"], 1600, 900))
    elif slug.endswith("-mob"):
        jobs.append((f, [IMG_A / f"tua-investoru-valstis-2026-{slug}.png"], MW, None))
    else:
        jobs.append((f, [IMG_T / f"2026-10-19-ur-viz-{slug}.png", IMG_A / f"tua-investoru-valstis-2026-{slug}.png"], 1600, 900))

if __name__ == "__main__" and "--render" in sys.argv:
    # Tas pats, ko scripts/render_shema.py, bet mobilajām versijām augstumu mēra pēc satura.
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch()
        for f, pngs, w, h in jobs:
            pg = br.new_page(viewport={"width": w, "height": h or 1000})
            pg.goto(f.resolve().as_uri(), wait_until="networkidle")
            pg.evaluate("document.fonts.ready.then(() => true)")
            fonts = pg.evaluate("[...document.fonts].map(x => x.family + ':' + x.status)")
            if any(x.endswith(":error") for x in fonts):
                raise SystemExit(f"Fonts neielādējās {f.name}: {sorted(set(fonts))}")
            sw, sh = pg.evaluate("[document.documentElement.scrollWidth, document.documentElement.scrollHeight]")
            if h is None:
                h = sh
                pg.set_viewport_size({"width": w, "height": h})
            elif sh > h or sw > w:
                print(f"  BRĪDINĀJUMS: {f.name} saturs {sw}×{sh} pārsniedz {w}×{h}")
            for png in pngs:
                png.parent.mkdir(parents=True, exist_ok=True)
                pg.screenshot(path=str(png), full_page=False)
                print(f"  {png} ({w}×{h})")
            pg.close()
        br.close()
