import json
import wave
from pathlib import Path
from unittest.mock import MagicMock

from src.video_ingest.diarize import diarize, extract_samples


def _write_silent_wav(path: Path, seconds: float = 1.0, rate: int = 16000) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * int(rate * seconds))


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
    _write_silent_wav(audio)

    fake_pipeline = MagicMock(return_value=_mock_pyannote_diarization())
    monkeypatch.setattr("src.video_ingest.diarize._load_pipeline", lambda: fake_pipeline)

    out = tmp_path / "diarized.json"
    diarize(audio, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    # Speakers re-labelled SPEAKER_00 -> A, SPEAKER_01 -> B
    speakers = sorted({d["speaker"] for d in data})
    assert speakers == ["A", "B"]
    assert len(data) == 3

    # Pipeline must receive a decoded waveform dict, not a file path
    # (torchcodec-free path — see diarize.py comment).
    (call_arg,), _ = fake_pipeline.call_args
    assert isinstance(call_arg, dict)
    assert set(call_arg) == {"waveform", "sample_rate"}
    assert call_arg["sample_rate"] == 16000


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
