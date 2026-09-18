"""pyannote.audio speaker diarization + per-speaker sample extraction."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable

import soundfile
import torch
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
            token=load_hf_token(),
        )
        # VIDEO_INGEST_DEVICE (kopīgs ar asr.py) uzvar; bez tā — auto-GPU.
        # Atšķirībā no ASR (ctranslate2 var nokrist ar exit 127 uz nesaderīga
        # cuDNN), pyannote iet caur torch, tāpēc auto-detekcija šeit ir droša.
        device = os.environ.get("VIDEO_INGEST_DEVICE", "").strip()
        if not device:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        if device != "cpu":
            _PIPELINE_CACHE.to(torch.device(device))
    return _PIPELINE_CACHE


def _relabel_to_letters(raw: list[tuple[float, float, str]]) -> list[dict]:
    """Map pyannote SPEAKER_00, SPEAKER_01 -> A, B in order of first appearance."""
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
    # Pass a decoded waveform instead of the path: pyannote 4.x decodes files via
    # torchcodec, which needs FFmpeg *shared* DLLs that the winget static build
    # lacks. audio.wav is plain PCM, so soundfile reads it without any codec.
    data, sample_rate = soundfile.read(str(audio_wav), dtype="float32", always_2d=True)
    waveform = torch.from_numpy(data.T)
    diar = pipeline({"waveform": waveform, "sample_rate": sample_rate}, **kwargs)
    # pyannote 4.x returns a structured output; 3.x returned the Annotation itself.
    annotation = diar if hasattr(diar, "itertracks") else diar.speaker_diarization

    raw_segments: list[tuple[float, float, str]] = []
    for turn, _, speaker in annotation.itertracks(yield_label=True):
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
