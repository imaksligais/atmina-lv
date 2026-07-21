"""One-shot backfill of saeima_bills from existing saeima_votes rows.

Reads all saeima_votes, groups by document_nr (falling back to
resolve_bill_from_motif() when document_nr is NULL), upserts a bill per
group, and appends one stage row per vote (using _reading_from_motif for
stage_name classification). Idempotent — safe to re-run; existing bills are
upserted, stages with the same vote_id are skipped.

Spec § 5. Acceptance: spec § 5.4.

Usage:
    python scripts/backfill_saeima_bills.py             # production DB
    python scripts/backfill_saeima_bills.py --dry-run   # report-only
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db import DB_PATH, get_db  # noqa: E402
from src.saeima import (  # noqa: E402
    init_saeima_bills,
    upsert_bill,
    append_bill_stage,
    _reading_from_motif,
    resolve_bill_from_motif,
)


def _extract_title_from_motif(motif: str) -> str:
    """Extract a human-readable title from a vote motif.

    Strips the trailing '(NNN/Lp14)' suffix and reading qualifier.
    """
    if not motif:
        return ""
    title = motif.split("(")[0].strip().rstrip(",").strip()
    return title or motif[:80]


def _bill_type_from_doc_nr(doc_nr: str) -> Optional[str]:
    if "/Lp14" in doc_nr:
        return "Lp14"
    if "/Lm14" in doc_nr:
        return "Lm14"
    if "/P14" in doc_nr:
        return "P14"
    return None


def _stage_exists_for_vote(db_path: str, vote_id: int) -> bool:
    """Check via a fresh connection whether a stage row exists for this vote_id.

    Using a fresh connection avoids SQLite WAL snapshot isolation issues where
    the outer connection opened before append_bill_stage (inner connection)
    committed might not see the newly written row.
    """
    db = get_db(db_path)
    row = db.execute(
        "SELECT id FROM saeima_bill_stages WHERE vote_id=?", (vote_id,)
    ).fetchone()
    db.close()
    return row is not None


def backfill(db_path: str = DB_PATH, dry_run: bool = False) -> dict:
    """Run the backfill. Returns a report dict for caller logging."""
    init_saeima_bills(db_path)

    db = get_db(db_path)
    rows = db.execute(
        """SELECT id, motif, document_nr, vote_date, result, summary, topic
           FROM saeima_votes
           ORDER BY vote_date ASC, id ASC"""
    ).fetchall()
    db.close()

    grouped: dict[str, list] = defaultdict(list)
    skipped_null = 0
    skipped_bad_type = 0
    for v in rows:
        doc_nr = v["document_nr"]
        if not doc_nr:
            # Fallback: extract document_nr from motif (handles P14 votes where
            # the tracker never set document_nr because these are paziņojumi,
            # not bill URLs — they were ingested but never annotated).
            doc_nr = resolve_bill_from_motif(v["motif"] or "")
        if not doc_nr:
            skipped_null += 1
            continue
        bt = _bill_type_from_doc_nr(doc_nr)
        if bt is None:
            skipped_bad_type += 1
            continue
        grouped[doc_nr].append({**dict(v), "document_nr": doc_nr})

    report = {
        "bills_created": 0,
        "votes_with_bill_id": 0,
        "votes_skipped_null_doc_nr": skipped_null,
        "votes_skipped_bad_type": skipped_bad_type,
        "unknown_stages": 0,
        "total_stages_appended": 0,
    }

    for doc_nr, vote_list in grouped.items():
        bill_type = _bill_type_from_doc_nr(doc_nr)
        latest = vote_list[-1]
        title = _extract_title_from_motif(latest["motif"])
        topic = latest["topic"]
        summary = latest["summary"]

        if dry_run:
            report["bills_created"] += 1
            continue

        bid = upsert_bill(
            db_path, doc_nr, title, bill_type,
            topic=topic, summary=summary,
        )
        report["bills_created"] += 1

        # For each vote in this group, append a stage if not already present.
        # Use _stage_exists_for_vote (fresh connection) to avoid WAL snapshot
        # isolation — the outer connection snapshot predates inner commits.
        for v in vote_list:
            if _stage_exists_for_vote(db_path, v["id"]):
                # Already backfilled; ensure bill_id FK is set (idempotent UPDATE)
                db2 = get_db(db_path)
                db2.execute(
                    "UPDATE saeima_votes SET bill_id=? WHERE id=? AND bill_id IS NULL",
                    (bid, v["id"]),
                )
                db2.commit()
                db2.close()
                continue

            stage_name = _reading_from_motif(v["motif"] or "")
            if stage_name == "nezināms":
                report["unknown_stages"] += 1
            append_bill_stage(
                db_path, bid, stage_name, v["result"], v["vote_date"], vote_id=v["id"],
            )
            report["total_stages_appended"] += 1

            # Link vote back to bill
            db3 = get_db(db_path)
            db3.execute(
                "UPDATE saeima_votes SET bill_id=? WHERE id=?",
                (bid, v["id"]),
            )
            db3.commit()
            db3.close()

        report["votes_with_bill_id"] += len(vote_list)

    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="Tikai atskaite; nekādus DB ierakstus neveido")
    args = ap.parse_args()
    report = backfill(dry_run=args.dry_run)
    mode = "izmēģinājums" if args.dry_run else "live"
    print(f"Vēsturisko datu papildināšana ({mode}):")
    for k, v in report.items():
        print(f"  {k}: {v}")
    if report["votes_with_bill_id"] > 0:
        unknown_pct = (report["unknown_stages"] / report["votes_with_bill_id"]) * 100
        print(f"  unknown_stages_pct: {unknown_pct:.1f}%")
        if unknown_pct > 10.0:
            print("  BRĪDINĀJUMS: nezināmas stadijas > 10% — apsveriet darba kārtības atkārtotu parsēšanu (spec § 5.4)")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
