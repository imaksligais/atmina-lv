"""Politician profile classification — drives role-aware tab dispatch.

Single source of truth for the ``profile_kind`` label that
``src/render/politicians.py`` reads to pick which tabs to render on a
given politician's profile page (deputy → 5 tabs, minister → 4 tabs,
journalist → 3 tabs etc.). Mirror of ``src/coalition.py``: small domain
module, ``Literal`` enum, single-row + batch helpers, rich docstring.

**Why not stored in DB.** ``profile_kind`` is derived from three signals
that already live in ``tracked_politicians`` (``relationship_type``,
``role``) and ``saeima_individual_votes`` (current-term vote count).
Computing at render time means a role rename or vote backfill flows
through on the next ``generate_public_site`` run with no migration.

**Distinct from ``relationship_type``.** ``relationship_type`` is a
per-politician tracking role (legacy MMN-centric origin, mostly
``'tracked'`` post-2026-04-11 migration). ``profile_kind`` is a
public-facing UI category that splits the dominant ``'tracked'`` bucket
into deputy / minister / mep / regional / politician based on the
``role`` text. Do NOT use ``relationship_type`` for tab dispatch.

**Distinct from ``_common._persona_category``.** That helper buckets
politicians for the Personas index (Deputāti / Žurnālisti / Amatpersonas
/ Citi). ``profile_kind`` is finer-grained (10 vs 5 categories) and
serves a different purpose (per-profile tab visibility, not list
filtering). They share inputs but the rule order differs because the
goals differ.
"""

from __future__ import annotations

import re
import sqlite3
from typing import Literal, Optional

ProfileKind = Literal[
    "deputy", "minister", "mep", "regional", "politician",
    "journalist", "analyst", "organization", "former", "inactive",
]

# Fallback labels for the role-chip when ``tracked_politicians.role`` is
# empty. Templates previously hard-coded ``'Politiķis'`` which surfaced on
# media/organization/journalist profiles (LETA, LTV Ziņas, IR žurnāls
# etc.), undermining the visual cue that distinguishes a politician from
# a third-party voice. Latvian noun gender stays masculine by lemma —
# the fallback only fires when no real role text exists, so an actual
# politician with a populated ``role`` ("Saeimas deputāte", "ministre")
# is unaffected.
PROFILE_KIND_LABELS: dict[str, str] = {
    "deputy":       "Saeimas deputāts",
    "minister":     "Amatpersona",
    "mep":          "EP deputāts",
    "regional":     "Pašvaldības politiķis",
    "politician":   "Politiķis",
    "journalist":   "Žurnālists",
    "analyst":      "Analītiķis",
    "organization": "Organizācija",
    "former":       "Bijušais politiķis",
    "inactive":     "Neaktīvs",
}


def profile_kind_label(kind: str) -> str:
    """Return the Latvian fallback label for a profile_kind.

    Returns ``"Politiķis"`` for unknown kinds — matches the legacy
    template fallback so templates can switch to ``profile_kind_label``
    without changing rendered output for the default branch.
    """
    return PROFILE_KIND_LABELS.get(kind, "Politiķis")

# 14. Saeima convened 2022-11-01. ``current_term_vote_count`` for
# ``derive_profile_kind`` rule 8 is restricted to votes on or after this
# date so a politician's pre-2022 voting history doesn't keep them
# classified as a "deputy" after they leave the chamber.
CURRENT_TERM_START = "2022-11-01"

# Filters chunks whose first word is a past participle of ``būt`` —
# i.e., ``bijis`` / ``bijusi`` / ``bijusī`` / ``bijušais`` / ``bijušā``
# etc. Any role chunk beginning with ``biju`` + ``s``/``š`` is a former-
# role marker; all other Latvian role keywords start differently. The
# trailing pattern is intentionally permissive (no ``[aīi]\b``) because
# narrower variants miss whole-role forms like ``Bijušais Rēzeknes
# mērs`` — ``bijuša`` matches but ``i`` after ``a`` is a word char so
# ``\b`` fails, and rule 7 (``mērs``) then mis-classifies a former mayor
# as ``regional``. Filtering the whole chunk lets rule 9 catch them as
# ``former`` instead.
_BIJUS_PREFIX_RE = re.compile(r"^biju[sš]")


def derive_profile_kind(
    relationship_type: str,
    role: Optional[str],
    current_term_vote_count: int,
) -> ProfileKind:
    """Classify a tracked politician for profile tab dispatch.

    First-match-wins rule order — deliberately ordered so that an active
    deputy who is also a former minister classifies as ``deputy`` (rule
    8) rather than ``minister`` (rule 5), reflecting their current
    function. The chunk-split + bijuš-filter on ``role`` avoids false
    positives from comma-separated past roles like
    ``"Saeimas deputāte, bijusī Izglītības un zinātnes ministre"``.

    Returns ``"politician"`` as a safe fallback when no rule matches.
    """
    if relationship_type == "inactive":
        return "inactive"
    if relationship_type == "journalist":
        return "journalist"
    if relationship_type == "organization":
        return "organization"
    if relationship_type == "neutral":
        return "analyst"

    chunks = [c.strip() for c in (role or "").split(",")]
    active_chunks = [c for c in chunks if not _BIJUS_PREFIX_RE.match(c.lower())]
    active_role = ", ".join(active_chunks).lower()

    if any(t in active_role for t in ("ministr", "valsts kanc", "valsts prezident")):
        return "minister"
    # ``\bep\b`` (word-anchored) catches both ``EP deputāts`` and EP leadership
    # roles like ``EP viceprezidents`` / ``EP prezidente`` / ``EP koordinators``
    # — substring ``ep deputāt`` would miss the latter and mis-classify a
    # vice-president (Roberts Zīle) as ``politician``.
    if re.search(r"\bep\b", active_role) or "eiropas parlament" in active_role:
        return "mep"
    if any(t in active_role for t in ("mērs", "vicemērs", "domes")):
        return "regional"

    if current_term_vote_count > 0:
        return "deputy"

    if "bijuš" in (role or "").lower():
        return "former"

    return "politician"


def get_profile_kind_map(db: sqlite3.Connection) -> dict[int, ProfileKind]:
    """Return ``{politician_id: profile_kind}`` for every tracked politician.

    Single batched vote-count query (one ``GROUP BY politician_id`` over
    ``saeima_individual_votes``) to keep this O(1) round-trips regardless
    of politician count. Called once per ``generate_public_site`` run by
    ``render_politicians``.
    """
    tracked_rows = db.execute(
        "SELECT id, relationship_type, role FROM tracked_politicians"
    ).fetchall()
    vote_rows = db.execute(
        "SELECT siv.politician_id AS pid, COUNT(*) AS c "
        "FROM saeima_individual_votes siv "
        "JOIN saeima_votes sv ON siv.vote_id = sv.id "
        "WHERE sv.vote_date >= ? "
        "GROUP BY siv.politician_id",
        (CURRENT_TERM_START,),
    ).fetchall()
    votes_by_pid = {r["pid"]: r["c"] for r in vote_rows}

    result: dict[int, ProfileKind] = {}
    for r in tracked_rows:
        result[r["id"]] = derive_profile_kind(
            r["relationship_type"] or "",
            r["role"],
            votes_by_pid.get(r["id"], 0),
        )
    return result
