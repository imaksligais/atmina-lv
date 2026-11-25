"""Uzbūvē assets/topics.svg no Lucide ikonām (ISC) pēc TOPIC_ICONS.

Lietojums:
    .venv/Scripts/python.exe scripts/build_topic_sprite.py <lucide-static/icons mape>

Lucide repo netiek glabāts: `npm pack lucide-static` jebkurā pagaidu mapē,
atspiež un nodod `package/icons` ceļu. Fails ir deterministisks (ikonas
alfabēta secībā, LF), tāpēc atkārtots skrējiens bez izmaiņām neko nemaina.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.render._common.constants import FALLBACK_TOPIC_ICON, TOPIC_ICONS  # noqa: E402

OUT = ROOT / "assets" / "topics.svg"
_INNER = re.compile(r"<svg\b[^>]*>(.*)</svg>", re.S)


def _names() -> list[str]:
    return sorted({*TOPIC_ICONS.values(), FALLBACK_TOPIC_ICON})


def build(icons_dir: Path) -> str:
    # Daļa Lucide ikonu ir atvasinātas no Feather un nes arī MIT licenci (saraksts
    # pakotnes LICENSE failā); assets/topics-LICENSE.txt satur tikai ISC tekstu.
    lic = icons_dir.parent / "LICENSE"
    feather: set[str] = set()
    if lic.exists():
        listed = lic.read_text(encoding="utf-8").split("derived from the Feather project:")
        if len(listed) > 1:
            feather = {n.strip() for n in listed[1].split("The MIT License")[0].split(",")}
    parts = [
        "<!-- Tēmu ikonas: Lucide (https://lucide.dev), ISC License, "
        "Copyright (c) Lucide Icons and Contributors; pilns teksts topics-LICENSE.txt. "
        "Būvē scripts/build_topic_sprite.py; ar roku nelabo. -->",
        '<svg xmlns="http://www.w3.org/2000/svg">',
    ]
    for name in _names():
        src = icons_dir / f"{name}.svg"
        if not src.exists():
            raise SystemExit(f"Lucide ikonas nav: {name} ({src})")
        if name in feather:
            raise SystemExit(f"{name} ir no Feather (MIT): pieliec MIT tekstu assets/topics-LICENSE.txt")
        m = _INNER.search(src.read_text(encoding="utf-8"))
        if not m:
            raise SystemExit(f"Neizdevās nolasīt: {src}")
        inner = " ".join(line.strip() for line in m.group(1).strip().splitlines())
        parts.append(f'<symbol id="ti-{name}" viewBox="0 0 24 24">{inner}</symbol>')
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    text = build(Path(sys.argv[1]))
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"{OUT.relative_to(ROOT)}: {len(_names())} ikonas, {len(text)} baiti")
