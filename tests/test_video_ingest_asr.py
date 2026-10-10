import json
from pathlib import Path
from unittest.mock import MagicMock

from src.video_ingest.asr import transcribe


def _mock_segment(start, end, text, words=None):
    s = MagicMock()
    s.start = start
    s.end = end
    s.text = text
    s.words = words or []
    return s


def test_transcribe_writes_json(tmp_path, monkeypatch):
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"fake")

    fake_segments = [
        _mock_segment(0.0, 2.0, "Sveicināti, šovakar studijā..."),
        _mock_segment(2.0, 5.0, "Mūsu viesi šovakar ir..."),
    ]
    fake_info = MagicMock(language="lv", language_probability=0.99, duration=300.0)

    fake_model = MagicMock()
    fake_model.transcribe.return_value = (iter(fake_segments), fake_info)

    monkeypatch.setattr(
        "src.video_ingest.asr._load_model",
        lambda: fake_model,
    )

    out_path = transcribe(audio, tmp_path / "transcript.json", language="lv")
    assert out_path.exists()
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert data["language"] == "lv"
    assert len(data["segments"]) == 2
    assert data["segments"][0]["text"] == "Sveicināti, šovakar studijā..."


def test_transcribe_preserves_diacritics(tmp_path, monkeypatch):
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"fake")

    fake_segments = [_mock_segment(0.0, 1.5, "Pārējie politiķi nezin.")]
    fake_info = MagicMock(language="lv", language_probability=0.99, duration=2.0)
    fake_model = MagicMock()
    fake_model.transcribe.return_value = (iter(fake_segments), fake_info)

    monkeypatch.setattr("src.video_ingest.asr._load_model", lambda: fake_model)

    out_path = transcribe(audio, tmp_path / "transcript.json", language="lv")
    text = out_path.read_text(encoding="utf-8")
    assert "Pārējie" in text
    assert "politiķi" in text
