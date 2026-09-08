"""Coverage diagnostics — which tracked politicians lack a channel through
which positions/contradictions could ever surface. Read-only.

**Dark zone** = a politician whose Saeima votes ARE tracked but who has no
analyses, no first-party position claims, and no X feed. With no rhetoric
channel, a contradiction can never form for them — the votes sit in isolation.
This is the concrete P4 target list (audit 2026-06-08). See also
[wiki/operations/operacijas.md] retrofetch backlog P4.

Truth sources (CLAUDE.md schema invariants):
- votes      → saeima_individual_votes.politician_id
- analyses   → analyses.opponent_id
- positions  → claims.opponent_id WHERE claim_type='position'
- X feed     → social_accounts.opponent_id WHERE platform='twitter'
- active     → tracked_politicians.relationship_type != 'inactive'
"""

from __future__ import annotations

from src.db import get_db

_SELECT = "SELECT p.id, p.name, p.party FROM tracked_politicians p WHERE "
_ORDER = " ORDER BY p.name"
_ACTIVE = "p.relationship_type != 'inactive'"
_HAS_VOTES = "EXISTS (SELECT 1 FROM saeima_individual_votes iv WHERE iv.politician_id = p.id)"
_NO_ANALYSES = "NOT EXISTS (SELECT 1 FROM analyses a WHERE a.opponent_id = p.id)"
_NO_POSITION = "NOT EXISTS (SELECT 1 FROM claims cl WHERE cl.opponent_id = p.id AND cl.claim_type = 'position')"
_NO_X = "NOT EXISTS (SELECT 1 FROM social_accounts sa WHERE sa.opponent_id = p.id AND sa.platform = 'twitter')"
_MIN_POSITION = (
    "(SELECT COUNT(*) FROM claims cl WHERE cl.opponent_id = p.id "
    "AND cl.claim_type = 'position') >= 5"
)


def compute_coverage(db_path: str | None = None) -> dict:
    """Return coverage gap buckets, each a list of {id, name, party} dicts.

    Keys: ``dark_zone`` (votes ∧ no analyses ∧ no position ∧ no X),
    ``no_x_feed``, ``never_analyzed``, ``no_position_claims``. All restricted
    to active politicians, sorted by name.
    """
    db = get_db(db_path) if db_path else get_db()
    try:
        def _rows(where: str) -> list[dict]:
            return [dict(r) for r in db.execute(f"{_SELECT}{where}{_ORDER}").fetchall()]

        return {
            "dark_zone": _rows(f"{_ACTIVE} AND {_HAS_VOTES} AND {_NO_ANALYSES} AND {_NO_POSITION} AND {_NO_X}"),
            "no_x_feed": _rows(f"{_ACTIVE} AND {_NO_X}"),
            "never_analyzed": _rows(f"{_ACTIVE} AND {_NO_ANALYSES}"),
            "no_position_claims": _rows(f"{_ACTIVE} AND {_NO_POSITION}"),
        }
    finally:
        db.close()


_SECTIONS = [
    ("dark_zone", "Tumšā zona",
     "balsojumi izsekoti, bet 0 analyses + 0 position claim + 0 X feed → pretruna nevar rasties. P4 mērķis."),
    ("no_x_feed", "Bez X feed",
     "nav social_accounts twitter rindas — pievieno handle (feed_type=relay) vai retrofetch."),
    ("never_analyzed", "Nekad nav analizēti",
     "nav neviena analyses ieraksta."),
    ("no_position_claims", "Bez position claims",
     "nav neviena claim_type='position'."),
]


def format_coverage_report(cov: dict) -> str:
    """Human-readable markdown report for the operator console."""
    lines = ["# atmina pārklājuma atskaite", ""]
    for key, title, note in _SECTIONS:
        rows = cov.get(key, [])
        lines.append(f"## {title} ({len(rows)})")
        lines.append(f"_{note}_")
        for r in rows:
            lines.append(f"- id={r['id']} {r['name']} ({r['party'] or '—'})")
        lines.append("")
    return "\n".join(lines)


def format_coverage_summary(cov: dict) -> str:
    """One-line informational coverage summary for print_routine().

    Informational only — NOT a routine step. Dark-zone deputies are a standing
    P4 retrofetch backlog, never a daily done/missing signal.
    """
    dark = len(cov.get("dark_zone", []))
    no_x = len(cov.get("no_x_feed", []))
    return f"Pārklājums: {dark} tumšās zonas deputāti · {no_x} bez X feed"


def stale_pol_politicians(db_path: str | None = None, stale_days: int = 60) -> list[dict]:
    """Active politicians with >=5 position claims whose contradiction check has
    NEVER found anything OR is stale (latest find older than ``stale_days``).

    Proxy for "last deep-check": ``MAX(contradictions.detected_at)`` over the
    politician's rows — there is no per-politician check timestamp, so NULL
    (no contradiction ever found) counts as "never checked". This overcounts
    politicians that were checked but came back clean (deep-check yield is
    ~1/2700 pairs); treat the list as a coverage-hygiene candidate pool, not a
    precise "unchecked" set. Returns [{id, name, party}], sorted by name.
    """
    db = get_db(db_path) if db_path else get_db()
    try:
        window = f"-{int(stale_days)} days"  # int() guards the date() modifier
        where = (
            f"{_ACTIVE} AND {_MIN_POSITION} AND ("
            "NOT EXISTS (SELECT 1 FROM contradictions c WHERE c.opponent_id = p.id) "
            "OR (SELECT MAX(c.detected_at) FROM contradictions c "
            "WHERE c.opponent_id = p.id) < date('now', ?))"
        )
        sql = f"{_SELECT}{where}{_ORDER}"
        return [dict(r) for r in db.execute(sql, (window,)).fetchall()]
    finally:
        db.close()
