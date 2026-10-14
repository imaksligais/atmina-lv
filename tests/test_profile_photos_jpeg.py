"""Profile photos must be real JPEG bytes, not just a `.jpg` name.

Failure named: X served Latvijas Banka's avatar as PNG; fetch_profile_photos
wrote it verbatim to `latvijas-banka.jpg` (2026-10-05). The og-card data URI
hardcodes `data:image/jpeg`, so a PNG-in-.jpg renders as a broken image.
"""
from io import BytesIO
from pathlib import Path

from PIL import Image

from scripts.fetch_profile_photos import _to_jpeg_bytes

JPEG_MAGIC = b"\xff\xd8\xff"
PHOTO_DIR = Path(__file__).resolve().parent.parent / "assets" / "photos"


def _png_bytes(mode: str) -> bytes:
    buf = BytesIO()
    Image.new(mode, (8, 8), (10, 20, 30, 0) if mode == "RGBA" else (10, 20, 30)).save(buf, "PNG")
    return buf.getvalue()


def test_png_avatar_is_reencoded_as_jpeg():
    out = _to_jpeg_bytes(_png_bytes("RGBA"))
    assert out[:3] == JPEG_MAGIC
    im = Image.open(BytesIO(out))
    assert im.format == "JPEG" and im.mode == "RGB"
    # fully transparent pixels are flattened onto white, not black
    assert min(im.getpixel((4, 4))) > 240


def test_every_committed_photo_is_real_jpeg():
    photos = sorted(PHOTO_DIR.glob("*.jpg"))
    assert len(photos) > 100, f"denominator too small: {len(photos)} photos"
    bad = [p.name for p in photos if p.read_bytes()[:3] != JPEG_MAGIC]
    assert not bad, f"not JPEG despite .jpg name: {bad}"
