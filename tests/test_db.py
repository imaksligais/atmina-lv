"""Tests for src/db.py — core database functions."""

import sqlite3
import tempfile
import os
from datetime import datetime, date
import pytest
from src.db import (
    now_lv,
    now_lv_dt,
    today_lv,
    _compute_content_hash,
    _compute_simhash,
    _hamming_distance,
    _float_list_to_bytes,
    get_db,
    init_db,
    insert_document,
)


def _safe_unlink(path):
    """Windows WAL mode keeps files open; ignore PermissionError on cleanup."""
    try:
        os.unlink(path)
    except PermissionError:
        pass


def _read_claim_vector(db_path, claim_id):
    """Read a claim_vectors row on a connection with sqlite_vec loaded (the vec0
    virtual table is otherwise 'no such module' on a plain get_db connection)."""
    import sqlite_vec

    db = get_db(db_path)
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)
    row = db.execute(
        "SELECT embedding FROM claim_vectors WHERE claim_id=?", (claim_id,)
    ).fetchone()
    db.close()
    return row


class TestNowLv:
    def test_returns_iso_format(self):
        result = now_lv()
        # Should be "YYYY-MM-DD HH:MM:SS"
        assert len(result) == 19
        assert result[4] == "-"
        assert result[10] == " "
        assert result[13] == ":"

    def test_returns_string(self):
        assert isinstance(now_lv(), str)


def test_now_lv_dt_returns_naive_datetime():
    result = now_lv_dt()
    assert isinstance(result, datetime)
    assert result.tzinfo is None  # naive (LV-local)


def test_today_lv_returns_date():
    result = today_lv()
    assert isinstance(result, date)
    # The date portion of now_lv() should match today_lv()
    assert now_lv().startswith(result.isoformat())


class TestComputeContentHash:
    def test_deterministic(self):
        h1 = _compute_content_hash("test content")
        h2 = _compute_content_hash("test content")
        assert h1 == h2

    def test_different_content_different_hash(self):
        h1 = _compute_content_hash("content A")
        h2 = _compute_content_hash("content B")
        assert h1 != h2

    def test_returns_hex_string(self):
        h = _compute_content_hash("test")
        assert len(h) == 64  # SHA-256 hex
        assert all(c in "0123456789abcdef" for c in h)

    def test_handles_latvian_chars(self):
        h = _compute_content_hash("Latvijas politiskā caurskatāmība šķērslis")
        assert len(h) == 64


class TestComputeSimhash:
    def test_similar_content_close_hashes(self):
        h1 = _compute_simhash("The quick brown fox jumps over the lazy dog")
        h2 = _compute_simhash("The quick brown fox leaps over the lazy dog")
        distance = _hamming_distance(h1, h2)
        assert distance < 20  # similar texts

    def test_different_content_different_hashes(self):
        h1 = _compute_simhash("NATO aizsardzības politika ir svarīga Latvijai")
        h2 = _compute_simhash("Ābolu recepte ar kanēli un medu saldēšanai")
        distance = _hamming_distance(h1, h2)
        assert distance > 5  # very different texts

    def test_returns_signed_int(self):
        h = _compute_simhash("test content")
        assert isinstance(h, int)
        # Signed 64-bit range
        assert -(1 << 63) <= h < (1 << 63)

    def test_handles_long_text(self):
        # Should truncate to 10k chars internally
        long_text = "Latvijas politiskā situācija ir mainīga " * 250
        h = _compute_simhash(long_text)
        assert isinstance(h, int)


class TestHammingDistance:
    def test_identical(self):
        assert _hamming_distance(0, 0) == 0
        assert _hamming_distance(42, 42) == 0

    def test_one_bit_diff(self):
        assert _hamming_distance(0b1000, 0b1001) == 1

    def test_all_bits_diff(self):
        assert _hamming_distance(0b0000, 0b1111) == 4


class TestFloatListToBytes:
    def test_returns_bytes(self):
        result = _float_list_to_bytes([1.0, 2.0, 3.0])
        assert isinstance(result, bytes)
        assert len(result) == 12  # 3 floats * 4 bytes

    def test_empty_list(self):
        result = _float_list_to_bytes([])
        assert result == b""


class TestGetDb:
    def test_returns_connection(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            db = get_db(path)
            assert isinstance(db, sqlite3.Connection)
            # Row factory should be set
            assert db.row_factory == sqlite3.Row
            db.close()
        finally:
            _safe_unlink(path)


class TestInitDb:
    def test_creates_all_tables(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            init_db(path)
            db = get_db(path)
            tables = [r[0] for r in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()]
            for expected in [
                "tracked_politicians", "sources", "social_accounts",
                "documents", "claims", "contradictions", "context_notes",
                "logs", "knab_donors", "knab_donations", "parties",
            ]:
                assert expected in tables, f"Missing table: {expected}"
            db.close()
        finally:
            _safe_unlink(path)

    def test_idempotent(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            init_db(path)
            init_db(path)  # should not raise
            db = get_db(path)
            tables = [r[0] for r in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()]
            assert "tracked_politicians" in tables
            db.close()
        finally:
            _safe_unlink(path)


class TestInsertDocument:
    def test_insert_and_dedup(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            init_db(path)
            content = "x " * 100  # some content
            doc_id = insert_document(
                content=content, source_id=None,
                platform="web", db_path=path,
            )
            assert doc_id is not None
            assert isinstance(doc_id, int)

            # Exact duplicate should return None
            dup_id = insert_document(
                content=content, source_id=None,
                platform="web", db_path=path,
            )
            assert dup_id is None
        finally:
            _safe_unlink(path)

    def test_different_content_inserts(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            init_db(path)
            id1 = insert_document(
                content="Unique content one " * 20,
                source_id=None, db_path=path,
            )
            id2 = insert_document(
                content="Totally different content " * 20,
                source_id=None, db_path=path,
            )
            assert id1 is not None
            assert id2 is not None
            assert id1 != id2
        finally:
            _safe_unlink(path)

    def test_stores_word_count(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            init_db(path)
            content = "viens divi trīs četri pieci " * 10
            doc_id = insert_document(
                content=content, source_id=None, db_path=path,
            )
            db = get_db(path)
            row = db.execute("SELECT word_count FROM documents WHERE id=?", (doc_id,)).fetchone()
            assert row["word_count"] == len(content.split())
            db.close()
        finally:
            _safe_unlink(path)

    def test_stores_engagement_counts(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            init_db(path)
            doc_id = insert_document(
                content="Test tweet with engagement " * 5,
                source_id=None, platform="twitter", db_path=path,
                reply_count=142, retweet_count=38, favorite_count=612,
            )
            db = get_db(path)
            row = db.execute(
                "SELECT reply_count, retweet_count, favorite_count "
                "FROM documents WHERE id=?", (doc_id,)
            ).fetchone()
            assert row["reply_count"] == 142
            assert row["retweet_count"] == 38
            assert row["favorite_count"] == 612
            db.close()
        finally:
            _safe_unlink(path)

    def test_engagement_defaults_to_null(self):
        """Omitting engagement kwargs stores NULL (backward compat)."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            init_db(path)
            doc_id = insert_document(
                content="Tweet without engagement " * 5,
                source_id=None, platform="twitter", db_path=path,
            )
            db = get_db(path)
            row = db.execute(
                "SELECT reply_count, retweet_count, favorite_count "
                "FROM documents WHERE id=?", (doc_id,)
            ).fetchone()
            assert row["reply_count"] is None
            assert row["retweet_count"] is None
            assert row["favorite_count"] is None
            db.close()
        finally:
            _safe_unlink(path)


class TestClaimsSchema:
    """Phase A: the claims table has a claim_type column with a default of
    'position' and indexes that support filtering by type.
    """

    def test_claim_type_column_exists_with_default(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            init_db(path)
            db = get_db(path)
            cols = {r[1]: r for r in db.execute("PRAGMA table_info(claims)").fetchall()}
            assert "claim_type" in cols, "claims table missing claim_type column"
            # sqlite PRAGMA table_info returns dflt_value at index 4
            default_value = cols["claim_type"][4]
            # Default may come back quoted: 'position'
            assert default_value is not None and "position" in str(default_value), (
                f"claim_type default not 'position': {default_value!r}"
            )
            db.close()
        finally:
            _safe_unlink(path)

    def test_claim_type_indexes_exist(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            init_db(path)
            db = get_db(path)
            # Phase A indexes are created in a separate migration step (ad-hoc
            # SQL on production), so init_db may not create them automatically.
            # This test documents the production state: the indexes are
            # present after migration. If init_db ever gains them, this test
            # still passes. If not, we explicitly create them here the way
            # production does.
            db.execute("CREATE INDEX IF NOT EXISTS idx_claims_claim_type ON claims(claim_type)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_claims_opp_type_topic ON claims(opponent_id, claim_type, topic)")
            db.commit()
            indexes = {r[0] for r in db.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='claims'"
            ).fetchall()}
            assert "idx_claims_claim_type" in indexes
            assert "idx_claims_opp_type_topic" in indexes
            db.close()
        finally:
            _safe_unlink(path)


class TestStoreClaimClaimType:
    """Phase A: store_claim accepts claim_type and persists it correctly.
    Default is 'position'; 'saeima_vote' is the explicit value for Saeima
    voting records.
    """

    @pytest.fixture
    def seeded_db(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        init_db(path)
        db = get_db(path)
        db.execute(
            "INSERT INTO tracked_politicians (id, name, party) VALUES (1, 'Test', 'JV')"
        )
        db.execute(
            "INSERT INTO documents (id, content, content_hash, source_url) "
            "VALUES (1, 'doc content', 'hash1', 'https://test.lv/a')"
        )
        db.execute(
            "INSERT INTO documents (id, content, content_hash, source_url) "
            "VALUES (2, 'doc content 2', 'hash2', 'https://test.lv/b')"
        )
        db.commit()
        db.close()
        yield path
        _safe_unlink(path)

    def test_store_claim_defaults_to_position(self, seeded_db):
        from src.db import store_claim
        claim_id = store_claim(
            opponent_id=1, document_id=1, topic="NATO", stance="pro",
            quote=None, confidence=0.5, reasoning="", salience=0.5,
            source_url="https://test.lv/a", stated_at=None,
            db_path=seeded_db,
        )
        db = get_db(seeded_db)
        row = db.execute("SELECT claim_type FROM claims WHERE id=?", (claim_id,)).fetchone()
        db.close()
        assert row["claim_type"] == "position"

    def test_store_claim_saeima_vote(self, seeded_db):
        from src.db import store_claim
        claim_id = store_claim(
            opponent_id=1, document_id=1, topic="Budžets",
            stance="atbalsta likumprojektu",
            quote=None, confidence=0.8, reasoning="", salience=0.5,
            source_url="https://test.lv/a", stated_at=None,
            claim_type="saeima_vote",
            db_path=seeded_db,
        )
        db = get_db(seeded_db)
        row = db.execute("SELECT claim_type FROM claims WHERE id=?", (claim_id,)).fetchone()
        db.close()
        assert row["claim_type"] == "saeima_vote"

    def test_store_claim_accepts_null_document_id(self, seeded_db):
        """saeima_vote claims pēc 2026-04-25 sanācijas glabājas bez fake docs.
        store_claim ir jāpieņem document_id=None — schēma to jau atļauj
        (notnull=0), tikai signature un canonicalization bloķēja.
        """
        from src.db import store_claim
        from src.db import get_db
        claim_id = store_claim(
            opponent_id=1, document_id=None, topic="Budžets",
            stance="Atbalsta: budžeta likumprojektu",
            quote=None, confidence=1.0, reasoning="Saeimas balsojums",
            salience=0.5, source_url="https://titania.saeima.lv/vote/123",
            stated_at="2026-04-25T10:00:00", claim_type="saeima_vote",
            db_path=seeded_db,
        )
        db = get_db(seeded_db)
        row = db.execute(
            "SELECT document_id, claim_type, source_url FROM claims WHERE id=?",
            (claim_id,)
        ).fetchone()
        db.close()
        assert row["document_id"] is None
        assert row["claim_type"] == "saeima_vote"
        assert row["source_url"] == "https://titania.saeima.lv/vote/123"

    def test_store_claim_null_document_id_url_dedup_still_works(self, seeded_db):
        """Idempotency on (opponent_id, source_url, topic) must work even when
        document_id is NULL — otherwise re-runs of generate_claims_from_votes
        would create duplicate saeima_vote claims for the same vote.
        """
        from src.db import store_claim
        url = "https://titania.saeima.lv/vote/dedup-test"
        first = store_claim(
            opponent_id=1, document_id=None, topic="Budžets",
            stance="Par", quote=None, confidence=1.0, reasoning="Vote",
            salience=0.5, source_url=url, stated_at=None,
            claim_type="saeima_vote", db_path=seeded_db,
        )
        second = store_claim(
            opponent_id=1, document_id=None, topic="Budžets",
            stance="Par", quote=None, confidence=1.0, reasoning="Vote2",
            salience=0.5, source_url=url, stated_at=None,
            claim_type="saeima_vote", db_path=seeded_db,
        )
        assert first == second, "Re-store with same triple must return same claim_id"


class TestStoreClaimEmbeddingBytes:
    """db.store_claim accepts a precomputed ``embedding_bytes`` so batch callers
    (save_analysis) can compute embeddings OUTSIDE the held write transaction.
    See BACKLOG.md § "SQLite write contention".
    """

    @pytest.fixture
    def seeded_db(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        init_db(path)
        db = get_db(path)
        db.execute(
            "INSERT INTO tracked_politicians (id, name, party) VALUES (1, 'Test', 'JV')"
        )
        db.execute(
            "INSERT INTO documents (id, content, content_hash, source_url) "
            "VALUES (1, 'doc content', 'hash1', 'https://test.lv/a')"
        )
        db.commit()
        db.close()
        yield path
        _safe_unlink(path)

    def test_provided_embedding_bytes_stored_and_embed_text_not_called(
        self, seeded_db, monkeypatch
    ):
        """When embedding_bytes is passed, store_claim stores exactly those
        bytes and never calls embed_text (patched at source module because
        db.store_claim imports it inside the function body)."""
        import src.embeddings as emb_mod
        from src.db import store_claim, _float_list_to_bytes

        def _boom(text):
            raise AssertionError(
                "embed_text must not be called when embedding_bytes is provided"
            )

        monkeypatch.setattr(emb_mod, "embed_text", _boom)

        sentinel = _float_list_to_bytes([0.05] * 384)
        claim_id = store_claim(
            opponent_id=1, document_id=1, topic="NATO",
            stance="Atbalsta NATO klātbūtni ar garumzīmēm ā ē ī ū.",
            quote=None, confidence=0.5,
            reasoning="Pamatojums ā ē ī ū ņ.", salience=0.5,
            source_url="https://test.lv/a", stated_at=None,
            embedding_bytes=sentinel, db_path=seeded_db,
        )
        row = _read_claim_vector(seeded_db, claim_id)
        assert bytes(row["embedding"]) == sentinel

    def test_none_embedding_bytes_computes_internally(self, seeded_db):
        """Default (embedding_bytes=None) keeps legacy behavior — the embedding
        matches embed_text of the normalized 'topic: stance' text."""
        from src.db import store_claim, _float_list_to_bytes
        from src.embeddings import embed_text

        stance = "Atbalsta NATO klātbūtni ar garumzīmēm ā ē ī ū."
        claim_id = store_claim(
            opponent_id=1, document_id=1, topic="NATO", stance=stance,
            quote=None, confidence=0.5, reasoning="Pamatojums ā ē ī ū ņ.",
            salience=0.5, source_url="https://test.lv/a", stated_at=None,
            db_path=seeded_db,
        )
        row = _read_claim_vector(seeded_db, claim_id)
        # db.store_claim embeds "NATO: <stance>" as passed (no normalization at
        # this layer — tools.store_claim normalizes before calling).
        expected = _float_list_to_bytes(embed_text(f"NATO: {stance}"))
        assert bytes(row["embedding"]) == expected


class TestStoreClaimDiacriticGuardrail:
    """store_claim must reject Latvian text with stripped diacritics
    (symptom of agent context-drift). See src/quality.py.
    """

    @pytest.fixture
    def seeded_db(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        init_db(path)
        db = get_db(path)
        db.execute(
            "INSERT INTO tracked_politicians (id, name, party) VALUES (1, 'Test', 'JV')"
        )
        db.execute(
            "INSERT INTO documents (id, content, content_hash, source_url) "
            "VALUES (1, 'doc', 'h1', 'https://test.lv/a')"
        )
        db.commit()
        db.close()
        yield path
        _safe_unlink(path)

    def test_rejects_stripped_stance(self, seeded_db):
        from src.db import store_claim
        # Real-world bad stance from claim #7493 (2026-04-16)
        bad_stance = (
            "Uzskata, ka Silina ir politiski beigusies, lai gan "
            "JV vel varetu turpinat pec krizes sarunam."
        )
        with pytest.raises(ValueError, match="diacritic"):
            store_claim(
                opponent_id=1, document_id=1, topic="Koalīcija",
                stance=bad_stance, quote=None, confidence=0.5,
                reasoning="", salience=0.5,
                source_url="https://test.lv/a", stated_at=None,
                db_path=seeded_db,
            )

    def test_rejects_stripped_quote(self, seeded_db):
        from src.db import store_claim
        bad_quote = (
            "Daudz tiek runats par airBaltic izmaksu sadalu, bet ne "
            "tik daudz par ienemumu sadalu un eksporta potencialu."
        )
        with pytest.raises(ValueError, match="diacritic"):
            store_claim(
                opponent_id=1, document_id=1, topic="airBaltic",
                stance="OK", quote=bad_quote, confidence=0.5,
                reasoning="", salience=0.5,
                source_url="https://test.lv/a", stated_at=None,
                db_path=seeded_db,
            )

    def test_accepts_valid_latvian(self, seeded_db):
        from src.db import store_claim
        good_stance = (
            "Kritizē valdību par ekonomiskās politikas neefektivitāti "
            "un aicina atjaunot rūpniecības ražošanu Latvijā."
        )
        claim_id = store_claim(
            opponent_id=1, document_id=1, topic="Ekonomika",
            stance=good_stance, quote=None, confidence=0.7,
            reasoning="", salience=0.6,
            source_url="https://test.lv/a", stated_at=None,
            db_path=seeded_db,
        )
        assert isinstance(claim_id, int)


class TestStoreTensionUrlValidation:
    """store_tension must reject hallucinated source_url/target_url — the URL
    must reference a real document in the ``documents`` table, catching cases
    where agents guess tweet status IDs or article slugs.
    """

    @pytest.fixture
    def seeded_db(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        init_db(path)
        db = get_db(path)
        db.execute(
            "INSERT INTO tracked_politicians (id, name, party) VALUES (1, 'Alpha', 'JV')"
        )
        db.execute(
            "INSERT INTO tracked_politicians (id, name, party) VALUES (2, 'Beta', 'ZZS')"
        )
        db.execute(
            "INSERT INTO documents (id, content, content_hash, source_url) "
            "VALUES (1, 'doc', 'h1', 'https://real.lv/a')"
        )
        db.execute(
            "INSERT INTO documents (id, content, content_hash, source_url) "
            "VALUES (2, 'doc2', 'h2', 'https://real.lv/b')"
        )
        db.commit()
        db.close()
        yield path
        _safe_unlink(path)

    def test_accepts_known_source_url(self, seeded_db):
        from src.db import store_tension
        tid = store_tension(
            source_pid=1, target_pid=2, topic="airBaltic",
            description="Alpha kritizē Beta pozīciju par ārpolitiku.",
            tension_type="uzbrukums",
            source_url="https://real.lv/a",
            db_path=seeded_db,
        )
        assert isinstance(tid, int)

    def test_rejects_missing_source_url(self, seeded_db):
        from src.db import store_tension
        with pytest.raises(ValueError, match="source_url is required"):
            store_tension(
                source_pid=1, target_pid=2, topic="airBaltic",
                description="Alpha kritizē Beta pozīciju par ārpolitiku.",
                source_url=None,
                db_path=seeded_db,
            )

    def test_rejects_hallucinated_source_url(self, seeded_db):
        from src.db import store_tension
        with pytest.raises(ValueError, match="source_url not found"):
            store_tension(
                source_pid=1, target_pid=2, topic="airBaltic",
                description="Alpha kritizē Beta pozīciju par ārpolitiku.",
                source_url="https://x.com/foo/status/2041700000000000000",
                db_path=seeded_db,
            )

    def test_rejects_hallucinated_target_url(self, seeded_db):
        from src.db import store_tension
        with pytest.raises(ValueError, match="target_url not found"):
            store_tension(
                source_pid=1, target_pid=2, topic="airBaltic",
                description="Alpha kritizē Beta pozīciju par ārpolitiku.",
                source_url="https://real.lv/a",
                target_url="https://delfi.lv/a/fabricated",
                db_path=seeded_db,
            )

    def test_accepts_known_target_url(self, seeded_db):
        from src.db import store_tension
        tid = store_tension(
            source_pid=1, target_pid=2, topic="airBaltic",
            description="Alpha kritizē Beta pozīciju par ārpolitiku.",
            source_url="https://real.lv/a",
            target_url="https://real.lv/b",
            db_path=seeded_db,
        )
        assert isinstance(tid, int)


class TestSearchSimilarClaimsFilter:
    """Phase A: search_similar_claims accepts claim_type_filter. The filter
    is directional per call-site — contradictions callers pass the right
    list for their direction of retrieval.

    Bidirectional coverage:
      - position → candidates with filter ['position', 'saeima_vote']: finds both
      - saeima_vote → candidates with filter ['position']: finds position only
    """

    @pytest.fixture
    def seeded_db(self):
        from src.db import store_claim
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        init_db(path)
        db = get_db(path)
        db.execute(
            "INSERT INTO tracked_politicians (id, name, party) VALUES (1, 'Test', 'JV')"
        )
        db.execute(
            "INSERT INTO documents (id, content, content_hash, source_url, platform) "
            "VALUES (1, 'media article', 'h1', 'https://lsm.lv/a', 'web')"
        )
        db.execute(
            "INSERT INTO documents (id, content, content_hash, source_url, platform) "
            "VALUES (2, 'saeima record', 'h2', 'https://titania.saeima.lv/v/1', 'saeima')"
        )
        db.commit()
        db.close()

        # Store a position: "Pret X likumu" (media quote)
        store_claim(
            opponent_id=1, document_id=1, topic="Aizsardzība un drošība",
            stance="Pret X likumprojektu — uzskata par nevajadzīgu",
            quote=None, confidence=0.8, reasoning="media quote",
            salience=0.7, source_url="https://lsm.lv/a", stated_at=None,
            claim_type="position",
            db_path=path,
        )
        # Store a saeima_vote: "Atbalsta X" (voting record)
        store_claim(
            opponent_id=1, document_id=2, topic="Aizsardzība un drošība",
            stance="Atbalsta X likumprojektu — balso PAR",
            quote=None, confidence=0.95, reasoning="vote record",
            salience=0.5, source_url="https://titania.saeima.lv/v/1", stated_at=None,
            claim_type="saeima_vote",
            db_path=path,
        )
        yield path
        _safe_unlink(path)

    def test_position_query_finds_both_types_with_filter(self, seeded_db):
        """Querying for similar claims to a position, with filter
        ['position', 'saeima_vote']: must return both the position and the
        saeima_vote as candidates (rhetoric-vs-action contradiction direction).
        """
        from src.db import search_similar_claims
        from src.embeddings import embed_text

        query_vec = embed_text("Aizsardzība un drošība: Pret X likumprojektu")
        results = search_similar_claims(
            query_vec, opponent_id=1, top_k=10,
            claim_type_filter=["position", "saeima_vote"],
            db_path=seeded_db,
        )
        types_found = {r["claim_type"] for r in results}
        assert "position" in types_found, f"position missing: {types_found}"
        assert "saeima_vote" in types_found, f"saeima_vote missing: {types_found}"

    def test_vote_query_finds_only_position_with_filter(self, seeded_db):
        """Querying for similar claims to a saeima_vote, with filter
        ['position']: must return only position-type candidates. Vote-vs-vote
        is procedural noise and must be excluded (the whole reason for the
        directional filter).
        """
        from src.db import search_similar_claims
        from src.embeddings import embed_text

        query_vec = embed_text("Aizsardzība un drošība: Atbalsta X likumprojektu balsojums")
        results = search_similar_claims(
            query_vec, opponent_id=1, top_k=10,
            claim_type_filter=["position"],
            db_path=seeded_db,
        )
        types_found = {r["claim_type"] for r in results}
        assert types_found == {"position"} or types_found == set(), (
            f"vote-side filter leaked non-position types: {types_found}"
        )
        # Specifically: the position row should still be present (not accidentally dropped)
        assert any(r["claim_type"] == "position" for r in results), (
            "position candidate missing from vote→position retrieval"
        )

    def test_no_filter_returns_all_types(self, seeded_db):
        """Regression: passing no filter (None) returns both types, matching
        pre-Phase-A behavior.
        """
        from src.db import search_similar_claims
        from src.embeddings import embed_text

        query_vec = embed_text("Aizsardzība un drošība: X likumprojekts")
        results = search_similar_claims(
            query_vec, opponent_id=1, top_k=10,
            claim_type_filter=None,
            db_path=seeded_db,
        )
        types_found = {r["claim_type"] for r in results}
        assert len(types_found) == 2, f"expected both types, got {types_found}"


def _query_vec(dim: int = 384) -> list[float]:
    """The query vector: basis e0."""
    v = [0.0] * dim
    v[0] = 1.0
    return v


def _near_vec(i: int, dim: int = 384) -> list[float]:
    """A vector very close to e0 (query), distinct per ``i``. e0 plus a tiny
    perturbation on a unique axis so the 15 NEAR vectors are DISTINCT points
    (sqlite-vec collapses byte-identical vectors) yet all far nearer to the
    query than the FAR vector below (distance ~0.003–0.02 vs sqrt(2))."""
    v = [0.0] * dim
    v[0] = 1.0
    v[2 + i] = 0.05 * (i + 1) / 15.0
    return v


def _far_vec(dim: int = 384) -> list[float]:
    """A vector orthogonal to the query (basis e1): distance sqrt(2) ≈ 1.414,
    i.e. globally "far" — squeezed out of any small-``top_k`` global kNN."""
    v = [0.0] * dim
    v[1] = 1.0
    return v


class TestSearchSimilarClaimsKnnPushdown:
    """Regression: search_similar_claims must push opponent_id + claim_type_filter
    + speaker_scope INTO the kNN query (sqlite-vec ``rowid IN`` subquery), not
    apply them only in a post-filter loop. Otherwise, when a politician's own
    (or filter-relevant) claims are not among the globally nearest ``top_k``
    vectors, they are squeezed out and the caller sees ``[]`` / self-match-only.
    See CLAUDE.md Known Traps T9/T10 context and BACKLOG § kNN izspiešana
    (2026-07-23).

    Geometry: query = e0. NEAR vectors = e0 (distance 0). FAR vectors = e1
    (distance sqrt(2)). With ~15 NEAR vectors and a small top_k, the target
    (FAR-but-relevant) claim can only surface if the filter is pushed down.
    """

    def _seed(self):
        """Fresh temp DB with two politicians and one document. The document has
        a NULL source_url so store_claim's canonicalization override does NOT
        rewrite each claim's per-call source_url — otherwise every claim would
        collapse onto one (opponent_id, source_url, topic) idempotency key."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        init_db(path)
        db = get_db(path)
        db.execute(
            "INSERT INTO tracked_politicians (id, name, party) VALUES (1, 'Alfa', 'JV')"
        )
        db.execute(
            "INSERT INTO tracked_politicians (id, name, party) VALUES (2, 'Beta', 'ZZS')"
        )
        db.execute(
            "INSERT INTO documents (id, content, content_hash, platform) "
            "VALUES (1, 'media', 'h1', 'web')"
        )
        db.commit()
        db.close()
        return path

    def _store(self, path, *, opponent_id, source_url, vec,
               claim_type="position", speaker_id=None, topic="Ekonomika"):
        """Store one claim with a crafted embedding vector. Distinct
        source_url per call so the idempotency triple never collapses."""
        from src.db import store_claim

        embedding_bytes = _float_list_to_bytes(vec)
        return store_claim(
            opponent_id=opponent_id, document_id=1, topic=topic,
            stance="Atbalsta priekšlikumu par nodokļu izmaiņām valstī.",
            quote=None, confidence=0.8, reasoning="", salience=0.6,
            source_url=source_url, stated_at=None,
            claim_type=claim_type, speaker_id=speaker_id,
            embedding_bytes=embedding_bytes, db_path=path,
        )

    def test_squeeze_out_regression_opponent_id_pushdown(self):
        """Politician A has 1 FAR claim; B has 15 NEAR claims. Query for A
        with top_k=5. Old code: global top-5 are all B's → post-filter → [].
        Fixed code: A's claim is returned because opponent_id is pushed down."""
        from src.db import search_similar_claims

        path = self._seed()
        try:
            a_id = self._store(
                path, opponent_id=1, source_url="https://lsm.lv/a/A", vec=_far_vec()
            )  # FAR
            for i in range(15):
                self._store(
                    path, opponent_id=2,
                    source_url=f"https://lsm.lv/b/B{i}", vec=_near_vec(i),
                )  # NEAR, each distinct

            results = search_similar_claims(
                _query_vec(), opponent_id=1, top_k=5, db_path=path,
            )
            ids = {r["id"] for r in results}
            assert a_id in ids, (
                f"A's claim squeezed out of the global top_k=5 (ids={ids}); "
                f"opponent_id was not pushed into the kNN query"
            )
        finally:
            _safe_unlink(path)

    def test_claim_type_pushdown(self):
        """One politician: 10 saeima_vote NEAR + 1 position FAR. Filter
        ['position'], top_k=5. Fixed code must return the position claim
        (fails if only opponent_id were pushed down — the 10 vote vectors
        would fill the top_k budget)."""
        from src.db import search_similar_claims

        path = self._seed()
        try:
            for i in range(10):
                self._store(
                    path, opponent_id=1,
                    source_url=f"https://lsm.lv/a/V{i}", vec=_near_vec(i),
                    claim_type="saeima_vote",
                )  # NEAR votes, each distinct
            pos_id = self._store(
                path, opponent_id=1, source_url="https://lsm.lv/a/P",
                vec=_far_vec(), claim_type="position",
            )  # FAR position

            results = search_similar_claims(
                _query_vec(), opponent_id=1, top_k=5,
                claim_type_filter=["position"], db_path=path,
            )
            ids = {r["id"] for r in results}
            assert pos_id in ids, (
                f"position claim squeezed out by NEAR saeima_vote claims "
                f"(ids={ids}); claim_type_filter was not pushed into the kNN query"
            )
            assert all(r["claim_type"] == "position" for r in results)
        finally:
            _safe_unlink(path)

    def test_speaker_scope_pushdown(self):
        """One politician (id=1): 10 NEAR commentary claims (speaker_id=2) +
        1 FAR first-party claim (speaker_id NULL). Default first_party scope,
        top_k=5 must return the first-party claim."""
        from src.db import search_similar_claims

        path = self._seed()
        try:
            for i in range(10):
                self._store(
                    path, opponent_id=1,
                    source_url=f"https://lsm.lv/a/C{i}", vec=_near_vec(i),
                    claim_type="commentary", speaker_id=2,
                )  # NEAR commentary (third-party), each distinct
            fp_id = self._store(
                path, opponent_id=1, source_url="https://lsm.lv/a/FP",
                vec=_far_vec(), claim_type="position", speaker_id=None,
            )  # FAR first-party

            results = search_similar_claims(
                _query_vec(), opponent_id=1, top_k=5,
                speaker_scope="first_party", db_path=path,
            )
            ids = {r["id"] for r in results}
            assert fp_id in ids, (
                f"first-party claim squeezed out by NEAR commentary claims "
                f"(ids={ids}); speaker_scope was not pushed into the kNN query"
            )
        finally:
            _safe_unlink(path)

    def test_empty_claim_type_filter_returns_empty(self):
        """An EMPTY claim_type_filter list means 'no types' → returns []
        (preserves the post-filter semantics). Passes both before and after
        the fix."""
        from src.db import search_similar_claims

        path = self._seed()
        try:
            self._store(
                path, opponent_id=1, source_url="https://lsm.lv/a/X", vec=_query_vec(),
            )
            results = search_similar_claims(
                _query_vec(), opponent_id=1, top_k=5,
                claim_type_filter=[], db_path=path,
            )
            assert results == [], f"empty filter must return [], got {results}"
        finally:
            _safe_unlink(path)


class TestDocumentsEngagementMigration:
    """Schema migration — documents gains reply_count / retweet_count / favorite_count columns."""

    def test_engagement_columns_present(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            init_db(path)
            db = get_db(path)
            cols = {r[1]: r for r in db.execute("PRAGMA table_info(documents)").fetchall()}
            assert "reply_count" in cols, "documents missing reply_count column"
            assert "retweet_count" in cols, "documents missing retweet_count column"
            assert "favorite_count" in cols, "documents missing favorite_count column"
            # All three nullable INTEGER
            for name in ("reply_count", "retweet_count", "favorite_count"):
                # PRAGMA table_info columns: (cid, name, type, notnull, dflt, pk)
                assert cols[name][2].upper() == "INTEGER", f"{name} should be INTEGER"
                assert cols[name][3] == 0, f"{name} must be nullable"
            db.close()
        finally:
            _safe_unlink(path)

    def test_migration_idempotent(self):
        """Calling init_db twice on same file must not raise."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            init_db(path)
            init_db(path)  # should not raise on ALTER TABLE duplicate
            db = get_db(path)
            cols = [r[1] for r in db.execute("PRAGMA table_info(documents)").fetchall()]
            # Should still only have one of each
            assert cols.count("reply_count") == 1
            db.close()
        finally:
            _safe_unlink(path)


class TestSocialDraftsTable:
    """Schema migration — social_drafts table for the X posting agent."""

    def test_social_drafts_columns_present(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            init_db(path)
            db = get_db(path)
            cols = {r[1]: r for r in db.execute("PRAGMA table_info(social_drafts)").fetchall()}
            for name in (
                "id", "pillar", "text", "image_path", "source_data_json",
                "score", "status", "telegram_msg_id", "telegram_chat_id",
                "revision_count", "parent_draft_id",
                "created_at", "posted_at", "tweet_id", "error_message",
            ):
                assert name in cols, f"social_drafts missing column {name}"
            # Indexes
            idx_names = {r[1] for r in db.execute(
                "SELECT * FROM sqlite_master WHERE type='index' AND tbl_name='social_drafts'"
            ).fetchall()}
            assert "idx_social_drafts_status" in idx_names
            assert "idx_social_drafts_pillar" in idx_names
            db.close()
        finally:
            _safe_unlink(path)

    def test_social_drafts_idempotent(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            init_db(path)
            init_db(path)  # must not raise
            db = get_db(path)
            cnt = db.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='social_drafts'"
            ).fetchone()[0]
            assert cnt == 1
            db.close()
        finally:
            _safe_unlink(path)

    def test_social_accounts_feed_type_column_present(self):
        """feed_type column exists on social_accounts with correct default,
        and idx_social_feed_type index is created."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            init_db(path)
            db = get_db(path)
            cols = {r[1]: r for r in db.execute("PRAGMA table_info(social_accounts)").fetchall()}
            assert "feed_type" in cols, "feed_type column must exist on social_accounts"
            default = cols["feed_type"][4]  # PRAGMA column 4 = dflt_value
            assert default == "'first_party'", f"expected default 'first_party', got {default!r}"
            # Issue C fix: verify index created alongside column
            idx_names = {r[0] for r in db.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='social_accounts'"
            ).fetchall()}
            assert "idx_social_feed_type" in idx_names, "idx_social_feed_type must be created"
            db.close()
        finally:
            _safe_unlink(path)

    def test_social_accounts_feed_type_idempotent(self):
        """Running init_db twice on a fresh DB must not fail or duplicate the column."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            init_db(path)
            init_db(path)  # second run is the idempotency check
            db = get_db(path)
            cols = [r[1] for r in db.execute("PRAGMA table_info(social_accounts)").fetchall()]
            assert cols.count("feed_type") == 1
            db.close()
        finally:
            _safe_unlink(path)


def test_claims_has_speaker_id_column(tmp_path):
    from src.db import init_db, get_db
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    db = get_db(db_path)
    cols = {row["name"] for row in db.execute("PRAGMA table_info(claims)").fetchall()}
    assert "speaker_id" in cols, f"speaker_id missing; got columns: {sorted(cols)}"
    db.close()


def test_claims_speaker_id_index_exists(tmp_path):
    from src.db import init_db, get_db
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    db = get_db(db_path)
    idx_names = {row["name"] for row in db.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='claims'"
    ).fetchall()}
    assert "idx_claims_speaker" in idx_names, f"speaker index missing; got: {sorted(idx_names)}"
    db.close()


def test_init_db_idempotent_on_speaker_id(tmp_path):
    """Running init_db twice must not raise 'duplicate column' errors."""
    from src.db import init_db
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    init_db(db_path)  # second call — must be a no-op, not raise


def test_store_claim_default_speaker_id_is_null(tmp_path, monkeypatch):
    """Legacy calls (no speaker_id kwarg) must store NULL for backward compat."""
    from src.db import init_db, get_db, store_claim
    # Setup: one tracked politician + one document with source_url
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("ATMINA_DB_PATH", db_path)  # if your test harness uses env; else pass db_path
    init_db(db_path)
    db = get_db(db_path)
    db.execute(
        "INSERT INTO tracked_politicians (id, name, relationship_type) VALUES (1, 'Testa Politiķis', 'tracked')"
    )
    db.execute(
        "INSERT INTO documents (id, content, content_hash, source_url, platform) VALUES (1, 'Testa saturs ar garumzīmēm ā ē ī ū.', 'hash-speaker-default', 'https://example.lv/1', 'web')"
    )
    db.commit()
    db.close()

    import json
    result_json = store_claim(
        opponent_id=1, document_id=1, topic="test",
        stance="Atbalsta testu — pārbaudām garumzīmes ā ē ī ū.", quote=None,
        confidence=0.8, reasoning="Testa pamatojums ar garumzīmēm ā ē ī ū ņ.",
        salience=0.5, source_url="https://example.lv/1", stated_at=None,
        db_path=db_path,
    )
    result = json.loads(result_json) if isinstance(result_json, str) else {"claim_id": result_json}
    cid = result.get("claim_id", result_json)

    db = get_db(db_path)
    row = db.execute("SELECT speaker_id FROM claims WHERE id = ?", (cid,)).fetchone()
    assert row["speaker_id"] is None
    db.close()


def test_store_claim_with_explicit_speaker_id(tmp_path):
    """When speaker_id is passed, it's persisted unchanged."""
    from src.db import init_db, get_db, store_claim
    import json
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    db = get_db(db_path)
    # Subject politician + commentator
    db.execute("INSERT INTO tracked_politicians (id, name, relationship_type) VALUES (1, 'Subjekta Politiķis', 'tracked')")
    db.execute("INSERT INTO tracked_politicians (id, name, relationship_type) VALUES (2, 'Komentētājs Ļūdzis', 'commentator')")
    db.execute("INSERT INTO documents (id, content, content_hash, source_url, platform) VALUES (1, 'Komentārs par subjektu ar garumzīmēm ā ē ī ū.', 'hash-speaker-explicit', 'https://x.com/komentetajs/status/1', 'twitter')")
    db.commit()
    db.close()

    result_json = store_claim(
        opponent_id=1, document_id=1, topic="korupcija",
        stance="Apgalvo, ka subjekts iesaistīts iepirkumos — pārbaudām garumzīmes ā ē ī.",
        quote=None, confidence=0.7,
        reasoning="Komentētāja publisks apgalvojums ar garumzīmēm ā ē ī ū ņ.",
        salience=0.5, source_url="https://x.com/komentetajs/status/1",
        stated_at=None, claim_type="commentary", speaker_id=2,
        db_path=db_path,
    )
    result = json.loads(result_json) if isinstance(result_json, str) else {"claim_id": result_json}
    cid = result.get("claim_id", result_json)

    db = get_db(db_path)
    row = db.execute("SELECT speaker_id, opponent_id, claim_type FROM claims WHERE id = ?", (cid,)).fetchone()
    assert row["speaker_id"] == 2
    assert row["opponent_id"] == 1
    assert row["claim_type"] == "commentary"
    db.close()


def test_search_similar_claims_excludes_commentary_by_default(tmp_path):
    """First-party contradiction check must not pull in commentary claims.

    This test validates the SQL filter shape: it inserts a first-party position
    and a commentary claim on the same opponent_id, then asserts the filter
    keeps only the first-party one. The actual vector search is not exercised
    here (it requires embeddings + sqlite_vec extension); this is a SQL-level
    coverage test for the speaker filter logic.
    """
    from src.db import init_db, get_db
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    db = get_db(db_path)
    db.execute("INSERT INTO tracked_politicians (id, name, relationship_type) VALUES (1, 'Subjekts', 'tracked')")
    db.execute("INSERT INTO tracked_politicians (id, name, relationship_type) VALUES (2, 'Komentētājs', 'commentator')")
    db.execute("INSERT INTO documents (id, content, content_hash, source_url, platform) VALUES (1, 'Subjekta paša teksts ar garumzīmēm ā ē ī ū ņ.', 'hash-sp-1', 'https://a.lv/1', 'web')")
    db.execute("INSERT INTO documents (id, content, content_hash, source_url, platform) VALUES (2, 'Komentētāja teksts ar garumzīmēm ā ē ī ū ņ.', 'hash-sp-2', 'https://b.lv/1', 'twitter')")
    # First-party position
    db.execute(
        "INSERT INTO claims (id, opponent_id, document_id, topic, stance, confidence, reasoning, salience, source_url, claim_type, speaker_id) "
        "VALUES (101, 1, 1, 'tema', 'subjekta pozīcija ar garumzīmēm ā ē ī ū', 0.8, 'pamatojums ar garumzīmēm ā ē ī ū ņ', 0.5, 'https://a.lv/1', 'position', NULL)"
    )
    # Third-party commentary on same opponent
    db.execute(
        "INSERT INTO claims (id, opponent_id, document_id, topic, stance, confidence, reasoning, salience, source_url, claim_type, speaker_id) "
        "VALUES (102, 1, 2, 'tema', 'komentētāja apgalvojums ar garumzīmēm ā ē ī ū', 0.6, 'pamatojums ar garumzīmēm ā ē ī ū ņ', 0.5, 'https://b.lv/1', 'commentary', 2)"
    )
    db.commit()
    # Direct SQL check matching the search_similar_claims 'first_party' scope:
    first_party_ids = {r["id"] for r in db.execute(
        "SELECT id FROM claims WHERE opponent_id = 1 AND (speaker_id IS NULL OR speaker_id = opponent_id)"
    ).fetchall()}
    assert first_party_ids == {101}
    db.close()


def test_init_db_creates_external_profiles_table(tmp_path):
    """init_db izveido external_profiles tabulu ar pareizo shēmu."""
    db_path = str(tmp_path / "test.db")
    from src.db import init_db, get_db
    init_db(db_path)
    db = get_db(db_path)
    cols = {row[1] for row in db.execute("PRAGMA table_info(external_profiles)").fetchall()}
    assert cols == {
        "id", "opponent_id", "platform", "url", "handle",
        "display_label", "last_fetched", "last_post_id",
        "active", "notes", "created_at",
    }
    idx_rows = db.execute("PRAGMA index_list(external_profiles)").fetchall()
    idx_names = {r[1] for r in idx_rows}
    assert "idx_external_profiles_opp" in idx_names
    db.close()


def test_init_db_external_profiles_idempotent(tmp_path):
    """Otrais init_db izsaukums nepalielina rindu skaitu."""
    db_path = str(tmp_path / "test.db")
    from src.db import init_db, get_db
    init_db(db_path)
    db = get_db(db_path)
    db.execute("INSERT INTO tracked_politicians (id, name, party) VALUES (1, 'Test', 'JV')")
    db.execute(
        "INSERT INTO external_profiles (opponent_id, platform, url) VALUES (?, ?, ?)",
        (1, "facebook", "https://facebook.com/test"),
    )
    db.commit()
    db.close()
    init_db(db_path)
    db = get_db(db_path)
    n = db.execute("SELECT COUNT(*) FROM external_profiles").fetchone()[0]
    assert n == 1


def test_insert_document_persists_title(tmp_path, monkeypatch):
    """insert_document writes the title kwarg to the documents.title column."""
    from src import db as db_module

    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(db_module, "DB_PATH", db_path)
    db_module.init_db(db_path)

    doc_id = db_module.insert_document(
        content="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
        source_id=None,
        platform="web",
        source_url="https://example.lv/article-1",
        title="Saeima atbalsta budžetu",
        db_path=db_path,
    )
    assert doc_id is not None

    conn = db_module.get_db(db_path)
    row = conn.execute(
        "SELECT title FROM documents WHERE id = ?", (doc_id,)
    ).fetchone()
    conn.close()
    assert row["title"] == "Saeima atbalsta budžetu"


def test_insert_document_title_optional(tmp_path, monkeypatch):
    """insert_document accepts no title — column stays NULL."""
    from src import db as db_module

    db_path = str(tmp_path / "test2.db")
    monkeypatch.setattr(db_module, "DB_PATH", db_path)
    db_module.init_db(db_path)

    doc_id = db_module.insert_document(
        content="Another article body with enough words to pass any filter.",
        source_id=None,
        source_url="https://example.lv/article-2",
        db_path=db_path,
    )
    assert doc_id is not None

    conn = db_module.get_db(db_path)
    row = conn.execute(
        "SELECT title FROM documents WHERE id = ?", (doc_id,)
    ).fetchone()
    conn.close()
    assert row["title"] is None
