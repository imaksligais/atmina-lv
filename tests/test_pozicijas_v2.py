"""Tests for Pozīcijas V2 data helpers in src/generate.py."""

import sqlite3
from datetime import datetime, timedelta

from src.db import now_lv_dt
from src.generate import PARTY_COLORS, PZV1_TOPIC_COLORS, _confidence_tier, _fetch_claims, _fetch_pozicijas_metrics
from src.topic_map import TOPIC_GROUPS


def _build_test_db() -> sqlite3.Connection:
    """In-memory SQLite with minimal schema for Pozīcijas V2 tests.

    Creates tracked_politicians + claims tables mirroring the production
    schema subset these helpers read from. Does NOT need vector tables.
    """
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE tracked_politicians (
            id INTEGER PRIMARY KEY,
            name TEXT,
            party TEXT,
            relationship_type TEXT DEFAULT 'tracked'
        );
        CREATE TABLE claims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            opponent_id INTEGER,
            topic TEXT,
            stance TEXT,
            source_url TEXT,
            stated_at TEXT,
            created_at TEXT,
            confidence REAL,
            salience REAL,
            claim_type TEXT DEFAULT 'position'
        );
    """)
    db.execute("INSERT INTO tracked_politicians (id, name, party) VALUES (1, 'Test Polit', 'Jaunā Vienotība')")
    return db


class TestConfidenceTier:
    def test_augsta_boundary(self):
        assert _confidence_tier(0.9) == "augsta"
        assert _confidence_tier(1.0) == "augsta"

    def test_laba_range(self):
        assert _confidence_tier(0.89) == "laba"
        assert _confidence_tier(0.75) == "laba"

    def test_merena_range(self):
        assert _confidence_tier(0.74) == "merena"
        assert _confidence_tier(0.0) == "merena"

    def test_none_is_merena(self):
        assert _confidence_tier(None) == "merena"


class TestTopicColors:
    def test_covers_all_canonical_groups(self):
        canonical = set(TOPIC_GROUPS.keys())
        palette = set(PZV1_TOPIC_COLORS.keys())
        missing = canonical - palette
        assert not missing, f"missing colors for: {sorted(missing)}"

    def test_all_colors_are_hex(self):
        for group, color in PZV1_TOPIC_COLORS.items():
            assert color.startswith("#"), f"{group} color not hex: {color}"
            assert len(color) == 7, f"{group} color wrong length: {color}"

    def test_no_color_matches_party_palette(self):
        party_colors = set(PARTY_COLORS.values())
        for group, color in PZV1_TOPIC_COLORS.items():
            assert color not in party_colors, \
                f"{group} color {color} clashes with a party color"


class TestFetchPozicijasMetrics:
    def test_empty_db(self):
        db = _build_test_db()
        m = _fetch_pozicijas_metrics(db)
        assert m == {"total": 0, "last_week": 0, "confidence_good_pct": 0}

    def test_counts_and_percentage(self):
        db = _build_test_db()
        # 4 rows: 2 augsta (both last week), 1 laba (old), 1 merena (last week)
        now = now_lv_dt()
        recent = now.strftime("%Y-%m-%d %H:%M:%S")
        old = (now - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        rows = [
            (1, "T", "s1", "u1", recent, recent, 0.95, 0.5, "position"),
            (1, "T", "s2", "u2", recent, recent, 0.92, 0.5, "position"),
            (1, "T", "s3", "u3", old,    old,    0.80, 0.5, "position"),
            (1, "T", "s4", "u4", recent, recent, 0.50, 0.5, "position"),
        ]
        db.executemany(
            "INSERT INTO claims (opponent_id, topic, stance, source_url, stated_at, created_at, confidence, salience, claim_type) VALUES (?,?,?,?,?,?,?,?,?)",
            rows,
        )
        m = _fetch_pozicijas_metrics(db)
        assert m["total"] == 4
        assert m["last_week"] == 3
        # 3 of 4 are ≥ 0.75 → 75%
        assert m["confidence_good_pct"] == 75

    def test_excludes_non_position_claim_types(self):
        db = _build_test_db()
        now = now_lv_dt().strftime("%Y-%m-%d %H:%M:%S")
        db.execute(
            "INSERT INTO claims (opponent_id, topic, stance, source_url, stated_at, created_at, confidence, claim_type) VALUES (1,'T','s','u',?,?,0.9,'saeima_vote')",
            (now, now),
        )
        m = _fetch_pozicijas_metrics(db)
        assert m["total"] == 0


class TestFetchClaimsEnrichment:
    def test_enrichment_fields_present(self):
        db = _build_test_db()
        now = now_lv_dt().strftime("%Y-%m-%d %H:%M:%S")
        db.execute(
            "INSERT INTO claims (opponent_id, topic, stance, source_url, stated_at, created_at, confidence, claim_type) VALUES (1,'Aizsardzība','s','https://lsm.lv/raksts/a/b',?,?,0.95,'position')",
            (now, now),
        )
        rows = _fetch_claims(db)
        assert len(rows) == 1
        r = rows[0]
        assert r["party_color"] == "#3b82f6"      # JV color
        assert r["party_short"] == "JV"
        assert r["confidence_tier"] == "augsta"
        assert r["source_domain"] == "lsm.lv"
        assert r["date_iso"] == now[:10]

    def test_missing_party_fallback(self):
        db = _build_test_db()
        db.execute("INSERT INTO tracked_politicians (id, name, party, relationship_type) VALUES (2, 'Lato Lapsa', NULL, 'neutral')")
        now = now_lv_dt().strftime("%Y-%m-%d %H:%M:%S")
        db.execute(
            "INSERT INTO claims (opponent_id, topic, stance, source_url, stated_at, created_at, confidence, claim_type) VALUES (2,'T','s','',?,?,0.5,'position')",
            (now, now),
        )
        rows = _fetch_claims(db)
        r = [x for x in rows if x["politician_name"] == "Lato Lapsa"][0]
        assert r["party_color"] == "#8b8fa3"
        assert r["party_short"] == "—"
        assert r["confidence_tier"] == "merena"
        assert r["source_domain"] == ""

    def test_source_domain_strips_www_prefix(self):
        db = _build_test_db()
        now = now_lv_dt().strftime("%Y-%m-%d %H:%M:%S")
        db.execute(
            "INSERT INTO claims (opponent_id, topic, stance, source_url, stated_at, created_at, confidence, claim_type) VALUES (1,'T','s','https://www.delfi.lv/raksts/a',?,?,0.9,'position')",
            (now, now),
        )
        rows = _fetch_claims(db)
        assert rows[0]["source_domain"] == "delfi.lv"
