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
