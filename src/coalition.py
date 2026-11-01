"""Party-level coalition/opposition mapping.

Single source of truth for TODAY's coalition: the ``parties`` table
(``coalition_status`` column), which is also what the ``partijas`` template reads. This
module is a thin facade — it does NOT hardcode any party list. If the
government changes, update the DB, not this file.

**Temporal semantics.** ``parties.coalition_status`` is a CURRENT
snapshot, not a time-versioned record. That is right for every surface that
speaks about TODAY (party pages, personas, briefs — briefs are frozen text in
``context_notes``, so they are never reclassified retroactively).

The ONE surface that speaks about the past is the vote card on the balsojumi
page: «Koalīcija»/«Opozīcija» there must be the government in office when the
vote was cast. That comes from the ``coalition_periods`` table (seeded from the
cabinet confidence votes by ``scripts/seed_coalition_periods.py``) through
:func:`coalition_periods` + :func:`coalition_at`, never from
``coalition_status`` (plan 2026-10-16-koalicija-balsojuma-diena.md). The
newest period must agree with ``coalition_status`` — audit check 24.

Distinct from ``tracked_politicians.relationship_type`` — that field is
a per-politician tracking role inherited from the platform's MMN-centric
origin. As of 2026-04-11 all active-row legacy values have been
migrated to 'tracked'. Do NOT use relationship_type for government
membership; always use ``party_status()`` or ``get_coalition_map()``
here instead.
"""

import sqlite3
from typing import Literal, NamedTuple, Optional

PartyStatus = Literal["coalition", "opposition", "not_in_saeima", "other"]

# Offline fallback ONLY — the union of the three hard-coded maps that lived in
# src/render/_common.py, src/briefs.py and src/graphics/weekly_chart.py before
# 2026-09-05 (plan 4.4 / audit § 3.3). It is consulted solely for names that
# `parties` does not carry; the table always wins. Where the three old maps
# disagreed ("Stabilitātei!" → "ST" vs "S!") the DB value ("ST", CLAUDE.md T6
# second corollary: the canonical label form IS `parties.short_name`) is kept.
# Do not grow this map — add the party to `parties` instead.
FALLBACK_PARTY_SHORT_NAMES: dict[str, str] = {
    "Apvienotais saraksts": "AS",
    "Austošā Saule Latvijai": "ASL",
    "Bezpartejisks": "Bezp.",
    "Jaunā Vienotība": "JV",
    "Latvija Pirmajā Vietā": "LPV",
    "Latvijas Krievu savienība": "LKS",
    "Latvijas attīstībai": "LA",
    "MMN": "MMN",
    "Nacionālā apvienība": "NA",
    "Progresīvie": "PRO",
    "Saskaņa": "SAS",
    "Stabilitātei!": "ST",
    "Suverenā vara": "SV",
    "Zaļo un Zemnieku savienība": "ZZS",
}

# {db_path: {name_or_short_name: short_name}}. The resolver is called once per
# rendered row (thousands of times in a full render), so a per-call get_db()
# is not affordable. Keyed on the resolved DB path so a test that monkeypatches
# src.db.DB_PATH gets its own entry.
_SHORT_NAME_CACHE: dict[str, dict[str, str]] = {}
# {db_path: {name_or_short_name: color}} — same keying, same reason.
_COLOR_CACHE: dict[str, dict[str, str]] = {}


def get_coalition_map(db) -> dict[str, str]:
    """Return {party_name_or_short_name: coalition_status}.

    Keyed by both full name and short_name so callers can match against
    either form. ``tracked_politicians.party`` historically stores the
    full name for most parties but 'MMN' for Mēs mainām noteikumus —
    this mapping handles both without requiring a data migration.
    """
    result: dict[str, str] = {}
    rows = db.execute(
        "SELECT name, short_name, coalition_status FROM parties"
    ).fetchall()
    for r in rows:
        status = r["coalition_status"] or "other"
        if r["name"]:
            result[r["name"]] = status
        if r["short_name"]:
            result[r["short_name"]] = status
    return result


class CoalitionPeriod(NamedTuple):
    """One government: in office from ``(valid_from_date, valid_from_time)``
    (LV, the confidence vote's ``saeima_votes.vote_date``/``vote_time``) until
    the next period starts. ``factions`` = canonical ``siv.faction`` labels."""
    valid_from_date: str
    valid_from_time: str
    factions: frozenset


def coalition_periods(db) -> list[CoalitionPeriod]:
    """All ``coalition_periods`` rows, oldest first. No table → ``[]`` (a DB
    built before the 2026-10-16 migration): the caller then names no coalition."""
    try:
        rows = db.execute(
            "SELECT valid_from_date, valid_from_time, factions FROM coalition_periods "
            "ORDER BY valid_from_date, valid_from_time"
        ).fetchall()
    except sqlite3.OperationalError:
        return []
    return [
        CoalitionPeriod(r[0], r[1] or "",
                        frozenset(f.strip() for f in (r[2] or "").split(",") if f.strip()))
        for r in rows
    ]


def coalition_period_index(
    periods: list[CoalitionPeriod], vote_date: str, vote_time: str
) -> Optional[int]:
    """Index of the period in force at ``(vote_date, vote_time)``, or ``None``
    before the first one. A vote belongs to the new period when
    ``(vote_date, vote_time) >= (valid_from_date, valid_from_time)`` — so the
    confidence vote itself already counts under the new government, and a
    vote earlier that same day under the old one. ``periods`` oldest first."""
    key = (str(vote_date or "")[:10], vote_time or "")
    found = None
    for i, p in enumerate(periods):
        if key >= (p.valid_from_date, p.valid_from_time):
            found = i
        else:
            break
    return found


def coalition_at(
    periods: list[CoalitionPeriod], vote_date: str, vote_time: str
) -> Optional[frozenset]:
    """Coalition faction labels in office at ``(vote_date, vote_time)``;
    ``None`` before the first known period (we do not name one)."""
    i = coalition_period_index(periods, vote_date, vote_time)
    return None if i is None else periods[i].factions


def party_status(party: Optional[str], db=None) -> PartyStatus:
    """Return coalition/opposition status for a party name.

    ``"other"`` covers bezpartejiski, neklasificēti, and unknown parties.
    Politicians with ``party IS NULL`` (journalists, influencers, neutral
    analysts) also resolve to ``"other"``.

    For batch usage over many rows, prefer ``get_coalition_map()`` once
    and look up directly to avoid repeated DB calls.
    """
    if not party:
        return "other"
    if db is None:
        from src.db import get_db
        db = get_db()
    coalition_map = get_coalition_map(db)
    return coalition_map.get(party, "other")  # type: ignore[return-value]


def _build_short_name_map(db) -> dict[str, str]:
    """{full name: short_name} ∪ {short_name: short_name} from ``parties``."""
    result: dict[str, str] = {}
    rows = db.execute("SELECT name, short_name FROM parties").fetchall()
    for r in rows:
        short = r["short_name"]
        if not short:
            continue
        if r["name"]:
            result[r["name"]] = short
        result[short] = short
    return result


def clear_party_short_name_cache() -> None:
    """Drop the cached ``parties`` short-name map (tests / after a DB write)."""
    _SHORT_NAME_CACHE.clear()


def _short_name_map(db=None) -> dict[str, str]:
    if db is not None:
        try:
            return _build_short_name_map(db)
        except Exception:
            return {}
    from src import db as _db_mod
    key = str(_db_mod.DB_PATH)
    cached = _SHORT_NAME_CACHE.get(key)
    if cached is None:
        try:
            conn = _db_mod.get_db()
            try:
                cached = _build_short_name_map(conn)
            finally:
                conn.close()
        except Exception:
            # No DB / no `parties` table / 0-byte file — the offline fallback
            # map still answers. Deliberately silent (nothing is logged): this
            # runs inside render loops and a per-row warning would be noise.
            cached = {}
        _SHORT_NAME_CACHE[key] = cached
    return cached


def lookup_party_short_name(party: Optional[str], db=None) -> Optional[str]:
    """Resolve a party label to its canonical ``parties.short_name``.

    Accepts either the full name ('Stabilitātei!') or an already-short form
    ('ST', 'MMN', 'JKP') and returns the ``short_name``. Returns ``None`` when
    the label resolves neither in the table nor in
    ``FALLBACK_PARTY_SHORT_NAMES`` — the caller then applies its own display
    fallback (initials, pass-through, truncation), which is why this returns
    an Optional rather than guessing.

    The ``parties`` table is the truth source (CLAUDE.md T6 second corollary);
    the offline map only covers labels absent from it.
    """
    if not party:
        return None
    table = _short_name_map(db)
    if party in table:
        return table[party]
    return FALLBACK_PARTY_SHORT_NAMES.get(party)


def _build_color_map(db) -> dict[str, str]:
    """{full name: color} ∪ {short_name: color} from ``parties``."""
    result: dict[str, str] = {}
    rows = db.execute("SELECT name, short_name, color FROM parties").fetchall()
    for r in rows:
        color = r["color"]
        if not color:
            continue
        if r["name"]:
            result[r["name"]] = color
        if r["short_name"]:
            result[r["short_name"]] = color
    return result


def clear_party_color_cache() -> None:
    """Drop the cached ``parties`` colour map (tests / after a DB write)."""
    _COLOR_CACHE.clear()


def party_color_map(db=None) -> dict[str, str]:
    """Return {party_name_or_short_name: ``parties.color``}.

    The ONE source of party colours for every rendered surface (until
    2026-10-11 a hard-coded ``PARTY_COLORS`` dict in
    ``src/render/_common/constants.py`` disagreed with this column on 8 of 9
    parties). Keyed by both forms, like :func:`get_coalition_map`, because
    ``tracked_politicians.party`` stores 'MMN'/'JKP' short. Parties with a
    NULL colour are absent — the caller applies its own display fallback.

    Render code passes its ``db`` (fetch once per function, then ``.get()``
    per row); ``db=None`` reads ``src.db.DB_PATH`` once and caches. There is
    deliberately NO offline colour map: a second palette is the bug this
    replaced. No DB → ``{}`` (silent, as :func:`_short_name_map`).
    """
    if db is not None:
        try:
            return _build_color_map(db)
        except Exception:
            return {}
    from src import db as _db_mod
    key = str(_db_mod.DB_PATH)
    cached = _COLOR_CACHE.get(key)
    if cached is None:
        try:
            conn = _db_mod.get_db()
            try:
                cached = _build_color_map(conn)
            finally:
                conn.close()
        except Exception:
            cached = {}
        _COLOR_CACHE[key] = cached
    return cached


def party_short_name(party: str, db=None) -> str:
    """Canonical short name for a party label, input unchanged if unknown.

    Thin wrapper over :func:`lookup_party_short_name` for callers whose
    display fallback is simply "show the name as given" (the daily/weekly
    brief). Callers with a different fallback should use the ``lookup_``
    variant and branch on ``None``.
    """
    return lookup_party_short_name(party, db) or (party or "")
