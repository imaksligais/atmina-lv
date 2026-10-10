"""Party-level coalition/opposition mapping.

Single source of truth: the ``parties`` table (``coalition_status``
column), which is also what the ``partijas`` template reads. This
module is a thin facade — it does NOT hardcode any party list. If the
government changes, update the DB, not this file.

**Temporal semantics.** ``parties.coalition_status`` is a CURRENT
snapshot, not a time-versioned record. This is safe because:

- Daily briefs are frozen text stored in ``context_notes`` at creation
  time — they are not regenerated from live data, so retroactive
  reclassification cannot happen.
- The ``partijas`` HTML page renders the current coalition at build
  time, which is what the user wants.
- Per-politician profile pages aggregate claims but do not display
  coalition membership alongside historical positions.

If a future feature needs "was this party in the coalition on
date X?", introduce a ``coalition_history`` table with
``(party_name, status, valid_from, valid_to)`` and add a
``coalition_at(date, db)`` helper here. Until then, current snapshot
is sufficient.

Distinct from ``tracked_politicians.relationship_type`` — that field is
a per-politician tracking role inherited from the platform's MMN-centric
origin. As of 2026-04-11 all active-row legacy values have been
migrated to 'tracked'. Do NOT use relationship_type for government
membership; always use ``party_status()`` or ``get_coalition_map()``
here instead.
"""

from typing import Literal, Optional

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


def party_short_name(party: str, db=None) -> str:
    """Canonical short name for a party label, input unchanged if unknown.

    Thin wrapper over :func:`lookup_party_short_name` for callers whose
    display fallback is simply "show the name as given" (the daily/weekly
    brief). Callers with a different fallback should use the ``lookup_``
    variant and branch on ``None``.
    """
    return lookup_party_short_name(party, db) or (party or "")
