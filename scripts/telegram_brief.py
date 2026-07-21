"""Print a Telegram-formatted daily brief for copy-paste into Bot API.

Usage:
    python scripts/telegram_brief.py                   # today, HTML
    python scripts/telegram_brief.py 2026-04-18        # specific date, HTML
    python scripts/telegram_brief.py 2026-04-18 --md2  # MarkdownV2 format
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.briefs import generate_telegram_brief  # noqa: E402


def main() -> None:
    args = [a for a in sys.argv[1:] if a]
    fmt = "markdownv2" if "--md2" in args else "html"
    args = [a for a in args if not a.startswith("--")]
    date = args[0] if args else None
    out = generate_telegram_brief(date=date, fmt=fmt)
    sys.stdout.write(out)
    sys.stdout.write("\n")
    sys.stderr.write(f"\n[{len(out)} chars / 4096 limit, fmt={fmt}]\n")


if __name__ == "__main__":
    main()
