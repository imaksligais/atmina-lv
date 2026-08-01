"""Generate retroactive saeima_vote claims for the 9 historic deputies (pid 205-213).

The historic deputies were added 2026-05-27 — at backfill time their individual
vote rows had politician_id=NULL, so generate_claims_from_votes() skipped them.
After the matcher backfill attributed 2369 rows, we now need to walk those
attributions and emit the saeima_vote claims that would have been emitted at
ingest time.

Idempotent: store_claim's (opponent_id, source_url, topic) UNIQUE check skips
re-runs.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.db import store_claim, log_action  # noqa: E402
from src.saeima.claims import _motif_to_topic, _vote_salience  # noqa: E402
from src.saeima.bills import _parse_vote_datetime, _resolve_vote_url  # noqa: E402

DB_PATH = str(REPO_ROOT / "data" / "atmina.db")
NEW_PIDS = list(range(205, 214))  # 205..213


def _build_stance(deputy_vote: str, motif: str, summary: str | None) -> str:
    """Mirror src.saeima.votes.generate_claims_from_votes stance logic."""
    is_sentinel = bool(summary and summary.startswith("Kopsavilkums nav pieejams"))
    if summary and summary != motif and not is_sentinel:
        prefix = {
            'Par': 'Atbalsta',
            'Pret': 'Iebilst pret',
            'Atturas': 'Atturējās balsojumā par',
            'Nebalsoja': 'Nebalsoja par',
        }.get(deputy_vote, deputy_vote)
        summary_lower = summary[0].lower() + summary[1:] if summary else ""
        return f"{prefix}: {summary_lower}"
    vote_lv = {
        'Par': 'Balsoja PAR',
        'Pret': 'Balsoja PRET',
        'Atturas': 'ATTURĒJĀS',
        'Nebalsoja': 'NEBALSOJA',
    }
    return f"{vote_lv.get(deputy_vote, deputy_vote)}: {motif}"


def main() -> int:
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()

    placeholders = ",".join("?" * len(NEW_PIDS))
    rows = cur.execute(
        f"""
        SELECT iv.id, iv.politician_id, iv.deputy_name, iv.vote,
               v.id AS vote_db_id, v.motif, v.url, v.summary,
               v.vote_date, v.vote_time, v.total_par, v.total_pret,
               v.total_atturas, v.total_nebalso
        FROM saeima_individual_votes iv
        JOIN saeima_votes v ON iv.vote_id = v.id
        WHERE iv.politician_id IN ({placeholders})
        """,
        NEW_PIDS,
    ).fetchall()

    print(f"=== Retro claim generation for pid 205-213 ===")
    print(f"  candidate rows: {len(rows)}")

    created = 0
    existing = 0
    failed = 0
    by_pid: dict[int, int] = {}
    for r in rows:
        (iv_id, pid, deputy_name, deputy_vote, vote_db_id, motif, url,
         summary, vote_date, vote_time, total_par, total_pret,
         total_atturas, total_nebalso) = r

        topic = _motif_to_topic(motif or "")
        salience = _vote_salience(motif or "")
        full_url = _resolve_vote_url(url)
        stance = _build_stance(deputy_vote, motif or "", summary)
        reasoning = (
            f"Saeimas balsojums {vote_date}: {deputy_name} balsoja {deputy_vote}. "
            f"Kopējais rezultāts: par {total_par}, pret {total_pret}, "
            f"atturas {total_atturas}."
        )

        try:
            claim_id = store_claim(
                opponent_id=pid,
                document_id=None,
                topic=topic,
                stance=stance,
                quote=None,
                confidence=1.0,
                reasoning=reasoning,
                salience=salience,
                source_url=full_url,
                stated_at=_parse_vote_datetime(vote_date, vote_time),
                claim_type="saeima_vote",
                db_path=DB_PATH,
            )
        except Exception as e:
            failed += 1
            print(f"  FAIL iv_id={iv_id} pid={pid}: {e}")
            continue

        # store_claim is idempotent on (opponent_id, source_url, topic);
        # we can't easily tell create vs reuse without a separate select,
        # so tally by-pid totals instead.
        created += 1
        by_pid[pid] = by_pid.get(pid, 0) + 1

    db.close()

    print()
    print(f"=== Done ===")
    print(f"  store_claim calls: {created}")
    print(f"  failed: {failed}")
    print(f"  per-pid counts:")
    for pid in sorted(by_pid):
        print(f"    pid={pid}: {by_pid[pid]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
