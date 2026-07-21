"""
Query writeback: enrich wiki person/topic pages with insights
discovered during interactive analysis sessions.
"""

from datetime import datetime, timezone, timedelta
from pathlib import Path

_LV_OFFSET = timedelta(hours=3)

WRITEBACK_SECTION = "## Writeback"


def _now_lv() -> str:
    return (datetime.now(timezone.utc) + _LV_OFFSET).strftime("%Y-%m-%d")


def enrich_person_page(
    page_path: str,
    insight: str,
    source: str = "query",
) -> bool:
    """Append an insight to a wiki person/topic page.

    Adds under a '## Writeback' section. Creates section if missing.
    Skips if the exact insight text already exists in the page.

    Returns True if the page was modified.
    """
    path = Path(page_path)
    if not path.exists():
        return False

    text = path.read_text(encoding="utf-8")

    if insight in text:
        return False

    date = _now_lv()
    entry = f"- _{date}_ ({source}): {insight}\n"

    if WRITEBACK_SECTION in text:
        idx = text.index(WRITEBACK_SECTION)
        newline_after = text.index("\n", idx)
        next_section = text.find("\n## ", newline_after + 1)
        if next_section == -1:
            if not text.endswith("\n"):
                text += "\n"
            text += entry
        else:
            text = text[:next_section] + entry + text[next_section:]
    else:
        if not text.endswith("\n"):
            text += "\n"
        text += f"\n{WRITEBACK_SECTION}\n\n{entry}"

    path.write_text(text, encoding="utf-8")
    return True


def enrich_topic_page(
    wiki_dir: str,
    topic_slug: str,
    insight: str,
    source: str = "query",
) -> bool:
    """Enrich a topic page by slug."""
    page = Path(wiki_dir) / "topics" / f"{topic_slug}.md"
    return enrich_person_page(str(page), insight, source)
