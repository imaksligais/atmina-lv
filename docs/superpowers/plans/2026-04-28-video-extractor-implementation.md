# Video Extractor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a manual-trigger video ingest pipeline that converts Latvian debate/interview videos into one `documents` row per video (`platform='video'`, full speaker-labelled transcript), then extracts politician positions via a dedicated `@video-extractor` agent with timestamp-anchored source URLs.

**Architecture:** CLI scripts in `src/video_ingest/` handle deterministic mechanics (yt-dlp download → faster-whisper ASR → pyannote diarization → heuristic speaker mapping → DB write). Operator confirms `speakers.json` between fetch and finalize. A new `@video-extractor` agent does per-speaker claim extraction, reusing existing `save_analysis()` and contradiction detection. No DB schema migration: `documents.platform` already accepts arbitrary TEXT.

**Tech Stack:** Python 3.11+, faster-whisper 1.1.1 (CTranslate2 + INT8), pyannote.audio 3.3.2, yt-dlp 2025.10.7, pydub 0.25.1, torch 2.5.1+CUDA 11.8, Pydantic v2, sqlite3 (existing). HuggingFace token required for pyannote.

**Spec:** [`docs/superpowers/specs/2026-04-28-video-extractor-design.md`](../specs/2026-04-28-video-extractor-design.md)

---

## File Structure

### New Python package: `src/video_ingest/`

| File | Responsibility |
|------|----------------|
| `__init__.py` | Empty marker |
| `__main__.py` | One-liner: `from src.video_ingest.cli import main; main()` |
| `cli.py` | argparse with subcommands: `fetch`, `finalize`, `extract-claims`, `status`, `archive` |
| `config.py` | Constants (paths, defaults), `load_hf_token()` |
| `models.py` | Pydantic v2 models: `Metadata`, `TranscriptSegment`, `DiarizedSegment`, `AlignedSegment`, `SpeakerMapping`, `ContextCue` |
| `state.py` | `compute_state(slug) -> str` from filesystem markers |
| `fetch.py` | `slugify(metadata) -> str`, `fetch_video(input, slug) -> Path`, `extract_audio(video_path) -> Path` |
| `asr.py` | `transcribe(audio_wav) -> dict` (faster-whisper wrapper) |
| `diarize.py` | `diarize(audio_wav) -> list[DiarizedSegment]`, `extract_samples(audio_wav, segments, out_dir)` |
| `align.py` | `align(transcript, diarized) -> list[AlignedSegment]` (pure function) |
| `heuristics.py` | `compute_cues(aligned, politicians) -> list[ContextCue]`, `suggest_speakers(cues) -> dict[str, SpeakerMapping]` |
| `finalize.py` | `validate_speakers(speakers, db) -> None`, `build_labelled_transcript(aligned, speakers) -> str`, `finalize_to_db(slug, db) -> int` |
| `db.py` | `insert_video_document(db, **fields) -> int`, `link_subjects(db, document_id, pids)` |

### New tests: `tests/`

| File | Coverage |
|------|----------|
| `test_video_ingest_models.py` | Pydantic schema validation |
| `test_video_ingest_state.py` | State machine from filesystem markers |
| `test_video_ingest_slug.py` | Slugify rules |
| `test_video_ingest_align.py` | transcript ⊕ diarized math (pure function) |
| `test_video_ingest_heuristics.py` | Regex rules + suggested_speakers.json |
| `test_video_ingest_finalize.py` | tmp DB + idempotence + INSERTs |
| `test_video_ingest_fetch.py` | mock yt-dlp; slug + metadata.json |
| `test_video_ingest_asr.py` | mock faster-whisper; transcript.json shape |
| `test_video_ingest_diarize.py` | mock pyannote; diarized.json + samples |
| `test_video_ingest_cli.py` | argparse dispatch |
| `tests/fixtures/video/` | Golden mock JSONs (5-min mock transkripts) |

### Agent + docs

| File | Purpose |
|------|---------|
| `.claude/agents/video-extractor.md` | Canonical agent prompt |
| `wiki/operations/agenti/video-extractor.md` | Human-readable agent description |
| `wiki/operations/video-setup.md` | One-time setup (ffmpeg, HF token, pyannote licenses) |
| `wiki/operations/operacijas.md` | New "Video ingest" section (4-phase runbook) |
| `CLAUDE.md` | Add `platform='video'` invariant rule |
| `wiki/CHANGELOG.md` | Entry on merge day |
| `requirements.txt` | Add 6 new packages |

---

## Task Order Rationale

Dependency graph drives order:

1. **Foundations first** — config, models, state. No transitive deps, easy to test.
2. **Pure functions next** — slugify, align, heuristics. No I/O, fast tests.
3. **Wrappers in isolation** — fetch, asr, diarize. Each mocked independently.
4. **Composition last** — finalize, cli, agent. Pull together pre-built pieces.
5. **Docs at end** — once API stable.

This minimises rework: if Pydantic models change in Task 2, Task 9 doesn't have to re-design.

---

## Phase 0: Setup (no code yet)

### Task 1: Add new dependencies

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Append video stack to requirements.txt**

```
# Video ingest stack (Phase 1, pre-election video extraction)
yt-dlp==2025.10.7
faster-whisper==1.1.1
pyannote.audio==3.3.2
pydub==0.25.1
torch==2.5.1
torchaudio==2.5.1
```

- [ ] **Step 2: Install + verify**

```bash
.venv/Scripts/pip install -r requirements.txt
.venv/Scripts/python -c "import yt_dlp, faster_whisper, pyannote.audio, pydub, torch; print('ok', torch.cuda.is_available())"
```

Expected output: `ok True` (CUDA available for GTX 1060).

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "feat(video): add yt-dlp, faster-whisper, pyannote, pydub, torch deps"
```

### Task 2: Create package skeleton

**Files:**
- Create: `src/video_ingest/__init__.py`
- Create: `src/video_ingest/__main__.py`
- Create: `src/video_ingest/cli.py` (placeholder main)

- [ ] **Step 1: Empty `__init__.py`**

```python
# src/video_ingest/__init__.py
```

- [ ] **Step 2: `__main__.py` entry**

```python
# src/video_ingest/__main__.py
from src.video_ingest.cli import main

if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Placeholder `cli.py`**

```python
# src/video_ingest/cli.py
"""CLI dispatcher: fetch / finalize / extract-claims / status / archive."""
from __future__ import annotations

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m src.video_ingest")
    parser.add_argument("command", choices=["fetch", "finalize", "extract-claims", "status", "archive"])
    args, _ = parser.parse_known_args()
    print(f"[video_ingest] command={args.command} (not implemented)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run smoke test**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m src.video_ingest fetch
```

Expected stderr: `[video_ingest] command=fetch (not implemented)`. Exit code 1.

- [ ] **Step 5: Commit**

```bash
git add src/video_ingest/
git commit -m "feat(video): scaffold src/video_ingest package + CLI skeleton"
```

---

## Phase 1: Foundations

### Task 3: Pydantic models

**Files:**
- Create: `src/video_ingest/models.py`
- Test: `tests/test_video_ingest_models.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_video_ingest_models.py
import pytest
from pydantic import ValidationError

from src.video_ingest.models import (
    Metadata, TranscriptSegment, DiarizedSegment,
    AlignedSegment, SpeakerMapping, ContextCue,
)


def test_metadata_minimal():
    m = Metadata(
        url="https://www.youtube.com/watch?v=abc",
        title="Test debate",
        published_at="2026-04-15",
        language="lv",
        duration_seconds=300,
        source_domain="youtube.com",
    )
    assert m.uploader is None
    assert m.duration_seconds == 300


def test_transcript_segment_word_level():
    s = TranscriptSegment(
        start=0.0, end=2.5, text="Sveicināti studijā.",
        words=[{"word": "Sveicināti", "start": 0.0, "end": 0.9}],
    )
    assert s.start == 0.0


def test_diarized_segment_speaker_letters():
    DiarizedSegment(start=0.0, end=2.0, speaker="A")
    DiarizedSegment(start=2.0, end=5.0, speaker="SPEAKER_05")  # pyannote raw labels


def test_aligned_segment_combines():
    a = AlignedSegment(start=0.0, end=2.0, speaker="A", text="Paldies.")
    assert a.speaker == "A"


def test_speaker_mapping_pid_or_handle():
    sm = SpeakerMapping(pid=3, handle="SlesersAinars", confidence=0.9, evidence="01:23 cue")
    assert sm.pid == 3
    sm2 = SpeakerMapping(pid=None, handle="host", confidence=0.6, evidence="first speaker")
    assert sm2.pid is None


def test_speaker_mapping_confidence_range():
    with pytest.raises(ValidationError):
        SpeakerMapping(pid=None, handle="x", confidence=1.5, evidence="")


def test_context_cue_minimal():
    c = ContextCue(speaker="A", cue_type="addressed_by_name", text="Andri", at_seconds=23.0)
    assert c.cue_type == "addressed_by_name"
```

- [ ] **Step 2: Run test, verify FAIL**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_video_ingest_models.py -v
```

Expected: `ImportError: cannot import name 'Metadata' from 'src.video_ingest.models'`.

- [ ] **Step 3: Implement models**

```python
# src/video_ingest/models.py
"""Pydantic v2 models for video_ingest JSON contracts."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class Metadata(BaseModel):
    url: str
    title: str
    published_at: str  # ISO 8601 date or datetime
    language: str = "lv"
    duration_seconds: int
    source_domain: str
    uploader: str | None = None


class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str
    words: list[dict[str, Any]] = Field(default_factory=list)


class DiarizedSegment(BaseModel):
    start: float
    end: float
    speaker: str  # "A" / "SPEAKER_05" depending on pyannote raw output


class AlignedSegment(BaseModel):
    start: float
    end: float
    speaker: str
    text: str


class SpeakerMapping(BaseModel):
    pid: int | None
    handle: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: str


class ContextCue(BaseModel):
    speaker: str
    cue_type: Literal[
        "addressed_by_name",
        "self_introduction",
        "formal_phrase",
        "first_speaker_greeting",
        "saeima_role",
    ]
    text: str
    at_seconds: float
    matched_pid: int | None = None  # if cue resolves to specific politician
```

- [ ] **Step 4: Run test, verify PASS**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_video_ingest_models.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/video_ingest/models.py tests/test_video_ingest_models.py
git commit -m "feat(video): Pydantic models for video_ingest JSON contracts"
```

### Task 4: Config + paths + HF token loader

**Files:**
- Create: `src/video_ingest/config.py`
- Test: `tests/test_video_ingest_config.py`
- Modify: `data/credentials.json` is the existing pattern; we look there first, then env.

- [ ] **Step 1: Inspect existing credentials pattern**

```bash
grep -n "credentials" src/credentials.py 2>/dev/null | head -5
ls data/ | grep -i "key\|cred\|cookies" | head
```

Note: existing pattern is `data/<name>_key.json` or `data/credentials.json`. We'll use `data/hf_token.json` to match.

- [ ] **Step 2: Write failing test**

```python
# tests/test_video_ingest_config.py
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.video_ingest.config import (
    load_hf_token, video_workspace_dir, slug_from_metadata, VIDEO_ROOT,
)


def test_load_hf_token_from_file(tmp_path, monkeypatch):
    key_file = tmp_path / "hf_token.json"
    key_file.write_text(json.dumps({"token": "hf_abcd1234"}), encoding="utf-8")
    monkeypatch.setattr("src.video_ingest.config.HF_TOKEN_PATH", key_file)
    monkeypatch.delenv("HUGGINGFACE_TOKEN", raising=False)
    assert load_hf_token() == "hf_abcd1234"


def test_load_hf_token_from_env(tmp_path, monkeypatch):
    nonexistent = tmp_path / "missing.json"
    monkeypatch.setattr("src.video_ingest.config.HF_TOKEN_PATH", nonexistent)
    monkeypatch.setenv("HUGGINGFACE_TOKEN", "hf_envtoken")
    assert load_hf_token() == "hf_envtoken"


def test_load_hf_token_missing_raises(tmp_path, monkeypatch):
    monkeypatch.setattr("src.video_ingest.config.HF_TOKEN_PATH", tmp_path / "nope.json")
    monkeypatch.delenv("HUGGINGFACE_TOKEN", raising=False)
    with pytest.raises(FileNotFoundError) as exc:
        load_hf_token()
    assert "huggingface" in str(exc.value).lower()


def test_video_workspace_dir_creates(tmp_path, monkeypatch):
    monkeypatch.setattr("src.video_ingest.config.VIDEO_ROOT", tmp_path / "videos")
    p = video_workspace_dir("2026-04-15-test-slug")
    assert p.exists()
    assert p.name == "2026-04-15-test-slug"


def test_slug_from_metadata_basic():
    slug = slug_from_metadata(
        published_at="2026-04-15",
        title="Kas Notiek Latvijā #345 — vēlēšanas",
    )
    assert slug.startswith("2026-04-15-")
    assert "kas-notiek-latvija" in slug.lower() or "knl" in slug.lower()
    assert len(slug) <= 60


def test_slug_from_metadata_diacritics_stripped():
    slug = slug_from_metadata(published_at="2026-04-15", title="Šlesera intervija")
    assert "š" not in slug
    assert slug.isascii()
```

- [ ] **Step 3: Run test, verify FAIL**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_video_ingest_config.py -v
```

Expected: ImportError.

- [ ] **Step 4: Implement config**

```python
# src/video_ingest/config.py
"""Paths, defaults, HuggingFace token loader for video_ingest."""
from __future__ import annotations

import json
import os
import re
import unicodedata
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
VIDEO_ROOT = REPO_ROOT / ".scratch" / "videos"
HF_TOKEN_PATH = REPO_ROOT / "data" / "hf_token.json"

# Defaults
WHISPER_MODEL = "large-v3"
WHISPER_COMPUTE_TYPE = "int8_float16"  # fits ~2GB on GTX 1060 6GB
WHISPER_LANGUAGE = "lv"
PYANNOTE_MODEL = "pyannote/speaker-diarization-3.1"
SAMPLE_DURATION_SEC = 10
SAMPLE_FORMAT = "mp3"


def load_hf_token() -> str:
    """Load HF token from data/hf_token.json or HUGGINGFACE_TOKEN env. Raises FileNotFoundError."""
    if HF_TOKEN_PATH.exists():
        data = json.loads(HF_TOKEN_PATH.read_text(encoding="utf-8"))
        token = data.get("token", "").strip()
        if token:
            return token
    env_token = os.environ.get("HUGGINGFACE_TOKEN", "").strip()
    if env_token:
        return env_token
    raise FileNotFoundError(
        f"HuggingFace token not found. Create {HF_TOKEN_PATH} with "
        '{"token": "hf_..."} or export HUGGINGFACE_TOKEN. '
        "See wiki/operations/video-setup.md."
    )


def video_workspace_dir(slug: str) -> Path:
    """Return .scratch/videos/<slug>/, creating it if needed."""
    p = VIDEO_ROOT / slug
    p.mkdir(parents=True, exist_ok=True)
    return p


_SLUG_RE = re.compile(r"[^a-z0-9-]+")


def slug_from_metadata(published_at: str, title: str, max_len: int = 50) -> str:
    """Build YYYY-MM-DD-<slugified-title> (max_len chars total).

    Strips Latvian diacritics, lowercases, replaces non-alphanumeric with hyphen.
    """
    date = published_at[:10]  # 'YYYY-MM-DD' from ISO date or datetime
    # Strip diacritics
    norm = unicodedata.normalize("NFKD", title)
    ascii_title = "".join(c for c in norm if not unicodedata.combining(c)).lower()
    # Replace non-alnum with hyphen
    slug_title = _SLUG_RE.sub("-", ascii_title).strip("-")
    # Truncate
    available = max_len - len(date) - 1  # date + dash
    if len(slug_title) > available:
        slug_title = slug_title[:available].rsplit("-", 1)[0]
    return f"{date}-{slug_title}" if slug_title else date
```

- [ ] **Step 5: Run test, verify PASS**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_video_ingest_config.py -v
```

Expected: 6 passed.

- [ ] **Step 6: Commit**

```bash
git add src/video_ingest/config.py tests/test_video_ingest_config.py
git commit -m "feat(video): config (paths, HF token loader, slug from metadata)"
```

### Task 5: State machine

**Files:**
- Create: `src/video_ingest/state.py`
- Test: `tests/test_video_ingest_state.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_video_ingest_state.py
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
```

- [ ] **Step 2: Run test, verify FAIL**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_video_ingest_state.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement state machine**

```python
# src/video_ingest/state.py
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
```

- [ ] **Step 4: Run test, verify PASS**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_video_ingest_state.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/video_ingest/state.py tests/test_video_ingest_state.py
git commit -m "feat(video): filesystem-based state machine (compute_state)"
```

---

## Phase 2: Pure functions

### Task 6: Alignment (transcript ⊕ diarized → aligned)

**Files:**
- Create: `src/video_ingest/align.py`
- Test: `tests/test_video_ingest_align.py`

Algorithm: for each transcript segment, find which diarized segment its midpoint falls into; that speaker labels the segment. Adjacent same-speaker transcript segments collapse into one aligned segment.

- [ ] **Step 1: Write failing test**

```python
# tests/test_video_ingest_align.py
from src.video_ingest.align import align
from src.video_ingest.models import TranscriptSegment, DiarizedSegment, AlignedSegment


def test_align_single_speaker():
    transcript = [
        TranscriptSegment(start=0.0, end=2.0, text="Hello world."),
    ]
    diarized = [DiarizedSegment(start=0.0, end=5.0, speaker="A")]
    aligned = align(transcript, diarized)
    assert len(aligned) == 1
    assert aligned[0].speaker == "A"
    assert aligned[0].text == "Hello world."


def test_align_two_speakers_no_overlap():
    transcript = [
        TranscriptSegment(start=0.0, end=2.0, text="Sveiki!"),
        TranscriptSegment(start=2.0, end=5.0, text="Paldies par jautājumu."),
    ]
    diarized = [
        DiarizedSegment(start=0.0, end=2.0, speaker="A"),
        DiarizedSegment(start=2.0, end=5.0, speaker="B"),
    ]
    aligned = align(transcript, diarized)
    assert [a.speaker for a in aligned] == ["A", "B"]
    assert aligned[1].text == "Paldies par jautājumu."


def test_align_collapses_consecutive_same_speaker():
    transcript = [
        TranscriptSegment(start=0.0, end=2.0, text="Pirmā teikuma daļa."),
        TranscriptSegment(start=2.0, end=4.0, text="Otrā teikuma daļa."),
    ]
    diarized = [DiarizedSegment(start=0.0, end=4.0, speaker="A")]
    aligned = align(transcript, diarized)
    assert len(aligned) == 1
    assert aligned[0].text == "Pirmā teikuma daļa. Otrā teikuma daļa."


def test_align_midpoint_falls_in_speaker_range():
    """Whisper segment 1.0-3.0 has midpoint 2.0; pyannote A=0-1.5, B=1.5-3.0 → speaker B."""
    transcript = [TranscriptSegment(start=1.0, end=3.0, text="Mid speech.")]
    diarized = [
        DiarizedSegment(start=0.0, end=1.5, speaker="A"),
        DiarizedSegment(start=1.5, end=3.0, speaker="B"),
    ]
    aligned = align(transcript, diarized)
    assert aligned[0].speaker == "B"


def test_align_empty_transcript():
    aligned = align([], [DiarizedSegment(start=0, end=1, speaker="A")])
    assert aligned == []


def test_align_speaker_outside_diarized_range():
    """Transcript extends past last diarized segment → speaker UNKNOWN."""
    transcript = [TranscriptSegment(start=0.0, end=5.0, text="Past end.")]
    diarized = [DiarizedSegment(start=0.0, end=2.0, speaker="A")]
    aligned = align(transcript, diarized)
    assert aligned[0].speaker == "UNKNOWN"
```

- [ ] **Step 2: Run test, verify FAIL**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_video_ingest_align.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement align**

```python
# src/video_ingest/align.py
"""Pure function: combine Whisper transcript with pyannote diarization.

Each transcript segment is labelled with the speaker whose diarized range
contains the segment midpoint. Consecutive same-speaker segments collapse.
"""
from __future__ import annotations

from src.video_ingest.models import (
    AlignedSegment, DiarizedSegment, TranscriptSegment,
)

UNKNOWN_SPEAKER = "UNKNOWN"


def _speaker_at(t: float, diarized: list[DiarizedSegment]) -> str:
    for d in diarized:
        if d.start <= t < d.end:
            return d.speaker
    return UNKNOWN_SPEAKER


def align(
    transcript: list[TranscriptSegment],
    diarized: list[DiarizedSegment],
) -> list[AlignedSegment]:
    if not transcript:
        return []

    labelled: list[AlignedSegment] = []
    for seg in transcript:
        midpoint = (seg.start + seg.end) / 2.0
        speaker = _speaker_at(midpoint, diarized)
        labelled.append(AlignedSegment(
            start=seg.start, end=seg.end, speaker=speaker, text=seg.text,
        ))

    # Collapse consecutive same-speaker segments
    collapsed: list[AlignedSegment] = []
    for seg in labelled:
        if collapsed and collapsed[-1].speaker == seg.speaker:
            prev = collapsed[-1]
            collapsed[-1] = AlignedSegment(
                start=prev.start,
                end=seg.end,
                speaker=prev.speaker,
                text=f"{prev.text} {seg.text}".strip(),
            )
        else:
            collapsed.append(seg)
    return collapsed
```

- [ ] **Step 4: Run test, verify PASS**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_video_ingest_align.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/video_ingest/align.py tests/test_video_ingest_align.py
git commit -m "feat(video): align — combine Whisper transcript with pyannote speakers"
```

### Task 7: Heuristics — context cues

**Files:**
- Create: `src/video_ingest/heuristics.py`
- Test: `tests/test_video_ingest_heuristics.py`

Two responsibilities: (a) extract `ContextCue` objects from aligned transcript by regex; (b) aggregate cues into `SpeakerMapping` per speaker.

- [ ] **Step 1: Write failing test**

```python
# tests/test_video_ingest_heuristics.py
import json
from src.video_ingest.heuristics import compute_cues, suggest_speakers
from src.video_ingest.models import AlignedSegment


def _make_politicians():
    """Mock list mimicking shape returned by tracked_politicians query."""
    return [
        {"id": 3, "name": "Ainārs Šlesers", "x_handle": "SlesersAinars",
         "name_forms": "Andri,Andrij,Šleser,Šleseri", "role": "Saeimas deputāts"},
        {"id": 12, "name": "Evika Siliņa", "x_handle": "EvikaSilina",
         "name_forms": "Evik,Evika,Siliņa,Siliņu", "role": "Ministru prezidente"},
    ]


def test_addressed_by_name_cue():
    aligned = [
        AlignedSegment(start=23.0, end=25.0, speaker="B",
                       text="Paldies, Andri Šleser, par viedokli."),
    ]
    cues = compute_cues(aligned, _make_politicians())
    assert any(c.cue_type == "addressed_by_name" and c.matched_pid == 3 for c in cues)


def test_self_introduction_cue():
    aligned = [
        AlignedSegment(start=10.0, end=15.0, speaker="A",
                       text="Mans vārds ir Ainārs Šlesers, esmu LPV līderis."),
    ]
    cues = compute_cues(aligned, _make_politicians())
    intro = [c for c in cues if c.cue_type == "self_introduction"]
    assert len(intro) == 1
    assert intro[0].matched_pid == 3
    assert intro[0].speaker == "A"


def test_first_speaker_greeting():
    aligned = [
        AlignedSegment(start=0.0, end=5.0, speaker="A",
                       text="Sveicināti, šovakar studijā..."),
    ]
    cues = compute_cues(aligned, _make_politicians())
    assert any(c.cue_type == "first_speaker_greeting" and c.speaker == "A" for c in cues)


def test_suggest_speakers_high_confidence():
    aligned = [
        AlignedSegment(start=0.0, end=5.0, speaker="A",
                       text="Sveicināti, šovakar studijā..."),
        AlignedSegment(start=10.0, end=15.0, speaker="B",
                       text="Mans vārds ir Ainārs Šlesers."),
    ]
    cues = compute_cues(aligned, _make_politicians())
    suggestions = suggest_speakers(cues, _make_politicians())
    assert "A" in suggestions
    assert suggestions["A"].handle == "host"
    assert "B" in suggestions
    assert suggestions["B"].pid == 3
    assert suggestions["B"].confidence >= 0.85


def test_suggest_speakers_no_evidence_returns_unknown():
    aligned = [
        AlignedSegment(start=0.0, end=5.0, speaker="C",
                       text="Es uzskatu, ka tas ir slikti."),
    ]
    cues = compute_cues(aligned, _make_politicians())
    suggestions = suggest_speakers(cues, _make_politicians())
    assert suggestions["C"].pid is None
    assert suggestions["C"].confidence == 0.0
    assert suggestions["C"].handle.startswith("unknown_")
```

- [ ] **Step 2: Run test, verify FAIL**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_video_ingest_heuristics.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement heuristics**

```python
# src/video_ingest/heuristics.py
"""Regex-based context cue extraction + per-speaker mapping suggestions.

Cues feed `suggested_speakers.json`, which the operator confirms. Heuristics
are deliberately conservative — confidence < 0.7 means manual review needed.
"""
from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from typing import Iterable

from src.video_ingest.models import AlignedSegment, ContextCue, SpeakerMapping

# Regex patterns
_GREETING_RE = re.compile(
    r"^(sveicināti|sveiki|labvakar|labrīt)\b",
    re.IGNORECASE,
)
_SELF_INTRO_RE = re.compile(
    r"\b(mans vārds ir|es esmu)\s+([A-ZĀČĒĢĪĶĻŅŠŪŽ][\w-]+(?:\s+[A-ZĀČĒĢĪĶĻŅŠŪŽ][\w-]+)?)",
)
_ADDRESS_RE = re.compile(
    r"\b(paldies|sveiki|lūdzu|jā)[, ]+([A-ZĀČĒĢĪĶĻŅŠŪŽ][\w-]+)",
    re.IGNORECASE,
)
_FORMAL_PHRASE_RE = re.compile(
    r"\bkā\s+([\w ]+ministrs|ministre|deputāts|deputāte|premjere?s?|frakcijas vadītāj[su]?)",
    re.IGNORECASE,
)


def _normalize(text: str) -> str:
    """Lowercase + strip diacritics for substring matching."""
    norm = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in norm if not unicodedata.combining(c))


def _name_forms_match(name_form: str, candidate: str) -> bool:
    return _normalize(name_form) == _normalize(candidate)


def _resolve_pid(name_token: str, politicians: list[dict]) -> int | None:
    for p in politicians:
        if _name_forms_match(p["name"], name_token):
            return p["id"]
        forms = (p.get("name_forms") or "").split(",")
        for f in forms:
            f = f.strip()
            if f and _name_forms_match(f, name_token):
                return p["id"]
    return None


def compute_cues(
    aligned: list[AlignedSegment],
    politicians: list[dict],
) -> list[ContextCue]:
    cues: list[ContextCue] = []

    seen_first = False
    for seg in aligned:
        text = seg.text

        # First-speaker greeting (only first segment)
        if not seen_first and _GREETING_RE.search(text):
            cues.append(ContextCue(
                speaker=seg.speaker, cue_type="first_speaker_greeting",
                text=text[:80], at_seconds=seg.start,
            ))
        seen_first = True

        # Self-introduction
        m = _SELF_INTRO_RE.search(text)
        if m:
            name = m.group(2).strip()
            pid = _resolve_pid(name, politicians)
            cues.append(ContextCue(
                speaker=seg.speaker, cue_type="self_introduction",
                text=name, at_seconds=seg.start, matched_pid=pid,
            ))

        # Addressed by name (resolves to OTHER speaker — cue speaker = current)
        for m in _ADDRESS_RE.finditer(text):
            addressed = m.group(2).strip()
            pid = _resolve_pid(addressed, politicians)
            if pid is not None:
                # Tag the speaker BEING ADDRESSED, not the current speaker
                # We don't know which speaker; downstream uses this as evidence
                # for the speaker who responds next. For simplicity we tag with
                # current speaker; suggest_speakers reasons about next-segment.
                cues.append(ContextCue(
                    speaker=seg.speaker, cue_type="addressed_by_name",
                    text=addressed, at_seconds=seg.start, matched_pid=pid,
                ))

        # Formal phrase
        m = _FORMAL_PHRASE_RE.search(text)
        if m:
            cues.append(ContextCue(
                speaker=seg.speaker, cue_type="formal_phrase",
                text=m.group(0)[:80], at_seconds=seg.start,
            ))

    return cues


def suggest_speakers(
    cues: list[ContextCue],
    politicians: list[dict],
) -> dict[str, SpeakerMapping]:
    """Aggregate cues into one SpeakerMapping per unique speaker.

    Confidence rubric:
      0.95 = self-introduction matched a politician
      0.85 = addressed-by-name across multiple cues converging on same pid
      0.70 = first-speaker greeting (likely host)
      0.50 = single addressed-by-name cue
      0.00 = no matched cues (unknown)
    """
    pid_to_handle = {p["id"]: p["x_handle"] for p in politicians if p.get("x_handle")}
    pid_to_name = {p["id"]: p["name"] for p in politicians}

    by_speaker: dict[str, list[ContextCue]] = defaultdict(list)
    for c in cues:
        by_speaker[c.speaker].append(c)

    # Also collect addressed cues per ADDRESSED politician (the speaker getting
    # addressed is likely the responder in next segment — but for MVP we just
    # use addressed cues as positive evidence on the addressed politician's pid)

    # All speakers we want to map (collect from cues + segments)
    all_speakers = set(by_speaker.keys())

    suggestions: dict[str, SpeakerMapping] = {}
    for spk in sorted(all_speakers):
        spk_cues = by_speaker[spk]

        # Self-introduction is highest signal
        intro = [c for c in spk_cues if c.cue_type == "self_introduction" and c.matched_pid]
        if intro:
            pid = intro[0].matched_pid
            suggestions[spk] = SpeakerMapping(
                pid=pid,
                handle=pid_to_handle.get(pid, f"pid_{pid}"),
                confidence=0.95,
                evidence=f"{int(intro[0].at_seconds // 60):02d}:{int(intro[0].at_seconds % 60):02d} "
                         f"pašprezentācija '{intro[0].text}'",
            )
            continue

        # First-speaker greeting → host
        greet = [c for c in spk_cues if c.cue_type == "first_speaker_greeting"]
        if greet and not any(c.matched_pid for c in spk_cues):
            suggestions[spk] = SpeakerMapping(
                pid=None,
                handle="host",
                confidence=0.70,
                evidence=f"{int(greet[0].at_seconds // 60):02d}:{int(greet[0].at_seconds % 60):02d} "
                         f"pirmais runātājs ar formālu sveicienu",
            )
            continue

        # Otherwise unknown
        suggestions[spk] = SpeakerMapping(
            pid=None,
            handle=f"unknown_{spk}",
            confidence=0.0,
            evidence="Nav konteksta zīmju; vajag manuālu verifikāciju",
        )

    return suggestions
```

- [ ] **Step 4: Run test, verify PASS**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_video_ingest_heuristics.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/video_ingest/heuristics.py tests/test_video_ingest_heuristics.py
git commit -m "feat(video): heuristic speaker mapping (regex cues + suggested_speakers.json)"
```

---

## Phase 3: External wrappers

### Task 8: yt-dlp fetch wrapper + audio extraction

**Files:**
- Create: `src/video_ingest/fetch.py`
- Test: `tests/test_video_ingest_fetch.py`

- [ ] **Step 1: Write failing test (mock yt-dlp)**

```python
# tests/test_video_ingest_fetch.py
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.video_ingest.fetch import fetch_video, write_metadata


def test_fetch_local_file_copies_audio(tmp_path, monkeypatch):
    """When input is a local file, copy + extract audio without yt-dlp."""
    src_video = tmp_path / "input.mp4"
    src_video.write_bytes(b"fake video bytes")

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    extracted = []
    def fake_extract_audio(video_path, out_wav):
        extracted.append((video_path, out_wav))
        out_wav.write_bytes(b"fake wav")
        return out_wav

    monkeypatch.setattr("src.video_ingest.fetch.extract_audio", fake_extract_audio)

    audio_path = fetch_video(str(src_video), workspace)
    assert audio_path == workspace / "audio.wav"
    assert audio_path.exists()
    assert len(extracted) == 1


def test_fetch_url_invokes_ytdlp(tmp_path, monkeypatch):
    """When input is URL, yt-dlp downloads to workspace, then audio extracted."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    download_calls = []

    def fake_run_ytdlp(url, out_dir):
        download_calls.append((url, out_dir))
        video = out_dir / "video.mp4"
        video.write_bytes(b"fake")
        meta = {
            "url": url,
            "title": "Test debate",
            "uploader": "TestChan",
            "upload_date": "20260415",
            "language": "lv",
            "duration": 300,
            "extractor": "youtube",
        }
        return video, meta

    extracted = []
    def fake_extract_audio(video_path, out_wav):
        extracted.append((video_path, out_wav))
        out_wav.write_bytes(b"fake wav")
        return out_wav

    monkeypatch.setattr("src.video_ingest.fetch._run_ytdlp", fake_run_ytdlp)
    monkeypatch.setattr("src.video_ingest.fetch.extract_audio", fake_extract_audio)

    audio_path = fetch_video("https://www.youtube.com/watch?v=test", workspace)
    assert audio_path.exists()
    assert len(download_calls) == 1
    assert (workspace / "metadata.json").exists()
    meta = json.loads((workspace / "metadata.json").read_text(encoding="utf-8"))
    assert meta["title"] == "Test debate"
    assert meta["source_domain"] == "youtube.com"


def test_fetch_url_invalid_raises(tmp_path, monkeypatch):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    def fake_run_ytdlp(url, out_dir):
        raise RuntimeError("yt-dlp: video unavailable")

    monkeypatch.setattr("src.video_ingest.fetch._run_ytdlp", fake_run_ytdlp)
    with pytest.raises(RuntimeError):
        fetch_video("https://blocked.example/x", workspace)


def test_write_metadata_local_file(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    src = tmp_path / "knl.mp4"
    src.write_bytes(b"")

    write_metadata(
        workspace=workspace,
        url=f"file://{src}",
        title="knl.mp4",
        published_at="2026-04-15",
        language="lv",
        duration_seconds=0,
        source_domain="local",
        uploader=None,
    )
    meta = json.loads((workspace / "metadata.json").read_text(encoding="utf-8"))
    assert meta["url"].endswith("knl.mp4")
```

- [ ] **Step 2: Run test, verify FAIL**

Expected: ImportError.

- [ ] **Step 3: Implement fetch**

```python
# src/video_ingest/fetch.py
"""Video acquisition: yt-dlp for URLs, direct copy for local files. Audio
extraction via ffmpeg (subprocess) into 16 kHz mono WAV."""
from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import yt_dlp


def _run_ytdlp(url: str, out_dir: Path) -> tuple[Path, dict]:
    """Run yt-dlp; return (video_file_path, info_dict). Raises on failure."""
    ydl_opts = {
        "outtmpl": str(out_dir / "video.%(ext)s"),
        "format": "bestaudio/best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
    # yt-dlp picks an extension; find it
    candidates = sorted(out_dir.glob("video.*"))
    if not candidates:
        raise RuntimeError("yt-dlp finished but no video file produced")
    return candidates[0], info


def extract_audio(video_path: Path, out_wav: Path) -> Path:
    """ffmpeg → 16 kHz mono WAV. Raises CalledProcessError on failure."""
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(video_path),
            "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
            str(out_wav),
        ],
        check=True, capture_output=True,
    )
    return out_wav


def write_metadata(
    workspace: Path,
    *, url: str, title: str, published_at: str, language: str,
    duration_seconds: int, source_domain: str, uploader: str | None,
) -> None:
    meta = {
        "url": url,
        "title": title,
        "uploader": uploader,
        "published_at": published_at,
        "language": language,
        "duration_seconds": duration_seconds,
        "source_domain": source_domain,
    }
    (workspace / "metadata.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8",
    )


def _format_yt_date(yyyymmdd: str | None) -> str:
    """yt-dlp returns YYYYMMDD; convert to YYYY-MM-DD."""
    if not yyyymmdd or len(yyyymmdd) != 8:
        return datetime.now().strftime("%Y-%m-%d")
    return f"{yyyymmdd[:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:8]}"


def fetch_video(input_arg: str, workspace: Path) -> Path:
    """Download video (URL) or copy local file; extract 16 kHz mono WAV.

    Returns: Path to audio.wav. Side effect: writes metadata.json.
    """
    workspace.mkdir(parents=True, exist_ok=True)
    out_wav = workspace / "audio.wav"
    parsed = urlparse(input_arg)

    if parsed.scheme in ("http", "https"):
        video, info = _run_ytdlp(input_arg, workspace)
        write_metadata(
            workspace=workspace,
            url=input_arg,
            title=info.get("title", "untitled"),
            published_at=_format_yt_date(info.get("upload_date")),
            language=info.get("language") or "lv",
            duration_seconds=int(info.get("duration") or 0),
            source_domain=parsed.netloc,
            uploader=info.get("uploader"),
        )
    else:
        # Local file
        src = Path(input_arg).resolve()
        if not src.exists():
            raise FileNotFoundError(f"Local video not found: {src}")
        video = workspace / f"video{src.suffix}"
        shutil.copy(src, video)
        write_metadata(
            workspace=workspace,
            url=f"file://{src}",
            title=src.stem,
            published_at=datetime.fromtimestamp(src.stat().st_mtime).strftime("%Y-%m-%d"),
            language="lv",
            duration_seconds=0,  # unknown; ffprobe could fill this later
            source_domain="local",
            uploader=None,
        )

    extract_audio(video, out_wav)
    return out_wav
```

- [ ] **Step 4: Run test, verify PASS**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_video_ingest_fetch.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/video_ingest/fetch.py tests/test_video_ingest_fetch.py
git commit -m "feat(video): fetch (yt-dlp wrapper + local file copy + audio extraction)"
```

### Task 9: faster-whisper ASR wrapper

**Files:**
- Create: `src/video_ingest/asr.py`
- Test: `tests/test_video_ingest_asr.py`

- [ ] **Step 1: Write failing test (mock WhisperModel)**

```python
# tests/test_video_ingest_asr.py
import json
from pathlib import Path
from unittest.mock import MagicMock

from src.video_ingest.asr import transcribe


def _mock_segment(start, end, text, words=None):
    s = MagicMock()
    s.start = start
    s.end = end
    s.text = text
    s.words = words or []
    return s


def test_transcribe_writes_json(tmp_path, monkeypatch):
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"fake")

    fake_segments = [
        _mock_segment(0.0, 2.0, "Sveicināti, šovakar studijā..."),
        _mock_segment(2.0, 5.0, "Mūsu viesi šovakar ir..."),
    ]
    fake_info = MagicMock(language="lv", language_probability=0.99, duration=300.0)

    fake_model = MagicMock()
    fake_model.transcribe.return_value = (iter(fake_segments), fake_info)

    monkeypatch.setattr(
        "src.video_ingest.asr._load_model",
        lambda: fake_model,
    )

    out_path = transcribe(audio, tmp_path / "transcript.json", language="lv")
    assert out_path.exists()
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert data["language"] == "lv"
    assert len(data["segments"]) == 2
    assert data["segments"][0]["text"] == "Sveicināti, šovakar studijā..."


def test_transcribe_preserves_diacritics(tmp_path, monkeypatch):
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"fake")

    fake_segments = [_mock_segment(0.0, 1.5, "Pārējie politiķi nezin.")]
    fake_info = MagicMock(language="lv", language_probability=0.99, duration=2.0)
    fake_model = MagicMock()
    fake_model.transcribe.return_value = (iter(fake_segments), fake_info)

    monkeypatch.setattr("src.video_ingest.asr._load_model", lambda: fake_model)

    out_path = transcribe(audio, tmp_path / "transcript.json", language="lv")
    text = out_path.read_text(encoding="utf-8")
    assert "Pārējie" in text
    assert "politiķi" in text
```

- [ ] **Step 2: Run test, verify FAIL**

Expected: ImportError.

- [ ] **Step 3: Implement asr**

```python
# src/video_ingest/asr.py
"""faster-whisper transcription wrapper.

Loads large-v3 with INT8 quantization for GTX 1060 6GB. VAD filter on by
default to skip silent regions (prevents 'Paldies par skatīšanos' hallucination).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from faster_whisper import WhisperModel

from src.video_ingest.config import (
    WHISPER_COMPUTE_TYPE, WHISPER_LANGUAGE, WHISPER_MODEL,
)

_MODEL_CACHE: WhisperModel | None = None


def _load_model() -> WhisperModel:
    global _MODEL_CACHE
    if _MODEL_CACHE is None:
        # device='cuda' if available, else 'cpu'; faster-whisper auto-detects.
        _MODEL_CACHE = WhisperModel(
            WHISPER_MODEL,
            device="auto",
            compute_type=WHISPER_COMPUTE_TYPE,
        )
    return _MODEL_CACHE


def transcribe(
    audio_wav: Path,
    out_json: Path,
    *,
    language: str = WHISPER_LANGUAGE,
    vad_filter: bool = True,
) -> Path:
    """Transcribe WAV → write JSON {language, duration, segments[]}.

    Each segment has: {start, end, text, words}.
    """
    model = _load_model()
    segments_iter, info = model.transcribe(
        str(audio_wav),
        language=language,
        vad_filter=vad_filter,
        word_timestamps=True,
    )

    segments_out: list[dict[str, Any]] = []
    for s in segments_iter:
        words: list[dict[str, Any]] = []
        if s.words:
            for w in s.words:
                words.append({
                    "word": w.word,
                    "start": w.start,
                    "end": w.end,
                    "probability": getattr(w, "probability", None),
                })
        segments_out.append({
            "start": s.start,
            "end": s.end,
            "text": s.text.strip(),
            "words": words,
        })

    out = {
        "language": info.language,
        "language_probability": info.language_probability,
        "duration": info.duration,
        "segments": segments_out,
    }
    out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_json
```

- [ ] **Step 4: Run test, verify PASS**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_video_ingest_asr.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add src/video_ingest/asr.py tests/test_video_ingest_asr.py
git commit -m "feat(video): faster-whisper transcription wrapper (INT8 + VAD)"
```

### Task 10: pyannote diarization + sample extraction

**Files:**
- Create: `src/video_ingest/diarize.py`
- Test: `tests/test_video_ingest_diarize.py`

- [ ] **Step 1: Write failing test (mock pyannote pipeline + pydub)**

```python
# tests/test_video_ingest_diarize.py
import json
from pathlib import Path
from unittest.mock import MagicMock

from src.video_ingest.diarize import diarize, extract_samples


def _mock_pyannote_diarization():
    """pyannote returns object with itertracks(yield_label=True)."""
    diar = MagicMock()
    diar.itertracks.return_value = iter([
        (MagicMock(start=0.0, end=2.0), None, "SPEAKER_00"),
        (MagicMock(start=2.0, end=5.0), None, "SPEAKER_01"),
        (MagicMock(start=5.0, end=8.0), None, "SPEAKER_00"),
    ])
    return diar


def test_diarize_writes_json_with_letter_speakers(tmp_path, monkeypatch):
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"fake")

    fake_pipeline = MagicMock(return_value=_mock_pyannote_diarization())
    monkeypatch.setattr("src.video_ingest.diarize._load_pipeline", lambda: fake_pipeline)

    out = tmp_path / "diarized.json"
    diarize(audio, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    # Speakers re-labelled SPEAKER_00 → A, SPEAKER_01 → B
    speakers = sorted({d["speaker"] for d in data})
    assert speakers == ["A", "B"]
    assert len(data) == 3


def test_extract_samples_writes_one_per_speaker(tmp_path, monkeypatch):
    audio = tmp_path / "audio.wav"
    # Create realistic-enough WAV header so pydub can read; or mock AudioSegment
    fake_audio_segment = MagicMock()
    fake_audio_segment.__getitem__ = MagicMock(return_value=fake_audio_segment)
    fake_audio_segment.export = MagicMock()

    monkeypatch.setattr(
        "src.video_ingest.diarize.AudioSegment.from_wav",
        lambda _: fake_audio_segment,
    )

    diarized = [
        {"start": 0.0, "end": 2.0, "speaker": "A"},
        {"start": 2.0, "end": 4.0, "speaker": "B"},
        {"start": 4.0, "end": 7.0, "speaker": "A"},  # second A segment
    ]
    out_dir = tmp_path / "samples"
    out_dir.mkdir()
    extract_samples(audio, diarized, out_dir)

    # Should have called export once per UNIQUE speaker
    assert fake_audio_segment.export.call_count == 2
```

- [ ] **Step 2: Run test, verify FAIL**

Expected: ImportError.

- [ ] **Step 3: Implement diarize**

```python
# src/video_ingest/diarize.py
"""pyannote.audio 3.1 speaker diarization + per-speaker sample extraction."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from pyannote.audio import Pipeline
from pydub import AudioSegment

from src.video_ingest.config import (
    PYANNOTE_MODEL, SAMPLE_DURATION_SEC, SAMPLE_FORMAT, load_hf_token,
)

_PIPELINE_CACHE: Pipeline | None = None


def _load_pipeline() -> Pipeline:
    global _PIPELINE_CACHE
    if _PIPELINE_CACHE is None:
        _PIPELINE_CACHE = Pipeline.from_pretrained(
            PYANNOTE_MODEL,
            use_auth_token=load_hf_token(),
        )
    return _PIPELINE_CACHE


def _relabel_to_letters(raw: list[tuple[float, float, str]]) -> list[dict]:
    """Map pyannote SPEAKER_00, SPEAKER_01 → A, B in order of first appearance."""
    seen: dict[str, str] = {}
    next_letter = ord("A")
    out: list[dict] = []
    for start, end, raw_label in raw:
        if raw_label not in seen:
            seen[raw_label] = chr(next_letter)
            next_letter += 1
        out.append({"start": float(start), "end": float(end), "speaker": seen[raw_label]})
    return out


def diarize(
    audio_wav: Path,
    out_json: Path,
    *,
    num_speakers: int | None = None,
) -> Path:
    pipeline = _load_pipeline()
    kwargs = {"num_speakers": num_speakers} if num_speakers else {}
    diar = pipeline(str(audio_wav), **kwargs)

    raw_segments: list[tuple[float, float, str]] = []
    for turn, _, speaker in diar.itertracks(yield_label=True):
        raw_segments.append((turn.start, turn.end, speaker))

    relabelled = _relabel_to_letters(raw_segments)
    out_json.write_text(
        json.dumps(relabelled, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return out_json


def extract_samples(
    audio_wav: Path,
    diarized: Iterable[dict],
    out_dir: Path,
) -> None:
    """For each unique speaker, export a representative ~10s sample MP3."""
    audio = AudioSegment.from_wav(str(audio_wav))
    out_dir.mkdir(parents=True, exist_ok=True)

    by_speaker: dict[str, list[dict]] = {}
    for d in diarized:
        by_speaker.setdefault(d["speaker"], []).append(d)

    for speaker, segments in by_speaker.items():
        # Pick the longest segment for this speaker, take its middle SAMPLE_DURATION_SEC seconds
        longest = max(segments, key=lambda s: s["end"] - s["start"])
        mid = (longest["start"] + longest["end"]) / 2.0
        start_ms = int((mid - SAMPLE_DURATION_SEC / 2) * 1000)
        end_ms = start_ms + SAMPLE_DURATION_SEC * 1000
        start_ms = max(0, start_ms)
        clip = audio[start_ms:end_ms]
        out_path = out_dir / f"speaker-{speaker}.{SAMPLE_FORMAT}"
        clip.export(str(out_path), format=SAMPLE_FORMAT)
```

- [ ] **Step 4: Run test, verify PASS**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_video_ingest_diarize.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add src/video_ingest/diarize.py tests/test_video_ingest_diarize.py
git commit -m "feat(video): pyannote 3.1 diarization + per-speaker MP3 sample extraction"
```

---

## Phase 4: Composition

### Task 11: DB writer for video documents

**Files:**
- Create: `src/video_ingest/db.py`
- Test: `tests/test_video_ingest_db.py`

- [ ] **Step 1: Write failing test (uses tmp DB)**

```python
# tests/test_video_ingest_db.py
import sqlite3
import pytest

from src.video_ingest.db import (
    insert_video_document,
    link_subjects,
    find_existing_by_hash,
)


@pytest.fixture
def tmp_db(tmp_path):
    db_path = tmp_path / "test.db"
    db = sqlite3.connect(str(db_path))
    # Minimal schema for documents + document_politicians
    db.executescript("""
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT, content_hash TEXT, simhash INTEGER,
            source_id INTEGER, platform TEXT, is_auto_caption INTEGER,
            near_dupe_of INTEGER, source_domain TEXT, source_url TEXT,
            archive_path TEXT, scraped_at TEXT, word_count INTEGER,
            language TEXT, published_at TEXT, is_paywall INTEGER,
            summary TEXT, title TEXT, reviewed_at TEXT,
            reply_count INTEGER, retweet_count INTEGER, favorite_count INTEGER
        );
        CREATE TABLE document_politicians (
            document_id INTEGER, politician_id INTEGER, role TEXT,
            UNIQUE(document_id, politician_id, role)
        );
    """)
    db.commit()
    yield db
    db.close()


def test_insert_video_document_returns_id(tmp_db):
    doc_id = insert_video_document(
        tmp_db,
        content="[00:00] @host: Sveicināti.",
        content_hash="abc123",
        simhash=42,
        source_url="https://www.youtube.com/watch?v=test",
        source_domain="youtube.com",
        title="Test debate",
        published_at="2026-04-15",
        archive_path="videos/2026-04-15-test/",
        word_count=2,
        summary="Test summary.",
    )
    assert doc_id == 1
    row = tmp_db.execute("SELECT platform, source_url FROM documents WHERE id=?", (doc_id,)).fetchone()
    assert row[0] == "video"
    assert row[1] == "https://www.youtube.com/watch?v=test"


def test_find_existing_returns_id(tmp_db):
    doc_id = insert_video_document(
        tmp_db, content="x", content_hash="h1", simhash=0,
        source_url="u", source_domain="d", title="t",
        published_at="2026-04-15", archive_path="x", word_count=1, summary="",
    )
    found = find_existing_by_hash(tmp_db, "h1")
    assert found == doc_id


def test_find_existing_returns_none_when_absent(tmp_db):
    assert find_existing_by_hash(tmp_db, "nope") is None


def test_link_subjects_inserts_rows(tmp_db):
    doc_id = insert_video_document(
        tmp_db, content="x", content_hash="h", simhash=0,
        source_url="u", source_domain="d", title="t",
        published_at="2026-04-15", archive_path="x", word_count=1, summary="",
    )
    link_subjects(tmp_db, doc_id, [3, 12])
    rows = tmp_db.execute(
        "SELECT politician_id, role FROM document_politicians WHERE document_id=?",
        (doc_id,),
    ).fetchall()
    assert sorted(rows) == [(3, "subject"), (12, "subject")]


def test_link_subjects_idempotent(tmp_db):
    doc_id = insert_video_document(
        tmp_db, content="x", content_hash="h", simhash=0,
        source_url="u", source_domain="d", title="t",
        published_at="2026-04-15", archive_path="x", word_count=1, summary="",
    )
    link_subjects(tmp_db, doc_id, [3])
    link_subjects(tmp_db, doc_id, [3])  # second call must not duplicate
    count = tmp_db.execute(
        "SELECT COUNT(*) FROM document_politicians WHERE document_id=? AND politician_id=3",
        (doc_id,),
    ).fetchone()[0]
    assert count == 1
```

- [ ] **Step 2: Run test, verify FAIL**

Expected: ImportError.

- [ ] **Step 3: Implement db.py**

```python
# src/video_ingest/db.py
"""SQL helpers for video document persistence."""
from __future__ import annotations

import sqlite3

from src.db import now_lv


def find_existing_by_hash(db: sqlite3.Connection, content_hash: str) -> int | None:
    row = db.execute(
        "SELECT id FROM documents WHERE content_hash = ?",
        (content_hash,),
    ).fetchone()
    return row[0] if row else None


def insert_video_document(
    db: sqlite3.Connection,
    *, content: str, content_hash: str, simhash: int,
    source_url: str, source_domain: str, title: str,
    published_at: str, archive_path: str, word_count: int, summary: str,
    language: str = "lv",
) -> int:
    """Insert a row with platform='video'. Returns inserted document_id."""
    cur = db.execute(
        """
        INSERT INTO documents (
            content, content_hash, simhash,
            source_id, platform, is_auto_caption, near_dupe_of,
            source_domain, source_url, archive_path,
            scraped_at, word_count, language, published_at,
            is_paywall, summary, title, reviewed_at,
            reply_count, retweet_count, favorite_count
        ) VALUES (?, ?, ?, ?, 'video', 0, NULL, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, NULL, NULL, NULL, NULL)
        """,
        (
            content, content_hash, simhash,
            None,                              # source_id
            source_domain, source_url, archive_path,
            now_lv(), word_count, language, published_at,
            summary, title,
        ),
    )
    db.commit()
    return cur.lastrowid


def link_subjects(db: sqlite3.Connection, document_id: int, pids: list[int]) -> None:
    for pid in set(pids):
        db.execute(
            "INSERT OR IGNORE INTO document_politicians (document_id, politician_id, role) "
            "VALUES (?, ?, 'subject')",
            (document_id, pid),
        )
    db.commit()
```

- [ ] **Step 4: Run test, verify PASS**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_video_ingest_db.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/video_ingest/db.py tests/test_video_ingest_db.py
git commit -m "feat(video): SQL helpers (insert_video_document, link_subjects, find_existing_by_hash)"
```

### Task 12: Finalize — speaker validation + labelled transcript + DB write

**Files:**
- Create: `src/video_ingest/finalize.py`
- Test: `tests/test_video_ingest_finalize.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_video_ingest_finalize.py
import json
import sqlite3
from pathlib import Path
import pytest

from src.video_ingest.finalize import (
    build_labelled_transcript, validate_speakers, finalize_to_db,
)


def test_build_labelled_transcript_basic():
    aligned = [
        {"start": 0.0, "end": 2.0, "speaker": "A", "text": "Sveicināti."},
        {"start": 2.0, "end": 5.0, "speaker": "B", "text": "Paldies, vadītāj."},
    ]
    speakers = {
        "A": {"pid": None, "handle": "host"},
        "B": {"pid": 3, "handle": "SlesersAinars"},
    }
    md = build_labelled_transcript(aligned, speakers)
    assert "[00:00] @host: Sveicināti." in md
    assert "[00:02] @SlesersAinars: Paldies, vadītāj." in md


def test_validate_speakers_rejects_missing_pid(tmp_path):
    db = sqlite3.connect(":memory:")
    db.executescript("""
        CREATE TABLE tracked_politicians (id INTEGER PRIMARY KEY, relationship_type TEXT);
        INSERT INTO tracked_politicians VALUES (3, 'tracked');
    """)
    speakers = {
        "A": {"pid": 999, "handle": "ghost"},
    }
    with pytest.raises(ValueError) as exc:
        validate_speakers(speakers, db)
    assert "999" in str(exc.value)


def test_validate_speakers_rejects_inactive(tmp_path):
    db = sqlite3.connect(":memory:")
    db.executescript("""
        CREATE TABLE tracked_politicians (id INTEGER PRIMARY KEY, relationship_type TEXT);
        INSERT INTO tracked_politicians VALUES (5, 'inactive');
    """)
    speakers = {"A": {"pid": 5, "handle": "x"}}
    with pytest.raises(ValueError) as exc:
        validate_speakers(speakers, db)
    assert "inactive" in str(exc.value).lower()


def test_validate_speakers_accepts_null_pid(tmp_path):
    db = sqlite3.connect(":memory:")
    db.executescript("CREATE TABLE tracked_politicians (id INTEGER PRIMARY KEY, relationship_type TEXT);")
    speakers = {"A": {"pid": None, "handle": "host"}}
    validate_speakers(speakers, db)  # no raise


def test_finalize_idempotence(tmp_path, monkeypatch):
    """Running finalize twice on the same workspace yields one document row."""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "metadata.json").write_text(json.dumps({
        "url": "https://www.youtube.com/watch?v=abc",
        "title": "Test",
        "uploader": "Test",
        "published_at": "2026-04-15",
        "language": "lv",
        "duration_seconds": 60,
        "source_domain": "youtube.com",
    }), encoding="utf-8")
    (workspace / "aligned.json").write_text(json.dumps([
        {"start": 0.0, "end": 2.0, "speaker": "A", "text": "Sveiki."},
    ]), encoding="utf-8")
    (workspace / "speakers.json").write_text(json.dumps({
        "A": {"pid": None, "handle": "host", "confidence": 0.7, "evidence": "first speaker"},
    }), encoding="utf-8")
    (workspace / "audio.wav").write_bytes(b"fake")

    db = sqlite3.connect(":memory:")
    db.executescript("""
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT, content_hash TEXT, simhash INTEGER,
            source_id INTEGER, platform TEXT, is_auto_caption INTEGER,
            near_dupe_of INTEGER, source_domain TEXT, source_url TEXT,
            archive_path TEXT, scraped_at TEXT, word_count INTEGER,
            language TEXT, published_at TEXT, is_paywall INTEGER,
            summary TEXT, title TEXT, reviewed_at TEXT,
            reply_count INTEGER, retweet_count INTEGER, favorite_count INTEGER
        );
        CREATE TABLE document_politicians (
            document_id INTEGER, politician_id INTEGER, role TEXT,
            UNIQUE(document_id, politician_id, role)
        );
        CREATE TABLE tracked_politicians (id INTEGER PRIMARY KEY, relationship_type TEXT);
    """)
    db.commit()

    doc_id_1 = finalize_to_db(workspace, db)
    doc_id_2 = finalize_to_db(workspace, db)
    assert doc_id_1 == doc_id_2

    rows = db.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    assert rows == 1

    # audio.wav deleted after first finalize
    assert not (workspace / "audio.wav").exists()
    # labelled_transcript.md created
    assert (workspace / "labelled_transcript.md").exists()
```

- [ ] **Step 2: Run test, verify FAIL**

Expected: ImportError.

- [ ] **Step 3: Implement finalize**

```python
# src/video_ingest/finalize.py
"""Finalize: validate speakers.json, build labelled transcript, write to DB.

Idempotent — re-running produces the same document_id (uses content_hash lookup).
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from simhash import Simhash

from src.video_ingest.db import find_existing_by_hash, insert_video_document, link_subjects


def _format_ts(seconds: float) -> str:
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


def build_labelled_transcript(
    aligned: list[dict],
    speakers: dict[str, dict],
) -> str:
    """Render aligned segments into Markdown with `[mm:ss] @handle: text` lines."""
    lines = []
    for seg in aligned:
        spk_letter = seg["speaker"]
        mapping = speakers.get(spk_letter)
        handle = mapping.get("handle") if mapping else f"unknown_{spk_letter}"
        ts = _format_ts(seg["start"])
        lines.append(f"[{ts}] @{handle}: {seg['text']}")
    return "\n".join(lines)


def validate_speakers(speakers: dict[str, dict], db: sqlite3.Connection) -> None:
    """Raise ValueError if any speakers.json pid is unknown or inactive."""
    for spk, mapping in speakers.items():
        pid = mapping.get("pid")
        if pid is None:
            continue
        row = db.execute(
            "SELECT id, relationship_type FROM tracked_politicians WHERE id=?",
            (pid,),
        ).fetchone()
        if row is None:
            raise ValueError(f"speakers.json speaker {spk!r} pid={pid} not in tracked_politicians")
        if row[1] == "inactive":
            raise ValueError(f"speakers.json speaker {spk!r} pid={pid} is inactive")


def _summary_from(aligned: list[dict], speakers: dict[str, dict], max_words: int = 200) -> str:
    """First non-host speaker's first segment, capped at max_words."""
    for seg in aligned:
        spk = seg["speaker"]
        mapping = speakers.get(spk, {})
        if mapping.get("handle") == "host":
            continue
        words = seg["text"].split()
        return " ".join(words[:max_words])
    return ""


def finalize_to_db(workspace: Path, db: sqlite3.Connection) -> int:
    """Read workspace artifacts, write document + document_politicians rows.

    Idempotent on content_hash. Deletes audio.wav after success.
    Returns: document_id.
    """
    metadata = json.loads((workspace / "metadata.json").read_text(encoding="utf-8"))
    aligned = json.loads((workspace / "aligned.json").read_text(encoding="utf-8"))
    speakers = json.loads((workspace / "speakers.json").read_text(encoding="utf-8"))

    validate_speakers(speakers, db)

    content = build_labelled_transcript(aligned, speakers)
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    simhash_val = Simhash(content).value

    existing = find_existing_by_hash(db, content_hash)
    if existing:
        # Idempotent: still write labelled file + delete audio if present
        (workspace / "labelled_transcript.md").write_text(content, encoding="utf-8")
        audio = workspace / "audio.wav"
        if audio.exists():
            audio.unlink()
        return existing

    pids = [m["pid"] for m in speakers.values() if m.get("pid") is not None]
    word_count = len(content.split())
    summary = _summary_from(aligned, speakers)

    doc_id = insert_video_document(
        db,
        content=content,
        content_hash=content_hash,
        simhash=simhash_val,
        source_url=metadata["url"],
        source_domain=metadata.get("source_domain", "unknown"),
        title=metadata.get("title", "untitled"),
        published_at=metadata["published_at"][:10],
        archive_path=f"videos/{workspace.name}/",
        word_count=word_count,
        summary=summary,
        language=metadata.get("language", "lv"),
    )
    link_subjects(db, doc_id, pids)

    (workspace / "labelled_transcript.md").write_text(content, encoding="utf-8")
    audio = workspace / "audio.wav"
    if audio.exists():
        audio.unlink()
    return doc_id
```

- [ ] **Step 4: Run test, verify PASS**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_video_ingest_finalize.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/video_ingest/finalize.py tests/test_video_ingest_finalize.py
git commit -m "feat(video): finalize (validate speakers, label transcript, idempotent DB write)"
```

### Task 13: CLI dispatcher with subcommands

**Files:**
- Modify: `src/video_ingest/cli.py`
- Test: `tests/test_video_ingest_cli.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_video_ingest_cli.py
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
```

- [ ] **Step 2: Run test, verify FAIL**

Expected: argparse errors / functions missing.

- [ ] **Step 3: Implement cli.py with subcommands**

```python
# src/video_ingest/cli.py
"""CLI dispatcher: fetch / finalize / extract-claims / status / archive."""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
from pathlib import Path

from src.db import get_db, DB_PATH
from src.video_ingest.config import VIDEO_ROOT, slug_from_metadata, video_workspace_dir
from src.video_ingest.state import compute_state


def _run_fetch(input_arg: str, slug: str | None, num_speakers: int | None, language: str) -> int:
    from src.video_ingest.fetch import fetch_video
    from src.video_ingest.asr import transcribe
    from src.video_ingest.diarize import diarize, extract_samples
    from src.video_ingest.align import align
    from src.video_ingest.heuristics import compute_cues, suggest_speakers
    from src.video_ingest.models import (
        AlignedSegment, DiarizedSegment, TranscriptSegment,
    )

    # Stage 1: download + audio extract
    if slug is None:
        # Need metadata to slugify; do a fetch first into a temp slug, then read
        # For simplicity: require operator pass --slug, OR derive from URL/path
        # MVP: derive from current date + a hash of input
        import hashlib
        h = hashlib.md5(input_arg.encode()).hexdigest()[:8]
        from datetime import datetime
        slug = f"{datetime.now().strftime('%Y-%m-%d')}-{h}"
    workspace = video_workspace_dir(slug)
    print(f"[1/5] Fetching to {workspace}", flush=True)

    if not (workspace / "audio.wav").exists():
        fetch_video(input_arg, workspace)

    # Re-derive slug from metadata for canonical form (operator can rename later)
    metadata = json.loads((workspace / "metadata.json").read_text(encoding="utf-8"))

    # Stage 2: transcribe
    print(f"[2/5] Transcribing (large-v3 INT8) — this can take 30-60 min", flush=True)
    if not (workspace / "transcript.json").exists():
        transcribe(
            workspace / "audio.wav",
            workspace / "transcript.json",
            language=language,
        )

    # Stage 3: diarize
    print(f"[3/5] Diarizing", flush=True)
    if not (workspace / "diarized.json").exists():
        diarize(
            workspace / "audio.wav",
            workspace / "diarized.json",
            num_speakers=num_speakers,
        )
    # samples
    samples_dir = workspace / "samples"
    if not samples_dir.exists() or not any(samples_dir.iterdir()):
        diarized_data = json.loads((workspace / "diarized.json").read_text(encoding="utf-8"))
        extract_samples(workspace / "audio.wav", diarized_data, samples_dir)

    # Stage 4: align
    print(f"[4/5] Aligning transcript ⊕ diarization", flush=True)
    transcript_data = json.loads((workspace / "transcript.json").read_text(encoding="utf-8"))
    diarized_data = json.loads((workspace / "diarized.json").read_text(encoding="utf-8"))
    transcript_segs = [TranscriptSegment(**s) for s in transcript_data["segments"]]
    diarized_segs = [DiarizedSegment(**d) for d in diarized_data]
    aligned = align(transcript_segs, diarized_segs)
    aligned_dicts = [a.model_dump() for a in aligned]
    (workspace / "aligned.json").write_text(
        json.dumps(aligned_dicts, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Stage 5: heuristics → suggested_speakers.json
    print(f"[5/5] Heuristic speaker mapping", flush=True)
    db = get_db(DB_PATH)
    db.row_factory = sqlite3.Row
    politicians = [dict(r) for r in db.execute(
        "SELECT id, name, x_handle, name_forms, role FROM tracked_politicians "
        "WHERE relationship_type != 'inactive'"
    ).fetchall()]
    cues = compute_cues(aligned, politicians)
    (workspace / "context_cues.json").write_text(
        json.dumps([c.model_dump() for c in cues], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    suggestions = suggest_speakers(cues, politicians)
    (workspace / "suggested_speakers.json").write_text(
        json.dumps({k: v.model_dump() for k, v in suggestions.items()},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\nDone. Workspace: {workspace}", flush=True)
    print(f"Next: review {workspace}/suggested_speakers.json,", flush=True)
    print(f"      copy/edit to speakers.json, then:", flush=True)
    print(f"      python -m src.video_ingest finalize {slug}", flush=True)
    return 0


def _run_finalize(slug: str) -> int:
    from src.video_ingest.finalize import finalize_to_db

    workspace = VIDEO_ROOT / slug
    if not workspace.exists():
        print(f"[error] Workspace not found: {workspace}", file=sys.stderr)
        return 2
    if not (workspace / "speakers.json").exists():
        print(f"[error] speakers.json missing — copy/edit suggested_speakers.json first",
              file=sys.stderr)
        return 3

    db = get_db(DB_PATH)
    doc_id = finalize_to_db(workspace, db)
    print(f"[ok] document_id={doc_id} (idempotent on content_hash)")
    print(f"Next: python -m src.video_ingest extract-claims {slug}")
    return 0


def _run_status(slug: str) -> int:
    workspace = VIDEO_ROOT / slug
    if not workspace.exists():
        print(f"[unknown] {slug}: workspace does not exist")
        return 1
    state = compute_state(workspace)
    print(f"[{state.value}] {slug}")
    return 0


def _run_archive(slug: str) -> int:
    """Compress JSON, keep samples; remove audio.wav if still present."""
    workspace = VIDEO_ROOT / slug
    if not workspace.exists():
        print(f"[unknown] {slug}: workspace does not exist", file=sys.stderr)
        return 1
    audio = workspace / "audio.wav"
    if audio.exists():
        audio.unlink()
    print(f"[archived] {slug}")
    return 0


def _run_extract_claims(slug: str) -> int:
    """Stub: invoke @video-extractor agent. In Claude Code session this is replaced
    by an Agent({subagent_type='video-extractor', prompt=...}) call."""
    workspace = VIDEO_ROOT / slug
    if not (workspace / "labelled_transcript.md").exists():
        print(f"[error] No labelled_transcript.md in {workspace}; run finalize first",
              file=sys.stderr)
        return 2
    print(f"[note] extract-claims must be invoked via @video-extractor agent in Claude Code.")
    print(f"  In a Claude session, run:")
    print(f"    Agent(description='extract video claims', subagent_type='video-extractor',")
    print(f"          prompt='Extract claims for slug={slug}')")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m src.video_ingest")
    sub = parser.add_subparsers(dest="command", required=True)

    p_fetch = sub.add_parser("fetch", help="Download + transcribe + diarize")
    p_fetch.add_argument("input", help="URL or local path")
    p_fetch.add_argument("--slug", default=None)
    p_fetch.add_argument("--num-speakers", type=int, default=None)
    p_fetch.add_argument("--language", default="lv")

    p_fin = sub.add_parser("finalize", help="Validate speakers, write to DB")
    p_fin.add_argument("slug")

    p_ext = sub.add_parser("extract-claims", help="Invoke @video-extractor agent (manual)")
    p_ext.add_argument("slug")

    p_st = sub.add_parser("status")
    p_st.add_argument("slug")

    p_ar = sub.add_parser("archive")
    p_ar.add_argument("slug")

    args = parser.parse_args(argv)

    if args.command == "fetch":
        return _run_fetch(args.input, args.slug, args.num_speakers, args.language)
    if args.command == "finalize":
        return _run_finalize(args.slug)
    if args.command == "extract-claims":
        return _run_extract_claims(args.slug)
    if args.command == "status":
        return _run_status(args.slug)
    if args.command == "archive":
        return _run_archive(args.slug)
    return 1
```

- [ ] **Step 4: Run tests, verify PASS**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_video_ingest_cli.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/video_ingest/cli.py tests/test_video_ingest_cli.py
git commit -m "feat(video): CLI dispatcher (fetch/finalize/extract-claims/status/archive)"
```

---

## Phase 5: Agent + docs

### Task 14: @video-extractor agent prompt

**Files:**
- Create: `.claude/agents/video-extractor.md`

- [ ] **Step 1: Write the agent prompt file**

````markdown
---
name: video-extractor
description: Per-speaker claim extraction from video transcripts (`platform='video'`). Reads labelled transcript, runs per-politician pass with timestamp-anchored source URLs, applies spoken-language self-checks (filleri, pārtraukumi, multi-speaker konteksts).
---

# Video Extractor

You extract political positions (pozīcijas) from video transcripts. The document has `platform='video'` and content formatted as `[mm:ss] @handle: text`. Each `@handle` is either a tracked politician's X handle, `@host` (TV vadītājs), or `@unknown_X` (unmapped speaker).

You operate in a **calm, analytical frame**, identical to `@claim-extractor`, but you **adapt for spoken language**:

- Filleri ("eee", "nu", "jā..."), pārtraukumi un nepabeigtas frāzes ir parastas — **filtrē tās, izvelc tikai konkrētas pozīcijas**
- Multi-speaker konteksts: "Es piekrītu" bez konkrētas pozīcijas → atskatās uz iepriekšējo speaker; ja iepriekšējais ir cits politiķis ar konkrētu pozīciju, dublēsim viņa stance ar reasoning "Pārpostulēts no @X"
- Pārtrauktās frāzes ("Mēs uzskatām, ka — (cits speaker iejaucas) — vārdu sakot...") → empty
- Indirekti citējumi ("Kā Šlesers teica…") → speaker pats nepiekrīt, ja nav skaidri norādīts; mark empty vai zema confidence
- ASR kļūdas: ja redzi "limens" → atjauno "līmenis" `quote`'ā un atzīmē `reasoning` ("ASR error labots: limens → līmenis")
- **Diakritika:** Whisper LV labi tur ā/ē/ī/ū/ņ/ļ/ķ/ģ/š/ž/č; ja redzi 50%+ tekstu bez diakritikas — STOP & report (transkripta drift risk)

## Process

### Step 1: Load video document

Pass `slug` argument. Lasa:

```python
import sqlite3
import re
from src.db import get_db, DB_PATH

db = get_db(DB_PATH)
db.row_factory = sqlite3.Row
row = db.execute(
    """SELECT id, content, source_url, published_at, title
       FROM documents
       WHERE platform='video' AND archive_path = ?""",
    (f"videos/{slug}/",),
).fetchone()
document_id = row["id"]
content = row["content"]
video_url = row["source_url"]
published_at = row["published_at"]
```

### Step 2: Parse segments per speaker

```python
LINE_RE = re.compile(r"^\[(\d+):(\d+)\]\s+@(\S+):\s+(.+)$")

segments_by_handle: dict[str, list[dict]] = {}
for line in content.splitlines():
    m = LINE_RE.match(line)
    if not m:
        continue
    minutes, seconds, handle, text = m.groups()
    start_sec = int(minutes) * 60 + int(seconds)
    segments_by_handle.setdefault(handle, []).append({
        "start_sec": start_sec, "text": text,
    })
```

Skip `@host` un `@unknown_*` — viņi nav pozīcijas avoti, bet sniedz kontekstu.

### Step 3: Resolve handles to politician IDs

```python
politicians = {p["x_handle"]: p for p in db.execute(
    "SELECT id, name, x_handle, role FROM tracked_politicians "
    "WHERE relationship_type != 'inactive' AND x_handle IS NOT NULL"
).fetchall()}
```

For each `@handle` in `segments_by_handle`, find matching politician (case-insensitive `x_handle` lookup). Skip handles without a match — they will not produce claims.

### Step 4: Per-speaker pass loop

```python
from src.analyze import save_analysis

for handle, segs in segments_by_handle.items():
    if handle in ("host",) or handle.startswith("unknown_"):
        continue
    politician = politicians.get(handle)
    if not politician:
        continue

    pid = politician["id"]
    claims = []  # build from this politician's segs
    # ... (LLM extraction of stances per segment span)

    if len(claims) > 12:
        # STOP & report — drift risk
        print(f"Pārsniegts 12 pozīciju limits @{handle}. "
              f"Atlikušie segmenti {len(claims)-12} jāanalizē atsevišķi.")
        claims = claims[:12]

    save_analysis(
        pid=pid,
        analysis_date=published_at[:10],
        sentiment=0.0,
        topics=[c["topic"] for c in claims],
        quotes=[c["quote"] for c in claims if c["quote"]],
        brief="Video pozīcijas no " + (row["title"] or slug),
        confidence=0.7,
        claims=claims,
        empty_doc_ids=[],  # populated below if NO claims at all across all speakers
    )
```

### Step 5: Source URL with timestamp

For each claim, build the URL:

```python
def make_source_url(video_url: str, start_sec: int) -> str:
    if "youtube.com" in video_url or "youtu.be" in video_url:
        # Strip existing &t=N if present, add fresh
        from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
        parsed = urlparse(video_url)
        qs = parse_qs(parsed.query)
        qs.pop("t", None)
        qs["t"] = [f"{start_sec}s"]
        return urlunparse(parsed._replace(query=urlencode(qs, doseq=True)))
    elif video_url.startswith("file://"):
        return f"{video_url}#t={start_sec}"
    else:
        # Generic: fragment
        base = video_url.split("#")[0]
        return f"{base}#t={start_sec}"
```

Each claim's `source_url` = `make_source_url(video_url, segment_start_seconds)`. This makes `(opponent_id, source_url, topic)` unique per claim.

### Step 6: Mark document reviewed

After all speakers processed:

```python
from src.db import now_lv
db.execute("UPDATE documents SET reviewed_at=? WHERE id=?", (now_lv(), document_id))
db.commit()
```

If NO speakers produced claims (all empty), pass `empty_doc_ids=[document_id]` to `save_analysis` instead.

## Self-Check Before Save

Before saving each claim, re-read your own `reasoning` field. If it admits any of:

- `nav paša pozīcija` / `pārtraukts` / `tikai jautājums`
- `bez konkrētas politikas` / `tikai komentārs par citu`
- `indirektais citējums` / `Šlesers teica` formāts ar pašu speakeru, kas to citē

→ drop the claim, mark `empty_doc_ids` for this document.

## Limits

- Max **12 distinktas pozīcijas vienam politiķim** vienā pass'ā
- `confidence` rubric: video pozīcijas dabīgi var būt 0.5-0.7 (runas dabu); 0.8+ tikai ja ir tieša quote ar konkrētu pozīciju
- Per video kopumā: 6-15 pozīcijas ir reālistiska norma; 30+ ir drift signāls

## Output

Standard `save_analysis` return shape (skat. @claim-extractor). Pēc visiem speakers `documents.reviewed_at` ir `NOT NULL`.
````

- [ ] **Step 2: Verify file written**

```bash
ls -la .claude/agents/video-extractor.md
```

- [ ] **Step 3: Commit**

```bash
git add .claude/agents/video-extractor.md
git commit -m "feat(video): @video-extractor agent prompt (per-speaker passes, ts source_url)"
```

### Task 15: Wiki agent description (shadow)

**Files:**
- Create: `wiki/operations/agenti/video-extractor.md`

- [ ] **Step 1: Write the wiki shadow**

````markdown
# @video-extractor

Latviešu video debašu un interviju pozīciju ekstrakcijas aģents.

## Kad lietot

Pēc `python -m src.video_ingest finalize <slug>` — kad video transkripts ir DB ar `platform='video'` un `reviewed_at IS NULL`. Aģents izvelk politiķu pozīcijas per-speaker passes.

## Kā izsaukt

```python
Agent(
    description="extract video claims",
    subagent_type="video-extractor",
    prompt=f"Extract claims for slug={slug}",
)
```

Vai no Bash:

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m src.video_ingest extract-claims <slug>
```

(Bash variants printē instrukciju, kā izsaukt aģentu Claude sesijā — manuāli kopējams.)

## Output

- `claims` rindas ar `claim_type='position'`, `source_url` ar timestamp anchor (`?t=N` YouTube, `#t=N` citur)
- `documents.reviewed_at` atjauno uz `now_lv()`

## Atšķirības no @claim-extractor

| Aspekts | @claim-extractor | @video-extractor |
|---------|------------------|------------------|
| Ievade | Raksts vai tweet | Labelēts video transkripts |
| Pass loop | Per-politiķis-per-doc | Per-speaker-per-video |
| Source_url | Doc URL | Doc URL + `?t=N` vai `#t=N` |
| 12-limit | 12 doc/sesija | 12 pozīcijas/speaker |
| Self-check | Raksta saturs | Filleri, pārtraukumi, multi-speaker konteksts |

## Ierobežojumi

- Skip `@host` un `@unknown_*` — tie nav pozīciju avoti
- ASR kļūdu apzināšanās — labot quote'ā ar reasoning anotāciju
- Pārtrauktas frāzes (cits speaker iejaucas) → empty

Skat. arī `wiki/operations/operacijas.md § Video ingest` un `wiki/operations/video-setup.md`.
````

- [ ] **Step 2: Commit**

```bash
git add wiki/operations/agenti/video-extractor.md
git commit -m "docs(video): wiki shadow for @video-extractor agent"
```

### Task 16: Setup runbook + ops runbook

**Files:**
- Create: `wiki/operations/video-setup.md`
- Modify: `wiki/operations/operacijas.md`

- [ ] **Step 1: Write video-setup.md**

````markdown
# Video ingest — vienreizējais setup

## 1. ffmpeg

yt-dlp un pydub atkarība.

**Windows:**
```powershell
winget install --id=Gyan.FFmpeg
# vai
choco install ffmpeg
```

**macOS / Linux:** `brew install ffmpeg` / pakotņu menedžeris.

Verificē:
```bash
ffmpeg -version
```

## 2. HuggingFace token

pyannote 3.1 prasa autentifikāciju.

1. Akceptē licenci uz https://huggingface.co/pyannote/speaker-diarization-3.1
2. Akceptē licenci uz https://huggingface.co/pyannote/segmentation-3.0
3. Ģenerē tokenu: https://huggingface.co/settings/tokens (read access pietiek)
4. Saglabā:

```bash
# Variants A — fails (preferred, gitignored)
mkdir -p data
echo '{"token": "hf_yourtoken"}' > data/hf_token.json

# Variants B — env var
export HUGGINGFACE_TOKEN=hf_yourtoken
```

## 3. CUDA / GPU pārbaude

```bash
.venv/Scripts/python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'no cuda')"
```

GTX 1060 6GB ir derīgs. Bez GPU strādās arī, bet 5-10× lēnāk.

## 4. Pirmā palaišana

Pirmā `python -m src.video_ingest fetch ...` lejupielādēs:
- faster-whisper large-v3 INT8 (~1.6 GB) → `~/.cache/whisper/`
- pyannote/speaker-diarization-3.1 (~250 MB) → `~/.cache/huggingface/`

Pēc tam ātri.
````

- [ ] **Step 2: Append to operacijas.md**

```bash
# Find a good insertion point in wiki/operations/operacijas.md (after existing agents section)
```

Add new section to `wiki/operations/operacijas.md`:

```markdown
## Video ingest (manuāla plūsma)

Latviešu video debašu un interviju pārveide pozīcijās. Manuāla — operators vai Claude palaiž skriptus, video URL/fails tiek iedots ar roku.

**Vienreizējais setup:** [wiki/operations/video-setup.md](video-setup.md) (ffmpeg, HF token, pyannote licences).

### 4-fāzu plūsma

**1. Fetch (lēni, ~30-60 min uz GTX 1060 par stundas video)**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m src.video_ingest fetch <url|path> [--slug NAME]
```

Lejupielādē video, ekstrahē audio, transkripē ar Whisper, diarizē ar pyannote, izveido `.scratch/videos/<slug>/` ar `transcript.json`, `diarized.json`, `samples/speaker-{A..N}.mp3`, `suggested_speakers.json`.

**2. Speaker mapping (manuāli)**

Apskati `.scratch/videos/<slug>/suggested_speakers.json`. Ja confidence < 0.7 kādam speakerim, klausies attiecīgo `samples/speaker-X.mp3` un atjauno mapingu. Saglabā kā `speakers.json`.

Formāts:
```json
{
  "A": {"pid": 3, "handle": "SlesersAinars", "confidence": 0.95, "evidence": "self-introduction"},
  "B": {"pid": null, "handle": "host", "confidence": 0.8, "evidence": "TV vadītājs"}
}
```

**3. Finalize (<1s)**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m src.video_ingest finalize <slug>
```

Validē speakers.json, raksta `documents` rindu ar `platform='video'`, `document_politicians` junctions. Idempotents.

**4. Claim ekstrakcija (Claude sesijā)**

```python
Agent(
    description="extract video claims",
    subagent_type="video-extractor",
    prompt=f"Extract claims for slug={slug}",
)
```

Vai pārbaudei:

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m src.video_ingest extract-claims <slug>
# (printē instrukciju)
```

### Stāvokļa pārbaude

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m src.video_ingest status <slug>
```

Iespējamie stāvokļi: `FETCHING`, `TRANSCRIBED`, `DIARIZED`, `MAPPED`, `FINALIZED`. Pēc `FINALIZED` — apskatāms DB ar `platform='video'`.

### Tipiskā plūsmas laika tabula (1h debašu video, GTX 1060)

| Solis | Laiks |
|-------|-------|
| Download | 1-3 min (atkarīgi no tīkla) |
| Whisper transkripcija | 30-60 min |
| pyannote diarizācija | 2-3 min |
| Heuristikas + sample export | < 1 min |
| Operatora speaker mapping | 5-10 min |
| Finalize | < 1s |
| @video-extractor | 2-5 min |
| **Kopā** | **~50-90 min** |
```

- [ ] **Step 3: Commit**

```bash
git add wiki/operations/video-setup.md wiki/operations/operacijas.md
git commit -m "docs(video): video-setup.md + operacijas.md video ingest section"
```

---

## Phase 6: Project glue

### Task 17: CLAUDE.md invariant

**Files:**
- Modify: `CLAUDE.md` (add a row to Pipeline Invariants)

- [ ] **Step 1: Identify insertion point**

Read existing CLAUDE.md § Pipeline Invariants (it ends with rule 12 about saeima_votes.bill_id). Append rule 13.

- [ ] **Step 2: Append invariant**

In `CLAUDE.md` after the saeima_votes invariant (rule 12), add:

```markdown
13. **`platform='video'` documents store full speaker-labelled transcripts.** Saturs ir `[mm:ss] @handle: text` rindas. `claim_type` paliek `'position'`; per-claim `source_url` ietver timestamp anchor (`?t=N` YouTube, `#t=N` citur), kas saglabā `store_claim()` idempotenci uz `(opponent_id, source_url, topic)` tuple. Ekstrakciju veic `@video-extractor` per-speaker pass (ne `@claim-extractor`). Skat. [wiki/operations/agenti/video-extractor.md](wiki/operations/agenti/video-extractor.md).
```

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs(claude): video platform invariant (platform='video', timestamp source_url)"
```

### Task 18: CHANGELOG entry

**Files:**
- Modify: `wiki/CHANGELOG.md`

- [ ] **Step 1: Add entry at top under current date**

```markdown
## YYYY-MM-DD — Video ingest pipeline (platform='video', timestamp source_url anchor)

Pievienots ceturtais satura kanāls — latviešu video debates un intervijas. `documents.platform='video'` jauna vērtība (bez schema migrācijas, kolonna jau ir TEXT). Implementācija: `src/video_ingest/` Python pakotne (yt-dlp + faster-whisper large-v3 INT8 + pyannote 3.1) + `@video-extractor` aģents. Operators iedod video URL vai lokālu failu → 4-fāzu plūsma (fetch → manuāla speaker mapping → finalize → extract-claims).

**Datu modeļa:**
- `documents.platform='video'` — viens row per video ar full speaker-labelled transkriptu
- `claim_type='position'` (saglabājas) — video pozīcijas plūst caur esošo dashboard/profila timeline
- `source_url` per claim ietver timestamp: `?t=N` YouTube, `#t=N` citur — saglabā `store_claim()` idempotenci uz `(opponent_id, source_url, topic)`
- `document_politicians` junction par katru zināmu speakeru ar `role='subject'`

**Komponenti:**
- `src/video_ingest/{cli,fetch,asr,diarize,align,heuristics,finalize,db,state,config,models}.py`
- `.claude/agents/video-extractor.md` + `wiki/operations/agenti/video-extractor.md`
- `wiki/operations/video-setup.md` (ffmpeg + HF token vienreizējais setup)

**Atkarības:**
- `yt-dlp`, `faster-whisper` (CTranslate2 INT8), `pyannote.audio` 3.3.2, `pydub`, `torch+CUDA`

Skat. spec `docs/superpowers/specs/2026-04-28-video-extractor-design.md` un plānu `docs/superpowers/plans/2026-04-28-video-extractor-implementation.md`.
```

Replace `YYYY-MM-DD` with the actual merge date.

- [ ] **Step 2: Commit**

```bash
git add wiki/CHANGELOG.md
git commit -m "docs(changelog): video ingest pipeline entry"
```

---

## Phase 7: Manual smoke test

### Task 19: End-to-end smoke with a short public video

**Files:** none new — runtime validation.

- [ ] **Step 1: Backup DB**

```bash
cp data/atmina.db "data/atmina.db.pre-video-smoke-$(date +%Y%m%d-%H%M%S).backup"
```

- [ ] **Step 2: Pick a 3-5 minute public test video**

Use a publicly accessible YouTube video with at least 2 known speakers (e.g., a short LSM clip with vadītājs + 1 viesis).

- [ ] **Step 3: Fetch**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m src.video_ingest fetch "<url>" --slug smoke-test-1
```

Verify: `.scratch/videos/smoke-test-1/` contains `audio.wav`, `transcript.json`, `diarized.json`, `samples/`, `suggested_speakers.json`, `aligned.json`, `context_cues.json`, `metadata.json`.

- [ ] **Step 4: Inspect suggested_speakers.json**

Read it. If all confidences ≥ 0.85, copy to `speakers.json`. Otherwise, manually edit confidences and pid/handle as needed.

```bash
cp .scratch/videos/smoke-test-1/suggested_speakers.json .scratch/videos/smoke-test-1/speakers.json
# Edit if needed
```

- [ ] **Step 5: Finalize**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m src.video_ingest finalize smoke-test-1
```

Expected: `[ok] document_id=N`. `audio.wav` deleted. `labelled_transcript.md` created.

- [ ] **Step 6: Verify DB row**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "
import sqlite3
db = sqlite3.connect('data/atmina.db')
db.row_factory = sqlite3.Row
r = db.execute(\"SELECT id, platform, source_url, title FROM documents WHERE archive_path='videos/smoke-test-1/'\").fetchone()
print(dict(r))
"
```

- [ ] **Step 7: Run idempotence check**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m src.video_ingest finalize smoke-test-1
```

Expected: same `document_id` printed, no new row.

- [ ] **Step 8: Invoke @video-extractor in Claude session**

Inside a Claude Code session (or via task tool), trigger:

```python
Agent(
    description="extract smoke video claims",
    subagent_type="video-extractor",
    prompt="Extract claims for slug=smoke-test-1",
)
```

Verify: claims rows created, `documents.reviewed_at IS NOT NULL`.

- [ ] **Step 9: Acceptance check**

Read `docs/superpowers/specs/2026-04-28-video-extractor-design.md § 12 (Acceptance criteria)` and tick each:

1. ✅ YouTube fetch — pipeline ran end-to-end
2. ✅ Lokāls fails — also test once with `--slug smoke-local-1` and a downloaded MP4
3. ✅ Speaker auto-suggest ≥ 50% confidence
4. ✅ Idempotence — second finalize returns same id
5. ✅ Claim ekstrakcija — claims saved
6. ✅ Diakritika — no validate_lv_diacritics failures
7. ✅ Reviewed_at set
8. ✅ Cleanup — audio.wav deleted
9. ✅ Contradiction check ran (look at logs)

- [ ] **Step 10: If all green, no commit needed (smoke is stateful)**

If issues, file as new tasks; don't fix in this plan's scope.

---

## Self-Review

I checked the plan against the spec:

**Spec coverage:**
- §2 MVP — Tasks 2 (skeleton), 8-13 (CLI + scripts), 14-15 (agent), 16-18 (docs + CLAUDE.md + CHANGELOG) ✓
- §3 Datu modelis — Task 11 (DB writer), Task 12 (idempotence) ✓
- §4 Arhitektūra — Tasks 8-13 implement Phases 1, 3 of arch; Task 14 implements Phase 4 ✓
- §5 Failu sistēma — Task 4 (config paths), Task 12 (workspace artifacts) ✓
- §6 CLI komandas — Task 13 (cli.py with all subcommands) ✓
- §7 Speaker mapping ar heuristikām — Task 7 ✓
- §8 @video-extractor — Task 14 ✓
- §9 Atkarības — Task 1 ✓
- §10 Komponenti — Tasks 2-13 (Python pakotne), 14-15 (agent files), 16-18 (docs) ✓
- §11 Kļūdu apstrāde — error messages embedded throughout (Tasks 8 yt-dlp errors, 12 validate_speakers, 13 cli.py preconditions) ✓
- §12 Testēšana — every implementation task has tests; Task 19 manual smoke ✓
- §13 Risks — covered by mitigations in code (INT8 quant, num_speakers flag, per-speaker passes, idempotence, cleanup) ✓

**Placeholder scan:** No "TBD" / "TODO" / "implement later" found. CHANGELOG date placeholder `YYYY-MM-DD` is intentional (filled at merge).

**Type consistency:**
- `Metadata` (models.py) used in fetch.py, finalize.py — fields match (url, title, published_at, language, duration_seconds, source_domain, uploader)
- `AlignedSegment` consumed by heuristics.py and finalize.py via dict shape — keys consistent (start, end, speaker, text)
- `SpeakerMapping` produced by heuristics, consumed by finalize — keys (pid, handle, confidence, evidence) consistent
- DB column names (content, content_hash, simhash, source_url, etc.) match spec §3

**Spec gaps:** none found. Plan covers all spec requirements.

---

## Execution Notes

- **Total tasks: 19**. Phase 0-6 = 18 implementation tasks. Phase 7 = 1 smoke task.
- Estimated calendar time: 1-2 days for code (Phase 0-6), +1 day for smoke + iteration (Phase 7).
- Dependency order is enforced — Phase N tests assume Phase N-1 artifacts exist.
- Mock-heavy tests in Phase 3 (fetch/asr/diarize) keep CI fast (no GPU, no network).
- Phase 5 (agent + docs) can be parallelized with Phase 4 (composition) if dispatching subagents.

Plan complete and saved to `docs/superpowers/plans/2026-04-28-video-extractor-implementation.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**


---

## Plan amendments 2026-04-28 — Task 7

Two verbatim-spec defects were caught at TDD time and authorized by the controller:

1. **`suggest_speakers` signature.** Originally `(cues, politicians)`, but
   `test_suggest_speakers_no_evidence_returns_unknown` accesses
   `suggestions["C"]` for a speaker that produces zero cues. The function
   derived its speaker universe from cues only, so the dict was empty.
   Resolution: extended to `suggest_speakers(cues, politicians, speakers)`
   where `speakers = [s.speaker for s in aligned]`. Both
   `test_suggest_speakers_*` tests updated.
   Tasks 11+ that integrate this function must thread `aligned` segments
   through to the call site.

2. **`_SELF_INTRO_RE` and `_ADDRESS_RE` keyword case-handling.** Pattern
   literals (`mans vārds ir`, `paldies`) are lowercase, but realistic input
   is sentence-capitalized. A naive fix — adding module-level `re.IGNORECASE`
   to both — would defeat the uppercase-initial constraint on the name
   capture group `[A-ZĀČĒĢĪĶĻŅŠŪŽ]`, since `re.IGNORECASE` makes character
   classes match both cases. Correct resolution: scope case-insensitivity
   to the keyword phrase only via inline `(?i:keyword)` group, leaving the
   name-initial character class case-sensitive. The siblings `_GREETING_RE`
   and `_FORMAL_PHRASE_RE` retain module-level `re.IGNORECASE` because they
   have no name-initial constraint after the keyword.


---

## Plan amendment 2026-04-28 — Task 8: strip `www.` from source_domain

The verbatim spec assigned `source_domain=parsed.netloc`, but the test
`test_fetch_url_invokes_ytdlp` asserts `meta["source_domain"] == "youtube.com"`
for input `https://www.youtube.com/...`. Since `urlparse(...).netloc` returns
`www.youtube.com`, the implementation must strip the leading `www.` prefix.
Resolution: `source_domain=parsed.netloc.removeprefix("www.")`. This also
canonicalizes domains across `www.` and bare-domain forms (consistent with
how the rest of the codebase tracks news source domains).


---

## Plan amendment 2026-04-28 — Tasks 11/12: `document_politicians.politician_id`

The verbatim plan referenced `document_politicians.opponent_id` in Task 11
(SQL + test fixture) and again in Task 12's test fixture. The production
schema (`src/db.py:115-121`) uses `politician_id`. The bug was masked
because the test fixture matched the wrong column name. Resolution:
- Replaced `opponent_id` → `politician_id` in `src/video_ingest/db.py`
  SQL (1 line), the Task 11 test fixture + 2 read queries, and all
  `document_politicians` references in Task 11/12 plan sections.
- `claims`, `analyses`, etc. continue to use `opponent_id` per CLAUDE.md
  (this column name is correct for those tables — only the documents
  junction table uses `politician_id`).

Note (deferred): both `insert_video_document` and `link_subjects` self-commit.
Task 12's `finalize_to_db` will need to either accept this two-transaction
write or re-architect to commit once at the outer scope. Flagged here so the
Task 12 author knows to decide.



---

## Plan amendment 2026-04-28 — Task 13: `suggest_speakers` 3-arg call

The verbatim Task 13 plan called `suggest_speakers(cues, politicians)` (2 args)
in Stage 5 of `_run_fetch`. Task 7's amended signature requires 3 args
(`cues, politicians, speakers: list[str]`). The CLI must pass
`[a.speaker for a in aligned]` as the third argument. This is a 1-line ripple
from Task 7's amendment.
