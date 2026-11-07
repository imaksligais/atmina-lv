"""Vāka datu grafiks «Atradumam» pilsoniba-ar-likumu-14-saeima: 14. Saeimas 11 pilsonības piešķīrumi ārpus naturalizācijas,
balsis «pret» un «atturas» galīgajā balsojumā. Desktop 1600×900 + mobilā (1080 px plata, augstums pēc satura).
Dati — Saeimas balsojumi (saeima_votes id 4364,1413,941,1182,1184,1274,1271,208,211,8473,8476), ierakstīti zemāk ar roku.
Stils pēc src/graphics/templates/izpete-shema.html un scripts/oneoff-content/tua_investoru_valstis_2026_viz.py (good-css + dataviz;
krāsu pāris #2d5aa0 / #b5541c — dataviz validators: ALL CHECKS PASS).
Palaišana: PYTHONUTF8=1 .venv/Scripts/python.exe scripts/oneoff-content/pilsoniba_2026_11_viz.py [--render]"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / ".scratch/pilsoniba-viz"
IMG = ROOT / "output/images/analizes"
SLUG = "pilsoniba-ar-likumu-14-saeima"
F = "../../output/atmina/assets/fonts/"  # relatīvi no .scratch/pilsoniba-viz/

# (sēdes datums, uzvārds uz ass, pret, atturas, īpašā atzīme)
SESIJAS = [
    ("14.09.2023", [("K. Višvanats", 0, 0, None)]),
    ("15.02.2024", [("Bilokrinicka", 0, 0, None)]),
    ("18.09.2025", [("Cibuļa", 0, 0, None)]),
    ("27.11.2025", [("Kargins", 0, 0, None), ("Alismails", 0, 1, None)]),
    ("18.12.2025", [("Manskis", 8, 1, "lemums"), ("Kuļišs", 0, 5, None)]),
    ("21.05.2026", [("dus Santuss-Šaviers", 3, 1, None), ("Kabicina", 5, 5, None)]),
    ("15.10.2026", [("Mičuda", 3, 0, None), ("D. K. Višvanata", 6, 8, "atcelts")]),
]
assert sum(len(p) for _, p in SESIJAS) == 11
MAXV = max(pr + at for _, p in SESIJAS for _, pr, at, _ in p)
assert MAXV == 14

TITLE = "Pilsonība ar Saeimas balsojumu 14. Saeimā"
SUB = "Galīgie balsojumi: balsis pret un atturas"
SRC = "Avots: Saeimas balsojumi · atmina.lv"
NOTE = "Manskis — Saeimas lēmums par īpašiem nopelniem; pārējie — atsevišķi likumi."

CSS = f"""
@font-face {{ font-family:'Source Serif 4'; src:url('{F}source-serif-4-normal-latin-ext.woff2') format('woff2'); font-weight:200 900; }}
@font-face {{ font-family:'Source Serif 4'; src:url('{F}source-serif-4-normal-latin.woff2') format('woff2'); font-weight:200 900; }}
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
  --red: oklch(50.2% 0.189 27);
  --pret: oklch(47.3% 0.124 259);    /* #2d5aa0 */
  --atturas: oklch(55.9% 0.142 46);  /* #b5541c */
  --serif: 'Source Serif 4', Georgia, serif;
  --mono: 'JetBrains Mono', ui-monospace, monospace;
  --sans: "Segoe UI", Roboto, sans-serif;
  font-synthesis: none; -webkit-font-smoothing: antialiased; text-wrap: pretty;
}}
body {{ background:var(--paper); color:var(--ink); font-family:var(--sans); overflow:clip; }}
.label {{ font-family:var(--mono); font-weight:500; letter-spacing:0.14em; text-transform:uppercase; }}
.num {{ font-variant-numeric: lining-nums tabular-nums; }}
.brand {{ display:flex; align-items:center; gap:12px; font-family:var(--serif); font-weight:700; color:var(--night); }}
.brand svg {{ flex:none; }}
.brand .label {{ margin-inline-start:auto; color:var(--red); font-family:var(--mono); font-weight:500; }}
h1 {{ font-family:var(--serif); font-weight:700; line-height:1.05; letter-spacing:-0.01em; text-wrap:balance; }}
.sub {{ color:var(--muted); }}
.key {{ display:flex; flex-wrap:wrap; color:var(--ink-2); }}
.key span {{ display:inline-flex; align-items:center; }}
.sw {{ display:inline-block; border-radius:3px; background:var(--c); flex:none; }}
.pret {{ --c:var(--pret); }} .atturas {{ --c:var(--atturas); }}
/* atcelts likums: krāsa paliek (identitāte), bet svītrots un ar raustītu kontūru */
.cut {{ background:repeating-linear-gradient(45deg, var(--c) 0 3px, color-mix(in oklch, var(--c) 22%, var(--paper)) 3px 8px) !important;
        outline:2px dashed var(--red); outline-offset:2px; }}
.sw.cut {{ outline-offset:1px; }}
.tag-cut {{ color:var(--red); font-family:var(--mono); font-weight:500; letter-spacing:0.04em; }}
.tag-dec {{ font-family:var(--mono); font-weight:500; letter-spacing:0.06em; color:var(--night);
            border:1.5px solid currentColor; border-radius:4px; }}
.src {{ color:var(--muted); font-family:var(--mono); letter-spacing:0.04em; }}
"""

LOGO = ('<svg viewBox="0 0 64 64" aria-hidden="true"><circle cx="27" cy="27" r="17" fill="none" stroke="currentColor" stroke-width="5.5"/>'
        '<line x1="40.5" y1="40.5" x2="52" y2="52" stroke="currentColor" stroke-width="5.5" stroke-linecap="round"/>'
        '<circle cx="27" cy="27" r="6" fill="#EF5350"/></svg>')


def vals_txt(pr, at, sep):
    parts = [f"{pr}&nbsp;pret" if pr else "", f"{at}&nbsp;atturas" if at else ""]
    parts = [p for p in parts if p]
    return sep.join(parts) if parts else "0"


# ======================= DESKTOP 1600×900 =======================
U = 23  # px uz vienu balsi
DCSS = f"""
body.d {{ inline-size:1600px; block-size:900px; padding:44px 64px 36px; display:flex; flex-direction:column; gap:0; }}
.d .brand {{ font-size:28px; }} .d .brand svg {{ inline-size:34px; block-size:34px; }} .d .brand .label {{ font-size:17px; }}
.d h1 {{ font-size:58px; margin-block-start:22px; }}
.d .sub {{ font-size:26px; margin-block-start:10px; }}
.d .key {{ gap:10px 34px; font-size:21px; margin-block-start:26px; }}
.d .key span {{ gap:10px; }}
.d .sw {{ inline-size:20px; block-size:20px; }}
.chart {{ margin-block-start:auto; display:flex; align-items:stretch; gap:44px; position:relative; }}
.grp {{ flex:var(--n) 1 0; display:grid; grid-template-columns:repeat(var(--n), 1fr); grid-template-rows:auto auto auto; column-gap:12px; }}
.slot {{ display:grid; grid-template-rows:subgrid; grid-row:1 / span 3; justify-items:center; }}
.plot {{ block-size:{MAXV * U + 96}px; display:flex; flex-direction:column; justify-content:flex-end; align-items:center; gap:8px;
         border-block-end:2px solid var(--ink); inline-size:100%; }}
.vals {{ text-align:center; font-size:19px; line-height:1.2; color:var(--ink-2); }}
.vals b {{ font-family:var(--serif); font-size:26px; font-weight:600; color:var(--ink); }}
.bar {{ display:flex; flex-direction:column-reverse; gap:2px; inline-size:44px; }}
.bar i {{ display:block; background:var(--c); }}
.bar i:last-child {{ border-start-start-radius:4px; border-start-end-radius:4px; }}
.zero {{ inline-size:14px; block-size:14px; border-radius:50%; border:2.5px solid var(--ink-2); background:var(--paper); margin-block-end:-8px; }}
.name {{ block-size:54px; margin-block-start:12px; text-align:center; font-size:19px; line-height:1.2; font-weight:600; }}
.date {{ grid-column:1 / -1; grid-row:4; margin-block-start:8px; text-align:center; font-family:var(--mono); font-weight:500; font-size:17px; color:var(--muted);
         border-block-start:1px solid var(--rule); padding-block-start:6px; }}
.d .tag-cut {{ font-size:17px; text-align:center; line-height:1.2; }}
.d .tag-dec {{ font-size:15px; padding:1px 8px; }}
.dec {{ block-size:26px; }}
.bracket {{ position:absolute; inset-inline-start:0; inset-block-start:{MAXV * U + 96 - 230}px; font-family:var(--serif); font-size:26px; line-height:1.25;
            border-block-start:2px solid var(--ink-2); padding-block-start:12px; color:var(--ink); }}
.bracket::before, .bracket::after {{ content:""; position:absolute; inset-block-start:-2px; block-size:14px; border-inline-start:2px solid var(--ink-2); }}
.bracket::before {{ inset-inline-start:0; }} .bracket::after {{ inset-inline-end:0; }}
.d .foot {{ display:flex; justify-content:space-between; gap:40px; margin-block-start:22px; font-size:17px; }}
.d .foot p {{ color:var(--ink-2); }}
.d .src {{ font-size:16px; }}
"""


def bar_html(pr, at, cut):
    c = " cut" if cut else ""
    segs = []
    if pr:
        segs.append(f'<i class="pret{c}" style="block-size:{pr * U - (2 if at else 0)}px"></i>')
    if at:
        segs.append(f'<i class="atturas{c}" style="block-size:{at * U}px"></i>')
    return f'<div class="bar">{"".join(segs)}</div>'


def desktop_chart():
    """Atslēga + grafiks + kājene (bez virsraksta bloka) — kopīgs vākam un 1. iekšējam grafikam."""
    grps = []
    for date, ppl in SESIJAS:
        slots = []
        for name, pr, at, mark in ppl:
            top = ""
            if mark == "atcelts":
                top = '<div class="tag-cut">likums<br>atcelts 22.10.</div>'
            if pr + at == 0:
                mark_html = '<div class="vals"><b class="num">0</b></div><div class="zero"></div>'
            else:
                lines = [f'<b class="num">{pr}</b> pret' if pr else "", f'<b class="num">{at}</b> atturas' if at else ""]
                mark_html = f'<div class="vals">{"<br>".join(x for x in lines if x)}</div>{bar_html(pr, at, mark == "atcelts")}'
            nm = name.replace("dus Santuss-Šaviers", "dus Santuss-<br>Šaviers").replace("D. K. Višvanata", "D. K.<br>Višvanata").replace("K. Višvanats", "K.<br>Višvanats")
            dec = '<span class="tag-dec">lēmums</span>' if mark == "lemums" else ""
            slots.append(f'<div class="slot"><div class="plot">{top}{mark_html}</div><div class="name">{nm}</div><div class="dec">{dec}</div></div>')
        grps.append(f'<div class="grp" style="--n:{len(ppl)}">{"".join(slots)}<div class="date num">{date}</div></div>')
    return f"""<div class="key"><span><i class="sw pret"></i>pret</span><span><i class="sw atturas"></i>atturas</span>
<span><i class="sw pret cut"></i>likums vēlāk atcelts</span><span><i class="zero" style="margin:0"></i>neviena balss pret vai atturas</span></div>
<div class="chart">{"".join(grps)}<div class="bracket" id="br">Līdz 2025. gada novembrim neviena balss pret</div></div>
<div class="foot"><p>{NOTE}</p><div class="src">{SRC}</div></div>"""


def desktop():
    return f"""<!doctype html>
<!-- Vāks: {SLUG}. Ģenerēts ar scripts/oneoff-content/pilsoniba_2026_11_viz.py. -->
<html lang="lv"><head><meta charset="utf-8"><title>{TITLE}</title><style>{CSS}{DCSS}</style></head>
<body class="d">
<div class="brand">{LOGO}atmina.lv<span class="label">Atradums · Saeima</span></div>
<h1>{TITLE}</h1>
<p class="sub">{SUB}</p>
{desktop_chart()}
</body></html>"""


# ======================= MOBILĀ 1080 px =======================
MU = 40
MCSS = f"""
body.m {{ inline-size:1080px; padding:60px 54px 56px; display:flex; flex-direction:column; gap:40px; }}
.m .brand {{ font-size:36px; }} .m .brand svg {{ inline-size:42px; block-size:42px; }} .m .brand .label {{ font-size:24px; }}
.m h1 {{ font-size:64px; line-height:1.08; }}
.m .sub {{ font-size:38px; line-height:1.35; margin-block-start:-16px; }}
.m .key {{ display:grid; grid-template-columns:1fr 1fr; gap:16px 30px; font-size:34px; line-height:1.25; }}
.m .key span {{ gap:16px; align-items:center; }}
.m .key .wide {{ grid-column:1 / -1; }}
.m .sw {{ inline-size:34px; block-size:34px; border-radius:5px; }}
.m .zero {{ inline-size:26px; block-size:26px; border-radius:50%; border:4px solid var(--ink-2); background:var(--paper); flex:none; }}
.mlist {{ display:grid; gap:34px; }}
.mg {{ display:grid; gap:20px; border-block-start:2px solid var(--ink); padding-block-start:16px; }}
.mg .d8 {{ font-family:var(--mono); font-weight:500; font-size:28px; color:var(--muted); letter-spacing:0.04em; }}
.mrow {{ display:grid; gap:10px; }}
.mrow.z {{ display:flex; align-items:center; gap:20px; }}
.mrow .nm {{ font-size:38px; font-weight:600; line-height:1.2; display:flex; flex-wrap:wrap; align-items:center; gap:8px 16px; }}
.mrow .line {{ display:flex; align-items:center; gap:18px; }}
.mbar {{ display:flex; gap:3px; }}
.mbar i {{ display:block; block-size:40px; background:var(--c); }}
.mbar i:last-child {{ border-start-end-radius:5px; border-end-end-radius:5px; }}
.mbar i.cut {{ outline-width:3px; outline-offset:3px; }}
.mrow .v {{ font-size:34px; color:var(--ink-2); }}
.mrow .v b {{ font-family:var(--serif); font-size:42px; font-weight:600; color:var(--ink); }}
.m .tag-cut {{ font-size:28px; }}
.m .tag-dec {{ font-size:24px; padding:2px 10px; border-width:2px; }}
.m .foot {{ display:grid; gap:28px; border-block-start:1px solid var(--rule); padding-block-start:36px; }}
.m .foot p {{ font-size:34px; line-height:1.4; color:var(--ink-2); }}
.m .src {{ font-size:28px; }}
"""


def mobile_chart():
    gs = []
    for date, ppl in SESIJAS:
        rows = []
        for name, pr, at, mark in ppl:
            tags = ""
            if mark == "atcelts":
                tags = '<span class="tag-cut">likums atcelts 22.10.</span>'
            elif mark == "lemums":
                tags = '<span class="tag-dec">lēmums</span>'
            if pr + at == 0:
                line = '<i class="zero"></i><span class="v"><b class="num">0</b></span>'
            else:
                c = " cut" if mark == "atcelts" else ""
                segs = "".join(
                    [f'<i class="pret{c}" style="inline-size:{pr * MU}px"></i>' if pr else "",
                     f'<i class="atturas{c}" style="inline-size:{at * MU}px"></i>' if at else ""])
                lines = [f'<b class="num">{pr}</b> pret' if pr else "", f'<b class="num">{at}</b> atturas' if at else ""]
                line = f'<div class="mbar">{segs}</div><span class="v">{", ".join(x for x in lines if x)}</span>'
            z = " z" if pr + at == 0 else ""
            rows.append(f'<div class="mrow{z}"><div class="nm">{name}{tags}</div><div class="line">{line}</div></div>')
        gs.append(f'<div class="mg"><div class="d8 num">{date}</div>{"".join(rows)}</div>')
    return f"""<div class="key"><span><i class="sw pret"></i>pret</span><span><i class="sw atturas"></i>atturas</span>
<span class="wide"><i class="sw pret cut"></i>likums vēlāk atcelts</span><span class="wide"><i class="zero" style="margin:0"></i>neviena balss pret vai atturas</span></div>
<div class="mlist">{"".join(gs)}</div>
<div class="foot"><p>{NOTE}</p><div class="src">{SRC}</div></div>"""


def mobile():
    return f"""<!doctype html>
<!-- Vāks (mobilā): {SLUG}. Ģenerēts ar scripts/oneoff-content/pilsoniba_2026_11_viz.py. -->
<html lang="lv"><head><meta charset="utf-8"><title>{TITLE}</title><style>{CSS}{MCSS}</style></head>
<body class="m">
<div class="brand">{LOGO}atmina.lv<span class="label">Atradums</span></div>
<h1>{TITLE}</h1>
<p class="sub">{SUB}</p>
{mobile_chart()}
</body></html>"""


# ======================= IEKŠĒJIE GRAFIKI (1–3) =======================
# Kopīgais: bez zīmola rindas un lielā virsraksta bloka; īss virsraksts grafika augšā, avots apakšā.
# Krāsas 2.–3. grafikam ir jaunas (zils/oranžs rakstā jau nozīmē «pret»/«atturas»):
#   likumi #00875f, lēmumi #9466c0 — dataviz validators uz #f7f3e8: visas pārbaudes PASS (CVD ΔE 13,9; normālā 24,8).
ICSS = """
:root { --likumi: #00875f; --lemumi: #9466c0; }
.likumi { --c:var(--likumi); } .lemumi { --c:var(--lemumi); }
h2 { font-family:var(--serif); font-weight:700; line-height:1.12; letter-spacing:-0.005em; text-wrap:balance; color:var(--ink); }
"""


def pct(x):
    """Latviešu formāts: «84 %»."""
    return f"{x}&nbsp;%"


# ---------- 1. Pret un atturas (vāka saturs bez virsraksta bloka) ----------
T1 = "Balsis pret un atturas galīgajos balsojumos"
D1CSS = """
body.d.c1 { block-size:auto; padding:44px 64px 40px; }
.c1 h2 { font-size:42px; }
.c1 .key { margin-block-start:18px; }
.c1 .chart { margin-block-start:34px; }
"""
M1CSS = """
.m.i h2 { font-size:52px; }
.m.i .d8, .m.i .src, .m.i .tag-cut { font-size:30px; }
.m.i .tag-dec { font-size:30px; padding:2px 12px; }
"""


def chart1_d():
    return f"""<!doctype html>
<!-- 1. grafiks: {SLUG}. Ģenerēts ar scripts/oneoff-content/pilsoniba_2026_11_viz.py. -->
<html lang="lv"><head><meta charset="utf-8"><title>{T1}</title><style>{CSS}{DCSS}{ICSS}{D1CSS}</style></head>
<body class="d c1 i">
<h2>{T1}</h2>
{desktop_chart()}
</body></html>"""


def chart1_m():
    return f"""<!doctype html>
<!-- 1. grafiks (mobilā): {SLUG}. -->
<html lang="lv"><head><meta charset="utf-8"><title>{T1}</title><style>{CSS}{MCSS}{ICSS}{M1CSS}</style></head>
<body class="m i">
<h2>{T1}</h2>
{mobile_chart()}
</body></html>"""


# ---------- 2. Steidzamība ----------
# saeima_votes id (steidzamība): 4398, 1401, 7296, 7523, 7524, 7867, 6729, 6730, 8471, 8474 — skaitļi ierakstīti ar roku no raksta tabulas.
STEIDZ = [  # (uzvārds, gads, par, pret, atturas, raksta tabulas procents, atzīme)
    ("K. Višvanats", 2023, 93, 0, 0, 100, None),
    ("Bilokrinicka", 2024, 79, 0, 0, 100, None),
    ("Cibuļa", 2025, 71, 0, 0, 100, None),
    ("Kargins", 2025, 81, 0, 0, 100, None),
    ("Alismails", 2025, 75, 0, 0, 100, None),
    ("Kuļišs", 2025, 73, 0, 1, 99, None),
    ("dus Santuss-Šaviers", 2026, 72, 4, 0, 95, None),
    ("Kabicina", 2026, 74, 5, 0, 94, None),
    ("Mičuda", 2026, 82, 3, 0, 96, None),
    ("D. K. Višvanata", 2026, 71, 8, 6, 84, "atcelts"),
]
for _n, _g, _p, _pr, _a, _t, _m in STEIDZ:
    assert round(100 * _p / (_p + _pr + _a)) == _t, _n
T2 = "Steidzamība: «par» daļa balsojušo"
NOTE2 = "Ja steidzamību atbalsta vismaz divas trešdaļas, Valsts prezidents nevar prasīt likumu caurlūkot vēlreiz (Satversmes 75.&nbsp;pants)."
SRC2 = "Avots: Saeimas balsojumi · atmina.lv"
SUB2 = "10 likumi par atzīšanu par Latvijas pilsoni, 14.&nbsp;Saeima. Pie joslas: <b style='white-space:nowrap'>par&nbsp;:&nbsp;pret&nbsp;:&nbsp;atturas</b>"
KEY2 = ('<span><i class="sw likumi"></i>«par» daļa balsojušo</span>'
        '<span><i class="sw likumi cut"></i>likums vēlāk atcelts</span>'
        '<span><i class="thr-sw"></i>divas trešdaļas (66,7&nbsp;%)</span>')
S2CSS = """
.sub2 { color:var(--muted); }
.sub2 b { font-family:var(--mono); font-weight:500; color:var(--ink-2); }
.key2 { color:var(--ink-2); }
.key2 span { display:inline-flex; align-items:center; }
.thr-sw { display:inline-block; flex:none; border-inline-start:3px solid var(--ink); }
.bar2 { position:relative; block-size:var(--bh); background:color-mix(in oklch, var(--rule) 45%, var(--paper)); border-radius:0 4px 4px 0; }
.bar2 > i { position:absolute; inset-block:0; inset-inline-start:0; background:var(--c); border-radius:0 4px 4px 0; }
.thr { position:absolute; inset-block:calc(var(--bh) * -0.3); inset-inline-start:calc(200% / 3); border-inline-start:3px solid var(--ink); }
.r2 .p { font-family:var(--serif); font-weight:600; color:var(--ink); }
.r2 .ppa { font-family:var(--mono); font-weight:500; color:var(--muted); letter-spacing:0.02em; }
.r2 .nm2 { font-weight:600; color:var(--ink); }
.r2 .nm2 small { font-weight:400; color:var(--muted); font-size:inherit; }
"""
D2CSS = """
body.d2 { inline-size:1600px; padding:44px 64px 40px; display:flex; flex-direction:column; }
.d2 h2 { font-size:42px; }
.d2 .sub2 { font-size:22px; margin-block-start:10px; }
.d2 .key2 { display:flex; gap:34px; font-size:20px; margin-block-start:16px; }
.d2 .key2 span { gap:10px; }
.d2 .sw { inline-size:20px; block-size:20px; }
.d2 .thr-sw { block-size:26px; }
.grid2 { --bh:30px; display:grid; grid-template-columns:330px 1fr 230px; column-gap:28px; row-gap:20px; margin-block-start:28px; align-items:center; }
.d2 .r2 { display:contents; }
.d2 .nm2 { font-size:25px; text-align:end; line-height:1.15; }
.d2 .nm2 .tag-cut { display:block; font-size:17px; margin-block-start:2px; }
.d2 .val { display:flex; align-items:baseline; gap:14px; }
.d2 .p { font-size:28px; min-inline-size:90px; text-align:end; }
.d2 .ppa { font-size:19px; }
.axis { grid-column:2; position:relative; block-size:34px; border-block-start:2px solid var(--ink); }
.axis span { position:absolute; inset-block-start:10px; translate:-50% 0; font-family:var(--mono); font-weight:500; font-size:17px; color:var(--muted); white-space:nowrap; }
.thr-lbl { grid-column:2; position:relative; block-size:30px; }
.thr-lbl span { position:absolute; inset-inline-start:calc(200% / 3); inset-block-end:0; translate:-50% 0; font-family:var(--serif); font-size:22px; font-weight:600; white-space:nowrap; }
.d2 .foot { display:flex; justify-content:space-between; align-items:end; gap:40px; margin-block-start:30px; border-block-start:1px solid var(--rule); padding-block-start:18px; }
.d2 .foot p { font-size:20px; line-height:1.35; color:var(--ink-2); max-inline-size:66ch; }
.d2 .src { font-size:16px; white-space:nowrap; }
"""
M2CSS = """
body.m2 { inline-size:1080px; padding:60px 54px 56px; display:flex; flex-direction:column; gap:34px; }
.m2 h2 { font-size:52px; }
.m2 .sub2 { font-size:32px; line-height:1.35; margin-block-start:-14px; }
.m2 .key2 { display:grid; gap:14px; font-size:32px; }
.m2 .key2 span { gap:16px; }
.m2 .sw { inline-size:34px; block-size:34px; border-radius:5px; }
.m2 .thr-sw { block-size:40px; border-inline-start-width:4px; margin-inline: 15px 15px; }
.mlist2 { --bh:40px; display:grid; gap:26px; }
.m2 .r2 { display:grid; gap:12px; border-block-start:1px solid var(--rule); padding-block-start:16px; }
.m2 .top { display:flex; justify-content:space-between; align-items:baseline; gap:16px; }
.m2 .nm2 { font-size:36px; line-height:1.2; }
.m2 .p { font-size:42px; }
.m2 .ppa { font-size:30px; }
.m2 .tag-cut { font-size:30px; }
.m2 .scale { position:relative; block-size:40px; font-family:var(--mono); font-weight:500; font-size:30px; color:var(--muted); }
.m2 .scale span { position:absolute; inset-block-start:0; white-space:nowrap; }
.m2 .scale .t0 { inset-inline-start:0; } .m2 .scale .t100 { inset-inline-end:0; }
.m2 .scale .t23 { inset-inline-start:calc(200% / 3); translate:-50% 0; color:var(--ink); font-family:var(--serif); font-weight:600; }
.m2 .foot { display:grid; gap:24px; border-block-start:1px solid var(--rule); padding-block-start:30px; }
.m2 .foot p { font-size:32px; line-height:1.4; color:var(--ink-2); }
.m2 .src { font-size:30px; }
"""


def _bar2(par, pr, at, cut):
    share = 100 * par / (par + pr + at)
    c = " cut" if cut else ""
    return f'<div class="bar2"><i class="likumi{c}" style="inline-size:{share:.3f}%"></i><b class="thr"></b></div>'


def _ppa(par, pr, at):
    return f'<span class="ppa num">{par}&nbsp;:&nbsp;{pr}&nbsp;:&nbsp;{at}</span>'


def chart2_d():
    rows = []
    for n, g, par, pr, at, t, m in STEIDZ:
        tag = '<span class="tag-cut">likums atcelts 22.10.</span>' if m == "atcelts" else ""
        rows.append(f'<div class="r2"><div class="nm2">{n} <small>({g})</small>{tag}</div>{_bar2(par, pr, at, m)}'
                    f'<div class="val"><span class="p num">{pct(t)}</span>{_ppa(par, pr, at)}</div></div>')
    ticks = "".join(f'<span class="num" style="inset-inline-start:{v}%">{v}&nbsp;%</span>' for v in (0, 25, 50, 75, 100))
    return f"""<!doctype html>
<!-- 2. grafiks: {SLUG}. -->
<html lang="lv"><head><meta charset="utf-8"><title>{T2}</title><style>{CSS}{ICSS}{S2CSS}{D2CSS}</style></head>
<body class="d2 i">
<h2>{T2}</h2>
<p class="sub2">{SUB2}</p>
<div class="key2">{KEY2}</div>
<div class="grid2"><div></div><div class="thr-lbl"><span>divas trešdaļas</span></div><div></div>
{"".join(rows)}
<div></div><div class="axis">{ticks}</div><div></div></div>
<div class="foot"><p>{NOTE2}</p><div class="src">{SRC2}</div></div>
</body></html>"""


def chart2_m():
    rows = []
    for n, g, par, pr, at, t, m in STEIDZ:
        tag = '<span class="tag-cut">likums atcelts 22.10.</span>' if m == "atcelts" else ""
        rows.append(f'<div class="r2"><div class="top"><div class="nm2">{n} <small>({g})</small></div><span class="p num">{pct(t)}</span></div>'
                    f'{_bar2(par, pr, at, m)}<div class="top">{_ppa(par, pr, at)}{tag}</div></div>')
    return f"""<!doctype html>
<!-- 2. grafiks (mobilā): {SLUG}. -->
<html lang="lv"><head><meta charset="utf-8"><title>{T2}</title><style>{CSS}{ICSS}{S2CSS}{M2CSS}</style></head>
<body class="m2 i">
<h2>{T2}</h2>
<p class="sub2">{SUB2}</p>
<div class="key2">{KEY2}</div>
<div class="mlist2"><div class="scale num"><span class="t0">0&nbsp;%</span><span class="t23">⅔</span><span class="t100">100&nbsp;%</span></div>{"".join(rows)}</div>
<div class="foot"><p>{NOTE2}</p><div class="src">{SRC2}</div></div>
</body></html>"""


# ---------- 3. Pa Saeimām ----------
# 5.–13. Saeima: .scratch/2026-10-18-pilsonibas/info781.txt (komisijas apkopojums 1995–2026);
# 14. Saeima: reģistri 1–1588/Lp14, 1–1140/Lm14 + balsojumi 15.10.2026 (info781 14. Saeimai uzskaita tikai 8 likumus līdz 21.05.2026).
# 5. Saeimai 25 (nevis 23): info781 «izvērtēja un virzīja … 25 personas», tabulā 25 rindas, visām Saeimas datums (pēdējais 26.10.95.).
SAEIMAS = [  # (Saeima, gadi, likumi, lēmumi)
    ("5.", "1993–1995", 0, 25),
    ("6.", "1995–1998", 0, 149),
    ("7.", "1998–2002", 3, 1),
    ("8.", "2002–2006", 14, 0),
    ("9.", "2006–2010", 6, 0),
    ("10.", "2010–2011", 0, 0),
    ("11.", "2011–2014", 0, 0),
    ("12.", "2014–2018", 0, 7),
    ("13.", "2018–2022", 6, 2),
    ("14.", "2022–", 10, 1),
]
assert sum(x[2] for x in SAEIMAS[2:5]) == 23  # info781: «7. – 9. Saeimu darbības laikā … 23 personas»
CAP = 30  # mērogs līdz 30; 6. Saeimas 149 — pārrauts stabiņš
T3 = "Pilsonība ar Saeimas balsojumu pa Saeimām"
SUB3 = "Atsevišķi likumi par atzīšanu par Latvijas pilsoni un Saeimas lēmumi par uzņemšanu pilsonībā par īpašiem nopelniem"
NOTE3 = ("6.&nbsp;Saeimas stabiņš pārrauts: 149 lēmumi neietilpst mērogā. "
         "14.&nbsp;Saeimā viens likums (Višvanata) atcelts 22.10.2026. Dati — līdz 2026.&nbsp;gada 22.&nbsp;oktobrim.")
SRC3 = "Avots: Saeimas Pilsonības, migrācijas un sabiedrības saliedētības komisija; Saeimas reģistri · atmina.lv"
KEY3 = ('<span><i class="sw likumi"></i>likumi</span><span><i class="sw lemumi"></i>lēmumi par nopelniem</span>'
        '<span><i class="sw likumi cut"></i>likums vēlāk atcelts</span>')
S3CSS = """
.sub2 { color:var(--muted); }
.key2 { color:var(--ink-2); }
.key2 span { display:inline-flex; align-items:center; }
.stk { display:flex; position:relative; }
.stk > i { display:block; background:var(--c); flex:none; }
.brk { position:absolute; background:var(--paper); border:solid var(--ink); }
.zero3 { display:block; border-radius:50%; border:solid var(--ink-2); background:var(--paper); flex:none; }
"""
DU = 13  # px uz vienību (desktop)
D3CSS = f"""
body.d3 {{ inline-size:1600px; padding:44px 64px 40px; display:flex; flex-direction:column; }}
.d3 h2 {{ font-size:42px; }}
.d3 .sub2 {{ font-size:22px; margin-block-start:10px; }}
.d3 .key2 {{ display:flex; gap:34px; font-size:21px; margin-block-start:16px; }}
.d3 .key2 span {{ gap:10px; }}
.d3 .sw {{ inline-size:20px; block-size:20px; }}
.cols {{ display:grid; grid-template-columns:repeat(10, 1fr); column-gap:18px; margin-block-start:30px; }}
.col {{ display:grid; justify-items:center; text-align:center; }}
.col .plot {{ block-size:{(CAP + 6) * DU + 70}px; display:flex; flex-direction:column; justify-content:flex-end; align-items:center; gap:10px;
             border-block-end:2px solid var(--ink); inline-size:100%; }}
.col .tot {{ font-family:var(--serif); font-size:30px; font-weight:600; line-height:1; }}
.col .tot small {{ display:block; font-family:var(--mono); font-weight:500; font-size:17px; color:var(--muted); margin-block-start:6px; }}
.d3 .stk {{ flex-direction:column-reverse; gap:2px; inline-size:64px; }}
.d3 .stk > i:last-of-type {{ border-start-start-radius:4px; border-start-end-radius:4px; }}
.d3 .brk {{ inset-inline:-12px; block-size:18px; border-width:3px 0; transform:skewY(-14deg); }}
.d3 .zero3 {{ inline-size:16px; block-size:16px; border-width:2.5px; margin-block-end:-9px; }}
.col .sn {{ margin-block-start:14px; font-size:24px; font-weight:600; }}
.col .yr {{ font-family:var(--mono); font-weight:500; font-size:16px; color:var(--muted); margin-block-start:4px; }}
.d3 .foot {{ display:flex; justify-content:space-between; align-items:end; gap:40px; margin-block-start:30px; border-block-start:1px solid var(--rule); padding-block-start:18px; }}
.d3 .foot p {{ font-size:19px; line-height:1.35; color:var(--ink-2); max-inline-size:70ch; }}
.d3 .src {{ font-size:16px; max-inline-size:46ch; text-align:end; line-height:1.35; }}
"""
MU3 = 30  # px uz vienību (mobilā)
M3CSS = """
body.m3 { inline-size:1080px; padding:60px 54px 56px; display:flex; flex-direction:column; gap:34px; }
.m3 h2 { font-size:52px; }
.m3 .sub2 { font-size:32px; line-height:1.35; margin-block-start:-14px; }
.m3 .key2 { display:grid; gap:14px; font-size:32px; }
.m3 .key2 span { gap:16px; }
.m3 .sw { inline-size:34px; block-size:34px; border-radius:5px; }
.rows3 { display:grid; gap:24px; }
.row3 { display:grid; gap:12px; border-block-start:1px solid var(--rule); padding-block-start:14px; }
.row3 .top { display:flex; justify-content:space-between; align-items:baseline; gap:16px; }
.row3 .sn { font-size:36px; font-weight:600; }
.row3 .sn small { font-family:var(--mono); font-weight:500; font-size:30px; color:var(--muted); margin-inline-start:14px; }
.row3 .tot { font-family:var(--serif); font-size:40px; font-weight:600; }
.row3 .tot small { font-family:var(--mono); font-weight:500; font-size:30px; color:var(--muted); margin-inline-end:16px; }
.m3 .stk { gap:3px; block-size:38px; }
.m3 .stk > i { block-size:100%; }
.m3 .stk > i:last-of-type { border-start-end-radius:5px; border-end-end-radius:5px; }
.m3 .brk { inset-block:-10px; inline-size:22px; border-width:0 3px; transform:skewX(-18deg); }
.m3 .stk > i.zero3 { inline-size:30px; block-size:30px; border-width:4px; border-radius:50%; align-self:center; }
.m3 .foot { display:grid; gap:24px; border-block-start:1px solid var(--rule); padding-block-start:30px; }
.m3 .foot p { font-size:32px; line-height:1.4; color:var(--ink-2); }
.m3 .src { font-size:30px; line-height:1.35; }
"""


def _segs3(lik, lem, unit, axis):
    """Segmenti: likumi (14. Saeimā pēdējā vienība = atcelts), tad lēmumi. axis = 'block-size' | 'inline-size'."""
    out, gap = [], 3 if axis == "inline-size" else 2
    if lik:
        if lik == 10:  # 14. Saeima: 9 spēkā + 1 atcelts
            out.append(f'<i class="likumi" style="{axis}:{9 * unit - gap}px"></i>')
            out.append(f'<i class="likumi cut" style="{axis}:{unit - gap}px"></i>')
        else:
            out.append(f'<i class="likumi" style="{axis}:{lik * unit - gap}px"></i>')
    if lem:
        out.append(f'<i class="lemumi" style="{axis}:{lem * unit - gap}px"></i>')
    return "".join(out)


def _split(lik, lem):
    return f"{lik}&nbsp;+&nbsp;{lem}" if lik and lem else ""


def chart3_d():
    cols = []
    for sn, yr, lik, lem in SAEIMAS:
        tot, sp = lik + lem, _split(lik, lem)
        if tot == 0:
            mark = '<div class="tot num">0</div><i class="zero3"></i>'
        elif tot > CAP:  # pārrāvums
            mark = (f'<div class="tot num">{tot}</div><div class="stk"><i class="lemumi" style="block-size:{(CAP + 6) * DU}px"></i>'
                    f'<b class="brk" style="inset-block-start:{4 * DU}px"></b></div>')
        else:
            mark = f'<div class="tot num">{tot}{f"<small>{sp}</small>" if sp else ""}</div><div class="stk">{_segs3(lik, lem, DU, "block-size")}</div>'
        cols.append(f'<div class="col"><div class="plot">{mark}</div><div class="sn">{sn} Saeima</div><div class="yr num">{yr}</div></div>')
    return f"""<!doctype html>
<!-- 3. grafiks: {SLUG}. -->
<html lang="lv"><head><meta charset="utf-8"><title>{T3}</title><style>{CSS}{ICSS}{S3CSS}{D3CSS}</style></head>
<body class="d3 i">
<h2>{T3}</h2>
<p class="sub2">{SUB3}</p>
<div class="key2">{KEY3}</div>
<div class="cols">{"".join(cols)}</div>
<div class="foot"><p>{NOTE3}</p><div class="src">{SRC3}</div></div>
</body></html>"""


def chart3_m():
    rows = []
    full = 25 * MU3 + 160  # 6. Saeimas pārrautā josla — garāka par 5. Saeimas 25
    for sn, yr, lik, lem in SAEIMAS:
        tot, sp = lik + lem, _split(lik, lem)
        if tot == 0:
            bar = '<div class="stk"><i class="zero3"></i></div>'
        elif tot > CAP:
            bar = (f'<div class="stk"><i class="lemumi" style="inline-size:{full}px"></i>'
                   f'<b class="brk" style="inset-inline-start:{full - 170}px"></b></div>')
        else:
            bar = f'<div class="stk">{_segs3(lik, lem, MU3, "inline-size")}</div>'
        rows.append(f'<div class="row3"><div class="top"><span class="sn">{sn} Saeima<small class="num">{yr}</small></span>'
                    f'<span class="tot num">{f"<small>{sp}</small>" if sp else ""}{tot}</span></div>{bar}</div>')
    return f"""<!doctype html>
<!-- 3. grafiks (mobilā): {SLUG}. -->
<html lang="lv"><head><meta charset="utf-8"><title>{T3}</title><style>{CSS}{ICSS}{S3CSS}{M3CSS}</style></head>
<body class="m3 i">
<h2>{T3}</h2>
<p class="sub2">{SUB3}</p>
<div class="key2">{KEY3}</div>
<div class="rows3">{"".join(rows)}</div>
<div class="foot"><p>{NOTE3}</p><div class="src">{SRC3}</div></div>
</body></html>"""


OUT.mkdir(parents=True, exist_ok=True)
ALL = [("vaks", desktop, 1600, 900), ("vaks-mob", mobile, 1080, None),
       ("1-pret-atturas", chart1_d, 1600, None), ("1-pret-atturas-mob", chart1_m, 1080, None),
       ("2-steidzamiba", chart2_d, 1600, None), ("2-steidzamiba-mob", chart2_m, 1080, None),
       ("3-saeimas", chart3_d, 1600, None), ("3-saeimas-mob", chart3_m, 1080, None)]
# Apstiprināto vāku PNG pārraksta tikai ar --vaks; bez tā renderē 1.–3. grafiku.
jobs = []
for kind, fn, w, h in ALL:
    f = OUT / f"{SLUG}-{kind}.html"
    f.write_text(fn(), encoding="utf-8")
    print(f)
    if kind.startswith("vaks") == ("--vaks" in sys.argv):
        jobs.append((f, IMG / f"{SLUG}-{kind}.png", w, h))

if __name__ == "__main__" and "--render" in sys.argv:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch()
        for f, png, w, h in jobs:
            pg = br.new_page(viewport={"width": w, "height": h or 1000})
            pg.goto(f.resolve().as_uri(), wait_until="networkidle")
            pg.evaluate("document.fonts.ready.then(() => true)")
            fonts = pg.evaluate("[...document.fonts].map(x => x.family + ':' + x.status)")
            if any(x.endswith(":error") for x in fonts) or not any(x.endswith(":loaded") for x in fonts):
                raise SystemExit(f"Fonts neielādējās {f.name}: {sorted(set(fonts))}")
            print("  fonti:", sorted(set(fonts)))
            # iekava virs pirmajām 4 sesijām (līdz 27.11.2025 ieskaitot) — tikai lapās, kurās ir #br
            pg.evaluate("""() => { const b=document.getElementById('br'); if (!b) return;
              const g=[...document.querySelectorAll('.grp')], c=document.querySelector('.chart').getBoundingClientRect();
              const r=g[3].getBoundingClientRect();
              b.style.insetInlineStart=(g[0].getBoundingClientRect().left-c.left)+'px'; b.style.inlineSize=(r.right-g[0].getBoundingClientRect().left)+'px'; }""")
            sw, sh = pg.evaluate("[document.body.scrollWidth, document.body.scrollHeight]")
            if sw > w:
                print(f"  BRĪDINĀJUMS: {f.name} platums {sw} > {w}")
            if h is None:
                h = sh
                pg.set_viewport_size({"width": w, "height": h})
            elif sh > h:
                print(f"  BRĪDINĀJUMS: {f.name} saturs {sw}×{sh} pārsniedz {w}×{h}")
            png.parent.mkdir(parents=True, exist_ok=True)
            pg.screenshot(path=str(png), full_page=False)
            print(f"  {png} ({w}×{h})")
            pg.close()
        br.close()
