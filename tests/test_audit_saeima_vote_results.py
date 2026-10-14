"""Test suite for saeima vote result audit guardrail."""

import pytest
from scripts.audit_saeima_vote_results import (
    _OUTCOME_ALIASES,
    _outcome_class,
    compute_expected_result,
)


def test_majority_par_above_present_half():
    # 60 par, 30 pret, 5 atturas → present=95, par > 47 → pieņemts
    assert compute_expected_result(60, 30, 5) == "pieņemts"


def test_majority_par_equal_present_half_is_noraidits():
    # 50 par, 30 pret, 20 atturas → present=100, par == 50 (not strictly greater) → noraidīts
    assert compute_expected_result(50, 30, 20) == "noraidīts"


def test_majority_par_below_present_half():
    # 30 par, 60 pret, 5 atturas → present=95, par < 48 → noraidīts
    assert compute_expected_result(30, 60, 5) == "noraidīts"


def test_zero_present_returns_nezinams():
    # All abstain or absent → no quorum participated
    assert compute_expected_result(0, 0, 0) == "nezināms"


def test_only_atturas_counts_as_present_so_par_zero_loses():
    # 0 par, 0 pret, 50 atturas → present=50, par=0 → noraidīts (atturas counts as present)
    assert compute_expected_result(0, 0, 50) == "noraidīts"


def test_nebalsoja_is_not_in_the_denominator():
    """Reference case vote 183 (2026-05-14), ingested live by @saeima-tracker.

    47 par / 44 pret / 1 atturas / 3 nebalsoja; the rendered page carried
    'Pieņemts'. Present = 92 (cast only) → majority 46 → 47 wins. Counting the
    3 nebalsoja would give present 95, majority 47, and predict 'noraidīts' —
    the reading used by the urllib backfill's fallback, which this test pins as
    wrong (checked 2026-08-17; votes 194 and 213 are the same class).
    """
    assert compute_expected_result(47, 44, 1) == "pieņemts"
    assert compute_expected_result(41, 28, 1) == "pieņemts"
    assert compute_expected_result(45, 7, 30) == "pieņemts"


# ── result dictionary: not binary ────────────────────────────────────────────
# Operator verdict 2026-08-18 (BACKLOG § Saeima): the literal agenda label
# `Nod. kom.` is stored VERBATIM, not mapped to `Pieņemts`. The audit resolves
# it to an outcome class so the numbers are still checked.


def test_nod_kom_resolves_to_pienemts_outcome_class():
    assert _outcome_class("Nod. kom.") == "pieņemts"
    assert _outcome_class(" nod. kom. ") == "pieņemts"


def test_likums_and_pazinojums_resolve_to_pienemts_outcome_class():
    """2026-08-21: verbatim action-labels from the live agenda page (20.08
    session, all rows result_source='agenda_label'). 'Likums' = the law was
    adopted; 'Paziņojums' = the announcement carried — both the ACTION of a
    carried motion, same class as 'Nod. kom.'."""
    assert _outcome_class("Likums") == "pieņemts"
    assert _outcome_class("Paziņojums") == "pieņemts"


@pytest.mark.parametrize(
    "par,pret,atturas",
    [
        (88, 0, 0),   # vote 7916, Likums
        (60, 26, 0),  # vote 7922, Likums
        (70, 17, 1),  # vote 7924, Likums
        (88, 0, 0),   # vote 7925, Likums
        (79, 0, 0),   # vote 7926, Likums
        (87, 0, 0),   # vote 7951, Paziņojums
        (89, 0, 0),   # vote 7953, Paziņojums
    ],
)
def test_likums_pazinojums_rows_agree_with_present_majority(par, pret, atturas):
    """The alias is a dictionary entry, not a gate bypass: every 'Likums' /
    'Paziņojums' row in the corpus must satisfy the present-majority rule."""
    for label in ("Likums", "Paziņojums"):
        assert _outcome_class(label) == compute_expected_result(par, pret, atturas)


def test_plain_labels_pass_through_unaliased():
    assert _outcome_class("Pieņemts") == "pieņemts"
    assert _outcome_class("Noraidīts") == "noraidīts"
    assert _outcome_class(None) == ""
    assert _outcome_class("") == ""


@pytest.mark.parametrize(
    "par,pret,atturas",
    [
        (41, 2, 38),   # vote 1435
        (42, 33, 1),   # vote 905
        (43, 14, 24),  # vote 956
        (46, 33, 0),   # vote 6192
    ],
)
def test_nod_kom_rows_agree_with_present_majority(par, pret, atturas):
    """The alias is a dictionary entry, not a gate bypass.

    Each of the four `Nod. kom.` rows must still satisfy the present-majority
    rule — a referral to committee only happens when the motion carried. If a
    future row carries this label with numbers that say noraidīts, the audit
    must still flag it.
    """
    assert _outcome_class("Nod. kom.") == compute_expected_result(par, pret, atturas)


def test_alias_map_stays_narrow():
    """Guard against the map growing into a catch-all that silences the audit.

    2026-08-21: widened to 'likums' + 'paziņojums' (verbatim agenda action-
    labels of carried motions, all result_source='agenda_label'). Every entry
    must remain a SOURCE-SEEN label with an evidence trail in CHANGELOG —
    never a convenience mapping invented to make the gate green.
    """
    assert _OUTCOME_ALIASES == {
        "nod. kom.": "pieņemts",
        "likums": "pieņemts",
        "paziņojums": "pieņemts",
    }
    assert all(v in ("pieņemts", "noraidīts") for v in _OUTCOME_ALIASES.values())
    assert all(k == k.strip().lower() for k in _OUTCOME_ALIASES)
