"""Daily TypeSafe pass: propose Saites links for a human to confirm.

Usage: .venv/Scripts/python.exe scripts/saites_proposals.py [--days 1] [--date YYYY-MM-DD]
Writes only `tension_proposals` + `tension_judged`; prints the denominator
(docs / judged / new proposals / errors / input tokens) and then every
pending proposal. One log_action('saites_proposals') is written AFTER the DB
connection used for judging is closed (second-connection busy-timeout rule).
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db import get_db, init_db, log_action  # noqa: E402
from src.saites_proposals import run  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=1)
    ap.add_argument("--date", default=date.today().isoformat())
    a = ap.parse_args()
    init_db()  # idempotent: applies the tension_proposals / tension_judged migration (same as ingest)
    db = get_db()
    summary = run(db, days=a.days)
    names = {r["id"]: r["name"] for r in db.execute("SELECT id, name FROM tracked_politicians")}
    rows = db.execute(
        "SELECT * FROM tension_proposals WHERE status = 'pending' ORDER BY relation, p_link DESC").fetchall()
    db.close()
    log_action("saites_proposals", status="success" if summary["errors"] == 0 else "partial",
               details={"date": a.date, **summary})
    print(f"docs {summary['docs']}  judged {summary['judged']}  new proposals {summary['proposed']}  "
          f"errors {summary['errors']}  input tokens {summary['input_tokens']}")
    print(f"pending proposals: {len(rows)}")
    for r in rows:
        print(f"  #{r['id']:<5} {r['relation']:<10} link={r['p_link']:.2f} type={r['p_relation']:.2f} "
              f"speaks={r['p_speaks']:.2f} doc {r['document_id']:<7} "
              f"{names.get(r['source_pid'], r['source_pid'])} -> {names.get(r['target_pid'], r['target_pid'])}")
        print(f"         {r['snippet']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
