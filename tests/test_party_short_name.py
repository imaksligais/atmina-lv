"""Party short-name resolution has ONE truth source: ``parties.short_name``.

Before 2026-09-05 three hard-coded maps answered this question and they
disagreed: the site rendered ``ST`` for Stabilitātei! while the daily brief
and the weekly movers chart rendered ``S!`` for the same faction, and each
map knew a different partial subset of the table (11 / 10 / 8 entries out of
19 parties). CLAUDE.md T6 second corollary makes ``parties.short_name`` the
canonical label form, so all three now route through
``src.coalition.lookup_party_short_name()``.

What is locked here:

1. Every key of the offline fallback map resolves — either the DB answers it
   or the fallback does. A key that resolves nowhere is a dead entry.
2. The three call sites agree with each other AND with ``short_name`` for
   every row of ``parties``.
3. An unknown label still gets each site's own display fallback (initials /
   pass-through / 5-char truncation) — the resolver must not guess.
"""

import sqlite3

import pytest

from src.briefs import _short_party as brief_short_party
from src.coalition import (
    FALLBACK_PARTY_SHORT_NAMES,
    clear_party_short_name_cache,
    get_coalition_map,
    lookup_party_short_name,
    party_short_name,
)
from src.db import DB_PATH
from src.graphics.weekly_chart import _short_party as chart_short_party
from src.render._common import _party_short_name as site_short_name

# Fallback keys that the live `parties` table does NOT carry. Pinned so that
# adding one of these parties to the DB (or dropping a party) surfaces here
# instead of silently changing a published label.
FALLBACK_ONLY_EXPECTED = {
    "Bezpartejisks",          # not a party — the "no party" display label
    "Latvijas Krievu savienība",
    "Saskaņa",                # DB carries 'Saskaņas Centrs' / 'SC'
    "Suverenā vara",          # DB carries 'Suverēnā vara/Jaunlatvieši' / 'SV-AJ'
}


@pytest.fixture
def parties_db():
    """Hermetic two-party `parties` table (the shape the resolver reads)."""
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute(
        "CREATE TABLE parties (name TEXT, short_name TEXT, coalition_status TEXT)"
    )
    db.executemany(
        "INSERT INTO parties (name, short_name, coalition_status) VALUES (?,?,?)",
        [("Stabilitātei!", "ST", "opposition"),
         ("Jaunā Vienotība", "JV", "coalition")],
    )
    db.commit()
    yield db
    db.close()


def _live_parties():
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT name, short_name FROM parties WHERE short_name IS NOT NULL"
        ).fetchall()
        conn.close()
        return [(r["name"], r["short_name"]) for r in rows]
    except sqlite3.Error:
        return []


# --- 1. the offline fallback map is live ----------------------------------

def test_every_fallback_key_resolves():
    """No dead entries: each key answers via the DB or via the fallback."""
    unresolved = [k for k in FALLBACK_PARTY_SHORT_NAMES
                  if lookup_party_short_name(k) is None]
    assert not unresolved, f"fallback keys resolving nowhere: {unresolved}"
    assert len(FALLBACK_PARTY_SHORT_NAMES) == 14  # denominator, not a vibe


def test_fallback_keys_absent_from_parties_are_the_pinned_set():
    """Which keys the table cannot answer is a fact worth pinning."""
    live = _live_parties()
    if not live:
        pytest.skip("live DB unavailable")
    known = {n for n, _ in live} | {s for _, s in live}
    fallback_only = {k for k in FALLBACK_PARTY_SHORT_NAMES if k not in known}
    assert fallback_only == FALLBACK_ONLY_EXPECTED


def test_fallback_keys_present_in_parties_resolve_via_coalition_map():
    """Plan 4.4: every map key that the table carries is a real party row."""
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        coalition_map = get_coalition_map(conn)
        conn.close()
    except sqlite3.Error:
        pytest.skip("live DB unavailable")
    if not coalition_map:
        pytest.skip("live DB unavailable")
    checked = [k for k in FALLBACK_PARTY_SHORT_NAMES if k not in FALLBACK_ONLY_EXPECTED]
    assert len(checked) == 10, "denominator drifted — re-check the pinned set"
    for key in checked:
        assert key in coalition_map, f"{key!r} in fallback map but not in parties"


# --- 2. the table wins, and the three sites agree -------------------------

def test_db_wins_over_fallback(parties_db):
    """`Stabilitātei!` is the case the three old maps disagreed on."""
    assert lookup_party_short_name("Stabilitātei!", parties_db) == "ST"
    assert party_short_name("Stabilitātei!", parties_db) == "ST"


def test_short_name_resolves_to_itself(parties_db):
    assert lookup_party_short_name("ST", parties_db) == "ST"
    assert lookup_party_short_name("JV", parties_db) == "JV"


def test_unknown_returns_none_and_passthrough(parties_db):
    assert lookup_party_short_name("Nezināma partija", parties_db) is None
    assert party_short_name("Nezināma partija", parties_db) == "Nezināma partija"
    assert lookup_party_short_name(None, parties_db) is None
    assert lookup_party_short_name("", parties_db) is None


def test_three_call_sites_agree_for_every_party():
    """site == brief == chart == parties.short_name, for every row."""
    live = _live_parties()
    if not live:
        pytest.skip("live DB unavailable")
    assert len(live) >= 10, f"suspiciously thin parties table: {len(live)}"
    clear_party_short_name_cache()
    diverged = []
    for name, short in live:
        got = (site_short_name(name), brief_short_party(name), chart_short_party(name))
        if got != (short, short, short):
            diverged.append((name, short, got))
        # the already-short form must round-trip too (tracked_politicians.party
        # stores 'MMN' and 'JKP' as short forms — CLAUDE.md § Coalition)
        got_short = (site_short_name(short), brief_short_party(short),
                     chart_short_party(short))
        if got_short != (short, short, short):
            diverged.append((short, short, got_short))
    assert not diverged, f"party label disagreement (site, brief, chart): {diverged}"


# --- 3. each site keeps its own display fallback ---------------------------

def test_site_falls_back_to_initials():
    assert site_short_name("Alfa Beta Gamma Delta") == "ABG"
    assert site_short_name("Nekad Nebijusi") == "NN"


def test_brief_falls_back_to_passthrough():
    assert brief_short_party("Nekad Nebijusi") == "Nekad Nebijusi"
    assert brief_short_party(None) == ""
    assert brief_short_party("") == ""


def test_chart_falls_back_to_truncation():
    assert chart_short_party("Nekad Nebijusi") == "Nekad"
    assert chart_short_party(None) == "—"


def test_resolver_survives_a_missing_parties_table():
    """A DB without `parties` must not raise — the fallback still answers."""
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    try:
        assert lookup_party_short_name("Nezināma", db) is None
        assert lookup_party_short_name("Stabilitātei!", db) == "ST"  # fallback
    finally:
        db.close()
