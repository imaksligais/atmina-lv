#!/usr/bin/env python
"""Ekstrakcijas sadalījuma plāns — kurš politiķis/doks kurā @claim-extractor
apakšaģentā un kurā kārtā (noteikumi: `src/extraction_plan.py` docstring).

Tikai lasa DB; neko neraksta.

Lietošana:
    .venv/Scripts/python.exe scripts/plan_extraction.py --days 2
    .venv/Scripts/python.exe scripts/plan_extraction.py --days 2 --json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src.extraction_plan import format_plan_line, plan_extraction_batches  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Ekstrakcijas sadalījuma plāns (tikai lasa DB).")
    ap.add_argument("--days", type=int, default=1, help="rindas logs dienās (noklusējums 1)")
    ap.add_argument("--json", action="store_true", help="izvade JSON formā")
    args = ap.parse_args(argv)

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    os.chdir(REPO)  # DB_PATH ir relatīvs repo saknei

    plan = plan_extraction_batches(days=args.days)
    if args.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    print(format_plan_line(plan["summary"]) + f" — pāri {plan['summary']['pairs']}")
    for d in plan["summary"].get("dropped") or []:
        print(f"  IZMESTS pid {d['pid']} {d['name']}: {d['reason']}")
    if not plan["agents"]:
        print("  (rinda tukša — nav ko dispečēt)")
        return 0
    for a in plan["agents"]:
        n = sum(len(i["doc_ids"]) for i in a["items"])
        print(f"\n#{a['agent']:>2}  kārta {a['round']}  {a['kind']:<4}  {n} doki")
        for i in a["items"]:
            ids = ", ".join(str(d) for d in i["doc_ids"])
            print(f"      pid {i['pid']:<5} {i['name']:<28} [{ids}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
