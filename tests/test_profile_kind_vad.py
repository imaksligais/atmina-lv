"""Tests for the deklaracijas tab integration into _profile_tab_set."""
from src.render.politicians import _profile_tab_set


def test_deputy_with_vad_gets_deklaracijas_tab():
    tabs = _profile_tab_set("deputy", has_contradictions=False, has_saites_content=False, has_vad_data=True)
    assert "deklaracijas" in tabs


def test_deputy_without_vad_no_tab():
    tabs = _profile_tab_set("deputy", False, False, has_vad_data=False)
    assert "deklaracijas" not in tabs


def test_journalist_with_vad_no_tab():
    tabs = _profile_tab_set("journalist", False, False, has_vad_data=True)
    assert "deklaracijas" not in tabs


def test_organization_with_vad_no_tab():
    tabs = _profile_tab_set("organization", False, False, has_vad_data=True)
    assert "deklaracijas" not in tabs


def test_minister_with_vad_gets_tab():
    tabs = _profile_tab_set("minister", False, False, has_vad_data=True)
    assert "deklaracijas" in tabs


def test_former_with_vad_gets_tab():
    tabs = _profile_tab_set("former", False, False, has_vad_data=True)
    assert "deklaracijas" in tabs


def test_inactive_with_vad_no_tab():
    tabs = _profile_tab_set("inactive", False, False, has_vad_data=True)
    assert "deklaracijas" not in tabs


def test_default_signature_no_vad_no_change():
    # Backward compat: callers that don't pass has_vad_data shouldn't get the tab
    tabs = _profile_tab_set("deputy", False, False)
    assert "deklaracijas" not in tabs


# ── Saeimā tab gated on actual vote presence ────────────────────────
# Regression: a 'former' profile_kind is assigned to anyone whose role
# text contains "bijuš…" with zero current-term votes — which captures
# former mayors and former TV hosts, NOT just former deputies. Those
# profiles must NOT show a "bijušais deputāts" Saeimā tab when there are
# no votes to display.


def test_former_without_saeima_content_no_tab():
    tabs = _profile_tab_set("former", has_saeima_content=False)
    assert "saeima" not in tabs


def test_former_with_saeima_content_gets_tab():
    tabs = _profile_tab_set("former", has_saeima_content=True)
    assert "saeima" in tabs


def test_deputy_default_keeps_saeima_tab():
    # Deputy kind implies current-term votes; default signature
    # (has_saeima_content defaulting True) must preserve the Saeimā tab
    # for existing callers.
    tabs = _profile_tab_set("deputy")
    assert "saeima" in tabs


def test_deputy_without_saeima_content_no_tab():
    tabs = _profile_tab_set("deputy", has_saeima_content=False)
    assert "saeima" not in tabs
