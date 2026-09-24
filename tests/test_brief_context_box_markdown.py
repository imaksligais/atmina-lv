"""Konteksta kastē markdown saitēm jākļūst par klikšķināmām saitēm.

Operatora ziņojums 2026-08-15: dienas pārskata «Konteksts» blokos saites nebija
uzspiežamas — publiski redzams bija burtisks `([x.com](https://…))`. Cēlonis:
`src/render/blog.py` sauca Python-Markdown bez `md_in_html`, tāpēc viss
``<div class="context-box">`` bloks gāja cauri kā raw HTML — iekšpusē ne
rindkopas, ne saišu konversijas. Mērījums tajā dienā: 14 tādas saites 5
pārskatos no 136, kuros ir konteksta kastes.

Fikss prasa DIVAS lietas kopā (`_brief_markdown_to_html`): `md_in_html`
paplašinājumu UN `markdown="1"` atribūtu uz kastes div. Katra atsevišķi neko
nedod, tāpēc zemāk ir tests arī tam, ka viens pats paplašinājums NEPIETIEK —
citādi kāds vēlāk var atribūta injekciju noņemt kā lieku, un pakete paliks
zaļa, kamēr publiskā lapa saplīsīs.

Fixture ir piesiets rakstītājam: pirmais tests apliecina, ka `src/briefs.py`
joprojām emitē tieši to kastes formu, ko renderis gaida (CLAUDE.md: čekeru
testi lasa to, ko rakstītājs tiešām raksta).
"""

from pathlib import Path

import markdown

from src.render.blog import (
    _CONTEXT_BOX_OPEN,
    _CONTEXT_BOX_OPEN_MD,
    _brief_markdown_to_html,
)

_REPO = Path(__file__).resolve().parent.parent

# Tieši tāda kaste, kādu emitē skelets: atverošais div, etiķete, TUKŠA RINDA,
# saturs ar saiti, aizverošais div. Tukšā rinda ir būtiska — tieši tā liek
# Python-Markdown uzskatīt bloku par raw HTML, ja `md_in_html` nav ieslēgts.
_BOX = (
    '<div class="context-box">\n'
    '<div class="context-label">Konteksts</div>\n'
    "\n"
    "Lapsa 12. augustā NBS vadību nosauca par gļēvu "
    "([x.com](https://x.com/Lato_Lapsa/status/2087565200547336393)).\n"
    "</div>\n"
)


def test_briefs_writer_still_emits_expected_context_box():
    """Ja skelets maina kastes formu, šis tests krīt PIRMS publiskās lapas."""
    src = (_REPO / "src" / "briefs.py").read_text(encoding="utf-8")
    assert _CONTEXT_BOX_OPEN_MD in src, (
        "briefs.py vairs neemitē kasti ar markdown=\"1\" — atjaunini testu "
        "kopā ar rakstītāju"
    )
    assert 'class="context-label"' in src, (
        "briefs.py vairs neemitē context-label — kastes forma mainījusies"
    )


def test_context_box_markdown_link_becomes_anchor():
    html = _brief_markdown_to_html(_BOX)
    assert '<a href="https://x.com/Lato_Lapsa/status/2087565200547336393">' in html, (
        "saite konteksta kastē nav konvertēta — tā publicēsies kā burtisks teksts"
    )
    # Burtiskā markdown forma nedrīkst palikt redzama.
    assert "[x.com](" not in html
    # Un pati kaste joprojām ir kaste (CSS klase nav pazudusi).
    assert 'class="context-box"' in html
    # `md_in_html` atribūtu apēd — tas nedrīkst nonākt publiskajā HTML.
    assert 'markdown="1"' not in html


def test_already_annotated_box_is_not_double_annotated():
    """Skelets jau emitē atribūtu; render-laika injekcija to nedrīkst dublēt."""
    html = _brief_markdown_to_html(_BOX.replace(_CONTEXT_BOX_OPEN, _CONTEXT_BOX_OPEN_MD))
    assert '<a href="https://x.com/Lato_Lapsa/status/2087565200547336393">' in html
    assert 'markdown="1"' not in html


def test_extension_alone_is_not_enough():
    """Vārti pret regresiju: bez atribūta saite paliek burtisks teksts.

    Šis tests eksistē, lai `markdown="1"` injekciju nevar noņemt kā «lieku» —
    ja kāds to izdara, `test_context_box_markdown_link_becomes_anchor` krīt, un
    šis paskaidro, kāpēc.
    """
    raw = markdown.Markdown(
        extensions=["tables", "fenced_code", "md_in_html"]
    ).convert(_BOX)
    assert "[x.com](" in raw, (
        "Python-Markdown uzvedība mainījusies — ja md_in_html tagad strādā bez "
        "atribūta, injekciju drīkst vienkāršot, bet tikai ar šo pierādījumu"
    )


def test_paragraph_outside_box_still_renders():
    """Kastes labojums nedrīkst salauzt parasto pārskata tekstu."""
    html = _brief_markdown_to_html(_BOX + "\nParasta rindkopa ar [saiti](https://a.lv).\n")
    assert "<p>Parasta rindkopa ar <a href=\"https://a.lv\">saiti</a>.</p>" in html
