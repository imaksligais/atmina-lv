"""Tests for the src.graphics image/thread CLI (TDD).

Covers the canonical SEPIA_STYLE, the lightweight thread helpers, and CLI
arg routing. Image generation is injected (fake generate_fn) so tests never
hit the nanobanana API or incur cost.
"""

from pathlib import Path


def test_sepia_style_is_canonical_and_text_free():
    from src.graphics.prompt import SEPIA_STYLE

    assert SEPIA_STYLE.strip(), "SEPIA_STYLE must be non-empty"
    low = SEPIA_STYLE.lower()
    assert "sepia" in low
    assert "no text" in low, "tweet/thread sepia is always text-free"


def test_brief_style_variants_unchanged():
    """Brief poster style set: sepia added 2026-08-19 (operator decision)."""
    from src.graphics.prompt import STYLE_VARIANTS, SEPIA_STYLE

    assert set(STYLE_VARIANTS) == {"editorial", "scandi", "constructivist", "weekly", "sepia"}
    assert STYLE_VARIANTS["sepia"] is SEPIA_STYLE


def test_thread_filename_format():
    from src.graphics.thread import thread_filename

    assert thread_filename("2026-06-06", "1-lead") == "2026-06-06-thread-1-lead.png"


def test_compose_thread_prompt_appends_sepia():
    from src.graphics.prompt import SEPIA_STYLE
    from src.graphics.thread import compose_thread_prompt

    out = compose_thread_prompt("A cabinet table.")
    assert out.startswith("A cabinet table.")
    assert SEPIA_STYLE in out


def test_generate_thread_writes_files_without_api(tmp_path):
    from src.graphics.prompt import SEPIA_STYLE
    from src.graphics.thread import generate_thread

    calls = []

    def fake_gen(prompt, aspect_ratio="16:9"):
        calls.append((prompt, aspect_ratio))
        return b"FAKEPNG"

    prompts = {"1-lead": "A cabinet table.", "2-valdiba": "Sealed folders."}
    written = generate_thread("2026-06-06", prompts, str(tmp_path), generate_fn=fake_gen)

    names = sorted(Path(p).name for p in written)
    assert names == ["2026-06-06-thread-1-lead.png", "2026-06-06-thread-2-valdiba.png"]
    for p in written:
        assert Path(p).read_bytes() == b"FAKEPNG"
    assert len(calls) == 2
    assert all(SEPIA_STYLE in c[0] for c in calls), "every prompt must carry SEPIA_STYLE"
    assert all(c[1] == "16:9" for c in calls)


def test_cli_parser_routes_subcommands():
    from src.graphics.cli import build_parser

    p = build_parser()
    a = p.parse_args(["thread", "--date", "2026-06-06", "--prompts", "t.json"])
    assert a.cmd == "thread"
    b = p.parse_args(["brief", "--note-id", "259"])
    assert b.cmd == "brief"
    assert b.note_id == 259


# --- weekly-brief slug + style resolution (bugfix: CLI hardcoded -dienas-parskats
# and never auto-selected the weekly ink-navy style by note_type) ---

def test_brief_slug_weekly_uses_nedelas_parskats():
    from src.graphics.cli import _brief_slug

    assert _brief_slug("2026-06-08 10:00:00", "weekly_brief") == "2026-06-08-nedelas-parskats"


def test_brief_slug_daily_uses_dienas_parskats():
    from src.graphics.cli import _brief_slug

    assert _brief_slug("2026-06-08", "daily_brief") == "2026-06-08-dienas-parskats"


def test_resolve_style_weekly_defaults_to_weekly():
    from src.graphics.cli import _resolve_style

    assert _resolve_style(None, "weekly_brief") == "weekly"


def test_resolve_style_daily_defaults_to_house_default():
    from src.graphics.cli import _resolve_style
    from src.graphics.prompt import DEFAULT_STYLE

    assert _resolve_style(None, "daily_brief") == DEFAULT_STYLE


def test_resolve_style_explicit_overrides_note_type():
    from src.graphics.cli import _resolve_style

    # An explicit --style must win even for a weekly brief.
    assert _resolve_style("constructivist", "weekly_brief") == "constructivist"


def test_brief_style_arg_defaults_to_none_for_note_type_resolution():
    from src.graphics.cli import build_parser

    b = build_parser().parse_args(["brief", "--note-id", "1"])
    assert b.style is None, "--style must default to None so note_type can drive style"


def test_run_brief_weekly_wires_nedelas_slug_and_weekly_style(tmp_path, monkeypatch):
    """End-to-end wiring: a weekly_brief note → -nedelas-parskats filename + weekly style,
    with all heavy externals (DB/API/budget) faked so no cost is incurred."""
    import src.graphics.cli as cli

    vb = '{"topic": "Valsts pārvalde", "headline": "H", "stat": null, "metaphor_hint": "desk"}'
    # topic carries the SUBJECT week; created_at is two days later, which is
    # exactly the after-midnight case the slug must ignore.
    fake_row = {
        "visual_brief_json": vb,
        "created_at": "2026-06-10 01:14:00",
        "note_type": "weekly_brief",
        "topic": "nedēļas analīze 2026-06-08 līdz 2026-06-14",
    }

    class _Cursor:
        def fetchone(self):
            return fake_row

    class _FakeDB:
        def execute(self, *a, **k):
            return _Cursor()

    monkeypatch.setattr("src.db.get_db", lambda *a, **k: _FakeDB())
    monkeypatch.setattr("src.graphics.storage.get_approved_image", lambda db, nid: None)
    monkeypatch.setattr("src.graphics.config.budget_check", lambda db: None)
    monkeypatch.setattr("src.graphics.config.load_gemini_key", lambda: {"model": "fake-model"})
    # Īsti PNG baiti — _run_brief tagad lasa izmērus no faktiskā attēla,
    # tāpēc butaforijas baitu virkne vairs neder.
    from io import BytesIO

    from PIL import Image

    _buf = BytesIO()
    Image.new("RGB", (4, 3)).save(_buf, "PNG")
    _png = _buf.getvalue()
    monkeypatch.setattr(
        "src.graphics.nanobanana.generate_image",
        lambda prompt, aspect_ratio="16:9": _png,
    )

    captured: dict = {}

    def _fake_build_prompt(visual_brief, vm, style_key, **kw):
        captured["style_key"] = style_key
        captured["no_text"] = kw.get("no_text")
        return "PROMPT"

    def _fake_save_image_row(db, note_id, *, image_path, **kw):
        captured["image_path"] = image_path
        return 999

    monkeypatch.setattr("src.graphics.prompt.build_prompt", _fake_build_prompt)
    monkeypatch.setattr("src.graphics.storage.save_image_row", _fake_save_image_row)
    monkeypatch.chdir(tmp_path)

    args = cli.build_parser().parse_args(["brief", "--note-id", "261"])
    cli._run_brief(args)

    assert captured["style_key"] == "weekly"
    assert captured["no_text"] is False
    assert "nedelas-parskats" in captured["image_path"]
    assert "dienas-parskats" not in captured["image_path"]


def test_brief_no_text_flag_reaches_build_prompt():
    """--no-text is off by default and parses to True when given."""
    from src.graphics import cli

    assert cli.build_parser().parse_args(["brief", "--note-id", "1"]).no_text is False
    assert cli.build_parser().parse_args(["brief", "--note-id", "1", "--no-text"]).no_text is True


# --- poster date must be the brief's SUBJECT day, not the note's created_at ---
#
# A routine finishing after midnight creates the note on the NEXT calendar day,
# so the 07-15 poster was named `2026-07-16-...` — repeatedly (07-10/11,
# 07-15/16). 33 stored briefs have a topic date differing from created_at. The
# blog render already keys its URL off `topic`; the poster now agrees with it.
# See BACKLOG § Timestamp glabāšana nav standartizēta.


def test_brief_slug_prefers_subject_date_from_topic_over_created_at():
    from src.graphics.cli import _brief_slug

    slug = _brief_slug("2026-07-16 00:12:03", "daily_brief", "dienas analīze 2026-07-15")

    assert slug == "2026-07-15-dienas-parskats"


def test_brief_slug_weekly_uses_the_week_start_from_topic():
    from src.graphics.cli import _brief_slug

    slug = _brief_slug(
        "2026-07-20 02:21:01", "weekly_brief",
        "nedēļas analīze 2026-07-13 līdz 2026-07-19",
    )

    assert slug == "2026-07-13-nedelas-parskats"


def test_brief_slug_falls_back_to_created_at_without_a_topic_date():
    """Pre-2026-07-25 behaviour, kept for rows whose topic carries no date."""
    from src.graphics.cli import _brief_slug

    assert _brief_slug("2026-06-08 10:00:00", "daily_brief", None) == "2026-06-08-dienas-parskats"
    assert _brief_slug("2026-06-08 10:00:00", "daily_brief", "bez datuma") == "2026-06-08-dienas-parskats"
