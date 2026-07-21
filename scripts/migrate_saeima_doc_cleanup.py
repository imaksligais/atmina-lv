"""One-shot idempotent migration: noņem fake "documents" Saeima vote skeletoniem.

Vēsturiski `generate_claims_from_votes()` katram individual_vote radīja sintētisku
documents tabulas rindu (platform='saeima', source_url=titania.saeima.lv...) tikai
tāpēc, ka `store_claim.document_id` nepieļāva NULL. Pēc 2026-04-25 sanācijas:
  - store_claim pieņem document_id=None
  - generate_claims_from_votes neveido sintētisko doc, padod NULL
  - šī migrācija dzēš jau eksistējošos 8985 fake docs un nullē 8876 claim atsauces

Vote provenance pilnībā rekonstruējama no saeima_votes + saeima_individual_votes
caur (claim.opponent_id, claim.source_url, claim.stated_at). Junction
document_politicians fake docs rindas (1:1) arī aiziet.

Operācijas (visas conditional → drīkst palaist atkārtoti):
  1. UPDATE claims SET document_id=NULL WHERE document_id atsaucas uz fake doc
     (kontrolē: claim_type='saeima_vote', citur platform='saeima' nav atļauts)
  2. DELETE FROM document_politicians WHERE document_id IN fake docs
  3. DELETE FROM documents WHERE platform='saeima'

Sanity check: pirms migrācijas verificē, ka katrs platform='saeima' doc ir
ekskluzīvi atsaukts no claim_type='saeima_vote' claims. Ja kāda cita atsauce
atrasta — abort, neizdari NEKO. Aizsardzība pret nezināmu cross-reference.

Usage:
    python -m scripts.migrate_saeima_doc_cleanup
    python -m scripts.migrate_saeima_doc_cleanup --db data/atmina.db
    python -m scripts.migrate_saeima_doc_cleanup --dry-run
"""
from __future__ import annotations

import argparse
import logging
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def _verify_no_foreign_references(db: sqlite3.Connection) -> tuple[bool, str]:
    """Pirms-migrācijas check: vai kāds claim_type != 'saeima_vote' atsaucas uz
    fake doc? Ja jā — neizdari NEKO. Tāpat dokumentu_chunks (vajadzētu būt 0).
    """
    n_foreign_claims = db.execute(
        """SELECT COUNT(*) FROM claims c JOIN documents d ON d.id=c.document_id
           WHERE d.platform='saeima' AND c.claim_type != 'saeima_vote'"""
    ).fetchone()[0]
    if n_foreign_claims > 0:
        return False, f"{n_foreign_claims} non-saeima_vote claims reference saeima fake docs — abort"

    n_chunks = db.execute(
        """SELECT COUNT(*) FROM document_chunks dc JOIN documents d ON d.id=dc.document_id
           WHERE d.platform='saeima'"""
    ).fetchone()[0]
    if n_chunks > 0:
        return False, f"{n_chunks} document_chunks point to saeima fake docs — chunks must be deleted manually first"

    return True, "ok"


def migrate(db_path: str, dry_run: bool = False) -> dict:
    """Run the migration. Returns counts dict."""
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")

    counts = {
        "fake_docs_pre": 0,
        "claims_nulled": 0,
        "junctions_deleted": 0,
        "docs_deleted": 0,
        "fake_docs_post": 0,
        "dry_run": dry_run,
    }

    counts["fake_docs_pre"] = db.execute(
        "SELECT COUNT(*) FROM documents WHERE platform='saeima'"
    ).fetchone()[0]

    if counts["fake_docs_pre"] == 0:
        logger.info("No saeima fake docs found — already clean. No-op.")
        db.close()
        return counts

    ok, msg = _verify_no_foreign_references(db)
    if not ok:
        db.close()
        raise RuntimeError(f"Pre-migration check failed: {msg}")

    if dry_run:
        # Compute what WOULD happen without writing
        counts["claims_nulled"] = db.execute(
            """SELECT COUNT(*) FROM claims c JOIN documents d ON d.id=c.document_id
               WHERE d.platform='saeima'"""
        ).fetchone()[0]
        counts["junctions_deleted"] = db.execute(
            """SELECT COUNT(*) FROM document_politicians dp
               JOIN documents d ON d.id=dp.document_id WHERE d.platform='saeima'"""
        ).fetchone()[0]
        counts["docs_deleted"] = counts["fake_docs_pre"]
        counts["fake_docs_post"] = counts["fake_docs_pre"]  # nothing actually deleted
        db.close()
        return counts

    try:
        with db:  # auto-commit / rollback
            cur = db.execute(
                """UPDATE claims SET document_id=NULL
                   WHERE document_id IN (SELECT id FROM documents WHERE platform='saeima')"""
            )
            counts["claims_nulled"] = cur.rowcount

            cur = db.execute(
                """DELETE FROM document_politicians
                   WHERE document_id IN (SELECT id FROM documents WHERE platform='saeima')"""
            )
            counts["junctions_deleted"] = cur.rowcount

            cur = db.execute("DELETE FROM documents WHERE platform='saeima'")
            counts["docs_deleted"] = cur.rowcount

        counts["fake_docs_post"] = db.execute(
            "SELECT COUNT(*) FROM documents WHERE platform='saeima'"
        ).fetchone()[0]
    finally:
        db.close()

    return counts


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="data/atmina.db", help="DB path")
    ap.add_argument("--dry-run", action="store_true", help="Compute counts without writing")
    ap.add_argument("--no-backup", action="store_true", help="Skip backup (testing only)")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    db_path = Path(args.db)
    if not db_path.exists():
        logger.error("DB not found: %s", db_path)
        return 1

    if not args.dry_run and not args.no_backup:
        ts = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        backup = db_path.parent / f"atmina_backup_pre_saeima_doc_cleanup_{ts}.db"
        logger.info("Backup → %s", backup)
        shutil.copy2(db_path, backup)

    counts = migrate(str(db_path), dry_run=args.dry_run)
    logger.info("Migration counts: %s", counts)

    if not args.dry_run and counts["fake_docs_post"] != 0:
        logger.error("Post-migration verification failed: %d fake docs remain", counts["fake_docs_post"])
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
