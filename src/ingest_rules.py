"""Per-site URL / keyword ingest rules — pure data + pure predicates.

Carved out of ``src/ingest.py`` on 2026-09-05 (plan
docs/plans/2026-09-05-strukturas-tirisanas-plans.md § 5.4, audit § 1.5). Pure
move: no behaviour, no comment and no name changed. This is really
``sources.yaml``-adjacent configuration that happened to live in code; keeping
it in one leaf makes a per-site rule change a one-file diff instead of a hunt
inside the 1 200-line scraper.

``src.ingest`` re-exports every name below under its original spelling —
``tests/test_ingest.py`` imports ``_extract_site_article_links`` and
``_is_relevant_section`` from ``src.ingest``. New callers should import here.
"""

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

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


# ── Nogrieztais ievads ──
# Dažu izdevēju rakstu ķermenis ienāk bez pirmās rindkopas, tāpēc `content`
# sākas ar anaforisku vietniekvārdu, kura atsauce palika neienākušajā rindkopā:
# «Viņš uzsvēra…», «Viņa norādīja…». Mērīts 2026-09-06: 56 no 14 737
# `platform='web'` doku (32 bija 08-23) — klase aug; sadalījums pa domēniem
# diena.lv 41, lsm.lv 12, la.lv 2, ogrenet.lv 1.
#
# Vārts KAROGO, nevis atmet (operatora lēmums 2026-09-06). Trīs no šiem
# dokiem izvilktās pozīcijas tika salasītas pret dzīvo rakstu — 0
# misatribūciju; atmešana zaudētu labu korpusu par risku, kas nav
# materializējies.
#
# Šaurums ir apzināts: tikai divas formas un reģistrjutīgi. «Viņu», «Viņas»,
# «Viņi» sākumā ir normāli teikumi («Viņu skaits pieauga»), un mazais burts
# nozīmē teikuma vidu, ne raksta sākumu — plašāks paterns pārvērstu 0,4 %
# signālu troksnī.
_CUT_LEDE_PREFIXES = ("Viņš ", "Viņa ")


def _looks_like_cut_lede(text: str | None) -> bool:
    """True, ja dokumenta saturs sākas ar nogrieztam ievadam raksturīgu formu."""
    if not text:
        return False
    return text.lstrip().startswith(_CUT_LEDE_PREFIXES)


def _is_relevant_section(url: str) -> bool:
    """Return True if URL belongs to a politics/news section we care about.

    If the URL doesn't match any known section pattern at all (e.g. a
    short/redirect URL), we keep it to avoid false negatives.
    """
    url_lower = url.lower()
    # Social platform URLs are always relevant (linked from social RSS feeds)
    # removeprefix, not lstrip: lstrip("www.") strips a CHARACTER SET, so
    # "wp.lv" became "p.lv" (latent, found 2026-09-05).
    domain = urlparse(url_lower).netloc.removeprefix("www.")
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

        # 2026-07-28 — collapse consecutive duplicate path segments
        # ("/neatkariga/neatkariga/izpete/…"): nra.lv relative-href artifact
        # that ingested the same article twice under two URLs. store_claim
        # idempotence keys on source_url, so the twin URLs would double-store
        # any future claim (BACKLOG § nra.lv dublēti ingesti; 3 known pairs).
        segments = path.split("/")
        collapsed = [s for i, s in enumerate(segments)
                     if not s or i == 0 or s != segments[i - 1]]
        path = "/".join(collapsed)

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
