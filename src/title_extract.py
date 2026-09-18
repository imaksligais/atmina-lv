"""Extract canonical article title from HTML.

Used at ingest time so ``documents.title`` is reliably populated for all
web news sources (LSM, Delfi, NRA, TVNet, LETA, Diena, LA.lv, jauns.lv,
rus.delfi.lv). Same pipeline is reused by scripts/backfill_titles.py for
legacy rows.

Signal priority:
    1. <meta property="og:title">       (most reliable, set by all majors)
    2. <meta name="twitter:title">
    3. JSON-LD NewsArticle.headline
    4. <title>
    5. First <h1>

Output is normalized: HTML entities decoded, whitespace collapsed, known
site suffixes stripped, capped at 250 chars. Returns None if no signal
yields a non-empty result.
"""
from __future__ import annotations

import html
import json
import re
from typing import Optional

# Site-suffix patterns to strip from <title> tags. Ordered most-specific first
# so e.g. " - LSM.lv" matches before " - LSM". Case-insensitive match.
_SITE_SUFFIXES = [
    " - LSM.lv", " | LSM.lv", " - LSM",
    " | Delfi", " - Delfi", " | DELFI", " - DELFI",
    " - Latvijas Avīze", " - LA.lv", " | LA.lv",
    " - Jauns.lv", " | Jauns.lv",
    " - TVNet", " | TVNet", " - tvnet.lv", " | tvnet.lv",
    " - Diena", " | Diena", " - diena.lv",
    " - NRA", " | NRA", " - nra.lv",
    " - LETA", " | LETA",
    " - rus.delfi.lv", " | rus.delfi.lv",
]

_OG_TITLE_FORWARD_RE = re.compile(
    r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']*)["\']',
    re.IGNORECASE,
)
_OG_TITLE_REVERSE_RE = re.compile(
    r'<meta[^>]+content=["\']([^"\']*)["\'][^>]+property=["\']og:title["\']',
    re.IGNORECASE,
)
_TWITTER_TITLE_FORWARD_RE = re.compile(
    r'<meta[^>]+name=["\']twitter:title["\'][^>]+content=["\']([^"\']*)["\']',
    re.IGNORECASE,
)
_TWITTER_TITLE_REVERSE_RE = re.compile(
    r'<meta[^>]+content=["\']([^"\']*)["\'][^>]+name=["\']twitter:title["\']',
    re.IGNORECASE,
)
_TITLE_TAG_RE = re.compile(
    r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL
)
_H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.IGNORECASE | re.DOTALL)
_JSONLD_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)
_TAG_STRIP_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")

_MAX_LEN = 250


def extract_title(raw_html: Optional[str]) -> Optional[str]:
    """Return the article's canonical title or None.

    Tries og:title → twitter:title → JSON-LD headline → <title> → <h1>.
    Strips known site suffixes, decodes HTML entities, collapses whitespace,
    caps length at 250 chars.
    """
    if not raw_html or not isinstance(raw_html, str):
        return None

    for getter in (
        lambda h: _try_meta_pair(h, _OG_TITLE_FORWARD_RE, _OG_TITLE_REVERSE_RE),
        lambda h: _try_meta_pair(h, _TWITTER_TITLE_FORWARD_RE, _TWITTER_TITLE_REVERSE_RE),
        _try_jsonld_headline,
        lambda h: _try_tag(h, _TITLE_TAG_RE),
        lambda h: _try_tag(h, _H1_RE),
    ):
        candidate = getter(raw_html)
        if not candidate:
            continue
        normalized = _normalize(candidate)
        if normalized:
            return normalized
    return None


def _try_meta_pair(
    raw_html: str,
    forward: re.Pattern[str],
    reverse: re.Pattern[str],
) -> Optional[str]:
    """Try forward attribute order first, fall back to reverse order."""
    m = forward.search(raw_html) or reverse.search(raw_html)
    return m.group(1) if m else None


def _try_tag(raw_html: str, pattern: re.Pattern[str]) -> Optional[str]:
    m = pattern.search(raw_html)
    if not m:
        return None
    inner = _TAG_STRIP_RE.sub(" ", m.group(1))
    return inner.strip() or None


def _try_jsonld_headline(raw_html: str) -> Optional[str]:
    """Search every <script type=application/ld+json> block for a `headline`."""
    for m in _JSONLD_RE.finditer(raw_html):
        block = m.group(1).strip()
        if not block:
            continue
        # JSON-LD may be a single object, an array, or have @graph wrapper.
        try:
            data = json.loads(block)
        except (json.JSONDecodeError, ValueError):
            continue
        for headline in _walk_jsonld_headline(data):
            if headline:
                return headline
    return None


def _walk_jsonld_headline(node):
    if isinstance(node, dict):
        h = node.get("headline")
        if isinstance(h, str) and h.strip():
            yield h
        for key in ("@graph", "mainEntity"):
            child = node.get(key)
            if child is not None:
                yield from _walk_jsonld_headline(child)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_jsonld_headline(item)


def _normalize(text: str) -> Optional[str]:
    decoded = html.unescape(text)
    collapsed = _WHITESPACE_RE.sub(" ", decoded).strip()
    if not collapsed:
        return None
    stripped = _strip_site_suffix(collapsed)
    if not stripped:
        return None
    return stripped[:_MAX_LEN].rstrip()


def _strip_site_suffix(text: str) -> str:
    lower = text.lower()
    for suffix in _SITE_SUFFIXES:
        if lower.endswith(suffix.lower()):
            return text[: -len(suffix)].rstrip()
    return text
