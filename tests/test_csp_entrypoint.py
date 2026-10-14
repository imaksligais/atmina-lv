"""``python -m src.csp`` — ieejas punkts CSP datu atsvaidzināšanai.

Verdikts 49b (operatora lēmums 2026-08-15, izpildīts 2026-09-07): ``sync_all()``
eksistēja, bet izsaucēja nebija, tāpēc ``data/csp.db`` atsvaidzināšana nebija
IZPILDĀMA. Šie testi fiksē to, kas tam ieejas punktam jāgarantē.

**Saucējs:** ``src/csp/__main__.py`` — visas 3 publiskās funkcijas
(``_table_counts``, ``build_parser``, ``main``).

**Tīkls: nekad.** ``src.csp.__main__.sync_all`` ir monkeypatchots katrā testā.

**DB: pagaidu.** Neviens tests neaiztiek īsto ``data/csp.db``; sausā palaidiena
tests to pierāda, salīdzinot faila baitus pirms un pēc.
"""

from __future__ import annotations

import sqlite3

import pytest

from src.csp import __main__ as csp_main
from src.csp.db import init_db


@pytest.fixture
def csp_db(tmp_path):
    """Tukša CSP bāze ar vienu csp_data rindu, lai skaitītājs nav 0/0."""
    path = tmp_path / "csp.db"
    conn = init_db(str(path))
    conn.execute(
        "INSERT INTO csp_data (table_id, period, freq, geo, breakdown, value,"
        " updated_at) VALUES ('NVA011m', '2026M01', 'M', 'LV', '_total_', 1.0,"
        " '2026-01-01T00:00:00')"
    )
    conn.commit()
    conn.close()
    return path


def _fake_sync(rows_per_table: int = 3):
    """Sync aizvietotājs: ieraksta N rindas un atgriež sync_all formas dict."""
    def _inner(conn: sqlite3.Connection) -> dict[str, int]:
        for i in range(rows_per_table):
            conn.execute(
                "INSERT OR REPLACE INTO csp_data (table_id, period, freq, geo,"
                " breakdown, value, updated_at) VALUES"
                " ('PCI021m', ?, 'M', 'LV', '_total_', 2.0, '2026-09-07')",
                (f"2026M{i + 2:02d}",),
            )
        conn.commit()
        return {"PCI021m": rows_per_table}
    return _inner


def test_default_is_dry_run_and_leaves_the_db_byte_identical(csp_db, monkeypatch, capsys):
    monkeypatch.setattr(csp_main, "sync_all", _fake_sync())
    before = csp_db.read_bytes()

    rc = csp_main.main(["--db", str(csp_db)])

    assert rc == 0
    assert csp_db.read_bytes() == before, "sausais palaidiens aiztika izsekoto bināro failu"
    out = capsys.readouterr().out
    assert "dry-run" in out
    assert "NETIKA mainīta" in out


def test_apply_writes_to_the_real_db(csp_db, monkeypatch):
    monkeypatch.setattr(csp_main, "sync_all", _fake_sync())
    conn = sqlite3.connect(csp_db)
    before = conn.execute("SELECT COUNT(*) FROM csp_data").fetchone()[0]
    conn.close()

    rc = csp_main.main(["--db", str(csp_db), "--apply"])

    assert rc == 0
    conn = sqlite3.connect(csp_db)
    after = conn.execute("SELECT COUNT(*) FROM csp_data").fetchone()[0]
    conn.close()
    assert after == before + 3


def test_dry_run_reports_the_delta_it_would_apply(csp_db, monkeypatch, capsys):
    """Sausais palaidiens strādā ar KOPIJU, tāpēc delta ir īsta, ne 0."""
    monkeypatch.setattr(csp_main, "sync_all", _fake_sync())

    csp_main.main(["--db", str(csp_db)])

    out = capsys.readouterr().out
    assert "csp_data" in out
    assert "(+3)" in out


def test_apply_and_dry_run_together_are_refused(csp_db, monkeypatch):
    monkeypatch.setattr(csp_main, "sync_all", _fake_sync())
    assert csp_main.main(["--db", str(csp_db), "--apply", "--dry-run"]) == 2


def test_zero_refreshed_tables_exit_nonzero(csp_db, monkeypatch):
    """Nulle atsvaidzinātu tabulu nedrīkst izskatīties pēc veiksmes."""
    monkeypatch.setattr(csp_main, "sync_all", lambda conn: {"PCI021m": 0})
    assert csp_main.main(["--db", str(csp_db)]) == 1


def test_table_counts_names_every_counted_table(csp_db):
    conn = sqlite3.connect(str(csp_db))
    counts = csp_main._table_counts(conn)
    conn.close()
    assert set(counts) == {"csp_data", "csp_metadata", "topic_links"}
    assert counts["csp_data"] == 1
