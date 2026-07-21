"""Tests for src.image_variants — responsive web variants for brief PNGs."""
from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from src.image_variants import (
    VARIANTS,
    make_variants,
    variant_filename,
    variant_path,
)


@pytest.fixture
def source_png(tmp_path: Path) -> Path:
    """Write a 1376x768 RGB PNG with per-pixel noise to *tmp_path*.

    Matches the dimensions of real brief images. Per-pixel noise is required
    because a flat-color PNG compresses to ~4 KB, too small for the "variant
    must be smaller than source" assertion to be meaningful — real brief PNGs
    from the Gemini pipeline are ~700 KB.
    """
    import os
    path = tmp_path / "2026-01-01-dienas-parskats-deadbeef.png"
    # os.urandom gives ~8 bpp entropy — PNG deflate can't compress this, so
    # the resulting file size is close to raw 1376×768×3 bytes ≈ 3 MB.
    raw = os.urandom(1376 * 768 * 3)
    img = Image.frombytes("RGB", (1376, 768), raw)
    img.save(path, "PNG")
    return path


def test_variant_filename_is_pure_string() -> None:
    assert (
        variant_filename("foo-abc12345.png", "hero")
        == "foo-abc12345-hero.webp"
    )
    assert (
        variant_filename("foo-abc12345.png", "og")
        == "foo-abc12345-og.jpg"
    )


def test_variant_filename_handles_all_four_names() -> None:
    name = "2026-04-20-dienas-parskats-ff5c1626.png"
    out = {v: variant_filename(name, v) for v in VARIANTS}
    assert out["hero"].endswith("-hero.webp")
    assert out["card"].endswith("-card.webp")
    assert out["thumb"].endswith("-thumb.webp")
    assert out["og"].endswith("-og.jpg")


def test_make_variants_emits_four_files_with_correct_dimensions(
    source_png: Path,
) -> None:
    out = make_variants(source_png)
    assert set(out.keys()) == {"hero", "card", "thumb", "og"}

    sizes = {name: Image.open(p).size for name, p in out.items()}
    # hero/card/thumb use thumbnail() which preserves aspect ratio, so width
    # matches the target exactly and height is derived from source ratio.
    assert sizes["hero"][0] == 1280
    assert sizes["card"][0] == 640
    assert sizes["thumb"][0] == 320
    # og uses cover_crop → exact target dimensions.
    assert sizes["og"] == (1200, 630)


def test_make_variants_each_variant_is_smaller_than_source(
    source_png: Path,
) -> None:
    src_kb = source_png.stat().st_size / 1024
    out = make_variants(source_png)
    for name, path in out.items():
        variant_kb = path.stat().st_size / 1024
        assert variant_kb < src_kb, (
            f"{name} variant ({variant_kb:.0f} KB) "
            f"is not smaller than source ({src_kb:.0f} KB)"
        )


def test_make_variants_is_idempotent(source_png: Path) -> None:
    first = make_variants(source_png)
    mtimes = {name: p.stat().st_mtime_ns for name, p in first.items()}
    # Second call with force=False should skip and leave mtimes untouched.
    second = make_variants(source_png)
    for name, path in second.items():
        assert path.stat().st_mtime_ns == mtimes[name]


def test_make_variants_force_rewrites(source_png: Path) -> None:
    first = make_variants(source_png)
    first_mtimes = {name: p.stat().st_mtime_ns for name, p in first.items()}
    # Sleep to ensure mtime resolution distinguishes the two writes on
    # Windows (NTFS has ~100ns resolution, but some filesystems round to ms).
    import time
    time.sleep(0.05)
    second = make_variants(source_png, force=True)
    for name, path in second.items():
        assert path.stat().st_mtime_ns >= first_mtimes[name]


def test_variant_path_lives_next_to_source(source_png: Path) -> None:
    for name in VARIANTS:
        p = variant_path(source_png, name)
        assert p.parent == source_png.parent
        assert p.name.startswith(source_png.stem)


def test_make_variants_raises_on_missing_source(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        make_variants(tmp_path / "nope.png")


def test_og_jpeg_is_baseline_not_progressive(source_png: Path) -> None:
    """The og.jpg variant MUST be baseline (sequential), not progressive.

    Twitter Cards historically render progressive JPEGs as blank previews —
    no error, no fallback, just no card. The 2026-05-01 daily brief surfaced
    this: meta tags valid, image fetchable, dimensions correct, but `file`
    reported ``progressive`` and x.com refused to render the card. After
    re-encoding to baseline + redeploy, the card rendered.

    This test pins the encoding so a future contributor flipping
    ``progressive=True`` back in ``image_variants.py`` (e.g. for "smaller
    file size" or "smoother loading") gets caught at CI time, not from
    a dropped social-media preview a few days later.
    """
    out = make_variants(source_png)
    og_path = out["og"]
    with Image.open(og_path) as img:
        # PIL's ``progressive`` flag lives in info dict; set means progressive.
        # We assert ABSENCE: a baseline JPEG has no ``progressive`` key (or
        # the key is falsy) in info.
        assert not img.info.get("progressive"), (
            f"og.jpg at {og_path} is progressive — Twitter Cards silently "
            "fail on these. Keep progressive=False in image_variants.py."
        )
        assert not img.info.get("progression"), (
            "og.jpg has 'progression' marker — variant of progressive flag."
        )
