"""Tests for scripts/backfill_titles.py — title derivation from existing content."""
from scripts.backfill_titles import derive_title_from_content


def test_first_line_extracted_as_title():
    content = "Saeima atbalsta budžetu\n\nŠodien Saeima trešajā lasījumā..."
    assert derive_title_from_content(content) == "Saeima atbalsta budžetu"


def test_site_suffix_stripped_from_first_line():
    content = "Saeima atbalsta budžetu - LSM.lv\n\nŠodien Saeima..."
    assert derive_title_from_content(content) == "Saeima atbalsta budžetu"


def test_skips_too_short_first_line():
    content = "FOTO\n\nSaeima atbalsta budžetu šodien plkst. 14.00."
    # First line "FOTO" is too short — falls through to next non-empty line
    assert derive_title_from_content(content) == "Saeima atbalsta budžetu šodien plkst. 14.00."


def test_skips_too_long_first_line():
    long_line = "x" * 500
    content = f"{long_line}\n\nReāls virsraksts šeit"
    out = derive_title_from_content(content)
    # Skip the 500-char line; pick the next reasonable one
    assert out == "Reāls virsraksts šeit"


def test_returns_none_for_empty_content():
    assert derive_title_from_content("") is None
    assert derive_title_from_content(None) is None


def test_strips_trailing_zero_count_marker():
    """LA.lv content often ends first line with ' 0' (comment count). Strip it."""
    content = "Premjeres VIP tēriņi Amsterdamā: atbilde 0\n\nVairāk nekā 4000 eiro..."
    assert derive_title_from_content(content) == "Premjeres VIP tēriņi Amsterdamā: atbilde"


def test_splits_rss_title_description_join():
    """RSS items concat title+description with ' — '. Use the prefix as title
    when the joined line is too long for the length gate."""
    title = "Saeima atbalsta budžetu"
    desc = "x" * 300
    content = f"{title} — {desc}\n\nNext paragraph."
    assert derive_title_from_content(content) == title


def test_does_not_split_short_lines_with_em_dash():
    """If line is within the length gate, an em-dash is part of the title —
    do not split."""
    content = "Komentārs — Kāpēc tas ir svarīgi\n\nDescription here."
    assert derive_title_from_content(content) == "Komentārs — Kāpēc tas ir svarīgi"
