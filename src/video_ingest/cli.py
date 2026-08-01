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
    import os
    model_label = os.environ.get("VIDEO_INGEST_MODEL", "").strip() or "AiLab LV fine-tune ct2-int8"
    print(f"[2/5] Transcribing ({model_label}) — this can take 30-60 min", flush=True)
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
    suggestions = suggest_speakers(cues, politicians, [a.speaker for a in aligned])  # AMENDED: 3rd arg per Task 7 signature
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
