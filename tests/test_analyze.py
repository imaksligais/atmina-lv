"""Tests for src/analyze.py — retrieval functions with temp DB."""

import os
import tempfile
import pytest
from unittest.mock import patch
from datetime import datetime, timedelta
from src.db import init_db, get_db


def _safe_unlink(path):
    try:
        os.unlink(path)
    except PermissionError:
        pass


@pytest.fixture
def analyze_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    db = get_db(path)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    old = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")

    # Politicians
    db.execute("INSERT INTO tracked_politicians (id, name, party) VALUES (1, 'Siliņa', 'JV')")
    db.execute("INSERT INTO tracked_politicians (id, name, party) VALUES (2, 'Šlesers', 'LPV')")

    # Documents — Siliņa has new docs, Šlesers doesn't
    db.execute("""INSERT INTO documents (id, content, content_hash, scraped_at)
                  VALUES (1, 'doc1 content lorem ipsum', 'h1', ?)""", (now,))
    db.execute("""INSERT INTO documents (id, content, content_hash, scraped_at)
                  VALUES (2, 'doc2 content lorem ipsum', 'h2', ?)""", (now,))
    db.execute("""INSERT INTO documents (id, content, content_hash, scraped_at)
                  VALUES (3, 'old doc content lorem', 'h3', ?)""", (old,))

    # Link documents to politicians via junction table
    db.execute("INSERT INTO document_politicians (document_id, politician_id, role) VALUES (1, 1, 'subject')")
    db.execute("INSERT INTO document_politicians (document_id, politician_id, role) VALUES (2, 1, 'subject')")
    db.execute("INSERT INTO document_politicians (document_id, politician_id, role) VALUES (3, 2, 'subject')")

    # Claims
    db.execute("""INSERT INTO claims (id, opponent_id, document_id, topic, stance,
                  confidence, reasoning, salience, source_url, stated_at, created_at)
                  VALUES (1, 1, 1, 'NATO', 'Pro NATO', 0.9, 'clear', 0.8, 'https://x.lv', ?, ?)""",
               (now, now))
    db.execute("""INSERT INTO claims (id, opponent_id, document_id, topic, stance,
                  confidence, reasoning, salience, source_url, stated_at, created_at)
                  VALUES (2, 1, 2, 'Budžets', 'Nulles budžets', 0.7, 'inferred', 0.6, 'https://y.lv', ?, ?)""",
               (now, now))

    # Analysis for Šlesers (recent) — he should not appear as pending
    db.execute("""INSERT INTO analyses (opponent_id, period_start, period_end, sentiment_score,
                  key_topics, notable_quotes, brief_markdown, confidence, created_at)
                  VALUES (2, '2026-04-01', '2026-04-07', 0.0, '[]', '[]', 'brief', 0.5, ?)""", (now,))

    db.commit()
    db.close()
    yield path
    _safe_unlink(path)


class TestGetPendingPoliticians:
    def test_returns_politician_with_new_docs(self, analyze_db):
        with patch("src.analyze.get_db", lambda: get_db(analyze_db)):
            from src.analyze import get_pending_politicians
            pending = get_pending_politicians(days=1)
            names = [p["name"] for p in pending]
            assert "Siliņa" in names

    def test_excludes_recently_analyzed(self, analyze_db):
        with patch("src.analyze.get_db", lambda: get_db(analyze_db)):
            from src.analyze import get_pending_politicians
            pending = get_pending_politicians(days=1)
            names = [p["name"] for p in pending]
            # Šlesers has old docs + recent analysis → not pending
            assert "Šlesers" not in names

    def test_sorted_by_doc_count(self, analyze_db):
        with patch("src.analyze.get_db", lambda: get_db(analyze_db)):
            from src.analyze import get_pending_politicians
            pending = get_pending_politicians(days=1)
            if len(pending) > 1:
                for i in range(len(pending) - 1):
                    assert pending[i]["doc_count"] >= pending[i + 1]["doc_count"]

    def test_returns_expected_fields(self, analyze_db):
        with patch("src.analyze.get_db", lambda: get_db(analyze_db)):
            from src.analyze import get_pending_politicians
            pending = get_pending_politicians(days=1)
            if pending:
                p = pending[0]
                for key in ["id", "name", "party", "doc_count", "last_analyzed"]:
                    assert key in p


class TestGetPoliticianDocuments:
    def test_returns_recent_docs(self, analyze_db):
        with patch("src.analyze.get_db", lambda: get_db(analyze_db)):
            from src.analyze import get_politician_documents
            docs = get_politician_documents(1, days=1)
            assert len(docs) == 2

    def test_returns_no_old_docs(self, analyze_db):
        with patch("src.analyze.get_db", lambda: get_db(analyze_db)):
            from src.analyze import get_politician_documents
            docs = get_politician_documents(2, days=1)
            assert len(docs) == 0

    def test_respects_max_results(self, analyze_db):
        with patch("src.analyze.get_db", lambda: get_db(analyze_db)):
            from src.analyze import get_politician_documents
            docs = get_politician_documents(1, days=1, max_results=1)
            assert len(docs) == 1


class TestGetExistingClaims:
    def test_returns_claims(self, analyze_db):
        with patch("src.analyze.get_db", lambda: get_db(analyze_db)):
            from src.analyze import get_existing_claims
            claims = get_existing_claims(1, days=90)
            assert len(claims) == 2

    def test_no_claims_for_other_politician(self, analyze_db):
        with patch("src.analyze.get_db", lambda: get_db(analyze_db)):
            from src.analyze import get_existing_claims
            claims = get_existing_claims(2, days=90)
            assert len(claims) == 0

    def test_returns_expected_fields(self, analyze_db):
        with patch("src.analyze.get_db", lambda: get_db(analyze_db)):
            from src.analyze import get_existing_claims
            claims = get_existing_claims(1, days=90)
            if claims:
                c = claims[0]
                for key in ["id", "topic", "stance", "confidence", "salience"]:
                    assert key in c


class TestGetExistingClaimsClaimType:
    """get_existing_claims default excludes saeima_vote (the ~520k-row vote
    corpus imported 2026-05-27 all lands inside the 90-day created_at window
    and otherwise floods every extractor-agent context). Default returns
    position + commentary; claim_types=None returns all types."""

    @pytest.fixture
    def typed_claims_db(self, analyze_db):
        # analyze_db already seeds two 'position' claims for pid=1 (ids 1,2).
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db = get_db(analyze_db)
        db.execute(
            """INSERT INTO claims (id, opponent_id, document_id, topic, stance,
               confidence, reasoning, salience, source_url, stated_at, created_at,
               claim_type)
               VALUES (10, 1, 1, 'Aizsardzība un drošība', 'Komentārs', 0.6,
                       'r', 0.5, 'https://c.lv', ?, ?, 'commentary')""",
            (now, now),
        )
        db.execute(
            """INSERT INTO claims (id, opponent_id, document_id, topic, stance,
               confidence, reasoning, salience, source_url, stated_at, created_at,
               claim_type)
               VALUES (11, 1, NULL, 'Budžets', 'Balsoja PAR', 1.0,
                       'r', 0.5, 'https://titania.saeima.lv/v/1', ?, ?, 'saeima_vote')""",
            (now, now),
        )
        db.commit()
        db.close()
        return analyze_db

    def test_default_excludes_saeima_vote(self, typed_claims_db):
        with patch("src.analyze.get_db", lambda: get_db(typed_claims_db)):
            from src.analyze import get_existing_claims
            claims = get_existing_claims(1, days=90)
            types = {c["claim_type"] for c in claims}
            assert types == {"position", "commentary"}, types
            assert all(c["claim_type"] != "saeima_vote" for c in claims)

    def test_none_returns_all_types(self, typed_claims_db):
        with patch("src.analyze.get_db", lambda: get_db(typed_claims_db)):
            from src.analyze import get_existing_claims
            claims = get_existing_claims(1, days=90, claim_types=None)
            types = {c["claim_type"] for c in claims}
            assert types == {"position", "commentary", "saeima_vote"}, types

    def test_returned_dicts_include_claim_type(self, typed_claims_db):
        with patch("src.analyze.get_db", lambda: get_db(typed_claims_db)):
            from src.analyze import get_existing_claims
            claims = get_existing_claims(1, days=90)
            assert claims, "expected at least one claim"
            assert all("claim_type" in c for c in claims)


class TestSaveAnalysisPrecomputedEmbedding:
    """The embedding precomputed by save_analysis (outside the write lock) must
    be byte-identical to what db.store_claim would compute internally. Locks the
    normalization-pipeline replication: raw topic 'NATO' → 'Aizsardzība un
    drošība' via normalize_topic; a missing normalization would diverge."""

    def test_precomputed_embedding_matches_internal(self, analyze_db, monkeypatch):
        import src.analyze as analyze_mod
        import src.tools as tools_mod
        import src.db as db_mod
        from src.db import _float_list_to_bytes
        from src.embeddings import embed_text
        from src.topic_map import normalize_topic

        monkeypatch.setattr(analyze_mod, "get_db", lambda: get_db(analyze_db))
        monkeypatch.setattr(tools_mod, "get_db", lambda: get_db(analyze_db))
        monkeypatch.setattr(db_mod, "DB_PATH", analyze_db)

        db = get_db(analyze_db)
        db.execute("UPDATE documents SET source_url='https://t.lv/emb' WHERE id=1")
        db.commit()
        db.close()

        raw_topic = "NATO"
        normalized = normalize_topic(raw_topic)
        assert normalized != raw_topic, (
            "test topic must be one normalize_topic actually changes"
        )
        stance = "Atbalsta NATO klātbūtni Baltijā ar garumzīmēm ā ē ī ū."

        result = analyze_mod.save_analysis(
            pid=1, analysis_date="2026-04-29", sentiment=0.0,
            topics=["t"], quotes=[], brief="equivalence test", confidence=0.5,
            claims=[{
                "document_id": 1, "topic": raw_topic, "stance": stance,
                "confidence": 0.5, "reasoning": "Pamatojums ā ē ī ū ņ.",
                "salience": 0.5,
            }],
        )
        assert result["status"] == "success", result
        claim_id = result["claim_ids"][0]

        import sqlite_vec
        db = get_db(analyze_db)
        db.enable_load_extension(True)
        sqlite_vec.load(db)
        db.enable_load_extension(False)
        row = db.execute(
            "SELECT embedding FROM claim_vectors WHERE claim_id=?", (claim_id,)
        ).fetchone()
        db.close()
        expected = _float_list_to_bytes(embed_text(f"{normalized}: {stance}"))
        assert bytes(row["embedding"]) == expected


class TestSaveAnalysisEmptyDocIds:
    """Regression: save_analysis(empty_doc_ids=[...]) must mark those docs
    reviewed. Before 2026-04-11 the only way to mark a doc reviewed was to
    include it in the claims list, so docs judged ceremonial reappeared in
    the backlog on every routine run (2026-04-10 audit)."""

    def test_empty_doc_ids_marks_documents_reviewed(self, analyze_db, monkeypatch):
        import src.analyze as analyze_mod
        import src.tools as tools_mod
        import src.db as db_mod

        monkeypatch.setattr(analyze_mod, "get_db", lambda: get_db(analyze_db))
        monkeypatch.setattr(tools_mod, "get_db", lambda: get_db(analyze_db))
        monkeypatch.setattr(db_mod, "DB_PATH", analyze_db)

        # Add a reviewed_at column if the fixture schema lacks it — init_db
        # creates the real schema so it should be present.
        db = get_db(analyze_db)
        cols = [r[1] for r in db.execute("PRAGMA table_info(documents)").fetchall()]
        assert "reviewed_at" in cols, (
            "fixture schema missing reviewed_at; check init_db"
        )
        db.close()

        result = analyze_mod.save_analysis(
            pid=1,
            analysis_date="2026-04-11",
            sentiment=0.0,
            topics=["test"],
            quotes=[],
            brief="looked at doc 1 and doc 2, both ceremonial",
            confidence=0.5,
            claims=[],
            empty_doc_ids=[1, 2],
        )
        assert result["status"] == "success"
        assert result["failures"] == []

        # Both docs should now have reviewed_at set
        db = get_db(analyze_db)
        rows = db.execute(
            "SELECT id, reviewed_at FROM documents WHERE id IN (1, 2)"
        ).fetchall()
        db.close()
        assert len(rows) == 2
        for r in rows:
            assert r["reviewed_at"] is not None, (
                f"doc {r['id']} should have been marked reviewed"
            )

    def test_empty_doc_ids_merges_with_claim_doc_ids(self, analyze_db, monkeypatch):
        """When both claims and empty_doc_ids are given, the union is marked."""
        import src.analyze as analyze_mod
        import src.tools as tools_mod
        import src.db as db_mod

        monkeypatch.setattr(analyze_mod, "get_db", lambda: get_db(analyze_db))
        monkeypatch.setattr(tools_mod, "get_db", lambda: get_db(analyze_db))
        monkeypatch.setattr(db_mod, "DB_PATH", analyze_db)

        # Doc 1 has a claim, doc 2 is empty_doc_ids only.
        analyze_mod.save_analysis(
            pid=1,
            analysis_date="2026-04-11",
            sentiment=0.0,
            topics=["test"],
            quotes=[],
            brief="doc 1 has a position, doc 2 is ceremonial",
            confidence=0.6,
            claims=[{
                "document_id": 1,
                "topic": "Valsts pārvalde",
                "stance": "Test stance for doc 1",
                "confidence": 0.6,
                "reasoning": "unit test",
                "salience": 0.3,
                "source_url": None,  # overridden from document
                "stated_at": "2026-04-11",
            }],
            empty_doc_ids=[2],
        )
        # Success (or partial if store_claim fails due to missing url) —
        # either way the empty_doc should still be marked reviewed.
        db = get_db(analyze_db)
        row2 = db.execute(
            "SELECT reviewed_at FROM documents WHERE id = 2"
        ).fetchone()
        db.close()
        assert row2["reviewed_at"] is not None

    def test_no_claims_no_empty_doc_ids_marks_nothing(self, analyze_db, monkeypatch):
        """Backwards compat: save_analysis with neither claims nor
        empty_doc_ids must not touch reviewed_at."""
        import src.analyze as analyze_mod
        import src.tools as tools_mod
        import src.db as db_mod

        monkeypatch.setattr(analyze_mod, "get_db", lambda: get_db(analyze_db))
        monkeypatch.setattr(tools_mod, "get_db", lambda: get_db(analyze_db))
        monkeypatch.setattr(db_mod, "DB_PATH", analyze_db)

        # Baseline: note initial reviewed_at state
        db = get_db(analyze_db)
        before = {
            r["id"]: r["reviewed_at"]
            for r in db.execute("SELECT id, reviewed_at FROM documents").fetchall()
        }
        db.close()

        analyze_mod.save_analysis(
            pid=1,
            analysis_date="2026-04-11",
            sentiment=0.0,
            topics=[],
            quotes=[],
            brief="no docs considered",
            confidence=0.5,
            claims=[],
        )

        db = get_db(analyze_db)
        after = {
            r["id"]: r["reviewed_at"]
            for r in db.execute("SELECT id, reviewed_at FROM documents").fetchall()
        }
        db.close()
        assert before == after, "reviewed_at changed even though no docs were passed"


class TestSaveAnalysisAtomicity:
    """S10: save_analysis wraps analysis + claims + reviewed-docs updates in a
    single SQLite transaction so a mid-batch DB write failure rolls back
    everything instead of leaving a half-persisted state.

    Validation-level drops (missing source_url, store_claim returning
    status='error') remain best-effort skips — the test covers truly
    catastrophic DB failures, which is what the transaction protects against.
    """

    def test_transaction_rolls_back_on_db_write_failure(
        self, analyze_db, monkeypatch
    ):
        """If store_claim raises a real exception (not a JSON-error return)
        partway through a batch, the entire save_analysis transaction must
        roll back: no analysis row, no claim rows, no reviewed_at updates.
        """
        import src.analyze as analyze_mod
        import src.tools as tools_mod
        import src.db as db_mod

        monkeypatch.setattr(analyze_mod, "get_db", lambda: get_db(analyze_db))
        monkeypatch.setattr(tools_mod, "get_db", lambda: get_db(analyze_db))
        monkeypatch.setattr(db_mod, "DB_PATH", analyze_db)

        # Baseline counts before the call
        db = get_db(analyze_db)
        analyses_before = db.execute("SELECT COUNT(*) FROM analyses").fetchone()[0]
        claims_before = db.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
        docs_unreviewed_before = db.execute(
            "SELECT COUNT(*) FROM documents WHERE reviewed_at IS NULL"
        ).fetchone()[0]
        db.close()

        # Inject a failure: the second store_claim call raises a RuntimeError
        # to simulate a disk-full / lock-timeout / unexpected DB error mid-batch.
        call_count = {"n": 0}
        real_store_claim = tools_mod.store_claim

        def flaky_store_claim(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise RuntimeError("simulated disk full")
            return real_store_claim(*args, **kwargs)

        monkeypatch.setattr(analyze_mod, "store_claim", flaky_store_claim)

        # Set document source_urls so the claims pass the missing-url skip
        db = get_db(analyze_db)
        db.execute(
            "UPDATE documents SET source_url = 'https://test.lv/1' WHERE id = 1"
        )
        db.execute(
            "UPDATE documents SET source_url = 'https://test.lv/2' WHERE id = 2"
        )
        db.commit()
        db.close()

        result = analyze_mod.save_analysis(
            pid=1,
            analysis_date="2026-04-11",
            sentiment=0.0,
            topics=["t"],
            quotes=[],
            brief="two claims, second one will explode",
            confidence=0.5,
            claims=[
                {
                    "document_id": 1,
                    "topic": "NATO",
                    "stance": "first claim",
                    "confidence": 0.5,
                    "reasoning": "rollback test",
                    "salience": 0.5,
                },
                {
                    "document_id": 2,
                    "topic": "Budžets",
                    "stance": "second claim — injected failure",
                    "confidence": 0.5,
                    "reasoning": "rollback test",
                    "salience": 0.5,
                },
            ],
            empty_doc_ids=[],
        )

        # The caller sees a "failed" status with a transaction_rolled_back failure
        assert result["status"] == "failed", (
            f"expected failed status, got {result['status']}: {result}"
        )
        assert result["analysis_id"] is None
        assert result["claim_ids"] == []
        failure_types = {f["type"] for f in result["failures"]}
        assert "transaction_rolled_back" in failure_types

        # Post-state: nothing was persisted. The fixture already has 2 pre-
        # existing claims and 0 analyses, so the counts must match the
        # baseline exactly — no leaked rows.
        db = get_db(analyze_db)
        analyses_after = db.execute("SELECT COUNT(*) FROM analyses").fetchone()[0]
        claims_after = db.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
        docs_unreviewed_after = db.execute(
            "SELECT COUNT(*) FROM documents WHERE reviewed_at IS NULL"
        ).fetchone()[0]
        db.close()

        assert analyses_after == analyses_before, (
            f"analysis row persisted despite rollback: "
            f"{analyses_before} -> {analyses_after}"
        )
        assert claims_after == claims_before, (
            f"claim row persisted despite rollback: "
            f"{claims_before} -> {claims_after}"
        )
        assert docs_unreviewed_after == docs_unreviewed_before, (
            f"documents.reviewed_at updated despite rollback: "
            f"{docs_unreviewed_before} -> {docs_unreviewed_after}"
        )

    def test_successful_batch_persists_everything(self, analyze_db, monkeypatch):
        """Happy path: when no failure occurs, save_analysis persists the
        analysis, both claims, and both reviewed_at updates in the same
        transaction. This guards against a regression where the transaction
        wrapper accidentally swallows successful writes.
        """
        import src.analyze as analyze_mod
        import src.tools as tools_mod
        import src.db as db_mod

        monkeypatch.setattr(analyze_mod, "get_db", lambda: get_db(analyze_db))
        monkeypatch.setattr(tools_mod, "get_db", lambda: get_db(analyze_db))
        monkeypatch.setattr(db_mod, "DB_PATH", analyze_db)

        db = get_db(analyze_db)
        db.execute(
            "UPDATE documents SET source_url = 'https://test.lv/1' WHERE id = 1"
        )
        db.execute(
            "UPDATE documents SET source_url = 'https://test.lv/2' WHERE id = 2"
        )
        db.commit()
        analyses_before = db.execute("SELECT COUNT(*) FROM analyses").fetchone()[0]
        db.close()

        result = analyze_mod.save_analysis(
            pid=1,
            analysis_date="2026-04-11",
            sentiment=0.0,
            topics=["t"],
            quotes=[],
            brief="two claims, both succeed",
            confidence=0.5,
            claims=[
                {
                    "document_id": 1,
                    "topic": "Aizsardzība un drošība",
                    "stance": "atomicity happy path claim 1",
                    "confidence": 0.5,
                    "reasoning": "ok",
                    "salience": 0.5,
                },
                {
                    "document_id": 2,
                    "topic": "Aizsardzība un drošība",
                    "stance": "atomicity happy path claim 2",
                    "confidence": 0.5,
                    "reasoning": "ok",
                    "salience": 0.5,
                },
            ],
        )

        assert result["status"] == "success", result
        assert result["analysis_id"] is not None
        assert len(result["claim_ids"]) == 2

        db = get_db(analyze_db)
        analyses_after = db.execute("SELECT COUNT(*) FROM analyses").fetchone()[0]
        assert analyses_after == analyses_before + 1
        # Both source docs marked reviewed
        for doc_id in (1, 2):
            r = db.execute(
                "SELECT reviewed_at FROM documents WHERE id = ?", (doc_id,)
            ).fetchone()
            assert r["reviewed_at"] is not None, f"doc {doc_id} not reviewed"
        db.close()


class TestIndirectReferenceGate:
    """2026-04-22 soft gate — reasoning containing indirect-reference phrases
    gets a NEEDS_REVIEW marker prepended. Legitimate "netiešs citāts" must
    pass through untouched (would false-positive if we hard-dropped).
    """

    def test_marker_detection_hits(self):
        from src.analyze import _indirect_marker_in
        assert _indirect_marker_in("Bare retweet of @foo") == "bare retweet"
        assert _indirect_marker_in("Pašam nav ekstraktējamas pozīcijas — matcher error") == "pašam nav ekstraktēj"
        assert _indirect_marker_in("Pure retweet, no commentary") == "pure retweet"
        assert _indirect_marker_in("Subject does not speak here") == "does not speak"
        assert _indirect_marker_in("Tikai pieminē Siliņu, bet viņa nerunā") == "tikai pieminē"

    def test_marker_detection_misses(self):
        from src.analyze import _indirect_marker_in
        # "netiešs citāts" (indirect quote via journalist) is legitimate.
        # Dropping these would regress ~half of real saves.
        assert _indirect_marker_in("Netiešs citāts caur LETA — ministrs teica, ka...") is None
        assert _indirect_marker_in("Skaidrs, tiešs atbalsts politikai") is None
        assert _indirect_marker_in("") is None
        assert _indirect_marker_in(None) is None

    def test_marker_detection_skips_negated(self):
        """2026-04-23 #11286 regression: explicit denial of a marker must not
        trigger NEEDS_REVIEW. Extractor saying "(nav bare retweet)" is asserting
        the OPPOSITE of the marker condition.
        """
        from src.analyze import _indirect_marker_in
        # Lapsa #11286 exact pattern
        assert _indirect_marker_in(
            "Lapsas paša tvīts ar pievienotu tekstu (nav bare retweet). Tieša pirmās personas apsūdzība."
        ) is None
        assert _indirect_marker_in("Tas nav bare retweet, autors pievieno komentāru") is None
        assert _indirect_marker_in("This is not bare retweet — author adds commentary") is None
        # Markers themselves starting with "nav" must still trigger — the "nav"
        # is part of the marker, not a separate preceding negation.
        assert _indirect_marker_in("Ekstraktoram nav paša pozīcijas") == "nav paša pozīcij"
        # Positive baseline still works
        assert _indirect_marker_in("Tas ir bare retweet bez komentāra") == "bare retweet"

    def test_marker_detection_skips_ne_tikai(self):
        """2026-06-02: the Latvian "ne tikai / ne vien" ("not only") construction
        immediately before a marker negates it — "ne tikai pieminēts" means the
        politician is NOT ONLY mentioned (i.e. he IS the speaker). Two real
        false-positives (Kleinbergs, Rinkēvičs) tripped the "tikai pieminē"
        marker this way.
        """
        from src.analyze import _indirect_marker_in
        assert _indirect_marker_in("Kleinbergs ir runātājs, ne tikai pieminēts rakstā") is None
        assert _indirect_marker_in("Viņš ne tikai pieminē tēmu, bet pats formulē nostāju") is None
        # A genuine indirect "tikai pieminēts" (no preceding "ne") must still fire.
        assert _indirect_marker_in("Tikai pieminēts citā rakstā, pats nerunā") == "tikai pieminē"

    def test_marker_requires_left_word_boundary(self):
        """A marker stem must begin at a word boundary, not match as a
        word-internal substring. "tikai minē" must NOT match inside
        "kritikai minē" (kri+tikai minē), which the old substring scan did.
        """
        from src.analyze import _indirect_marker_in
        assert _indirect_marker_in("Kritikai minēšana raksta beigās ir asa") is None
        # boundary-aligned occurrence still fires
        assert _indirect_marker_in("Tikai minē vārdu, nekādas pozīcijas") == "tikai minē"

    def test_save_analysis_appends_needs_review(self, analyze_db, monkeypatch):
        import src.analyze as analyze_mod
        import src.tools as tools_mod
        import src.db as db_mod

        monkeypatch.setattr(analyze_mod, "get_db", lambda: get_db(analyze_db))
        monkeypatch.setattr(tools_mod, "get_db", lambda: get_db(analyze_db))
        monkeypatch.setattr(db_mod, "DB_PATH", analyze_db)

        db = get_db(analyze_db)
        db.execute("UPDATE documents SET source_url='https://t.lv/1' WHERE id=1")
        db.commit()
        db.close()

        result = analyze_mod.save_analysis(
            pid=1,
            analysis_date="2026-04-22",
            sentiment=0.0,
            topics=["t"],
            quotes=[],
            brief="indirect-reference gate test",
            confidence=0.5,
            claims=[
                {
                    "document_id": 1,
                    "topic": "Aizsardzība un drošība",
                    "stance": "Kritizē VARAM",
                    "confidence": 0.5,
                    "reasoning": "Pure retweet — subject does not speak here.",
                    "salience": 0.5,
                },
            ],
        )

        assert result["status"] == "success"
        assert len(result["claim_ids"]) == 1
        db = get_db(analyze_db)
        row = db.execute(
            "SELECT reasoning FROM claims WHERE id = ?", (result["claim_ids"][0],)
        ).fetchone()
        db.close()
        assert row["reasoning"].startswith("NEEDS_REVIEW:"), row["reasoning"]
        assert "pure retweet" in row["reasoning"].lower()

    def test_save_analysis_preserves_legitimate_indirect(self, analyze_db, monkeypatch):
        """A claim whose reasoning says 'netiešs citāts' (legitimate indirect
        citation) must NOT be flagged. Guards against false-positive hard-
        dropping that would regress ~half of real saves.
        """
        import src.analyze as analyze_mod
        import src.tools as tools_mod
        import src.db as db_mod

        monkeypatch.setattr(analyze_mod, "get_db", lambda: get_db(analyze_db))
        monkeypatch.setattr(tools_mod, "get_db", lambda: get_db(analyze_db))
        monkeypatch.setattr(db_mod, "DB_PATH", analyze_db)

        db = get_db(analyze_db)
        db.execute("UPDATE documents SET source_url='https://t.lv/1' WHERE id=1")
        db.commit()
        db.close()

        original_reasoning = "Netiešs citāts caur LETA, bet skaidra pozīcija par budžetu."
        result = analyze_mod.save_analysis(
            pid=1,
            analysis_date="2026-04-22",
            sentiment=0.0,
            topics=["t"],
            quotes=[],
            brief="legitimate indirect citation",
            confidence=0.5,
            claims=[
                {
                    "document_id": 1,
                    "topic": "Budžets un finanses",
                    "stance": "Atbalsta budžetu",
                    "confidence": 0.7,
                    "reasoning": original_reasoning,
                    "salience": 0.5,
                },
            ],
        )

        assert result["status"] == "success"
        db = get_db(analyze_db)
        row = db.execute(
            "SELECT reasoning FROM claims WHERE id = ?", (result["claim_ids"][0],)
        ).fetchone()
        db.close()
        assert row["reasoning"] == original_reasoning, (
            f"legitimate 'netiešs citāts' was incorrectly flagged: {row['reasoning']}"
        )


def test_save_analysis_passes_speaker_id(tmp_path, monkeypatch):
    """When a claim dict has 'speaker_id', save_analysis must forward it to store_claim."""
    from src.db import init_db, get_db
    from src.analyze import save_analysis
    import src.analyze as analyze_mod
    import src.tools as tools_mod
    import src.db as db_mod

    db_path = str(tmp_path / "test.db")
    init_db(db_path)

    # Redirect all DB access to tmp_path. Existing tests in this file use the
    # same three-patch pattern because get_db's default db_path arg is bound
    # at import time, so patching only DB_PATH isn't enough.
    monkeypatch.setattr(analyze_mod, "get_db", lambda: get_db(db_path))
    monkeypatch.setattr(tools_mod, "get_db", lambda: get_db(db_path))
    monkeypatch.setattr(db_mod, "DB_PATH", db_path)

    db = get_db(db_path)
    db.execute("INSERT INTO tracked_politicians (id, name, relationship_type) VALUES (1, 'Subjekts Politiķis', 'tracked')")
    db.execute("INSERT INTO tracked_politicians (id, name, relationship_type) VALUES (2, 'Komentētājs Ļūdzis', 'commentator')")
    db.execute("INSERT INTO documents (id, content, content_hash, source_url, platform) VALUES (1, 'Komentārs par subjektu ar garumzīmēm ā ē ī ū ņ.', 'hash-save-analysis-speaker-id', 'https://x.com/kom/status/1', 'twitter')")
    db.commit()
    db.close()

    result = save_analysis(
        pid=1,
        analysis_date="2026-04-23",
        sentiment=0.0,
        topics=["korupcija"],
        quotes=[],
        brief="Testa īss pārskats ar garumzīmēm ā ē ī ū ņ.",
        confidence=0.7,
        claims=[{
            "document_id": 1,
            "topic": "korupcija",
            "stance": "Apgalvo, ka subjekts iesaistīts — ar garumzīmēm ā ē ī ū.",
            "quote": None,
            "confidence": 0.7,
            "reasoning": "Komentētāja publisks apgalvojums ar garumzīmēm ā ē ī ū ņ.",
            "salience": 0.5,
            "source_url": "https://x.com/kom/status/1",
            "claim_type": "commentary",
            "speaker_id": 2,
        }],
    )
    assert result["status"] == "success", f"save_analysis failed: {result}"
    claim_id = result["claim_ids"][0]

    db = get_db(db_path)
    row = db.execute("SELECT speaker_id, claim_type FROM claims WHERE id = ?", (claim_id,)).fetchone()
    assert row["speaker_id"] == 2
    assert row["claim_type"] == "commentary"
    db.close()
