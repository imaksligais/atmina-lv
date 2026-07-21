"""Render the per-politician profile pages.

Phase F3b (refactor-plan-2026-04-29 § Fāze 3) carve-out from
src/generate.py. Imports flow strictly from ``src.render._common`` —
no peer-module dependencies.

Outputs:
- ``output/atmina/politiki/<slug>.html`` — one detail page per
  tracked politician (~159 pages). The Personas index lives in
  src/render/personas.py.

Sibling module ``src.render.personas`` shares ``_get_last_activity``
via ``_common`` (F4 leaf rule — neither imports from the other).
"""

from __future__ import annotations

import math
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment

from src.coalition import get_coalition_map
from src.db import now_lv_dt
from src.profile_kind import profile_kind_label
from src.render._common import (
    ASSETS_DIR,
    BASE_URL,
    PARTY_COLORS,
    _bill_slug,
    _date_sort_key,
    _enrich_contradiction,
    _initials_from_name,
    _load_wiki_profile,
    _outlet_feed_map,
    _render_page,
    _slugify,
    norm_source_domain_sql,
    derive_profile_kind,
)
from src.render.vad import (
    VadDeclarationView,
    get_vad_data_for_politicians,
)

# Pārskats cilnes signāla blokus regulējošās konstantes — spec
# docs/superpowers/specs/2026-05-14-profila-parskats-design.md § 5.2.
# Empīriski kalibrētas pret 2026-05-14 DB: pretrunu mediāns confirmed=1 ir
# 0.55 (12/17 ≥ 0.5); tēmu count ≥ 3 / 180d aptver 40% profilus (69 / 174).
PARSKATS_CONTRADICTION_SALIENCE_MIN = 0.5
PARSKATS_TOPIC_COUNT_MIN = 3
PARSKATS_TOPIC_WINDOW_DAYS = 180


def _fetch_politicians(db: sqlite3.Connection) -> list[dict[str, Any]]:
    """Full politician list with per-person claim/contradiction/vote counts.

    ``claims_count`` is restricted to claim_type='position' so the label
    "pozīcijas" in templates reflects real rhetorical activity rather
    than bulk Saeima vote imports. ``votes_count`` comes from
    ``saeima_individual_votes`` (the raw vote ledger) and is unchanged.
    """
    rows = db.execute(
        "SELECT * FROM tracked_politicians "
        "WHERE relationship_type NOT IN ('inactive', 'commentator') "
        "ORDER BY name"
    ).fetchall()
    results = []
    for r in rows:
        p = dict(r)
        pid = p["id"]
        p["slug"] = _slugify(p["name"])
        p["claims_count"] = db.execute(
            "SELECT COUNT(*) FROM claims WHERE opponent_id = ? AND claim_type = 'position'",
            (pid,),
        ).fetchone()[0]
        # COALESCE(confirmed,1)=1 matches the public pretrunas/temas/search
        # filter — neapstiprinātās pretrunas neskaita, lai profila/typeahead
        # skaitlis nesadalītos no publiskajām lapām.
        p["contradictions_count"] = db.execute(
            "SELECT COUNT(*) FROM contradictions "
            "WHERE opponent_id = ? AND COALESCE(confirmed, 1) = 1",
            (pid,),
        ).fetchone()[0]
        p["votes_count"] = db.execute(
            "SELECT COUNT(*) FROM saeima_individual_votes WHERE politician_id = ?", (pid,)
        ).fetchone()[0]
        # profile_kind drives role-aware tab dispatch in the template.
        # Computed here so politician.profile_kind is available alongside
        # the rest of the politician row without an extra query per page.
        # votes_count is a 14. Saeima count in practice (saeima-tracker
        # is the only votes source; pre-2022 votes were never imported).
        p["profile_kind"] = derive_profile_kind(
            p.get("relationship_type") or "",
            p.get("role"),
            p["votes_count"],
        )
        # Fallback label for the role-chip when ``role`` is empty/None —
        # avoids the legacy ``'Politiķis'`` mis-label on journalist /
        # organization / inactive profiles.
        p["role_label"] = p.get("role") or profile_kind_label(p["profile_kind"])
        results.append(p)
    return results


def _fetch_commentary_about(db: sqlite3.Connection, pid: int) -> list[dict[str, Any]]:
    """Return third-party commentary claims about politician pid.

    A commentary claim has ``speaker_id IS NOT NULL`` and ``speaker_id != opponent_id``
    and ``claim_type = 'commentary'``. Joined with the speaker's tracked_politicians
    row so the template can render "X apgalvo par [this politician]" with a link
    to the speaker's own page.

    Ordering: most recent first (by stated_at, fallback created_at).
    """
    rows = db.execute(
        """
        SELECT c.id, c.topic, c.stance, c.quote, c.confidence, c.reasoning,
               c.source_url, c.stated_at, c.created_at, c.claim_type,
               c.speaker_id,
               sp.name AS speaker_name,
               sp.x_handle AS speaker_handle
        FROM claims c
        JOIN tracked_politicians sp ON sp.id = c.speaker_id
        WHERE c.opponent_id = ?
          AND c.claim_type = 'commentary'
          AND c.speaker_id IS NOT NULL
          AND c.speaker_id != c.opponent_id
        ORDER BY COALESCE(c.stated_at, c.created_at) DESC
        """,
        (pid,),
    ).fetchall()
    return [dict(r) for r in rows]


_VAD_KIND_ELIGIBLE = frozenset(
    {"deputy", "minister", "mep", "regional", "former", "politician"}
)


def _profile_tab_set(
    kind: str,
    has_contradictions: bool = False,
    has_saites_content: bool = False,
    has_vad_data: bool = False,
    has_parskats: bool = False,
    has_publikacijas: bool = False,
    has_saeima_content: bool = True,
) -> list[str]:
    """Return ordered tab IDs for a politician profile, keyed by profile_kind.

    ``tabs[0]`` is the default — both visually (active stat-bar button)
    and behaviorally (open tab on page-load when no URL hash). Per spec
    § 4.1 (2026-05-14):

    - Politiķi / inactive: ``parskats`` first when data exists, else
      ``timeline``.
    - Journalist / analyst: ``publikacijas`` first when data exists,
      else ``timeline``.
    - Organization: ``publikacijas`` first if data, then ``saites`` if
      data, else ``timeline``.

    ``deklaracijas`` is appended for VAD-eligible kinds when
    ``has_vad_data`` is true.
    """
    if kind in ("deputy", "minister", "mep", "regional", "politician", "former"):
        head = ["parskats"] if has_parskats else []
        tail = ["timeline", "pozicijas"]
        # The Saeimā tab hosts votes + Likumprojekti, so it is meaningful
        # only when there is at least one of those to show. ``former`` is
        # assigned to anyone whose role text says "bijuš…" with zero
        # current-term votes — which captures former mayors and former TV
        # hosts, not just former deputies. Gating on ``has_saeima_content``
        # keeps the "bijušais deputāts" tab off those non-deputy profiles
        # while preserving it for a genuine former deputy with vote/bill
        # history.
        if kind in ("deputy", "former") and has_saeima_content:
            tail.append("saeima")
        tail.extend(["pretrunas", "saites"])
        tabs = head + tail
    elif kind in ("journalist", "analyst"):
        if has_publikacijas:
            tabs = ["publikacijas", "timeline", "komentari-by"]
        else:
            tabs = ["timeline", "komentari-by", "publikacijas"]
        if has_contradictions:
            tabs.append("pretrunas")
        if has_saites_content:
            tabs.append("saites")
    elif kind == "organization":
        if has_publikacijas:
            tabs = ["publikacijas", "timeline", "pozicijas", "saites"]
        elif has_saites_content:
            tabs = ["saites", "timeline", "pozicijas"]
        else:
            tabs = ["timeline", "pozicijas", "saites"]
    elif kind == "inactive":
        tabs = ["parskats", "timeline"] if has_parskats else ["timeline"]
    else:
        tabs = ["timeline"]

    if has_vad_data and kind in _VAD_KIND_ELIGIBLE:
        tabs.append("deklaracijas")
    return tabs


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


def _vote_alignment_for(
    db: sqlite3.Connection, pid: int, top_n: int = 3
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Top/bottom-N most/least aligned co-deputies by Saeima vote agreement.

    Restricted to pairs sharing >=10 votes (filters seat-warmers and
    one-off appearances). Returns ``(top, bottom)`` lists of dicts with
    name/slug/party/agree_pct. Empty lists when the pid has no
    qualifying co-voters.

    Re-implemented per F4 leaf rule rather than imported from
    ``src.render.links``: that module's ``_fetch_graph_data`` is
    optimised for the global cross-party graph (filters by extreme
    alignment thresholds), not the per-pid view we want here. Promote
    to ``_common`` if/when both consumers need the same shape.
    """
    # Tikai nodotās balsis (Par/Pret/Atturas) abās savienojuma pusēs —
    # klātbūtnes/reģistrācijas stāvokļi (Reģistrējies/Nebalsoja/Nereģistrējies)
    # izslēgti, lai metrika mēra balsojumu sakritību, ne klātbūtni. Sk. fiksu
    # rankings.py::_vote_alignment_outliers (2026-06-08).
    rows = db.execute(
        """
        SELECT v2.politician_id AS pid, p.name, p.party,
               SUM(CASE WHEN v1.vote = v2.vote THEN 1 ELSE 0 END) AS agree,
               COUNT(*) AS total
        FROM saeima_individual_votes v1
        JOIN saeima_individual_votes v2
          ON v1.vote_id = v2.vote_id AND v2.politician_id != v1.politician_id
        JOIN tracked_politicians p ON v2.politician_id = p.id
        WHERE v1.politician_id = ?
          AND p.relationship_type != 'inactive'
          AND v1.vote IN ('Par', 'Pret', 'Atturas')
          AND v2.vote IN ('Par', 'Pret', 'Atturas')
        GROUP BY v2.politician_id
        HAVING total >= 10
        """,
        (pid,),
    ).fetchall()
    items = []
    for r in rows:
        items.append({
            "name": r["name"],
            "slug": _slugify(r["name"]),
            "party": r["party"],
            "agree_pct": round(r["agree"] * 100 / r["total"]),
            "agree": r["agree"],
            "total": r["total"],
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
        vote_top, vote_bottom = _vote_alignment_for(db, pid, top_n=3)

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


def _fetch_commentary_by(db: sqlite3.Connection, pid: int) -> list[dict[str, Any]]:
    """Claims authored BY this politician about OTHERS — journalist/analyst feed.

    Mirror image of ``_fetch_commentary_about``: speaker_id = pid (not
    opponent_id), opponent != speaker (filters first-party self-talk),
    claim_type = 'commentary'. Joined to ``tracked_politicians`` so the
    template can link to the target's profile page.
    """
    rows = db.execute(
        """
        SELECT c.id, c.topic, c.stance, c.quote, c.confidence,
               c.source_url, c.stated_at, c.created_at,
               c.opponent_id AS target_pid,
               target.name AS target_name,
               target.party AS target_party
        FROM claims c
        JOIN tracked_politicians target ON c.opponent_id = target.id
        WHERE c.speaker_id = ?
          AND c.opponent_id != c.speaker_id
          AND c.claim_type = 'commentary'
        ORDER BY COALESCE(c.stated_at, c.created_at) DESC
        LIMIT 50
        """,
        (pid,),
    ).fetchall()
    return [
        {**dict(r), "target_slug": _slugify(r["target_name"]) if r["target_name"] else ""}
        for r in rows
    ]


# Max individual-vote rows rendered inline in the Saeimā tab. The full
# per-deputy ledger (up to ~5700 rows) was ~82% of each heavy deputy page;
# the complete, filterable history lives at balsojumi.html (Balsojumu matrica).
VOTE_DISPLAY_CAP = 100


def _fetch_politician_detail(
    db: sqlite3.Connection,
    pid: int,
    profile_kind: str = "politician",
    vad_data: list[VadDeclarationView] | None = None,
    feed_outlets: dict[int, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Full detail for one politician: positions, contradictions, votes.

    After Phase D2 of the claim_type split: the Pozīcijas tab iterates
    ``positions`` (claim_type='position' only). The Balsojumi tab uses
    the ``votes`` list, which comes from the richer saeima_individual_votes
    ledger (with per-vote faction breakdown and result metadata) — a
    strictly better representation than would be possible from just the
    claims table. The legacy ``claims`` key is retained for any
    consumer that still expects a unified list.
    """
    claims_rows = db.execute("""
        SELECT c.*, COALESCE(d.platform, '') AS platform
        FROM claims c
        LEFT JOIN documents d ON c.document_id = d.id
        WHERE c.opponent_id = ? AND c.claim_type = 'position'
        ORDER BY c.stated_at DESC
    """, (pid,)).fetchall()
    positions = [dict(r) for r in claims_rows]
    # Sort by stated_at DESC, tiebreaker by salience DESC — ensures
    # same-day claims show in importance order. Without salience tiebreaker,
    # Pārskats Bloks A picked arbitrary claim when politiķim multiple
    # claims sharing stated_at (e.g., Siliņas 14.05 demisija sal=1.0
    # vs Melņa aizstāvība sal=0.9, both stated_at='2026-05-14').
    positions.sort(
        key=lambda c: (_date_sort_key(c.get("stated_at") or ""), c.get("salience") or 0.0),
        reverse=True,
    )
    # Back-compat alias for any consumer still reading `claims`. Same list
    # — Phase C/D cross-checks showed no site reader needs a union list.
    claims = positions

    # Contradictions
    # INNER JOIN tp is safe — this function is always called with a live pid
    # from the politicians list, so tp.id will resolve. Matches _fetch_contradictions.
    ct_rows = db.execute("""
        SELECT
            ct.id, ct.opponent_id, ct.topic, ct.summary, ct.severity,
            ct.detected_at, ct.salience, ct.confirmed,
            tp.name AS politician_name, tp.party, tp.role,
            c_old.stance AS old_stance, c_old.stated_at AS old_date,
            c_old.source_url AS old_source, c_old.quote AS old_quote,
            c_new.stance AS new_stance, c_new.stated_at AS new_date,
            c_new.source_url AS new_source, c_new.quote AS new_quote
        FROM contradictions ct
        JOIN tracked_politicians tp ON ct.opponent_id = tp.id
        LEFT JOIN claims c_old ON ct.claim_old_id = c_old.id
        LEFT JOIN claims c_new ON ct.claim_new_id = c_new.id
        WHERE ct.opponent_id = ?
        ORDER BY ct.detected_at DESC
    """, (pid,)).fetchall()
    contradictions = []
    for r in ct_rows:
        d = dict(r)
        _enrich_contradiction(d, db)
        contradictions.append(d)

    # Individual votes — inline ledger capped at VOTE_DISPLAY_CAP most-recent
    # rows (the full history was the dominant deputy-page weight). votes_total
    # is the true count, kept for the profile stat chip + the "rādīti N no M"
    # link to the full Balsojumu matrica.
    votes_total = db.execute(
        "SELECT COUNT(*) FROM saeima_individual_votes WHERE politician_id = ?",
        (pid,),
    ).fetchone()[0]
    votes_rows = db.execute("""
        SELECT siv.vote, sv.motif, sv.vote_date, sv.vote_time, sv.result
        FROM saeima_individual_votes siv
        JOIN saeima_votes sv ON siv.vote_id = sv.id
        WHERE siv.politician_id = ?
        ORDER BY sv.vote_date DESC, sv.vote_time DESC
        LIMIT ?
    """, (pid, VOTE_DISPLAY_CAP)).fetchall()
    votes = [dict(r) for r in votes_rows]

    # Unique topics for filter
    claim_topics = sorted(set(c["topic"] for c in claims if c.get("topic")))

    # Timeline: interleaved first-party positions + Saeima votes, most recent first.
    # claim_type='position' filter drops:
    #   (a) 'saeima_vote' claims, which duplicate the saeima_individual_votes
    #       UNION below AND carry DD.MM.YYYY stated_at strings that break the
    #       ISO ORDER BY (pre-2026-04-11 split legacy); without this filter,
    #       active deputies' timelines were 96% saeima vote claims, masking
    #       real positions out of the LIMIT 50 window.
    #   (b) 'commentary' claims, which are third-party speech about the
    #       politician (CLAUDE.md §5) and belong in Saites > Komentāri par X,
    #       not in this politician's own activity feed.
    timeline_rows = db.execute("""
        SELECT stated_at as date, 'claim' as event_type, topic, stance as detail,
               source_url, confidence, NULL as vote_result
        FROM claims
        WHERE opponent_id = ?
          AND claim_type = 'position'
          AND stated_at IS NOT NULL
        UNION ALL
        SELECT sv.vote_date as date, 'vote' as event_type, sv.topic,
               sv.motif as detail, sv.url as source_url, NULL as confidence,
               siv.vote as vote_result
        FROM saeima_individual_votes siv
        JOIN saeima_votes sv ON siv.vote_id = sv.id
        WHERE siv.politician_id = ?
        ORDER BY date DESC
        LIMIT 50
    """, (pid, pid)).fetchall()
    timeline = [dict(r) for r in timeline_rows]

    # Tensions involving this politician
    tension_rows = db.execute("""
        SELECT pt.*, s.name AS source_name, s.party AS source_party,
               t.name AS target_name, t.party AS target_party
        FROM political_tensions pt
        JOIN tracked_politicians s ON pt.source_pid = s.id
        JOIN tracked_politicians t ON pt.target_pid = t.id
        WHERE (pt.source_pid = ? OR pt.target_pid = ?)
          AND s.relationship_type NOT IN ('inactive', 'commentator')
          AND t.relationship_type NOT IN ('inactive', 'commentator')
        ORDER BY pt.created_at DESC LIMIT 20
    """, (pid, pid)).fetchall()
    tensions = [dict(r) for r in tension_rows]

    # Recent news mentioning this politician (subject first, then mentioned)
    news_rows = db.execute("""
        SELECT d.id, d.source_url, d.source_domain, d.scraped_at,
               SUBSTR(d.content, 1, 200) as preview,
               dp.role
        FROM documents d
        JOIN document_politicians dp ON dp.document_id = d.id
        WHERE dp.politician_id = ? AND d.platform = 'web'
        ORDER BY CASE dp.role WHEN 'subject' THEN 0 ELSE 1 END,
                 d.scraped_at DESC
        LIMIT 10
    """, (pid,)).fetchall()
    news = [dict(r) for r in news_rows]

    # Medija paša publikācijas — tikai organizāciju profiliem, kuriem ir
    # outlets mapping (sources.yaml outlet, kura X feeds saskan ar profila
    # social_accounts.handle). Atlasa pēc source_domain (NE matcher-saiti),
    # tāpēc parādās arī raksti, kuros medijs nepiemin sevi. `news` saraksts
    # paliek pieminējumu signāls; šis ir paša satura signāls.
    own_pubs: list[dict[str, Any]] = []
    own_pubs_outlet: dict[str, str] | None = None
    if profile_kind == "organization":
        if feed_outlets is None:
            feed_outlets = _outlet_feed_map(db)
        outlet = feed_outlets.get(pid)
        if outlet:
            # Normalizē hostus Python-ā (nostrippo www.) — sakrīt ar SQL NORM.
            # Secība saglabāta: hosts[0] = primārais domēns sadaļas virsrakstam.
            hosts: list[str] = []
            for h in outlet.get("hosts") or []:
                h = (h or "").strip().lower()
                if h.startswith("www."):
                    h = h[4:]
                if h and h not in hosts:
                    hosts.append(h)
            if hosts:
                norm = norm_source_domain_sql("d.source_domain")
                ph = ",".join("?" * len(hosts))
                own_rows = db.execute(f"""
                    SELECT d.id, d.source_url, d.source_domain, d.scraped_at,
                           d.published_at, SUBSTR(d.content, 1, 200) AS preview
                    FROM documents d
                    WHERE d.platform = 'web' AND {norm} IN ({ph})
                    ORDER BY COALESCE(d.published_at, d.scraped_at) DESC
                    LIMIT 10
                """, hosts).fetchall()
                own_pubs = [dict(r) for r in own_rows]
            # `host` = primārais domēns virsrakstam "Publikācijas vietnē X" —
            # brenda nosaukums nominatīvā virsrakstā prasītu ģenitīva locījumu.
            own_pubs_outlet = {
                "name": outlet["name"], "slug": outlet["slug"],
                "host": hosts[0] if hosts else None,
            }

    # Party metadata (color, link to party page)
    party_meta = None
    politician_row = db.execute("SELECT party FROM tracked_politicians WHERE id = ?", (pid,)).fetchone()
    if politician_row:
        p_party = politician_row[0]
        if p_party:
            try:
                party_row = db.execute(
                    "SELECT * FROM parties WHERE name = ? OR short_name = ?",
                    (p_party, p_party)
                ).fetchone()
                if party_row:
                    party_meta = dict(party_row)
            except Exception:
                pass

    commentary_about = _fetch_commentary_about(db, pid)

    # External profiles (FB, website, ...) — fetch-ready shēma, pagaidām tikai UI.
    ext_rows = db.execute(
        "SELECT platform, url, handle, display_label "
        "FROM external_profiles WHERE opponent_id=? AND active=1 "
        "ORDER BY platform, id",
        (pid,),
    ).fetchall()
    external_profiles = [dict(r) for r in ext_rows]

    # X subtab: the politician's OWN tweets — role='subject' on twitter
    # platform docs. Excludes x_mention (always third-party-authored about
    # them) and 'mentioned' / 'mention_target' roles (where someone else
    # is the speaker). Distinct from `news` (web articles) and
    # `commentary_about` (curated commentary claims).
    x_posts_rows = db.execute("""
        SELECT d.id, d.content, d.source_url, d.source_domain,
               d.platform, d.published_at, d.scraped_at, d.language,
               dp.role
        FROM documents d
        JOIN document_politicians dp ON dp.document_id = d.id
        WHERE dp.politician_id = ?
          AND d.platform = 'twitter'
          AND dp.role = 'subject'
        ORDER BY COALESCE(d.published_at, d.scraped_at) DESC
        LIMIT 50
    """, (pid,)).fetchall()
    x_posts = [dict(r) for r in x_posts_rows]

    # Bills this politician is linked to via saeima_bill_politicians junction.
    # Currently empty in production (Phase 1A backfill didn't populate junction);
    # Phase 1C live agent will populate it going forward.
    # Guard against test DBs that haven't run init_saeima_bills().
    bills_involved = []
    try:
        for r in db.execute("""
            SELECT DISTINCT b.id, b.document_nr, b.bill_type, b.title, b.summary, b.topic,
                   b.current_stage, b.current_status, b.last_updated_at, b.first_seen_at,
                   b.institutional_submitter,
                   (SELECT COUNT(*) FROM saeima_bill_politicians WHERE bill_id=b.id AND role='submitter') AS submitter_count,
                   (SELECT COUNT(*) FROM saeima_bill_stages WHERE bill_id=b.id) AS stage_count,
                   (SELECT COUNT(*) FROM saeima_votes WHERE bill_id=b.id) AS vote_count
            FROM saeima_bills b
            JOIN saeima_bill_politicians bp ON bp.bill_id = b.id
            WHERE bp.politician_id = ?
            ORDER BY b.last_updated_at DESC
        """, (pid,)).fetchall():
            bills_involved.append({
                **dict(r),
                "slug": _bill_slug(r["document_nr"]),
            })
    except sqlite3.OperationalError:
        # saeima_bills tables not present (legacy test DB) — silently return empty
        bills_involved = []

    saites_data = _fetch_saites_for_profile(
        db, pid, profile_kind, tensions, commentary_about
    )
    has_saites_content = bool(
        saites_data["uzbrukumi"] or saites_data["spriedzes"]
        or saites_data["atbalsts"] or saites_data["commentary_about"]
        or saites_data["vote_alignment_top"]
    )
    commentary_by: list[dict[str, Any]] = []
    if profile_kind in ("journalist", "analyst"):
        commentary_by = _fetch_commentary_by(db, pid)
    vad_data = vad_data or []

    # Pārskats data — built only for kinds where the tab is offered
    # (politiķi + inactive; žurnālisti / analītiķi / organizācijas saglabā
    # Publikācijas / Saites kā primāro signālu — sk. _profile_tab_set base
    # mapping). Empty dict signals "no Pārskats" → tab_set excludes it.
    parskats_data: dict[str, Any] = {}
    if profile_kind not in ("journalist", "analyst", "organization"):
        parskats_data = _build_parskats_data(db, pid, positions, contradictions)

    tab_set = _profile_tab_set(
        profile_kind,
        has_contradictions=bool(contradictions),
        has_saites_content=has_saites_content,
        has_vad_data=bool(vad_data),
        has_parskats=bool(parskats_data),
        has_publikacijas=bool(x_posts or news or own_pubs),
        has_saeima_content=votes_total > 0 or bool(bills_involved),
    )

    return {
        "bills_involved": bills_involved,
        "claims": claims,
        "commentary_about": commentary_about,
        "commentary_by": commentary_by,
        "contradictions": contradictions,
        "external_profiles": external_profiles,
        "news": news,
        "own_pubs": own_pubs,
        "own_pubs_outlet": own_pubs_outlet,
        "party_meta": party_meta,
        "positions": positions,
        "claim_topics": claim_topics,
        "parskats_data": parskats_data,
        "saites_data": saites_data,
        "tab_set": tab_set,
        "timeline": timeline,
        "tensions": tensions,
        "vad_data": vad_data,
        "votes": votes,
        "votes_total": votes_total,
        "x_posts": x_posts,
    }


def _keep_digging_for_profile(
    p: dict[str, Any],
    politicians: list[dict[str, Any]],
    idx: int,
    db: sqlite3.Connection,
    coalition_map: dict[str, str],
) -> dict[str, Any]:
    """"Turpini rakt" columns for a profile page (hrefs relative to
    ``politiki/<slug>.html``). Deterministic — no runtime randomness — so the
    char baselines stay byte-stable across rebuilds.

    Link enrichment consumed by ``_keep_digging.html.j2``:
    profile links carry ``initials`` + ``coalition`` (avatar + ring/dot colour);
    topic links carry ``count`` + ``bar`` (0–100, ∝ position count → underline).
    """
    columns: list[dict[str, Any]] = []
    party = p.get("party") or ""
    slug = p.get("slug")
    photos_dir = ASSETS_DIR / "photos"

    def _profile_link(q: dict[str, Any], with_party: bool) -> dict[str, Any]:
        q_party = q.get("party") or ""
        return {
            "label": q["name"],
            "href": f"{q['slug']}.html",
            "initials": _initials_from_name(q["name"]),
            "slug": q["slug"],
            "photo": (photos_dir / f"{q['slug']}.jpg").exists(),
            "coalition": coalition_map.get(q_party, "other"),
            "sub": (q_party or None) if with_party else None,
        }

    if party:
        same = [
            q for q in politicians
            if (q.get("party") or "") == party and q.get("slug") != slug
        ][:6]
        if same:
            columns.append({
                "title": "Citi šajā partijā",
                "links": [_profile_link(q, with_party=False) for q in same],
            })

    topic_rows = db.execute(
        """
        SELECT topic, COUNT(*) AS n FROM claims
        WHERE opponent_id = ? AND claim_type = 'position' AND topic IS NOT NULL
        GROUP BY topic ORDER BY n DESC, topic LIMIT 4
        """,
        (p["id"],),
    ).fetchall()
    if topic_rows:
        max_n = max(r["n"] for r in topic_rows) or 1
        columns.append({
            "title": "Tēmas",
            "links": [
                {
                    "label": r["topic"],
                    "href": f"../temas/{_slugify(r['topic'])}.html",
                    "count": r["n"],
                    "bar": round(r["n"] / max_n * 100),
                }
                for r in topic_rows
            ],
        })

    # "Vēl profili" — deterministic spread across the roster (no randomness).
    n = len(politicians)
    others: list[dict[str, Any]] = []
    seen = {slug}
    for off in (40, 87, 134, 61, 23):
        if n == 0 or len(others) >= 3:
            break
        q = politicians[(idx + off) % n]
        if q.get("slug") not in seen:
            seen.add(q.get("slug"))
            others.append(q)
    if others:
        columns.append({
            "title": "Vēl profili",
            "links": [_profile_link(q, with_party=True) for q in others],
        })

    return {"columns": columns}


def render_politicians(
    env: Environment,
    db: sqlite3.Connection,
    atmina_dir: Path,
    politicians: list[dict[str, Any]],
    pid_to_syntheses: dict[int, list[dict[str, Any]]],
) -> int:
    """Render one politiki/<slug>.html per tracked politician.

    Mirrors the inline block previously at ``src/generate.py`` lines
    3146-3173. Returns the count of pages emitted (one per politician).
    """
    politiki_dir = atmina_dir / "politiki"
    politiki_dir.mkdir(parents=True, exist_ok=True)
    photos_dir = ASSETS_DIR / "photos"
    photos_exist = photos_dir.exists()

    # Pre-load VAD declarations for all politicians in one batch (F4 leaf-vs-fan-out).
    # Returns empty dict if vad_* tables don't exist yet (Phase 0 not run).
    all_pids = [p["id"] for p in politicians]
    vad_by_pid = get_vad_data_for_politicians(db, all_pids)

    # Coalition status per party (one query) — colours the "Turpini rakt"
    # avatar rings + dots. Source of truth: parties.coalition_status.
    coalition_map = get_coalition_map(db)

    feed_outlets = _outlet_feed_map(db)  # opponent_id -> outlet {name, slug}

    count = 0
    for idx, p in enumerate(politicians):
        profile_kind = p.get("profile_kind", "politician")
        vad_for_pid = vad_by_pid.get(p["id"], [])
        detail = _fetch_politician_detail(
            db, p["id"], profile_kind, vad_data=vad_for_pid,
            feed_outlets=feed_outlets,
        )
        wiki_profile = _load_wiki_profile(p["slug"])
        has_photo = (photos_dir / f"{p['slug']}.jpg").exists() if photos_exist else False
        keep_digging = _keep_digging_for_profile(p, politicians, idx, db, coalition_map)

        _render_page(env, "politician.html.j2", politiki_dir / f"{p['slug']}.html", {
            "politician": p,
            "feed_outlet": feed_outlets.get(p["id"]),
            "BASE_URL": BASE_URL,
            "share_url": f"{BASE_URL}/politiki/{p['slug']}.html",
            "digging": keep_digging,
            "bills_involved": detail["bills_involved"],
            "claims": detail["claims"],
            "positions": detail["positions"],
            "contradictions": detail["contradictions"],
            "votes": detail["votes"],
            "votes_total": detail["votes_total"],
            "claim_topics": detail["claim_topics"],
            "timeline": detail["timeline"],
            "tensions": detail["tensions"],
            "news": detail["news"],
            "own_pubs": detail["own_pubs"],
            "own_pubs_outlet": detail["own_pubs_outlet"],
            "party_meta": detail["party_meta"],
            "commentary_about": detail["commentary_about"],
            "commentary_by": detail["commentary_by"],
            "external_profiles": detail["external_profiles"],
            "parskats_data": detail["parskats_data"],
            "saites_data": detail["saites_data"],
            "tab_set": detail["tab_set"],
            "vad_data": detail["vad_data"],
            "x_posts": detail["x_posts"],
            "wiki_profile": wiki_profile,
            "has_photo": has_photo,
            "syntheses": pid_to_syntheses.get(p["id"], []),
        })
        count += 1
    return count
