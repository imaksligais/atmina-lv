import os
import sqlite3
import tempfile

from src.render.vad import (
    get_vad_data_for_politicians,
    vad_count_per_politician,
)
from src.vad.schema import init_vad_tables


def _safe_unlink(path):
    try:
        os.unlink(path)
    except (PermissionError, FileNotFoundError):
        pass


def _fresh_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("CREATE TABLE tracked_politicians(id INTEGER PRIMARY KEY, name TEXT)")
    db.execute("INSERT INTO tracked_politicians(id, name) VALUES (1, 'X'), (2, 'Y')")
    db.commit()
    init_vad_tables(path)
    return db, path


def _insert_declaration(db, opp_id, year, uuid, position="Saeimas deputāts", submitted="2025-03-27"):
    cur = db.execute(
        "INSERT INTO vad_declarations(opponent_id, vad_uuid, declaration_type, "
        "declaration_kind, declaration_year, position_title, submitted_at, source_url) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (opp_id, uuid, f"Kārtējā gada deklarācija - par {year}. gadu", "annual", year,
         position, submitted, "https://example/"),
    )
    db.commit()
    return cur.lastrowid


def test_returns_empty_when_no_data():
    db, path = _fresh_db()
    try:
        assert get_vad_data_for_politicians(db, [1]) == {}
    finally:
        db.close()
        _safe_unlink(path)


def test_returns_empty_when_table_missing():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        db = sqlite3.connect(path)
        db.row_factory = sqlite3.Row
        # No init_vad_tables — table doesn't exist
        assert get_vad_data_for_politicians(db, [1]) == {}
        db.close()
    finally:
        _safe_unlink(path)


def test_loads_declarations_with_year_desc():
    db, path = _fresh_db()
    try:
        # Use distinct submitted_at to satisfy natural-key UNIQUE
        _insert_declaration(db, 1, 2022, "u-2022", submitted="2023-03-27")
        _insert_declaration(db, 1, 2024, "u-2024", submitted="2025-03-27")
        _insert_declaration(db, 1, 2023, "u-2023", submitted="2024-03-27")
        data = get_vad_data_for_politicians(db, [1])
        assert 1 in data
        years = [v.year for v in data[1]]
        assert years == [2024, 2023, 2022]
    finally:
        db.close()
        _safe_unlink(path)


def test_sections_get_delta_markers():
    db, path = _fresh_db()
    try:
        d_2023 = _insert_declaration(db, 1, 2023, "u-2023", submitted="2024-03-27")
        d_2024 = _insert_declaration(db, 1, 2024, "u-2024", submitted="2025-03-27")
        db.execute(
            "INSERT INTO vad_income(declaration_id, source, is_individual, income_type, amount, currency) "
            "VALUES (?,?,?,?,?,?)",
            (d_2023, "Saeima", 0, "Alga", 50000.0, "EUR"),
        )
        db.execute(
            "INSERT INTO vad_income(declaration_id, source, is_individual, income_type, amount, currency) "
            "VALUES (?,?,?,?,?,?)",
            (d_2024, "Saeima", 0, "Alga", 76000.0, "EUR"),
        )
        db.commit()
        data = get_vad_data_for_politicians(db, [1])
        income_2024 = data[1][0].sections["income"]
        assert income_2024[0].delta == "modified"
        assert income_2024[0].diff_text is not None
        assert "76000" in income_2024[0].diff_text
    finally:
        db.close()
        _safe_unlink(path)


def test_vad_count_per_politician():
    db, path = _fresh_db()
    try:
        # Distinct submitted_at to satisfy natural-key UNIQUE
        _insert_declaration(db, 1, 2024, "u1", submitted="2025-03-27")
        _insert_declaration(db, 1, 2023, "u2", submitted="2024-03-27")
        _insert_declaration(db, 2, 2024, "u3", submitted="2025-03-27")
        counts = vad_count_per_politician(db)
        assert counts == {1: 2, 2: 1}
    finally:
        db.close()
        _safe_unlink(path)
