"""One name per contradiction type, everywhere (operator decision 2026-09-28).

Failure guarded: the same ``severity`` drifted to three names — ``reversal``
was «Apvērsums» on the site and graph but «reversija» in the brief;
``minor_shift`` was «Pozīcijas maiņa», «neliela novirze» and «Nobīde» — and
«Pozīcijas maiņa» also named the ``position_position`` category. Each surface
kept a private copy, so a rename in one left the others behind.
"""

from __future__ import annotations

import re
from pathlib import Path

from src.contradiction_labels import CATEGORY_LV, SEVERITY_LV, lower_first

ROOT = Path(__file__).resolve().parent.parent


def test_render_constants_are_the_canonical_maps():
    from src.render._common import CATEGORY_LV as r_cat
    from src.render._common import SEVERITY_LV as r_sev

    assert r_sev is SEVERITY_LV and r_cat is CATEGORY_LV


def test_brief_severity_is_lowercased_canonical():
    from src.briefs import _SEVERITY_LV

    assert _SEVERITY_LV == {k: lower_first(v) for k, v in SEVERITY_LV.items()}


def test_graph_js_severity_literals_match_python():
    """assets/sav1.js (saites graph side panel) cannot import Python — its
    ternary literals must equal the canonical map."""
    js = (ROOT / "assets" / "sav1.js").read_text(encoding="utf-8")
    m = re.search(
        r"var sevLabel = c\.severity === 'direct_contradiction' \? '([^']+)' :\s*"
        r"c\.severity === 'reversal' \? '([^']+)' : '([^']+)';",
        js,
    )
    assert m, "sav1.js sevLabel ternary not found — update this test with the new shape"
    assert m.groups() == (
        SEVERITY_LV["direct_contradiction"],
        SEVERITY_LV["reversal"],
        SEVERITY_LV["minor_shift"],
    )


def test_social_drafter_and_chart_colours_share_the_vocabulary():
    from src.social_agent.drafters import _category_subtitle
    from src.social_agent.visuals import _CATEGORY_COLORS

    assert _category_subtitle("position", "saeima_vote") == lower_first(CATEGORY_LV["position_saeima_vote"])
    assert set(_CATEGORY_COLORS) == set(CATEGORY_LV.values())


def test_retired_names_are_gone_from_code_surfaces():
    retired = ("Apvērsum", "apvērsum", "reversij", "Nobīde", "vs. Darbi", "vs. darbi")
    surfaces = [
        *ROOT.glob("templates/*.j2"),
        *ROOT.glob("assets/*.js"),
        ROOT / "src" / "render" / "_common" / "constants.py",
        ROOT / "src" / "social_agent" / "drafters.py",
        ROOT / "src" / "social_agent" / "visuals.py",
    ]
    assert len(surfaces) > 20  # denominator: a bad glob must not pass silently
    hits = [
        f"{p.relative_to(ROOT)}: {w}"
        for p in surfaces
        for w in retired
        if w in p.read_text(encoding="utf-8")
    ]
    assert hits == []
