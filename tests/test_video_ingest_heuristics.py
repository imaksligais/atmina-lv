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
    suggestions = suggest_speakers(cues, _make_politicians(), [s.speaker for s in aligned])
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
    suggestions = suggest_speakers(cues, _make_politicians(), [s.speaker for s in aligned])
    assert suggestions["C"].pid is None
    assert suggestions["C"].confidence == 0.0
    assert suggestions["C"].handle.startswith("unknown_")
