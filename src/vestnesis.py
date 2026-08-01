"""Latvijas Vēstnesis (JL feed) two-stage fetcher.

The JL RSS at https://www.vestnesis.lv/feed/JL exposes only title+link+pubDate
per item; the body lives at /ta/id/<N>. This module fetches the feed,
parses act IDs out of the URLs, and pulls each detail page through
trafilatura.

Used by scripts/ingest_vestnesis.py — manual, idempotent ingest path.
"""

import re
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as ET

import httpx
import trafilatura

JL_FEED_URL = "https://www.vestnesis.lv/feed/JL"
ACT_URL_RE = re.compile(r"vestnesis\.lv/ta/id/(\d+)")
DEFAULT_TIMEOUT = 30
USER_AGENT = "atmina-bot/1.0 (+https://atmina.lv)"

# Match signer lines like:
#   "Ministru prezidente: E. Siliņa"
#   "Klimata un enerģētikas ministrs K. Melnis"
#   "Valsts prezidents E. Rinkēvičs"
# Captures the I. Uzvārds form.
_SIGNER_RE = re.compile(
    r"(?:Valsts\s+prezident\w*|Saeimas\s+priekšsēdētāj\w*|"
    r"Ministru\s+prezident\w*|"
    r"[A-ZĀČĒĢĪĶĻŅŠŪŽ][\w-]+(?:\s+un\s+\w+)?\s+ministr\w*|"
    r"Tieslietu\s+ministr\w*)"
    r"\s*[:.]?\s*"
    r"([A-ZĀČĒĢĪĶĻŅŠŪŽ]\.\s*[A-ZĀČĒĢĪĶĻŅŠŪŽ][\wāčēģīķļņšūž-]+)",
    re.UNICODE,
)


def fetch_jl_feed(max_age_days: int = 7, timeout: int = DEFAULT_TIMEOUT) -> list[dict]:
    """Fetch the JL RSS. Returns newest-first list of:
    {act_id, title, url, published_at}.
    """
    cutoff = datetime.now() - timedelta(days=max_age_days)
    headers = {"User-Agent": USER_AGENT}
    with httpx.Client(timeout=timeout, headers=headers, follow_redirects=True) as client:
        resp = client.get(JL_FEED_URL)
        resp.raise_for_status()
        xml_text = resp.text

    root = ET.fromstring(xml_text)
    items: list[dict] = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_date_str = item.findtext("pubDate")
        m = ACT_URL_RE.search(link)
        if not m:
            continue
        act_id = m.group(1)
        pub_dt = None
        if pub_date_str:
            try:
                pub_dt = parsedate_to_datetime(pub_date_str).replace(tzinfo=None)
                if pub_dt < cutoff:
                    continue
            except (ValueError, TypeError):
                pass
        items.append({
            "act_id": act_id,
            "title": title,
            "url": link,
            "published_at": pub_dt.isoformat() if pub_dt else None,
        })
    return items


def fetch_act_body(url: str, timeout: int = DEFAULT_TIMEOUT) -> str | None:
    """Fetch a single vestnesis act detail page. Returns plain-text body or None."""
    headers = {"User-Agent": USER_AGENT}
    try:
        with httpx.Client(timeout=timeout, headers=headers, follow_redirects=True) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                return None
            html = resp.text
    except httpx.HTTPError:
        return None
    body = trafilatura.extract(
        html, include_comments=False, include_tables=True, favor_recall=True
    )
    if not body or len(body) < 200:
        return None
    return body


def extract_signers(body: str) -> list[str]:
    """Extract distinct signer names ('I. Uzvārds' form) from act body."""
    seen: set[str] = set()
    out: list[str] = []
    for m in _SIGNER_RE.finditer(body):
        name = re.sub(r"\s+", " ", m.group(1).strip())
        if name not in seen:
            seen.add(name)
            out.append(name)
    return out
