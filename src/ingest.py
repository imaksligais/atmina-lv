import asyncio
import os
import re
import sys
import time
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse

import httpx
import numpy as np
import trafilatura
import yaml
from bs4 import BeautifulSoup

from src.db import (
    get_db,
    init_db,
    insert_chunks,
    insert_document,
    log_action,
    now_lv,
    now_lv_dt,
    _compute_content_hash,
    _compute_simhash,
    _hamming_distance,
)
from src.embeddings import embed_document
from src.ingest_log import append_ingest_batch_summary

# Politician matching API moved to src.matcher in Phase 1 of the
# refactor (2026-04-29). Re-exported here so .claude/agents/* prompts and
# scripts/* keep their `from src.ingest import ...` imports working
# without churn. Internal ingest helpers (_log_failure, ingest_all,
# _parse_rss_items etc.) stay in this module. NEW callers should import
# from src.matcher directly. See docs/refactor/agent_api_inventory.txt.
from src.matcher import (  # noqa: F401 — re-export shim
    _clear_politician_cache,
    _latvian_surname_inflections,
    _load_politician_forms,
    _match_politician_from_url,
    _surname_has_person_context,
    assign_unmatched_documents,
    extract_twitter_author_handle,
    link_politicians_to_documents,
    match_politician,
    match_politicians,
)


def extract_tweet_id(url_or_id: str | None) -> str | None:
    """Accepts 'https://x.com/Foo/status/123' or '123'. Returns the tweet ID or None."""
    if not url_or_id:
        return None
    s = url_or_id.strip()
    if s.isdigit():
        return s
    m = re.search(r"/status/(\d+)", s)
    return m.group(1) if m else None


# --- Language detection (fasttext) ---

_ft_model = None


def _get_ft_model():
    global _ft_model
    if _ft_model is None:
        import fasttext
        import warnings
        warnings.filterwarnings("ignore", category=UserWarning, module="fasttext")
        model_path = os.path.join("tests", "calibration_results", "lid.176.ftz")
        if not os.path.exists(model_path):
            import urllib.request
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            url = "https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz"
            urllib.request.urlretrieve(url, model_path)
        _ft_model = fasttext.load_model(model_path)
    return _ft_model


def _detect_language(text: str) -> tuple[str, float]:
    model = _get_ft_model()
    # Limit to first 2000 chars for detection (fasttext chokes on huge texts)
    clean = text[:2000].replace("\n", " ").strip()
    _orig_array = np.array
    def _compat_array(*args, **kwargs):
        kwargs.pop("copy", None)
        return _orig_array(*args, **kwargs)
    np.array = _compat_array
    try:
        predictions = model.predict(clean, k=3)
    finally:
        np.array = _orig_array
    labels, scores = predictions
    lang = labels[0].replace("__label__", "")
    return lang, float(scores[0])


# --- Content validation ---

ERROR_PAGE_PATTERNS = [
    r"404\s*(not\s*found|page\s*not\s*found|lapa\s*nav\s*atrasta)",
    r"403\s*forbidden",
    r"access\s*denied",
    r"paywall",
    r"subscribe\s*to\s*(continue|read|access)",
    r"captcha",
    r"recaptcha",
    r"please\s*verify\s*you\s*are\s*(a\s*)?human",
    r"lapa\s*nav\s*atrasta",
]

NON_PUBLIC_PATTERNS = [
    r"\bCONFIDENTIAL\b",
    r"\bEMBARGOED UNTIL\b",
    r"\bNOT FOR PUBLIC RELEASE\b",
    r"\bDRAFT — NOT FOR DISTRIBUTION\b",
    r"\bDRAFT - NOT FOR DISTRIBUTION\b",
    r"\bKONFIDENCIĀLI\b",
    r"\bKONFIDENCIALI\b",
]


def validate_content(text: str, source_url: str) -> tuple[bool, str]:  # noqa: ARG001 - source_url is API-stable; callers always pass it, reserved for future context-aware validation
    if len(text) < 100:
        return False, "Length: content too short (< 100 chars)"
    for pattern in NON_PUBLIC_PATTERNS:
        if re.search(pattern, text.upper(), re.IGNORECASE):
            return False, f"Non-public: matched '{pattern}'"
    # Error page detection — only short docs (real articles have "captcha" in page chrome)
    if len(text) < 5000:
        for pattern in ERROR_PAGE_PATTERNS:
            if re.search(pattern, text.lower()):
                return False, f"Error page: matched pattern '{pattern}'"

    # 4. Language detection
    lang, confidence = _detect_language(text)
    if lang not in ("lv", "ru", "en"):
        return False, f"Language: detected '{lang}' (confidence {confidence:.2f}), expected lv/ru/en"

    # 5-6. Dedup checks (exact hash + simhash)
    try:
        db = get_db()
        content_hash = _compute_content_hash(text)
        existing = db.execute("SELECT id FROM documents WHERE content_hash = ?", (content_hash,)).fetchone()
        if existing:
            db.close()
            return False, f"Exact dedup: content_hash already exists (doc {existing['id']})"
        sim = _compute_simhash(text)
        for row in db.execute("SELECT id, simhash FROM documents WHERE simhash IS NOT NULL").fetchall():
            if _hamming_distance(sim, row["simhash"]) <= 3:
                db.close()
                return False, f"Near-dupe: simhash too close to doc {row['id']}"
        db.close()
    except Exception:
        pass

    return True, f"OK (lang={lang}, confidence={confidence:.2f})"


# --- Scraping ---

RETRY_DELAYS = [1, 4, 16]


async def scrape_source(
    url: str, tier: int, fetcher_mode: str = "fetcher"
) -> str | None:
    if tier == 1:
        return await _scrape_tier1(url)
    elif tier == 2:
        if fetcher_mode == "web_scraper":
            return await _scrape_web_articles(url)
        return await _scrape_tier2(url, fetcher_mode)
    return None


async def _scrape_tier1(url: str) -> list[dict] | str | None:
    """Returns list of {text, url} dicts for RSS, raw text for HTML, or None on failure."""
    for attempt, delay in enumerate(RETRY_DELAYS):
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(url, headers={
                    "User-Agent": "PoliTracker/1.0 (political-monitoring; contact@example.com)"
                })
                resp.raise_for_status()
                content_type = resp.headers.get("content-type", "")
                text = resp.text

                # If RSS/XML, return structured items with links
                if "xml" in content_type or text.strip().startswith("<?xml") or "<rss" in text[:200]:
                    items = _parse_rss_items(text, url)
                    return await _enrich_rss_items_fulltext(items, url)
                elif "html" in content_type:
                    return _extract_html_text(text)

                return text
        except Exception:
            if attempt < len(RETRY_DELAYS) - 1:
                await asyncio.sleep(delay)
            else:
                return None
    return None


async def _enrich_rss_items_fulltext(
    items: list[dict], feed_url: str
) -> list[dict]:
    """Replace each RSS item's lede (title + description) with the article's
    FULL text, fetched from its `url` via httpx + trafilatura.

    Why: RSS ``<description>`` is only the lede (~30–70 words); the live article
    is 200–800. Tier-1 sources (LSM, Diena) previously stored just the lede,
    truncating every doc silently. Tier-2 sources already fetch full text via
    ``_scrape_web_articles``; this brings tier-1 RSS to parity.

    Guardrail (CLAUDE.md "Silent success is a defect class" + T12): when the
    full-text fetch fails, we do NOT silently keep the lede as if complete — we
    keep it as a fallback but mark the item ``truncated=True`` and log a WARN per
    URL so the batch summary counts it. ``insert_document`` updates web docs in
    place on ``source_url``, so a later successful re-fetch upgrades the stored
    doc from lede to full text automatically.

    Items whose ``url`` is the feed itself (no per-article link — the RSS
    fallback shape) or a social/known-non-article URL are passed through
    untouched.
    """
    if not items:
        return items

    async with httpx.AsyncClient(
        timeout=20.0, follow_redirects=True, headers=_HTTP_HEADERS
    ) as client:
        for item in items:
            article_url = item.get("url")
            # No per-article link, or link is just the feed URL -> nothing to fetch.
            if not article_url or article_url == feed_url:
                continue
            # Social/media URLs are not fetchable articles.
            domain = urlparse(article_url.lower()).netloc.removeprefix("www.")
            if domain in _SOCIAL_DOMAINS:
                continue

            lede = item.get("text", "")
            try:
                html = await _fetch_page(client, article_url)
                full = None
                if html:
                    full = _clean_extracted_text(
                        trafilatura.extract(
                            html,
                            include_comments=False,
                            include_tables=False,
                            deduplicate=True,
                        )
                    )
            except Exception:
                full = None
                html = None

            # Only upgrade if the fetched full text is meaningfully longer than
            # the lede; otherwise the article page yielded no usable body.
            if full and len(full) > max(len(lede), 200):
                item["text"] = full[:50000]
                # Backfill published_at from the article HTML if the RSS pubDate
                # was missing (some feeds omit it).
                if not item.get("published_at") and html:
                    pub = _extract_published_at(html)
                    if pub:
                        item["published_at"] = pub
            else:
                # Full-text fetch failed or gave nothing usable. Keep the lede
                # but make the truncation LOUD, not silent.
                item["truncated"] = True
                print(
                    f"WARN rss-fulltext: fetch/extract failed, keeping lede "
                    f"({len(lede.split())} words) for {article_url[:100]}",
                    file=sys.stderr,
                )
            await asyncio.sleep(0.5)  # polite pacing between article fetches

    return items


_HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "lv,en;q=0.5",
}

# URL path segments to skip (sports, weather, entertainment, lifestyle)
_SKIP_URL_SEGMENTS = {
    # Sports
    "/sports/", "/sport/", "/basketbols/", "/hokejs/", "/futbols/",
    "/volejbols/", "/teniss/", "/motorsports/", "/olimpiskas-speles/",
    # Weather
    "/laika-zinas/", "/laikapstakli/",
    # Entertainment & lifestyle
    "/izklaide/", "/dzivesstils/", "/dzive-stils/", "/lifehacks/",
    "/horoskopi/", "/zodiaks/", "/receptes/", "/virtuve/",
    # Culture (not political)
    "/kultura/kino-foto-un-tv/", "/kultura/teatris-un-deja/",
    "/kultura/maksla/", "/kultura/literatura/", "/kultura/muzika/",
    # Tech, auto, travel
    "/auto/", "/motori/", "/tehnoloģijas/", "/tehnologijas/",
    "/celojumi/", "/turisms/",
    # Lifestyle / tabloid
    "/life/", "/tautaruna/",
    # Misc
    "/foto/", "/showroom/", "/komerczinas/",
    "/vide-un-dzivnieki/",
}

# ── Positive section filter for RSS items ──
# RSS feeds return all sections; we only keep articles whose URL contains
# at least one of these path segments.  Articles with no recognizable
# section path are kept (safety net for unusual URL structures).
_POLITICS_PATH_SEGMENTS = {
    # Latvian news / politics / economy / law
    "/latvija/", "/politika/", "/ekonomika/", "/likumi/",
    "/zinas/", "/sabiedriba/", "/eiropa/", "/arzemes/",
    # Delfi section IDs (numeric + named)
    "/politics/", "/criminal/", "/kapec/", "/video/",
    # Russian-language equivalents (rus.delfi.lv)
    "/latvia/", "/biznes/", "/mir/",
    # LETA sections
    "/home/important/", "/news/",
    # NRA sections
    "/pasaule/", "/viedokli/", "/neatkariga/",
}


_SOCIAL_DOMAINS = {"x.com", "twitter.com", "facebook.com", "youtube.com", "nitter.net"}

# Political keyword filter — used for sources with keyword_filter: true
# (e.g. TVNet whose RSS has no section feeds). Items must contain at least
# one keyword OR mention a tracked politician to be stored.
_POLITICAL_KEYWORDS_LV = [
    "Saeima", "saeima", "valdīb", "ministr", "Ministru kabinet",
    "koalīcij", "opozīcij", "deputāt", "likumprojekt", "partij",
    "vēlēšan", "budžet", "Latvijas prezident", "premjer",
    "frakcij", "komisij", "reformu", "nodokļ", "subsīdij",
    "aizdevum", "deficīt", "Satversm", "likumdošan",
]
_POLITICAL_KEYWORDS_RU = [
    "правительств", "Сейм", "министр", "депутат",
    "коалици", "оппозици", "бюджет", "выбор",
]
_POLITICAL_KEYWORDS = _POLITICAL_KEYWORDS_LV + _POLITICAL_KEYWORDS_RU


def _passes_keyword_filter(text: str) -> bool:
    """Return True if text contains at least one political keyword."""
    return any(kw in text for kw in _POLITICAL_KEYWORDS)


def _is_relevant_section(url: str) -> bool:
    """Return True if URL belongs to a politics/news section we care about.

    If the URL doesn't match any known section pattern at all (e.g. a
    short/redirect URL), we keep it to avoid false negatives.
    """
    url_lower = url.lower()
    # Social platform URLs are always relevant (linked from social RSS feeds)
    domain = urlparse(url_lower).netloc.lstrip("www.")
    if domain in _SOCIAL_DOMAINS:
        return True
    # If URL contains any skip segment, reject regardless
    if not _is_relevant_url(url_lower):
        return False
    # If URL contains a politics/news segment, accept
    if any(seg in url_lower for seg in _POLITICS_PATH_SEGMENTS):
        return True
    # If URL has a recognizable section-like path (3+ segments), it's
    # probably a section we don't track — reject
    path_parts = [p for p in urlparse(url_lower).path.split("/") if p]
    if len(path_parts) >= 3:
        # Has a section structure but didn't match our politics paths
        return False
    # Short/ambiguous URL — keep as safety net
    return True


def _is_relevant_url(url: str) -> bool:
    """Return False if URL matches known irrelevant sections."""
    url_lower = url.lower()
    return not any(seg in url_lower for seg in _SKIP_URL_SEGMENTS)


# Site-specific article link patterns
_DELFI_RULES_BASE = {
    "include": [r"/\d+/\w+/\d{9,}/[a-z][\w-]+-[\w-]+"],
    "exclude": [r"/comments$", r"/showroom/", r"/par-mums", r"/abonesana",
                 r"/kontakti", r"/podkast", r"/archive/",
                 r"/sports/", r"/izklaide/", r"/auto/", r"/kino/",
                 r"/kultura/", r"/dzivesstils/", r"/virtual/"],
}
_SITE_LINK_RULES: dict[str, dict] = {
    "delfi.lv": {**_DELFI_RULES_BASE, "entry_pages": ["/", "/latvija/", "/bizness/"]},
    "rus.delfi.lv": {**_DELFI_RULES_BASE, "entry_pages": ["/", "/latvija/"]},
    "leta.lv": {
        # LETA articles: /home/important/<UUID>/ or /news/<section>/<UUID>/
        "include": [
            r"/home/important/[0-9A-Fa-f-]{36}",
            r"/news/[\w_]+/[0-9A-Fa-f-]{36}",
            r"/press_releases/[0-9A-Fa-f-]{36}",
        ],
        "exclude": [r"/plus/", r"/info_pages/", r"/jaunumi/", r"/infographics/"],
        # /news/* and /topic/* section indexes return 403/404 (locked).
        # /regions/ returns 200 with ~20 article links (regional politics/news).
        # No sitemap available. /jaunumi and /themes return 200 but 0 articles.
        "entry_pages": ["/", "/regions/"],
    },
    "la.lv": {
        # Latvijas Avīze (la.lv) — WordPress, flat-slug article URLs.
        # Article: /<long-hyphenated-slug>  (e.g. /saeimas-deputats-felss-...)
        # No working sitemap. Discovery: homepage + /category/zinas/.
        "include": [r"^/[a-z][\w-]{20,}$"],
        "exclude": [r"^/category/", r"^/tag/", r"^/video/", r"^/search",
                     r"^/testi/?$", r"^/top/?$", r"^/jaunakas-zinas/",
                     r"^/komentari", r"^/wp-", r"^/feed", r"^/\d+/?$"],
        "entry_pages": ["/", "/category/zinas/"],
    },
    "nra.lv": {
        # NRA articles: /<section>/<id>-<slug>.htm or /viedokli/<author>/<id>-<slug>.htm
        "include": [r"/[\w-]+/\d{5,}-[\w-]+\.htm$", r"/viedokli/[\w-]+/\d{5,}-[\w-]+\.htm$"],
        # /tautaruna/ subcategories: keep /citi/ + /raksti/ (politiski/oficiāli
        # raksti — piem., Felsa MK deklarācija); izslēgt slavenību, krimināls,
        # dīvainie utt. Sk. 2026-04-17 Felsa raksta gadījumu.
        "exclude": [r"/komentari", r"/komerczinas/", r"/foto/", r"/birka/", r"/tema/",
                     r"/lifehacks/", r"/dzivesstils/", r"/tautaruna/nebusanas/",
                     r"/tautaruna/miluli/", r"/tautaruna/dzivesstils/",
                     r"/tautaruna/slavenibas/", r"/tautaruna/divaini/",
                     r"/tautaruna/palidzi/", r"/tautaruna/kriminali/",
                     r"/sports/", r"/izklaide/", r"/auto/", r"/kultura/",
                     r"/receptes/", r"/celojumi/"],
        "entry_pages": ["/", "/latvija/", "/pasaule/", "/viedokli/", "/tautaruna/"],
    },
    "jauns.lv": {
        # Jauns.lv: /raksts/<top-cat>/<id>-<slug>. Top cats include zinas,
        # bizness, arzemes, izklaide, sports, sievietem, par-veselibu,
        # maja-un-darzs, receptes, lielie-stasti, tava-izglitiba.
        # Whitelist political-leaning cats only (zinas + arzemes); politikas
        # subkategorija dzīvo zem /kategorija/zinas/politika, bet raksta URL
        # vienmēr nēs /raksts/zinas/... neatkarīgi no subkat. Bizness sadaļa
        # ir lielākoties consumer/lifestyle — politiskie budžeta stāsti šeit
        # parasti tāpat ietverti zem /zinas/.
        "include": [r"^/raksts/(zinas|arzemes)/\d{5,}-[\w-]+$"],
        "exclude": [r"^/kategorija/", r"^/galerija/", r"^/video/",
                    r"/komentari$", r"^/tema/", r"^/temati/"],
        # Politikas lapa pirmā — _scrape_web_articles dedup-ē globāli un cap-o
        # uz 30 rakstiem; tāpēc politiski blīvākajām entry-page-ēm jābūt augšā,
        # lai homepage mixed content neaizpilda budžetu.
        "entry_pages": [
            "/kategorija/zinas/politika",
            "/kategorija/zinas/sabiedriba",
            "/kategorija/zinas",
            "/",
        ],
    },
}


def _extract_site_article_links(html: str, base_url: str) -> list[str]:
    """Extract article URLs using site-specific rules.
    Falls back to generic heuristics if no rules match."""
    parsed_base = urlparse(base_url)
    domain = parsed_base.netloc.lower()

    # Find matching site rules
    rules = None
    for site_key, site_rules in _SITE_LINK_RULES.items():
        if domain == site_key or domain.endswith("." + site_key):
            rules = site_rules
            break

    soup = BeautifulSoup(html, "html.parser")
    seen = set()
    articles = []

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        full_url = urljoin(base_url, href)
        parsed = urlparse(full_url)

        # Must be same domain or subdomain
        link_domain = parsed.netloc.lower()
        base_root = ".".join(domain.split(".")[-2:])
        link_root = ".".join(link_domain.split(".")[-2:])
        if link_root != base_root:
            continue

        path = parsed.path
        if not path or path == "/":
            continue

        # Deduplicate (strip query params and trailing slash for comparison)
        clean_url = f"{parsed.scheme}://{parsed.netloc}{path.rstrip('/')}"
        if clean_url in seen:
            continue

        if rules:
            # Check exclusions first
            if any(re.search(pat, path, re.IGNORECASE) for pat in rules.get("exclude", [])):
                continue
            # Must match at least one include pattern
            if not any(re.search(pat, path) for pat in rules["include"]):
                continue
        else:
            # Generic fallback: use the existing _extract_article_links logic
            # Skip very short paths
            path_parts = [p for p in path.split("/") if p]
            if len(path_parts) < 3:
                continue
            # Must have some article-like pattern
            if not re.search(r"\d{6,}", path) and not re.search(r"/\d{4}/\d{2}/", path):
                continue

        # Global irrelevant URL filter (sports, weather, etc.)
        if not _is_relevant_url(clean_url):
            continue

        seen.add(clean_url)
        articles.append(clean_url)

    return articles


def _clean_extracted_text(text: str) -> str | None:
    """Clean trafilatura output: strip cookie banners, navigation, markdown artifacts.
    Returns cleaned text or None if content is junk."""
    if not text:
        return None

    # Remove common boilerplate patterns from Latvian news sites
    junk_patterns = [
        r"!\[logo\]\(data:.*?\)",                   # Inline base64 logos
        r"\[?\s*Powered by Cookiebot\s*\]?",        # Cookiebot banners
        r"\*\s*\[Consent\].*?(?=\n\n|\Z)",          # Cookie consent blocks
        r"Sīkdatņu izvēles.*?(?=\n\n|\Z)",          # Latvian cookie notice
        r"Этот сайт использует.*?(?=\n\n|\Z)",       # Russian cookie notice
        r"^\s*\*\s*\[(?:Home|Sākums|Главная)\].*$", # Navigation breadcrumbs
        r"^[\s\*\[\]#]+$",                           # Lines that are only markdown artifacts
    ]
    for pat in junk_patterns:
        text = re.sub(pat, "", text, flags=re.MULTILINE | re.IGNORECASE)

    # Remove lines that are just links (navigation remnants)
    _link_only = re.compile(r"^\s*\[?\s*\]\(https?://.*\)\s*$")
    _bullet_link = re.compile(r"^\s*\*\s*\[.*?\]\(.*?\)\s*$")
    text = "\n".join(
        ln for ln in text.split("\n")
        if not _link_only.match(ln.strip())
        and not (_bullet_link.match(ln.strip()) and len(ln.strip()) < 80)
    )

    # Collapse excessive whitespace
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    # If after cleaning the text is too short, it was junk
    if len(text) < 100:
        return None

    return text


async def _fetch_page(client: httpx.AsyncClient, url: str) -> str | None:
    """Fetch a page with retries. Returns HTML text or None."""
    for attempt, delay in enumerate(RETRY_DELAYS):
        try:
            resp = await client.get(url, headers=_HTTP_HEADERS)
            resp.raise_for_status()
            return resp.text
        except Exception:
            if attempt < len(RETRY_DELAYS) - 1:
                await asyncio.sleep(delay)
    return None


async def _scrape_web_articles(url: str, max_articles: int = 30) -> list[dict] | None:
    """Scrape news sites using httpx + trafilatura. No browser needed.
    Returns list of {text, url} dicts, or None on failure."""

    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        # Step 1: Fetch entry page(s) to discover article links.
        # Use site-specific entry_pages if defined (e.g. /latvija/, /bizness/)
        # so we only discover articles from relevant sections.
        parsed_base = urlparse(url)
        domain = parsed_base.netloc.lower()
        entry_pages = ["/"]
        for site_key, site_rules in _SITE_LINK_RULES.items():
            if domain == site_key or domain.endswith("." + site_key):
                entry_pages = site_rules.get("entry_pages", ["/"])
                break

        article_urls: list[str] = []
        seen_urls: set[str] = set()
        for page_path in entry_pages:
            page_url = f"{parsed_base.scheme}://{parsed_base.netloc}{page_path}"
            page_html = await _fetch_page(client, page_url)
            if not page_html:
                continue
            for link in _extract_site_article_links(page_html, page_url):
                if link not in seen_urls:
                    seen_urls.add(link)
                    article_urls.append(link)

        if not article_urls:
            # Last resort: extract whatever text we can from the homepage
            fallback_html = await _fetch_page(client, url)
            text = trafilatura.extract(fallback_html, include_comments=False) if fallback_html else None
            if text and len(text) >= 100:
                from src.title_extract import extract_title
                return [{"text": text, "url": url,
                         "title": extract_title(fallback_html)}]
            return None

        # Step 2: Fetch and extract each article (limit to max_articles)
        from src.title_extract import extract_title
        items = []
        for article_url in article_urls[:max_articles]:
            try:
                html = await _fetch_page(client, article_url)
                if not html:
                    continue
                text = _clean_extracted_text(trafilatura.extract(
                    html, include_comments=False, include_tables=False, deduplicate=True))
                if not text:
                    continue
                items.append({"text": text[:50000], "url": article_url,
                              "published_at": _extract_published_at(html),
                              "title": extract_title(html)})

            except Exception:
                continue

            # Brief pause between requests to be respectful
            await asyncio.sleep(0.5)

        return items if items else None


async def _scrape_tier2(url: str, _fetcher_mode: str) -> list[dict] | None:
    """Scrape a Tier 2 site: discover article links from homepage, then scrape each.
    Returns list of {text, url} dicts (same format as RSS items), or None on failure."""
    try:
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

        browser_config = BrowserConfig(headless=True, verbose=False)
        run_config = CrawlerRunConfig(page_timeout=15000, verbose=False)

        async with AsyncWebCrawler(config=browser_config) as crawler:
            # Step 1: Scrape homepage to discover article links
            homepage = await crawler.arun(url=url, config=run_config)
            if not homepage.success:
                return None

            # Extract article links from the homepage
            article_urls = _extract_site_article_links(homepage.html or "", url)
            if not article_urls:
                # Fallback: if no article links found, return homepage markdown as single item
                if homepage.markdown:
                    from src.title_extract import extract_title
                    return [{"text": homepage.markdown, "url": url,
                             "published_at": _extract_published_at(homepage.html),
                             "title": extract_title(homepage.html)}]
                return None

            from src.title_extract import extract_title
            items = []
            for article_url in article_urls[:30]:
                try:
                    r = await crawler.arun(url=article_url, config=run_config)
                    text = (getattr(r, 'fit_markdown', None) or r.markdown) if r.success else None
                    if text and len(text) >= 100:
                        article_html = getattr(r, "html", None)
                        items.append({"text": text[:50000], "url": article_url,
                                      "published_at": _extract_published_at(article_html),
                                      "title": extract_title(article_html)})
                except Exception:
                    pass
                await asyncio.sleep(1)

            return items if items else None

    except Exception:
        return None


def _strip_html(text: str) -> str:
    """Strip HTML tags and collapse whitespace."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()


# Patterns ordered by specificity: article: > og: > itemprop > generic name=
# > <time> > JSON-LD. First valid match wins.
_PUB_AT_PATTERNS = (
    (re.compile(r'<meta\s+(?:property|name)=["\']article:published_time["\']\s+content=["\']([^"\']+)', re.I), "article:published_time"),
    (re.compile(r'<meta\s+(?:property|name)=["\']og:published_time["\']\s+content=["\']([^"\']+)', re.I), "og:published_time"),
    (re.compile(r'<meta\s+itemprop=["\']datePublished["\']\s+content=["\']([^"\']+)', re.I), "itemprop=datePublished"),
    (re.compile(r'<meta\s+name=["\']publish[-_]?date["\']\s+content=["\']([^"\']+)', re.I), "name=publish-date"),
    (re.compile(r'<meta\s+name=["\']pubdate["\']\s+content=["\']([^"\']+)', re.I), "name=pubdate"),
    (re.compile(r'<meta\s+name=["\']articledate["\']\s+content=["\']([^"\']+)', re.I), "name=articledate"),
    (re.compile(r'<meta\s+name=["\']date["\']\s+content=["\']([^"\']+)', re.I), "name=date"),
    (re.compile(r'<time[^>]+datetime=["\']([^"\']+)', re.I), "time-datetime"),
    (re.compile(r'"datePublished"\s*:\s*"([^"]+)', re.I), "JSON-LD"),
)

# Latvia/Estonia/Baltic timezone aliases used by some sites (notably LSM.lv)
# instead of ISO-8601 offsets. Replace before ISO validation.
_TZ_ALIASES = (
    ("EEST", "+03:00"),  # Eastern European Summer Time
    ("EET", "+02:00"),   # Eastern European Time
)


def _extract_published_at(html: str | None) -> str | None:
    """Parse published_at from common HTML metadata patterns.

    Returns ISO datetime string (raw, unmodified) or None. Validates that the
    candidate parses as ISO; rejects garbage like "not-a-date".

    Used by tier-2 web_scraper path so NRA/Delfi/LA docs match RSS-fed sources
    on published_at (LSM/Diena/TVNet RSS feeds keep it via _parse_rss_items).

    LSM.lv puts published_at in `<meta name="articledate" ...>` with a non-ISO
    timezone alias (e.g. `2022-02-22T16:27:00EET`). The articledate pattern +
    `_TZ_ALIASES` normalize this to a parseable ISO offset.
    """
    if not html:
        return None
    for pattern, _label in _PUB_AT_PATTERNS:
        m = pattern.search(html)
        if not m:
            continue
        candidate = m.group(1).strip()
        for alias, offset in _TZ_ALIASES:
            if candidate.endswith(alias):
                candidate = candidate[: -len(alias)] + offset
                break
        # LSM emits a non-zero-padded hour for times before 10:00 (`T8:36`, not
        # `T08:36`); ISO 8601 requires `08`, so fromisoformat would reject it and
        # the date would be silently dropped. Zero-pad the hour position only.
        candidate = re.sub(r"T(\d):", r"T0\1:", candidate)
        if _looks_like_iso_datetime(candidate):
            return candidate
    return None


def _looks_like_iso_datetime(s: str) -> bool:
    """Cheap validator — accepts ISO 8601 dates and datetimes."""
    if not s or len(s) < 10:
        return False
    try:
        # fromisoformat handles 2026-04-25, 2026-04-25T07:25:00, 2026-04-25T07:25:00+03:00
        # but NOT trailing Z or fractional seconds in older Pythons. Use replace.
        datetime.fromisoformat(s.replace("Z", "+00:00"))
        return True
    except (ValueError, TypeError):
        return False


def _parse_rss_items(xml_text: str, base_url: str, max_age_days: int = 30) -> list[dict]:
    """Extract structured items from RSS/XML feed. Returns list of {text, url} dicts."""
    from xml.etree import ElementTree as ET
    from email.utils import parsedate_to_datetime
    cutoff = datetime.now(tz=None) - timedelta(days=max_age_days)
    fallback = [{"text": xml_text, "url": base_url}]
    items = []
    try:
        root = ET.fromstring(xml_text)
        # RSS 2.0
        for item in root.iter("item"):
            pub_date_str = item.findtext("pubDate")
            pub_dt = None
            if pub_date_str:
                try:
                    pub_dt = parsedate_to_datetime(pub_date_str).replace(tzinfo=None)
                    if pub_dt < cutoff:
                        continue
                except (ValueError, TypeError):
                    pass
            title = (item.findtext("title") or "").strip()
            desc = _strip_html(item.findtext("description") or "")
            # Dedup title/desc when desc starts with title
            if title and desc and desc.startswith(title[:30]):
                parts = [desc]
            else:
                parts = [p for p in (title, desc) if p]
            link = item.findtext("link")
            item_url = (link.strip() if link else None) or base_url
            if parts and _is_relevant_section(item_url):
                items.append({"text": " — ".join(parts), "url": item_url,
                              "published_at": pub_dt.isoformat() if pub_dt else None,
                              "title": title or None})
        # Atom
        for ns in ["", "{http://www.w3.org/2005/Atom}"]:
            for entry in root.iter(f"{ns}entry"):
                title = (entry.findtext(f"{ns}title") or "").strip()
                summary = _strip_html(entry.findtext(f"{ns}summary") or "")
                parts = [p for p in (title, summary) if p]
                link_el = entry.find(f"{ns}link")
                link = link_el.get("href") if link_el is not None else None
                pub_dt = None
                for dtag in [f"{ns}published", f"{ns}updated"]:
                    ds = entry.findtext(dtag)
                    if ds:
                        try:
                            pub_dt = datetime.fromisoformat(ds.replace("Z", "+00:00")).replace(tzinfo=None)
                        except (ValueError, TypeError):
                            pass
                        break
                if parts:
                    items.append({"text": " — ".join(parts),
                                  "url": (link.strip() if link else None) or base_url,
                                  "published_at": pub_dt.isoformat() if pub_dt else None,
                                  "title": title or None})
    except ET.ParseError:
        return fallback
    return items or fallback


_SKIP_TAGS = frozenset(("script", "style", "nav", "header", "footer"))
_BLOCK_TAGS = frozenset(("p", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6"))


def _extract_html_text(html: str) -> str:
    """Basic HTML to text extraction."""
    from html.parser import HTMLParser
    from io import StringIO

    class _S(HTMLParser):
        def __init__(self):
            super().__init__()
            self.r, self._skip = StringIO(), False
        def handle_starttag(self, tag, attrs):  # noqa: ARG002 - HTMLParser API contract
            if tag in _SKIP_TAGS:
                self._skip = True
        def handle_endtag(self, tag):
            if tag in _SKIP_TAGS:
                self._skip = False
            if tag in _BLOCK_TAGS:
                self.r.write("\n")
        def handle_data(self, data):
            if not self._skip:
                self.r.write(data)

    s = _S()
    s.feed(html)
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", s.r.getvalue())).strip()


# Matcher API moved to src.matcher (Phase 1 refactor 2026-04-29).
# Re-exported above; see top-of-file shim.


# --- Main ingestion ---

def _log_failure(db_source_id, duration_ms, error_msg, dry_run):
    """Log an ingest failure and track it in the sources table."""
    if dry_run:
        return
    _track_failure(db_source_id)
    log_action("ingest", source_id=db_source_id, status="failure",
               duration_ms=duration_ms, error_message=error_msg)


def _load_sources() -> list[dict]:
    with open("sources.yaml", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("sources", [])


async def _ingest_source(
    source: dict,
    db_source_id: int | None,
    dry_run: bool,
    semaphores: dict,
) -> dict:
    """Ingest a single source. Returns result dict."""
    url = source["url"]
    name = source.get("name", url)
    tier = source.get("tier", 1)
    fetcher_mode = source.get("fetcher_mode", "fetcher")
    rate_limit = source.get("rate_limit_seconds", 60)

    domain = urlparse(url).netloc
    if domain not in semaphores:
        semaphores[domain] = asyncio.Semaphore(1)

    result = {
        "source": name,
        "url": url,
        "status": "skipped",
        "documents": 0,
        "error": None,
    }

    async with semaphores[domain]:
        t0 = time.time()
        try:
            scraped = await scrape_source(url, tier, fetcher_mode)
            duration_ms = int((time.time() - t0) * 1000)

            if scraped is None:
                result["status"] = "failure"
                result["error"] = "Scrape returned None"
                _log_failure(db_source_id, duration_ms, "Scrape returned None", dry_run)
                return result

            # Normalize to list of {text, url} items
            if isinstance(scraped, list):
                # Structured RSS items already have text + url
                items = scraped
            else:
                # Plain text (HTML or Tier 2 markdown) — split into chunks
                items = [{"text": t, "url": url} for t in _split_into_items(scraped)]

            use_keyword_filter = source.get("keyword_filter", False)

            stored = 0
            filtered_out = 0
            truncated = 0
            for item in items:
                item_text = item["text"]
                article_url = item.get("url") or url

                ok, reason = validate_content(item_text, article_url)
                if not ok:
                    continue

                # Match politicians early so keyword filter can reuse it
                source_opponent_id = source.get("opponent_id")
                if source_opponent_id:
                    politician_links = [(source_opponent_id, "subject")]
                else:
                    politician_links = match_politicians(item_text)
                # Fallback: extract author from URL (e.g. NRA viedokli /viedokli/author-name/...)
                if not politician_links and article_url:
                    url_pid = _match_politician_from_url(article_url)
                    if url_pid:
                        politician_links = [(url_pid, "subject")]

                # Keyword filter: skip items without political relevance
                # (only for sources flagged with keyword_filter: true)
                if use_keyword_filter:
                    if not politician_links and not _passes_keyword_filter(item_text):
                        filtered_out += 1
                        continue

                # General relevance gate: skip web articles that mention no
                # tracked politicians AND contain no political keywords.
                # Prevents accumulation of general news (international,
                # sports, weather) that will never produce claims.
                if not use_keyword_filter and not politician_links:
                    if not _passes_keyword_filter(item_text):
                        filtered_out += 1
                        continue

                if dry_run:
                    stored += 1
                    continue

                detected_lang, _ = _detect_language(item_text)
                if detected_lang not in ("lv", "ru", "en"):
                    detected_lang = "lv"
                src_platform = source.get("platform", "web")

                doc_id = insert_document(
                    item_text,
                    politician_links=politician_links or None,
                    source_id=db_source_id,
                    platform=src_platform,
                    language=detected_lang,
                    source_url=article_url,
                    published_at=item.get("published_at"),
                    title=item.get("title"),
                )
                if doc_id:
                    chunks = embed_document(item_text)
                    insert_chunks(doc_id, chunks)
                    stored += 1
                    if item.get("truncated"):
                        truncated += 1

            result["status"] = "success"
            result["documents"] = stored
            result["truncated"] = truncated

            if not dry_run:
                _reset_failures(db_source_id)
                log_action(
                    "ingest",
                    source_id=db_source_id,
                    status="success",
                    duration_ms=duration_ms,
                    details={"documents_stored": stored, "filtered_out": filtered_out,
                             "truncated_lede_fallback": truncated, "source_name": name},
                )

        except Exception as e:
            duration_ms = int((time.time() - t0) * 1000)
            result["status"] = "failure"
            result["error"] = str(e)
            _log_failure(db_source_id, duration_ms, str(e), dry_run)

        # Rate limiting
        await asyncio.sleep(rate_limit / 10)  # Reduced for batch processing

    return result


def _split_into_items(text: str) -> list[str]:
    """Split concatenated text into individual content items."""
    MAX_ITEM_SIZE = 5000  # Cap individual items

    # Split on double newlines
    parts = re.split(r"\n{2,}", text)
    # Merge small parts, split large parts
    items = []
    current = ""
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if len(current) + len(part) < 100:
            current = f"{current} {part}".strip() if current else part
        else:
            if current:
                items.append(current)
            current = part
    if current:
        items.append(current)

    if not items:
        items = [text]

    # Cap oversized items
    final = []
    for item in items:
        if len(item) <= MAX_ITEM_SIZE:
            final.append(item)
        else:
            # Split on paragraph boundaries within the item
            sub_parts = re.split(r"\n", item)
            chunk = ""
            for sp in sub_parts:
                if len(chunk) + len(sp) > MAX_ITEM_SIZE and len(chunk) >= 100:
                    final.append(chunk)
                    chunk = sp
                else:
                    chunk = f"{chunk}\n{sp}" if chunk else sp
            if chunk and len(chunk) >= 100:
                final.append(chunk)

    return final


def _get_or_create_source(sc: dict) -> int | None:
    """Get existing source ID from DB or create new one."""
    try:
        db = get_db()
        row = db.execute("SELECT id FROM sources WHERE url = ?", (sc["url"],)).fetchone()
        if row:
            db.close()
            return row["id"]
        g = sc.get
        db.execute(
            "INSERT INTO sources (url, name, tier, fetcher_mode, rate_limit_seconds,"
            " legal_status, legal_notes, last_tos_review) VALUES (?,?,?,?,?,?,?,?)",
            (sc["url"], g("name"), g("tier", 1), g("fetcher_mode", "fetcher"),
             g("rate_limit_seconds", 60), g("legal_status"), g("legal_notes"), g("last_tos_review")),
        )
        source_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.commit()
        db.close()
        return source_id
    except Exception:
        return None


def _update_source(source_id: int | None, *stmts: tuple) -> None:
    """Execute one or more SQL statements against sources table, commit & close."""
    if source_id is None:
        return
    try:
        db = get_db()
        for sql, params in stmts:
            db.execute(sql, params)
        db.commit()
        db.close()
    except Exception:
        pass


def _track_failure(source_id: int | None) -> None:
    _update_source(
        source_id,
        ("UPDATE sources SET consecutive_failures = consecutive_failures + 1 WHERE id = ?", (source_id,)),
        ("UPDATE sources SET active = FALSE WHERE id = ? AND consecutive_failures >= 3", (source_id,)),
        ("UPDATE sources SET active = TRUE WHERE id IN ("
         "SELECT fallback_source_id FROM sources "
         "WHERE id = ? AND consecutive_failures >= 3 AND fallback_source_id IS NOT NULL)", (source_id,)),
    )


def _reset_failures(source_id: int | None) -> None:
    _update_source(
        source_id,
        ("UPDATE sources SET consecutive_failures = 0, last_scraped = ? WHERE id = ?", (now_lv(), source_id)),
    )


def ingest_all(dry_run: bool = False) -> list[dict]:
    """Main entry point: ingest all active sources."""
    if not dry_run:
        from src.preflight import preflight_check
        ok, issues = preflight_check()
        if not ok:
            print("Preflight check failed:")
            for issue in issues:
                print(f"  - {issue}")
            return []

    init_db()
    sources = _load_sources()

    # Filter to active tier 1 and 2 sources
    active_sources = [
        s for s in sources
        if s.get("tier", 3) <= 2
        and s.get("legal_status") != "excluded"
    ]

    print(f"{'[DRY RUN] ' if dry_run else ''}Ingesting {len(active_sources)} sources...")

    # Create/get source IDs
    source_ids = {s["url"]: _get_or_create_source(s) for s in active_sources} if not dry_run else {}

    # Check which sources are still active in DB
    if not dry_run:
        db = get_db()
        for s in active_sources[:]:
            sid = source_ids.get(s["url"])
            if sid:
                row = db.execute("SELECT active FROM sources WHERE id = ?", (sid,)).fetchone()
                if row and not row["active"]:
                    print(f"  Skipping deactivated source: {s.get('name', s['url'])}")
                    active_sources.remove(s)
        db.close()

    # Run async ingestion
    semaphores = {}
    results = asyncio.run(_ingest_all_async(active_sources, source_ids, dry_run, semaphores))

    # Print summary
    total_docs = sum(r["documents"] for r in results)
    successes = sum(1 for r in results if r["status"] == "success")
    failures = len(results) - successes - sum(1 for r in results if r["status"] == "skipped")
    print(f"\nIngestion complete: {len(results)} sources, {successes} ok, {failures} failed, {total_docs} docs")
    for r in results:
        icon = "+" if r["status"] == "success" else "x" if r["status"] == "failure" else "-"
        err = f" ({r['error']})" if r.get("error") else ""
        print(f"  [{icon}] {r['source']}: {r['documents']} docs{err}".encode("ascii", "replace").decode("ascii"))

    if not dry_run:
        append_ingest_batch_summary(results)

    return results


async def _ingest_all_async(sources, source_ids, dry_run, semaphores):
    """Ingest sources: tier 1 concurrently, tier 2 sequentially."""
    coros = {s["url"]: _ingest_source(s, source_ids.get(s["url"]), dry_run, semaphores)
             for s in sources}
    tier1 = [coros[s["url"]] for s in sources if s.get("tier") == 1]
    tier2 = [coros[s["url"]] for s in sources if s.get("tier") == 2]
    results = list(await asyncio.gather(*tier1)) if tier1 else []
    for t in tier2:
        results.append(await t)
    return results


def main():
    dry_run = "--dry-run" in sys.argv
    ingest_all(dry_run=dry_run)


if __name__ == "__main__":
    main()
