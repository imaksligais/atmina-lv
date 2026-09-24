"""Profile tab builders for the per-politician page ("Pārskats" + "Saites").

Phase 5.6 of docs/plans/2026-09-05-strukturas-tirisanas-plans.md — a pure
move of the two tab-builder clusters out of ``src.render.politicians``
(former L55-57, L215-401 and L462-583). No behaviour change;
``src.render.politicians`` re-imports every name below, so the historical
paths ``from src.render.politicians import _build_parskats_data`` /
``_fetch_saites_for_profile`` / ``PARSKATS_*`` keep resolving
(tests/test_render_politicians_parskats.py, tests/test_render_saites.py).

Both builders are consumed only by ``_fetch_politician_detail``. Imports
flow from ``src.render._common`` (leaf) and ``src.db`` only — never a peer
page module, so the partial-init contract in ``src/render/__init__.py``
holds.
"""

from __future__ import annotations

import math
import sqlite3
from datetime import date, timedelta
from typing import Any, Optional

from src.db import now_lv_dt
from src.render._common import (
    PARTY_COLORS,
    _slugify,
    vote_alignment_data,
)


# Pārskats cilnes signāla blokus regulējošās konstantes — spec
# docs/superpowers/specs/2026-05-14-profila-parskats-design.md § 5.2.
# Empīriski kalibrētas pret 2026-05-14 DB: pretrunu mediāns confirmed=1 ir
# 0.55 (12/17 ≥ 0.5); tēmu count ≥ 3 / 180d aptver 40% profilus (69 / 174).
PARSKATS_CONTRADICTION_SALIENCE_MIN = 0.5
PARSKATS_TOPIC_COUNT_MIN = 3
PARSKATS_TOPIC_WINDOW_DAYS = 180


# ── Pārskats helpers ────────────────────────────────────────────────


def _format_relative_time_lv(date_str: str, today: date) -> str:
    """Convert ``YYYY-MM-DD`` (or longer ISO string) to a Latvian relative
    time phrase: ``šodien``, ``vakar``, ``pirms N dienām``, ``pirms N
    nedēļām``, ``pirms mēneša``, ``pirms N mēnešiem``, ``pirms gada``,
    ``pirms N gadiem``.

    Returns empty string for unparseable input. Used for Pārskats Bloks A
    timestamp display.
    """
    s = (date_str or "")[:10]
    if not s or len(s) != 10:
        return ""
    try:
        d = date.fromisoformat(s)
    except ValueError:
        return ""
    days = (today - d).days
    if days < 0:
        return ""
    if days == 0:
        return "šodien"
    if days == 1:
        return "vakar"
    if days < 7:
        return f"pirms {days} dienām"
    if days < 30:
        weeks = days // 7
        if weeks == 1:
            return "pirms nedēļas"
        return f"pirms {weeks} nedēļām"
    if days < 365:
        months = days // 30
        if months == 1:
            return "pirms mēneša"
        return f"pirms {months} mēnešiem"
    years = days // 365
    if years == 1:
        return "pirms gada"
    return f"pirms {years} gadiem"


def _latest_activity_block(
    db: sqlite3.Connection,
    pid: int,
    positions: list[dict[str, Any]],
    today: date,
) -> Optional[dict[str, Any]]:
    """Compose Bloks A — pēdējā aktivitāte (jaunākā pozīcija vai balsojums).

    Picks whichever is newer between latest position (`positions[0]`,
    already sorted DESC by stated_at) and the most recent Saeima vote.
    Returns ``None`` if politician has no claims and no votes.
    """
    pos_date = ""
    latest_pos = positions[0] if positions else None
    if latest_pos:
        pos_date = (latest_pos.get("stated_at") or "")[:10]

    vote_row = db.execute("""
        SELECT sv.vote_date, sv.topic, sv.motif, sv.url, siv.vote
        FROM saeima_individual_votes siv
        JOIN saeima_votes sv ON siv.vote_id = sv.id
        WHERE siv.politician_id = ?
        ORDER BY sv.vote_date DESC, sv.vote_time DESC
        LIMIT 1
    """, (pid,)).fetchone()
    vote_date = ""
    if vote_row:
        vote_date = (vote_row["vote_date"] or "")[:10]

    if pos_date and (not vote_date or pos_date >= vote_date):
        return {
            "type": "position",
            "date": pos_date,
            "relative": _format_relative_time_lv(pos_date, today),
            "topic": latest_pos.get("topic") or "",
            "content": (latest_pos.get("stance") or "")[:200],
            "source_url": latest_pos.get("source_url") or "",
        }
    if vote_date:
        return {
            "type": "vote",
            "date": vote_date,
            "relative": _format_relative_time_lv(vote_date, today),
            "topic": vote_row["topic"] or "",
            "content": (vote_row["motif"] or "")[:200],
            "vote": vote_row["vote"] or "",
            "source_url": vote_row["url"] or "",
        }
    return None


def _top_contradiction_block(
    contradictions: list[dict[str, Any]],
) -> Optional[dict[str, Any]]:
    """Compose Bloks B — ievērojamākā pretruna.

    Filters to ``confirmed=1`` rows with ``salience >= 0.5`` and picks
    the one with highest salience (ties broken by detected_at DESC).
    Returns ``None`` if no qualifying row exists.
    """
    qualifying = [
        c for c in contradictions
        if c.get("confirmed") == 1
        and c.get("salience") is not None
        and c["salience"] >= PARSKATS_CONTRADICTION_SALIENCE_MIN
    ]
    if not qualifying:
        return None
    qualifying.sort(
        key=lambda c: (c["salience"], c.get("detected_at") or ""),
        reverse=True,
    )
    top = qualifying[0]
    return {
        "id": top["id"],
        "topic": top.get("topic") or "",
        "summary": (top.get("summary") or "")[:240],
        "severity": top.get("severity") or "",
        "salience": top["salience"],
        "delta_days": top.get("delta_days"),
    }


def _dominant_topics_block(
    positions: list[dict[str, Any]],
    today: date,
) -> list[dict[str, Any]]:
    """Compose Bloks C — top 3 dominējošās tēmas pēdējos 180 dienās.

    Pure Python — operates on the already-fetched ``positions`` list (no
    extra DB roundtrip). Returns ``[]`` if no topic clears the count
    threshold.
    """
    cutoff = (today - timedelta(days=PARSKATS_TOPIC_WINDOW_DAYS)).isoformat()
    counts: dict[str, int] = {}
    for p in positions:
        s = (p.get("stated_at") or "")[:10]
        if not s or s < cutoff:
            continue
        topic = (p.get("topic") or "").strip()
        if not topic:
            continue
        counts[topic] = counts.get(topic, 0) + 1
    top = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
    return [
        {"topic": t, "count": n}
        for t, n in top
        if n >= PARSKATS_TOPIC_COUNT_MIN
    ][:3]


def _build_parskats_data(
    db: sqlite3.Connection,
    pid: int,
    positions: list[dict[str, Any]],
    contradictions: list[dict[str, Any]],
    today: Optional[date] = None,
) -> dict[str, Any]:
    """Compose Pārskats cilne 3-block payload.

    Returns dict with optional keys ``latest_activity`` / ``top_contradiction``
    / ``dominant_topics``. A key is omitted (not set to None/[]) when the
    corresponding block is below threshold, so the template renders
    ``{% if parskats_data.latest_activity %}`` conditionally without
    further null checks.

    Spec: ``docs/superpowers/specs/2026-05-14-profila-parskats-design.md``
    § 3. ``today`` parameter is injectable for tests so threshold
    boundary cases are deterministic.
    """
    today = today or now_lv_dt().date()
    result: dict[str, Any] = {}

    activity = _latest_activity_block(db, pid, positions, today)
    if activity is not None:
        result["latest_activity"] = activity

    contradiction = _top_contradiction_block(contradictions)
    if contradiction is not None:
        result["top_contradiction"] = contradiction

    topics = _dominant_topics_block(positions, today)
    if topics:
        result["dominant_topics"] = topics

    return result


# ── Saites cilnes palīgi ────────────────────────────────────────────


def _vote_alignment_for(
    db: sqlite3.Connection,
    pid: int,
    top_n: int = 3,
    align: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Top/bottom-N most/least aligned co-deputies by Saeima vote agreement.

    Restricted to pairs sharing >=10 votes (filters seat-warmers and
    one-off appearances). Returns ``(top, bottom)`` lists of dicts with
    name/slug/party/agree_pct. Empty lists when the pid has no
    qualifying co-voters.

    ``align`` is the shared ``vote_alignment_data(db)`` bundle — pass it
    when calling in a loop (render_politicians computes it once; the old
    per-pid SQL self-join here cost ~60s across 195 profiles). Omitted,
    it is computed on the spot, which keeps single-profile callers and
    tests working unchanged.

    Tikai nodotās balsis (Par/Pret/Atturas) abās savienojuma pusēs —
    klātbūtnes/reģistrācijas stāvokļi (Reģistrējies/Nebalsoja/Nereģistrējies)
    izslēgti, lai metrika mēra balsojumu sakritību, ne klātbūtni; filtrs
    dzīvo ``vote_alignment_data`` (sk. rankings.py::_vote_alignment_outliers,
    2026-06-08).
    """
    if align is None:
        align = vote_alignment_data(db)
    meta = align["meta"]
    # Partneru pid augošā secībā — tas pats tie-break, ko deva vecā SQL
    # GROUP BY secība: Python sort ir stabils, tāpēc vienādi agree_pct
    # paliek pid kārtībā un top/bottom-3 nesajaucas pēc refaktora.
    partners = []
    for (lo, hi), (agree, total) in align["pairs"].items():
        if pid not in (lo, hi):
            continue
        partners.append((hi if lo == pid else lo, agree, total))
    partners.sort()
    items = []
    for other, agree, total in partners:
        p = meta.get(other)
        if p is None or p["relationship_type"] == "inactive":
            continue
        items.append({
            "name": p["name"],
            "slug": _slugify(p["name"]),
            "party": p["party"],
            "agree_pct": round(agree * 100 / total),
            "agree": agree,
            "total": total,
        })
    if not items:
        return [], []
    items.sort(key=lambda x: x["agree_pct"], reverse=True)
    top = items[:top_n]
    bottom = list(reversed(items[-top_n:])) if len(items) > top_n else []
    return top, bottom



def _saites_neighbors_with_coords(
    neighbors: list[dict[str, Any]],
    cx: float = 200.0,
    cy: float = 140.0,
    r: float = 90.0,
) -> list[dict[str, Any]]:
    """Annotate each neighbor with pre-computed SVG ring-layout coords.

    Jinja has no built-in trig filters, so we compute ``x``/``y`` Python-
    side and emit a static SVG (no runtime JS). 8 max — denser rings
    overlap labels at 400×280 viewBox. Center node sits at (cx, cy)
    and is rendered separately by the template.
    """
    n = len(neighbors)
    if n == 0:
        return []
    out = []
    for i, neighbor in enumerate(neighbors):
        angle = (i / n) * 2 * math.pi - math.pi / 2
        out.append({
            **neighbor,
            "x": round(cx + r * math.cos(angle), 1),
            "y": round(cy + r * math.sin(angle), 1),
        })
    return out


def _fetch_saites_for_profile(
    db: sqlite3.Connection,
    pid: int,
    profile_kind: str,
    tensions: list[dict[str, Any]],
    commentary_about: list[dict[str, Any]],
    align: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the Saites tab payload from already-fetched per-politician data.

    Splits ``tensions`` by ``tension_type`` into uzbrukumi / spriedzes /
    atbalsts (the 3 type-color sections), surfaces commentary_about as a
    fourth section, runs vote_alignment_for deputies only, and pre-
    computes a ring of up to 8 tension-neighbor coords for the static
    SVG mini-graf. Pure transformation — no extra queries beyond
    ``_vote_alignment_for``.
    """
    uzbrukumi: list[dict[str, Any]] = []
    spriedzes: list[dict[str, Any]] = []
    atbalsts: list[dict[str, Any]] = []
    for t in tensions:
        tt = (t.get("tension_type") or "").lower()
        if tt == "uzbrukums":
            uzbrukumi.append(t)
        elif tt == "atbalsts":
            atbalsts.append(t)
        else:
            spriedzes.append(t)

    vote_top: list[dict[str, Any]] = []
    vote_bottom: list[dict[str, Any]] = []
    if profile_kind == "deputy":
        vote_top, vote_bottom = _vote_alignment_for(db, pid, top_n=3, align=align)

    # Anotē katras kartiņas other_pid / other_slug / is_anchor priekš
    # B-lite saites tab — pirmā kartiņa pārim (Uzbrukumi → Spriedzes → Atbalsts)
    # saņem is_anchor=True, kalpojot kā URL fragment target.
    anchored_pids: set[int] = set()

    def _annotate_card(t: dict[str, Any]) -> dict[str, Any]:
        if t.get("source_pid") == pid:
            other_pid = t.get("target_pid")
            other_name = t.get("target_name")
        else:
            other_pid = t.get("source_pid")
            other_name = t.get("source_name")
        is_anchor = other_pid is not None and other_pid not in anchored_pids
        if is_anchor:
            anchored_pids.add(other_pid)
        return {
            **t,
            "other_pid": other_pid,
            "other_slug": _slugify(other_name) if other_name else "",
            "is_anchor": is_anchor,
        }

    uzbrukumi = [_annotate_card(t) for t in uzbrukumi]
    spriedzes = [_annotate_card(t) for t in spriedzes]
    atbalsts = [_annotate_card(t) for t in atbalsts]

    # Build mini-graf neighbors: up to 8 unique tension partners.
    seen: dict[int, dict[str, Any]] = {}
    for t in tensions:
        if t.get("source_pid") == pid:
            other_pid = t.get("target_pid")
            other_name = t.get("target_name")
            other_party = t.get("target_party")
        elif t.get("target_pid") == pid:
            other_pid = t.get("source_pid")
            other_name = t.get("source_name")
            other_party = t.get("source_party")
        else:
            continue
        if other_pid is None or other_pid in seen:
            continue
        seen[other_pid] = {
            "pid": other_pid,
            "name": other_name or "",
            "slug": _slugify(other_name) if other_name else "",
            "tension_type": (t.get("tension_type") or "spriedze"),
            "party_color": PARTY_COLORS.get(other_party or "", "#8b8fa3"),
        }
        if len(seen) >= 8:
            break
    neighbors = _saites_neighbors_with_coords(list(seen.values()))

    return {
        "uzbrukumi": uzbrukumi,
        "spriedzes": spriedzes,
        "atbalsts": atbalsts,
        "commentary_about": commentary_about,
        "vote_alignment_top": vote_top,
        "vote_alignment_bottom": vote_bottom,
        "mini_graph": {"neighbors": neighbors},
    }
