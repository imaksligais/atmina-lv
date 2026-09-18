"""``_common`` datumu / formāta lapu-funkcijas.

Izgriezts no vienfaila ``src/render/_common.py`` 2026-09-05 (plāna 5.8).
Audita § 1.3 klasteris "Date/format leaves" — bez DB, bez māsu-moduļiem.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlparse

from src.render._common.constants import _LV_OFFSET_HOURS, _PARTY_LOWERCASE_WORDS

def _confidence_tier(c: float | None) -> str:
    """Map a numeric confidence (0.0–1.0) to the Pozīcijas V2 tier label.
    None falls through to 'merena' — conservative default for any future
    rows where extraction didn't record confidence."""
    if c is None:
        return "merena"
    if c >= 0.9:
        return "augsta"
    if c >= 0.75:
        return "laba"
    return "merena"


def _normalize_date(raw: str) -> str:
    """Normalize '26.03.2026' or '2026-03-26 ...' to 'YYYY-MM-DD'."""
    d = (raw or "")[:10]
    if "." in d and len(d) == 10:
        parts = d.split(".")
        if len(parts) == 3:
            return f"{parts[2]}-{parts[1]}-{parts[0]}"
    return d


def _date_sort_key(date_str: str | None) -> str:
    """Normalize date strings for sorting: handles both ISO (2026-04-01) and EU (01.04.2026) formats."""
    if not date_str:
        return ""
    s = date_str.strip()
    # EU format: dd.mm.yyyy
    if len(s) >= 10 and s[2] == "." and s[5] == ".":
        return s[6:10] + "-" + s[3:5] + "-" + s[0:2] + s[10:]
    return s


def _format_tweet_time(published_at: Optional[str], scraped_at: Optional[str]) -> str:
    """Return 'YYYY-MM-DD HH:MM' for the X feed.

    Prefers published_at (actual tweet post time, UTC ISO from twikit) converted
    to Latvia local time. Falls back to scraped_at (already LV-local) when the
    published_at is missing or unparseable. Without this, every tweet shows the
    scrape-run HH:MM instead of when it was posted.
    """
    if published_at:
        try:
            dt = datetime.fromisoformat(published_at)
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None) + timedelta(hours=_LV_OFFSET_HOURS)
            return dt.strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            pass
    return (scraped_at or "")[:16]


def _titlecase_party_name(name: str) -> str:
    """Capitalize first letter of each word, lowercasing the rest.
    Conjunctions like 'un' stay lowercase unless they're the first word.
    '/' is also a word boundary — joint lists ("Suverēnā vara/Jaunlatvieši")
    otherwise come out as "Vara/jaunlatvieši"."""
    words = name.split(" ")
    out = []
    for i, w in enumerate(words):
        if not w:
            out.append(w)
            continue
        segs = []
        for j, seg in enumerate(w.split("/")):
            if not seg:
                segs.append(seg)
                continue
            ls = seg.lower()
            stripped = ls.rstrip(",.!?;:")
            if (i > 0 or j > 0) and stripped in _PARTY_LOWERCASE_WORDS:
                segs.append(ls)
            else:
                segs.append(ls[0].upper() + ls[1:])
        out.append("/".join(segs))
    return " ".join(out)


def _initials_from_name(name: str | None) -> str:
    """Two-letter initials for avatar chip; '?' fallback."""
    if not name:
        return "?"
    parts = [p for p in name.split() if p]
    if not parts:
        return "?"
    return "".join(p[0].upper() for p in parts[:2])


def _delta_days(old_date: str | None, new_date: str | None) -> int | None:
    """Absolute day diff between two ISO dates; None if either missing/malformed."""
    if not old_date or not new_date:
        return None
    try:
        d_old = date.fromisoformat(old_date[:10])
        d_new = date.fromisoformat(new_date[:10])
        return abs((d_new - d_old).days)
    except (ValueError, TypeError):
        return None


def _domain_from_url(url: str | None) -> str | None:
    """Hostname with leading 'www.' stripped; None on empty/invalid."""
    if not url:
        return None
    try:
        netloc = urlparse(url).netloc
    except (ValueError, TypeError):
        return None
    if not netloc:
        return None
    return netloc.removeprefix("www.")


def _domain_label(source_domain: str | None, source_url: str | None) -> str | None:
    """Izdevēja etiķete claim rindai: ``documents.source_domain`` ir noteicošais.

    Hosts URL-ā ne vienmēr ir izdevējs. TVNET raksti daļēji tiek pasniegti no
    partnera hosta ``pmo.ee`` (2 125 doki, 176 pozīcijas, mērīts 2026-09-06) —
    ievākšanas brīdī ``documents.source_domain`` tiem visiem ir ``tvnet.lv`` un
    tas ir pareizs, bet virsmas etiķeti atvasināja no URL, tāpēc lasītājs redzēja
    ``pmo.ee``. URL netiek migrēts — tas ietilpst ``store_claim()`` idempotences
    trijniekā —, tāpēc labojums dzīvo tikai etiķetes atvasināšanā.

    Atkāpšanās uz URL hostu paliek rindām bez dokumenta (``saeima_vote`` claims
    glabā ``document_id`` NULL) un vēsturiskām rindām bez ``source_domain``.
    """
    if source_domain:
        return source_domain.removeprefix("www.")
    return _domain_from_url(source_url)
