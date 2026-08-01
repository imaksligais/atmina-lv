"""State machine reading filesystem markers in workspace directory.

DB-aware states (IN_DB, CLAIMS_EXTRACTED) are computed by callers that
combine compute_state(ws) with DB row lookups; this module is filesystem-only.
"""
from __future__ import annotations

from enum import Enum
from pathlib import Path


class State(str, Enum):
    FETCHING = "FETCHING"          # nothing or partial audio.wav
    TRANSCRIBED = "TRANSCRIBED"    # transcript.json exists
    DIARIZED = "DIARIZED"          # diarized.json + samples + suggested_speakers.json
    MAPPED = "MAPPED"              # operator's speakers.json present
    FINALIZED = "FINALIZED"        # labelled_transcript.md present, audio.wav deleted
    UNKNOWN = "UNKNOWN"


def compute_state(workspace: Path) -> State:
    """Return current state from filesystem markers in <workspace>."""
    has_audio = (workspace / "audio.wav").exists()
    has_transcript = (workspace / "transcript.json").exists()
    has_diarized = (workspace / "diarized.json").exists()
    has_samples = (workspace / "samples").exists() and any(
        (workspace / "samples").iterdir()
    ) if (workspace / "samples").exists() else False
    has_suggested = (workspace / "suggested_speakers.json").exists()
    has_speakers = (workspace / "speakers.json").exists()
    has_labelled = (workspace / "labelled_transcript.md").exists()

    if has_labelled and not has_audio:
        return State.FINALIZED
    if has_speakers:
        return State.MAPPED
    if has_diarized and has_samples and has_suggested:
        return State.DIARIZED
    if has_transcript:
        return State.TRANSCRIBED
    return State.FETCHING
