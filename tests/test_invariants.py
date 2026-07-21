"""Smoke tests for the critical CLAUDE.md invariants.

This file is a single-glance "is the contract still alive" layer. Each test
is intentionally minimal — full behavioral coverage lives in dedicated test
modules. The header of each test cites the CLAUDE.md punkts and the deeper
test file that exercises edge cases.

If a refactor commit makes any of these fail, that commit broke a contract
agents and downstream consumers depend on.

Running: pytest tests/test_invariants.py -v
"""

from __future__ import annotations

import os
import tempfile
from datetime import datetime

import pytest

from src.db import (
    get_db,
    init_db,
    search_similar_claims,
    store_claim,
)
from src.embeddings import embed_text


def _safe_unlink(path: str) -> None:
    try:
        os.unlink(path)
    except (PermissionError, FileNotFoundError):
        pass


@pytest.fixture
def tmp_db():
    """Minimal seeded DB: one active politician, two documents (one with
    source_url, one without), one tweet-source document for Inv 11."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    db = get_db(path)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.execute(
        "INSERT INTO tracked_politicians (id, name, party) "
        "VALUES (1, 'Test Politiķis', 'JV')"
    )
    db.execute(
        "INSERT INTO documents (id, content, content_hash, source_url, platform, scraped_at) "
        "VALUES (1, 'media article ar garumzīmēm ā ē ī', 'h1', "
        "'https://lsm.lv/raksts/inv-test', 'web', ?)",
        (now,),
    )
    db.execute(
        "INSERT INTO documents (id, content, content_hash, source_url, platform, scraped_at) "
        "VALUES (2, 'doc bez source_url', 'h2', NULL, 'web', ?)",
        (now,),
    )
    db.execute(
        "INSERT INTO documents (id, content, content_hash, source_url, platform, scraped_at) "
        "VALUES (3, 'tweet doc', 'h3', 'https://x.com/handle/status/9001', 'twitter', ?)",
        (now,),
    )
    db.commit()
    db.close()
    yield path
    _safe_unlink(path)


# =============================================================================
# Invariant 2 — Claims without source_url are silently dropped at the DB
# layer. No URL = no provenance = can't cite, can't re-fetch, can't contradict.
#
# Drop site: src/analyze.py save_analysis() — claims whose document has no
# source_url are recorded as a `missing_source_url` failure and not inserted.
# Deeper coverage: tests/test_analyze.py — save_analysis batch tests.
# =============================================================================
def test_inv2_claim_without_source_url_dropped(tmp_db, monkeypatch):
    import src.analyze as analyze_mod
    import src.db as db_mod
    import src.tools as tools_mod

    monkeypatch.setattr(analyze_mod, "get_db", lambda: get_db(tmp_db))
    monkeypatch.setattr(tools_mod, "get_db", lambda: get_db(tmp_db))
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_db)

    result = analyze_mod.save_analysis(
        pid=1,
        analysis_date="2026-04-29",
        sentiment=0.0,
        topics=["test"],
        quotes=[],
        brief="claim referencing doc with NULL source_url",
        confidence=0.5,
        claims=[{
            "document_id": 2,
            "topic": "Aizsardzība un drošība",
            "stance": "Pozīcija ar pareizajām garumzīmēm ā ē ī ū.",
            "confidence": 0.5,
            "reasoning": "Smoke tests pamatojums ar diakritiķiem ā ē ī ū ņ.",
            "salience": 0.5,
        }],
    )

    failure_types = {f["type"] for f in result.get("failures", [])}
    assert "missing_source_url" in failure_types, (
        f"missing_source_url drop not recorded: {result}"
    )
    db = get_db(tmp_db)
    rows = db.execute("SELECT id FROM claims WHERE document_id = 2").fetchall()
    db.close()
    assert rows == [], f"claim should have been dropped, found rows: {list(rows)}"


# =============================================================================
# Invariant 3 — store_claim() is idempotent on (opponent_id, source_url, topic).
# Re-running the same triple returns the existing claim_id; first-write-wins.
#
# Deeper coverage: tests/test_db.py::TestStoreClaimType (saeima_vote variant)
# This test covers the position-type variant.
# =============================================================================
def test_inv3_store_claim_idempotent_on_triple(tmp_db):
    first = store_claim(
        opponent_id=1, document_id=1, topic="Aizsardzība un drošība",
        stance="Atbalsta NATO klātbūtni Baltijā ar garumzīmēm ā ē ī.",
        quote=None, confidence=0.8,
        reasoning="Pamatojums ar diakritiķiem ā ē ī ū ņ.",
        salience=0.6, source_url="https://lsm.lv/raksts/inv-test",
        stated_at=None, claim_type="position", db_path=tmp_db,
    )
    second = store_claim(
        opponent_id=1, document_id=1, topic="Aizsardzība un drošība",
        stance="Pavisam cita stance — bet triple ir tāds pats ā ē ī.",
        quote=None, confidence=0.95,
        reasoning="Atšķirīgs pamatojums, tomēr triple sakrīt ā ē ī ū ņ.",
        salience=0.9, source_url="https://lsm.lv/raksts/inv-test",
        stated_at=None, claim_type="position", db_path=tmp_db,
    )
    assert first == second, (
        "second store_claim with same (opponent_id, source_url, topic) "
        "must return existing claim_id (first-write-wins)"
    )


# =============================================================================
# Invariant 4 — claim_type segregation in search_similar_claims.
# Readers filter by claim_type, not URL heuristics. position/saeima_vote/
# commentary are distinct retrieval cohorts.
#
# Deeper coverage: tests/test_db.py::TestSearchSimilarClaimsFilter (3 tests).
# =============================================================================
def test_inv4_claim_type_filter_segregation(tmp_db):
    db = get_db(tmp_db)
    db.execute(
        "INSERT INTO documents (id, content, content_hash, source_url, platform) "
        "VALUES (10, 'saeima vote rec', 'hv', "
        "'https://titania.saeima.lv/v/inv', 'saeima')"
    )
    db.commit()
    db.close()

    store_claim(
        opponent_id=1, document_id=1, topic="Aizsardzība un drošība",
        stance="Pret X likumprojektu — uzskata par nevajadzīgu ā ē ī.",
        quote=None, confidence=0.8,
        reasoning="Mediju citāts ar diakritiķiem ā ē ī ū ņ.",
        salience=0.7, source_url="https://lsm.lv/raksts/inv-test",
        stated_at=None, claim_type="position", db_path=tmp_db,
    )
    store_claim(
        opponent_id=1, document_id=None, topic="Aizsardzība un drošība",
        stance="Atbalsta likumprojektu — balso PAR",
        quote=None, confidence=0.95, reasoning="Saeimas balsojums",
        salience=0.5, source_url="https://titania.saeima.lv/v/inv",
        stated_at=None, claim_type="saeima_vote", db_path=tmp_db,
    )

    qvec = embed_text("Aizsardzība un drošība: position retrieval")
    only_positions = search_similar_claims(
        qvec, opponent_id=1, top_k=10,
        claim_type_filter=["position"], db_path=tmp_db,
    )
    types = {r["claim_type"] for r in only_positions}
    assert types <= {"position"}, f"vote leaked through position-only filter: {types}"


# =============================================================================
# Invariant 5 — claims.speaker_id attributes authorship separately from subject.
# NULL = first-party (speaker IS opponent_id); non-NULL ≠ opponent_id =
# third-party commentary. search_similar_claims excludes commentary by default.
#
# Deeper coverage: tests/test_db.py — speaker_id column tests + search exclusion.
# =============================================================================
def test_inv5_speaker_id_separation(tmp_db):
    first_party = store_claim(
        opponent_id=1, document_id=1, topic="Aizsardzība un drošība",
        stance="Pirmās personas stance ar garumzīmēm ā ē ī.",
        quote=None, confidence=0.7,
        reasoning="Pirmās personas pamatojums ā ē ī ū ņ.",
        salience=0.5, source_url="https://lsm.lv/raksts/inv-test",
        stated_at=None, claim_type="position", db_path=tmp_db,
    )
    db = get_db(tmp_db)
    row = db.execute(
        "SELECT speaker_id FROM claims WHERE id = ?", (first_party,)
    ).fetchone()
    db.close()
    assert row["speaker_id"] is None, (
        f"first-party claim must have speaker_id=NULL, got {row['speaker_id']}"
    )


# =============================================================================
# Invariant 6 — claim_type='saeima_vote' allows document_id=NULL.
# Vote provenance lives in saeima_individual_votes; position/commentary still
# REQUIRE document_id NOT NULL.
#
# Deeper coverage: tests/test_db.py::TestStoreClaimType — accepts_null_document_id
# and url_dedup_still_works.
# =============================================================================
def test_inv6_saeima_vote_document_id_nullable(tmp_db):
    cid = store_claim(
        opponent_id=1, document_id=None, topic="Budžets",
        stance="Atbalsta: budžeta likumprojektu",
        quote=None, confidence=1.0, reasoning="Saeimas balsojums",
        salience=0.5, source_url="https://titania.saeima.lv/v/budzets-2026",
        stated_at="2026-04-29T10:00:00", claim_type="saeima_vote",
        db_path=tmp_db,
    )
    db = get_db(tmp_db)
    row = db.execute(
        "SELECT document_id, claim_type FROM claims WHERE id = ?", (cid,)
    ).fetchone()
    db.close()
    assert row["document_id"] is None
    assert row["claim_type"] == "saeima_vote"


# =============================================================================
# Invariant 9 — save_analysis() is atomic. Catastrophic DB failures roll back
# everything (analysis + claims + reviewed_at) and return status='failed'.
#
# Deeper coverage: tests/test_analyze.py::TestSaveAnalysisAtomicity — full
# rollback verification with injected RuntimeError mid-batch.
# =============================================================================
def test_inv9_save_analysis_atomic_on_failure(tmp_db, monkeypatch):
    import src.analyze as analyze_mod
    import src.db as db_mod
    import src.tools as tools_mod

    monkeypatch.setattr(analyze_mod, "get_db", lambda: get_db(tmp_db))
    monkeypatch.setattr(tools_mod, "get_db", lambda: get_db(tmp_db))
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_db)

    def boom(*args, **kwargs):
        raise RuntimeError("inv9 simulated DB failure")

    monkeypatch.setattr(analyze_mod, "store_claim", boom)

    db = get_db(tmp_db)
    analyses_before = db.execute("SELECT COUNT(*) FROM analyses").fetchone()[0]
    claims_before = db.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
    db.close()

    result = analyze_mod.save_analysis(
        pid=1,
        analysis_date="2026-04-29",
        sentiment=0.0,
        topics=["t"],
        quotes=[],
        brief="will explode",
        confidence=0.5,
        claims=[{
            "document_id": 1,
            "topic": "Aizsardzība un drošība",
            "stance": "Stance ar garumzīmēm ā ē ī ū.",
            "confidence": 0.5,
            "reasoning": "Pamatojums ā ē ī ū ņ.",
            "salience": 0.5,
        }],
    )

    assert result["status"] == "failed"
    failure_types = {f["type"] for f in result.get("failures", [])}
    assert "transaction_rolled_back" in failure_types

    db = get_db(tmp_db)
    analyses_after = db.execute("SELECT COUNT(*) FROM analyses").fetchone()[0]
    claims_after = db.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
    db.close()
    assert analyses_after == analyses_before
    assert claims_after == claims_before


# =============================================================================
# Invariant 11 — social_accounts.feed_type ∈ {first_party, relay} controls
# _store_tweets author-linking. first_party requires author handle match for
# role='subject'; relay defers to text-scanned mentions (no junction at insert).
#
# Deeper coverage: tests/test_ingest.py::test_store_tweets_first_party_links_*
# and test_store_tweets_relay_skips_*.
# =============================================================================
def test_inv11_social_accounts_feed_type_constraint(tmp_db):
    db = get_db(tmp_db)
    db.execute(
        "INSERT INTO social_accounts (opponent_id, platform, handle, feed_type) "
        "VALUES (1, 'twitter', 'testhandle', 'first_party')"
    )
    db.execute(
        "INSERT INTO tracked_politicians (id, name, party) "
        "VALUES (2, 'Relay Source', 'TB')"
    )
    db.execute(
        "INSERT INTO social_accounts (opponent_id, platform, handle, feed_type) "
        "VALUES (2, 'twitter', 'relayhandle', 'relay')"
    )
    db.commit()
    rows = db.execute(
        "SELECT opponent_id, feed_type FROM social_accounts ORDER BY opponent_id"
    ).fetchall()
    db.close()
    feed_types = {r["feed_type"] for r in rows}
    assert feed_types == {"first_party", "relay"}, (
        f"feed_type column rejects required values: got {feed_types}"
    )


# =============================================================================
# Invariant 10 — coalition truth source is parties.coalition_status, read via
# src.coalition.get_coalition_map() / party_status(). NEVER use
# tracked_politicians.relationship_type for coalition logic — that is a legacy
# per-politician tracking role.
#
# Deeper coverage: none yet — src/coalition.py is a thin DB facade. This smoke
# is the only guard against a refactor wiring coalition logic back to
# relationship_type.
# =============================================================================
def test_inv10_coalition_status_is_truth_source_not_relationship_type(tmp_db):
    from src.coalition import get_coalition_map, party_status

    db = get_db(tmp_db)
    # LPV is opposition per parties.coalition_status...
    db.execute(
        "INSERT INTO parties (name, short_name, coalition_status) "
        "VALUES ('Latvija Pirmajā Vietā', 'LPV', 'opposition')"
    )
    # ...even though we attach a politician whose relationship_type sounds like
    # coalition. Coalition logic must follow coalition_status, not this field.
    db.execute(
        "INSERT INTO tracked_politicians (id, name, party, relationship_type) "
        "VALUES (50, 'Opo Politiķis', 'Latvija Pirmajā Vietā', 'coalition_partner')"
    )
    db.commit()
    cmap = get_coalition_map(db)
    db.close()

    # Keyed by both full name and short_name, value follows coalition_status.
    assert cmap["Latvija Pirmajā Vietā"] == "opposition"
    assert cmap["LPV"] == "opposition"
    assert party_status("Latvija Pirmajā Vietā", db=get_db(tmp_db)) == "opposition"


def test_inv10_null_or_unknown_party_resolves_to_other(tmp_db):
    """Bezpartejiski (party IS NULL) and parties absent from the table resolve
    to 'other' — the bucket the daily brief's Bezpartejiskie block depends on."""
    from src.coalition import party_status

    assert party_status(None, db=get_db(tmp_db)) == "other"
    assert party_status("Nav Tādas Partijas", db=get_db(tmp_db)) == "other"
