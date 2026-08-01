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
