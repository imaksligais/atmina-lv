"""Clean today's (2026-04-25) commentator-pipeline-derived rows to start fresh
before commentator demotion migration.

DELETES:
- 8 tensions (id 75-82) from political_tensions — all registered today by
  scripts/register_tensions_2026_04_25.py with commentator source_pid
- 8 commentary claims from claims (claim_type='commentary' AND
  date(created_at)='2026-04-25')

KEEPS:
- All historical commentary claims (pre-2026-04-25)
- All historical tensions (id 1-74)
- Today's 16 first-party position claims
- All documents (the underlying source content stays)
- All commentator entries in tracked_politicians (those get migrated by the plan)

Backup is written to data/backups/cleanup_2026-04-25_commentator-prep.json
before any deletion, so this is reversible by re-INSERTing from the JSON.
"""
import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path("data/atmina.db")
BACKUP_DIR = Path("data/backups")
BACKUP_FILE = BACKUP_DIR / "cleanup_2026-04-25_commentator-prep.json"


def main() -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    tension_ids = [75, 76, 77, 78, 79, 80, 81, 82]

    tensions = [dict(r) for r in con.execute(
        f"SELECT * FROM political_tensions WHERE id IN ({','.join('?' * len(tension_ids))})",
        tension_ids,
    ).fetchall()]

    claims = [dict(r) for r in con.execute(
        "SELECT * FROM claims WHERE claim_type='commentary' "
        "AND date(created_at)='2026-04-25'"
    ).fetchall()]

    backup = {
        "exported_at": datetime.now().isoformat(),
        "purpose": "cleanup before commentator demotion migration",
        "tensions": tensions,
        "claims": claims,
    }
    BACKUP_FILE.write_text(
        json.dumps(backup, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    print(f"Backup written to {BACKUP_FILE} ({BACKUP_FILE.stat().st_size / 1024:.1f} KB)")
    print(f"  tensions: {len(tensions)}")
    print(f"  commentary claims: {len(claims)}")

    if not tensions and not claims:
        print("\nNothing to delete.")
        con.close()
        return

    print("\nDeleting...")
    cur = con.cursor()
    cur.execute(
        f"DELETE FROM political_tensions WHERE id IN ({','.join('?' * len(tension_ids))})",
        tension_ids,
    )
    print(f"  political_tensions: {cur.rowcount} rows deleted")

    cur.execute(
        "DELETE FROM claims WHERE claim_type='commentary' "
        "AND date(created_at)='2026-04-25'"
    )
    print(f"  claims: {cur.rowcount} rows deleted")

    con.commit()

    # Verify
    remaining_tensions = con.execute(
        f"SELECT COUNT(*) FROM political_tensions WHERE id IN ({','.join('?' * len(tension_ids))})",
        tension_ids,
    ).fetchone()[0]
    remaining_claims = con.execute(
        "SELECT COUNT(*) FROM claims WHERE claim_type='commentary' "
        "AND date(created_at)='2026-04-25'"
    ).fetchone()[0]
    print(f"\nVerification: {remaining_tensions} target tensions, "
          f"{remaining_claims} today's commentary claims remain "
          f"(expected: 0 each).")

    con.close()


if __name__ == "__main__":
    main()
