"""Regression tests for post-launch debt fixes.

Covers:
  - Bug C: ``get_pending_politicians`` must filter by ``reviewed_at``,
    ``role='subject'``, and exclude inactive politicians.
  - Bug D: ``store_claim`` must reject unknown and inactive politicians
    with a loud ``ValueError``.

These tests exist to lock in the semantics introduced during the 2026-04-10
pre-launch cleanup. If future refactors break them, reconsider carefully —
the prior behavior caused a 100% false-positive pending pool and silent
claim assignment to sentinel entities like 'Nepareizais'.
"""

import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from src.db import get_db, init_db, store_claim


def _safe_unlink(path):
    try:
        os.unlink(path)
    except PermissionError:
        pass


# ─── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def fixtures_db():
    """A fresh DB with active, inactive, and sentinel politicians,
    plus documents in all the relevant (role, reviewed_at) states."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    db = get_db(path)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    old = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")

    # Politicians: one active, one inactive (sentinel-like), one unknown id
    db.execute("""INSERT INTO tracked_politicians (id, name, party, relationship_type)
                  VALUES (1, 'Aktīvais', 'JV', 'coalition_partner')""")
    db.execute("""INSERT INTO tracked_politicians (id, name, party, relationship_type)
                  VALUES (2, 'Nepareizais', NULL, 'inactive')""")
    db.execute("""INSERT INTO tracked_politicians (id, name, party, relationship_type)
                  VALUES (3, 'Otrais aktīvais', 'PRO', 'opponent')""")

    # Documents in different states
    # doc 1: fresh, role=subject, unreviewed → SHOULD appear as pending
    db.execute(
        "INSERT INTO documents (id, content, content_hash, scraped_at, reviewed_at) "
        "VALUES (1, 'c1', 'h1', ?, NULL)", (now,),
    )
    # doc 2: fresh, role=subject, ALREADY reviewed → should NOT appear
    db.execute(
        "INSERT INTO documents (id, content, content_hash, scraped_at, reviewed_at) "
        "VALUES (2, 'c2', 'h2', ?, ?)", (now, now),
    )
    # doc 3: fresh, role=mentioned (not subject), unreviewed → should NOT appear
    db.execute(
        "INSERT INTO documents (id, content, content_hash, scraped_at, reviewed_at) "
        "VALUES (3, 'c3', 'h3', ?, NULL)", (now,),
    )
    # doc 4: subject for the inactive sentinel, unreviewed → should NOT appear
    db.execute(
        "INSERT INTO documents (id, content, content_hash, scraped_at, reviewed_at) "
        "VALUES (4, 'c4', 'h4', ?, NULL)", (now,),
    )
    # doc 5: old (beyond window) → should NOT appear
    db.execute(
        "INSERT INTO documents (id, content, content_hash, scraped_at, reviewed_at) "
        "VALUES (5, 'c5', 'h5', ?, NULL)", (old,),
    )

    db.execute("INSERT INTO document_politicians (document_id, politician_id, role) VALUES (1, 1, 'subject')")
    db.execute("INSERT INTO document_politicians (document_id, politician_id, role) VALUES (2, 1, 'subject')")
    db.execute("INSERT INTO document_politicians (document_id, politician_id, role) VALUES (3, 1, 'mentioned')")
    db.execute("INSERT INTO document_politicians (document_id, politician_id, role) VALUES (4, 2, 'subject')")
    db.execute("INSERT INTO document_politicians (document_id, politician_id, role) VALUES (5, 3, 'subject')")

    db.commit()
    db.close()
    yield path
    _safe_unlink(path)


# ─── Bug C: get_pending_politicians filter semantics ──────────────────


class TestGetPendingPoliticiansFilters:
    def test_includes_active_with_unreviewed_subject_doc(self, fixtures_db):
        with patch("src.analyze.get_db", lambda: get_db(fixtures_db)):
            from src.analyze import get_pending_politicians
            pending = get_pending_politicians(days=1)
            names = {p["name"] for p in pending}
            assert "Aktīvais" in names, (
                "active politician with unreviewed subject doc must be pending"
            )

    def test_excludes_reviewed_docs(self, fixtures_db):
        """Politician with only reviewed subject docs must not appear."""
        with patch("src.analyze.get_db", lambda: get_db(fixtures_db)):
            from src.analyze import get_pending_politicians
            pending = get_pending_politicians(days=1)
            # Aktīvais has doc 1 (unreviewed) AND doc 2 (reviewed). Only
            # the unreviewed one should contribute to doc_count.
            row = next((p for p in pending if p["name"] == "Aktīvais"), None)
            assert row is not None
            assert row["doc_count"] == 1, (
                "reviewed docs must not be counted — expected 1, "
                f"got {row['doc_count']}"
            )

    def test_excludes_mentioned_role(self, fixtures_db):
        """A politician with only 'mentioned' role docs must not be pending."""
        with patch("src.analyze.get_db", lambda: get_db(fixtures_db)):
            from src.analyze import get_pending_politicians
            pending = get_pending_politicians(days=1)
            row = next((p for p in pending if p["name"] == "Aktīvais"), None)
            # doc 3 is role='mentioned' → not counted
            assert row["doc_count"] == 1

    def test_excludes_inactive_politicians(self, fixtures_db):
        """Sentinel entries (inactive) must be filtered out entirely."""
        with patch("src.analyze.get_db", lambda: get_db(fixtures_db)):
            from src.analyze import get_pending_politicians
            pending = get_pending_politicians(days=1)
            names = {p["name"] for p in pending}
            assert "Nepareizais" not in names, (
                "inactive sentinel politicians must never be pending"
            )

    def test_respects_window(self, fixtures_db):
        """Docs older than the window must not surface."""
        with patch("src.analyze.get_db", lambda: get_db(fixtures_db)):
            from src.analyze import get_pending_politicians
            pending = get_pending_politicians(days=1)
            names = {p["name"] for p in pending}
            # Otrais aktīvais only has doc 5 (30 days old) → not in 1-day window
            assert "Otrais aktīvais" not in names


# ─── Bug D: store_claim inactive politician guard ─────────────────────


class TestStoreClaimGuard:
    def test_rejects_unknown_politician(self, fixtures_db):
        """Calling store_claim with a non-existent opponent_id must raise."""
        with pytest.raises(ValueError, match="not found"):
            store_claim(
                opponent_id=99999,
                document_id=1,
                topic="Aizsardzība un drošība",
                stance="test",
                quote=None,
                confidence=0.8,
                reasoning="",
                salience=0.5,
                source_url="https://example.lv/1",
                stated_at=None,
                db_path=fixtures_db,
            )

    def test_rejects_inactive_politician(self, fixtures_db):
        """Sentinel/inactive politicians must never receive claims."""
        with pytest.raises(ValueError, match="inactive"):
            store_claim(
                opponent_id=2,  # Nepareizais, relationship_type='inactive'
                document_id=4,
                topic="Aizsardzība un drošība",
                stance="test",
                quote=None,
                confidence=0.8,
                reasoning="",
                salience=0.5,
                source_url="https://example.lv/2",
                stated_at=None,
                db_path=fixtures_db,
            )

    def test_error_message_names_sentinel(self, fixtures_db):
        """Error message should include the politician name for debuggability."""
        with pytest.raises(ValueError) as exc_info:
            store_claim(
                opponent_id=2,
                document_id=4,
                topic="Aizsardzība un drošība",
                stance="test",
                quote=None,
                confidence=0.8,
                reasoning="",
                salience=0.5,
                source_url="https://example.lv/3",
                stated_at=None,
                db_path=fixtures_db,
            )
        assert "Nepareizais" in str(exc_info.value)

    def test_guard_runs_before_embedding(self, fixtures_db):
        """The guard must raise before touching sqlite_vec / embeddings,
        so that an invalid pid produces a cheap, deterministic failure even
        when embedding dependencies aren't available."""
        # If the guard runs in the correct order, this call should raise
        # ValueError immediately — not ImportError, not sqlite_vec error.
        try:
            store_claim(
                opponent_id=99999,
                document_id=1,
                topic="x",
                stance="y",
                quote=None,
                confidence=0.5,
                reasoning="",
                salience=0.5,
                source_url="https://z.lv",
                stated_at=None,
                db_path=fixtures_db,
            )
            pytest.fail("store_claim should have raised ValueError")
        except ValueError:
            pass  # expected


# ─── Bug G: source_url canonicalization ───────────────────────────────


class TestStoreClaimUrlCanonicalization:
    def test_caller_url_overridden_by_doc_url(self, fixtures_db):
        """If caller passes a source_url that differs from the document's
        source_url, store_claim must override with the document's URL.

        Earlier extractor sessions hallucinated URLs (e.g., status ID
        ending in zeros, profile URL instead of status URL). The document
        is authoritative.
        """
        # Set a real URL on doc 1 (fresh, role=subject, unreviewed)
        db = get_db(fixtures_db)
        canonical_url = "https://example.lv/canonical-article"
        db.execute(
            "UPDATE documents SET source_url = ? WHERE id = 1",
            (canonical_url,),
        )
        db.commit()
        db.close()

        # Caller provides a wrong URL
        wrong_url = "https://example.lv/WRONG-hallucinated-url"
        try:
            cid = store_claim(
                opponent_id=1,
                document_id=1,
                topic="Aizsardzība un drošība",
                stance="test",
                quote=None,
                confidence=0.8,
                reasoning="",
                salience=0.5,
                source_url=wrong_url,
                stated_at=None,
                db_path=fixtures_db,
            )
        except (ImportError, Exception) as e:
            # If embeddings aren't available in the test environment, the
            # canonicalization still happens before the embed call. Read the
            # claim back to verify.
            if "vec0" in str(e) or "embed" in str(e).lower():
                pytest.skip(f"embeddings unavailable in test env: {e}")
            raise

        # Verify the stored claim has the canonical URL, not the wrong one
        db = get_db(fixtures_db)
        row = db.execute(
            "SELECT source_url FROM claims WHERE id = ?", (cid,)
        ).fetchone()
        db.close()
        assert row is not None
        assert row["source_url"] == canonical_url, (
            f"store_claim must override caller URL with doc URL. "
            f"Got: {row['source_url']}, expected: {canonical_url}"
        )
