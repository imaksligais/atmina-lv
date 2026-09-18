"""Partiju tests — v0 statiskā matricas lapa (tikai LASA DB).

Ieeja: `content/partiju-tests/jautajumi.yaml` + `kodejums.json` (validatoram
jābūt zaļam — šis skripts to izsauc pats un apstājas, ja nav) + `parties`
(pilnie nosaukumi). Izeja: `curated/atmina/analizes/partiju-tests.html`
(standalone paterns, ui-conventions §24; chrome sinhronizē `_copy_curated`) —
BET tikai ar `--publish`; noklusējums ir melnraksts `content/partiju-tests/
partiju-tests.draft.html`, kas deploy kokā nenonāk (T15).

Bez JS: katra partijas šūna ir `<details>` ar citātu, CVK saiti un saiti uz
partijas lapas sadaļu "Programma". Lapas dizains tur tos pašus tokenus, ko
pārējās kurētās analīzes (dark noklusējums, @media light, [data-theme]).

Lietošana:
    .venv/Scripts/python.exe scripts/render_partiju_tests.py            # melnraksts
    .venv/Scripts/python.exe scripts/render_partiju_tests.py --publish  # uz curated/
"""

from __future__ import annotations

import html
import json
import re
import sqlite3
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from scripts.partiju_tests_validate import (STARTING, load_saraksti, question_gate,  # noqa: E402
                                            validate, QUIZ_MIN_QUESTIONS,
                                            QUIZ_MIN_READABLE, QUIZ_MIN_MINORITY)
from src.render._common.slugs import _party_page_slug  # noqa: E402

OUT_PUBLISH = REPO / "curated" / "atmina" / "analizes" / "partiju-tests.html"
# Melnraksts dzīvo ĀRPUS curated/, jo _copy_curated pārnes visu curated/atmina/
# uz output/ un deploy.sh — visu output/ (T15). Uz curated tikai ar --publish.
OUT_DRAFT = REPO / "content" / "partiju-tests" / "partiju-tests.draft.html"
Q_PATH = REPO / "content" / "partiju-tests" / "jautajumi.yaml"
K_PATH = REPO / "content" / "partiju-tests" / "kodejums.json"
DB = REPO / "data" / "atmina.db"
OG_IMAGE = REPO / "output" / "images" / "analizes" / "partiju-tests-og.jpg"

LABEL = {"par": "Piekrīt", "pret": "Iebilst", "klusē": "Neizsakās"}
MIN_M = 4  # zem tā partija iet atsevišķā sarakstā, ne rindā

AVOTS_LABEL = {"cvk": "CVK programma", "pilna_programma": "pilnā programma",
               "izteikums": "izteikums"}

E = html.escape


def load_parties() -> dict[str, dict]:
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    rows = c.execute("SELECT short_name, name FROM parties").fetchall()
    c.close()
    return {sn: {"name": name, "slug": _party_page_slug(sn)} for sn, name in rows}


def party_summary(questions, coding):
    out = {}
    for p in STARTING:
        cnt = {"par": 0, "pret": 0, "klusē": 0}
        for q in questions:
            cnt[coding[q["id"]][p]["nostaja"]] += 1
        out[p] = cnt
    return out


def render_cell(p: str, cell: dict, parties: dict) -> str:
    st = cell["nostaja"]
    name = parties[p]["name"]
    slug = parties[p]["slug"]
    if st == "klusē":
        body = (f'<p class="pt-note">{E(cell["piezime"])}</p>'
                f'<p class="pt-links"><a href="../partijas/{slug}.html#programma">Programma partijas lapā</a></p>')
    else:
        src = AVOTS_LABEL.get(cell.get("avots"), "CVK programma")
        body = (f'<blockquote class="pt-quote">„{E(cell["citats"])}”</blockquote>'
                f'<p class="pt-links"><a href="{E(cell["url"])}" rel="noopener">{src}</a> · '
                f'<a href="../partijas/{slug}.html#programma">Programma partijas lapā</a></p>')
    return (f'<details class="pt-cell pt-{st}"><summary title="{E(name)}">'
            f'<span class="pt-abbr">{E(p)}</span><span class="pt-st">{LABEL[st]}</span></summary>'
            f'<div class="pt-body"><div class="pt-name">{E(name)}</div>{body}</div></details>')


def render_question(i: int, q: dict, cells: dict, parties: dict, n_lists: int) -> str:
    groups = {"par": [], "pret": [], "klusē": []}
    for p in STARTING:
        groups[cells[p]["nostaja"]].append(p)
    n_par, n_pret = len(groups["par"]), len(groups["pret"])
    parts = [f'<section class="pt-q" id="{q["id"]}">',
             f'<h2><span class="pt-num">{i}</span> {E(q["apgalvojums"])}</h2>',
             f'<p class="pt-meta">Tēma: {E(q["tema"])} · piekrīt {n_par} · iebilst {n_pret} · neizsakās {n_lists - n_par - n_pret}</p>']
    for st in ("par", "pret", "klusē"):
        if not groups[st]:
            continue
        parts.append(f'<div class="pt-group"><div class="pt-group-l">{LABEL[st]}</div><div class="pt-cells">')
        parts.extend(render_cell(p, cells[p], parties) for p in groups[st])
        parts.append("</div></div>")
    parts.append("</section>")
    return "\n".join(parts)


def render_summary(summary: dict, parties: dict, n_questions: int,
                   pp_url: dict[str, str | None] | None = None) -> str:
    rows = sorted(STARTING, key=lambda p: (-(summary[p]["par"] + summary[p]["pret"]), p))
    out = ['<table class="pt-sum"><thead><tr><th>Saraksts</th><th>Izsakās</th><th>Piekrīt</th><th>Iebilst</th><th>Neizsakās</th></tr></thead><tbody>']
    for p in rows:
        s = summary[p]
        m = s["par"] + s["pret"]
        cls = ' class="pt-thin"' if m < MIN_M else ""
        pp = f' · <a class="pt-pp" href="{E(pp_url[p])}" rel="noopener">pilnā programma</a>' if pp_url and pp_url.get(p) else ""
        out.append(f'<tr{cls}><td><a href="../partijas/{parties[p]["slug"]}.html#programma">{E(p)}</a>{pp} '
                   f'<span class="pt-full">{E(parties[p]["name"])}</span></td>'
                   f'<td><strong>{m}</strong> no {n_questions}</td><td>{s["par"]}</td><td>{s["pret"]}</td><td>{s["klusē"]}</td></tr>')
    out.append("</tbody></table>")
    return "\n".join(out)


def _u3_note(n_lists: int) -> str:
    """Aklās pārkodēšanas (U3) skaitļi no kodejums_draft.md komentāra; ja nav — izlaiž."""
    md = K_PATH.with_name("kodejums_draft.md")
    m = (re.search(r"<!--\s*u3:\s*(\{.*?\})\s*-->", md.read_text(encoding="utf-8"))
         if md.exists() else None)
    if not m:
        return ""
    try:
        u3 = json.loads(m.group(1))
    except json.JSONDecodeError:
        return ""
    n_q = u3["sunas"] // n_lists
    return (f'Kvalitātes pārbaudei {u3["sunas"]} šūnas ({n_q} apgalvojumi × {n_lists} saraksti) '
            f'{u3["datums"]} kodētas otrreiz, neredzot pirmo kodējumu: sakrita {u3["sakrit"]}, '
            f'{u3["nostajas_mainitas"]} nostājas pēc pārskata mainītas.')


def build(questions: list | None = None, coding: dict | None = None,
          parties: dict | None = None, saraksti: list | None = None,
          og_image_exists: bool | None = None) -> str:
    if questions is None:
        questions = yaml.safe_load(Q_PATH.read_text(encoding="utf-8"))
    if coding is None:
        coding = json.loads(K_PATH.read_text(encoding="utf-8"))
    if saraksti is None:
        saraksti = load_saraksti()
    if parties is None:
        rep = validate(questions, coding, str(DB), saraksti=saraksti)
        if rep.errors or rep.cells == 0:
            raise SystemExit(f"kodējums nav zaļš ({len(rep.errors)} kļūdas, {rep.cells} šūnas) — lapu neģenerēju")
        parties = load_parties()
    if og_image_exists is None:
        og_image_exists = OG_IMAGE.exists()
    n_q = len(questions)
    n_s = len(saraksti)
    summary = party_summary(questions, coding)
    total_stated = sum(s["par"] + s["pret"] for s in summary.values())
    thin = [p for p in STARTING if summary[p]["par"] + summary[p]["pret"] < MIN_M]
    n_pp = sum(1 for s in saraksti if s.get("pilna_programma_url"))
    exc = [f'{s["short_name"]} — {s["pilna_programma_piezime"]}'
           for s in saraksti if s.get("pilna_programma_piezime")]
    exc_str = f"; izņēmumi: {'; '.join(exc)}" if exc else ""
    lvl: dict[str, int] = {}
    for q in questions:
        for s in saraksti:
            a = coding[q["id"]][s["short_name"]].get("avots", "klusē")
            lvl[a] = lvl.get(a, 0) + 1
    src_txt = f'„CVK programma” {lvl.get("cvk", 0)} šūnās'
    for k in ("pilna_programma", "izteikums"):
        if lvl.get(k):
            src_txt += f', „{AVOTS_LABEL[k]}” {lvl[k]}'
    n_pass = sum(r["ok"] for r in question_gate(questions, coding, saraksti))
    u3_note = _u3_note(n_s)
    u3_html = f" {E(u3_note)}" if u3_note else ""

    q_html = "\n".join(render_question(i, q, coding[q["id"]], parties, n_s) for i, q in enumerate(questions, 1))
    toc = "\n".join(f'<li><a href="#{q["id"]}">{E(q["apgalvojums"])}</a></li>' for q in questions)
    og_meta = ('  <meta property="og:image" content="https://atmina.lv/images/analizes/partiju-tests-og.jpg">\n'
               if og_image_exists else "")
    tw_meta = ('  <meta name="twitter:image" content="https://atmina.lv/images/analizes/partiju-tests-og.jpg">\n'
               if og_image_exists else "")

    return f"""<!DOCTYPE html>
<html lang="lv">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="color-scheme" content="light" id="meta-color-scheme"><meta name="darkreader-lock">
  <meta name="theme-color" content="#f7f3e8" id="meta-theme-color">
  <title>Partiju tests — Politiskā atmiņa</title>
  <meta name="description" content="{n_q} apgalvojumi, {n_s} saraksti: ko katra partija savā oficiālajā CVK programmā sola, kam iebilst un par ko klusē. Katra atbilde ar citātu un saiti uz avotu.">
  <link rel="canonical" href="https://atmina.lv/analizes/partiju-tests.html">
  <meta property="og:title" content="Partiju tests — {n_q} apgalvojumi, {n_s} programmas, katra atbilde ar citātu">
  <meta property="og:description" content="Ko partijas savās 2026. gada vēlēšanu programmās sola, kam iebilst un par ko klusē. Nevis partiju pašnovērtējums, bet programmu teksts ar avotiem.">
  <meta property="og:type" content="website">
  <meta property="og:locale" content="lv_LV">
  <meta property="og:site_name" content="atmina.lv">
{og_meta}  <meta property="og:url" content="https://atmina.lv/analizes/partiju-tests.html">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:site" content="@atminaLV">
{tw_meta}  <link rel="icon" type="image/svg+xml" href="../assets/favicon.svg"><link rel="icon" type="image/png" sizes="96x96" href="../assets/favicon-96.png">
  <link rel="icon" type="image/png" sizes="192x192" href="../assets/favicon-192.png">
  <link rel="apple-touch-icon" href="../assets/apple-touch-icon.png">
  <script src="../assets/theme-init.js?v=1"></script>
  <link rel="stylesheet" href="../assets/style.css?v=1">
<style>
:root {{
  color-scheme: dark;
  --bg: #0d1014; --surface: #161a22; --surface2: #242838;
  --text: #e2e4e9; --text-soft: #c8ccd8; --text-muted: #8b8fa3; --text-dim: #5e6478;
  --accent: #90A4AE; --accent-highlight: #B71C1C; --hl: #ef5350;
  --logo-ring: #90A4AE; --logo-dot: #EF5350;
  --green: #22c55e; --orange: #f97316; --blue: #3b82f6; --purple: #a855f7;
  --border: #2d3148; --border-soft: #1f2432;
  --par-bg: rgba(34,197,94,.14); --par-fg: #4ade80;
  --pret-bg: rgba(239,83,80,.14); --pret-fg: #f87171;
  --kluse-bg: rgba(255,255,255,.04); --kluse-fg: #8b8fa3;
  --radius: 8px;
}}
@media (prefers-color-scheme: light) {{
  :root {{
    color-scheme: light;
    --bg: #f7f3e8; --surface: #f4efe4; --surface2: #e9e1cc;
    --text: #1f1b14; --text-soft: #3b3526; --text-muted: #5d5747; --text-dim: #6e654f;
    --accent: #2c4270; --accent-highlight: #B71C1C; --hl: #b42318;
    --logo-ring: #1f2d4d; --logo-dot: #B71C1C;
    --green: #1a7a3a; --orange: #b8400c; --blue: #1d4ed8; --purple: #7e22ce;
    --border: #d3c9af; --border-soft: #e5dccb;
    --par-bg: rgba(26,122,58,.12); --par-fg: #166534;
    --pret-bg: rgba(180,35,24,.12); --pret-fg: #991b1b;
    --kluse-bg: rgba(31,27,20,.05); --kluse-fg: #5d5747;
  }}
}}
:root[data-theme="light"] {{
  color-scheme: light;
  --bg: #f7f3e8; --surface: #f4efe4; --surface2: #e9e1cc;
  --text: #1f1b14; --text-soft: #3b3526; --text-muted: #5d5747; --text-dim: #6e654f;
  --accent: #2c4270; --accent-highlight: #B71C1C; --hl: #b42318;
  --logo-ring: #1f2d4d; --logo-dot: #B71C1C;
  --green: #1a7a3a; --orange: #b8400c; --blue: #1d4ed8; --purple: #7e22ce;
  --border: #d3c9af; --border-soft: #e5dccb;
  --par-bg: rgba(26,122,58,.12); --par-fg: #166534;
  --pret-bg: rgba(180,35,24,.12); --pret-fg: #991b1b;
  --kluse-bg: rgba(31,27,20,.05); --kluse-fg: #5d5747;
}}
:root[data-theme="dark"] {{
  color-scheme: dark;
  --bg: #0d1014; --surface: #161a22; --surface2: #242838;
  --text: #e2e4e9; --text-soft: #c8ccd8; --text-muted: #8b8fa3; --text-dim: #5e6478;
  --accent: #90A4AE; --accent-highlight: #B71C1C; --hl: #ef5350;
  --logo-ring: #90A4AE; --logo-dot: #EF5350;
  --green: #22c55e; --orange: #f97316; --blue: #3b82f6; --purple: #a855f7;
  --border: #2d3148; --border-soft: #1f2432;
  --par-bg: rgba(34,197,94,.14); --par-fg: #4ade80;
  --pret-bg: rgba(239,83,80,.14); --pret-fg: #f87171;
  --kluse-bg: rgba(255,255,255,.04); --kluse-fg: #8b8fa3;
}}
body {{ background: var(--bg); color: var(--text); }}
.wrap {{ max-width: 880px; margin: 0 auto; padding: 2rem 1.25rem 4rem; }}
.wrap h1, .wrap h2 {{ font-family: Georgia, 'Times New Roman', serif; font-weight: 600; text-wrap: balance; }}
.wrap h1 {{ font-size: clamp(1.7rem, 4.5vw, 2.35rem); line-height: 1.15; margin: .5rem 0 1rem; letter-spacing: -.01em; }}
.wrap h2 {{ font-size: 1.25rem; line-height: 1.3; margin: 0 0 .3rem; }}
.kicker {{ font-size: .75rem; letter-spacing: .12em; text-transform: uppercase; color: var(--accent); }}
.lede {{ color: var(--text-muted); font-size: 1rem; max-width: 64ch; margin: 0 0 1rem; }}
.lede strong {{ color: var(--text-soft); }}
.pt-explain {{ background: var(--surface); border: 1px solid var(--border-soft); border-radius: var(--radius); padding: 1rem 1.1rem; margin: 1.25rem 0; }}
.pt-explain p {{ margin: .35rem 0; font-size: .92rem; line-height: 1.5; }}
.pt-toc {{ margin: 1rem 0 2rem; padding-left: 1.2rem; font-size: .9rem; line-height: 1.6; }}
.pt-toc a {{ color: var(--text-soft); text-decoration: none; border-bottom: 1px solid var(--border); }}
.pt-sum {{ width: 100%; border-collapse: collapse; font-size: .9rem; margin: .5rem 0 2rem; }}
.pt-sum th, .pt-sum td {{ padding: .4rem .5rem; text-align: left; border-bottom: 1px solid var(--border-soft); }}
.pt-sum th {{ font-size: .72rem; letter-spacing: .06em; text-transform: uppercase; color: var(--text-dim); font-weight: 600; }}
.pt-sum td:nth-child(n+2) {{ text-align: right; font-variant-numeric: tabular-nums; }}
.pt-sum th:nth-child(n+2) {{ text-align: right; }}
.pt-sum a {{ color: var(--text); font-weight: 600; text-decoration: none; }}
.pt-pp {{ font-weight: 400 !important; font-size: .78rem; color: var(--accent) !important; border-bottom: 1px solid var(--border); }}
.pt-full {{ color: var(--text-dim); font-size: .8rem; }}
.pt-thin td {{ color: var(--text-dim); }}
.pt-q {{ margin: 0 0 2rem; padding-top: 1.25rem; border-top: 1px solid var(--border-soft); }}
.pt-num {{ display: inline-block; min-width: 1.6em; color: var(--accent); font-family: inherit; }}
.pt-meta {{ font-size: .78rem; color: var(--text-dim); margin: 0 0 .75rem; }}
.pt-group {{ display: grid; grid-template-columns: 6.5rem 1fr; gap: .5rem; align-items: start; margin: .4rem 0; }}
.pt-group-l {{ font-size: .72rem; letter-spacing: .08em; text-transform: uppercase; color: var(--text-dim); padding-top: .45rem; }}
.pt-cells {{ display: flex; flex-wrap: wrap; gap: .4rem; }}
.pt-cell {{ border-radius: 999px; border: 1px solid transparent; }}
.pt-cell summary {{ list-style: none; cursor: pointer; display: inline-flex; align-items: baseline; gap: .4rem; padding: .3rem .7rem; border-radius: 999px; font-size: .85rem; user-select: none; }}
.pt-cell summary::-webkit-details-marker {{ display: none; }}
.pt-abbr {{ font-weight: 700; }}
.pt-st {{ font-size: .72rem; opacity: .8; display: none; }}
.pt-cell[open] .pt-st {{ display: inline; }}
.pt-par summary {{ background: var(--par-bg); color: var(--par-fg); }}
.pt-pret summary {{ background: var(--pret-bg); color: var(--pret-fg); }}
.pt-klusē summary {{ background: var(--kluse-bg); color: var(--kluse-fg); }}
.pt-cell[open] {{ flex-basis: 100%; }}
.pt-cell[open] summary {{ border-bottom-left-radius: 0; border-bottom-right-radius: 0; }}
.pt-body {{ background: var(--surface); border: 1px solid var(--border-soft); border-radius: 0 var(--radius) var(--radius) var(--radius); padding: .75rem .9rem; margin-top: -1px; font-size: .9rem; }}
.pt-name {{ font-weight: 600; margin-bottom: .35rem; }}
.pt-quote {{ margin: .25rem 0 .5rem; padding-left: .75rem; border-left: 3px solid var(--accent); color: var(--text-soft); font-style: italic; line-height: 1.5; }}
.pt-note {{ margin: .25rem 0 .5rem; color: var(--text-muted); line-height: 1.5; }}
.pt-links {{ margin: 0; font-size: .82rem; }}
.pt-links a {{ color: var(--accent); }}
.pt-method {{ margin-top: 2.5rem; padding-top: 1.25rem; border-top: 1px solid var(--border); font-size: .9rem; line-height: 1.55; color: var(--text-soft); }}
.pt-method h2 {{ font-size: 1.15rem; }}
footer {{ margin-top: 2rem; font-size: .78rem; color: var(--text-dim); line-height: 1.5; }}
@media (max-width: 600px) {{
  .pt-group {{ grid-template-columns: 1fr; gap: .2rem; }}
  .pt-group-l {{ padding-top: .2rem; }}
  .pt-full {{ display: none; }}
}}
</style>
  <script defer src="https://cloud.umami.is/script.js" data-website-id="ed2729be-82e1-48d9-a164-645a8f389d35"></script>
</head>
<body>
  <nav class="nav">
    <div class="container"><a href="../index.html" class="nav-logo"><span class="nav-logo-text">atmina.lv</span></a></div>
  </nav>
  <main>
    <div class="wrap">
  <header>
    <div class="kicker">Partiju tests · 15. Saeimas vēlēšanas 2026</div>
    <h1>Ko partijas sola, kam iebilst un par ko klusē</h1>
    <p class="lede">{n_q} apgalvojumi un visu {n_s} sarakstu oficiālās programmas. Katra atbilde ir <strong>citāts no programmas teksta</strong>, nevis partijas pašnovērtējums. Ja programma par jautājumu neizsakās, tā arī rakstām — klusēšana ir informācija.</p>
  </header>

  <div class="pt-explain">
    <p><strong>Kā lasīt.</strong> Pie katra apgalvojuma partijas ir trīs grupās: piekrīt, iebilst, neizsakās. Klikšķis uz saraksta atver citātu un saiti uz avotu.</p>
    <p><strong>Programma nav rīcība.</strong> Šeit ir tikai tas, kas rakstīts programmās. Parlamenta partiju balsojumus skaties to lapās sadaļā „Balsojumi”.</p>
    <p><strong>Tas nav balsošanas ieteikums.</strong> Apgalvojumi izvēlēti tā, lai programmas tajos atšķirtos; tie neaptver visu, kas vēlētājam var būt svarīgs.</p>
  </div>

  <h2>Cik jautājumos katra programma vispār izsakās</h2>
  <p class="pt-meta">Kopā {total_stated} nolasāmas atbildes no {n_q * n_s} iespējamām. Saraksti ar mazāk nekā {MIN_M} atbildēm ({", ".join(thin)}) rakstīti blāvāk — to programmas ir rakstītas vispārīgi, un pēc šī testa tās salīdzināt nevar. „Neizsakās” nozīmē „neviens no abiem pārbaudītajiem dokumentiem neizsakās” (sk. metodoloģiju).</p>
  {render_summary(summary, parties, n_q, {s["short_name"]: s.get("pilna_programma_url") for s in saraksti})}

  <h2>Apgalvojumi</h2>
  <ol class="pt-toc">
  {toc}
  </ol>

  {q_html}

  <section class="pt-method">
    <h2>Metodoloģija</h2>
    <p>Avoti ir divi dokumenti katram sarakstam, lasīti šādā secībā: vispirms CVK iesniegtā priekšvēlēšanu programma (dati.cvk.lv — likums to ierobežo līdz 4000 rakstzīmēm, aptuveni vienai lappusei), pēc tam pilnā programma saraksta mājaslapā. Pilnu programmu atradām {n_pp} no {n_s} sarakstiem{exc_str}. CVK programmas ir apkopotas 276 pozīcijās 31 tēmā (sk. <a href="../sintezes/partiju-programmas-2026-solijumu-karte.html">solījumu karti</a>); šis tests iet soli tālāk un pie {n_q} konkrētiem apgalvojumiem nolasa, ko katra programma saka.</p>
    <p><strong>„Neizsakās” nozīmē „neviens no abiem dokumentiem apgalvojumu neadresē”, nevis „partijai nav viedokļa”.</strong> Piezīme pie katras šādas šūnas saka, ko katrs dokuments raksta tā vietā. Programmas ir īsas un saraksti izvēlas dažādi: vieni raksta konkrētu solījumu sarakstu, citi — vispārīgus principus. Tāpēc atbilžu skaits starp partijām tik ļoti atšķiras, un tas pats par sevi ir informācija par programmu, ne par partiju. Plašākas nostājas no mediju un sociālo tīklu plūsmas skatāmas katras partijas lapā pie pozīcijām; testā tās nelietojam, jo tām nav vienota avota visiem {n_s} sarakstiem.</p>
    <p>Kodējums ir trīs vērtībās: <em>piekrīt</em>, <em>iebilst</em>, <em>neizsakās</em>. „Piekrīt” vai „iebilst” rakstām tikai tad, ja programmas teikums attiecas uz apgalvojumu bez interpretācijas, un katrai šādai šūnai pievienots citāts vārds vārdā ar norādi, no kura dokumenta tas nāk ({src_txt}). Vispārīgi formulējumi („gudra politika”, „taisnīga sadale”) tiek kodēti kā „neizsakās”. Piecu ballu skalu neizmantojam apzināti: no programmas prozas var nolasīt virzienu, ne pakāpi.</p>
    <p>Apgalvojumi atlasīti pēc datiem: kandidāts ieiet kopā, ja vismaz piecām programmām nostāja ir nolasāma. Tāpēc kopa ir {n_q}, ne vairāk — daudzās tēmās programmas vienkārši nesaka neko konkrētu. Apgalvojumu formulējumi ir atmina.lv, tie nav pārņemti no citiem vēlētāju testiem; LSM un Providus „Partiju šķirotava” ir cita pieeja, kur atbildes sniedz pašas partijas.</p>
    <p>Katru šūnu kodēja un pārbaudīja atsevišķi, un automātisks pārbaudītājs apstiprina, ka katrs citāts atrodams programmas tekstā un katra saite ved uz attiecīgo dokumentu.{u3_html} Ja pamanāt kļūdu, rakstiet — labojumi tiek publicēti ar norādi.</p>
    <p>Interaktīvs tests — savu atbilžu salīdzinājums ar programmām — tiks pievienots tikai tad, ja vismaz {QUIZ_MIN_QUESTIONS} apgalvojumi izturēs godīguma pārbaudi: vismaz {QUIZ_MIN_READABLE} no {n_s} sarakstiem izsakās un mazākumā ir vismaz {QUIZ_MIN_MINORITY}. Šodien to iztur {n_pass} no {n_q}.</p>
  </section>

  <footer>
    Avoti: Centrālās vēlēšanu komisijas publicētās 15. Saeimas vēlēšanu programmas (dati.cvk.lv) un sarakstu pilnās programmas to mājaslapās. Kodējums: atmina.lv, 2026. gada septembris.
  </footer>
    </div>
  </main>
</body>
</html>
"""


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", action="store_true",
                    help="rakstīt uz curated/ (deployojams) — tikai pēc operatora atļaujas")
    a = ap.parse_args(argv)
    out = OUT_PUBLISH if a.publish else OUT_DRAFT
    out.write_text(build(), encoding="utf-8")
    print(f"rakstīts {out.relative_to(REPO)} ({out.stat().st_size:,} B)"
          + ("" if a.publish else "  [melnraksts — nav deploy kokā]"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
