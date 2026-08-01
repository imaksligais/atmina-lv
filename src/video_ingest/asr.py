"""faster-whisper transcription wrapper.

Default: AiLab IMCS-UL/whisper-large-v3-lv-late-cv19 (LV fine-tune, Apache 2.0)
in CT2 int8 quantization. ~5-7pp better WER on LV galotnes/political terms than
vanilla Whisper. Operator opt-out: `VIDEO_INGEST_MODEL=large-v3` (or any
faster-whisper-supported name) reverts to multilingual model.

VAD filter on by default to skip silent regions (prevents 'Paldies par
skatīšanos' hallucination).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from faster_whisper import WhisperModel

from src.video_ingest.config import (
    WHISPER_COMPUTE_TYPE, WHISPER_CPU_THREADS, WHISPER_CT2_SUBFOLDER,
    WHISPER_HF_REPO, WHISPER_LANGUAGE,
)

_MODEL_CACHE: WhisperModel | None = None


def _resolve_model_path() -> str:
    """Return WhisperModel arg: env override (faster-whisper name) or
    local path to AiLab CT2 int8 subfolder."""
    import os
    env_override = os.environ.get("VIDEO_INGEST_MODEL", "").strip()
    if env_override:
        return env_override
    from huggingface_hub import snapshot_download
    local_dir = snapshot_download(
        repo_id=WHISPER_HF_REPO,
        allow_patterns=[
            f"{WHISPER_CT2_SUBFOLDER}/*",
            "tokenizer.json", "tokenizer_config.json",
            "preprocessor_config.json", "special_tokens_map.json",
            "added_tokens.json", "vocab.json", "merges.txt", "normalizer.json",
        ],
    )
    return str(Path(local_dir) / WHISPER_CT2_SUBFOLDER)


def _load_model() -> WhisperModel:
    global _MODEL_CACHE
    if _MODEL_CACHE is None:
        # Default CPU — the safe path. GPU: VIDEO_INGEST_DEVICE=cuda.
        # ctranslate2 4.8.x is a CUDA 12 + cuDNN 9 build, so a modern GPU box
        # with a current driver works; the historical cuDNN 8/9 clash applied
        # to ct2 4.4 + torch cu118 (the 2026-05 stack). No auto-detection here
        # on purpose: a missing/mismatched cuDNN aborts the process with
        # exit 127 (not Python-catchable), so GPU stays an explicit opt-in.
        import os
        device = os.environ.get("VIDEO_INGEST_DEVICE", "cpu")
        compute_type = WHISPER_COMPUTE_TYPE if device == "cuda" else "int8"
        _MODEL_CACHE = WhisperModel(
            _resolve_model_path(),
            device=device,
            compute_type=compute_type,
            cpu_threads=WHISPER_CPU_THREADS,
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
