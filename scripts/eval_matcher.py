"""Run src.matcher.match_politicians() over the hand-labeled eval set
and report per-case correctness plus overall precision / recall / F1.

Distinct from tests/test_matcher.py (which pins CURRENT behavior).
This eval measures REAL correctness — failing cases are real bugs.

Usage:
    PYTHONPATH=. python scripts/eval_matcher.py                # full report
    PYTHONPATH=. python scripts/eval_matcher.py --fails-only   # only failing cases
    PYTHONPATH=. python scripts/eval_matcher.py --metric-only  # single line: "F1=0.xxx"

Fixture: tests/fixtures/eval_matcher_labeled.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.matcher import match_politicians, _clear_politician_cache

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "eval_matcher_labeled.json"


def _evaluate_case(case: dict) -> dict:
    """Run matcher on one case, return per-case verdict + counts."""
    text = case["text"]
    expected_ids = {pid for pid, _role in case.get("expected_matches", [])}
    expected_excludes = set(case.get("expected_excludes", []))

    actual = match_politicians(text)
    actual_ids = {pid for pid, _role in actual}

    true_positives = expected_ids & actual_ids
    false_positives = actual_ids - expected_ids
    false_negatives = expected_ids - actual_ids
    excluded_but_matched = expected_excludes & actual_ids

    return {
        "id": case["id"],
        "category": case["category"],
        "passed": not false_positives and not false_negatives and not excluded_but_matched,
        "expected": sorted(expected_ids),
        "actual": sorted(actual_ids),
        "true_positives": sorted(true_positives),
        "false_positives": sorted(false_positives),
        "false_negatives": sorted(false_negatives),
        "excluded_but_matched": sorted(excluded_but_matched),
        "source_url": case.get("source_url"),
        "note": case.get("note", ""),
        "actual_roles": actual,
    }


def _aggregate(verdicts: list[dict]) -> dict:
    """Sum TP/FP/FN across all cases for micro-averaged P/R/F1."""
    tp = sum(len(v["true_positives"]) for v in verdicts)
    fp = sum(len(v["false_positives"]) + len(v["excluded_but_matched"]) for v in verdicts)
    fn = sum(len(v["false_negatives"]) for v in verdicts)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    pass_count = sum(1 for v in verdicts if v["passed"])
    return {
        "cases_total": len(verdicts),
        "cases_passed": pass_count,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fails-only", action="store_true", help="Only print failing cases")
    parser.add_argument("--metric-only", action="store_true", help="Print only 'F1=0.xxx' (for /goal-style verify scripts)")
    args = parser.parse_args()

    with FIXTURE_PATH.open(encoding="utf-8") as f:
        fixture = json.load(f)

    _clear_politician_cache()
    verdicts = [_evaluate_case(c) for c in fixture["cases"]]
    agg = _aggregate(verdicts)

    if args.metric_only:
        print(f"F1={agg['f1']:.4f}")
        return 0

    for v in verdicts:
        if args.fails_only and v["passed"]:
            continue
        status = "PASS" if v["passed"] else "FAIL"
        print(f"[{status}] {v['id']}  ({v['category']})")
        if not v["passed"]:
            print(f"        expected: {v['expected']}")
            print(f"        actual:   {v['actual']}")
            if v["false_positives"]:
                print(f"        false +:  {v['false_positives']}")
            if v["false_negatives"]:
                print(f"        false -:  {v['false_negatives']}")
            if v["excluded_but_matched"]:
                print(f"        excluded but matched (collision regression!):  {v['excluded_but_matched']}")
            print(f"        source:   {v['source_url']}")
            print(f"        note:     {v['note']}")
            print()

    print("=" * 70)
    print(f"Cases: {agg['cases_passed']}/{agg['cases_total']} passing")
    print(f"Politician-ID matches — TP={agg['tp']}  FP={agg['fp']}  FN={agg['fn']}")
    print(f"Precision={agg['precision']:.4f}  Recall={agg['recall']:.4f}  F1={agg['f1']:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
