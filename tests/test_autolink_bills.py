"""Phase 1C — autolink_bills Jinja filter wraps bill references in <a> tags."""
import pytest

from src.render._common import _autolink_bills_filter


def test_single_bill_match():
    out = _autolink_bills_filter("Atbalsta 1288/Lp14 likumprojektu", {"1288-lp14"})
    assert '<a href="likumprojekti/1288-lp14.html">1288/Lp14</a>' in out


def test_unknown_doc_nr_preserved():
    out = _autolink_bills_filter("Atbalsta 9999/Lp14", set())
    assert out == "Atbalsta 9999/Lp14"
    assert "<a" not in out


def test_multiple_bills_one_summary():
    out = _autolink_bills_filter("1288/Lp14 un 934/Lm14", {"1288-lp14", "934-lm14"})
    assert out.count("<a href=") == 2


def test_surrounding_punctuation():
    out = _autolink_bills_filter("(1288/Lp14), 934/Lm14.", {"1288-lp14", "934-lm14"})
    assert '>1288/Lp14</a>' in out
    assert '>934/Lm14</a>' in out


def test_word_boundary_no_partial_match():
    # Should NOT wrap "abc1288/Lp14def" — \b ensures clean boundaries
    out = _autolink_bills_filter("abc1288/Lp14def", {"1288-lp14"})
    assert "<a" not in out


def test_empty_text_and_none_slugs_graceful():
    assert _autolink_bills_filter("", set()) == ""
    assert _autolink_bills_filter(None, set()) == ""
    # bill_slugs=None must not crash (graceful default)
    assert _autolink_bills_filter("Atbalsta 1288/Lp14", None) == "Atbalsta 1288/Lp14"


def test_lp15_and_mixed_convocations():
    out = _autolink_bills_filter(
        "Skatīt 1/Lp15 un 1315/Lp14; 5/P140 nav numurs.",
        bill_slugs={"1-lp15", "1315-lp14"},
    )
    assert 'href="likumprojekti/1-lp15.html"' in out
    assert 'href="likumprojekti/1315-lp14.html"' in out
    assert "5/P140" in out and "p140" not in out
