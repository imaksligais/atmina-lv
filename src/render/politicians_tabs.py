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
    _lv_number,
    _lv_plural,
    _slugify,
    faction_alignment_data,
    vote_alignment_data,
)


# Pārskats cilnes signāla blokus regulējošās konstantes — spec
# docs/superpowers/specs/2026-05-14-profila-parskats-design.md § 5.2.
# Empīriski kalibrētas pret 2026-05-14 DB: pretrunu mediāns confirmed=1 ir
# 0.55 (12/17 ≥ 0.5); tēmu count ≥ 3 / 180d aptver 40% profilus (69 / 174).
PARSKATS_CONTRADICTION_SALIENCE_MIN = 0.5
PARSKATS_TOPIC_COUNT_MIN = 3
PARSKATS_TOPIC_WINDOW_DAYS = 180


# Klātbūtnes reģistrācija nav balsojums (Data Contract 4b): biļetena vērtības
# Reģistrējies/Nereģistrējies ir klātbūtnes stāvokļi. Viens predikāts visām
# profila Saeimas balsojumu vietām (politicians.py to importē no šejienes —
# importa virziens ir politicians → politicians_tabs, ne otrādi).
NOT_ATTENDANCE_SQL = "siv.vote NOT IN ('Reģistrējies', 'Nereģistrējies')"


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
    """Compose Bloks A — pēdējā aktivitāte (jaunākā pozīcija vai sēdes diena).

    Picks whichever is newer between latest position (`positions[0]`,
    already sorted DESC by stated_at) and the most recent Saeima vote.
    Returns ``None`` if politician has no claims and no votes.

    Balsojuma gadījumā bloks ir SĒDES DIENA ar nodoto balsojumu skaitu, ne
    viena balsojuma motīvs (T14 — procedurāls balsojums izskatās pēc nostājas;
    2026-10-08). Tie paši predikāti kā Laika līnijas «Saeimas sēde» rindai:
    klātbūtnes reģistrācija nav balsojums.
    """
    pos_date = ""
    latest_pos = positions[0] if positions else None
    if latest_pos:
        pos_date = (latest_pos.get("stated_at") or "")[:10]

    vote_row = db.execute(f"""
        SELECT sv.vote_date, COUNT(*) AS n
        FROM saeima_individual_votes siv
        JOIN saeima_votes sv ON siv.vote_id = sv.id
        WHERE siv.politician_id = ? AND {NOT_ATTENDANCE_SQL}
          AND sv.vote_date IS NOT NULL
        GROUP BY sv.vote_date
        ORDER BY sv.vote_date DESC
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
        n = vote_row["n"]
        return {
            "type": "vote",
            "date": vote_date,
            "relative": _format_relative_time_lv(vote_date, today),
            "n": n,
            "meta": f"{n} {_lv_plural(n, 'balsojums', 'balsojumi')}",
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
    faction_alignment: dict[int, dict[str, int]] | None = None,
) -> dict[str, Any]:
    """Compose Pārskats cilne signal-block payload.

    Returns dict with optional keys ``latest_activity`` / ``top_contradiction``
    / ``dominant_topics`` / ``faction_alignment``. A key is omitted (not set to None/[]) when the
    corresponding block is below threshold, so the template renders
    ``{% if parskats_data.latest_activity %}`` conditionally without
    further null checks.

    Spec: ``docs/superpowers/specs/2026-05-14-profila-parskats-design.md``
    § 3. ``today`` parameter is injectable for tests so threshold
    boundary cases are deterministic.

    ``faction_alignment`` is the shared ``faction_alignment_data(db)`` map
    («Balso kopā ar savu frakciju») — pass it when calling in a loop
    (render_politicians computes it once); omitted, it is computed on the
    spot, the same contract as ``_vote_alignment_for``'s ``align``.
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

    if faction_alignment is None:
        faction_alignment = faction_alignment_data(db)
    fa = faction_alignment.get(pid)
    if fa is not None:
        # Teksts sagatavots šeit (kā ``latest_activity.meta``): «7 258», ne «7258».
        result["faction_alignment"] = {
            **fa,
            "body": f"{_lv_number(fa['agree'])} no {_lv_number(fa['total'])} "
                    f"balsojumiem {fa['convocation']}. Saeimā",
        }

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
    has_votes: bool = False,
) -> dict[str, Any]:
    """Build the Saites tab payload from already-fetched per-politician data.

    Splits ``tensions`` by ``tension_type`` into uzbrukumi / spriedzes /
    atbalsts (the 3 type-color sections), surfaces commentary_about as a
    fourth section, runs vote_alignment_for only when ``has_votes`` (the
    caller's cast-ballot count > 0; ``profile_kind`` is kept for callers
    but no longer gates it), and pre-
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
    # Vārti ir balsojumu esamība, ne profile_kind: kind izvēlas pēc lomas
    # teksta («ministr…» uzvar balsojumus), tāpēc deputāts ar lomu «…
    # parlamentārais sekretārs» kļūst par ``minister`` un agrāk palika bez
    # balsojumu sakritības (sk. politicians._profile_tab_set, 2026-10-07).
    if has_votes:
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


# ── Profila galvene: skaitļu josla + mēnešu aktivitātes grafiks ─────
# Plāns docs/plans/2026-10-07-profilu-dizains.md, B uzd. 3. un 5. punkts.

_LV_MONTHS = (
    "janvāris", "februāris", "marts", "aprīlis", "maijs", "jūnijs",
    "jūlijs", "augusts", "septembris", "oktobris", "novembris", "decembris",
)
_LV_MONTHS_SHORT = (
    "janv.", "febr.", "marts", "apr.", "maijs", "jūn.",
    "jūl.", "aug.", "sept.", "okt.", "nov.", "dec.",
)

# Grafika sērijas (atslēga, leģendas nosaukums). Balsojumi apzināti NAV —
# simtiem mēnesī tie sabojā mērogu, un balsojums nav paša aktivitāte tādā
# pašā nozīmē (T14). Visi trīs avoti ir LV datuma kolonnas; UTC kolonnas
# (document_politicians.created_at) šeit nedrīkst nonākt (T17).
CHART_SERIES: tuple[tuple[str, str], ...] = (
    ("pos", "Pozīcijas"),
    ("speech", "Uzstāšanās debatēs"),
    ("q", "Jautājumi un pieprasījumi"),
)
CHART_MONTHS = 12
_CHART_GROUP_W = 30.0   # viewBox vienības uz mēnesi (12 × 30 = 360)
_CHART_BAR_W = 7.0
_CHART_BAR_GAP = 1.5


def _table_exists(db: sqlite3.Connection, name: str) -> bool:
    return db.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)
    ).fetchone() is not None


def _nice_ceiling(v: int) -> tuple[int, int]:
    """Mazākais «apaļais» griestu skaitlis ≥ v un tā solis (≤ 4 iedaļas)."""
    if v <= 0:
        return 0, 1
    for exp in range(7):
        for base in (1, 2, 5):
            step = base * 10 ** exp
            if math.ceil(v / step) <= 4:
                return math.ceil(v / step) * step, step
    return v, v


def _monthly_activity(
    db: sqlite3.Connection, pid: int, today: Optional[date] = None,
) -> dict[str, Any]:
    """Pēdējo 12 mēnešu (ieskaitot tekošo) aktivitāte pa sērijām.

    Pozīcijas — ``claims.stated_at`` (claim_type='position'); uzstāšanās —
    ``saeima_debate_speeches.session_date``; iesniegtie jautājumi —
    ``saeima_questions.submitted_date`` (role='submitter', katrs jautājums
    vienreiz). Atgriež arī SVG ģeometriju (viewBox 360 × 100), lai Jinja
    tikai izvada skaitļus.
    """
    today = today or now_lv_dt().date()
    months: list[tuple[int, int]] = []
    y, m = today.year, today.month
    for _ in range(CHART_MONTHS):
        months.append((y, m))
        y, m = (y, m - 1) if m > 1 else (y - 1, 12)
    months.reverse()
    start = f"{months[0][0]:04d}-{months[0][1]:02d}-01"

    counts: dict[str, dict[str, int]] = {k: {} for k, _ in CHART_SERIES}
    sources: list[tuple[str, str]] = [("pos", """
        SELECT SUBSTR(stated_at, 1, 7) ym, COUNT(*) n FROM claims
        WHERE opponent_id = ? AND claim_type = 'position' AND stated_at >= ?
        GROUP BY ym
    """)]
    if _table_exists(db, "saeima_debate_speeches"):
        sources.append(("speech", """
            SELECT SUBSTR(session_date, 1, 7) ym, COUNT(*) n FROM saeima_debate_speeches
            WHERE politician_id = ? AND session_date >= ?
            GROUP BY ym
        """))
    if _table_exists(db, "saeima_questions") and _table_exists(db, "saeima_question_politicians"):
        sources.append(("q", """
            SELECT SUBSTR(q.submitted_date, 1, 7) ym, COUNT(*) n FROM saeima_questions q
            WHERE q.id IN (SELECT question_id FROM saeima_question_politicians
                           WHERE politician_id = ? AND role = 'submitter')
              AND q.submitted_date >= ?
            GROUP BY ym
        """))
    for key, sql in sources:
        for r in db.execute(sql, (pid, start)).fetchall():
            counts[key][r[0]] = r[1]

    peak = max((n for c in counts.values() for n in c.values()), default=0)
    ceiling, step = _nice_ceiling(peak)
    out_months: list[dict[str, Any]] = []
    total = 0
    for i, (yy, mm) in enumerate(months):
        ym = f"{yy:04d}-{mm:02d}"
        vals = [counts[k].get(ym, 0) for k, _ in CHART_SERIES]
        total += sum(vals)
        x0 = i * _CHART_GROUP_W + (
            _CHART_GROUP_W - 3 * _CHART_BAR_W - 2 * _CHART_BAR_GAP) / 2
        bars = []
        for j, ((key, _label), v) in enumerate(zip(CHART_SERIES, vals, strict=True)):
            if not v:
                continue
            h = round(v / ceiling * 100, 2)
            bars.append({"key": key, "x": round(x0 + j * (_CHART_BAR_W + _CHART_BAR_GAP), 2),
                         "y": round(100 - h, 2), "h": h})
        full = f"{yy}. gada {_LV_MONTHS[mm - 1]}"
        out_months.append({
            "ym": ym,
            "label": _LV_MONTHS_SHORT[mm - 1],
            "full": full,
            "counts": vals,
            "x": i * _CHART_GROUP_W,
            "bars": bars,
            "title": full + ": " + ", ".join(
                f"{label.lower()} {v}" for (_k, label), v in zip(CHART_SERIES, vals, strict=True)
            ),
        })
    ticks = [{"value": v, "pct": round(v / ceiling * 100, 2)}
             for v in range(0, ceiling + 1, step)] if ceiling else []
    return {
        "months": out_months,
        "series": [{"key": k, "label": label} for k, label in CHART_SERIES],
        "ticks": ticks,
        "total": total,
        "group_w": _CHART_GROUP_W,
        "bar_w": _CHART_BAR_W,
        "first_label": out_months[0]["full"],
        "last_label": out_months[-1]["full"],
    }


# Skaitļu joslas flīzes: (atslēga, vienskaitlis, daudzskaitlis, paskaidrojums,
# cilne, uz kuru flīze ved). Paskaidrojums — virkne vai (vsk., dsk.) pāris.
_STAT_DEFS: dict[str, tuple[str, str, str | tuple[str, str], str]] = {
    "pozicijas": ("Pozīcija", "Pozīcijas", "No ziņām un X ierakstiem", "pozicijas"),
    "balsojumi": ("Balsojums", "Balsojumi", "Saeimas sēdēs", "saeima"),
    "pretrunas": ("Pretruna", "Pretrunas", ("Apstiprināta", "Apstiprinātas"), "pretrunas"),
    "dokumenti": ("Dokuments", "Dokumenti", "Ziņās un X ierakstos", "publikacijas"),
    "x": ("X ieraksts", "X ieraksti", "Savā kontā", "publikacijas"),
    "komentari": ("Komentārs", "Komentāri", "Par citiem politiķiem", "komentari-by"),
    "saites": ("Saite", "Saites", "Ar citām personām", "saites"),
}

# Kuras flīzes kurai profila grupai (līdz 4; nulles nerāda).
_STAT_ORDER: dict[str, tuple[str, ...]] = {
    "journalist": ("x", "komentari", "dokumenti", "pretrunas"),
    "analyst": ("x", "komentari", "dokumenti", "pretrunas"),
    "organization": ("dokumenti", "pozicijas", "x", "saites"),
}
_STAT_ORDER_DEFAULT = ("pozicijas", "balsojumi", "pretrunas", "dokumenti")


def _profile_stat_tiles(
    kind: str, counts: dict[str, int], tab_set: list[str],
) -> list[dict[str, Any]]:
    """Skaitļu joslas flīzes profila grupai. Nulles izmet; tukšs saraksts =
    «Vēl nav datu» stāvoklis templotē. Flīze ved uz cilni tikai tad, ja tā
    cilne lapā ir."""
    tiles = []
    for key in _STAT_ORDER.get(kind, _STAT_ORDER_DEFAULT):
        n = int(counts.get(key) or 0)
        if n <= 0:
            continue
        sing, plur, sub, tab = _STAT_DEFS[key]
        one = n % 10 == 1 and n % 100 != 11
        if isinstance(sub, tuple):
            sub = sub[0] if one else sub[1]
        if key == "dokumenti" and tab not in tab_set:
            tab = "pozicijas"  # politiķiem ziņas + X ir zem Pozīcijām
        tiles.append({
            "key": key,
            "value": _lv_number(n, 0),
            "label": sing if one else plur,
            "sub": sub,
            "tab": tab if tab in tab_set else None,
        })
    return tiles
