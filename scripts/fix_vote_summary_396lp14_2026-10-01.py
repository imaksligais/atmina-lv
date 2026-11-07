"""Labo 396/Lp14 (votes 4917, 5297) kopsavilkumu: degviela NAV starp paaugstinātajām likmēm.

likumi.lv 348551: grozījumi autotransporta degvielas likmes nemainīja (jauna likme
tikai naftas produktiem brīvostās). Kopsavilkums «… alkoholam, tabakai, e-cigarešu
šķidrumiem un degvielai» nonāca katrā `saeima_vote` stancē un radīja viltus
retorika↔balsojums kandidātus (BACKLOG § Atliktais 62, verdikts D6 2026-10-01).
Mainās tikai uzskaitījums; `topic` nemainās, `saeima_vote` netiek embedēti.
Rollback: data/rollback_vote_summary_396lp14_2026-10-01.sql
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.db import get_db  # noqa: E402

VOTES = (4917, 5297)
OLD = "alkoholam, tabakai, e-cigarešu šķidrumiem un degvielai"
NEW = "alkoholam, tabakai un e-cigarešu šķidrumiem"


def main() -> int:
    apply = "--apply" in sys.argv
    db = get_db(None)
    q = ",".join("?" * len(VOTES))
    n_sum = db.execute(f"SELECT COUNT(*) FROM saeima_votes WHERE id IN ({q}) AND summary LIKE ?",
                       (*VOTES, f"%{OLD}%")).fetchone()[0]
    n_cl = db.execute(
        f"SELECT COUNT(*) FROM claims WHERE claim_type='saeima_vote' AND stance LIKE ? "
        f"AND source_url IN (SELECT url FROM saeima_votes WHERE id IN ({q}))",
        (f"%{OLD}%", *VOTES)).fetchone()[0]
    print(f"summaries {n_sum}/2, claims {n_cl}")
    if apply:
        db.execute(f"UPDATE saeima_votes SET summary=replace(summary, ?, ?) WHERE id IN ({q})",
                   (OLD, NEW, *VOTES))
        cur = db.execute(
            f"UPDATE claims SET stance=replace(stance, ?, ?) WHERE claim_type='saeima_vote' "
            f"AND stance LIKE ? AND source_url IN (SELECT url FROM saeima_votes WHERE id IN ({q}))",
            (OLD, NEW, f"%{OLD}%", *VOTES))
        db.commit()
        print(f"applied: claims {cur.rowcount} (intended {n_cl})")
    db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
