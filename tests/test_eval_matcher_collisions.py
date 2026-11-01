"""Tests for scripts.eval_matcher_collisions — declared regression gates are enforced."""

from scripts.eval_matcher_collisions import (
    REGRESSION_FP_LINKS_MAX,
    REGRESSION_GOLD_HIT_MIN,
    regression_gates_failed,
)


def _run(fp_links=0, gold_hit=1300):
    return {"fp_links": list(range(fp_links)), "gold_hit": gold_hit}


def test_gates_pass_at_declared_thresholds():
    assert regression_gates_failed(_run(fp_links=3, gold_hit=1260)) is False


def test_gates_pass_inside_thresholds():
    assert regression_gates_failed(_run(fp_links=0, gold_hit=2000)) is False


def test_gate_fails_on_too_many_fp_links():
    assert regression_gates_failed(_run(fp_links=4, gold_hit=1260)) is True


def test_gate_fails_on_low_gold_hit():
    assert regression_gates_failed(_run(fp_links=0, gold_hit=1259)) is True


def test_thresholds_match_docstring_contract():
    """The enforced constants must equal the gates documented in the module docstring."""
    assert REGRESSION_FP_LINKS_MAX == 3
    assert REGRESSION_GOLD_HIT_MIN == 1260
