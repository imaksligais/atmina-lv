"""Tests for src.graphics.prompt — nanobanana prompt composition."""
import pytest
from src.graphics import prompt
from src.graphics.visual_map import get_visual


def test_build_prompt_includes_headline_and_metaphor():
    vb = {
        "topic": "Budžets un finanses",
        "headline": "Saeima apstiprina budžeta grozījumus",
        "stat": "+47 milj.",
        "metaphor_hint": "budžeta dokuments",
    }
    vm = get_visual(vb["topic"])
    p = prompt.build_prompt(vb, vm, style_key="editorial")
    assert "Saeima apstiprina budžeta grozījumus" in p
    assert "+47 milj." in p
    # metaphor may contain "OR" alternatives — check at least the opening fragment appears
    first_alt = vm["metaphor"].split(" OR ")[0].strip()
    assert first_alt in p


def test_build_prompt_omits_stat_section_when_none():
    vb = {
        "topic": "airBaltic",
        "headline": "airBaltic krīze",
        "stat": None,
        "metaphor_hint": "",
    }
    vm = get_visual("airBaltic")
    p = prompt.build_prompt(vb, vm, style_key="editorial")
    assert "Key figure" not in p


def test_build_prompt_omits_stat_section_when_dash():
    vb = {
        "topic": "airBaltic",
        "headline": "airBaltic krīze",
        "stat": "-",
        "metaphor_hint": "",
    }
    vm = get_visual("airBaltic")
    p = prompt.build_prompt(vb, vm, style_key="editorial")
    assert "Key figure" not in p
    assert "prominently: -" not in p


def test_build_prompt_unknown_style_raises():
    vb = {"topic": "airBaltic", "headline": "x", "stat": None, "metaphor_hint": ""}
    vm = get_visual("airBaltic")
    with pytest.raises(KeyError):
        prompt.build_prompt(vb, vm, style_key="nonexistent")


def test_style_variants_exist():
    assert set(prompt.STYLE_VARIANTS.keys()) == {"editorial", "scandi", "constructivist", "weekly"}


def test_weekly_style_exists_and_builds():
    vb = {"topic": "Koalīcija un partijas", "headline": "Apstiprināta valdība",
          "stat": "5 % IKP", "metaphor_hint": "puzzle"}
    vm = {"metaphor": "interlocking puzzle pieces", "mood": "tension", "accent": "ink navy"}
    p = prompt.build_prompt(vb, vm, style_key="weekly")
    assert "Apstiprināta valdība" in p
    assert "navy" in p.lower()


def test_default_style_is_valid_variant():
    assert prompt.DEFAULT_STYLE in prompt.STYLE_VARIANTS


def test_style_variants_are_nonempty_strings():
    for key, val in prompt.STYLE_VARIANTS.items():
        assert isinstance(val, str) and val.strip(), f"Style '{key}' is empty"


def test_build_prompt_includes_negative_constraints():
    vb = {"topic": "airBaltic", "headline": "x", "stat": None, "metaphor_hint": ""}
    vm = get_visual("airBaltic")
    p = prompt.build_prompt(vb, vm, style_key="editorial")
    # Negative constraints section must explicitly forbid people, flags, logos
    assert "people" in p.lower() or "faces" in p.lower()
    assert "flag" in p.lower()
    assert "logo" in p.lower()


def test_build_prompt_preserves_diacritics_instruction():
    vb = {"topic": "airBaltic", "headline": "Sākums", "stat": None, "metaphor_hint": ""}
    vm = get_visual("airBaltic")
    p = prompt.build_prompt(vb, vm, style_key="editorial")
    # Explicit instruction to preserve Latvian diacritics must appear
    assert "diacritic" in p.lower()
