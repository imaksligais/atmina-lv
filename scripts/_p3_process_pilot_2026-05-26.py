"""P3 Phase 1 pilot processor — read manifest, run process_vote_snapshot for each.

Manifest format: list of {"idx": int, "url": str, "snapshot": str}
For each entry, reads the Playwright accessibility snapshot file and runs
process_vote_snapshot() with sentinel summary for historic backfill.

Sentinel: 'Kopsavilkums nav pieejams — historic backfill 2026-05-26'
  - This is the explicit-signal value per @saeima-tracker prompt Step 3.B.
  - Bill summaries can be filled lazily later when contradiction hunting
    surfaces a particular vote and we have reason to read the bill text.

Skips entries whose snapshot file does not exist (in case Playwright run
was partial).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.saeima import init_saeima_tables, process_vote_snapshot  # noqa: E402

MANIFEST = REPO_ROOT / ".playwright-mcp" / "p3_pilot" / "manifest.json"
DB_PATH = str(REPO_ROOT / "data" / "atmina.db")
SENTINEL_SUMMARY = "Kopsavilkums nav pieejams — historic backfill 2026-05-26"

# Match document_nr in motif like "(1286/Lp14)" / "(976/Lm14)" / "(123/P14)"
_DOC_NR_RE = re.compile(r"\((\d+/(?:Lp14|Lm14|P14))\)")


def _extract_doc_nr(motif: str) -> str | None:
    if not motif:
        return None
    m = _DOC_NR_RE.search(motif)
    return m.group(1) if m else None


def _is_bill_type(motif: str) -> bool:
    return bool(re.search(r"\(\d+/L[pm]14\)", motif or ""))


def main() -> int:
    init_saeima_tables(DB_PATH)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    processed = 0
    skipped_missing = 0
    skipped_existing = 0
    failed = 0
    total_individual = 0
    total_matched = 0
    total_claims = 0
    by_result: dict[str, int] = {}

    for entry in manifest:
        snap = REPO_ROOT / entry["snapshot"]
        if not snap.exists():
            skipped_missing += 1
            print(f"  SKIP idx={entry['idx']}: snapshot missing — {snap}")
            continue

        text = snap.read_text(encoding="utf-8")

        # Quick pre-parse to extract motif so we can decide summary/doc_nr
        motif_match = re.search(
            r'Balsošanas motīvs:\s*(.+)"\s*$',
            text,
            re.MULTILINE,
        )
        if not motif_match:
            motif_match = re.search(
                r'Balsošanas motīvs:\s*(.+?)(?:\n|$)',
                text,
            )
        motif = motif_match.group(1).replace('\\"', '"').strip() if motif_match else ""
        doc_nr = _extract_doc_nr(motif)
        is_bill = _is_bill_type(motif)
        summary = SENTINEL_SUMMARY if is_bill else None

        try:
            result = process_vote_snapshot(
                snapshot_text=text,
                vote_url=entry["url"],
                summary=summary,
                document_url=None,  # backfill — bill page URL filled lazily later
                document_nr=doc_nr,
                db_path=DB_PATH,
            )
        except Exception as e:
            failed += 1
            print(f"  FAIL idx={entry['idx']}  url={entry['url']}  err={e}")
            continue

        # process_vote_snapshot is idempotent via saeima_votes.url UNIQUE.
        # We can't tell here whether it created or reused; the per-row counter
        # below uses the (current) totals.
        total_individual += result["total_deputies"]
        total_matched += len(result["matched_politicians"])
        total_claims += len(result["claim_ids"])
        by_result[result.get("date") or "?"] = result["motif"][:60]
        processed += 1

        marker = "BILL" if is_bill else "proc"
        print(
            f"  OK idx={entry['idx']:02d}  {marker}  date={result['date']}  "
            f"vote_db_id={result['vote_db_id']}  totals={result['totals']}  "
            f"matched={len(result['matched_politicians'])}/{result['total_deputies']}  "
            f"claims={len(result['claim_ids'])}  motif={(result['motif'] or '')[:60]}"
        )

    print()
    print("=== Pilot summary ===")
    print(f"  processed: {processed}")
    print(f"  skipped_missing_snapshot: {skipped_missing}")
    print(f"  skipped_existing_dedup: {skipped_existing}")
    print(f"  failed: {failed}")
    print(f"  total individual_votes (sum): {total_individual}")
    print(f"  total matched politicians (sum): {total_matched}")
    print(f"  total claims generated (sum): {total_claims}")
    if total_individual:
        match_rate = 100.0 * total_matched / total_individual
        print(f"  match rate: {match_rate:.1f}%")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
