"""Opt-in UI skaņu (cuelume) + chrome-sync invarianti.

Konteksts (2026-07-17): pievienojam navigācijas skaņu-slēdzi (default OFF).
Ieslēdzot, UI efekti (toggle uz tēmas pārslēga, success uz kopēšanas)
atskaņoti caur cuelume, ko lādē TIKAI ar lēno dynamic import, kad skaņa ir
ieslēgta.

Konteksts (2026-07-23, stingrā CSP): visa chrome-JS loģika izcelta ārējā
``assets/chrome-v1.js`` (ielādēts ar ``<script src=...chrome-v1.js defer>``),
lai ``script-src`` varētu atmest 'unsafe-inline'. Skaņu loģikas apgalvojumi
tagad attiecas uz šī faila saturu; bāzes veidnē paliek tikai vienīgā ārējā
skripta atsauce (chrome-sync kontrakts — sk. ``_orchestrator._CHROME_SPECS``).

Šie testi sargā:
  1. Skaņu poga IEKŠ ``<nav class="nav">``.
  2. Visa skaņu-JS loģika IEKŠ ``assets/chrome-v1.js``; cuelume URL atvasināts
     no ``document.currentScript`` (Jinja tur vairs nedzīvo).
  3. Kopēšanas handlers izsauc ``atmina:copied`` notikumu.
  4. Vendorētā bibliotēka klātesoša (verbatim).
  5. Bāzes veidnē tieši VIENS chrome ``<script`` tags starp </nav> un <main,
     ar ``src=`` un chrome-v1.js atsauci.
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader


def _render_base() -> str:
    env = Environment(loader=FileSystemLoader("templates"), autoescape=True)
    env.globals["assets_version"] = "test"
    return env.get_template("base.html.j2").render()


def _chrome_js() -> str:
    return Path("assets/chrome-v1.js").read_text(encoding="utf-8")


def test_nav_sound_button_inside_nav():
    html = _render_base()
    assert 'id="nav-sound"' in html
    assert 'role="switch"' in html
    # poga starp <nav class="nav"> un </nav>
    nav_open = html.index('<nav class="nav">')
    nav_close = html.index("</nav>", nav_open)
    nav_fragment = html[nav_open:nav_close]
    assert 'id="nav-sound"' in nav_fragment
    assert 'role="switch"' in nav_fragment
    assert 'aria-checked="false"' in nav_fragment


def test_sound_logic_in_chrome_asset():
    js = _chrome_js()
    assert "nav-sound" in js
    assert "atmina:sound" in js
    assert "cuelume" in js
    # cuelume URL atvasināts no paša skripta atrašanās vietas (currentScript),
    # nevis Jinja-injicēta specifikatora — ārējā failā Jinja nedzīvo.
    assert "document.currentScript" in js
    assert "new URL('cuelume/index.js'" in js
    # tabu pārslēgšana -> 'tick'; iekšējie satura linki -> 'page'
    # (ārējiem avotu linkiem un enkuriem skaņas NAV — delegācija tos izlaiž)
    assert "play('tick')" in js
    assert "play('page')" in js


def test_single_chrome_script():
    html = _render_base()
    nav_close = html.index("</nav>")
    main_start = html.index("<main", nav_close)
    segment = html[nav_close:main_start]
    assert segment.count("<script") == 1, (
        "exactly ONE <script tag allowed between </nav> and <main "
        "(chrome-sync fragment holds a single external script)"
    )
    assert "src=" in segment
    assert "chrome-v1.js" in segment


def test_copy_dispatches_event():
    js = _chrome_js()
    assert "atmina:copied" in js


def test_vendored_lib_present():
    idx = Path("assets/cuelume/index.js")
    assert idx.exists()
    idx_text = idx.read_text(encoding="utf-8")
    assert "play" in idx_text
    assert "setEnabled" in idx_text
    assert Path("assets/cuelume/LICENSE").exists()
