"""VAD deny-list testi — homonīmu aizsardzība (pid=146 LPP/LC Bērziņa klase).

Fons: data/rollback_vad_homonimu_purge_2026-08-12.sql; backlog/vad.md § (2).
Divas kājas: stabila (kind, year) un uuid-only. Vad_uuid rotē per-session
(test_vad_declarations.py idempotence tests to jau dokumentē), tāpēc
uuid-only kāja ir best-effort, stabila kāja ir galvenā aizsardzība.
"""

import json
import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from src.vad.declarations import fetch_for_politician
from src.vad.denylist import DenyEntry, VadDenylist, deny_hit, load_denylist
from src.vad.fetch import SearchResultRow
from src.vad.schema import init_vad_tables

FIXTURE_HTML = (Path(__file__).parent / "fixtures" / "vad" / "slesers-2024.html").read_text(encoding="utf-8")


def _safe_unlink(path):
    try:
        os.unlink(path)
    except (PermissionError, FileNotFoundError):
        pass


def _make_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript("""
        CREATE TABLE tracked_politicians (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            role TEXT,
            keywords TEXT DEFAULT '[]',
            negative_patterns TEXT
        );
        INSERT INTO tracked_politicians(id, name, role) VALUES (146, 'Andris Bērziņš', 'Saeimas deputāts');
    """)
    db.commit()
    init_vad_tables(path)
    return db, path


def _row(uuid="homonims-uuid", year=2009):
    return SearchResultRow(
        vad_uuid=uuid,
        declaration_type=f"Kārtējā gada deklarācija - par {year}. gadu",
        is_legacy=False,
        institution="Latvijas Republikas Saeima",
        position_title="Saeimas deputāts",
    )


def _own_row():
    """Paša politiķa likumīga mūsdienu rinda (14. Saeima)."""
    return _row(uuid="own-2024-uuid", year=2024)


def _denylist():
    return VadDenylist(entries=(
        DenyEntry(pid=146, vad_uuid="30252e0c-stabila", match_kind="annual", match_year=2009, reason="LPP/LC 2009"),
        DenyEntry(pid=146, vad_uuid="5f4a657d-uuid-only", match_kind=None, match_year=None, reason="LPP/LC interim"),
        DenyEntry(pid=999, vad_uuid="cits-pid-uuid", match_kind="annual", match_year=2020, reason="cits pid"),
    ))


def _mock_client(rows):
    client = MagicMock()
    client.search.return_value = rows
    client.fetch_detail.return_value = FIXTURE_HTML
    return client


# ----- loader -----


def test_load_denylist_parses_entries_and_ignores_comment_keys(tmp_path):
    p = tmp_path / "vad_denylist.json"
    p.write_text(json.dumps({
        "_readme": ["komentārs"],
        "entries": [
            {"pid": 146, "vad_uuid": "u1", "match": {"kind": "annual", "year": 2009}, "reason": "r1"},
            {"pid": 146, "vad_uuid": "u2", "match": None, "reason": "r2"},
        ],
    }, ensure_ascii=False), encoding="utf-8")
    dl = load_denylist(p)
    assert len(dl.entries) == 2
    stable, uuid_only = dl.entries
    assert stable.match_kind == "annual" and stable.match_year == 2009
    assert uuid_only.match_kind is None


def test_load_denylist_missing_file_is_empty(tmp_path):
    assert not load_denylist(tmp_path / "nav-eksiste.json")


def test_load_denylist_year_none_in_match_is_preserved(tmp_path):
    p = tmp_path / "vad_denylist.json"
    p.write_text(json.dumps({
        "entries": [
            {"pid": 1, "vad_uuid": "u", "match": {"kind": "end"}, "reason": "gads nav"},
        ],
    }), encoding="utf-8")
    e = load_denylist(p).entries[0]
    assert e.match_kind == "end" and e.match_year is None


# ----- deny_hit predikāts -----


def test_stable_kind_year_leg_survives_uuid_rotation():
    """Galvenais scenārijs: VID rotēja uuid, bet (kind, year) joprojām trāpa."""
    hit = deny_hit(146, "JAUNS-ROTETS-UUID", "annual", 2009, _denylist())
    assert hit is not None and "kind-year" in hit


def test_uuid_only_leg_blocks_exact_uuid_only():
    assert deny_hit(146, "5f4a657d-uuid-only", "interim", None, _denylist()) is not None
    # Rotēts uuid uz to pašu deklarāciju — kāja NEtrāpa (dokumentēts robežgadījums)
    assert deny_hit(146, "rotets-nedrikst-iet-cauri", "interim", None, _denylist()) is None


def test_own_rows_pass_and_other_pid_unaffected():
    assert deny_hit(146, "jebkurš", "annual", 2024, _denylist()) is None
    assert deny_hit(3, "30252e0c-stabila", "annual", 2009, _denylist()) is None
    assert deny_hit(146, "jebkurš", "annual", 2010, _denylist()) is None  # 2010 nav sarakstā šajā fiksčurā


def test_empty_or_missing_denylist_never_hits():
    assert deny_hit(146, "x", "annual", 2009, None) is None
    assert deny_hit(146, "x", "annual", 2009, VadDenylist()) is None


# ----- integrācija caur fetch_for_politician -----


def test_fetch_denies_stable_key_row_before_any_write():
    """Bloķētā rinda nedrīkst ne insertēt, ne trāpīt disambig/dedup zaram."""
    db, path = _make_db()
    try:
        client = _mock_client([_row("rotets-uuid-2026", 2009)])
        result = fetch_for_politician(3 - 3 + 146, db, client, denylist=_denylist())
        assert result.rows_skipped_denylist == 1
        assert result.new_inserted == 0
        n = db.execute("SELECT COUNT(*) FROM vad_declarations WHERE opponent_id=146").fetchone()[0]
        assert n == 0
    finally:
        db.close()
        _safe_unlink(path)


def test_fetch_deny_precedes_natural_key_refresh():
    """Ja svešā rinda sakrīt ar esošu natural key, vad_uuid NEDRĪKST pārrakstīties."""
    db, path = _make_db()
    try:
        # Iesēj legālu annual/2009 rindu (piem. no vēsturiskā sweep)
        db.execute(
            "INSERT INTO vad_declarations(opponent_id, vad_uuid, declaration_type, "
            "declaration_kind, declaration_year, institution, position_title, source_url, raw_html) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (146, "esoshs-legaals-uuid", "Kārtējā gada deklarācija - par 2009. gadu",
             "annual", 2009, "Latvijas Republikas Saeima", "Saeimas deputāts", "https://x", "<html/>"),
        )
        db.commit()
        client = _mock_client([_row("rotets-uuid-2026", 2009)])
        result = fetch_for_politician(146, db, client, denylist=_denylist())
        assert result.rows_skipped_denylist == 1
        assert result.already_present == 0  # refresh nav noticis
        uuid_now = db.execute(
            "SELECT vad_uuid FROM vad_declarations WHERE opponent_id=146"
        ).fetchone()["vad_uuid"]
        assert uuid_now == "esoshs-legaals-uuid"
    finally:
        db.close()
        _safe_unlink(path)


def test_fetch_still_inserts_own_rows_with_denylist_active():
    db, path = _make_db()
    try:
        client = _mock_client([_own_row()])
        result = fetch_for_politician(146, db, client, denylist=_denylist())
        assert result.new_inserted == 1
        assert result.rows_skipped_denylist == 0
    finally:
        db.close()
        _safe_unlink(path)


def test_fetch_default_denylist_param_loads_repo_file():
    """Bez explicit denylist → ielādējas repo data/vad_denylist.json; pid=146
    annual/2009 homonīms tiek bloķēts ar īsto ierakstu no faila."""
    from src.vad.denylist import DEFAULT_DENYLIST_PATH
    assert DEFAULT_DENYLIST_PATH.exists(), "repo data/vad_denylist.json jāeksistē"
    dl = load_denylist(DEFAULT_DENYLIST_PATH)
    assert len(dl.by_pid(146)) == 7
    db, path = _make_db()
    try:
        client = _mock_client([_row("jebkurs-svešs-uuid", 2009)])
        result = fetch_for_politician(146, db, client)
        assert result.rows_skipped_denylist == 1
        assert result.new_inserted == 0
    finally:
        db.close()
        _safe_unlink(path)
