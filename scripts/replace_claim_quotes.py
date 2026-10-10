"""Replace `claims.quote` with a VERBATIM sentence from the claim's own document.

Operator decision 2026-09-23 (CHANGELOG 2026-09-23 (2)): when a claim's quote
is the journalist's lede or the headline — the stub-era class found by the
truncated-doc backfill (docs/audits/2026-09-23-backfill-trial48-reextract.md)
— it may be replaced with the politician's own words, on two conditions:

  1. the new quote appears VERBATIM in the claim's document (code-enforced
     here: a contiguous substring after whitespace collapse and HTML-entity
     decoding — no ellipses, no bracketed cuts, no case folding);
  2. every replacement ships a rollback, written and fsynced BEFORE the
     UPDATE.

Who is speaking is NOT checkable by code — the caller (an Opus extraction
agent) owns that; this tool only guarantees the words are really in the text.
`quote` is not part of the claim embedding (`store_claim` embeds
"{topic}: {stance}"), so no re-embed is needed.

Input: JSON list of {"claim_id": int, "quote": str, "reason": str}.

    python scripts/replace_claim_quotes.py --input fixes.json --report out.jsonl
    python scripts/replace_claim_quotes.py --input fixes.json --report out.jsonl \
        --apply --rollback-out data/rollback_claim_quotes_<scope>_YYYY-MM-DD.sql
"""
from __future__ import annotations

import argparse
import html
import json
import os
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import DB_PATH, get_db, now_lv  # noqa: E402

MIN_QUOTE_CHARS = 20


def _norm(text: Optional[str]) -> str:
    return " ".join(html.unescape(text or "").split())


def _sql_lit(v) -> str:
    if v is None:
        return "NULL"
    return "'" + str(v).replace("'", "''") + "'"


def classify(db, fix: dict) -> tuple[str, Optional[dict]]:
    """Return (class, claim_row). Only 'ok' may be written."""
    quote = _norm(fix.get("quote"))
    if len(quote) < MIN_QUOTE_CHARS:
        return "too_short", None
    row = db.execute(
        "SELECT c.id, c.quote, c.document_id, d.content FROM claims c "
        "LEFT JOIN documents d ON d.id = c.document_id WHERE c.id = ?",
        (fix["claim_id"],),
    ).fetchone()
    if row is None:
        return "claim_missing", None
    if row["document_id"] is None or row["content"] is None:
        return "no_document", row
    if quote not in _norm(row["content"]):
        return "not_verbatim", row
    if _norm(row["quote"]) == quote:
        return "unchanged", row
    return "ok", row


def run(fixes: list[dict], *, db_path: str = DB_PATH, apply: bool = False,
        rollback_path: Optional[str] = None,
        report_path: Optional[str] = None) -> dict:
    if apply and not rollback_path:
        raise ValueError("apply requires rollback_path")
    db = get_db(db_path)
    counts: dict[str, int] = {}
    records = []
    rb = None
    try:
        for fix in fixes:
            cls, row = classify(db, fix)
            new_quote = _norm(fix.get("quote"))
            if cls == "ok" and apply:
                if rb is None:
                    rb = open(rollback_path, "w", encoding="utf-8", newline="\n")
                    rb.write(
                        f"-- Rollback: scripts/replace_claim_quotes.py --apply, run {now_lv()[:10]}\n"
                        "-- Forward change: claims.quote replaced with a verbatim sentence\n"
                        "--   from the claim's own document (operator decision 2026-09-23).\n\n"
                    )
                rb.write(f"UPDATE claims SET quote = {_sql_lit(row['quote'])} "
                         f"WHERE id = {row['id']};\n")
                rb.flush()
                os.fsync(rb.fileno())
                db.execute("UPDATE claims SET quote = ? WHERE id = ?",
                           (new_quote, row["id"]))
                db.commit()
                stored = db.execute("SELECT quote FROM claims WHERE id = ?",
                                    (row["id"],)).fetchone()["quote"]
                cls = "updated" if stored == new_quote else "update_failed"
            counts[cls] = counts.get(cls, 0) + 1
            rec = {"claim_id": fix["claim_id"], "class": cls,
                   "old_quote": row["quote"] if row else None,
                   "new_quote": new_quote, "reason": fix.get("reason")}
            records.append(rec)
    finally:
        if rb:
            rb.close()
        db.close()
    if report_path:
        with open(report_path, "w", encoding="utf-8", newline="\n") as fh:
            for rec in records:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return {"examined": len(fixes), **counts, "records": records}


def main(argv: Optional[list[str]] = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--input", required=True, help="JSON list of fixes")
    ap.add_argument("--db", default=DB_PATH)
    ap.add_argument("--report", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--rollback-out")
    args = ap.parse_args(argv)
    if args.apply and not args.rollback_out:
        print("error: --apply requires --rollback-out", file=sys.stderr)
        return 2
    fixes = json.loads(Path(args.input).read_text(encoding="utf-8"))
    summary = run(fixes, db_path=args.db, apply=args.apply,
                  rollback_path=args.rollback_out, report_path=args.report)
    print(" ".join(f"{k}={v}" for k, v in summary.items() if k != "records"))
    for r in summary["records"]:
        if r["class"] not in ("ok", "updated", "unchanged"):
            print(f"  {r['claim_id']}: {r['class']}", file=sys.stderr)
    if not args.apply:
        print("(dry-run — nekas nav rakstīts)")
    return 2 if not fixes else 0


if __name__ == "__main__":
    raise SystemExit(main())
