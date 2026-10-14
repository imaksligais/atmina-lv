import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.video_ingest.fetch import fetch_video, write_metadata


def test_fetch_local_file_copies_audio(tmp_path, monkeypatch):
    """When input is a local file, copy + extract audio without yt-dlp."""
    src_video = tmp_path / "input.mp4"
    src_video.write_bytes(b"fake video bytes")

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    extracted = []
    def fake_extract_audio(video_path, out_wav):
        extracted.append((video_path, out_wav))
        out_wav.write_bytes(b"fake wav")
        return out_wav

    monkeypatch.setattr("src.video_ingest.fetch.extract_audio", fake_extract_audio)

    audio_path = fetch_video(str(src_video), workspace)
    assert audio_path == workspace / "audio.wav"
    assert audio_path.exists()
    assert len(extracted) == 1


def test_fetch_url_invokes_ytdlp(tmp_path, monkeypatch):
    """When input is URL, yt-dlp downloads to workspace, then audio extracted."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    download_calls = []

    def fake_run_ytdlp(url, out_dir):
        download_calls.append((url, out_dir))
        video = out_dir / "video.mp4"
        video.write_bytes(b"fake")
        meta = {
            "url": url,
            "title": "Test debate",
            "uploader": "TestChan",
            "upload_date": "20260415",
            "language": "lv",
            "duration": 300,
            "extractor": "youtube",
        }
        return video, meta

    extracted = []
    def fake_extract_audio(video_path, out_wav):
        extracted.append((video_path, out_wav))
        out_wav.write_bytes(b"fake wav")
        return out_wav

    monkeypatch.setattr("src.video_ingest.fetch._run_ytdlp", fake_run_ytdlp)
    monkeypatch.setattr("src.video_ingest.fetch.extract_audio", fake_extract_audio)

    audio_path = fetch_video("https://www.youtube.com/watch?v=test", workspace)
    assert audio_path.exists()
    assert len(download_calls) == 1
    assert (workspace / "metadata.json").exists()
    meta = json.loads((workspace / "metadata.json").read_text(encoding="utf-8"))
    assert meta["title"] == "Test debate"
    assert meta["source_domain"] == "youtube.com"


def test_fetch_url_invalid_raises(tmp_path, monkeypatch):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    def fake_run_ytdlp(url, out_dir):
        raise RuntimeError("yt-dlp: video unavailable")

    monkeypatch.setattr("src.video_ingest.fetch._run_ytdlp", fake_run_ytdlp)
    with pytest.raises(RuntimeError):
        fetch_video("https://blocked.example/x", workspace)


def test_write_metadata_local_file(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    src = tmp_path / "knl.mp4"
    src.write_bytes(b"")

    write_metadata(
        workspace=workspace,
        url=f"file://{src}",
        title="knl.mp4",
        published_at="2026-04-15",
        language="lv",
        duration_seconds=0,
        source_domain="local",
        uploader=None,
    )
    meta = json.loads((workspace / "metadata.json").read_text(encoding="utf-8"))
    assert meta["url"].endswith("knl.mp4")
