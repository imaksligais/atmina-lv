"""Konteksta kastē saraksts paliek saraksts, un tendences virsraksts kļūst par
kastes virsrakstu (2026-09-05).

Operatora ziņojums: dienas pārskatā «Konteksts» bloks lasās kā viens blīvs
teksta gabals, lai gan piezīme DB ir rakstīta ar ``- `` rindām. Cēlonis:
piezīmes ievada rinda («… Pozīcijas:») un pirmais saraksta punkts stāv blakus
bez tukšas rindas, un Python-Markdown tad saraksta rindas uzskata par
rindkopas turpinājumu. Tas pats otrā virzienā — noslēguma teikums uzreiz aiz
pēdējā punkta ielīp pēdējā ``<li>``.

``format_context_note()`` ir vienīgā vieta, kur skelets piezīmes tekstu
sagatavo Markdown-am: tukšas rindas ap sarakstu un ``Tendence (datums,
virsraksts):`` prefikss kā treknraksta virsraksts savā rindkopā.
"""

from src.briefs import format_context_note
from src.render.blog import _CONTEXT_BOX_OPEN_MD, _brief_markdown_to_html

_NOTE = (
    "Tendence (2026-09-04, jauns aizņēmums saņem sešas kritiskas reakcijas): "
    "21. augusta piezīme fiksēja kļūdu; 4. septembrī apspriež jaunu aizņēmumu. "
    "Pozīcijas:\n"
    "- Viktors Valainis (ZZS) — aizņēmums nav skatīts;\n"
    "- Jurģis Liepnieks — prasa skaidrojumu;\n"
    "- Guntars Vītols — neiebilst.\n"
    "Pirmoreiz šajā strīdā iebildumu ceļ koalīcijas ministrs."
)


def _box(content: str) -> str:
    return (
        f"{_CONTEXT_BOX_OPEN_MD}\n"
        '<div class="context-label">Konteksts</div>\n\n'
        f"{content}\n</div>\n"
    )


def test_list_renders_as_list_items_not_one_paragraph():
    html = _brief_markdown_to_html(_box(format_context_note(_NOTE)))
    assert html.count("<li>") == 3, html
    assert "<li>Viktors Valainis (ZZS) — aizņēmums nav skatīts;</li>" in html


def test_closing_sentence_is_its_own_paragraph_not_last_list_item():
    html = _brief_markdown_to_html(_box(format_context_note(_NOTE)))
    assert "<li>Guntars Vītols — neiebilst.</li>" in html
    assert "<p>Pirmoreiz šajā strīdā iebildumu ceļ koalīcijas ministrs.</p>" in html


def test_tendence_prefix_becomes_bold_heading_line():
    html = _brief_markdown_to_html(_box(format_context_note(_NOTE)))
    assert (
        "<p><strong>Jauns aizņēmums saņem sešas kritiskas reakcijas</strong>"
        " · 04.09.2026</p>"
    ) in html
    # Prefiksa vārds «Tendence» un iekavas nedrīkst palikt publiskajā tekstā.
    assert "Tendence (" not in html
    assert "<p>21. augusta piezīme fiksēja kļūdu" in html


def test_note_without_prefix_or_list_is_unchanged():
    plain = "Lapsa 12. augustā NBS vadību nosauca par gļēvu ([x.com](https://x.com/a))."
    assert format_context_note(plain) == plain


def test_unformatted_note_reproduces_the_defect():
    """Vārtiem jābūt redzētiem krītam: bez formatēšanas saraksts izplūst.

    Tieši Python-Markdown, apejot `_brief_markdown_to_html` (kas kopš
    2026-09-05 formatē pats) — tā ir forma, kādā kastīte publicējās līdz tam.
    """
    import markdown

    html = markdown.markdown(_box(_NOTE), extensions=["md_in_html"])
    assert "<li>" not in html


def test_paragraph_starting_with_date_ordinal_is_not_an_ordered_list():
    """«21. augusta …» rindkopas sākumā nedrīkst kļūt par <ol>."""
    html = _brief_markdown_to_html(_box(format_context_note(_NOTE)))
    assert "<ol>" not in html
    assert "<p>21. augusta piezīme fiksēja kļūdu" in html


def test_stored_brief_box_is_formatted_at_render_time():
    """Glabātie pārskati nes neformatētu kastes tekstu — renderis to sakārto."""
    html = _brief_markdown_to_html(_box(_NOTE).replace(' markdown="1"', ""))
    assert html.count("<li>") == 3, html
    assert "<ol>" not in html
    assert "Tendence (" not in html


def test_format_context_note_is_idempotent():
    once = format_context_note(_NOTE)
    assert format_context_note(once) == once
