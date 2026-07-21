"""CSP invariants: nekāda inline JavaScript nevienā vietnes virsmā.

Konteksts (2026-07-23): Content-Security-Policy `script-src` vairs nesatur
'unsafe-inline' — pārlūks bloķē (a) katru `<script>` bloku bez `src=` (izņemot
ne-izpildāmos datu tipus application/json un application/ld+json) un (b) katru
inline notikumu atribūtu (onclick=, oninput=, …), ieskaitot ar innerHTML
iesprausto. Viss izpildāmais JS dzīvo assets/*.js failos.

Šie testi tur invariantu uz VISIEM avotiem, no kuriem rodas lapas HTML:
  1. templates/*.j2 — visu ģenerēto lapu avots;
  2. curated/atmina/**/*.html — iesaldētās (frozen) lapas, ko deploy'o kā-ir.

Ja tests krīt: pārcel skriptu uz assets/*.js (datus — uz
`<script type="application/json">` bloku vai data-* atribūtu) un pieslēdz ar
`<script src=…?v={{ assets_version }}>`. NEDRĪKST atgriezt 'unsafe-inline'
CSP galvenē (assets/htaccess.template) — tas ir apzināts drošības lēmums.
"""

import re
from pathlib import Path

# Izpildāms <script> = bez src un bez ne-izpildāma type (application/json,
# application/ld+json). type="text/javascript" u.c. izpildāmie tipi krīt.
_SCRIPT_RE = re.compile(r"<script(?![^>]*\bsrc=)([^>]*)>", re.IGNORECASE)
_NONEXEC_TYPES = ("application/json", "application/ld+json")

# Inline notikumu atribūts: atstarpe + on[a-z]+= ar pēdiņu — šaurs paterns,
# lai neķertu content="..." u.tml. metadatus.
_HANDLER_RE = re.compile(r"""\son[a-z]+\s*=\s*["']""", re.IGNORECASE)


def _executable_inline_scripts(text: str) -> list[str]:
    hits = []
    for m in _SCRIPT_RE.finditer(text):
        attrs = m.group(1)
        if any(t in attrs for t in _NONEXEC_TYPES):
            continue
        hits.append(m.group(0))
    return hits


def _files():
    root = Path(__file__).resolve().parents[1]
    yield from sorted((root / "templates").glob("*.j2"))
    yield from sorted((root / "curated" / "atmina").rglob("*.html"))


def test_no_srcless_executable_scripts():
    bad = {}
    for f in _files():
        hits = _executable_inline_scripts(f.read_text(encoding="utf-8"))
        if hits:
            bad[str(f)] = hits
    assert not bad, f"Inline izpildāmi <script> bloki (CSP tos bloķēs): {bad}"


def test_no_inline_event_handler_attributes():
    bad = {}
    for f in _files():
        hits = _HANDLER_RE.findall(f.read_text(encoding="utf-8"))
        if hits:
            bad[str(f)] = hits
    assert not bad, f"Inline on*= notikumu atribūti (CSP tos bloķēs): {bad}"


def test_no_handlers_injected_via_js_strings():
    """innerHTML ar on*= atribūtu klusi mirst zem stingrās CSP (risk 4)."""
    root = Path(__file__).resolve().parents[1]
    bad = {}
    for f in sorted((root / "assets").glob("*.js")):
        text = f.read_text(encoding="utf-8")
        hits = [
            ln.strip()
            for ln in text.splitlines()
            if _HANDLER_RE.search(ln) and not ln.lstrip().startswith("//")
        ]
        if hits:
            bad[f.name] = hits
    assert not bad, f"on*= atribūti JS virknēs (innerHTML → klusi mirst): {bad}"
