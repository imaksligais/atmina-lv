import os
import sqlite3
import tempfile

from src.vad.schema import init_vad_tables


def _safe_unlink(path):
    try:
        os.unlink(path)
    except PermissionError:
        pass


def _make_db_with_politicians() -> str:
    """Create a temp SQLite DB with tracked_politicians table, return path."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    with sqlite3.connect(path) as boot:
        boot.execute("""
            CREATE TABLE tracked_politicians (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            )
        """)
        boot.commit()
    return path


def test_init_creates_eleven_tables():
    path = _make_db_with_politicians()
    try:
        init_vad_tables(path)
        with sqlite3.connect(path) as con:
            tables = {r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'vad_%'"
            )}
    finally:
        _safe_unlink(path)

    expected = {
        "vad_declarations", "vad_positions", "vad_real_estate",
        "vad_companies", "vad_vehicles", "vad_savings",
        "vad_income", "vad_transactions", "vad_debts",
        "vad_loans_given", "vad_family",
    }
    assert tables == expected, f"missing or extra: {expected ^ tables}"


def test_init_is_idempotent():
    path = _make_db_with_politicians()
    try:
        init_vad_tables(path)
        init_vad_tables(path)  # second call must not raise
        # Verify second call left the table set identical (real idempotence)
        with sqlite3.connect(path) as con:
            tables = {r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'vad_%'"
            )}
        assert len(tables) == 11, f"second call drifted table set: {tables}"
    finally:
        _safe_unlink(path)


def test_unique_constraint_on_natural_key():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        with sqlite3.connect(path) as boot:
            boot.execute("CREATE TABLE tracked_politicians (id INTEGER PRIMARY KEY, name TEXT)")
            boot.execute("INSERT INTO tracked_politicians(id, name) VALUES (1, 'X')")
            boot.commit()
        init_vad_tables(path)
        with sqlite3.connect(path) as con:
            # 1. First insert succeeds
            con.execute(
                "INSERT INTO vad_declarations(opponent_id, vad_uuid, declaration_type, "
                "declaration_kind, declaration_year, submitted_at, position_title, source_url) "
                "VALUES (1, 'uuid-A', 'X', 'annual', 2024, '2025-03-27', 'Saeimas deputāts', 'https://example/')"
            )
            con.commit()

            # 2. Same natural key but different vad_uuid → must fail
            try:
                con.execute(
                    "INSERT INTO vad_declarations(opponent_id, vad_uuid, declaration_type, "
                    "declaration_kind, declaration_year, submitted_at, position_title, source_url) "
                    "VALUES (1, 'uuid-B', 'X', 'annual', 2024, '2025-03-27', 'Saeimas deputāts', 'https://example/')"
                )
                con.commit()
                assert False, "expected IntegrityError on duplicate natural key"
            except sqlite3.IntegrityError:
                pass

            # 3. Different position_title → succeeds
            con.execute(
                "INSERT INTO vad_declarations(opponent_id, vad_uuid, declaration_type, "
                "declaration_kind, declaration_year, submitted_at, position_title, source_url) "
                "VALUES (1, 'uuid-C', 'X', 'annual', 2024, '2025-03-27', 'Ministrs', 'https://example/')"
            )
            con.commit()

            # 4. NULL submitted_at — SQLite treats NULLs as distinct → succeeds
            con.execute(
                "INSERT INTO vad_declarations(opponent_id, vad_uuid, declaration_type, "
                "declaration_kind, declaration_year, submitted_at, position_title, source_url) "
                "VALUES (1, 'uuid-D', 'X', 'annual', 2024, NULL, 'Saeimas deputāts', 'https://example/')"
            )
            con.commit()

            # Verify total rows
            n = con.execute("SELECT COUNT(*) FROM vad_declarations").fetchone()[0]
            assert n == 3, f"expected 3 rows after deduplication, got {n}"
    finally:
        _safe_unlink(path)


def test_vad_uuid_is_nullable():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        with sqlite3.connect(path) as boot:
            boot.execute("CREATE TABLE tracked_politicians (id INTEGER PRIMARY KEY, name TEXT)")
            boot.execute("INSERT INTO tracked_politicians(id, name) VALUES (1, 'X')")
            boot.commit()
        init_vad_tables(path)
        with sqlite3.connect(path) as con:
            # Insert with NULL vad_uuid — must succeed (post-F11 fix)
            con.execute(
                "INSERT INTO vad_declarations(opponent_id, vad_uuid, declaration_type, "
                "declaration_kind, declaration_year, submitted_at, position_title, source_url) "
                "VALUES (1, NULL, 'X', 'annual', 2024, '2025-03-27', 'Saeimas deputāts', 'https://example/')"
            )
            con.commit()
    finally:
        _safe_unlink(path)
