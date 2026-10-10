"""Tēmu meta-tagu invarianti bāzes veidnē (templates/base.html.j2).

Konteksts (2026-07-17): Brave iOS "Night Mode" (DarkReader-bāzēts) piespiedu
kārtā pārkrāsoja gaišo tēmu olīvbrūnā puskrāsojumā. Vietnei IR sava tumšā
tēma, tāpēc DarkReader-saimes rīkiem jāsaka "neaiztikt":

  1. ``<meta name="darkreader-lock">`` — dokumentētais DarkReader atslēgs
     (Brave iOS Night Mode lieto DarkReader; brave-browser#39786).
  2. ``meta[name=color-scheme]`` nedrīkst būt statisks "light" — tumšajā
     tēmā tas aicina auto-dark rīkus tumšot jau tumšu lapu. Tagam ir id,
     un abi tēmas skripti (agrīnais head + pārslēga sync) to atjauno.

Konteksts (2026-07-23, stingrā CSP): agrīnais inline FOUC-skripts + fontu
onload triks izcelti ārējā ``assets/theme-init.js`` (renderēšanu bloķējošs
head skripts, BEZ defer/async), lai ``script-src`` varētu atmest
'unsafe-inline'. Tests tagad sargā ārējā skripta atsauci galvenē + tā saturu.
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader


def _render_base() -> str:
    env = Environment(loader=FileSystemLoader("templates"), autoescape=True)
    env.globals["assets_version"] = "test"
    return env.get_template("base.html.j2").render()


def test_darkreader_lock_meta_present():
    html = _render_base()
    assert '<meta name="darkreader-lock">' in html


def test_color_scheme_meta_is_dynamic():
    html = _render_base()
    # id, lai skripti to var atjaunot pēc tēmas
    assert '<meta name="color-scheme" content="light" id="meta-color-scheme">' in html


def test_theme_init_script_is_blocking_and_before_style_css():
    """Ārējais theme-init.js ir renderēšanu bloķējošs (BEZ defer/async) un
    ielādēts PIRMS style.css, lai FOUC aizsargs paspēj pirms pirmās krāsošanas."""
    html = _render_base()
    head = html.split("</head>")[0]
    assert "assets/theme-init.js" in head
    ti = head.index("assets/theme-init.js")
    # skripta tags ap atsauci
    tag_start = head.rindex("<script", 0, ti)
    tag_end = head.index(">", ti)
    tag = head[tag_start:tag_end]
    assert "defer" not in tag, "theme-init.js jābūt bloķējošam (bez defer)"
    assert "async" not in tag, "theme-init.js jābūt bloķējošam (bez async)"
    # PIRMS style.css saites
    style_idx = head.index("assets/style.css")
    assert ti < style_idx, "theme-init.js jāielādē pirms style.css"


def test_theme_init_asset_content():
    """assets/theme-init.js satur FOUC aizsargu (atmina:theme, meta-color-scheme)
    un fontu media-swap loģiku (data-font-async)."""
    js = Path("assets/theme-init.js").read_text(encoding="utf-8")
    assert "atmina:theme" in js
    assert "meta-color-scheme" in js
    assert "data-font-async" in js
