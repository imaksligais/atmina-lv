#!/usr/bin/env python
"""Nedēļas pārskata vārdu skaits pa sadaļām (`src.briefs.weekly_brief_word_counts`).

    .venv/Scripts/python.exe scripts/weekly_brief_words.py --note 840
    .venv/Scripts/python.exe scripts/weekly_brief_words.py --file .scratch/draft.md

Rakstītājs un `@quality-reviewer` lieto šo pašu komandu. Tikai ziņo — izejas
kods ir 0 arī ārpus latiņas; rindas ārpus latiņas atzīmētas ar «!».
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src.briefs import (  # noqa: E402
    WEEKLY_STORY_WORDS_TARGET,
    WEEKLY_WORDS_TARGET,
    weekly_brief_word_counts,
)
from src.db import get_db  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description="Nedēļas pārskata vārdu skaits (tikai ziņo).")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--note", type=int, help="context_notes.id (weekly_brief)")
    g.add_argument("--file", help="markdown fails")
    args = ap.parse_args(argv)

    if args.file:
        content = Path(args.file).read_text(encoding="utf-8")
    else:
        db = get_db()
        try:
            row = db.execute(
                "SELECT content FROM context_notes WHERE id = ? AND note_type = 'weekly_brief'",
                (args.note,),
            ).fetchone()
        finally:
            db.close()
        if row is None:
            print(f"Nav nedēļas pārskata ar id {args.note}.")
            return 2
        content = row[0]

    counts = weekly_brief_word_counts(content)
    lo, hi = WEEKLY_STORY_WORDS_TARGET
    for title, n, is_story in counts["sections"]:
        flag = "!" if is_story and not lo <= n <= hi else " "
        print(f"{n:5d} {flag} {title}")
    lo, hi = WEEKLY_WORDS_TARGET
    flag = " " if lo <= counts["total"] <= hi else "!"
    stories = sum(1 for _, _, is_story in counts["sections"] if is_story)
    print(f"{counts['total']:5d} {flag} KOPĀ (latiņa {lo}–{hi}); stāsti: {stories}, tajos {counts['stories']} vārdi")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
