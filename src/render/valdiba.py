"""Render valdiba.html — Ministru kabinets un katra ministra pozīcijas viņa nozarē.

Ministrus nolasa no ``tracked_politicians.role`` (pašreizējās lomas daļas,
``src.profile_kind.active_role_chunks``), nevis no roku saraksta: pēc
``scripts/government_switch.py --apply`` lapa seko DB. Kodā glabājas tikai
ministriju saraksts un katras ministrijas tēmas (35 kanoniskās grupas,
``src/topic_map.py``). Ministrija, kuras ministrs nav mūsu datos, paliek
sarakstā ar paskaidrojumu — klusi nepazūd.

Augšā — jaunākais pieņemtais uzticības balsojums Ministru kabinetam
(``saeima_votes``, tas pats motīvs, ko lieto ``scripts/seed_coalition_periods.py``).

Sub-page boundary: imports only from ``src.render._common``, ``src.profile_kind``
and stdlib.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from src.profile_kind import (
    _NOT_MINISTER_MARKERS,
    active_role_chunks,
    current_term_vote_counts,
    derive_profile_kind,
)
from src.render._common import PUBLIC_PROFILE_WHERE, _party_short_name, _render_page, _slugify

# Publicēšanas slēdzis (2026-11-17): False = lapa netiek ne pilnā build, ne sitemap;
# priekšskatījums tikai ar `--only=valdiba --output=<.scratch/...>`. Pārslēdz uz
# True tikai pēc operatora apstiprinājuma. Ieslēgts 2026-11-18 (operatora «jā»).
VALDIBA_PUBLISHED = True

# Tas pats motīvs, ko scripts/seed_coalition_periods.py::CONFIDENCE_MOTIF.
CONFIDENCE_MOTIF = "Uzticības izteikšana Ministru kabinetam%"

POSITIONS_SHOWN = 5

# (amata nosaukums lapā, role apakšvirkne, nozares tēmas; None = visas tēmas).
# Secība = Ministru kabineta ierastā secība (premjers, tad ministrijas).
MINISTRIES: list[tuple[str, str, tuple[str, ...] | None]] = [
    ("Ministru prezidents", "ministru prezident", None),
    ("Aizsardzības ministrija", "aizsardzības ministr", ("Aizsardzība un drošība", "Droni")),
    ("Ārlietu ministrija", "ārlietu ministr", ("Ārpolitika", "ES politika", "Ukraina un Krievija")),
    ("Ekonomikas ministrija", "ekonomikas ministr",
     ("Ekonomika un uzņēmējdarbība", "Valsts kapitālsabiedrības")),
    ("Finanšu ministrija", "finanšu ministr", ("Budžets un finanses",)),
    ("Iekšlietu ministrija", "iekšlietu ministr", ("Imigrācija", "Aizsardzība un drošība")),
    ("Izglītības un zinātnes ministrija", "izglītības un zinātnes ministr", ("Izglītība", "Sports")),
    ("Klimata un enerģētikas ministrija", "klimata un enerģētikas ministr",
     ("Klimats", "Degviela un enerģētika", "Vide")),
    ("Kultūras ministrija", "kultūras ministr",
     ("Kultūra", "Valodu politika", "Sabiedriskie mediji")),
    ("Labklājības ministrija", "labklājības ministr", ("Sociālā politika", "Pensijas")),
    ("Satiksmes ministrija", "satiksmes ministr", ("Transports", "Rail Baltica", "airBaltic")),
    ("Tieslietu ministrija", "tieslietu ministr", ("Tieslietas", "Korupcija un KNAB")),
    ("Veselības ministrija", "veselības ministr", ("Veselības aprūpe",)),
    ("Viedās administrācijas un reģionālās attīstības ministrija",
     "viedās administrācijas un reģionālās attīstības ministr",
     ("Pašvaldības", "Valsts pārvalde", "Digitālā politika", "Pilsētvide")),
    ("Zemkopības ministrija", "zemkopības ministr", ("Lauksaimniecība", "Mežsaimniecība")),
]


def _holds(role: str | None, needle: str) -> bool:
    """Vai pašreizējā loma ir ŠIS amats (ne biedrs, ne padomnieks, ne bijušais)."""
    for chunk in active_role_chunks(role):
        if needle not in chunk:
            continue
        if any(m in chunk for m in _NOT_MINISTER_MARKERS) or "biedr" in chunk:
            continue
        return True
    return False


def _confidence_vote(db: sqlite3.Connection) -> dict[str, Any] | None:
    row = db.execute(
        "SELECT vote_date, total_par, total_pret, total_atturas, url FROM saeima_votes "
        "WHERE motif LIKE ? AND result = 'Pieņemts' "
        "ORDER BY vote_date DESC, vote_time DESC LIMIT 1",
        (CONFIDENCE_MOTIF,),
    ).fetchone()
    return dict(row) if row else None


def _positions(
    db: sqlite3.Connection, pid: int, topics: tuple[str, ...] | None
) -> tuple[int, list[dict[str, Any]]]:
    """(nozares pozīciju skaits, jaunākās POSITIONS_SHOWN) — tikai ``claim_type='position'``."""
    topic_sql = ""
    params: list[Any] = [pid]
    if topics:
        topic_sql = f" AND topic IN ({','.join('?' * len(topics))})"
        params += list(topics)
    total = db.execute(
        "SELECT COUNT(*) FROM claims WHERE opponent_id = ? AND claim_type = 'position'"
        + topic_sql,
        params,
    ).fetchone()[0]
    rows = db.execute(
        "SELECT stance, topic, stated_at, source_url FROM claims "
        "WHERE opponent_id = ? AND claim_type = 'position'" + topic_sql
        + " ORDER BY stated_at DESC, salience DESC, id DESC LIMIT ?",
        [*params, POSITIONS_SHOWN],
    ).fetchall()
    return total, [dict(r) for r in rows]


def _member(db: sqlite3.Connection, p: sqlite3.Row, topics: tuple[str, ...] | None) -> dict[str, Any]:
    total, latest = _positions(db, p["id"], topics)
    return {
        "name": p["name"],
        "slug": _slugify(p["name"]),
        "party_short": _party_short_name(p["party"], db) if p["party"] else "",
        "count": total,
        "positions": latest,
    }


def _other_post(role: str | None) -> str:
    """Pašreizējā amata daļa ar «ministr» (oriģinālais reģistrs) — citu locekļu rindai."""
    for chunk in (role or "").split(","):
        c = chunk.strip()
        if c.lower() in active_role_chunks(role) and "ministr" in c.lower():
            return c[:1].upper() + c[1:]
    return (role or "").strip()


def fetch_cabinet(db: sqlite3.Connection) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """(ministrijas, citi valdības locekļi).

    Ministrijām — viena rinda katrai; ``ministers`` tukšs = mūsu datos neviena.
    Citi — ministri pēc ``derive_profile_kind``, kas neatbilst nevienai
    ministrijai (premjera biedrs, ministrs bez portfeļa), lai neviens valdības
    loceklis klusi nepazūd. Valsts kanceleja un Valsts prezidents nav valdība.
    """
    people = db.execute(
        f"SELECT id, name, party, role, relationship_type FROM tracked_politicians "
        f"WHERE {PUBLIC_PROFILE_WHERE}"
    ).fetchall()
    cabinet = []
    matched: set[int] = set()
    for post, needle, topics in MINISTRIES:
        holders = [p for p in people if _holds(p["role"], needle)]
        matched.update(p["id"] for p in holders)
        cabinet.append({
            "post": post,
            "anchor": _slugify(post),
            "topics": topics,
            "ministers": sorted((_member(db, p, topics) for p in holders), key=lambda m: m["name"]),
        })
    term_votes = current_term_vote_counts(db)
    others = []
    for p in people:
        if p["id"] in matched:
            continue
        role = (p["role"] or "").lower()
        if "valsts kanc" in role or "valsts prezident" in role:
            continue
        if derive_profile_kind(p["relationship_type"] or "", p["role"], term_votes.get(p["id"], 0)) != "minister":
            continue
        post = _other_post(p["role"])
        others.append({"post": post, "anchor": _slugify(f"{post}-{p['name']}"), "topics": None,
                       "ministers": [_member(db, p, None)]})
    others.sort(key=lambda r: (r["post"], r["ministers"][0]["name"]))
    return cabinet, others


def render_valdiba(env, db: sqlite3.Connection, atmina_dir: Path) -> None:
    """Emit ``atmina_dir/valdiba.html``."""
    cabinet, others = fetch_cabinet(db)
    _render_page(env, "valdiba.html.j2", atmina_dir / "valdiba.html", {
        "cabinet": cabinet,
        "others": others,
        "vote": _confidence_vote(db),
        "positions_shown": POSITIONS_SHOWN,
    })
