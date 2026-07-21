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
WHISPER_HF_REPO = "AiLab-IMCS-UL/whisper-large-v3-lv-late-cv19"  # LV fine-tune (Apache 2.0)
WHISPER_CT2_SUBFOLDER = "ct2-int8"  # int8 quantized CT2 variant in repo
WHISPER_MODEL = "large-v3"  # vanilla fallback name; opt-out via VIDEO_INGEST_MODEL env
WHISPER_COMPUTE_TYPE = "int8_float32"  # Pascal+ (no Tensor Cores needed); ~1GB VRAM on large-v3
WHISPER_LANGUAGE = "lv"
WHISPER_CPU_THREADS = 4  # leave cores for other work; CPU large-v3 is ~2.3× real-time
PYANNOTE_MODEL = "pyannote/speaker-diarization-community-1"  # pyannote 4.x; 3.1 vārds tāpat novirza šurp
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
