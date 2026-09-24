"""Generate responsive web variants from a source brief PNG.

Source images in ``output/images/briefs/<slug>-<hash>.png`` are 1376x768 PNGs
(~700 KB each). For web delivery we emit four variants alongside each PNG:

- ``<stem>-hero.webp``  1280x720 q85 — full-bleed hero on blog-post.html
- ``<stem>-card.webp``  640x360  q85 — homepage 3-column featured grid
- ``<stem>-thumb.webp`` 320x180  q85 — analizes.html daily-card thumbs
- ``<stem>-og.jpg``     1200x630 q82 — og:image for social share previews

The DB row in ``brief_images.image_path`` continues to point at the source PNG;
templates derive variant filenames via :func:`variant_filename` (pure string op).
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from PIL import Image

VariantName = Literal["hero", "card", "thumb", "og"]

VARIANTS: dict[VariantName, dict] = {
    "hero":  {"size": (1280, 720), "fmt": "webp", "quality": 85, "crop": False},
    "card":  {"size": (640, 360),  "fmt": "webp", "quality": 85, "crop": False},
    "thumb": {"size": (320, 180),  "fmt": "webp", "quality": 85, "crop": False},
    "og":    {"size": (1200, 630), "fmt": "jpeg", "quality": 82, "crop": True},
}

_EXT = {"webp": "webp", "jpeg": "jpg"}


def variant_filename(png_filename: str, variant: VariantName) -> str:
    """Derive a variant filename from a source PNG filename (pure string op).

    >>> variant_filename("2026-04-20-dienas-parskats-abc12345.png", "hero")
    '2026-04-20-dienas-parskats-abc12345-hero.webp'
    """
    spec = VARIANTS[variant]
    ext = _EXT[spec["fmt"]]
    stem = png_filename.rsplit(".", 1)[0]
    return f"{stem}-{variant}.{ext}"


def variant_path(png_path: Path, variant: VariantName) -> Path:
    return png_path.with_name(variant_filename(png_path.name, variant))


def _cover_crop(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Scale to cover the target ratio, then center-crop to exact dimensions."""
    src_ratio = img.width / img.height
    tgt_ratio = target_w / target_h
    if src_ratio > tgt_ratio:
        new_h = target_h
        new_w = round(img.width * (target_h / img.height))
    else:
        new_w = target_w
        new_h = round(img.height * (target_w / img.width))
    resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return resized.crop((left, top, left + target_w, top + target_h))


def make_variants(
    png_path: Path | str, *, force: bool = False
) -> dict[VariantName, Path]:
    """Emit all four variants for *png_path* in the same directory.

    Existing variants are skipped unless ``force=True``. Returns a mapping
    ``{variant_name: output_path}`` for every variant (existing or newly
    written).
    """
    png_path = Path(png_path)
    if not png_path.exists():
        raise FileNotFoundError(png_path)

    src = Image.open(png_path).convert("RGB")
    out: dict[VariantName, Path] = {}
    for name, spec in VARIANTS.items():
        dest = variant_path(png_path, name)  # type: ignore[arg-type]
        if dest.exists() and not force:
            out[name] = dest  # type: ignore[index]
            continue
        w, h = spec["size"]
        if spec["crop"]:
            img = _cover_crop(src, w, h)
        else:
            img = src.copy()
            img.thumbnail((w, h), Image.Resampling.LANCZOS)
        if spec["fmt"] == "webp":
            img.save(dest, "WEBP", quality=spec["quality"], method=6)
        else:
            # Baseline JPEG (progressive=False) — Twitter Cards historically
            # silently fail to render progressive JPEGs as og:image. The wider
            # web supports both, but the og.jpg variant exists specifically for
            # social-card previews where baseline is the safer default.
            img.save(
                dest, "JPEG",
                quality=spec["quality"], optimize=True, progressive=False,
            )
        out[name] = dest  # type: ignore[index]
    return out
