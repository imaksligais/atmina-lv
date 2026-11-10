"""Public label for a tweet's reply parent / quoted tweet (2026-11-10).

`documents.context_json` holds the FOREIGN tweet's text for the extractor.
The public page shows only «↪ Atbild @x» / «Citē @x» with a link to the
original — never that text, because the author may be a private person
(operator decision 2026-11-10). Only label and URL leave this function, so
the raw JSON never reaches a template (`x.py` spreads post dicts into `feed`).
"""

from __future__ import annotations

import json
import re

_HANDLE_RE = re.compile(r"^[A-Za-z0-9_]{1,30}$")
_ID_RE = re.compile(r"^[0-9]{1,25}$")
_LABELS = {"reply": "↪ Atbild", "quote": "Citē"}


def tweet_context_links(context_json: str | None) -> list[dict[str, str]]:
    """[{label, url}] for the direct reply parent and the quoted tweet.

    ``reply_root`` is extractor context only and is never shown. Handles and
    ids are re-validated before a URL is built from them.
    """
    if not context_json:
        return []
    try:
        items = json.loads(context_json)
    except (TypeError, ValueError):
        return []
    out = []
    for c in items if isinstance(items, list) else []:
        if not isinstance(c, dict):
            continue
        label = _LABELS.get(c.get("kind"))
        author, tid = str(c.get("author") or ""), str(c.get("id") or "")
        if label and _HANDLE_RE.match(author) and _ID_RE.match(tid):
            out.append({"label": f"{label} @{author}",
                        "url": f"https://x.com/{author}/status/{tid}"})
    return out
