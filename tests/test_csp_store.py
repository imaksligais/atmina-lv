"""``src/csp/db.py`` shēma + ``src/csp/sync.py`` rakstīšanas ceļš.

**Saucējs (plāna 6.1):**
- ``src/csp/db.py`` — **1 no 1** publiskās funkcijas (``init_db``).
- ``src/csp/sync.py`` — **3 no 4** publiskajām funkcijām (``upsert_rows``,
  ``populate_metadata_and_topics``, ``sync_table``) + privātais
  ``_build_query_with_time``. **NEsegts: ``sync_all``** — tas ir tikai cilpa
  pār ``sync_table`` ar `except Exception` apkārt, un tā vienīgā papildu
  uzvedība (kļūda → ``results[table_id] = 0``) ir segta netieši caur
  ``sync_table`` kļūdas testu; to atsevišķi segt nozīmētu monkeypatchot 10
  galdus bez jauna apgalvojuma.

**Tīkls: nekad.** ``src.csp.sync.fetch_table`` ir monkeypatchots visos testos,
kas sauc ``sync_table``.

**DB: pagaidu.** Katrs tests taisa savu ``csp.db`` zem ``tmp_path``, kas
``tests/conftest.py`` dēļ krīt ``<repo>/.pytest-tmp``. ``data/atmina.db`` netiek
aiztikta; ``data/csp.db`` arī ne.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from src.csp import db as csp_db
from src.csp import sync as csp_sync
from src.csp.tables import FREQ_PERIODS_PER_YEAR, TABLES

FIXTURES = Path(__file__).resolve().parent / "fixtures"

EXPECTED_TABLES = {"csp_data", "csp_metadata", "events", "topic_links"}


@pytest.fixture
def conn(tmp_path):
    c = csp_db.init_db(str(tmp_path / "csp.db"))
    yield c
    c.close()


def _names(conn: sqlite3.Connection) -> set[str]:
    return {
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }


# --- db.py -----------------------------------------------------------------


def test_init_db_creates_exactly_the_four_expected_tables(conn):
    assert _names(conn) >= EXPECTED_TABLES
    # Saucējs: 4 galdi. Ja parādās piektais bez šī saraksta atjaunināšanas,
    # kāds pievienoja shēmu bez vārtiem.
    assert _names(conn) - {"sqlite_sequence"} == EXPECTED_TABLES


def test_init_db_sets_row_factory_and_pragmas(conn, tmp_path):
    assert conn.row_factory is sqlite3.Row
    assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_init_db_is_idempotent(tmp_path):
    """Otrreizējs izsaukums pār to pašu failu neizmet un nezaudē datus."""
    path = str(tmp_path / "csp.db")
    c1 = csp_db.init_db(path)
    c1.execute(
        "INSERT INTO csp_data (table_id, period, freq, value, updated_at) "
        "VALUES ('T', '2026M01', 'M', 1.0, 'x')"
    )
    c1.commit()
    c1.close()
    c2 = csp_db.init_db(path)
    assert c2.execute("SELECT COUNT(*) FROM csp_data").fetchone()[0] == 1
    c2.close()


def test_csp_data_primary_key_is_table_period_geo_breakdown(conn):
    """PK forma ir tas, kas padara ``INSERT OR REPLACE`` par upsert."""
    pk = [r["name"] for r in conn.execute("PRAGMA table_info(csp_data)") if r["pk"]]
    assert pk == ["table_id", "period", "geo", "breakdown"]


def test_csp_data_defaults_geo_lv_and_total_breakdown(conn):
    """Renderis vaicā ``WHERE geo='LV'`` — noklusējums to nes bez rakstītāja."""
    conn.execute(
        "INSERT INTO csp_data (table_id, period, freq, value, updated_at) "
        "VALUES ('T', '2026M01', 'M', 1.0, 'x')"
    )
    row = conn.execute("SELECT geo, breakdown FROM csp_data").fetchone()
    assert (row["geo"], row["breakdown"]) == ("LV", "_total_")


# --- sync.py: upsert_rows --------------------------------------------------


def _rows(**over):
    base = {"indicator": "EliminatedValue", "period": "2026M01",
            "value": 1.0, "breakdown": "_total_", "updated": "u"}
    base.update(over)
    return base


def test_upsert_rows_skips_none_values_and_reports_the_stored_count(conn):
    """``None`` vērtības tiek izmestas — un atgriežamais skaits to atspoguļo.

    CLAUDE.md § "Silent success is a defect class": glabāto skaitu drīkst
    salīdzināt ar iecerēto tikai tad, ja funkcija to godīgi atgriež.
    """
    rows = [
        _rows(period="2026M01", value=1.0),
        _rows(period="2026M02", value=None),
        _rows(period="2026M03", value=3.0),
    ]
    stored = csp_sync.upsert_rows(conn, "NVA011m", "M", rows)
    assert stored == 2
    assert conn.execute("SELECT COUNT(*) FROM csp_data").fetchone()[0] == 2


def test_upsert_rows_replaces_on_repeat_instead_of_duplicating(conn):
    csp_sync.upsert_rows(conn, "T", "M", [_rows(value=1.0)])
    csp_sync.upsert_rows(conn, "T", "M", [_rows(value=9.0)])
    got = conn.execute("SELECT period, value FROM csp_data").fetchall()
    assert len(got) == 1
    assert got[0]["value"] == 9.0


def test_upsert_rows_keeps_breakdowns_apart(conn):
    """``breakdown`` ir PK daļa, tāpēc GRS un NET NEpārraksta viens otru.

    Tas ir tas, kas 3D galdiem ļauj sabojāt renderi (sk.
    ``tests/test_csp_readpath.py`` — renderis nefiltrē pēc breakdown).
    """
    csp_sync.upsert_rows(conn, "DSV010m", "M", [
        _rows(breakdown="GRS", value=1710.0),
        _rows(breakdown="NET", value=1240.0),
    ])
    assert conn.execute("SELECT COUNT(*) FROM csp_data").fetchone()[0] == 2


def test_upsert_rows_stamps_utc_updated_at(conn):
    """``updated_at`` ir UTC ISO ar nobīdi — CSP kešs nav LV laika tabula."""
    csp_sync.upsert_rows(conn, "T", "M", [_rows()])
    stamp = conn.execute("SELECT updated_at FROM csp_data").fetchone()[0]
    assert stamp.endswith("+00:00")


# --- sync.py: metadata + topics -------------------------------------------


def test_populate_metadata_covers_every_configured_table(conn):
    csp_sync.populate_metadata_and_topics(conn)
    got = {r["table_id"] for r in conn.execute("SELECT table_id FROM csp_metadata")}
    assert got == set(TABLES)          # saucējs: visi 10 konfigurētie galdi
    assert len(got) == len(TABLES) == 10


def test_populate_topics_writes_one_row_per_table_topic_pair(conn):
    csp_sync.populate_metadata_and_topics(conn)
    expected = sum(len(cfg["topics"]) for cfg in TABLES.values())
    got = conn.execute("SELECT COUNT(*) FROM topic_links").fetchone()[0]
    assert got == expected > 0
    row = conn.execute(
        "SELECT keywords FROM topic_links WHERE table_id='NVA011m'"
    ).fetchone()
    assert "bezdarbs" in row["keywords"].split(",")


def test_populate_metadata_is_idempotent(conn):
    csp_sync.populate_metadata_and_topics(conn)
    first = conn.execute("SELECT COUNT(*) FROM csp_metadata").fetchone()[0]
    csp_sync.populate_metadata_and_topics(conn)
    assert conn.execute("SELECT COUNT(*) FROM csp_metadata").fetchone()[0] == first


# --- sync.py: _build_query_with_time + sync_table --------------------------


def test_build_query_with_time_converts_history_years_to_top_n():
    cfg = {"freq": "M", "history_years": 25, "query": [{"code": "ContentsCode"}]}
    out = csp_sync._build_query_with_time(cfg)
    assert out[:-1] == cfg["query"]          # oriģināls nav mutēts, tikai papildināts
    assert out[-1] == {
        "code": "TIME", "selection": {"filter": "top", "values": ["300"]},
    }
    assert cfg["query"] == [{"code": "ContentsCode"}]


@pytest.mark.parametrize("freq,years,expect", [("M", 2, "24"), ("Q", 3, "12"), ("A", 5, "5")])
def test_build_query_with_time_uses_freq_periods_per_year(freq, years, expect):
    cfg = {"freq": freq, "history_years": years, "query": []}
    assert csp_sync._build_query_with_time(cfg)[-1]["selection"]["values"] == [expect]
    assert FREQ_PERIODS_PER_YEAR[freq] * years == int(expect)


def test_sync_table_filters_rows_by_the_configured_value_indicator(conn, monkeypatch):
    """Tikai ``cfg['value_indicator']`` rindas nonāk DB.

    Šis ir vienīgais filtrs starp CSP atbildi un ``csp_data``; ja tas pazustu,
    galds savāktu visus indikatorus vienā ``table_id`` un renderis rādītu
    sajauktas sērijas.
    """
    payload = json.loads((FIXTURES / "csp_jsonstat2_2d.json").read_text(encoding="utf-8"))
    # Otrs indikators, ko konfigurācija NEprasa.
    payload["id"] = ["ContentsCode", "TIME"]
    payload["size"] = [2, 4]
    payload["dimension"]["ContentsCode"]["category"]["index"] = {
        "EliminatedValue": 0, "SomethingElse": 1,
    }
    payload["value"] = [6.4, 6.2, 6.0, None, 99.0, 99.0, 99.0, 99.0]

    monkeypatch.setattr(csp_sync, "fetch_table", lambda path, query: payload)
    csp_sync.populate_metadata_and_topics(conn)
    # PCI021m: nav ``archive`` atslēgas, tāpēc tikai viens fetch.
    stored = csp_sync.sync_table(conn, "PCI021m")

    assert stored == 3                       # 4 periodi mīnus viens None
    vals = [r["value"] for r in conn.execute(
        "SELECT value FROM csp_data WHERE table_id='PCI021m' ORDER BY period")]
    assert vals == [6.4, 6.2, 6.0]
    assert 99.0 not in vals


def test_sync_table_records_last_sync_and_csp_updated(conn, monkeypatch):
    payload = json.loads((FIXTURES / "csp_jsonstat2_2d.json").read_text(encoding="utf-8"))
    monkeypatch.setattr(csp_sync, "fetch_table", lambda path, query: payload)
    csp_sync.populate_metadata_and_topics(conn)
    csp_sync.sync_table(conn, "PCI021m")

    row = conn.execute(
        "SELECT last_sync, csp_updated FROM csp_metadata WHERE table_id='PCI021m'"
    ).fetchone()
    assert row["csp_updated"] == "2026-08-28T07:00:00Z"
    assert row["last_sync"] and row["last_sync"].endswith("+00:00")


def test_sync_table_archive_failure_does_not_lose_the_current_fetch(conn, monkeypatch):
    """NVA011m nes ``archive``; arhīva kļūme drīkst nomest tikai vēsturi.

    ``sync_table`` to noglabā ar ``except Exception`` + ``logger.warning``.
    Tas ir apzināts, BET klusais zars: skaitītājs atgriež tikai svaigo daļu,
    tāpēc "cik rindu tika nomestas" nekur neparādās. Šis tests to fiksē kā
    RAKSTURU, ne kā apstiprinājumu, ka tā ir pareizi.
    """
    payload = json.loads((FIXTURES / "csp_jsonstat2_2d.json").read_text(encoding="utf-8"))
    calls: list[str] = []

    def fake_fetch(path, query):
        calls.append(path)
        if path == TABLES["NVA011m"]["archive"]["path"]:
            raise RuntimeError("arhīvs nav pieejams")
        return payload

    monkeypatch.setattr(csp_sync, "fetch_table", fake_fetch)
    csp_sync.populate_metadata_and_topics(conn)
    stored = csp_sync.sync_table(conn, "NVA011m")

    assert calls == [TABLES["NVA011m"]["archive"]["path"], TABLES["NVA011m"]["path"]]
    assert stored == 3
    assert conn.execute(
        "SELECT COUNT(*) FROM csp_data WHERE table_id='NVA011m'"
    ).fetchone()[0] == 3
