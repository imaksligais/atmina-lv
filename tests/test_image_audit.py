"""Attēlu ģenerēšanas audita rinda — VIENS saucējs mēneša budžetam.

Verdikts 47b (2026-09-06, izpildīts 2026-09-07): līdz šim rindu rakstīja tikai
``cli brief --note-id`` (``brief_images``), tāpēc ``cli thread`` un tiešie
``generate_image()`` izsaukumi mēneša budžetā (griesti 5,00 USD) neparādījās
vispār — 2026-09-06 divi sintēzes attēli tā palika nereģistrēti. Tagad rindu
raksta pati ``generate_image()``, un ``monthly_cost_usd()`` lasa TIKAI
``image_audit``.

**Saucējs:** ``src/graphics/nanobanana.py::generate_image`` (veiksmes + abi kļūdu
zari), ``src/graphics/storage.py::save_audit_row`` + ``monthly_cost_usd``,
``src/db_migrations.py`` backfila solis, ``src/graphics/thread.py`` stilu vārti,
``src/graphics/cli.py`` ``thread --style``.

**Tīkls: nekad.** Gemini klients ir aizvietots visos testos.
**DB: pagaidu.** Katrs tests strādā ar savu bāzi zem ``tmp_path``.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.graphics import nanobanana

SCHEMA = (Path(__file__).resolve().parents[1] / "src" / "schema.sql").read_text(encoding="utf-8")


@pytest.fixture
def audit_db(tmp_path):
    """Bāze ar pilnu schema.sql (tātad arī ``image_audit``)."""
    path = tmp_path / "atmina.db"
    conn = sqlite3.connect(str(path))
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    return str(path)


def _image_response(data: bytes):
    resp = MagicMock()
    part = MagicMock()
    part.inline_data.data = data
    part.inline_data.mime_type = "image/png"
    resp.parts = [part]
    cand = MagicMock()
    cand.finish_reason = "STOP"
    cand.content.parts = [part]
    resp.candidates = [cand]
    return resp


def _safety_response():
    resp = MagicMock()
    resp.parts = []
    cand = MagicMock()
    cand.finish_reason = "SAFETY"
    cand.content.parts = []
    resp.candidates = [cand]
    return resp


def _rows(db_path: str) -> list[sqlite3.Row]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute("SELECT * FROM image_audit ORDER BY id").fetchall()
    finally:
        conn.close()


def _generate(db_path: str, prompt="p", **kw):
    client = MagicMock()
    client.models.generate_content.return_value = kw.pop("response", _image_response(b"png"))
    with patch("src.graphics.nanobanana._get_client", return_value=client), \
         patch("src.graphics.nanobanana.load_gemini_key",
               return_value={"api_key": "k", "model": "nano-test"}):
        return nanobanana.generate_image(prompt, db_path=db_path, **kw)


# --- 1. Veiksmīgs izsaukums -------------------------------------------------

def test_success_writes_exactly_one_audit_row(audit_db):
    assert _generate(audit_db, "cabinet table", kind="thread") == b"png"

    rows = _rows(audit_db)
    assert len(rows) == 1, "viens izsaukums = viena rinda"
    r = rows[0]
    assert r["kind"] == "thread"
    assert r["model"] == "nano-test"
    assert r["aspect"] == "16:9"
    assert r["prompt"] == "cabinet table"
    assert r["status"] == "ok"
    assert abs(r["cost_usd"] - 0.039) < 1e-9
    assert r["error_message"] is None


def test_default_kind_is_direct_so_oneoff_scripts_are_counted(audit_db):
    """Vienreizējs skripts par audita tabulu neko nezina — tāpēc noklusējums."""
    _generate(audit_db)
    assert _rows(audit_db)[0]["kind"] == "direct"


# --- 2. Kļūdu zari ----------------------------------------------------------

def test_safety_refusal_writes_a_zero_cost_error_row(audit_db):
    with pytest.raises(nanobanana.SafetyError):
        _generate(audit_db, response=_safety_response())

    rows = _rows(audit_db)
    assert len(rows) == 1
    assert rows[0]["status"] == "error"
    assert rows[0]["cost_usd"] == 0.0
    assert "SafetyError" in rows[0]["error_message"]


def test_terminal_api_error_writes_one_row_not_one_per_retry(audit_db):
    from google.genai.errors import APIError

    client = MagicMock()
    client.models.generate_content.side_effect = APIError(
        429, {"error": {"message": "rate limit"}}
    )
    with patch("src.graphics.nanobanana._get_client", return_value=client), \
         patch("src.graphics.nanobanana.load_gemini_key",
               return_value={"api_key": "k", "model": "nano-test"}), \
         patch("src.graphics.nanobanana.time.sleep"):
        with pytest.raises(APIError):
            nanobanana.generate_image("p", db_path=audit_db)

    rows = _rows(audit_db)
    assert len(rows) == 1, "atkārtojumi nav atsevišķi izsaukumi"
    assert rows[0]["status"] == "error"
    assert rows[0]["cost_usd"] == 0.0


# --- 3. Viens saucējs -------------------------------------------------------

def test_monthly_cost_counts_every_path_in_one_denominator(audit_db):
    for kind in ("brief", "thread", "synthesis", "direct"):
        _generate(audit_db, kind=kind)

    from src.graphics.storage import monthly_cost_usd

    conn = sqlite3.connect(audit_db)
    try:
        assert abs(monthly_cost_usd(conn) - 4 * 0.039) < 1e-9
    finally:
        conn.close()


def test_audit_write_failure_does_not_lose_the_image(audit_db, caplog):
    """Attēls ir produkts, audita rinda ir uzskaite — bet klusēt nedrīkst."""
    with patch("src.graphics.storage.save_audit_row", side_effect=RuntimeError("nope")):
        assert _generate(audit_db) == b"png"
    assert any("image_audit" in rec.message for rec in caplog.records), \
        "neizdevies audits jāpiesaka skaļi"


# --- 4. Migrācijas backfill -------------------------------------------------

def _apply_migrations(db_path: str) -> None:
    from src.db_migrations import apply_migrations

    conn = sqlite3.connect(db_path)
    try:
        apply_migrations(conn)
        conn.commit()
    finally:
        conn.close()


def test_backfill_moves_brief_images_history_and_is_idempotent(audit_db):
    conn = sqlite3.connect(audit_db)
    conn.execute(
        "INSERT INTO context_notes (id, note_type, content, created_at)"
        " VALUES (1, 'daily_brief', 'c', '2026-09-01 10:00:00')"
    )
    conn.executemany(
        "INSERT INTO brief_images (note_id, image_path, prompt, model, aspect,"
        " generated_at, cost_usd, approved) VALUES (1, ?, 'p', 'm', '16:9', ?, ?, 1)",
        [
            ("images/briefs/a.png", "2026-09-01 10:00:00", 0.039),
            ("images/synthesis/b.png", "2026-09-02 10:00:00", 0.039),
            ("", "2026-09-03 10:00:00", 0.0),
        ],
    )
    conn.commit()
    conn.close()

    _apply_migrations(audit_db)
    rows = _rows(audit_db)
    assert len(rows) == 3
    assert [r["kind"] for r in rows] == ["brief", "synthesis", "brief"]
    assert rows[2]["status"] == "error"
    assert all(r["source_table"] == "brief_images" for r in rows)

    _apply_migrations(audit_db)
    assert len(_rows(audit_db)) == 3, "atkārtots backfill nedrīkst dublēt"


# --- 5. `cli thread --style light|sepia` ------------------------------------

def test_thread_styles_expose_sepia_and_light():
    from src.graphics.prompt import LIGHT_STYLE, SEPIA_STYLE, THREAD_STYLES

    assert set(THREAD_STYLES) == {"sepia", "light"}
    assert THREAD_STYLES["sepia"] is SEPIA_STYLE
    assert THREAD_STYLES["light"] is LIGHT_STYLE
    low = LIGHT_STYLE.lower()
    assert "no text" in low, "pavediena attēli vienmēr ir bez teksta"
    assert "cream" in low and "no dark background" in low


def test_compose_thread_prompt_honours_the_style():
    from src.graphics.prompt import LIGHT_STYLE, SEPIA_STYLE
    from src.graphics.thread import compose_thread_prompt

    assert SEPIA_STYLE in compose_thread_prompt("A cabinet table.")
    light = compose_thread_prompt("A cabinet table.", "light")
    assert LIGHT_STYLE in light
    assert SEPIA_STYLE not in light


def test_generate_thread_light_style_reaches_every_prompt(tmp_path):
    from src.graphics.prompt import LIGHT_STYLE
    from src.graphics.thread import generate_thread

    seen: list[str] = []

    def fake_gen(prompt, aspect_ratio="16:9"):
        seen.append(prompt)
        return b"PNG"

    generate_thread(
        "2026-09-07", {"1": "a", "2": "b"}, str(tmp_path),
        generate_fn=fake_gen, style="light",
    )
    assert len(seen) == 2
    assert all(LIGHT_STYLE in p for p in seen)


def test_unknown_thread_style_stops_instead_of_falling_back(tmp_path):
    from src.graphics.thread import generate_thread

    with pytest.raises(KeyError):
        generate_thread("2026-09-07", {"1": "a"}, str(tmp_path), style="neon")


def test_cli_thread_style_parses_and_defaults_to_sepia():
    from src.graphics.cli import build_parser

    p = build_parser()
    assert p.parse_args(["thread", "--date", "d", "--prompts", "t.json"]).style == "sepia"
    assert p.parse_args(
        ["thread", "--date", "d", "--prompts", "t.json", "--style", "light"]
    ).style == "light"
