"""Sintēžu/analīžu kartītes lieto responsīvos webp variantus, nevis raw PNG.

Divi neatkarīgi vārti, abi hermētiski (bez data/atmina.db, bez reāliem
attēliem ārpus tmp_path):

1. Kartīšu tīkls (index.html.j2 / analizes.html.j2) izvada ``-card.webp``, nevis
   ~600 KB raw ``.png`` — pārbaudīts caur mazu Jinja render ar to pašu
   ``image_variant`` filtru, ko reģistrē _orchestrator.py.

2. ``_ensure_image_variants`` ir self-healing: katram avota PNG blakus ģenerē
   -hero/-og/-card/-thumb variantus; trūkstošs katalogs = no-op; atkārtots
   izsaukums (mtime-kešs) izlaiž svaigos.
"""
from __future__ import annotations

import os
from pathlib import Path

from jinja2 import Environment
from PIL import Image

from src.image_variants import variant_filename
from src.render._orchestrator import _ensure_image_variants


def _env() -> Environment:
    env = Environment(autoescape=True)
    env.filters["image_variant"] = variant_filename
    return env


def test_synthesis_card_renders_card_webp_not_raw_png() -> None:
    tmpl = _env().from_string(
        '<img src="images/synthesis/'
        "{{ s.image_filename|image_variant('card') }}\">"
    )
    out = tmpl.render(s={"image_filename": "imigracijas-konsenss-2026-06.png"})
    assert "imigracijas-konsenss-2026-06-card.webp" in out
    # Raw PNG basename must NOT survive into the card grid.
    assert "imigracijas-konsenss-2026-06.png" not in out


def test_analizes_thumb_renders_thumb_webp() -> None:
    tmpl = _env().from_string(
        "{{ s.image_filename|image_variant('thumb') }}"
    )
    out = tmpl.render(s={"image_filename": "vad-2026.png"})
    assert out == "vad-2026-thumb.webp"
    assert not out.endswith(".png")


def _make_source_png(path: Path) -> Path:
    # Noise so the PNG doesn't compress to nothing; small enough to stay fast.
    raw = os.urandom(200 * 120 * 3)
    Image.frombytes("RGB", (200, 120), raw).save(path, "PNG")
    return path


def test_ensure_image_variants_self_heals(tmp_path: Path) -> None:
    src = tmp_path / "synthesis"
    src.mkdir()
    _make_source_png(src / "airbaltic-30-miljoni.png")

    generated = _ensure_image_variants(src)
    assert generated == 1
    for variant in ("hero", "card", "thumb", "og"):
        expected = src / variant_filename("airbaltic-30-miljoni.png", variant)
        assert expected.exists(), f"missing {variant} variant: {expected}"


def test_ensure_image_variants_missing_dir_is_noop(tmp_path: Path) -> None:
    assert _ensure_image_variants(tmp_path / "does-not-exist") == 0


def test_ensure_image_variants_skips_variant_files(tmp_path: Path) -> None:
    """Already-generated variant stems (-hero/-og/-card/-thumb) are not re-swept
    as sources, and the mtime cache leaves fresh variants untouched."""
    src = tmp_path / "synthesis"
    src.mkdir()
    _make_source_png(src / "deklaracijas-2026.png")

    first = _ensure_image_variants(src)
    assert first == 1
    card = src / variant_filename("deklaracijas-2026.png", "card")
    mtime = card.stat().st_mtime_ns

    # Re-run: still only ONE source counted (the -hero/-og/... webp/jpg files
    # are excluded), and make_variants' mtime cache skips the fresh variant.
    second = _ensure_image_variants(src)
    assert second == 1
    assert card.stat().st_mtime_ns == mtime
