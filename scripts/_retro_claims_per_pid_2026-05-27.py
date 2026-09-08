"""Per-pid retro saeima_vote claim generation — faster than LEFT JOIN approach.

For each tracked politician where iv_count > claim_count, iterate their
unclaimed individual_votes and emit claims. Uses store_claim's idempotency
to skip already-stored claims.

Prints progress every politician + per-row counter.
"""
from __future__ import annotations

import sqlite3
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.db import store_claim  # noqa: E402
from src.saeima.claims import _motif_to_topic, _vote_salience  # noqa: E402
from src.saeima.bills import _parse_vote_datetime, _resolve_vote_url  # noqa: E402

DB_PATH = str(REPO_ROOT / "data" / "atmina.db")


def _build_stance(deputy_vote: str, motif: str, summary: str | None) -> str:
    is_sentinel = bool(summary and summary.startswith("Kopsavilkums nav pieejams"))
    if summary and summary != motif and not is_sentinel:
        prefix = {
            'Par': 'Atbalsta',
            'Pret': 'Iebilst pret',
            'Atturas': 'Atturējās balsojumā par',
            'Nebalsoja': 'Nebalsoja par',
        }.get(deputy_vote, deputy_vote)
        s_lower = summary[0].lower() + summary[1:] if summary else ""
        return f"{prefix}: {s_lower}"
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

    # Identify pids where iv_count > claim_count
    print("Computing per-pid deltas...", flush=True)
    deltas = cur.execute(
        """
        SELECT tp.id, tp.name,
               (SELECT COUNT(*) FROM saeima_individual_votes WHERE politician_id=tp.id) iv_count,
               (SELECT COUNT(*) FROM claims WHERE opponent_id=tp.id AND claim_type='saeima_vote') claim_count
        FROM tracked_politicians tp
        """
    ).fetchall()

    work = [(pid, name, iv_c, cl_c, iv_c - cl_c) for pid, name, iv_c, cl_c in deltas if iv_c > cl_c]
    work.sort(key=lambda x: -x[4])

    total_delta = sum(w[4] for w in work)
    print(f"  {len(work)} pids with iv > claims (total delta: {total_delta})", flush=True)
    for pid, name, iv_c, cl_c, delta in work[:25]:
        print(f"    pid={pid:3d}  {name[:35]:35s}  iv={iv_c:5d}  claims={cl_c:5d}  delta={delta:5d}", flush=True)

    total_created = 0
    total_failed = 0
    start = time.time()

    for pid, name, iv_c, cl_c, delta in work:
        # Fetch iv+v rows for this pid only (small per-pid sets, indexed by politician_id)
        rows = cur.execute(
            """
            SELECT iv.id, iv.deputy_name, iv.vote,
                   v.motif, v.url, v.summary,
                   v.vote_date, v.vote_time,
                   v.total_par, v.total_pret, v.total_atturas, v.total_nebalso
            FROM saeima_individual_votes iv
            JOIN saeima_votes v ON iv.vote_id = v.id
            WHERE iv.politician_id = ?
            """,
            (pid,),
        ).fetchall()

        pid_created = 0
        for (iv_id, deputy_name, deputy_vote, motif, url, summary,
             vote_date, vote_time, total_par, total_pret, total_atturas, total_nebalso) in rows:
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
                store_claim(
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
                pid_created += 1
            except Exception as e:
                total_failed += 1
                if total_failed <= 3:
                    print(f"    FAIL iv_id={iv_id} pid={pid}: {e}", flush=True)
        total_created += pid_created
        elapsed = time.time() - start
        print(f"  pid={pid:3d} {name[:35]:35s} processed {len(rows)} iv rows, attempted {pid_created} claims (total {total_created}, {elapsed:.0f}s)", flush=True)

    print(flush=True)
    print(f"=== Done ===", flush=True)
    print(f"  store_claim attempts: {total_created}", flush=True)
    print(f"  failed: {total_failed}", flush=True)
    print(f"  total elapsed: {time.time()-start:.1f}s", flush=True)
    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
