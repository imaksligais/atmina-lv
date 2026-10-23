"""Video acquisition: yt-dlp for URLs, direct copy for local files. Audio
extraction via ffmpeg (subprocess) into 16 kHz mono WAV."""
from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import yt_dlp


def _run_ytdlp(url: str, out_dir: Path) -> tuple[Path, dict]:
    """Run yt-dlp; return (video_file_path, info_dict). Raises on failure."""
    ydl_opts = {
        "outtmpl": str(out_dir / "video.%(ext)s"),
        "format": "bestaudio/best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        # YouTube SABR streaming forces 403 on default 'web' client (yt-dlp #12482).
        # Android client without PO token still serves combined-format streams.
        "extractor_args": {"youtube": {"player_client": ["android", "ios", "web"]}},
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
    # yt-dlp picks an extension; find it
    candidates = sorted(out_dir.glob("video.*"))
    if not candidates:
        raise RuntimeError("yt-dlp finished but no video file produced")
    return candidates[0], info


def extract_audio(video_path: Path, out_wav: Path) -> Path:
    """ffmpeg -> 16 kHz mono WAV. Raises CalledProcessError on failure."""
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(video_path),
            "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
            str(out_wav),
        ],
        check=True, capture_output=True,
    )
    return out_wav


def write_metadata(
    workspace: Path,
    *, url: str, title: str, published_at: str, language: str,
    duration_seconds: int, source_domain: str, uploader: str | None,
) -> None:
    meta = {
        "url": url,
        "title": title,
        "uploader": uploader,
        "published_at": published_at,
        "language": language,
        "duration_seconds": duration_seconds,
        "source_domain": source_domain,
    }
    (workspace / "metadata.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8",
    )


def _format_yt_date(yyyymmdd: str | None) -> str:
    """yt-dlp returns YYYYMMDD; convert to YYYY-MM-DD."""
    if not yyyymmdd or len(yyyymmdd) != 8:
        return datetime.now().strftime("%Y-%m-%d")
    return f"{yyyymmdd[:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:8]}"


def fetch_video(input_arg: str, workspace: Path) -> Path:
    """Download video (URL) or copy local file; extract 16 kHz mono WAV.

    Returns: Path to audio.wav. Side effect: writes metadata.json.
    """
    workspace.mkdir(parents=True, exist_ok=True)
    out_wav = workspace / "audio.wav"
    parsed = urlparse(input_arg)

    if parsed.scheme in ("http", "https"):
        video, info = _run_ytdlp(input_arg, workspace)
        write_metadata(
            workspace=workspace,
            url=input_arg,
            title=info.get("title", "untitled"),
            published_at=_format_yt_date(info.get("upload_date")),
            language=info.get("language") or "lv",
            duration_seconds=int(info.get("duration") or 0),
            source_domain=parsed.netloc.removeprefix("www."),
            uploader=info.get("uploader"),
        )
    else:
        # Local file
        src = Path(input_arg).resolve()
        if not src.exists():
            raise FileNotFoundError(f"Local video not found: {src}")
        video = workspace / f"video{src.suffix}"
        shutil.copy(src, video)
        write_metadata(
            workspace=workspace,
            url=f"file://{src}",
            title=src.stem,
            published_at=datetime.fromtimestamp(src.stat().st_mtime).strftime("%Y-%m-%d"),
            language="lv",
            duration_seconds=0,  # unknown; ffprobe could fill this later
            source_domain="local",
            uploader=None,
        )

    extract_audio(video, out_wav)
    return out_wav
