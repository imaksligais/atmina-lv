"""Vāks + 2 datu grafiki «Atradumam» maksliga-intelekta-centrs-2026. Desktop 1600 px (vāks 1600×900) + mobilā (1080 px).
Visi skaitļi ierakstīti ar roku no content/analizes/maksliga-intelekta-centrs-2026.md — jaunu skaitļu nav.
Kopīgais CSS un renderis pārņemts no scripts/oneoff-content/lsm_2026_11_viz.py (good-css + dataviz).
Krāsas: VARAM #2d5aa0 / Aizsardzības ministrija #b5541c — pāris, ko dataviz validators jau pārbaudīja LSM rakstā
(ALL CHECKS PASS, CVD ΔE 20,9); plāns = tās pašas krāsas svītrojums, jo tā nav izmaksāta nauda.
Palaišana: PYTHONUTF8=1 .venv/Scripts/python.exe scripts/oneoff-content/mic_2026_11_viz.py [--render]"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / ".scratch/mic-viz"
IMG = ROOT / "output/images/analizes"
SLUG = "maksliga-intelekta-centrs-2026"
F = "../../output/atmina/assets/fonts/"  # relatīvi no .scratch/mic-viz/
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
<!-- {comment}: {SLUG}. Ģenerēts ar scripts/oneoff-content/mic_2026_11_viz.py. -->
<html lang="lv"><head><meta charset="utf-8"><title>{title}</title><style>{CSS}{extra_css}</style></head>
<body class="{body_cls}">
{body}
</body></html>"""


def foot(note, src):
    return f'<div class="foot">{f"<p>{note}</p>" if note else ""}<div class="src">{src}</div></div>'


def ticks(vals, maxv, fmt):
    return "".join(f'<span class="num" style="inset-inline-start:{100 * v / maxv:.3f}%">{fmt(v)}</span>' for v in vals)


# ======================= VĀKS: četri lauciņi =======================
# Katrs lauciņš ir cits mērs. Vienīgās īstās daļas: 370 000 + 46 000 = 416 000 (izmaksāts);
# 184 000 ir plāns — svītrots un aiz izmaksātā, ar parakstu «plāns».
TV = "Mākslīgā intelekta centrs"
SUBV = "Nauda, vadība un rezultāti 19 mēnešos — no valsts pārskatiem, reģistriem un paziņojumiem"
SRCV = "Avoti: Valsts kanceleja, MK rīkojumi Nr. 193 un Nr. 39, VARAM, VDAA, LV portāls, LSM · atmina.lv"
VARAM, AM_PAID, AM_PLAN = 370_000, 46_000, 184_000
PAID = VARAM + AM_PAID
assert PAID == 416_000 and AM_PAID + AM_PLAN == 230_000
SCALE = 600_000
VCSS = """
.v .grid { display:grid; grid-template-columns:1fr 1fr; gap:0 72px; margin-block-start:auto; }
.v .t { display:grid; gap:10px; align-content:start; padding-block:24px 26px; border-block-start:2px solid var(--ink); }
.v .k { font-size:19px; color:var(--red); }
.v .big { font-family:var(--serif); font-weight:700; font-size:72px; line-height:1; }
.v .big small { font-size:38px; font-weight:600; }
.v .n { font-size:22px; color:var(--ink-2); line-height:1.3; }
.v .mini { display:flex; block-size:22px; gap:2px; background:var(--track); border-radius:0 4px 4px 0; }
.v .mini > i { display:block; block-size:100%; background:var(--c); flex:none; }
.v .mini > i:last-child { border-start-end-radius:4px; border-end-end-radius:4px; }
.v .steps { display:flex; align-items:baseline; gap:18px; }
.v .steps .arr { font-size:40px; color:var(--muted); }
.v.m .grid { grid-template-columns:1fr; }
.v.m .t { gap:16px; padding-block:30px 34px; }
.v.m .k { font-size:26px; } .v.m .big { font-size:92px; } .v.m .big small { font-size:46px; }
.v.m .n { font-size:32px; } .v.m .mini { block-size:34px; }
.v.m .steps .arr { font-size:52px; }
"""


def _money_bar():
    # Vākā josla = TIKAI izmaksātais (416 000 = 100 %), lai plāns neizskatītos pēc daļas (quality-reviewer 11-02).
    return (f'<div class="mini"><i class="ltv1" style="inline-size:calc({100 * VARAM / PAID:.3f}% - 1px)"></i>'
            f'<i class="ltv7" style="inline-size:calc({100 * AM_PAID / PAID:.3f}% - 1px)"></i></div>')


def _tiles():
    return f"""<div class="grid">
<div class="t"><span class="k label">Nauda</span><div class="big num">416{NB}000<small>{NB}€</small></div>{_money_bar()}
<p class="n">izmaksāts līdz 15.07.2026.: VARAM 370{NB}000 + Aizsardzības ministrija 46{NB}000. Vēl 184{NB}000 ir tikai plānā, un joslā tie nav</p></div>
<div class="t"><span class="k label">Laiks</span><div class="big num">19<small>{NB}mēneši</small></div>
<p class="n">no dibināšanas (02.04.2025.) līdz ministra vārdiem «kapacitāte absolūti šobrīd nevelk» (01.11.2026.)</p></div>
<div class="t"><span class="k label">Vadība</span><div class="big num">2<small>{NB}direktores</small></div>
<p class="n">Čerņecka iecelta 08.2025.; 12.2025. padome lēma par maiņu, kopš tā laika centru vada Puce</p></div>
<div class="t"><span class="k label">Smilškaste</span><div class="big num steps"><span>10</span><span class="arr">→</span><span>3</span><span class="arr">→</span><span>2</span></div>
<p class="n">pieteikumi → atlasīti → projekti, ar kuriem centrs strādā</p></div>
</div>"""


def vaks_d():
    body = f"""<div class="brand">{LOGO}atmina.lv<span class="label">Atradums · MIC</span></div>
<h1>{TV}</h1>
<p class="sub">{SUBV}</p>
{_tiles()}
{foot("", SRCV)}"""
    return page(TV, "d v", VCSS + "body.d.v { block-size:900px; }", body, "Vāks")


def vaks_m():
    body = f"""<div class="brand">{LOGO}atmina.lv<span class="label">Atradums</span></div>
<h1>{TV}</h1>
<p class="sub">{SUBV}</p>
{_tiles()}
{foot("", SRCV)}"""
    return page(TV, "m v", VCSS, body, "Vāks (mobilā)")


# ======================= 1. NAUDA =======================
T1 = f"Valsts nauda centram: 416{NB}000{NB}€ izmaksāti, 184{NB}000{NB}€ plānā"
SUB1 = "Valsts kancelejas pārskats par maksājumiem nodibinājumiem, dati līdz 15.07.2026."
KEY1 = ('<span><i class="sw ltv1"></i>VARAM / VDAA (MK rīkojums Nr. 193)</span>'
        '<span><i class="sw ltv7"></i>Aizsardzības ministrija (MK rīkojums Nr. 39)</span>'
        '<span><i class="sw ltv7 hatch7"></i>plānots 2026. g. 2. pusgadā — nav izmaksāts</span>')
NOTE1 = (f"Aizsardzības nauda nāk no apakšprogrammas «Nacionālo bruņoto spēku uzturēšana»; rīkojumā — līdz 230{NB}000{NB}€. "
         f"Intervijā direktore nosauca 280{NB}000{NB}€; šo summu nesummējam.")
SRC1 = "Avots: Valsts kanceleja, pārskats par maksājumiem biedrībām un nodibinājumiem (2026) · atmina.lv"
MONEY = [  # (nosaukums, paskaidrojums, [(klase, summa)], kopsumma teksts)
    ("VARAM / VDAA, 2025", "Centra izveidei", [("ltv1", VARAM)], eur(VARAM)),
    ("Aizsardzības ministrija, 2026", f"Izmaksāts {eur(AM_PAID)} + plānots {eur(AM_PLAN)}",
     [("ltv7", AM_PAID), ("ltv7 hatch7", AM_PLAN)], f"līdz {eur(AM_PAID + AM_PLAN)}"),
]
NCSS = """
.hatch7 { background:repeating-linear-gradient(45deg, var(--ltv7) 0 4px, color-mix(in oklch, var(--ltv7) 25%, var(--paper)) 4px 10px) !important; }
.n .rows { display:grid; grid-template-columns:400px 1fr 230px; align-items:center; column-gap:28px; row-gap:30px; margin-block-start:36px; }
.n .r { display:contents; }
.n .nm { text-align:end; font-size:25px; font-weight:600; line-height:1.2; }
.n .nm small { display:block; font-size:19px; font-weight:400; color:var(--muted); margin-block-start:2px; }
.n .val { font-family:var(--serif); font-weight:600; font-size:29px; white-space:nowrap; }
.n .val small { display:block; font-family:var(--sans); font-weight:400; font-size:19px; color:var(--muted); }
.n.m .val small { font-size:28px; }
.n .tot .nm { font-weight:700; } .n .tot .val { font-weight:700; }
.n .lane { display:flex; gap:2px; block-size:50px; }
.n .lane > i { display:block; block-size:100%; background:var(--c); flex:none; }
.n .lane > i:last-child { border-start-end-radius:4px; border-end-end-radius:4px; }
.n .tot .lane { block-size:62px; }
.n .sep { grid-column:1 / -1; border-block-start:1px solid var(--rule); }
.n.m .mrows { display:grid; gap:34px; }
.n.m .r { display:grid; gap:12px; border-block-start:1px solid var(--rule); padding-block-start:16px; }
.n.m .nm { text-align:start; font-size:36px; }
.n.m .nm small { font-size:28px; }
.n.m .val { font-size:42px; }
.n.m .lane { block-size:50px; } .n.m .tot .lane { block-size:62px; }
"""


def _lane(parts):
    return '<div class="lane">' + "".join(
        f'<i class="{c}" style="inline-size:calc({100 * a / SCALE:.3f}% - 2px)"></i>' for c, a in parts) + "</div>"


def _money_rows():
    rows = [(nm, expl, parts, val, False) for nm, expl, parts, val in MONEY]
    rows.append(("Kopā", f"Izmaksāts {eur(PAID)}; vēl {eur(AM_PLAN)} plānā",
                 [("ltv1", VARAM), ("ltv7", AM_PAID), ("ltv7 hatch7", AM_PLAN)], f"{eur(PAID)}<small>izmaksāts<br>svītrotais — plāns</small>", True))
    return rows


def nauda_d():
    rows = []
    for nm, expl, parts, val, tot in _money_rows():
        if tot:
            rows.append('<div class="sep"></div>')
        rows.append(f'<div class="r{" tot" if tot else ""}"><div class="nm">{nm}<small>{expl}</small></div>'
                    f'{_lane(parts)}<div class="val num">{val}</div></div>')
    axis = ticks(range(0, 601, 100), 600, lambda x: f"{x}{NB}000{NB}€" if x == 600 else (f"{x}{NB}000" if x else "0"))
    body = f"""<h2>{T1}</h2>
<p class="sub">{SUB1}</p>
<div class="key">{KEY1}</div>
<div class="rows">{"".join(rows)}<div></div><div class="axis">{axis}</div><div></div></div>
{foot(NOTE1, SRC1)}"""
    return page(T1, "d n", NCSS, body, "1. grafiks")


def nauda_m():
    rows = "".join(
        f'<div class="r{" tot" if tot else ""}"><div class="nm">{nm}<small>{expl}</small></div>'
        f'<div class="val num">{val}</div>{_lane(parts)}</div>'
        for nm, expl, parts, val, tot in _money_rows())
    body = f"""<h2>{T1}</h2>
<p class="sub">{SUB1}</p>
<div class="key">{KEY1}</div>
<div class="mrows"><div class="scale num"><span>0</span><span>300{NB}000</span><span>600{NB}000{NB}€</span></div>{rows}</div>
{foot(NOTE1, SRC1)}"""
    return page(T1, "m n", NCSS, body, "1. grafiks (mobilā)")


# ======================= 2. SMILŠKASTE =======================
FUNNEL = [  # (skaits, ko nozīmē, avots/datums)
    (10, "projekti pieteicās smilškastei", "LV portāls, 12.05.2026."),
    (3, "projektus atlasīja", "LV portāls, 12.05.2026."),
    (2, "projekti, ar kuriem centrs strādā", "centra vietne 08.2026.; LSM, 01.11.2026."),
]
T2 = f"Smilškaste: no 10{NB}pieteikumiem līdz 2{NB}projektiem"
SUB2 = "Smilškaste — vide, kurā uzņēmumi uzraudzībā pārbauda savus mākslīgā intelekta risinājumus"
NOTE2 = "Trešajā projektā, pēc LSM rakstītā, izrādījies, ka smilškastē nav ko testēt. Projektus un iesniedzējus mēs nevērtējam."
SRC2 = "Avoti: LV portāls, Mākslīgā intelekta centra vietne, LSM · atmina.lv"
FCSS = """
.f .rows { display:grid; grid-template-columns:1fr; row-gap:22px; margin-block-start:36px; }
.f .r { display:grid; grid-template-columns:110px 1fr; align-items:center; column-gap:28px; }
.f .cnt { font-family:var(--serif); font-weight:700; font-size:64px; text-align:end; line-height:1; }
.f .sq { display:flex; gap:10px; }
.f .sq > i { inline-size:56px; aspect-ratio:1; background:var(--night); border-radius:6px; }
.f .lbl { grid-column:2; font-size:25px; color:var(--ink); margin-block-start:10px; }
.f .lbl small { color:var(--muted); font-family:var(--mono); font-size:16px; letter-spacing:0.04em; margin-inline-start:14px; }
.f.m .rows { row-gap:30px; margin-block-start:0; }
.f.m .r { grid-template-columns:90px 1fr; column-gap:24px; border-block-start:1px solid var(--rule); padding-block-start:18px; }
.f.m .cnt { font-size:72px; }
.f.m .sq { flex-wrap:wrap; gap:10px; }
.f.m .sq > i { inline-size:70px; }
.f.m .lbl { font-size:32px; }
.f.m .lbl small { display:block; font-size:24px; margin-inline-start:0; margin-block-start:6px; }
"""


def _funnel():
    return "".join(
        f'<div class="r"><div class="cnt num">{n}</div><div class="sq">{"<i></i>" * n}</div>'
        f'<div class="lbl">{t}<small>{s}</small></div></div>' for n, t, s in FUNNEL)


def smils_d():
    body = f"""<h2>{T2}</h2>
<p class="sub">{SUB2}</p>
<div class="rows">{_funnel()}</div>
{foot(NOTE2, SRC2)}"""
    return page(T2, "d f", FCSS, body, "2. grafiks")


def smils_m():
    body = f"""<h2>{T2}</h2>
<p class="sub">{SUB2}</p>
<div class="rows">{_funnel()}</div>
{foot(NOTE2, SRC2)}"""
    return page(T2, "m f", FCSS, body, "2. grafiks (mobilā)")


HATCH = ".hatch7 { background:repeating-linear-gradient(45deg, var(--ltv7) 0 4px, color-mix(in oklch, var(--ltv7) 25%, var(--paper)) 4px 10px) !important; }"
VCSS += HATCH

OUT.mkdir(parents=True, exist_ok=True)
ALL = [("vaks", vaks_d, 1600, 900), ("vaks-mob", vaks_m, 1080, None),
       ("1-nauda", nauda_d, 1600, None), ("1-nauda-mob", nauda_m, 1080, None),
       ("2-smilskaste", smils_d, 1600, None), ("2-smilskaste-mob", smils_m, 1080, None)]

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
