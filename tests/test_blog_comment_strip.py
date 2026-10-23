"""Skeleta iekšējie komentāri nedrīkst nonākt publiskajā blog HTML.

BACKLOG 2026-08-04 kvalitātes pārbaude: `<!-- DIENAS STATS -->` no pārskata
skeleta nonāca dzīvajā lapā, jo markdown raw-HTML komentārus laiž cauri.
Fikss: `src/render/blog.py` strippo visus HTML komentārus pirms markdown
konversijas, PĒC WEEKLY_STATS marķiera aizstāšanas (tas pats ir komentārs).

Fixture ir piesiets rakstītājam: pirmais tests apliecina, ka pārbaudāmais
komentāra prefikss joprojām ir tieši tas, ko `src/briefs.py` emitē — lai
tests nevar zaļot uz izdomātas formas (CLAUDE.md: čekeru testi lasa to, ko
rakstītājs tiešām raksta).
"""

from pathlib import Path

from src.render.blog import _HTML_COMMENT_RE, _WEEKLY_STATS_RE

_REPO = Path(__file__).resolve().parent.parent

_WRITER_PREFIX = (
    "<!-- DIENAS STATS (iekšēja piezīme aģentam; nav renderēta publikai): "
)


def test_dienas_stats_comment_stripped_and_prefix_matches_writer():
    briefs_src = (_REPO / "src" / "briefs.py").read_text(encoding="utf-8")
    assert _WRITER_PREFIX in briefs_src, (
        "briefs.py vairs neemitē šo prefiksu — atjaunini testu kopā ar rakstītāju"
    )
    comment = _WRITER_PREFIX + "1217 dokumenti · 67 pozīcijas · 0 pretrunas -->"
    text = f"# Virsraksts\n\n{comment}\n\nPirmā rindkopa."
    out = _HTML_COMMENT_RE.sub("", text)
    assert "DIENAS STATS" not in out
    assert "Pirmā rindkopa." in out


def test_multiline_narrative_comment_stripped():
    text = (
        "Ievads.\n\n"
        "<!-- NARATĪVA MATERIĀLS (izmanto Galvenais paragrāfam):\n"
        "Spriedžu tēmas:\n  - Tēma (2 spriedzes)\n-->\n\n"
        "Nobeigums."
    )
    out = _HTML_COMMENT_RE.sub("", text)
    assert "NARATĪVA" not in out
    assert "Spriedžu" not in out
    assert "Ievads." in out and "Nobeigums." in out


def test_weekly_stats_cards_survive_because_sub_runs_first():
    marker = (
        "<!-- WEEKLY_STATS: positions=5 votes=2 contradictions=1 "
        "top_topic=Drošība top_party=JV -->"
    )
    content = f"## Nedēļa skaitļos\n\n{marker}\n\n<!-- DIENAS STATS iekšējs -->\n"
    content = _WEEKLY_STATS_RE.sub("KARTĪTES", content)
    content = _HTML_COMMENT_RE.sub("", content)
    assert "KARTĪTES" in content
    assert "DIENAS STATS" not in content


def test_render_loop_applies_strip_after_weekly_sub():
    """Secības sargs: strippam renderī jāstāv AIZ WEEKLY_STATS aizstāšanas,
    citādi nedēļas kartītes pazūd kopā ar iekšējiem komentāriem."""
    src = (_REPO / "src" / "render" / "blog.py").read_text(encoding="utf-8")
    sub_pos = src.index("_WEEKLY_STATS_RE.sub")
    strip_pos = src.index('_HTML_COMMENT_RE.sub("", content)')
    assert sub_pos < strip_pos
