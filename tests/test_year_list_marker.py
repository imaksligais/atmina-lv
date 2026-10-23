"""Rinda «2026. gada …» nedrīkst kļūt par numurētu sarakstu.

Kļūme (2026-10-23, 10 lapas): markdown rindas sākumu «2026.» uztvēra kā saraksta
numuru — gads pazuda, teikums kļuva par saraksta punktu.
"""
import markdown
import pytest

from src.render._common.filters import escape_year_list_markers


@pytest.mark.parametrize("src", [
    "2026. gada 18. oktobrī lūdzām komentāru.",
    "- 2025. gada aprīlī pieņemti grozījumi",
    "Teikums.\n\n2019. g. tika pieņemts likums",
])
def test_year_at_line_start_stays_text(src):
    html = markdown.markdown(escape_year_list_markers(src))
    assert "<ol" not in html
    year = next(w for w in src.replace("\n", " ").split() if w[:2] in ("19", "20"))
    assert year in html


@pytest.mark.parametrize("src", ["1. punkts\n2. punkts", "2026. Gads ar lielo burtu"])
def test_real_lists_untouched(src):
    assert escape_year_list_markers(src) == src
