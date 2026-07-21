"""Test suite for saeima vote result audit guardrail."""

import pytest
from scripts.audit_saeima_vote_results import compute_expected_result


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
