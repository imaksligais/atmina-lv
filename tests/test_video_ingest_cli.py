import json
from unittest.mock import patch, MagicMock

import pytest

from src.video_ingest.cli import main


def test_cli_status_unknown_slug(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("src.video_ingest.cli.VIDEO_ROOT", tmp_path)
    rc = main(["status", "no-such-slug"])
    out = capsys.readouterr().out
    assert "no-such-slug" in out or rc != 0


def test_cli_status_diarized(tmp_path, monkeypatch, capsys):
    ws = tmp_path / "test-slug"
    ws.mkdir()
    (ws / "audio.wav").write_bytes(b"")
    (ws / "transcript.json").write_text("{}")
    (ws / "diarized.json").write_text("[]")
    (ws / "samples").mkdir()
    (ws / "samples" / "speaker-A.mp3").write_bytes(b"")
    (ws / "suggested_speakers.json").write_text("{}")
    monkeypatch.setattr("src.video_ingest.cli.VIDEO_ROOT", tmp_path)

    rc = main(["status", "test-slug"])
    out = capsys.readouterr().out
    assert "DIARIZED" in out
    assert rc == 0


def test_cli_fetch_dispatches(tmp_path, monkeypatch):
    called = {}
    def fake_run_fetch(input_arg, slug, num_speakers, language):
        called["args"] = (input_arg, slug, num_speakers, language)
        return 0

    monkeypatch.setattr("src.video_ingest.cli._run_fetch", fake_run_fetch)
    rc = main(["fetch", "https://www.youtube.com/watch?v=test", "--slug", "my-slug"])
    assert rc == 0
    assert called["args"][0] == "https://www.youtube.com/watch?v=test"
    assert called["args"][1] == "my-slug"


def test_cli_finalize_dispatches(monkeypatch):
    called = {}
    def fake_run_finalize(slug):
        called["slug"] = slug
        return 0
    monkeypatch.setattr("src.video_ingest.cli._run_finalize", fake_run_finalize)
    rc = main(["finalize", "my-slug"])
    assert rc == 0
    assert called["slug"] == "my-slug"
