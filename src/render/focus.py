"""Uzmanības centrā composite — landing slot data (spec 2026-07-07).

Pure helpers: katrs atgriež dict | None; nekādu rakstīšanu DB. Visi vaicājumi
gated uz claim_type='position' + audience-izslēgšanu (tas pats filtrs kā brief
statistikai). `quote` teksti ir VERBATIM — nekādas normalizācijas (CLAUDE.md
Output Conventions izņēmums).
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from typing import Any, Optional

from src.coalition import get_coalition_map
from src.db import today_lv
from src.render._common import (
    PARTY_COLORS,
    _domain_from_url,
    _initials_from_name,
    _party_short_name,
    _slugify,
    ASSETS_DIR,
)

_AUDIENCE = ("journalist", "organization", "neutral", "inactive")
_SALIENCE_W = 4.0   # skora svars: n + 4*MAX(salience) — 0.85-solo pārspēj 2×0.3
_FRESH_DAYS = 14
_MIN_QUOTE_LEN = 40


def _person_card(name: str, party: Optional[str]) -> dict[str, Any]:
    slug = _slugify(name)
    party = party or ""
    return {
        "name": name,
        "slug": slug,
        "initials": _initials_from_name(name),
        "party_short": _party_short_name(party) if party else "",
        "party_color": PARTY_COLORS.get(party, "#8b8fa3"),
        "has_photo": (ASSETS_DIR / "photos" / f"{slug}.jpg").exists(),
    }


def _hot_topic(db: sqlite3.Connection) -> Optional[dict[str, Any]]:
    """Nedēļas karstākā tēma: skors = n + 4*MAX(salience), izšķirtne → politiķu skaits."""
    # Robežas LV laikā (stated_at glabā now_lv()); DATE('now') būtu UTC → līdz 3h nobīde.
    cutoff_7d = (today_lv() - timedelta(days=7)).isoformat()
    rows = db.execute(
        """SELECT c.topic, COUNT(*) n, COUNT(DISTINCT c.opponent_id) pol,
                  MAX(c.salience) maxsal
           FROM claims c JOIN tracked_politicians tp ON tp.id = c.opponent_id
           WHERE c.claim_type = 'position' AND c.stated_at >= ?
             AND tp.relationship_type NOT IN (?,?,?,?)
           GROUP BY c.topic""",
        (cutoff_7d, *_AUDIENCE),
    ).fetchall()
    if not rows:
        return None
    best = max(
        rows,
        key=lambda r: (r["n"] + _SALIENCE_W * (r["maxsal"] or 0), r["pol"], r["topic"]),
    )
    topic = best["topic"]

    qrows = db.execute(
        """SELECT c.opponent_id, c.quote, c.salience, c.stated_at, c.source_url,
                  tp.name, tp.party
           FROM claims c JOIN tracked_politicians tp ON tp.id = c.opponent_id
           WHERE c.claim_type = 'position' AND c.topic = ?
             AND c.stated_at >= ?
             AND c.quote IS NOT NULL AND LENGTH(c.quote) > ?
             AND tp.relationship_type NOT IN (?,?,?,?)
           ORDER BY c.salience DESC, c.stated_at DESC, c.id DESC""",
        (topic, cutoff_7d, _MIN_QUOTE_LEN, *_AUDIENCE),
    ).fetchall()
    quotes, seen = [], set()
    for r in qrows:
        if r["opponent_id"] in seen:
            continue
        seen.add(r["opponent_id"])
        card = _person_card(r["name"], r["party"])
        card.update({
            "quote": r["quote"],                       # VERBATIM
            "source_url": r["source_url"],
            "source_domain": _domain_from_url(r["source_url"]),
            "date": (r["stated_at"] or "")[:10],
        })
        quotes.append(card)
        if len(quotes) == 3:
            break

    cmap = get_coalition_map(db)
    koal = opoz = 0
    for r in db.execute(
        """SELECT tp.party, COUNT(*) n
           FROM claims c JOIN tracked_politicians tp ON tp.id = c.opponent_id
           WHERE c.claim_type = 'position' AND c.topic = ?
             AND c.stated_at >= ?
             AND tp.relationship_type NOT IN (?,?,?,?)
           GROUP BY tp.party""",
        (topic, cutoff_7d, *_AUDIENCE),
    ).fetchall():
        status = cmap.get(r["party"] or "")
        if status == "coalition":
            koal += r["n"]
        elif status == "opposition":
            opoz += r["n"]
    return {
        "topic": topic,
        "topic_slug": _slugify(topic),
        "n": best["n"],
        "pol": best["pol"],
        "quotes": quotes,
        "koal_n": koal,
        "opoz_n": opoz,
    }


def _quote_of_day(db: sqlite3.Connection) -> Optional[dict[str, Any]]:
    """Dienas (fallback: 7d) augstākās salience pozīcija ar kvalitatīvu citātu."""
    # Robežas LV laikā: vispirms šodienas citāts, tad 7d atkāpe.
    cutoffs = (
        today_lv().isoformat(),
        (today_lv() - timedelta(days=7)).isoformat(),
    )
    for cutoff in cutoffs:
        r = db.execute(
            """SELECT c.quote, c.salience, c.stated_at, c.source_url, c.topic,
                      tp.name, tp.party
               FROM claims c JOIN tracked_politicians tp ON tp.id = c.opponent_id
               WHERE c.claim_type = 'position' AND c.stated_at >= ?
                 AND c.quote IS NOT NULL AND LENGTH(c.quote) > ?
                 AND tp.relationship_type NOT IN (?,?,?,?)
               ORDER BY c.salience DESC, c.stated_at DESC, c.id DESC LIMIT 1""",
            (cutoff, _MIN_QUOTE_LEN, *_AUDIENCE),
        ).fetchone()
        if r:
            card = _person_card(r["name"], r["party"])
            card.update({
                "quote": r["quote"],                   # VERBATIM
                "topic": r["topic"],
                "source_url": r["source_url"],
                "source_domain": _domain_from_url(r["source_url"]),
                "date": (r["stated_at"] or "")[:10],
            })
            return card
    return None


_C_TENSIONS_MAX = 3


def _fresh_tensions(
    tensions: list[dict[str, Any]],
    limit: int,
    exclude: Optional[dict[str, Any]] = None,
    today: Optional[date] = None,
) -> list[dict[str, Any]]:
    """Svaigās spriedzes <14d no jau nofetčotā saraksta (DESC pēc created_at)."""
    cutoff = ((today or today_lv()) - timedelta(days=_FRESH_DAYS)).isoformat()
    out: list[dict[str, Any]] = []
    for t in tensions:
        if t is exclude:
            continue
        if (t.get("created_at") or "")[:10] >= cutoff:
            out.append(t)
            if len(out) == limit:
                break
    return out


def assemble_focus(
    hot: Optional[dict[str, Any]],
    contradictions: list[dict[str, Any]],
    tensions: list[dict[str, Any]],
    quote_of_day: Optional[dict[str, Any]],
    today: Optional[date] = None,
) -> dict[str, Any]:
    """B = pretruna(<14d) → spriedze(<14d) → citāts (viens vienums);
    C = steks: līdz _C_TENSIONS_MAX svaigas spriedzes (bez B dubļa) + citāts pēdējais.

    `contradictions` = orchestratora jau padotais enriched saraksts (satur
    detected_at; DESC). Citāts nekad nedublē A slota citātu (source_url).
    """
    cutoff = ((today or today_lv()) - timedelta(days=_FRESH_DAYS)).isoformat()
    fresh_c = next(
        (c for c in contradictions if (c.get("detected_at") or "")[:10] >= cutoff), None
    )
    used_urls = {q.get("source_url") for q in (hot or {}).get("quotes", [])}
    qod = quote_of_day if (quote_of_day and quote_of_day.get("source_url") not in used_urls) else None

    slot_b = None
    b_tension = None
    if fresh_c:
        slot_b = {"kind": "contradiction", "item": fresh_c}
    else:
        b_candidates = _fresh_tensions(tensions, 1, today=today)
        if b_candidates:
            b_tension = b_candidates[0]
            slot_b = {"kind": "tension", "item": b_tension}
        elif qod:
            slot_b, qod = {"kind": "quote", "item": qod}, None

    slot_c_items = [
        {"kind": "tension", "item": t}
        for t in _fresh_tensions(tensions, _C_TENSIONS_MAX, exclude=b_tension, today=today)
    ]
    if qod:
        slot_c_items.append({"kind": "quote", "item": qod})
    return {"hot": hot, "slot_b": slot_b, "slot_c_items": slot_c_items}


def _focus_used_urls(focus: Optional[dict[str, Any]]) -> set:
    """source_url kopa, ko kompozīts jau rāda (karstās tēmas citāti + citātu sloti).

    NB: lasa assemble_focus atgriežamo slot-formu (hot/slot_b/slot_c_items) —
    mainot focus struktūru, šī hero-dedup funkcija JĀPIELĀGO līdzi (07-07 mācība).
    """
    focus = focus or {}
    urls = {q.get("source_url") for q in ((focus.get("hot") or {}).get("quotes") or [])}
    for slot in [focus.get("slot_b"), *(focus.get("slot_c_items") or [])]:
        if slot and slot.get("kind") == "quote":
            urls.add(slot["item"].get("source_url"))
    urls.discard(None)
    return urls


def _top_positions(
    db: sqlite3.Connection,
    exclude_urls: set,
    limit: int,
    today: Optional[date] = None,
) -> list[dict[str, Any]]:
    """Spilgtākās 7d pozīcijas ar citātu — viena uz politiķi, bez kompozīta dubļiem."""
    cutoff = ((today or today_lv()) - timedelta(days=7)).isoformat()
    rows = db.execute(
        """SELECT c.opponent_id, c.quote, c.topic, c.stated_at, c.source_url,
                  tp.name, tp.party
           FROM claims c JOIN tracked_politicians tp ON tp.id = c.opponent_id
           WHERE c.claim_type = 'position' AND c.stated_at >= ?
             AND c.quote IS NOT NULL AND LENGTH(c.quote) > ?
             AND tp.relationship_type NOT IN (?,?,?,?)
           ORDER BY c.salience DESC, c.stated_at DESC, c.id DESC""",
        (cutoff, _MIN_QUOTE_LEN, *_AUDIENCE),
    ).fetchall()
    out, seen = [], set()
    for r in rows:
        if r["opponent_id"] in seen or r["source_url"] in exclude_urls:
            continue
        seen.add(r["opponent_id"])
        card = _person_card(r["name"], r["party"])
        card.update({
            "quote": r["quote"],                       # VERBATIM
            "topic": r["topic"],
            "source_url": r["source_url"],
            "source_domain": _domain_from_url(r["source_url"]),
            "date": (r["stated_at"] or "")[:10],
        })
        out.append(card)
        if len(out) == limit:
            break
    return out


def _hero_votes(votes: list[dict[str, Any]], limit: int = 2) -> list[dict[str, Any]]:
    """Jaunākie izceļamie balsojumi: ar rezultātu un balsīm, dedup pēc summary.

    Bez svaiguma loga — Saeimai ir brīvlaiki; datums kartītē vienmēr redzams.
    0/0/0 rindas ir procedurālas reģistrācijas, ne balsojumi. Summary-dedup ir
    tikai displeja atlase (jaunākais uzvar) — izlaistie balsojumi paliek
    balsojumi.html sarakstā, tas NAV datu zudums.
    """
    out, seen = [], set()
    for v in votes:  # saraksts jau DESC pēc vote_date, vote_time
        total = ((v.get("total_par") or 0) + (v.get("total_pret") or 0)
                 + (v.get("total_atturas") or 0))
        title = (v.get("summary") or v.get("motif") or "").strip()
        if not v.get("result") or total == 0 or not title or title in seen:
            continue
        seen.add(title)
        out.append({
            "id": v["id"],
            "date": str(v.get("vote_date") or "")[:10],
            "title": title,
            "par": v.get("total_par") or 0,
            "pret": v.get("total_pret") or 0,
            "atturas": v.get("total_atturas") or 0,
            "result": v.get("result"),
        })
        if len(out) == limit:
            break
    return out


def hero_feed(
    db: sqlite3.Connection,
    hero_cards: list[dict[str, Any]],
    votes: list[dict[str, Any]],
    focus: dict[str, Any],
    today: Optional[date] = None,
) -> list[dict[str, Any]]:
    """Hero karuseļa jauktais saturs (spec 2026-07-07): ≤6 {kind, item} kartītes.

    Svaigās pretrunas (<_FRESH_DAYS) līdz 2; ja svaigu nav — 1 jaunākā kā
    enkurs. Pozīcijas nedublē kompozīta citātus. Round-robin mija sākas ar
    pretrunu; viena veida kartītes blakus nonāk tikai atlikumā.
    """
    cutoff = ((today or today_lv()) - timedelta(days=_FRESH_DAYS)).isoformat()
    fresh = [c for c in hero_cards if (c.get("detected_at") or "")[:10] >= cutoff]
    cons = fresh[:2] if fresh else hero_cards[:1]
    vote_items = _hero_votes(votes)
    pos_limit = min(3, 6 - len(cons) - len(vote_items))
    positions = _top_positions(db, _focus_used_urls(focus), pos_limit, today=today)
    queues = [("contradiction", list(cons)), ("position", positions), ("vote", vote_items)]
    items: list[dict[str, Any]] = []
    while len(items) < 6 and any(q for _, q in queues):
        for kind, q in queues:
            if q and len(items) < 6:
                items.append({"kind": kind, "item": q.pop(0)})
    return items
