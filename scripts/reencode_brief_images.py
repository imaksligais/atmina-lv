"""Backfill responsive web variants for every brief PNG.

Iterates ``output/images/briefs/*.png`` and emits hero/card/thumb/og variants
alongside each source file via :func:`src.image_variants.make_variants`.
Already-existing variants are skipped unless ``--force`` is given.

Usage::

    .venv/Scripts/python scripts/reencode_brief_images.py          # incremental
    .venv/Scripts/python scripts/reencode_brief_images.py --force  # rebuild all
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.image_variants import VARIANTS, make_variants, variant_path  # noqa: E402


def _kb(path: Path) -> float:
    return path.stat().st_size / 1024


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force", action="store_true",
        help="Regenerate variants even if they already exist",
    )
    parser.add_argument(
        "--dir", default="output/images/briefs",
        help="Directory containing source PNGs (default: output/images/briefs)",
    )
    args = parser.parse_args()

    src_dir = REPO_ROOT / args.dir
    if not src_dir.exists():
        print(f"ERROR: {src_dir} does not exist", file=sys.stderr)
        return 1

    pngs = sorted(p for p in src_dir.iterdir()
                  if p.is_file() and p.suffix.lower() == ".png")
    if not pngs:
        print(f"No PNGs found in {src_dir}")
        return 0

    total_src_kb = 0.0
    total_variant_kb = 0.0
    wrote = 0
    skipped = 0

    for png in pngs:
        # Count variants that exist before this call
        pre_existing = sum(
            1 for v in VARIANTS if variant_path(png, v).exists()  # type: ignore[arg-type]
        )
        variants = make_variants(png, force=args.force)
        src_kb = _kb(png)
        var_kb = sum(_kb(p) for p in variants.values())
        total_src_kb += src_kb
        total_variant_kb += var_kb
        post_existing = len(variants)
        newly_written = post_existing - pre_existing if not args.force else post_existing
        if newly_written > 0:
            wrote += newly_written
            print(
                f"  {png.name}  src={src_kb:4.0f} KB  "
                f"-> 4 variants total {var_kb:4.0f} KB  "
                f"({newly_written} written, {4 - newly_written} skipped)"
            )
        else:
            skipped += 4
            print(f"  {png.name}  (all variants up-to-date)")

    print()
    print(f"Processed {len(pngs)} source PNGs")
    print(f"  Source total:   {total_src_kb/1024:.2f} MB")
    print(f"  Variants total: {total_variant_kb/1024:.2f} MB")
    if total_src_kb:
        ratio = total_src_kb / total_variant_kb if total_variant_kb else 0
        print(f"  Ratio:          {ratio:.1f}x smaller per complete set")
    print(f"  Variants written this run: {wrote}")
    print(f"  Variants skipped (existed): {skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
