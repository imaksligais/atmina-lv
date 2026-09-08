import json
from pathlib import Path

from src.video_ingest.state import compute_state, State


def make_workspace(tmp_path: Path, files: list[str]) -> Path:
    ws = tmp_path / "test-slug"
    ws.mkdir()
    for f in files:
        p = ws / f
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{}")
    return ws


def test_state_no_files(tmp_path):
    ws = tmp_path / "empty-slug"
    ws.mkdir()
    assert compute_state(ws) == State.FETCHING


def test_state_audio_only(tmp_path):
    ws = make_workspace(tmp_path, ["audio.wav"])
    assert compute_state(ws) == State.FETCHING


def test_state_transcribed(tmp_path):
    ws = make_workspace(tmp_path, ["audio.wav", "transcript.json"])
    assert compute_state(ws) == State.TRANSCRIBED


def test_state_diarized(tmp_path):
    ws = make_workspace(tmp_path, [
        "audio.wav", "transcript.json", "diarized.json",
        "samples/speaker-A.mp3", "suggested_speakers.json",
    ])
    assert compute_state(ws) == State.DIARIZED


def test_state_mapped(tmp_path):
    ws = make_workspace(tmp_path, [
        "audio.wav", "transcript.json", "diarized.json",
        "samples/speaker-A.mp3", "suggested_speakers.json",
        "speakers.json",
    ])
    assert compute_state(ws) == State.MAPPED


def test_state_archived_after_finalize(tmp_path):
    """audio.wav deleted by finalize; transcript+samples remain."""
    ws = make_workspace(tmp_path, [
        "transcript.json", "diarized.json",
        "samples/speaker-A.mp3", "suggested_speakers.json",
        "speakers.json", "labelled_transcript.md",
    ])
    # No DB lookup yet — state machine treats this as MAPPED+FINALIZED
    # but we can't tell IN_DB without DB; that's a separate check
    assert compute_state(ws) == State.FINALIZED
