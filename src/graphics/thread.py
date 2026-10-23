"""Lightweight @atmina_lv thread/tweet image generation.

Tweet-thread illustrations are text-free, metaphor-only (distinct from the brief
poster, which renders a headline). They are NOT tied to a context_note, so there
is no ``brief_images`` row and no budget gate here — just compose prompt +
generate + write PNG. Izmaksu uzskaite tomēr NOTIEK: kopš 2026-09-07 (verdikts
47b) ``generate_image()`` pati raksta ``image_audit`` rindu ar ``kind='thread'``.

Stils: ``sepia`` (noklusējums) vai ``light`` — abi no ``prompt.THREAD_STYLES``.
Līdz 2026-09-07 sepia tika pievienots bez nosacījuma, tāpēc gaišais variants CLI
nebija sasniedzams.

The creative part (per-tweet base prompts) is authored by @graphics-designer
and passed in as a dict; this module only applies the canonical style and writes
files. ``generate_fn`` is injectable so tests never hit the API.
"""

from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Callable

from src.graphics.nanobanana import generate_image
from src.graphics.prompt import THREAD_STYLES

DEFAULT_THREAD_STYLE = "sepia"

_generate_thread_image = partial(generate_image, kind="thread")


def thread_filename(date: str, suffix: str) -> str:
    """Canonical thread image filename: ``{date}-thread-{suffix}.png``."""
    return f"{date}-thread-{suffix}.png"


def compose_thread_prompt(base_prompt: str, style: str = DEFAULT_THREAD_STYLE) -> str:
    """Append the named thread style to a base metaphor prompt.

    Raises ``KeyError`` for an unknown style — klusa atkāpšanās uz sepia būtu
    tieši tā klusā veiksme, kas šo ierakstu radīja.
    """
    return f"{base_prompt.rstrip()} {THREAD_STYLES[style]}"


def generate_thread(
    date: str,
    prompts: dict[str, str],
    out_dir: str,
    generate_fn: Callable[..., bytes] = _generate_thread_image,
    aspect_ratio: str = "16:9",
    style: str = DEFAULT_THREAD_STYLE,
) -> list[Path]:
    """Generate one text-free 16:9 image per ``{suffix: base_prompt}`` entry.

    Writes ``{out_dir}/{date}-thread-{suffix}.png`` for each. Returns the list
    of written paths (insertion order). No ``brief_images`` row and no budget
    gate; ``image_audit`` rinda rodas pašā ``generate_image()``.
    """
    if style not in THREAD_STYLES:
        raise KeyError(
            f"Nezināms pavediena stils {style!r}; pieejamie: "
            f"{', '.join(sorted(THREAD_STYLES))}"
        )
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for suffix, base_prompt in prompts.items():
        png = generate_fn(
            compose_thread_prompt(base_prompt, style), aspect_ratio=aspect_ratio
        )
        path = out / thread_filename(date, suffix)
        path.write_bytes(png)
        written.append(path)
    return written
