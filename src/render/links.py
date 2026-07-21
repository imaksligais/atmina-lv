"""Render saites.html — politician relationship force-graph page.

Pass-through pattern: ``tensions`` is pre-fetched in
``generate_public_site`` and shared with ``render_tensions``
(spriedzes.html).

Sub-page boundary: imports only from ``src.render._common`` and stdlib.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

from src.render._common import (
    CLAIM_TYPE_LABEL,
    PARTY_COLORS,
    _date_sort_key,
    _emit_json_compressed,
    _render_page,
    _slugify,
    _split_summary,
)

logger = logging.getLogger(__name__)


def _emit_saites_json(
    payload_data: dict[str, Any], atmina_dir: Path, basename: str = "saites-data"
) -> Path:
    """Write a saites force-graph detail payload to ``atmina/data/<basename>.json``.

    Two files are emitted by ``render_links``: ``saites-data.json`` (claims +
    a small per-politician vote-count map for the node badges) which loads on
    first node/link detail open, and ``saites-votes.json`` (the heavy normalized
    vote ledger, ~9 MB raw) which loads only when a node's "Balsojumi" section is
    opened. Splitting the bulk off the common detail-open path keeps that fetch
    ~6× lighter. Pre-compressed ``.br``/``.gz`` siblings are served by the same
    htaccess ``*.json`` rewrite. Idempotent. Mirrors ``votes.py:_emit_matrix_json``.
    """
    data_dir = atmina_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    dest = data_dir / f"{basename}.json"
    payload = json.dumps(
        payload_data, ensure_ascii=False, separators=(",", ":"), default=str
    ).encode("utf-8")
    _emit_json_compressed(payload, dest)
    logger.info(
        "Wrote saites sidecar → %s (%d raw, %d br, %d gz)",
        dest,
        dest.stat().st_size,
        (data_dir / f"{basename}.json.br").stat().st_size,
        (data_dir / f"{basename}.json.gz").stat().st_size,
    )
    return dest


def _fetch_graph_data(db: sqlite3.Connection) -> dict[str, Any]:
    """Build force-graph data: nodes (politicians) and links (tensions + shared topics)."""
    # Nodes: any active politician with at least 1 position claim, 1 Saeima vote,
    # or appearance in tensions. Node radius uses `claims` (position count) so
    # rhetorical weight still drives visual prominence — vote-only politicians
    # appear as small peripheral nodes, which is honest signalling.
    pols = db.execute("""
        SELECT tp.id, tp.name, tp.party,
               (SELECT COUNT(*) FROM claims
                WHERE opponent_id = tp.id AND claim_type = 'position') AS claims_count,
               (SELECT COUNT(*) FROM claims
                WHERE opponent_id = tp.id AND claim_type = 'saeima_vote') AS votes_count
        FROM tracked_politicians tp
        WHERE tp.relationship_type NOT IN ('inactive', 'commentator')
        ORDER BY tp.name
    """).fetchall()

    # IDs that appear in tensions
    tension_pids = set()
    tension_rows = db.execute("""
        SELECT source_pid, target_pid, topic, description, tension_type
        FROM political_tensions
    """).fetchall()
    for t in tension_rows:
        tension_pids.add(t["source_pid"])
        tension_pids.add(t["target_pid"])

    # Contradiction counts per politician
    contra_counts: dict[int, int] = {}
    for row in db.execute(
        "SELECT opponent_id, COUNT(*) AS cnt FROM contradictions GROUP BY opponent_id"
    ).fetchall():
        contra_counts[row["opponent_id"]] = row["cnt"]

    nodes = []
    node_ids = set()
    for p in pols:
        if p["claims_count"] > 0 or p["votes_count"] > 0 or p["id"] in tension_pids:
            nodes.append({
                "id": p["id"],
                "name": p["name"],
                "party": p["party"] or "",
                "claims": p["claims_count"],
                "votes": p["votes_count"],
                "slug": _slugify(p["name"]),
                "contradictions": contra_counts.get(p["id"], 0),
            })
            node_ids.add(p["id"])

    links = []

    # Links from tensions
    for t in tension_rows:
        if t["source_pid"] not in node_ids or t["target_pid"] not in node_ids:
            continue
        tt = t["tension_type"] or "spriedze"
        link_type = "support" if tt == "atbalsts" else "tension"
        links.append({
            "source": t["source_pid"],
            "target": t["target_pid"],
            "type": link_type,
            "tension_type": tt,
            "topic": t["topic"] or "",
            "label": t["description"] or "",
        })

    # Links from Saeima vote alignment
    # Only cross-party pairs with >=10 shared votes AND extreme alignment/disagreement.
    # Tikai nodotās balsis (Par/Pret/Atturas) abās savienojuma pusēs —
    # klātbūtnes/reģistrācijas stāvokļi izslēgti, lai sakritība mēra balsojumu,
    # ne klātbūtni. Sk. rankings.py::_vote_alignment_outliers (2026-06-08).
    vote_rows = db.execute("""
        SELECT v1.politician_id AS pid1, v2.politician_id AS pid2,
               SUM(CASE WHEN v1.vote = v2.vote THEN 1 ELSE 0 END) AS agree,
               COUNT(*) AS total,
               p1.party AS party1, p2.party AS party2
        FROM saeima_individual_votes v1
        JOIN saeima_individual_votes v2
          ON v1.vote_id = v2.vote_id AND v1.politician_id < v2.politician_id
        JOIN tracked_politicians p1 ON v1.politician_id = p1.id
        JOIN tracked_politicians p2 ON v2.politician_id = p2.id
        WHERE v1.vote IN ('Par', 'Pret', 'Atturas')
          AND v2.vote IN ('Par', 'Pret', 'Atturas')
        GROUP BY v1.politician_id, v2.politician_id
        HAVING total >= 10
    """).fetchall()
    for v in vote_rows:
        if v["pid1"] not in node_ids or v["pid2"] not in node_ids:
            continue
        pct = round(v["agree"] * 100 / v["total"])
        # Only show the most notable pairs to avoid clutter:
        # - Cross-party high disagreement (<25%) = strong rivals
        # - Same-party rebels (<50%) = internal conflict (rare, interesting)
        # Skip high agreement — it's expected within coalitions
        same_party = (v["party1"] or "") == (v["party2"] or "")
        if same_party and pct >= 50:
            continue
        if not same_party and pct >= 25:
            continue
        links.append({
            "source": v["pid1"],
            "target": v["pid2"],
            "type": "vote",
            "tension_type": "vote",
            "topic": "",
            "label": f"{pct}% sakritība ({v['agree']}/{v['total']})",
            "agree_pct": pct,
            "agree": v["agree"],
            "total": v["total"],
        })

    # Links from shared topics (cross-party only, 3+ shared claims, excluding generic topics)
    # Only niche/specific topics — broad topics produce noise
    NICHE_TOPICS = {
        "airBaltic", "Rail Baltica", "Droni", "Mežsaimniecība",
        "Degviela un enerģētika", "Irāna", "Sabiedriskie mediji",
    }
    # Use position claim counts per politician per topic (not claim pairs)
    # to find politicians who BOTH speak about the same niche topic.
    # Restricted to claim_type='position' so niche-topic links represent
    # shared RHETORIC, not shared vote attendance.
    topic_pols = db.execute("""
        SELECT c.opponent_id AS pid, c.topic, COUNT(*) AS cnt,
               p.party
        FROM claims c
        JOIN tracked_politicians p ON c.opponent_id = p.id
        WHERE p.party IS NOT NULL AND c.topic IS NOT NULL
          AND c.claim_type = 'position'
        GROUP BY c.opponent_id, c.topic
        HAVING cnt >= 3
    """).fetchall()
    # Build {topic: [(pid, party, count), ...]}
    topic_map: dict[str, list] = {}
    for r in topic_pols:
        topic_map.setdefault(r["topic"], []).append(
            (r["pid"], r["party"], r["cnt"])
        )
    # Generate cross-party pairs per niche topic
    shared_rows = []
    for topic, pols_list in topic_map.items():
        if topic not in NICHE_TOPICS:
            continue
        for i in range(len(pols_list)):
            for j in range(i + 1, len(pols_list)):
                p1, party1, cnt1 = pols_list[i]
                p2, party2, cnt2 = pols_list[j]
                if party1 == party2:
                    continue
                shared_rows.append({
                    "pid1": min(p1, p2), "pid2": max(p1, p2),
                    "topic": topic,
                    "cnt": min(cnt1, cnt2),  # strength = weaker side
                })
    shared_rows.sort(key=lambda x: -x["cnt"])
    # Dedupe: keep only the strongest topic per pair, max 20 links total
    MAX_SHARED_LINKS = 20
    seen_pairs: set[tuple[int, int]] = set()
    for s in shared_rows:
        if len(seen_pairs) >= MAX_SHARED_LINKS:
            break
        pair = (s["pid1"], s["pid2"])
        if pair in seen_pairs:
            continue
        if s["pid1"] not in node_ids or s["pid2"] not in node_ids:
            continue
        if s["topic"] not in NICHE_TOPICS:
            continue
        seen_pairs.add(pair)
        links.append({
            "source": s["pid1"],
            "target": s["pid2"],
            "type": "shared_topic",
            "tension_type": "shared_topic",
            "topic": s["topic"],
            "label": f"{s['cnt']} kopīgas pozīcijas par {s['topic']}",
            "weight": s["cnt"],
        })

    return {"nodes": nodes, "links": links}


def render_links(
    env, db: sqlite3.Connection, atmina_dir: Path, tensions: list[dict[str, Any]]
) -> None:
    """Emit ``atmina_dir/saites.html`` (force-graph + per-politician detail panel)."""
    type_counts: dict[str, int] = {}
    for t in tensions:
        tt = t.get("tension_type", "")
        type_counts[tt] = type_counts.get(tt, 0) + 1
    graph_data = _fetch_graph_data(db)
    # Headline count reflects actual graph nodes (politicians with position
    # claims, Saeima votes, or tensions) — not just tension participants.
    politician_count = len(graph_data["nodes"])

    # Position claims grouped by politician (for graph detail panel).
    # Vote rows are excluded — the detail panel shows rhetorical stances,
    # not procedural votes.
    claims_rows = db.execute("""
        SELECT c.opponent_id, c.topic, c.stance, c.confidence, c.salience,
               c.source_url, c.stated_at
        FROM claims c
        WHERE c.claim_type = 'position'
        ORDER BY c.stated_at DESC
    """).fetchall()
    claims_by_pid: dict[int, list[dict]] = {}
    for r in claims_rows:
        pid = r["opponent_id"]
        claims_by_pid.setdefault(pid, []).append({
            "topic": r["topic"],
            "stance": r["stance"],
            "confidence": r["confidence"],
            "salience": r["salience"],
            "source_url": r["source_url"],
            "date": (r["stated_at"] or "")[:10],
        })
    for pid in claims_by_pid:
        claims_by_pid[pid].sort(key=lambda c: _date_sort_key(c.get("date") or ""), reverse=True)
    # Convert int keys to strings for consistent JS access
    claims_by_pid = {str(k): v for k, v in claims_by_pid.items()}

    # Contradictions grouped by politician
    contra_rows = db.execute("""
        SELECT ct.opponent_id, ct.topic, ct.summary, ct.severity, ct.salience,
               ct.detected_at,
               c1.stance AS old_stance, c2.stance AS new_stance,
               c1.source_url AS old_url, c2.source_url AS new_url,
               c1.stated_at AS old_stated, c2.stated_at AS new_stated,
               c1.claim_type AS old_claim_type, c2.claim_type AS new_claim_type
        FROM contradictions ct
        LEFT JOIN claims c1 ON ct.claim_old_id = c1.id
        LEFT JOIN claims c2 ON ct.claim_new_id = c2.id
        ORDER BY ct.detected_at DESC
    """).fetchall()
    contras_by_pid: dict[int, list[dict]] = {}
    for r in contra_rows:
        pid = r["opponent_id"]
        # Swap to chronological order — same policy as _enrich_contradiction.
        old_s = r["old_stance"]
        new_s = r["new_stance"]
        old_u = r["old_url"]
        new_u = r["new_url"]
        old_ct = r["old_claim_type"] or "position"
        new_ct = r["new_claim_type"] or "position"
        old_stated = r["old_stated"] or ""
        new_stated = r["new_stated"] or ""
        if old_stated and new_stated and old_stated > new_stated:
            old_s, new_s = new_s, old_s
            old_u, new_u = new_u, old_u
            old_ct, new_ct = new_ct, old_ct
            old_stated, new_stated = new_stated, old_stated
        if old_ct == new_ct:
            old_label, new_label = "Iepriekš", "Pašlaik"
        else:
            old_label = CLAIM_TYPE_LABEL.get(old_ct, "Iepriekš")
            new_label = CLAIM_TYPE_LABEL.get(new_ct, "Pašlaik")
        clean_summary, context_note = _split_summary(r["summary"])
        contras_by_pid.setdefault(pid, []).append({
            "topic": r["topic"],
            "summary": clean_summary,
            "context_note": context_note,
            "severity": r["severity"],
            "salience": r["salience"],
            "date": (r["detected_at"] or "")[:10],
            "old_stance": old_s,
            "new_stance": new_s,
            "old_url": old_u,
            "new_url": new_u,
            "old_label": old_label,
            "new_label": new_label,
        })
    contras_by_pid = {str(k): v for k, v in contras_by_pid.items()}

    # Saeima votes for graph detail panel "Balsojumi" tab.
    # Normalized payload to avoid duplicating motif/topic/url for every deputy:
    #   votes_meta  = list of unique vote events, newest-first
    #   votes_by_pid = {pid: [[vote_id_index, "Par"|"Pret"|...], ...]}
    # Client looks up metadata by index. Cuts JSON size ~10x.
    vote_meta_rows = db.execute("""
        SELECT id, motif, vote_date, topic, url
        FROM saeima_votes
        ORDER BY vote_date DESC, id DESC
    """).fetchall()
    vote_idx_by_id: dict[int, int] = {}
    votes_meta: list[dict] = []
    for i, r in enumerate(vote_meta_rows):
        vote_idx_by_id[r["id"]] = i
        votes_meta.append({
            "id": r["id"],
            "motif": r["motif"] or "",
            "topic": r["topic"] or "",
            "date": r["vote_date"] or "",
            "url": r["url"] or "",
        })
    individual_rows = db.execute("""
        SELECT siv.politician_id, siv.vote_id, siv.vote
        FROM saeima_individual_votes siv
        JOIN saeima_votes sv ON siv.vote_id = sv.id
        ORDER BY sv.vote_date DESC, sv.id DESC
    """).fetchall()
    votes_by_pid: dict[int, list] = {}
    for r in individual_rows:
        idx = vote_idx_by_id.get(r["vote_id"])
        if idx is None:
            continue
        votes_by_pid.setdefault(r["politician_id"], []).append([idx, r["vote"] or ""])
    votes_by_pid = {str(k): v for k, v in votes_by_pid.items()}

    # Split the detail-panel payload across two lazy sidecars:
    #   saites-data.json  = claims (~1 MB) + a tiny {pid: vote_count} map, loaded
    #                       on first node/link detail open (drives the badges).
    #   saites-votes.json = the heavy normalized vote ledger (~9 MB raw), loaded
    #                       only when a node's "Balsojumi" section is opened.
    # The common detail-open path no longer pulls the vote bulk. tensionsData +
    # contrasByPid stay inline (graph paint + small).
    votes_count = {pid: len(pairs) for pid, pairs in votes_by_pid.items()}
    _emit_saites_json(
        {"claimsByPid": claims_by_pid, "votesCount": votes_count}, atmina_dir
    )
    _emit_saites_json(
        {"meta": votes_meta, "byPid": votes_by_pid}, atmina_dir, basename="saites-votes"
    )

    saites_metrics = {
        "total": len(tensions),
        "politicians": politician_count,
        "attacks": type_counts.get("uzbrukums", 0),
    }
    tension_parties = sorted(set(
        [t["source_party"] for t in tensions if t.get("source_party")] +
        [t["target_party"] for t in tensions if t.get("target_party")]
    ))
    tension_types = sorted(set(t["tension_type"] for t in tensions if t.get("tension_type")))
    spriedze_persons = sorted(set(
        [t["source_name"] for t in tensions if t.get("source_name")] +
        [t["target_name"] for t in tensions if t.get("target_name")]
    ))
    # Viens apvienots datu bloks lapai — sav1.js to nolasa no
    # <script type="application/json" id="saites-data">. Grafa zīmēšanas dati
    # (graph) + detaļu paneļa dati (tensions/contrasByPid) + partiju krāsas
    # (partyColors) vienā vietā; renderēts ar `| tojson | safe_json` (deterministiski baiti).
    saites_data = {
        "graph": graph_data,
        "tensions": tensions,
        "contrasByPid": contras_by_pid,
        "partyColors": PARTY_COLORS,
    }
    _render_page(env, "saites.html.j2", atmina_dir / "saites.html", {
        "tensions": tensions,
        "saites_data": saites_data,
        "parties": tension_parties,
        "tension_types": tension_types,
        "persons": spriedze_persons,
        "politician_count": politician_count,
        "type_counts": type_counts,
        "metrics": saites_metrics,
    })
