"""Soft-404 guard for article fetches.

A "soft-404" is an HTTP 200 page that is not the article — a missing-article
response that slips past ``raise_for_status()`` and feeds trafilatura a body
that can OVERWRITE the real stored document on re-fetch (the truncated-doc
backfill campaign prerequisite; ``backlog/avoti.md``).

Signals are deliberately narrow and each is tied to a live observation —
a false positive costs one fetch, a false negative silently overwrites a
stored document. Do not add keyword guesses for domains that already answer
with a real status code.

Probe, 2026-09-23 (httpx + project HEADERS, nonexistent article URLs):

- ``www.lsm.lv`` — SOFT-404. A dead ``.aNNNNNN`` id 301-redirects to
  ``https://www.lsm.lv/`` (the homepage): status 200, portal-tagline
  ``<title>``, no ``og:title``, trafilatura extracts ~13k chars of headline
  listings. Article ids that DO exist 301 to the article's canonical URL —
  the id is the key, slug and date in the path are ignored.
- ``www.diena.lv``, ``tvnet.lv``, ``nra.lv``, ``www.delfi.lv`` — all return
  real 404 statuses (e.g. ``<title>Lapa nav atrasta (404) - nra.lv</title>``).
  ``raise_for_status()`` already drops them upstream, so there is no signal
  for them here. diena.lv real articles also show a benign
  ``www.`` → apex redirect that KEEPS the path — that is not a soft-404.

Fixtures: ``tests/fixtures/soft404/`` (trimmed copies of the probe pages).
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)

# lsm.lv, observed 2026-09-23: the homepage shell served for a dead /raksts/
# URL carries the portal tagline as <title>; real articles are titled
# "<article title> / Raksts" and always set og:title.
_LSM_HOMEPAGE_TITLE = "LSM.lv - Uzticamas ziņas"


def _is_site_root(url: str) -> bool:
    return urlparse(url).path in ("", "/")


def _title(html: str) -> str | None:
    m = _TITLE_RE.search(html or "")
    if not m:
        return None
    return re.sub(r"\s+", " ", m.group(1)).strip()


def looks_like_soft_404(
    html: str,
    text: str | None,
    url: str,
    final_url: str | None = None,
) -> str | None:
    """Return a short reason when the fetched page is a soft-404, else None.

    ``text`` is the already-extracted article text when the caller has it —
    reserved for content-level signals; none observed as of 2026-09-23 (every
    soft-404 seen so far is detectable from the redirect target or <title>).
    """
    # `text` is API-stable — callers always pass it, reserved for future
    # extracted-text signals (same convention as ingest.validate_content).

    # Redirect to site root (www.lsm.lv, 2026-09-23): an article-path fetch
    # landing on "/" is never the article. A root URL fetched as root (the
    # homepage itself, an entry page) is not flagged.
    if final_url and not _is_site_root(url) and _is_site_root(final_url):
        return f"redirected to site root ({final_url})"

    # lsm.lv homepage shell without redirect info (same observation): a
    # /raksts/ article URL returning the generic portal <title>.
    host = urlparse(url).netloc.lower().removeprefix("www.")
    if host == "lsm.lv" and "/raksts/" in urlparse(url).path:
        if _title(html) == _LSM_HOMEPAGE_TITLE:
            return "lsm.lv /raksts/ URL returned the homepage shell"

    return None
