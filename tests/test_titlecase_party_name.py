"""Regression: _titlecase_party_name must treat '/' as a word boundary.

SV/AJ ("Suverēnā vara/Jaunlatvieši", parties id=19, seeded 2026-07-08) was the
first tracked party with '/' in its name; the space-only split produced
"Suverēnā Vara/jaunlatvieši" in <title>/<h1> (caught by @quality-reviewer
pre-deploy gate 2026-07-08).
"""

from src.render._common import _titlecase_party_name


def test_slash_is_word_boundary():
    assert (
        _titlecase_party_name("Suverēnā vara/Jaunlatvieši")
        == "Suverēnā Vara/Jaunlatvieši"
    )


def test_plain_names_unchanged_behavior():
    # Established site style (matches live pages pre-fix).
    assert _titlecase_party_name("Latvijas attīstībai") == "Latvijas Attīstībai"
    assert (
        _titlecase_party_name("Zaļo un Zemnieku savienība")
        == "Zaļo un Zemnieku Savienība"
    )


def test_lowercase_conjunction_after_slash():
    assert _titlecase_party_name("A/un B") == "A/un B"
