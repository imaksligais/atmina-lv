"""Shadow-week report for the TypeSafe matcher veto.

Reads logs/typesafe_veto.jsonl and lists every vetoed (or would-be vetoed)
surname-only match with its snippet, grouped by politician, so the operator
can spot gold losses before switching ATMINA_TYPESAFE_VETO to enforce.
Always prints the denominator (judged / vetoed / unavailable) first — a
report that shows only findings is not evidence.

Usage: .venv/Scripts/python.exe scripts/typesafe_veto_report.py --days 7
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db import get_db  # noqa: E402
from src.matcher_veto import LOG_PATH  # noqa: E402


def summarize(events: list[dict]) -> dict:
    by_pid: dict[int, int] = {}
    for e in events:
        if e["vetoed"]:
            by_pid[e["pid"]] = by_pid.get(e["pid"], 0) + 1
    return {"judged": len(events), "vetoed": sum(1 for e in events if e["vetoed"]),
            "unavailable": sum(1 for e in events if e["p_same"] is None), "by_pid": by_pid}


def shadow_verdict(s: dict) -> str:
    """'scored' only if TypeSafe actually judged something in the window.

    A window where every call was unavailable (HTTP 402 on 2026-09-22: judged
    112, unavailable 112) prints "vetoed 0", which reads as a clean shadow day
    but is no evidence at all — such days must not count toward the 7.
    """
    return "scored" if s["judged"] - s["unavailable"] > 0 else "no_evidence"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    args = ap.parse_args()
    if not LOG_PATH.exists():
        print(f"no events: {LOG_PATH} missing")
        return 0
    since = (datetime.now() - timedelta(days=args.days)).isoformat(timespec="seconds")
    events = [json.loads(line) for line in LOG_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    events = [e for e in events if e.get("ts", "") >= since]
    db = get_db()
    names = {r["id"]: r["name"] for r in db.execute("SELECT id, name FROM tracked_politicians")}
    db.close()
    s = summarize(events)
    print(f"judged {s['judged']}  vetoed {s['vetoed']}  unavailable {s['unavailable']}  (last {args.days} d)")
    if shadow_verdict(s) == "no_evidence":
        print("NO EVIDENCE: TypeSafe scored 0 matches in this window — it does NOT count as a shadow day")
        return 2
    for pid, n in sorted(s["by_pid"].items(), key=lambda x: -x[1]):
        print(f"  {names.get(pid, pid):<30} {n}")
    for e in events:
        if e["vetoed"]:
            print(f"  {e['ts']} {names.get(e['pid'], e['pid']):<26} p={e['p_same']:.2f} [{e['mode']}] {e['snippet'][:120]!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
