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
