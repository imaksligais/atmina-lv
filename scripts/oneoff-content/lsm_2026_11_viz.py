"""Vāks + 3 datu grafiki «Atradumam» lsm-2026-skaitlos. Desktop 1600 px (vāks 1600×900) + mobilā (1080 px, augstums pēc satura).
Visi skaitļi ierakstīti ar roku no content/analizes/lsm-2026-skaitlos.md (tabulas un aizzīmes) — jaunu skaitļu nav.
Stils pēc scripts/oneoff-content/pilsoniba_2026_11_viz.py un src/graphics/templates/izpete-shema.html (good-css + dataviz).
Krāsas (dataviz validators, virsma #f7f3e8):
  LTV1 #2d5aa0 / LTV7 #b5541c — ALL CHECKS PASS (CVD ΔE 20,9; normālā 26,9);
  par #00875f / pret #9466c0 / atturas #c08a00 — --pairs all PASS (CVD ΔE 10,0; normālā 20,7); #c08a00 kontrasts 2,75:1 → WARN,
  tāpēc katrai rindai redzami skaitļi (ar tintes krāsu). Zils/oranžs šajā rakstā jau nozīmē kanālus, tāpēc balsojumiem citas krāsas.
  Nauda — viena sērija (--night), vienreizējā tehnika — svītrota tekstūra tās pašas krāsas.
Palaišana: PYTHONUTF8=1 .venv/Scripts/python.exe scripts/oneoff-content/lsm_2026_11_viz.py [--render]"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / ".scratch/lsm-viz"
IMG = ROOT / "output/images/analizes"
SLUG = "lsm-2026-skaitlos"
F = "../../output/atmina/assets/fonts/"  # relatīvi no .scratch/lsm-viz/
NB = "&nbsp;"

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
  --track: color-mix(in oklch, var(--rule) 45%, var(--paper));
  --red: oklch(50.2% 0.189 27);
  --ltv1: #2d5aa0; --ltv7: #b5541c;
  --par: #00875f; --pret: #9466c0; --atturas: #c08a00;
  --serif: 'Source Serif 4', Georgia, serif;
  --mono: 'JetBrains Mono', ui-monospace, monospace;
  --sans: "Segoe UI", Roboto, sans-serif;
  font-synthesis: none; -webkit-font-smoothing: antialiased; text-wrap: pretty;
}}
body {{ background:var(--paper); color:var(--ink); font-family:var(--sans); overflow:clip; display:flex; flex-direction:column; }}
.label {{ font-family:var(--mono); font-weight:500; letter-spacing:0.14em; text-transform:uppercase; }}
.num {{ font-variant-numeric: lining-nums tabular-nums; }}
.brand {{ display:flex; align-items:center; gap:12px; font-family:var(--serif); font-weight:700; color:var(--night); }}
.brand svg {{ flex:none; }}
.brand .label {{ margin-inline-start:auto; color:var(--red); }}
h1, h2 {{ font-family:var(--serif); font-weight:700; letter-spacing:-0.01em; text-wrap:balance; color:var(--ink); }}
h1 {{ line-height:1.05; }} h2 {{ line-height:1.12; }}
.sub {{ color:var(--muted); }}
.key {{ display:flex; flex-wrap:wrap; color:var(--ink-2); }}
.key span {{ display:inline-flex; align-items:center; }}
.sw {{ display:inline-block; border-radius:3px; background:var(--c); flex:none; }}
.ltv1 {{ --c:var(--ltv1); }} .ltv7 {{ --c:var(--ltv7); }} .night {{ --c:var(--night); }}
.par {{ --c:var(--par); }} .pret {{ --c:var(--pret); }} .atturas {{ --c:var(--atturas); }}
.hatch {{ background:repeating-linear-gradient(45deg, var(--night) 0 4px, color-mix(in oklch, var(--night) 30%, var(--paper)) 4px 10px) !important; }}
.trk {{ position:relative; background:var(--track); border-radius:0 4px 4px 0; }}
.fill {{ display:flex; block-size:100%; gap:2px; }}
.fill > i {{ display:block; block-size:100%; background:var(--c); flex:none; }}
.fill > i:last-child {{ border-start-end-radius:4px; border-end-end-radius:4px; }}
.bare {{ display:flex; align-items:center; }}
.bare > i {{ display:block; background:var(--c); border-radius:0 4px 4px 0; flex:none; }}
.bare > span {{ color:var(--ink); font-family:var(--serif); font-weight:600; }}
.foot {{ border-block-start:1px solid var(--rule); }}
.foot p {{ color:var(--ink-2); }}
.src {{ color:var(--muted); font-family:var(--mono); letter-spacing:0.04em; }}
/* desktop */
body.d {{ inline-size:1600px; padding:44px 64px 40px; }}
.d .brand {{ font-size:28px; }} .d .brand svg {{ inline-size:34px; block-size:34px; }} .d .brand .label {{ font-size:17px; }}
.d h1 {{ font-size:58px; margin-block-start:22px; }}
.d h2 {{ font-size:42px; }}
.d .sub {{ font-size:23px; line-height:1.35; margin-block-start:10px; }}
.d .key {{ gap:10px 34px; font-size:20px; margin-block-start:18px; }}
.d .key span {{ gap:10px; }}
.d .sw {{ inline-size:20px; block-size:20px; }}
.d .foot {{ display:flex; justify-content:space-between; align-items:end; gap:40px; margin-block-start:30px; padding-block-start:18px; }}
.d .foot p {{ font-size:19px; line-height:1.4; max-inline-size:72ch; }}
.d .src {{ margin-inline-start:auto; font-size:16px; text-align:end; line-height:1.4; max-inline-size:52ch; }}
.d .axis {{ position:relative; block-size:30px; border-block-start:2px solid var(--ink); }}
.d .axis span {{ position:absolute; inset-block-start:8px; translate:-50% 0; font-family:var(--mono); font-weight:500; font-size:16px; color:var(--muted); white-space:nowrap; }}
/* mobilā */
body.m {{ inline-size:1080px; padding:60px 54px 56px; gap:34px; }}
.m .brand {{ font-size:36px; }} .m .brand svg {{ inline-size:42px; block-size:42px; }} .m .brand .label {{ font-size:24px; }}
.m h1 {{ font-size:64px; line-height:1.08; }}
.m h2 {{ font-size:52px; }}
.m .sub {{ font-size:32px; line-height:1.35; margin-block-start:-14px; }}
.m .key {{ display:grid; gap:14px; font-size:32px; }}
.m .key span {{ gap:16px; }}
.m .key.row {{ display:flex; gap:40px; }}
.m .sw {{ inline-size:34px; block-size:34px; border-radius:5px; }}
.m .foot {{ display:grid; gap:24px; padding-block-start:30px; }}
.m .foot p {{ font-size:32px; line-height:1.4; }}
.m .src {{ font-size:28px; line-height:1.4; }}
.m .scale {{ display:flex; justify-content:space-between; font-family:var(--mono); font-weight:500; font-size:28px; color:var(--muted);
             border-block-end:2px solid var(--ink); padding-block-end:6px; }}
"""

LOGO = ('<svg viewBox="0 0 64 64" aria-hidden="true"><circle cx="27" cy="27" r="17" fill="none" stroke="currentColor" stroke-width="5.5"/>'
        '<line x1="40.5" y1="40.5" x2="52" y2="52" stroke="currentColor" stroke-width="5.5" stroke-linecap="round"/>'
        '<circle cx="27" cy="27" r="6" fill="#EF5350"/></svg>')


def pct(s):
    """'65,7' -> '65,7 %' (nedalāma atstarpe)."""
    return f"{s}{NB}%"


def num(s):
    return float(s.replace(",", "."))


def eur(n):
    return f"{n:,}".replace(",", NB) + f"{NB}€"


def page(title, body_cls, extra_css, body, comment):
    return f"""<!doctype html>
<!-- {comment}: {SLUG}. Ģenerēts ar scripts/oneoff-content/lsm_2026_11_viz.py. -->
<html lang="lv"><head><meta charset="utf-8"><title>{title}</title><style>{CSS}{extra_css}</style></head>
<body class="{body_cls}">
{body}
</body></html>"""


def foot(note, src):
    return f'<div class="foot">{f"<p>{note}</p>" if note else ""}<div class="src">{src}</div></div>'


def ticks(vals, maxv, fmt):
    return "".join(f'<span class="num" style="inset-inline-start:{100 * v / maxv:.3f}%">{fmt(v)}</span>' for v in vals)


# ======================= VĀKS: četri skaitļi (operatora izvēle 2026-11-01, variants B) =======================
# Četri atsevišķi lauciņi — katrs skaitlis ir cits mērs, tie nav viena veseluma daļas.
# Nauda: dotācija uz 0–70 milj. € skalas, svītrotā daļa = vienreizējā tehnika (vienīgā īstā daļa).
# Ēters: katrs kanāls uz sava 0–100 % celiņa. Saeima: 76/4/8 uz 0–100 deputātu skalas.
TV = "Sabiedriskais medijs skaitļos"
SUBV = "LSM nauda, cilvēki, ēters un Saeimas lēmums — no pārskatiem, programmas un balsojumiem"
SRCV = "Avoti: LSM un SEPLP pārskati, TV.lv programma, Saeimas balsojumi · atmina.lv"
DOT, TEH = 69_046_512, 10_289_846
VCSS = """
.v .grid { display:grid; grid-template-columns:1fr 1fr; gap:0 72px; margin-block-start:auto; }
.v .t { display:grid; gap:10px; align-content:start; padding-block:26px 30px; border-block-start:2px solid var(--ink); }
.v .k { font-size:19px; color:var(--red); }
.v .big { font-family:var(--serif); font-weight:700; font-size:76px; line-height:1; }
.v .big small { font-size:40px; font-weight:600; }
.v .n { font-size:23px; color:var(--ink-2); line-height:1.3; }
.v .mini { display:flex; block-size:22px; gap:2px; background:var(--track); border-radius:0 4px 4px 0; }
.v .mini > i { display:block; block-size:100%; background:var(--c); flex:none; }
.v .mini > i:last-child { border-start-end-radius:4px; border-end-end-radius:4px; }
.v .two { display:grid; gap:6px; }
.v .two .lbl { display:grid; grid-template-columns:70px 1fr 90px; align-items:center; gap:12px; font-size:19px; color:var(--ink-2); }
.v .two .lbl b { font-family:var(--serif); font-weight:600; color:var(--ink); text-align:end; }
.v.m .grid { grid-template-columns:1fr; }
.v.m .t { gap:16px; padding-block:30px 34px; }
.v.m .k { font-size:26px; } .v.m .big { font-size:96px; } .v.m .big small { font-size:48px; }
.v.m .n { font-size:32px; } .v.m .mini { block-size:34px; }
.v.m .two { gap:12px; } .v.m .two .lbl { grid-template-columns:100px 1fr 140px; font-size:30px; }
"""


def _tiles():
    nauda = (f'<div class="mini"><i class="night" style="inline-size:{100 * (DOT - TEH) / 70e6:.3f}%"></i>'
             f'<i class="night hatch" style="inline-size:{100 * TEH / 70e6:.3f}%"></i></div>')
    eters = "".join(f'<div class="lbl"><span>{c}</span><div class="mini"><i class="{k}" style="inline-size:{num(v):.3f}%"></i></div>'
                    f'<b class="num">{pct(v)}</b></div>' for k, c, v in (("ltv7", "LTV7", "65,7"), ("ltv1", "LTV1", "10,7")))
    bals = ('<div class="mini"><i class="par" style="inline-size:76%"></i>'
            '<i class="pret" style="inline-size:4%"></i><i class="atturas" style="inline-size:8%"></i></div>')
    return f"""<div class="grid">
<div class="t"><span class="k label">Nauda 2025</span><div class="big num">69,05<small>{NB}milj.{NB}€</small></div>{nauda}
<p class="n">valsts dotācija; svītrotā daļa — 10,29{NB}milj.{NB}€ vienreizējai tehnikai</p></div>
<div class="t"><span class="k label">Cilvēki</span><div class="big num">850</div>
<p class="n">darbinieku 2025. gada beigās (829 pilnas slodzes)</p></div>
<div class="t"><span class="k label">Ēters vakarā (18–23)</span><div class="two">{eters}</div>
<p class="n">ārvalstu seriāļu daļa, rudens 2026</p></div>
<div class="t"><span class="k label">Saeima 22.10.2026</span><div class="big num">76{NB}:{NB}4{NB}:{NB}8</div>{bals}
<p class="n">likums: radio un TV ziņu dienestus nedrīkst apvienot</p></div>
</div>"""


def vaks_d():
    body = f"""<div class="brand">{LOGO}atmina.lv<span class="label">Atradums · LSM</span></div>
<h1>{TV}</h1>
<p class="sub">{SUBV}</p>
{_tiles()}
{foot("", SRCV)}"""
    return page(TV, "d v", VCSS + "body.d.v { block-size:900px; } .d.v h1 { font-size:60px; }", body, "Vāks")


def vaks_m():
    body = f"""<div class="brand">{LOGO}atmina.lv<span class="label">Atradums</span></div>
<h1>{TV}</h1>
<p class="sub">{SUBV}</p>
{_tiles()}
{foot("", SRCV)}"""
    return page(TV, "m v", VCSS, body, "Vāks (mobilā)")


# ======================= 1. NAUDA =======================
# Dažādi rādītāji uz vienas € skalas; vienīgā daļa — vienreizējā tehnika dotācijas joslā.
NAUDA = [  # (rādītājs — kā tabulas 1. kolonnā, summa, paskaidrojums)
    ("Sākumā apstiprinātais LSM budžets", 51_359_239, "Ar to LSM sāka 2025. gadu"),
    ("SEPLP budžeta izpilde LSM programmā", 68_957_903, f"Plāns 69{NB}123{NB}115{NB}€"),
    ("LSM saņemtā valsts dotācija", 69_046_512, "LSM gada pārskata 28. piezīme"),
    ("LSM neto apgrozījums", 52_770_755, "Gada pārskata ieņēmumu rādītājs"),
]
TEHN = 10_289_846  # …no dotācijas vienreizēja tehnika
assert len(NAUDA) == 4 and TEHN < NAUDA[2][1]
NMAX = 70_000_000
T1 = "LSM nauda 2025. gadā: dažādi rādītāji, nevis viena summa"
SUB1 = "Katra josla ir cits rādītājs. Joslas nav viena veseluma daļas, un tās nedrīkst saskaitīt."
KEY1 = ('<span><i class="sw night"></i>rādītājs (katrs atsevišķi)</span>'
        '<span><i class="sw hatch"></i>…no dotācijas vienreizēja tehnika (pārvietojamās televīzijas stacijas)</span>')
NOTE1 = ""
SRC1 = "Avots: LSM 2025. gada pārskats; SEPLP 2025. gada budžeta izpildes analīze · atmina.lv"
NCSS = """
.n .rows { display:grid; grid-template-columns:440px 1fr 230px; align-items:center; column-gap:28px; row-gap:26px; margin-block-start:34px; }
.n .r { display:contents; }
.n .nm { text-align:end; font-size:25px; font-weight:600; line-height:1.2; }
.n .nm small { display:block; font-size:19px; font-weight:400; color:var(--muted); margin-block-start:2px; }
.n .val { font-family:var(--serif); font-weight:600; font-size:29px; white-space:nowrap; }
.n .lane { position:relative; block-size:46px; }
.n .bar { position:absolute; inset-block:0; inset-inline-start:0; background:var(--night); border-radius:0 4px 4px 0; }
.n .seg { position:absolute; inset-block:0; inset-inline-end:0; border-inline-start:2px solid var(--paper); border-radius:0 4px 4px 0; }
.n .sub-r .nm { font-weight:400; font-size:22px; color:var(--ink-2); }
.n .sub-r .val { font-size:24px; color:var(--ink-2); }
.n .brk { position:relative; block-size:28px; }
.n .brk b { position:absolute; inset-block-start:0; block-size:16px; border:2px solid var(--ink-2); border-block-start:0; }
.n .sub-r { margin-block-start:-14px; }
.n.m .mrows { display:grid; gap:34px; }
.n.m .r { display:grid; gap:12px; border-block-start:1px solid var(--rule); padding-block-start:16px; }
.n.m .nm { text-align:start; font-size:36px; }
.n.m .nm small { font-size:28px; }
.n.m .val { font-size:42px; }
.n.m .lane { block-size:46px; }
.n.m .sub { margin-block-start:-14px; }
.n.m .seg-lbl { display:flex; justify-content:space-between; align-items:baseline; gap:16px; font-size:30px; color:var(--ink-2); }
.n.m .seg-lbl b { font-family:var(--serif); font-weight:600; font-size:36px; white-space:nowrap; }
.n.m .brk { block-size:22px; margin-block-start:-4px; }
.n.m .brk b { border-width:3px; }
"""


def _lane(amount, with_seg):
    w = 100 * amount / NMAX
    seg = f'<i class="seg hatch" style="inline-size:{100 * TEHN / amount:.3f}%"></i>' if with_seg else ""
    return f'<div class="lane"><div class="bar" style="inline-size:{w:.3f}%">{seg}</div></div>'


def _brk():
    tot = NAUDA[2][1]
    return (f'<div class="brk"><b style="inset-inline-start:{100 * (tot - TEHN) / NMAX:.3f}%;'
            f'inline-size:{100 * TEHN / NMAX:.3f}%"></b></div>')


def nauda_d():
    rows = []
    for i, (nm, a, expl) in enumerate(NAUDA):
        rows.append(f'<div class="r"><div class="nm">{nm}<small>{expl}</small></div>{_lane(a, i == 2)}<div class="val num">{eur(a)}</div></div>')
        if i == 2:
            rows.append(f'<div class="r sub-r"><div class="nm">…no tās vienreizēja tehnika</div>{_brk()}<div class="val num">{eur(TEHN)}</div></div>')
    axis = ticks(range(0, 71, 10), 70, lambda x: f"{x}{NB}milj.{NB}€" if x == 70 else str(x))
    body = f"""<h2>{T1}</h2>
<p class="sub">{SUB1}</p>
<div class="key">{KEY1}</div>
<div class="rows">{"".join(rows)}<div></div><div class="axis">{axis}</div><div></div></div>
{foot(NOTE1, SRC1)}"""
    return page(T1, "d n", NCSS, body, "1. grafiks")


def nauda_m():
    rows = []
    for i, (nm, a, expl) in enumerate(NAUDA):
        extra = ""
        if i == 2:
            extra = (f'{_brk()}<div class="seg-lbl"><span>…no tās vienreizēja tehnika</span><b class="num">{eur(TEHN)}</b></div>')
        rows.append(f'<div class="r"><div class="nm">{nm}<small>{expl}</small></div><div class="val num">{eur(a)}</div>{_lane(a, i == 2)}{extra}</div>')
    body = f"""<h2>{T1}</h2>
<p class="sub">{SUB1}</p>
<div class="key">{KEY1}</div>
<div class="mrows"><div class="scale num"><span>0</span><span>35</span><span>70{NB}milj.{NB}€</span></div>{"".join(rows)}</div>
{foot(NOTE1, SRC1)}"""
    return page(T1, "m n", NCSS, body, "1. grafiks (mobilā)")


# ======================= 2. ĒTERS =======================
ETERS = [  # (satura grupa, LTV1, LTV7)
    ("Ziņas, intervijas un aktualitātes", "33,6", "18,8"),
    ("Ārvalstu filmas un seriāli", "22,5", "34,2"),
    ("Dokumentālais, izzinošais un dzīvesveida saturs", "9,3", "24,9"),
    ("Kultūra un māksla", "14,4", "3,2"),
    ("Mūzika, izklaide un viktorīnas", "8,1", "6,6"),
    ("Sports", "3,0", "9,0"),
    ("Bērnu saturs", "4,9", "0,1"),
    ("Latvijas filmas un seriāli", "2,3", "2,4"),
    ("Reliģija, himna un izlozes", "1,8", "0,8"),
]
assert len(ETERS) == 9
assert abs(sum(num(a) for _, a, _ in ETERS) - 100) <= 0.15 and abs(sum(num(b) for _, _, b in ETERS) - 100) <= 0.15
EMAX = 40
T2 = "Satura grupas LTV1 un LTV7, visa diennakts"
SUB2 = "Daļa no kanāla raidlaika četrās nedēļās (30.09.–27.10.2026.)"
KEY2 = '<span><i class="sw ltv1"></i>LTV1</span><span><i class="sw ltv7"></i>LTV7</span>'
NOTE2 = "Žanrus raidījumiem piešķīrām paši. Analizēta publicētā programma, nevis faktiskais ēters."
SRC2 = SRCV
ECSS = """
.e .rows { display:grid; grid-template-columns:480px 1fr; align-items:center; column-gap:28px; row-gap:18px; margin-block-start:30px; }
.e .r { display:contents; }
.e .nm { text-align:end; font-size:23px; font-weight:600; line-height:1.2; }
.e .pair { display:grid; gap:4px; border-inline-start:2px solid var(--ink); padding-block:3px; }
.e .bare { gap:12px; }
.e .bare > i { block-size:24px; }
.e .bare > span { font-size:21px; }
.e.m .mrows { display:grid; gap:26px; }
.e.m .r { display:grid; gap:10px; border-block-start:1px solid var(--rule); padding-block-start:14px; }
.e.m .nm { text-align:start; font-size:34px; }
.e.m .pair { gap:6px; }
.e.m .bare { gap:14px; }
.e.m .bare > i { block-size:36px; }
.e.m .bare > span { font-size:32px; }
"""


def _pair(a, b):
    out = []
    for cls, v in (("ltv1", a), ("ltv7", b)):
        out.append(f'<div class="bare"><i class="{cls}" style="inline-size:calc({num(v) / EMAX:.4f} * (100% - 110px))"></i>'
                   f'<span class="num">{pct(v)}</span></div>')
    return f'<div class="pair">{"".join(out)}</div>'


def eters_d():
    rows = "".join(f'<div class="r"><div class="nm">{nm}</div>{_pair(a, b)}</div>' for nm, a, b in ETERS)
    body = f"""<h2>{T2}</h2>
<p class="sub">{SUB2}</p>
<div class="key">{KEY2}</div>
<div class="rows">{rows}</div>
{foot(NOTE2, SRC2)}"""
    return page(T2, "d e", ECSS, body, "2. grafiks")


def eters_m():
    rows = "".join(f'<div class="r"><div class="nm">{nm}</div>{_pair(a, b)}</div>' for nm, a, b in ETERS)
    body = f"""<h2>{T2}</h2>
<p class="sub">{SUB2}</p>
<div class="key row">{KEY2}</div>
<div class="mrows">{rows}</div>
{foot(NOTE2, SRC2)}"""
    return page(T2, "m e", ECSS, body, "2. grafiks (mobilā)")


# ======================= 3. BALSOJUMI 1434/Lp14 =======================
BALS = [  # (datums, balsojums — kā raksta tabulā, par, pret, atturas, galīgais?)
    ("23.07.2026.", "Nodošana komisijām", 53, 0, 31, False),
    ("15.10.2026.", "Atzīšana par steidzamu", 74, 8, 0, False),
    ("15.10.2026.", "1. lasījums", 86, 0, 0, False),
    ("22.10.2026.", "Brantes priekšlikums Nr.&nbsp;2 (atsevišķi ziņu dienesti) — pieņemts", 53, 13, 17, False),
    ("22.10.2026.", "Kalniņas-Lukaševicas priekšlikums Nr.&nbsp;5 (atsevišķas redakcijas ar savu vadību) — noraidīts", 1, 24, 51, False),
    ("22.10.2026.", "Nodot atpakaļ komisijai — noraidīts", 31, 53, 2, False),
    ("22.10.2026.", "2. (galīgais) lasījums — likums", 76, 4, 8, True),
]
assert len(BALS) == 7 and all(p + pr + a <= 100 for _, _, p, pr, a, _ in BALS)
T3 = "Likumprojekts 1434/Lp14: visi septiņi balsojumi"
SUB3 = "Arī procedurālie balsojumi. Joslas garums — balsojušo deputātu skaits."
KEY3 = ('<span><i class="sw par"></i>par</span><span><i class="sw pret"></i>pret</span>'
        '<span><i class="sw atturas"></i>atturas</span>')
NOTE3 = "Valsts prezidents likumu izsludināja 30. oktobrī; tas stājās spēkā 31. oktobrī."
SRC3 = "Avots: Saeimas balsojumi · atmina.lv"
BCSS = """
.b .rows { display:grid; grid-template-columns:150px 530px 1fr 76px 76px 96px; align-items:center; column-gap:22px; row-gap:18px; margin-block-start:28px; }
.b .r { display:contents; }
.b .dt { font-family:var(--mono); font-weight:500; font-size:17px; color:var(--muted); }
.b .nm { font-size:22px; line-height:1.25; }
.b .fin .nm { font-weight:700; }
.b .trk { block-size:34px; }
.b .fin .trk { block-size:44px; }
.b .c { text-align:end; font-family:var(--serif); font-weight:600; font-size:28px; }
.b .hd { font-family:var(--mono); font-weight:500; font-size:16px; color:var(--muted); text-align:end; letter-spacing:0.04em; }
.b .zero { color:var(--muted); font-weight:400; }
.b.m .mrows { display:grid; gap:28px; }
.b.m .r { display:grid; gap:12px; border-block-start:1px solid var(--rule); padding-block-start:16px; }
.b.m .dt { font-size:28px; }
.b.m .nm { font-size:34px; }
.b.m .trk { block-size:44px; } .b.m .fin .trk { block-size:56px; }
.b.m .cnt { display:flex; gap:30px; font-size:30px; color:var(--ink-2); }
.b.m .cnt b { font-family:var(--serif); font-weight:600; font-size:38px; color:var(--ink); margin-inline-end:8px; }
"""


def _vbar(p, pr, a):
    segs = "".join(f'<i class="{c}" style="inline-size:calc({v}% - 2px)"></i>' for c, v in (("par", p), ("pret", pr), ("atturas", a)) if v)
    return f'<div class="trk"><div class="fill">{segs}</div></div>'


def _c(v):
    return f'<div class="c num{" zero" if v == 0 else ""}">{v}</div>'


def bals_d():
    rows = []
    for dt, nm, p, pr, a, fin in BALS:
        rows.append(f'<div class="r{" fin" if fin else ""}"><div class="dt num">{dt}</div><div class="nm">{nm}</div>'
                    f'{_vbar(p, pr, a)}{_c(p)}{_c(pr)}{_c(a)}</div>')
    axis = ticks((0, 25, 50, 75, 100), 100, str)
    hd = '<div></div><div></div><div></div><div class="hd">par</div><div class="hd">pret</div><div class="hd">atturas</div>'
    body = f"""<h2>{T3}</h2>
<p class="sub">{SUB3}</p>
<div class="key">{KEY3}</div>
<div class="rows">{hd}{"".join(rows)}<div></div><div></div><div class="axis">{axis}</div><div></div><div></div><div></div></div>
{foot(NOTE3, SRC3)}"""
    return page(T3, "d b", BCSS, body, "3. grafiks")


def bals_m():
    rows = []
    for dt, nm, p, pr, a, fin in BALS:
        rows.append(f'<div class="r{" fin" if fin else ""}"><div class="dt num">{dt}</div><div class="nm">{nm}</div>{_vbar(p, pr, a)}'
                    f'<div class="cnt num"><span><b>{p}</b>par</span><span><b>{pr}</b>pret</span><span><b>{a}</b>atturas</span></div></div>')
    body = f"""<h2>{T3}</h2>
<p class="sub">{SUB3}</p>
<div class="key row">{KEY3}</div>
<div class="mrows"><div class="scale num"><span>0</span><span>50</span><span>100</span></div>{"".join(rows)}</div>
{foot(NOTE3, SRC3)}"""
    return page(T3, "m b", BCSS, body, "3. grafiks (mobilā)")


OUT.mkdir(parents=True, exist_ok=True)
ALL = [("vaks", vaks_d, 1600, 900), ("vaks-mob", vaks_m, 1080, None),
       ("1-nauda", nauda_d, 1600, None), ("1-nauda-mob", nauda_m, 1080, None),
       ("2-eters", eters_d, 1600, None), ("2-eters-mob", eters_m, 1080, None),
       ("3-balsojumi", bals_d, 1600, None), ("3-balsojumi-mob", bals_m, 1080, None)]
jobs = []
for kind, fn, w, h in ALL:
    f = OUT / f"{SLUG}-{kind}.html"
    f.write_text(fn(), encoding="utf-8")
    print(f)
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
