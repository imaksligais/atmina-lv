import sqlite3

from src.scope import queue_politician_sql, relay_media_pids


def test_journalist_relay_queue_preserves_web_and_junction_scope():
    with sqlite3.connect(":memory:") as db:
        db.executescript("""
            CREATE TABLE tracked_politicians (id, relationship_type);
            CREATE TABLE social_accounts (opponent_id, feed_type);
            CREATE TABLE documents (id, platform);
            CREATE TABLE document_politicians (politician_id, document_id);
            INSERT INTO tracked_politicians VALUES
                (1, 'journalist'), (2, 'journalist'), (3, 'organization');
            INSERT INTO social_accounts VALUES
                (1, 'relay'), (2, 'first_party'), (3, 'relay');
            INSERT INTO documents VALUES
                (1, 'twitter'), (2, 'x_mention'), (3, 'web'), (4, 'twitter');
            INSERT INTO document_politicians VALUES (1,1), (1,2), (1,3), (2,4);
        """)
        assert relay_media_pids(db) == frozenset({3})
        pairs = db.execute(f"""
            SELECT dp.politician_id, d.id FROM document_politicians dp
            JOIN documents d ON d.id = dp.document_id
            WHERE {queue_politician_sql()}
        """).fetchall()
        assert pairs == [(1, 3), (2, 4)]
        assert relay_media_pids(db) == frozenset({3})
