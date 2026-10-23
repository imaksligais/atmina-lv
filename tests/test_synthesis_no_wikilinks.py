"""Obsidian wikilinks must never reach a published synthesis page.

`wiki/synthesis/*.md` is the one hand-authored surface that renders straight
onto atmina.lv (CLAUDE.md standing decision: "Syntheses are hand-written").
Every other wiki page is either generated or stays inside the vault, so
Obsidian's `[[slug|Display]]` syntax is legitimate there — but the synthesis
renderer runs the file through python-markdown, which has no notion of a
wikilink and passes it through as literal text.

2026-08-01 audit: `kafijas-jura-kartelis-staki-2026-05.html` had been serving
six raw `[[martins-stakis|Staķis]]` strings to readers on the live site,
confirmed by HTTP fetch. Nothing caught it because the vault renders wikilinks
correctly in Obsidian — the defect is only visible in the published HTML.

The fix is to use ordinary markdown links to real site URLs; this test keeps
the next hand-authored synthesis from reintroducing the class. Note that one
target (`didzis-klucins`) had no page at all: he is
`relationship_type='inactive'`, so `wiki_sync` never generates a person page
and the renderer never emits a profile. Inactive politicians get plain text,
not a link.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

_SYNTHESIS_DIR = Path(__file__).resolve().parents[1] / "wiki" / "synthesis"

# `[[target]]` or `[[target|Display]]`. Deliberately not anchored: a wikilink
# anywhere in the body ships to the reader as literal text.
_WIKILINK = re.compile(r"\[\[[^\]\n]+\]\]")


def _synthesis_pages() -> list[Path]:
    if not _SYNTHESIS_DIR.exists():
        return []
    return sorted(p for p in _SYNTHESIS_DIR.glob("*.md"))


@pytest.mark.parametrize(
    "page", _synthesis_pages(), ids=lambda p: p.name
)
def test_synthesis_page_has_no_obsidian_wikilinks(page: Path) -> None:
    text = page.read_text(encoding="utf-8")
    hits = _WIKILINK.findall(text)
    assert not hits, (
        f"{page.relative_to(_SYNTHESIS_DIR.parents[1])} contains Obsidian "
        f"wikilinks that would render as literal text on the public site: "
        f"{hits}. Use a markdown link to the real URL instead, e.g. "
        f"[Vārds Uzvārds](/politiki/vards-uzvards.html), or plain text when "
        f"the politician is inactive and has no published page."
    )


def test_synthesis_dir_is_actually_being_checked() -> None:
    """Guard the guard: an empty glob would make the parametrized test vacuous."""
    assert _synthesis_pages(), (
        f"no synthesis pages found under {_SYNTHESIS_DIR} — the wikilink "
        f"check above would silently pass on nothing"
    )
