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
