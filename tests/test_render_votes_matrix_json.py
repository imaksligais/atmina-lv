"""Tests for the compact balsojumi matrix JSON emitter (Step 1).

Spec: docs/superpowers/plans/2026-05-28-balsojumi-virtualization.md § Datu formāts.

The emitter takes _build_matrix_data() output and produces a compact JSON shape
designed for client-side virtualization. These tests cover:
- Vote-type → single-char encoding (P/N/A/X/.)
- Compact transform shape (renamed keys, vote string per politician)
- File write at output/atmina/data/balsojumi-matrica.json with valid JSON
- Dissenting-vote index resolution via date+motif lookup

No DB access; the transform is a pure function over already-built matrix_data.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.render.votes import (
    _build_matrix_compact,
    _emit_matrix_json,
    _encode_vote_char,
    _find_vote_index_by_date_motif,
)


# ── _encode_vote_char ──────────────────────────────────────────────────


def test_encode_par():
    assert _encode_vote_char("Par") == "P"


def test_encode_pret():
    assert _encode_vote_char("Pret") == "N"


def test_encode_atturas():
    assert _encode_vote_char("Atturas") == "A"


def test_encode_nebalsoja():
    assert _encode_vote_char("Nebalsoja") == "X"


def test_encode_none_is_dot():
    assert _encode_vote_char(None) == "."


def test_encode_unknown_collapses_to_x():
    """Any non-standard vote-type collapses to 'X' (matches _build_matrix_data's
    nebalso bucket for `vtype is not None and not in standard set`."""
    assert _encode_vote_char("Weird") == "X"
    assert _encode_vote_char("") == "X"


# ── _build_matrix_compact ──────────────────────────────────────────────


@pytest.fixture
def sample_matrix_data():
    """Minimal matrix_data dict that mirrors _build_matrix_data's output."""
    return {
        "votes": [
            {
                "id": 100,
                "motif": "Par MK noteikumiem A",
                "summary": "Skaidrojums",
                "date": "2026-05-01",
                "time": "10:00",
                "result": "Pieņemts",
                "topic": "Drošība",
                "total_par": 50,
                "total_pret": 10,
                "total_atturas": 5,
                "url": "https://saeima.lv/v/100",
                "document_url": "https://saeima.lv/d/100",
                "document_nr": "Lp-1",
                "bill_slug": "1-lp14",
                "bill_doc_nr": "1/Lp14",
                "faction_breakdown": [
                    {"faction": "JV", "par": 25, "pret": 0, "atturas": 2, "nebalso": 3},
                    {"faction": "NA", "par": 10, "pret": 0, "atturas": 1, "nebalso": 1},
                ],
                "is_unanimous": False,
            },
            {
                "id": 101,
                "motif": "Par grozījumiem B",
                "summary": "",
                "date": "2026-05-02",
                "time": "11:15",
                "result": "Noraidīts",
                "topic": "",
                "total_par": 20,
                "total_pret": 60,
                "total_atturas": 0,
                "url": "",
                "document_url": "",
                "document_nr": "",
                "faction_breakdown": [
                    {"faction": "JV", "par": 15, "pret": 12, "atturas": 0, "nebalso": 3},
                ],
                "is_unanimous": False,
            },
        ],
        "factions": [
            {
                "name": "JV",
                "short": "JV",
                "color": "#3b82f6",
                "coalition_status": "coalition",
                "members": [
                    {"id": 2, "name": "Evika Siliņa", "slug": "evika-silina",
                     "votes": ["Par", "Pret"]},
                    {"id": 15, "name": "Baiba Braže", "slug": "baiba-braze",
                     "votes": ["Atturas", None]},
                ],
            },
        ],
        "politicians": {
            2: {
                "name": "Evika Siliņa",
                "faction": "JV",
                "slug": "evika-silina",
                "par": 1,
                "pret": 1,
                "atturas": 0,
                "nebalso": 0,
                "attendance_pct": 100,
                "dissenting_votes": [
                    {
                        "motif": "Par grozījumiem B",
                        "date": "2026-05-02",
                        "vote": "Pret",
                        "faction_majority": "Par",
                    }
                ],
            },
            15: {
                "name": "Baiba Braže",
                "faction": "JV",
                "slug": "baiba-braze",
                "par": 0,
                "pret": 0,
                "atturas": 1,
                "nebalso": 0,
                "attendance_pct": 50,
                "dissenting_votes": [],
            },
        },
    }


def test_compact_top_level_keys(sample_matrix_data):
    compact = _build_matrix_compact(sample_matrix_data)
    assert set(compact.keys()) == {"meta", "votes", "factions", "politicians"}


def test_compact_meta_version_and_total(sample_matrix_data):
    compact = _build_matrix_compact(sample_matrix_data)
    assert compact["meta"]["version"] == 1
    assert compact["meta"]["votes_total"] == 2
    assert "encoding" in compact["meta"]
    assert "P=Par" in compact["meta"]["encoding"]
    assert "generated_at" in compact["meta"]


def test_compact_meta_all_dates_derived(sample_matrix_data):
    """Without an explicit all_dates, meta.all_dates derives from the shard's
    own vote dates (newest-first)."""
    compact = _build_matrix_compact(sample_matrix_data)
    assert compact["meta"]["all_dates"] == ["2026-05-02", "2026-05-01"]


def test_compact_meta_all_dates_passthrough(sample_matrix_data):
    """An explicit all_dates (the FULL session list) is carried verbatim so the
    recent shard can advertise sessions beyond its own window."""
    full = ["2026-05-02", "2026-05-01", "2025-01-10", "2022-11-01"]
    compact = _build_matrix_compact(sample_matrix_data, all_dates=full)
    assert compact["meta"]["all_dates"] == full


def test_compact_votes_renamed_keys(sample_matrix_data):
    compact = _build_matrix_compact(sample_matrix_data)
    v0 = compact["votes"][0]
    assert v0["i"] == 0
    assert v0["vid"] == 100
    assert v0["d"] == "2026-05-01"
    assert v0["t"] == "10:00"
    assert v0["m"] == "Par MK noteikumiem A"
    assert v0["r"] == "Pieņemts"
    assert v0["tp"] == "Drošība"
    assert v0["tot"] == [50, 10, 5]
    assert v0["uni"] is False
    # faction_breakdown shortened
    assert v0["f"][0] == {"f": "JV", "p": 25, "n": 0, "a": 2, "x": 3}
    # Optional fields present when non-empty
    assert v0["s"] == "Skaidrojums"
    assert v0["url"] == "https://saeima.lv/v/100"
    assert v0["doc_url"] == "https://saeima.lv/d/100"
    assert v0["doc_nr"] == "Lp-1"
    # Bill link target for TAB-1 archive cards
    assert v0["bsl"] == "1-lp14"
    assert v0["bnr"] == "1/Lp14"


def test_compact_votes_drop_empty_optional_fields(sample_matrix_data):
    """Optional url/doc_url/doc_nr/summary fields must be absent when source is empty."""
    compact = _build_matrix_compact(sample_matrix_data)
    v1 = compact["votes"][1]
    assert "s" not in v1
    assert "url" not in v1
    assert "doc_url" not in v1
    assert "doc_nr" not in v1
    assert "bsl" not in v1
    assert "bnr" not in v1


def test_compact_factions_carry_only_member_ids(sample_matrix_data):
    compact = _build_matrix_compact(sample_matrix_data)
    f = compact["factions"][0]
    assert f["f"] == "JV"
    assert f["c"] == "#3b82f6"
    assert f["cs"] == "coalition"
    assert f["m"] == [2, 15]


def test_compact_politicians_vote_string(sample_matrix_data):
    """Each politician's vote list collapses to a single string aligned with votes[i]."""
    compact = _build_matrix_compact(sample_matrix_data)
    silina = compact["politicians"]["2"]
    assert silina["n"] == "Evika Siliņa"
    assert silina["f"] == "JV"
    assert silina["s"] == "evika-silina"
    assert silina["v"] == "PN"  # ["Par", "Pret"] → "PN"
    assert silina["sum"] == [1, 1, 0, 0]
    assert silina["att"] == 100

    braze = compact["politicians"]["15"]
    assert braze["v"] == "A."  # ["Atturas", None] → "A."


def test_compact_politicians_keys_are_strings(sample_matrix_data):
    """JSON object keys must be strings (JSON spec), even if matrix_data uses int pids."""
    compact = _build_matrix_compact(sample_matrix_data)
    for key in compact["politicians"]:
        assert isinstance(key, str)


def test_compact_dissenting_votes_indexed_by_position(sample_matrix_data):
    compact = _build_matrix_compact(sample_matrix_data)
    silina = compact["politicians"]["2"]
    assert len(silina["dis"]) == 1
    dv = silina["dis"][0]
    assert dv["i"] == 1  # second vote (index 1) — "Par grozījumiem B" on 2026-05-02
    assert dv["v"] == "N"
    assert dv["fm"] == "P"


def test_compact_vote_string_padded_when_member_list_shorter():
    """Defensive: if a politician's vote list is shorter than votes[], pad with '.'."""
    md = {
        "votes": [
            {"id": 1, "date": "2026-05-01", "motif": "A", "result": "Pieņemts",
             "topic": "", "total_par": 1, "total_pret": 0, "total_atturas": 0,
             "faction_breakdown": [], "is_unanimous": True, "time": ""},
            {"id": 2, "date": "2026-05-02", "motif": "B", "result": "Pieņemts",
             "topic": "", "total_par": 1, "total_pret": 0, "total_atturas": 0,
             "faction_breakdown": [], "is_unanimous": True, "time": ""},
            {"id": 3, "date": "2026-05-03", "motif": "C", "result": "Pieņemts",
             "topic": "", "total_par": 1, "total_pret": 0, "total_atturas": 0,
             "faction_breakdown": [], "is_unanimous": True, "time": ""},
        ],
        "factions": [
            {"name": "JV", "short": "JV", "color": "#000",
             "members": [{"id": 99, "name": "X", "slug": "x", "votes": ["Par"]}]},
        ],
        "politicians": {
            99: {"name": "X", "faction": "JV", "slug": "x", "par": 1, "pret": 0,
                 "atturas": 0, "nebalso": 0, "attendance_pct": 33, "dissenting_votes": []},
        },
    }
    compact = _build_matrix_compact(md)
    assert compact["politicians"]["99"]["v"] == "P.."  # padded to votes_total=3


def test_compact_handles_missing_dissenting_votes():
    """A politician with no dissenting_votes key still produces dis=[]."""
    md = {
        "votes": [
            {"id": 1, "date": "2026-05-01", "motif": "A", "result": "P", "topic": "",
             "total_par": 1, "total_pret": 0, "total_atturas": 0, "faction_breakdown": [],
             "is_unanimous": True, "time": ""},
        ],
        "factions": [{"name": "JV", "short": "JV", "color": "#000",
                      "members": [{"id": 1, "name": "X", "slug": "x", "votes": ["Par"]}]}],
        "politicians": {
            1: {"name": "X", "faction": "JV", "slug": "x", "par": 1, "pret": 0,
                "atturas": 0, "nebalso": 0, "attendance_pct": 100}  # no dissenting_votes key
        },
    }
    compact = _build_matrix_compact(md)
    assert compact["politicians"]["1"]["dis"] == []


# ── _find_vote_index_by_date_motif ────────────────────────────────────


def test_find_vote_index_exact_match():
    votes = [
        {"i": 0, "d": "2026-05-01", "m": "Full motif text"},
        {"i": 1, "d": "2026-05-02", "m": "Another motif"},
    ]
    assert _find_vote_index_by_date_motif(votes, "2026-05-02", "Another motif") == 1


def test_find_vote_index_prefix_match():
    """_build_matrix_data truncates motif to 80 chars in dissenting entries — we
    must match by prefix on the full motif in votes[]."""
    long_motif = "Par grozījumiem MK noteikumos par sociālā atbalsta piešķiršanu Ukrainas"
    truncated = long_motif[:80]
    votes = [{"i": 0, "d": "2026-05-01", "m": long_motif + " bēgļiem (papildus)"}]
    assert _find_vote_index_by_date_motif(votes, "2026-05-01", truncated) == 0


def test_find_vote_index_missing_returns_minus_one():
    votes = [{"i": 0, "d": "2026-05-01", "m": "A"}]
    assert _find_vote_index_by_date_motif(votes, "2026-99-99", "Z") == -1
    assert _find_vote_index_by_date_motif(votes, None, "A") == -1


# ── _emit_matrix_json (file write) ─────────────────────────────────────


def test_emit_matrix_json_creates_file(tmp_path: Path, sample_matrix_data):
    dest = _emit_matrix_json(sample_matrix_data, tmp_path)
    assert dest == tmp_path / "data" / "balsojumi-matrica.json"
    assert dest.exists()
    payload = json.loads(dest.read_text(encoding="utf-8"))
    assert payload["meta"]["version"] == 1
    assert payload["meta"]["votes_total"] == 2
    assert set(payload["politicians"].keys()) == {"2", "15"}


def test_emit_matrix_json_idempotent(tmp_path: Path, sample_matrix_data):
    """Running twice overwrites cleanly (idempotent for repeated builds)."""
    _emit_matrix_json(sample_matrix_data, tmp_path)
    first_size = (tmp_path / "data" / "balsojumi-matrica.json").stat().st_size
    _emit_matrix_json(sample_matrix_data, tmp_path)
    second_size = (tmp_path / "data" / "balsojumi-matrica.json").stat().st_size
    # generated_at timestamp may shift by 1 sec → size can differ by ±2 chars;
    # the artifact stays in the same order of magnitude.
    assert abs(first_size - second_size) <= 4


def test_emit_matrix_json_creates_data_subdir(tmp_path: Path, sample_matrix_data):
    """The data/ subdir is created automatically if missing."""
    assert not (tmp_path / "data").exists()
    _emit_matrix_json(sample_matrix_data, tmp_path)
    assert (tmp_path / "data").is_dir()


def test_emit_matrix_json_compact_separators(tmp_path: Path, sample_matrix_data):
    """File uses compact JSON separators (no whitespace) to minimize size."""
    dest = _emit_matrix_json(sample_matrix_data, tmp_path)
    raw = dest.read_text(encoding="utf-8")
    # No ", " or ": " — those are the default separators that pad JSON.
    assert ", " not in raw
    assert ": " not in raw


def test_emit_matrix_json_custom_basename(tmp_path: Path, sample_matrix_data):
    """A custom basename writes <basename>.json (+ .br/.gz) — used for the recent shard."""
    dest = _emit_matrix_json(sample_matrix_data, tmp_path, basename="balsojumi-matrica-recent")
    assert dest == tmp_path / "data" / "balsojumi-matrica-recent.json"
    assert dest.exists()
    assert (tmp_path / "data" / "balsojumi-matrica-recent.json.br").exists()
    assert (tmp_path / "data" / "balsojumi-matrica-recent.json.gz").exists()


def test_filter_recent_votes_keeps_only_recent():
    """_filter_recent_votes keeps votes on/after cutoff; old + null dates drop."""
    from src.render.votes import _filter_recent_votes
    votes = [
        {"id": 1, "vote_date": "2020-01-01"},
        {"id": 2, "vote_date": "2099-01-01"},
        {"id": 3, "vote_date": None},
    ]
    kept = _filter_recent_votes(votes, "2026-01-01")
    assert [v["id"] for v in kept] == [2]


def test_render_votes_emits_recent_shard(tmp_path: Path, monkeypatch):
    """render_votes writes both the full archive and the recent shard; the recent
    shard contains only votes within the window (mocked builder keeps it pure)."""
    import json as _json

    import src.render.votes as V

    monkeypatch.setattr(V, "_build_matrix_data", lambda db, votes: {
        "votes": [{"id": v["id"], "date": v["vote_date"], "motif": "m",
                   "result": "Pieņemts", "topic": "", "total_par": 1, "total_pret": 0,
                   "total_atturas": 0, "faction_breakdown": [], "is_unanimous": True,
                   "time": ""} for v in votes],
        "factions": [], "politicians": {},
    })
    monkeypatch.setattr(V, "_render_page", lambda *a, **k: None)
    votes = [
        {"id": 1, "vote_date": "2099-06-01", "topic": "", "result": "Pieņemts"},
        {"id": 2, "vote_date": "2000-01-01", "topic": "", "result": "Pieņemts"},
    ]
    # render_votes now runs a DISTINCT-deputies query against the DB (the
    # Option-2 SSR-card removal moved deputy names off the in-memory votes list),
    # so a real (empty) connection is required — deputies resolves to [].
    from src.db import get_db, init_db
    from src.saeima.schema import init_saeima_tables
    db_path = str(tmp_path / "t.db")
    init_db(db_path)
    init_saeima_tables(db_path)
    db = get_db(db_path)
    V.render_votes(env=None, db=db, atmina_dir=tmp_path, votes=votes, bills=[],
                   laws_index_count=0)
    db.close()
    full = _json.loads((tmp_path / "data" / "balsojumi-matrica.json").read_text("utf-8"))
    recent = _json.loads((tmp_path / "data" / "balsojumi-matrica-recent.json").read_text("utf-8"))
    assert full["meta"]["votes_total"] == 2
    assert recent["meta"]["votes_total"] == 1


def test_emit_matrix_json_writes_br_and_gz_siblings(tmp_path: Path, sample_matrix_data):
    """LiteSpeed shared host does not auto-compress application/json — the
    .htaccess rewrite rule serves pre-compressed .br/.gz siblings when the
    client supports them. See assets/htaccess.template."""
    import gzip
    import brotli
    _emit_matrix_json(sample_matrix_data, tmp_path)
    base = tmp_path / "data" / "balsojumi-matrica.json"
    br = tmp_path / "data" / "balsojumi-matrica.json.br"
    gz = tmp_path / "data" / "balsojumi-matrica.json.gz"
    assert base.exists()
    assert br.exists()
    assert gz.exists()
    # Both compressed variants must round-trip back to the raw bytes.
    raw = base.read_bytes()
    assert brotli.decompress(br.read_bytes()) == raw
    assert gzip.decompress(gz.read_bytes()) == raw
    # Compression should actually shrink the payload (sample is small but
    # repetitive enough that both encoders win).
    assert br.stat().st_size < base.stat().st_size
    assert gz.stat().st_size < base.stat().st_size
