"""Lightweight @atmina_lv thread/tweet image generation.

Tweet-thread illustrations are sepia, text-free, metaphor-only (distinct from
the brief poster, which renders a headline). Unlike the brief pipeline these
images are NOT tied to a context_note, so there is no brief_images audit row
or budget gate here — just compose prompt + generate + write PNG.

The creative part (per-tweet base prompts) is authored by @graphics-designer
and passed in as a dict; this module only applies the canonical SEPIA_STYLE
and writes files. ``generate_fn`` is injectable so tests never hit the API.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from src.graphics.nanobanana import generate_image
from src.graphics.prompt import SEPIA_STYLE


def thread_filename(date: str, suffix: str) -> str:
    """Canonical thread image filename: ``{date}-thread-{suffix}.png``."""
    return f"{date}-thread-{suffix}.png"


def compose_thread_prompt(base_prompt: str) -> str:
    """Append the canonical SEPIA_STYLE to a base metaphor prompt."""
    return f"{base_prompt.rstrip()} {SEPIA_STYLE}"


def generate_thread(
    date: str,
    prompts: dict[str, str],
    out_dir: str,
    generate_fn: Callable[..., bytes] = generate_image,
    aspect_ratio: str = "16:9",
) -> list[Path]:
    """Generate one sepia 16:9 image per ``{suffix: base_prompt}`` entry.

    Writes ``{out_dir}/{date}-thread-{suffix}.png`` for each. Returns the list
    of written paths (insertion order). No DB writes, no budget gate.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for suffix, base_prompt in prompts.items():
        png = generate_fn(compose_thread_prompt(base_prompt), aspect_ratio=aspect_ratio)
        path = out / thread_filename(date, suffix)
        path.write_bytes(png)
        written.append(path)
    return written
