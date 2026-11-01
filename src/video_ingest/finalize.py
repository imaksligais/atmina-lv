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
