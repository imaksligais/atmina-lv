"""Pre-migration audit: print current state of 7 commentators.
Run: python scripts/audit_commentator_state.py
"""
import sqlite3
from pathlib import Path

DB_PATH = Path("data/atmina.db")
COMMENTATOR_IDS = [62, 169, 171, 172, 174, 175, 177]


def main() -> None:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    print("=== tracked_politicians ===")
    rows = con.execute(
        f"SELECT id, name, party, x_handle, relationship_type "
        f"FROM tracked_politicians WHERE id IN ({','.join('?' * 7)})",
        COMMENTATOR_IDS,
    ).fetchall()
    for r in rows:
        print(f"  pid={r['id']:4} {r['name']:30} rel={r['relationship_type']} handle=@{r['x_handle']}")

    print("\n=== social_accounts ===")
    rows = con.execute(
        f"SELECT opponent_id, platform, handle, feed_type, active "
        f"FROM social_accounts WHERE opponent_id IN ({','.join('?' * 7)})",
        COMMENTATOR_IDS,
    ).fetchall()
    for r in rows:
        print(f"  pid={r['opponent_id']:4} {r['platform']:8} @{r['handle']:20} feed={r['feed_type']} active={r['active']}")

    print("\n=== documents w/ commentator as subject (last 30 days) ===")
    cutoff = "datetime('now','-30 day')"
    rows = con.execute(
        f"SELECT dp.politician_id, COUNT(*) as cnt "
        f"FROM document_politicians dp "
        f"JOIN documents d ON d.id = dp.document_id "
        f"WHERE dp.politician_id IN ({','.join('?' * 7)}) AND dp.role='subject' "
        f"AND d.scraped_at >= {cutoff} "
        f"GROUP BY dp.politician_id",
        COMMENTATOR_IDS,
    ).fetchall()
    for r in rows:
        print(f"  pid={r['politician_id']:4}: {r['cnt']} docs as subject")

    print("\n=== claims w/ speaker_id IN commentators (historical) ===")
    rows = con.execute(
        f"SELECT speaker_id, COUNT(*) as cnt FROM claims "
        f"WHERE speaker_id IN ({','.join('?' * 7)}) GROUP BY speaker_id",
        COMMENTATOR_IDS,
    ).fetchall()
    for r in rows:
        print(f"  speaker_id={r['speaker_id']}: {r['cnt']} historical commentary claims")

    print("\n=== tensions w/ source_pid OR target_pid IN commentators ===")
    rows = con.execute(
        f"SELECT source_pid, target_pid, COUNT(*) as cnt FROM political_tensions "
        f"WHERE source_pid IN ({','.join('?' * 7)}) OR target_pid IN ({','.join('?' * 7)}) "
        f"GROUP BY source_pid, target_pid",
        COMMENTATOR_IDS + COMMENTATOR_IDS,
    ).fetchall()
    for r in rows:
        print(f"  {r['source_pid']}->{r['target_pid']}: {r['cnt']}")


if __name__ == "__main__":
    main()
