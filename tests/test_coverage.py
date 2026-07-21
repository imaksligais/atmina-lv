"""Tests for src.coverage — read-only coverage diagnostics.

Dark zone = a politician whose Saeima votes are tracked but who has no
analyses, no first-party position claims, and no X feed — so no rhetoric
channel exists and a contradiction can never form (audit 2026-06-08, P4).
"""

import os
import sqlite3
import tempfile

import pytest

from src.coverage import (
    compute_coverage,
    format_coverage_report,
    format_coverage_summary,
    stale_pol_politicians,
)


@pytest.fixture
def cov_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = sqlite3.connect(path)
    db.executescript("""
        CREATE TABLE tracked_politicians (id INTEGER PRIMARY KEY, name TEXT, party TEXT, relationship_type TEXT);
        CREATE TABLE saeima_individual_votes (id INTEGER PRIMARY KEY, politician_id INTEGER);
        CREATE TABLE analyses (id INTEGER PRIMARY KEY, opponent_id INTEGER);
        CREATE TABLE claims (id INTEGER PRIMARY KEY, opponent_id INTEGER, claim_type TEXT);
        CREATE TABLE social_accounts (id INTEGER PRIMARY KEY, opponent_id INTEGER, platform TEXT, handle TEXT);

        -- p1: dark zone (votes, NO analyses, NO position claim, NO X)
        INSERT INTO tracked_politicians VALUES (1, 'Dark Deputāts', 'JV', 'tracked');
        INSERT INTO saeima_individual_votes (politician_id) VALUES (1);
        -- p2: votes + X feed → NOT dark
        INSERT INTO tracked_politicians VALUES (2, 'X Deputāts', 'ZZS', 'tracked');
        INSERT INTO saeima_individual_votes (politician_id) VALUES (2);
        INSERT INTO social_accounts (opponent_id, platform, handle) VALUES (2, 'twitter', 'xdep');
        -- p3: votes + position claim → NOT dark
        INSERT INTO tracked_politicians VALUES (3, 'Claim Deputāts', 'NA', 'tracked');
        INSERT INTO saeima_individual_votes (politician_id) VALUES (3);
        INSERT INTO claims (opponent_id, claim_type) VALUES (3, 'position');
        -- p4: inactive → excluded everywhere
        INSERT INTO tracked_politicians VALUES (4, 'Inactive', 'X', 'inactive');
        INSERT INTO saeima_individual_votes (politician_id) VALUES (4);
        -- p5: active, NO votes, NO X → in no_x_feed + never_analyzed, but NOT dark (no votes)
        INSERT INTO tracked_politicians VALUES (5, 'No Votes', 'P', 'tracked');

        -- stale-pol fixtures (need >=5 position claims + contradictions table)
        CREATE TABLE contradictions (id INTEGER PRIMARY KEY, opponent_id INTEGER, detected_at TIMESTAMP);
        -- p6: active, 5 position claims, NEVER any contradiction → stale-pol IN
        INSERT INTO tracked_politicians VALUES (6, 'Never Checked', 'JV', 'tracked');
        INSERT INTO claims (opponent_id, claim_type) VALUES (6,'position'),(6,'position'),(6,'position'),(6,'position'),(6,'position');
        -- p7: active, 5 position claims, FRESH contradiction (-10d) → OUT
        INSERT INTO tracked_politicians VALUES (7, 'Fresh Check', 'NA', 'tracked');
        INSERT INTO claims (opponent_id, claim_type) VALUES (7,'position'),(7,'position'),(7,'position'),(7,'position'),(7,'position');
        INSERT INTO contradictions (opponent_id, detected_at) VALUES (7, datetime('now','-10 days'));
        -- p8: active, 5 position claims, OLD contradiction (-200d) → IN
        INSERT INTO tracked_politicians VALUES (8, 'Old Check', 'ZZS', 'tracked');
        INSERT INTO claims (opponent_id, claim_type) VALUES (8,'position'),(8,'position'),(8,'position'),(8,'position'),(8,'position');
        INSERT INTO contradictions (opponent_id, detected_at) VALUES (8, datetime('now','-200 days'));
        -- p9: active, only 4 position claims → OUT (below threshold)
        INSERT INTO tracked_politicians VALUES (9, 'Too Few', 'P', 'tracked');
        INSERT INTO claims (opponent_id, claim_type) VALUES (9,'position'),(9,'position'),(9,'position'),(9,'position');
    """)
    db.commit()
    db.close()
    yield path
    try:
        os.unlink(path)
    except PermissionError:
        pass


def test_dark_zone_is_votes_without_any_channel(cov_db):
    cov = compute_coverage(cov_db)
    dark_ids = {r["id"] for r in cov["dark_zone"]}
    assert dark_ids == {1}, f"dark zone should be exactly p1, got {dark_ids}"


def test_no_x_feed_excludes_those_with_twitter(cov_db):
    cov = compute_coverage(cov_db)
    nox_ids = {r["id"] for r in cov["no_x_feed"]}
    assert 2 not in nox_ids, "p2 has a twitter account — must not be in no_x_feed"
    assert {1, 3, 5} <= nox_ids, f"p1,p3,p5 lack twitter; got {nox_ids}"


def test_inactive_excluded_from_all_sections(cov_db):
    cov = compute_coverage(cov_db)
    for key in ("dark_zone", "no_x_feed", "never_analyzed", "no_position_claims"):
        assert 4 not in {r["id"] for r in cov[key]}, f"inactive p4 leaked into {key}"


def test_format_report_includes_counts_and_ids(cov_db):
    cov = compute_coverage(cov_db)
    report = format_coverage_report(cov)
    assert "Tumšā zona (1)" in report
    assert "Dark Deputāts" in report


def test_format_summary_is_one_info_line(cov_db):
    cov = compute_coverage(cov_db)
    line = format_coverage_summary(cov)
    assert "\n" not in line, "summary must be a single line"
    # dark_zone=1; counts surface
    assert str(len(cov["dark_zone"])) in line
    assert "tum" in line.lower()  # 'tumšās zonas'
    assert "X feed" in line


def test_stale_pol_includes_never_and_old(cov_db):
    ids = {r["id"] for r in stale_pol_politicians(cov_db, stale_days=60)}
    assert {6, 8} <= ids, f"p6 (never) and p8 (>60d) must be in stale-pol, got {ids}"


def test_stale_pol_excludes_recent_and_too_few(cov_db):
    ids = {r["id"] for r in stale_pol_politicians(cov_db, stale_days=60)}
    assert 7 not in ids, "p7 with a fresh (<60d) check must be excluded"
    assert 9 not in ids, "p9 with <5 position claims must be excluded"


def test_stale_pol_excludes_inactive(cov_db):
    ids = {r["id"] for r in stale_pol_politicians(cov_db, stale_days=60)}
    assert 4 not in ids, "inactive p4 must not leak into stale-pol"
