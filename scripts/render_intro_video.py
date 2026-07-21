"""Render the atmina.lv 9:16 intro HTML into a publishable MP4."""

from __future__ import annotations

import argparse
import math
import subprocess
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HTML = ROOT / "docs" / "atmina-intro-video.html"
DEFAULT_OUTPUT = ROOT / "output" / "social" / "atmina-intro-video.mp4"


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    index = 2
    while True:
        candidate = parent / f"{stem}-v{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def render_frames(html: Path, frames_dir: Path, fps: int, duration: float) -> int:
    total_frames = math.ceil(fps * duration)
    frames_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        # 405x720 is exactly 9:16; device_scale_factor makes screenshots 1080x1920.
        context = browser.new_context(
            viewport={"width": 405, "height": 720},
            device_scale_factor=1080 / 405,
            reduced_motion="no-preference",
        )
        page = context.new_page()
        page.goto(html.resolve().as_uri(), wait_until="load")
        page.evaluate("document.fonts ? document.fonts.ready : Promise.resolve()")

        animations = page.evaluate("document.getAnimations({ subtree: true }).length")
        if animations == 0:
            raise RuntimeError("No CSS animations found to render.")

        for index in range(total_frames):
            ms = (index / fps) * 1000
            page.evaluate(
                """
                (ms) => {
                  for (const animation of document.getAnimations({ subtree: true })) {
                    animation.pause();
                    animation.currentTime = ms;
                  }
                }
                """,
                ms,
            )
            page.screenshot(
                path=str(frames_dir / f"frame_{index:05d}.jpg"),
                type="jpeg",
                quality=90,
                full_page=False,
            )
            if index % fps == 0:
                print(f"rendered {index // fps:02d}s / {duration:.0f}s")

        context.close()
        browser.close()

    return total_frames


def encode_mp4(frames_dir: Path, output: Path, fps: int) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-y",
        "-framerate",
        str(fps),
        "-i",
        str(frames_dir / "frame_%05d.jpg"),
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "19",
        "-pix_fmt",
        "yuv420p",
        "-color_range",
        "tv",
        "-colorspace",
        "bt709",
        "-color_primaries",
        "bt709",
        "-color_trc",
        "bt709",
        "-movflags",
        "+faststart",
        "-vf",
        "scale=1080:1920:flags=lanczos:in_range=pc:out_range=tv,format=yuv420p",
        str(output),
    ]
    subprocess.run(command, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--html", type=Path, default=DEFAULT_HTML)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--duration", type=float, default=28.0)
    args = parser.parse_args()

    html = args.html.resolve()
    if not html.exists():
        raise FileNotFoundError(html)

    output = unique_path(args.out.resolve())
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    frames_dir = ROOT / "tmp" / f"atmina_intro_frames_{stamp}"

    frame_count = render_frames(html, frames_dir, args.fps, args.duration)
    encode_mp4(frames_dir, output, args.fps)

    print(f"frames: {frame_count}")
    print(f"frames_dir: {frames_dir}")
    print(f"output: {output}")


if __name__ == "__main__":
    main()
