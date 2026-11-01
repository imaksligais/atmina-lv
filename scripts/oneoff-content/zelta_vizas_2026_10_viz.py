"""Četri attēli X pavedienam «Zelta vīzas — trīs balsojumi 29.10.» (docs/tweet_bank/2026-10-30-zelta-vizas-balsojumi-social.md).
Skaitļi nāk tieši no DB (saeima_votes 8577/8637/8638 + saeima_individual_votes) un pirms zīmēšanas tiek salīdzināti ar total_*.
Stils pēc src/graphics/templates/izpete-shema.html un scripts/oneoff-content/pinned_2026_10_viz.py; 1600×900, teksts ≥28 px.
Palaišana: .venv/Scripts/python.exe scripts/oneoff-content/zelta_vizas_2026_10_viz.py"""
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_HTML = ROOT / "docs/tweet_bank"
OUT_PNG = ROOT / "output/images/threads"
DAY = "2026-10-30"
TOTAL = 4
F = "../../output/atmina/assets/fonts/"

VOTES = [  # (id, laiks, nosaukums, procedūras?)
    (8577, "09:11", "Iekļaut darba kārtībā", True),
    (8637, "18:32", "Atzīt par steidzamu", True),
    (8638, "18:37", "1. lasījums", False),
]
BALLOTS = ["Par", "Pret", "Atturas", "Nebalsoja"]
BALLOT_LABEL = {"Par": "par", "Pret": "pret", "Atturas": "atturas", "Nebalsoja": "nebalsoja"}
GROUPS = [
    ("Līdzšinējā koalīcija", ["NA", "JV", "AS", "ZZS"]),
    ("Opozīcija", ["PRO", "LPV"]),
    ("Pie frakcijām nepiederošie", [None]),
]
FACTION_NAME = {
    "NA": "Nacionālā apvienība", "JV": "Jaunā Vienotība", "AS": "Apvienotais saraksts",
    "ZZS": "Zaļo un Zemnieku savienība", "PRO": "Progresīvie", "LPV": "Latvija pirmajā vietā",
    None: "Nepiederošie",
}
FACTION_SHORT = {k: (k or "—") for k in FACTION_NAME}


def load():
    db = sqlite3.connect(ROOT / "data/atmina.db")
    data = {}
    for vid, *_ in VOTES:
        tot = db.execute("select total_par,total_pret,total_atturas,total_nebalso,result from saeima_votes where id=?",
                         (vid,)).fetchone()
        rows = db.execute("select faction, vote, count(*) from saeima_individual_votes where vote_id=? group by 1,2",
                          (vid,)).fetchall()
        by = {}
        for fac, vote, n in rows:
            by.setdefault(fac, dict.fromkeys(BALLOTS, 0))[vote] = n
        sums = [sum(f[b] for f in by.values()) for b in BALLOTS]
        assert sums == list(tot[:4]), (vid, sums, tot)  # frakciju summa = oficiālais kopsavilkums
        data[vid] = {"tot": dict(zip(BALLOTS, tot[:4])), "result": tot[4], "by": by}
    return data


D = load()

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
  --par: oklch(50% 0.13 150);       /* vietnes --green #1a7a3a */
  --pret: oklch(50.2% 0.189 27);    /* vietnes --red #b42318 */
  --att: oklch(56% 0.12 80);        /* vietnes --yellow #8a6500, nedaudz gaišāks */
  --neb: oklch(70% 0.02 88);
  --on-night: oklch(96% 0.015 90);
  --on-night-muted: color-mix(in oklch, var(--on-night) 68%, var(--night));
  --on-night-rule: color-mix(in oklch, var(--on-night) 20%, transparent);
  --serif: 'Source Serif 4', Georgia, serif;
  --mono: 'JetBrains Mono', ui-monospace, monospace;
  --sans: "Segoe UI", Roboto, sans-serif;
  font-synthesis: none; -webkit-font-smoothing: antialiased; text-wrap: pretty; overflow-wrap: break-word;
}}
body {{ inline-size:1600px; block-size:900px; background:var(--paper); color:var(--ink); font-family:var(--sans);
       display:grid; grid-template-columns:400px 1fr; overflow:clip; }}
.num {{ font-variant-numeric: lining-nums tabular-nums; }}
.lead {{ background:var(--night); color:var(--on-night); padding:48px 44px 44px; display:flex; flex-direction:column; gap:30px; }}
.brand {{ display:flex; align-items:center; gap:14px; font-family:var(--serif); font-weight:700; font-size:34px; }}
.brand svg {{ flex:none; inline-size:42px; block-size:42px; }}
.lead h1 {{ font-family:var(--serif); font-weight:700; font-size:64px; line-height:1.02; letter-spacing:-0.015em; text-wrap:balance; }}
.lead .dek {{ font-family:var(--serif); font-size:31px; line-height:1.3; color:var(--on-night-muted); }}
.lead .step {{ margin-block-start:auto; border-block-start:1px solid var(--on-night-rule); padding-block-start:22px;
              font-family:var(--mono); font-weight:500; font-size:28px; letter-spacing:0.06em; color:var(--on-night-muted); }}
.body {{ padding:52px 52px 44px 56px; display:flex; flex-direction:column; gap:34px; }}
.foot {{ margin-block-start:auto; border-block-start:2px solid var(--rule); padding-block-start:22px;
         display:flex; justify-content:space-between; align-items:baseline; gap:28px; }}
.foot p {{ font-size:28px; line-height:1.3; color:var(--ink-2); }}
.foot .url {{ font-family:var(--mono); font-weight:500; font-size:30px; color:var(--ink); white-space:nowrap; }}
.legend {{ display:flex; flex:none; gap:24px; font-size:28px; color:var(--ink-2); }}
.legend span {{ display:inline-flex; align-items:baseline; gap:10px; }}
.legend i {{ flex:none; inline-size:1cap; block-size:1cap; border-radius:4px; }}
.legend .neb, .seg.neb, .dot.neb {{ background:transparent; border:3px solid var(--neb); }}
.par {{ background:var(--par); }} .pret {{ background:var(--pret); }} .att {{ background:var(--att); }}
"""
CLS = {"Par": "par", "Pret": "pret", "Atturas": "att", "Nebalsoja": "neb"}

LOGO = ('<svg viewBox="0 0 64 64" aria-hidden="true"><circle cx="27" cy="27" r="17" fill="none" stroke="#f7f3e8" stroke-width="5.5"/>'
        '<line x1="40.5" y1="40.5" x2="52" y2="52" stroke="#f7f3e8" stroke-width="5.5" stroke-linecap="round"/>'
        '<circle cx="27" cy="27" r="6" fill="#EF5350"/></svg>')


def page(n, title, dek, body, css=""):
    return f"""<!doctype html><html lang="lv"><head><meta charset="utf-8"><style>{CSS}{css}</style></head><body>
<aside class="lead"><div class="brand">{LOGO}atmina.lv</div><h1>{title}</h1><p class="dek">{dek}</p>
<div class="step num">{n}/{TOTAL} · 29.10.2026</div></aside>
<main class="body">{body}</main></body></html>"""


def legend(with_att=True):
    items = [("par", "par"), ("pret", "pret")] + ([("att", "atturas")] if with_att else []) + [("neb", "nebalsoja")]
    return '<div class="legend">' + "".join(f'<span><i class="{c}"></i>{t}</span>' for c, t in items) + "</div>"


pages = {}

# ---------------- 1. Ko piedāvāja -----------------
css1 = """
.kicker { font-family:var(--mono); font-weight:500; font-size:28px; letter-spacing:0.06em; color:var(--muted); }
.flow { display:grid; grid-template-columns:1.1fr 1fr 56px 1.2fr; gap:22px; align-items:stretch; }
.box { border:2px solid var(--rule); border-radius:14px; padding:26px 26px 24px; background:oklch(98.5% 0.008 90);
       display:flex; flex-direction:column; gap:10px; }
.box b { font-family:var(--serif); font-weight:700; font-size:56px; white-space:nowrap; line-height:1; letter-spacing:-0.01em; }
.box span { font-size:28px; line-height:1.28; color:var(--ink-2); }
.box.out { background:var(--ink); border-color:var(--ink); color:var(--paper); }
.box.out b { font-size:38px; line-height:1.1; white-space:normal; hyphens:manual; }
.box.out span { color:color-mix(in oklch, var(--paper) 75%, var(--ink)); }
.arrow { align-self:center; font-family:var(--serif); font-size:70px; color:var(--muted); text-align:center; }
.strike { display:grid; grid-template-columns:auto 1fr; gap:28px; align-items:center; border-block-start:4px solid var(--red); padding-block-start:30px; }
.strike .x { font-family:var(--serif); font-weight:700; font-size:64px; color:var(--red); line-height:1; }
.strike p { font-family:var(--serif); font-size:42px; line-height:1.22; text-wrap:balance; }
.res { display:flex; gap:22px; align-items:baseline; font-size:32px; color:var(--ink-2); }
.res b { font-family:var(--serif); font-size:60px; color:var(--ink); }
"""
t3 = D[8638]["tot"]
body1 = f"""<p class="kicker">ŠOBRĪD IMIGRĀCIJAS LIKUMĀ</p>
<div class="flow">
  <div class="box"><b class="num">150 000 €</b><span>vismaz tik liels ieguldījums valsts izveidotā alternatīvo ieguldījumu fondā</span></div>
  <div class="box"><b class="num">+10 000 €</b><span>iemaksa valsts budžetā</span></div>
  <div class="arrow">→</div>
  <div class="box out"><b>Termiņ&shy;uzturēšanās atļauja</b><span>ārzemniekam uz laiku līdz pieciem gadiem</span></div>
</div>
<div class="strike"><span class="x">✕</span><p>Progresīvie piedāvāja šo ceļu svītrot, norādot uz drošības, sankciju apiešanas un naudas atmazgāšanas riskiem.</p></div>
<div class="res num">Pirmajā lasījumā noraidīts: <b>{t3['Par']} : {t3['Pret']}</b> («par» : «pret»)</div>"""
pages["1-piedavajums"] = page(1, "«Zelta vīzas»", "Viens likumprojekts, trīs balsojumi 14. Saeimas pēdējā sēdē", body1, css1)

# ---------------- 2. Diena trijos balsojumos -----------------
css2 = """
.rows { display:grid; gap:34px; }
.row { display:grid; grid-template-columns:120px 1fr; gap:26px; }
.time { font-family:var(--mono); font-weight:500; font-size:34px; color:var(--muted); padding-block-start:6px; }
.what { display:flex; justify-content:space-between; align-items:baseline; gap:20px; margin-block-end:12px; }
.what h2 { font-family:var(--serif); font-weight:700; font-size:42px; line-height:1.1; }
.what h2 small { font-family:var(--sans); font-weight:400; font-size:26px; color:var(--muted); margin-inline-start:12px; }
.tag { font-family:var(--mono); font-weight:500; font-size:28px; letter-spacing:0.04em; padding:12px 16px; text-box:trim-both cap alphabetic; border-radius:8px; white-space:nowrap; }
.tag.ok { background:color-mix(in oklch, var(--par) 16%, var(--paper)); color:var(--par); }
.tag.no { background:color-mix(in oklch, var(--pret) 14%, var(--paper)); color:var(--pret); }
.bar { display:flex; gap:4px; block-size:56px; }
.seg { border-radius:6px; display:grid; place-items:center; color:var(--paper); font-weight:700; font-size:30px; }
.seg.neb { color:var(--muted); }
.nums { margin-block-start:8px; font-size:27px; color:var(--ink-2); }
"""
rows = []
for vid, tm, name, proc in VOTES:
    v = D[vid]
    ok = v["result"] == "Pieņemts"
    segs = "".join(
        f'<div class="seg {CLS[b]}" style="flex:{v["tot"][b]}">{v["tot"][b] if v["tot"][b] >= 3 else ""}</div>'
        for b in BALLOTS if v["tot"][b])
    nums = " · ".join(f'{v["tot"][b]} {BALLOT_LABEL[b]}' for b in BALLOTS if v["tot"][b])
    sub = "<small>procedūra</small>" if proc else "<small>konceptuāli</small>"
    rows.append(f"""<div class="row"><div class="time num">{tm}</div><div>
<div class="what"><h2>{name}{sub}</h2><span class="tag {'ok' if ok else 'no'}">{'PIEŅEMTS' if ok else 'NORAIDĪTS'}</span></div>
<div class="bar num">{segs}</div><div class="nums num">{nums}</div></div></div>""")
body2 = f"""<div class="rows">{''.join(rows)}</div>
<div class="foot"><p>Saeimā «atturas» lēmumu bloķē tāpat kā «pret».</p>{legend()}</div>"""
pages["2-diena"] = page(2, "No rīta iekļāva, vakarā noraidīja", "Viena likumprojekta ceļš vienā sēdes dienā", body2, css2)

# ---------------- 3. Frakcijas pirmajā lasījumā -----------------
css3 = """
.grp { display:grid; gap:14px; }
.grp h3 { font-family:var(--mono); font-weight:500; font-size:26px; letter-spacing:0.06em; color:var(--muted); text-transform:uppercase; }
.fr { display:grid; grid-template-columns:110px 1fr 330px; gap:22px; align-items:center; }
.fr .nm { font-family:var(--serif); font-weight:700; font-size:40px; }
.dots { display:flex; flex-wrap:wrap; gap:6px; }
.dot { inline-size:26px; block-size:26px; border-radius:50%; }
.fr .ct { font-size:28px; color:var(--ink-2); }
.wrap { display:grid; gap:26px; }
"""
v3 = D[8638]["by"]
grp_html = []
for gname, facs in GROUPS:
    frs = []
    for fac in facs:
        c = v3.get(fac, dict.fromkeys(BALLOTS, 0))
        dots = "".join(f'<i class="dot {CLS[b]}"></i>' * c[b] for b in BALLOTS)
        ct = ", ".join(f"{c[b]} {BALLOT_LABEL[b]}" for b in BALLOTS if c[b])
        label = "" if fac is None else FACTION_SHORT[fac]
        frs.append(f'<div class="fr"><span class="nm">{label}</span><div class="dots">{dots}</div><span class="ct num">{ct}</span></div>')
    grp_html.append(f'<div class="grp"><h3>{gname}</h3>{"".join(frs)}</div>')
body3 = f"""<div class="wrap">{''.join(grp_html)}</div>
<div class="foot"><p>Viens punkts — viens deputāts. Pirmais lasījums, 18:37.</p>{legend(with_att=False)}</div>"""
pages["3-frakcijas"] = page(3, "Koalīcija sadalījās", "NA un JV vairākums — «par», AS un ZZS — «pret»", body3, css3)

# ---------------- 4. Visi trīs balsojumi pa frakcijām -----------------
css4 = """
.mx { display:grid; grid-template-columns:110px repeat(3, 1fr); column-gap:26px; row-gap:16px; align-items:center; }
.mx .h { font-family:var(--serif); font-weight:700; font-size:30px; line-height:1.1; }
.mx .h small { display:block; font-family:var(--mono); font-weight:500; font-size:24px; color:var(--muted); margin-block-start:4px; }
.mx .nm { font-family:var(--serif); font-weight:700; font-size:34px; }
.mini { display:flex; gap:3px; block-size:40px; }
.mini .seg { border-radius:5px; font-size:24px; display:grid; place-items:center; color:var(--paper); font-weight:700; }
.mini .seg.neb { color:var(--muted); }
.sep { grid-column:1 / -1; border-block-start:2px solid var(--rule); }
"""
facs_all = [f for _, fs in GROUPS for f in fs]
maxn = max(sum(D[vid]["by"].get(f, {}).values()) if D[vid]["by"].get(f) else 0 for vid, *_ in VOTES for f in facs_all)
cells = ['<span></span>'] + [f'<span class="h">{name}<small>{tm}</small></span>' for _, tm, name, _p in VOTES]
for gi, (_, facs) in enumerate(GROUPS):
    if gi:
        cells.append('<span class="sep"></span>')
    for fac in facs:
        cells.append(f'<span class="nm">{"—" if fac is None else FACTION_SHORT[fac]}</span>')
        for vid, *_ in VOTES:
            c = D[vid]["by"].get(fac, dict.fromkeys(BALLOTS, 0))
            n = sum(c.values())
            segs = "".join(f'<div class="seg {CLS[b]}" style="flex:{c[b]}">{c[b] if c[b] >= 2 else ""}</div>'
                           for b in BALLOTS if c[b])
            pad = maxn - n
            if pad:
                segs += f'<div style="flex:{pad}"></div>'
            cells.append(f'<div class="mini num">{segs}</div>')
body4 = f"""<div class="mx">{''.join(cells)}</div>
<div style="margin-block-start:auto">{legend()}</div>
<div class="foot" style="margin-block-start:0"><p>Kā balsoja katrs deputāts:</p><span class="url">atmina.lv/likumprojekti/1521-lp14.html</span></div>"""
pages["4-visi"] = page(4, "Visi trīs balsojumi", "Frakciju balsis katrā solī. «—» — pie frakcijām nepiederošie", body4, css4)


def main():
    OUT_HTML.mkdir(parents=True, exist_ok=True)
    for slug, html in pages.items():
        h = OUT_HTML / f"{DAY}-zelta-vizas-{slug}.html"
        h.write_text(html, encoding="utf-8")
        png = OUT_PNG / f"{DAY}-zelta-vizas-{slug}.png"
        subprocess.run([sys.executable, str(ROOT / "scripts/render_shema.py"), str(h), str(png)], check=True)
        print(png)


if __name__ == "__main__":
    main()
