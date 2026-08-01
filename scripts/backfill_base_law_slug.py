"""Phase 1B-ii Step 0 — populate saeima_bills.base_law_slug retroactively.

Iterē pār bills WHERE base_law_slug IS NULL, izsauc _resolve_base_law_slug
ar title + jaunākā saistītā vote motif konkatenāciju. Idempotents:
re-run = same final state, jo WHERE filter aizsargā jau matched bills.

Usage:
    python scripts/backfill_base_law_slug.py             # production DB
    python scripts/backfill_base_law_slug.py --db path/to/atmina.db
"""

import argparse
import logging
import sys
from pathlib import Path

# Permit running as script: ensure parent dir on sys.path
_PARENT = Path(__file__).resolve().parent.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

from src.db import get_db
from src.saeima import _resolve_base_law_slug, load_laws_index

logger = logging.getLogger(__name__)


def backfill_base_law_slug(
    db_path: str = "data/atmina.db",
    wiki_dir: Path | None = None,
) -> dict:
    """Retroactively populate saeima_bills.base_law_slug.

    Returns {'matched': N, 'unmatched': M, 'coverage_pct': P}.
    - matched/unmatched: this-run counts (bills WHERE base_law_slug IS NULL).
    - coverage_pct: population-level (all bills), stable across idempotent re-runs.
    """
    if wiki_dir is None:
        wiki_dir = _PARENT / "wiki"

    laws_index = load_laws_index(wiki_dir)
    if not laws_index:
        logger.warning("laws_index is empty — wiki/laws/ missing or has no .md files. Aborting.")
        return {"matched": 0, "unmatched": 0, "coverage_pct": 0.0}

    logger.info("Loaded %d laws from index", len(laws_index))

    db = get_db(db_path)
    rows = db.execute("""
        SELECT b.id, b.document_nr, b.title,
               (SELECT motif FROM saeima_votes WHERE bill_id=b.id ORDER BY id DESC LIMIT 1) AS motif
        FROM saeima_bills b
        WHERE b.base_law_slug IS NULL
        ORDER BY b.id
    """).fetchall()

    matched, unmatched = 0, 0
    for r in rows:
        match_text = f"{r['title']} {r['motif'] or ''}"
        slug = _resolve_base_law_slug(match_text, laws_index)
        if slug:
            db.execute("UPDATE saeima_bills SET base_law_slug=? WHERE id=?", (slug, r["id"]))
            matched += 1
        else:
            unmatched += 1
    db.commit()

    # Compute GLOBAL coverage for warning (not per-run)
    total_bills = db.execute("SELECT COUNT(*) FROM saeima_bills").fetchone()[0]
    populated = db.execute(
        "SELECT COUNT(*) FROM saeima_bills WHERE base_law_slug IS NOT NULL"
    ).fetchone()[0]
    db.close()

    global_coverage_pct = (populated / total_bills * 100) if total_bills else 0.0
    result = {
        "matched": matched,
        "unmatched": unmatched,
        "coverage_pct": global_coverage_pct,
    }

    logger.info("backfill_base_law_slug: %s", result)
    if global_coverage_pct < 30 and total_bills > 0:
        logger.warning(
            "Low global coverage (%.1f%%); apsver Phase 1.5 manuālo pārklasifikāciju",
            global_coverage_pct,
        )

    return result


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Backfill saeima_bills.base_law_slug")
    parser.add_argument("--db", default="data/atmina.db", help="Path to SQLite DB")
    args = parser.parse_args()
    result = backfill_base_law_slug(args.db)
    print(
        f"Matched: {result['matched']}, Unmatched: {result['unmatched']}, "
        f"Coverage: {result['coverage_pct']:.1f}%"
    )


if __name__ == "__main__":
    main()
