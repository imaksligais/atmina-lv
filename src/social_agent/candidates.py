"""Candidate selection + interest score ranking."""
from __future__ import annotations

import json
from contextlib import closing
from datetime import datetime

from src.db import get_db, now_lv_dt

SEVERITY_MAP = {
    "critical": 1.0,
    "major": 0.7,
    "minor": 0.4,
    "none": 0.0,
}
DEFAULT_SEVERITY_NORM = 0.6  # non-pretrunas pillars (None)


def interest_score(
    salience: float,
    severity: str | None,
    age_hours: float,
    candidate_topics: set[str],
    recent_topics: set[str],
) -> float:
    """Compute interest score ∈ [0, 1] for ranking draft candidates.

    score = 0.3*salience + 0.3*severity_norm + 0.2*freshness + 0.2*novelty
    """
    salience_c = max(0.0, min(1.0, salience))
    if severity is None:
        severity_norm = DEFAULT_SEVERITY_NORM
    else:
        severity_norm = SEVERITY_MAP.get(severity.lower(), DEFAULT_SEVERITY_NORM)

    freshness = max(0.0, 1.0 - (age_hours / 168.0))

    union = candidate_topics | recent_topics
    if not union:
        novelty = 1.0
    else:
        intersection = candidate_topics & recent_topics
        jaccard = len(intersection) / len(union)
        novelty = 1.0 - jaccard

    return 0.3 * salience_c + 0.3 * severity_norm + 0.2 * freshness + 0.2 * novelty


def fetch_pretrunas_candidates(db_path: str | None = None) -> list[dict]:
    """Return unposted contradictions joined to both claims + politician name.

    Excludes contradictions whose `id` already appears in a posted
    social_drafts row (`source_data_json->>'contradiction_id'`).
    """
    with closing(get_db(db_path)) as db:
        rows = db.execute(
            """
            SELECT
                c.id            AS contradiction_id,
                c.opponent_id   AS politician_id,
                p.name          AS politician_name,
                p.party         AS party,
                c.topic         AS topic,
                c.summary       AS summary,
                c.severity      AS severity,
                c.salience      AS salience,
                c.detected_at   AS detected_at,
                co.quote        AS old_quote,
                co.stance       AS old_stance,
                co.stated_at    AS old_stated_at,
                co.source_url   AS old_source_url,
                co.claim_type   AS old_claim_type,
                cn.quote        AS new_quote,
                cn.stance       AS new_stance,
                cn.stated_at    AS new_stated_at,
                cn.source_url   AS new_source_url,
                cn.claim_type   AS new_claim_type
            FROM contradictions c
            LEFT JOIN tracked_politicians p ON p.id = c.opponent_id
            LEFT JOIN claims co ON co.id = c.claim_old_id
            LEFT JOIN claims cn ON cn.id = c.claim_new_id
            WHERE c.id NOT IN (
                SELECT CAST(json_extract(source_data_json, '$.contradiction_id') AS INTEGER)
                FROM social_drafts
                WHERE pillar = 'pretrunas' AND status = 'posted'
            )
            ORDER BY c.detected_at DESC
            """
        ).fetchall()
    out: list[dict] = []
    for r in rows:
        d = dict(r)
        # Chronological swap — mirrors src.generate._enrich_contradiction so that
        # drafters and OG images see the same old=earlier / new=later ordering.
        old_s = d.get("old_stated_at") or ""
        new_s = d.get("new_stated_at") or ""
        if old_s and new_s and old_s > new_s:
            for k in ("quote", "stance", "stated_at", "source_url", "claim_type"):
                ok, nk = f"old_{k}", f"new_{k}"
                d[ok], d[nk] = d.get(nk), d.get(ok)
        out.append(d)
    return out


def fetch_stats_candidate(db_path: str | None = None, now_iso: str | None = None) -> dict | None:
    """Return weekly leaderboard payload, or None if this ISO week was already posted.

    Leaderboard counts `position` claims in the past 7 days, grouped by politician.
    Returns at most top 10.
    """
    if now_iso is None:
        now = now_lv_dt()
    else:
        now = datetime.fromisoformat(now_iso.replace("Z", ""))

    iso_year, iso_week, _ = now.isocalendar()
    iso_week_str = f"{iso_year}-W{iso_week:02d}"

    with closing(get_db(db_path)) as db:
        # Skip if already posted for this week
        already = db.execute(
            """
            SELECT 1 FROM social_drafts
            WHERE pillar = 'stats'
              AND status = 'posted'
              AND json_extract(source_data_json, '$.iso_week') = ?
            LIMIT 1
            """,
            (iso_week_str,),
        ).fetchone()
        if already:
            return None

        rows = db.execute(
            """
            SELECT p.id, p.name, p.party, COUNT(c.id) AS n
            FROM claims c
            JOIN tracked_politicians p ON p.id = c.opponent_id
            WHERE c.claim_type = 'position'
              AND c.stated_at >= datetime(?, '-7 days')
              AND p.relationship_type NOT IN (
                  'journalist', 'influencer', 'neutral', 'inactive', 'organization'
              )
            GROUP BY p.id, p.name, p.party
            HAVING n > 0
            ORDER BY n DESC, p.name ASC
            LIMIT 10
            """,
            (now.strftime("%Y-%m-%d %H:%M:%S"),),
        ).fetchall()

    if not rows:
        return None

    return {
        "iso_week": iso_week_str,
        "leaderboard": [
            {"politician_id": r["id"], "name": r["name"], "party": r["party"], "count": r["n"]}
            for r in rows
        ],
    }


def fetch_highlights_candidates(db_path: str | None = None, lookback_days: int = 7) -> list[dict]:
    """Return list of highlight candidates from recent oppo_briefs.strongest_attacks
    and political_tensions.

    Each row is a dict with `kind` ∈ {'attack', 'tension'} + pillar-specific fields.
    Skips rows already represented in approved/posted social_drafts.
    """
    attacks: list[dict] = []
    tension_rows: list[dict] = []
    posted_keys: set[tuple[str, int, int | None]] = set()

    with closing(get_db(db_path)) as db:
        attacks_raw = db.execute(
            """
            SELECT ob.id AS brief_id, ob.opponent_id, p.name AS politician_name,
                   p.party, ob.strongest_attacks, ob.created_at
            FROM oppo_briefs ob
            JOIN tracked_politicians p ON p.id = ob.opponent_id
            WHERE ob.strongest_attacks IS NOT NULL
              AND ob.created_at >= datetime('now', ?)
            """,
            (f"-{lookback_days} days",),
        ).fetchall()

        for r in attacks_raw:
            try:
                items = json.loads(r["strongest_attacks"]) or []
            except (TypeError, json.JSONDecodeError):
                continue
            for idx, item in enumerate(items):
                if not isinstance(item, dict) or not item.get("text"):
                    continue
                attacks.append({
                    "kind": "attack",
                    "brief_id": r["brief_id"],
                    "attack_index": idx,
                    "politician_id": r["opponent_id"],
                    "politician_name": r["politician_name"],
                    "party": r["party"],
                    "text": item["text"],
                    "created_at": r["created_at"],
                })

        tensions = db.execute(
            """
            SELECT t.id AS tension_id, t.source_pid, t.target_pid,
                   ps.name AS source_name, pt.name AS target_name,
                   t.topic, t.description, t.tension_type,
                   t.source_url, t.created_at
            FROM political_tensions t
            LEFT JOIN tracked_politicians ps ON ps.id = t.source_pid
            LEFT JOIN tracked_politicians pt ON pt.id = t.target_pid
            WHERE t.created_at >= datetime('now', ?)
            """,
            (f"-{lookback_days} days",),
        ).fetchall()
        tension_rows = [
            {
                "kind": "tension",
                "tension_id": r["tension_id"],
                "source_name": r["source_name"],
                "target_name": r["target_name"],
                "topic": r["topic"],
                "description": r["description"],
                "tension_type": r["tension_type"],
                "source_url": r["source_url"],
                "created_at": r["created_at"],
            }
            for r in tensions
        ]

        posted = db.execute(
            """
            SELECT source_data_json FROM social_drafts
            WHERE pillar = 'highlights' AND status = 'posted'
            """
        ).fetchall()
        for p in posted:
            try:
                sd = json.loads(p["source_data_json"])
            except (TypeError, json.JSONDecodeError):
                continue
            if sd.get("kind") == "attack":
                posted_keys.add(("attack", sd.get("brief_id"), sd.get("attack_index")))
            elif sd.get("kind") == "tension":
                posted_keys.add(("tension", sd.get("tension_id"), None))

    out: list[dict] = []
    for a in attacks:
        if ("attack", a["brief_id"], a["attack_index"]) in posted_keys:
            continue
        out.append(a)
    for t in tension_rows:
        if ("tension", t["tension_id"], None) in posted_keys:
            continue
        out.append(t)
    return out


def select_top_n(pool: list[dict], n: int = 3, per_pillar_cap: int = 2) -> list[dict]:
    """Pick top-N candidates by score with a hard per-pillar cap.

    Each pool entry must have keys 'pillar' and 'score'. Ties broken by input order.
    """
    sorted_pool = sorted(
        enumerate(pool),
        key=lambda pair: (-pair[1]["score"], pair[0]),
    )
    picked: list[dict] = []
    pillar_counts: dict[str, int] = {}
    for _, entry in sorted_pool:
        if len(picked) >= n:
            break
        count = pillar_counts.get(entry["pillar"], 0)
        if count >= per_pillar_cap:
            continue
        picked.append(entry)
        pillar_counts[entry["pillar"]] = count + 1
    return picked
