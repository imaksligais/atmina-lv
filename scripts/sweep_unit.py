"""Print one backlog-sweep work unit chunk.

    .venv/Scripts/python.exe scripts/sweep_unit.py <plan_key> <unit> <chunk> [--plan PATH]

`--plan` defaults to the 2026-10-05 historic sweep plan; plans for later sweeps
come from `scripts/plan_stale_sweep.py`.
"""
import argparse
import json

DEFAULT_PLAN = "docs/audits/2026-10-05-backlog-sweep/plan.json"

ap = argparse.ArgumentParser()
ap.add_argument("key")
ap.add_argument("unit", type=int)
ap.add_argument("chunk", type=int)
ap.add_argument("--plan", default=DEFAULT_PLAN)
args = ap.parse_args()

plan = json.load(open(args.plan, encoding="utf-8"))
u = plan[args.key][args.unit]
pols = {p["pid"]: p for p in u["pols"]}
for c in u["chunks"][args.chunk]:
    p = pols[c["pid"]]
    ar = [d for d in p.get("already_reviewed", []) if d in c["docs"]]
    noun = "claims" if u.get("kind") == "claims" else "docs"
    print(f"pid {c['pid']} ({p['name']}): {noun} {', '.join(map(str, c['docs']))}"
          + (f" — already_reviewed: {', '.join(map(str, ar))}" if ar else ""))
