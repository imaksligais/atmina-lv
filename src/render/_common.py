"""Shared rendering helpers — leaf module for src/render/.

Phase F3a (refactor-plan-2026-04-29 § Fāze 3) carve-out from src/generate.py.
Hosts constants, security filters, slug/format helpers, and cross-page
domain enrichment that any sub-page renderer in src/render/ may import.

**Architectural rule (F4 lesson):** _common.py imports nothing from
src.render.* — it is the leaf. Sub-page modules (e.g. contradictions.py)
import from _common but never from each other. If two sub-pages share a
helper, promote it here.

src/generate.py re-exports every public-ish name from this module so
existing test imports (``from src.generate import _slugify``,
``from src.generate import PARTY_COLORS``, …) keep working without
churn while later sub-phases (F3b–F3g) progressively delegate.
"""

from __future__ import annotations

import gzip as _gzip
import json
import logging
import os
import re
import sqlite3
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote as _quote, urlparse

import bleach
import brotli as _brotli
import markdown
import yaml
from jinja2 import Environment
from markupsafe import Markup

# Re-export from src.profile_kind so sub-page renderers (politicians.py
# under F4 leaf rule) import everything domain-related through _common.
from src.profile_kind import ProfileKind, derive_profile_kind  # noqa: F401

_logger = logging.getLogger(__name__)


# ── Path roots ──────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

DEFAULT_DB_PATH = str(PROJECT_ROOT / "data" / "atmina.db")
DEFAULT_OUTPUT_DIR = str(PROJECT_ROOT / "output")
TEMPLATES_DIR = str(PROJECT_ROOT / "templates")
ASSETS_DIR = PROJECT_ROOT / "assets"
WIKI_DIR = PROJECT_ROOT / "wiki"
CONTENT_DIR = PROJECT_ROOT / "content"


# ── Site-wide constants ─────────────────────────────────────────────

BASE_URL = "https://atmina.lv"

ELECTION_DATE = date(2026, 10, 3)


def norm_source_domain_sql(col: str = "d.source_domain") -> str:
    """SQL izteiksme, kas nostrippo ``www.`` priedēkli no source_domain, lai
    dokumentus grupētu pēc normalizēta hosta. Vienots avots — agrāk inline
    ``src/render/mediji.py``, tagad to importē arī politicians.py own_pubs
    vaicājums. ``col`` ļauj norādīt citu aliasa kvalifikāciju, defaults
    ``d.source_domain``."""
    return (f"CASE WHEN {col} LIKE 'www.%' THEN substr({col}, 5) "
            f"ELSE lower({col}) END")

PARTY_COLORS = {
    'Jaunā Vienotība': '#3b82f6', 'Zaļo un Zemnieku savienība': '#84cc16',
    'Nacionālā apvienība': '#22c55e', 'Progresīvie': '#a855f7',
    'Latvija Pirmajā Vietā': '#ef4444', 'Apvienotais saraksts': '#06b6d4',
    'Stabilitātei!': '#f97316', 'MMN': '#f97316', 'Latvijas attīstībai': '#14b8a6',
}

# 32 canonical topic groups (topic_map.TOPIC_GROUPS keys) → chip colors.
# Single source of truth, promoted here from positions.py so both the
# Pozīcijas feed (``positions.PZV1_TOPIC_COLORS`` alias) and the Tēmas
# destination pages (``topics.py``) share one map without a sibling
# import (F4 leaf rule). First 16 entries match the handoff palette
# (atmina-handoff/…/pozicijas-data.jsx); next 10 are HSL-derived (L=62%,
# S=52%) at 36° intervals, avoiding PARTY_COLORS; last 5 added 2026-04-25
# for the new canonical topics (semantic affinity, distinct from
# PARTY_COLORS and the existing 26).
TOPIC_COLORS: dict[str, str] = {
    "Aizsardzība un drošība":      "#dc2626",
    "airBaltic":                   "#2563eb",
    "Koalīcija un partijas":       "#a856f7",
    "Ukraina un Krievija":         "#eab308",
    "Valsts pārvalde":             "#64748b",
    "Ārpolitika":                  "#0891b2",
    "Vēlēšanas":                   "#ec4899",
    "Degviela un enerģētika":      "#f97317",
    "Tieslietas":                  "#16a34a",
    "Budžets un finanses":         "#85cc16",   # #84cc16 clashes with ZZS party color
    "Pašvaldības":                 "#06b6d5",   # #06b6d4 clashes with AS party color
    "Imigrācija":                  "#d946ef",
    "Transports":                  "#15b8a6",   # #14b8a6 clashes with LA party color
    "Sabiedriskie mediji":         "#f43f5e",
    "Droni":                       "#6366f1",
    "Sociālā politika":            "#8b5cf6",
    # handoff palette ends here — next 10 derived HSL rotation
    "ES politika":                 "#e17055",
    "Rail Baltica":                "#b89a5b",
    "Mežsaimniecība":              "#6b8e4e",
    "Valsts kapitālsabiedrības":   "#4fa58a",
    "Izglītība":                   "#5b8fb8",
    "Valodu politika":             "#7a6fb8",
    "Vide":                        "#b85b8f",
    "Pensijas":                    "#b87a5b",
    "Lauksaimniecība":             "#8fa55b",
    "Kultūra":                     "#5bb88e",
    # 2026-04-25 — 5 new canonical topics
    "Klimats":                     "#5b8eb8",   # sky-atmosphere blue
    "Veselības aprūpe":            "#5b9b8e",   # medical teal (avoids LA #14b8a6)
    "Pilsētvide":                  "#708090",   # slate, urban
    "Korupcija un KNAB":           "#6b5b8e",   # weighty deep purple
    "Digitālā politika":           "#5bb8b8",   # cyan-tech (avoids AS #06b6d4)
    # 2026-07-04 — 32. kanoniskā tēma
    "Sports":                      "#c9803d",   # medal bronze (avoids Degviela #f97317, Rail Baltica #b89a5b)
}

SEVERITY_LV = {
    "direct_contradiction": "Tieša pretruna",
    "reversal": "Apvērsums",
    "minor_shift": "Pozīcijas maiņa",
}

# Category derived from claim_type pair. Canonical key: sorted types joined by "_".
# Drives the main badge text on OG cards, pretrunas list, detail page, politician page.
CATEGORY_LV = {
    "position_position": "Pozīcijas maiņa",
    "position_saeima_vote": "Vārdi vs. Darbi",
    "saeima_vote_saeima_vote": "Balsojuma maiņa",
}

# Label for a single claim panel when the pair is mixed-type.
# For same-type pairs we fall back to chronological "Iepriekš" / "Pašlaik".
CLAIM_TYPE_LABEL = {
    "position": "Vārdi",
    "saeima_vote": "Darbi",
}

_SEVERITY_GLYPHS: dict[str, str] = {
    "direct_contradiction": "⇄",
    "reversal": "↺",
    "minor_shift": "≈",
}

# Latvian transliteration map (same as wiki.py)
_LV_TRANS = str.maketrans(
    "āčēģīķļņōŗšūžĀČĒĢĪĶĻŅŌŖŠŪŽ",
    "acegiklnorsuzACEGIKLNORSUZ",
)

# EEST fixed offset (summer 2026) — matches src.db._LV_OFFSET. Tweet
# timestamps render in this zone so the X feed shows real post times.
_LV_OFFSET_HOURS = 3

# Conjunctions that stay lowercase in title-cased party names unless
# they're the first word (e.g. "Zaļo un Zemnieku savienība").
_PARTY_LOWERCASE_WORDS = {"un"}


# ── Security filters (SEC-01, SEC-02, SEC-04) ───────────────────────

_SAFE_HTML_TAGS = [
    "p", "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li", "a", "strong", "em", "b", "i",
    "code", "pre", "blockquote", "br", "hr",
    "table", "thead", "tbody", "tr", "th", "td",
    "dl", "dt", "dd", "sub", "sup", "abbr",
]
_SAFE_HTML_ATTRS = {
    "a": ["href", "title"],
    "abbr": ["title"],
    "td": ["align"],
    "th": ["align"],
}


def _sanitize_html(html: str) -> str:
    """Sanitize HTML from markdown rendering (SEC-01)."""
    return bleach.clean(
        html,
        tags=_SAFE_HTML_TAGS,
        attributes=_SAFE_HTML_ATTRS,
        protocols=["http", "https", "mailto"],
    )


# Bare claim-ID citations (e.g. "claim #208", "(#6757)", "(#14411)") lead
# nowhere in the public UI — strip them per house citation style. The optional
# "claim " prefix is consumed with the ID so no orphan word remains. The 3-6
# digit bound spares contradiction refs like "#1"/"#12" (house style keeps those).
_CLAIM_ID_RE = re.compile(r"\s*\(?(?:claim\s+)?#\d{3,6}\)?")


def _clean_context_note(content: str | None) -> str:
    """Clean a context-note body for public display.

    Strips bare claim-ID citations, renders markdown (bold/italic/lists),
    and sanitizes the resulting HTML. Returns ``""`` for empty/None input.
    """
    if not content:
        return ""
    text = _CLAIM_ID_RE.sub("", content)
    # Collapse only space/tab runs left where an ID was removed — NOT newlines,
    # which markdown needs for paragraph breaks. Then drop any space stranded
    # before punctuation (e.g. "pārbaudi (#208)." -> "pārbaudi.").
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\s+([.,;:])", r"\1", text)
    md = markdown.Markdown(extensions=["tables", "fenced_code"])
    return _sanitize_html(md.convert(text.strip()))


def _safe_json_filter(value: str) -> Markup:
    """Jinja2 filter: mark JSON safe for inline <script> after escaping </script> (SEC-02).

    Replaces '</' with '<\\/' to prevent script tag breakout in inline JSON.
    """
    if isinstance(value, str):
        escaped = value.replace("</", r"<\/")
    else:
        escaped = json.dumps(value, ensure_ascii=False, default=str).replace("</", r"<\/")
    return Markup(escaped)


def _safe_url_filter(url: str) -> str:
    """Jinja2 filter: validate URL protocol to prevent javascript: injection (SEC-04)."""
    if url and isinstance(url, str):
        stripped = url.strip()
        if stripped.lower().startswith(("http://", "https://", "mailto:")):
            return stripped
    return "#"


_BILL_REF_RE = re.compile(r"\b(\d+)/(Lp14|Lm14|P14)\b")


def _autolink_bills_filter(
    text: str | None,
    bill_slugs: set[str] | None = None,
    prefix: str = "",
) -> str:
    """Wrap '1288/Lp14' style references in <a href="likumprojekti/<slug>.html">.

    Unknown document_nr (slug not in bill_slugs) preserved as plain text — no
    broken links. Caller must ensure input is trusted (claim summaries are
    plain Latvian text); template uses `| safe` after this filter.
    bill_slugs=None is graceful (renders as plain text); never crash on
    missing context.

    ``prefix`` = depth-prefikss (``assets_prefix``): depth-1 lapas
    (politiki/<slug>.html, pretrunas/<id>.html) padod ``"../"``, citādi
    saite atrisinās uz neeksistējošu ``politiki/likumprojekti/...``.
    Tas pats depth-paterns kā ``_bill_card.html.j2`` makro ``prefix``.
    """
    if not text:
        return text or ""
    bill_slugs = bill_slugs or set()

    def _sub(m: re.Match) -> str:
        nr, suffix = m.group(1), m.group(2)
        slug = f"{nr}-{suffix.lower()}"
        if slug not in bill_slugs:
            return m.group(0)
        return f'<a href="{prefix}likumprojekti/{slug}.html">{m.group(0)}</a>'

    return _BILL_REF_RE.sub(_sub, text)


# ── Markdown content helpers ────────────────────────────────────────


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown text.

    Shared across ``src.render.analyses`` (``_load_wiki_profile`` +
    ``_load_analyses``) and ``src.render.syntheses`` (``_load_syntheses``).
    Promoted from ``src/generate.py:143`` in F3f.5 — both sub-page
    modules consume it, and keeping it in ``_common`` avoids a reverse
    ``from src.generate import _parse_frontmatter`` cycle (F3-prep
    promotion rule). Note: ``_fetch_blog_posts`` (F3f.4 ``src.render.blog``)
    does NOT call this — blog posts come from the ``context_notes`` DB
    table, not markdown files.
    """
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    yaml_block = text[3:end].strip()
    body = text[end + 4:].lstrip("\n")
    try:
        fm = yaml.safe_load(yaml_block) or {}
    except yaml.YAMLError:
        fm = {}
    return fm, body


def _lv_plural(n: object, singular: str, plural: str) -> str:
    """Latvian count→noun agreement. Numbers ending in 1 (but NOT 11) take the
    singular form; everything else (including 0 and 2–9, 11–19, …) takes the
    plural. Registered as a Jinja filter ``lv_plural`` — use as
    ``{{ n }} {{ n|lv_plural("pozīcija", "pozīcijas") }}``.
    """
    try:
        i = int(n)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return plural
    return singular if (i % 10 == 1 and i % 100 != 11) else plural


def _load_wiki_profile(slug: str) -> Optional[str]:
    """Load editorial profile body from ``wiki/persons/<slug>.md``.

    Strips the auto-synced stats block bracketed by ``<!-- SYNC-AUTO -->`` /
    ``<!-- /SYNC-AUTO -->`` markers — that block is for Obsidian graph view
    (uses ``[[wikilinks]]``) and is not meant for public render.

    Promoted from ``src/render/analyses.py`` in F3g.3 alongside
    restoring the callsite at ``src/render/politicians.py:310``
    (F3f.5 follow-up — the function had been dead code since F3b
    PR #7 hardcoded ``wiki_profile = None``). It belongs in
    ``_common`` semantically: its only consumer is
    ``render_politicians``, not analyses-themed rendering.
    """
    path = WIKI_DIR / "persons" / f"{slug}.md"
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    _fm, body = _parse_frontmatter(text)
    body = re.sub(
        r"<!--\s*SYNC-AUTO\s*-->.*?<!--\s*/SYNC-AUTO\s*-->",
        "",
        body,
        flags=re.DOTALL,
    ).strip()
    if not body:
        return None
    md = markdown.Markdown(extensions=["tables", "fenced_code"])
    return _sanitize_html(md.convert(body))


# ── Slug / party / format helpers ───────────────────────────────────


def _slugify(name: str) -> str:
    """Transliterate Latvian characters and convert to URL-safe slug."""
    transliterated = name.translate(_LV_TRANS)
    slug = transliterated.lower().replace(" ", "-")
    slug = "".join(c for c in slug if c.isalnum() or c == "-")
    return slug


def _party_page_slug(short_name: str) -> str:
    """Filename-safe slug for a party detail page (``partijas/<slug>.html``).

    Historically this was just ``short_name.lower()``, which breaks when a
    short_name contains a filesystem/path-separator character — e.g. a
    'SV/AJ'-style class label would point the render at a nested/invalid
    path. Rule: lowercase, then map every character that is unsafe in a
    filename (``/ \\ : * ? " < > |`` and whitespace) to ``-``. All
    currently-tracked short_names contain only ``[A-Za-z0-9-]`` so their
    URLs are unchanged (locked by
    ``tests/test_party_page_slug.py::test_existing_party_urls_unchanged``).

    This is the ONE canonical party-page slug — every link to a party page
    (render modules, templates, sitemap) must route through it.
    """
    _UNSAFE = set('/\\:*?"<>|')
    slug = "".join(
        "-" if (ch in _UNSAFE or ch.isspace()) else ch
        for ch in short_name.lower()
    )
    return slug


def _party_short_name(party: str) -> str:
    """Map party full name to its official short name (NA, JV, etc.). Falls
    back to first-letters-of-words if no explicit mapping."""
    SHORT = {
        "Apvienotais saraksts": "AS",
        "Austošā Saule Latvijai": "ASL",
        "Jaunā Vienotība": "JV",
        "Latvija Pirmajā Vietā": "LPV",
        "Latvijas attīstībai": "LA",
        "MMN": "MMN",
        "Nacionālā apvienība": "NA",
        "Progresīvie": "PRO",
        "Stabilitātei!": "ST",
        "Suverenā vara": "SV",
        "Zaļo un Zemnieku savienība": "ZZS",
    }
    if party in SHORT:
        return SHORT[party]
    letters = [w[0].upper() for w in party.split() if w]
    return "".join(letters[:3])


def _persona_category(
    votes_count: int,
    relationship_type: str | None,
    party: str | None,
    role: str | None,
) -> str:
    """Classify a tracked politician into a UI category for the Personas page.

    Rules (first match wins):
      1. votes_count > 0 → Deputāti (active MP regardless of role)
      2. relationship_type = organization → Iestādes un mediji (NBS, LVM,
         LDDK, ziņu raidījumi/aģentūras — pre-2026-06-09 these leaked into
         Amatpersonas (role set) or Citi (bare), and media feeds typed
         'journalist' sat among human journalists)
      3. relationship_type ∈ {journalist, influencer, neutral} → mapped label
      4. party set → Amatpersonas (ministers, party officials)
      5. role set (no party) → Amatpersonas (civil servants, board members)
      6. otherwise → Citi

    Kandidāti category was removed 2026-04-25 evening — even with broadened
    `coalition_status='not_in_saeima'` rule the bucket showed mostly MMN
    members (9 of 12), which gave a misleading impression. Non-Saeima party
    members now flow into Amatpersonas like other party-affiliated
    non-deputies. Re-introduce when there is a credible cross-party
    candidate dataset (e.g. CVK kandidātu saraksts ingest).
    """
    if votes_count > 0:
        return "Deputāti"
    if relationship_type == "organization":
        return "Iestādes un mediji"
    role_map = {"journalist": "Žurnālisti", "influencer": "Ietekmētāji", "neutral": "Analītiķi"}
    if relationship_type in role_map:
        return role_map[relationship_type]
    if party:
        return "Amatpersonas"
    if role:
        return "Amatpersonas"
    return "Citi"


def _outlet_feed_map(
    db: sqlite3.Connection,
    outlets: list[dict[str, Any]] | None = None,
) -> dict[int, dict[str, Any]]:
    """opponent_id -> {short_name, name, slug, hosts} outletam, kuram pieder
    profila X konts (sources.yaml ``x_feeds`` x social_accounts.handle join).

    ``hosts`` ir outleta domēnu saraksts (sources.yaml ``hosts``) — to izmanto
    politicians.py own_pubs vaicājums, lai atlasītu medija paša publikācijas
    pēc source_domain. Aditīvs atslēga; agrākie lasītāji (short_name/name/slug)
    nemainās.

    Handle salīdzinājums case-insensitive; join iet caur social_accounts.handle
    (autoritatīvais), NE tracked_politicians.x_handle (legacy, klusi diverģē —
    sk. CLAUDE.md schema invariants). Dublēts handle divos outletos -> pirmais
    uzvar + stderr brīdinājums. outlets=None ielādē no sources.yaml.
    """
    if outlets is None:
        from src.outlets import load_outlets
        outlets = load_outlets()
    handle_to_outlet: dict[str, dict[str, Any]] = {}
    for o in outlets:
        for h in o.get("x_feeds") or []:
            hl = h.lower()
            if hl in handle_to_outlet and handle_to_outlet[hl]["short_name"] != o["short_name"]:
                print(f"[mediji] @{h} divos outletos — paliek "
                      f"{handle_to_outlet[hl]['short_name']}", file=sys.stderr)
                continue
            handle_to_outlet.setdefault(hl, o)
    if not handle_to_outlet:
        return {}
    m: dict[int, dict[str, Any]] = {}
    # Reālā DB glabā platform='twitter' (vēsturiskais nosaukums); 'x' pieņemts
    # testu/nākotnes rindām. Tikai 'x' šeit nozīmētu klusu 0-rindu join.
    for pid, handle in db.execute(
            "SELECT opponent_id, handle FROM social_accounts "
            "WHERE platform IN ('twitter', 'x')"):
        o = handle_to_outlet.get((handle or "").lower())
        if o is not None:
            m.setdefault(pid, {"short_name": o["short_name"],
                               "name": o["name"], "slug": o["slug"],
                               "hosts": list(o.get("hosts") or [])})
    return m


def _split_org_category(category: str, pid: int, media_feed_ids: set[int]) -> str:
    """'Iestādes un mediji' -> 'Mediji' (outleta feeds) vai 'Iestādes' (pārējie).
    Citas kategorijas iziet cauri nemainītas. Sk. spec 2026-06-10."""
    if category != "Iestādes un mediji":
        return category
    return "Mediji" if pid in media_feed_ids else "Iestādes"


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


_BRACKET_RE = re.compile(r'\s*\[([^\]]+)\]')


def _split_summary(summary: str | None) -> tuple[str, str | None]:
    """Lift bracketed context notes out of a contradiction summary.

    Summaries authored by @contradiction-hunter sometimes append meta
    context in square brackets (e.g. coalition discipline, tactical
    alternatives, plausible explanations). Rendering them inline as
    literal brackets is noisy; surface them as a separate block instead.

    Returns (clean_summary, context_note). Multiple bracket groups are
    joined with ' · '. Leading/trailing "Konteksts:" / "Iespējams
    skaidrojums:" framing tokens are stripped — they're implied by the
    block label in the UI.
    """
    if not summary:
        return (summary or "", None)
    matches = _BRACKET_RE.findall(summary)
    if not matches:
        return (summary, None)
    clean = _BRACKET_RE.sub('', summary).strip()
    notes: list[str] = []
    for m in matches:
        t = m.strip()
        for prefix in ("Konteksts:", "Konteksts —", "Iespējams skaidrojums:", "Iespējams skaidrojums —"):
            if t.startswith(prefix):
                t = t[len(prefix):].strip()
                break
        if t:
            notes.append(t)
    ctx = ' · '.join(notes) if notes else None
    return (clean, ctx)


def _latvian_quotes(text: str | None) -> str | None:
    """Convert paired straight double-quotes to Latvian „..." style.

    Only applied to paraphrase text (summaries, stances) — verbatim
    quote fields are never normalized. Alternates open/close; if count
    is odd, trailing stray quote is left as-is.
    """
    if not text or '"' not in text:
        return text
    out: list[str] = []
    is_open = True
    for ch in text:
        if ch == '"':
            out.append("„" if is_open else "”")
            is_open = not is_open
        else:
            out.append(ch)
    return "".join(out)


# Sentence-boundary splitter for hero_excerpt: split AFTER terminal
# punctuation (. ! ? …) only when the next sentence starts with an
# uppercase letter (incl. LV diacritics) or an opening quote/paren.
# This keeps Latvian ordinal dates intact — "līdz 2028. gadam" vai
# "3. oktobra vēlēšanas" must NOT split at the digit period, or the
# excerpt could end "…līdz 2028." and look broken (the very bug this
# helper exists to fix). Trailing punctuation runs ("tiešām?!") stay
# attached to their sentence.
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?…])\s+(?=[A-ZĀČĒĢĪĶĻŅŠŪŽ„“\"(])")

# Clause-boundary characters for the soft mid-sentence truncation fallback.
_CLAUSE_PUNCT = (",", ";", "—", "–")


def _normalize_ws(text: str) -> str:
    """Collapse any whitespace run to a single space and strip ends."""
    return re.sub(r"\s+", " ", text).strip()


def _clause_truncate(text: str, limit: int) -> str:
    """Soft-truncate ``text`` at the last clause boundary before ``limit``,
    appending '…'. Boundaries are , ; — –. Falls back to a hard word-boundary
    cut (then a raw char cut) when no clause punctuation precedes the limit.
    Assumes ``len(text) > limit`` (caller guarantees an over-length input)."""
    window = text[:limit]
    cut = max(window.rfind(p) for p in _CLAUSE_PUNCT)
    if cut > 0:
        # Drop the clause punctuation itself, then any trailing space, add ellipsis.
        return window[:cut].rstrip() + "…"
    # No clause boundary — fall back to the last word boundary.
    sp = window.rfind(" ")
    if sp > 0:
        return window[:sp].rstrip() + "…"
    return window.rstrip() + "…"


def hero_excerpt(
    quote: str | None,
    stance: str | None,
    limit: int = 140,
) -> tuple[str, bool]:
    """Pick a homepage-hero fragment for a contradiction pane.

    Returns ``(text, is_quote)`` where ``is_quote`` says whether ``text`` is
    drawn from the verbatim ``quote`` (so the template can wrap it in Latvian
    quotation marks) rather than the paraphrased ``stance``.

    Selection order (first that yields non-empty text wins):
      a) ``quote`` fits whole within ``limit`` → ``(quote, True)``
      b) the leading run of FULL sentences from ``quote`` that together fit
         within ``limit`` → ``(sentences, True)``. Sentence boundaries are
         ``. ! ? …`` (terminal punctuation kept). A sentence that itself
         starts with a lowercase letter (a quote lifted from mid-sentence,
         e.g. "neviens cits neesot bijis…") is still valid when complete and
         is NOT discarded.
      c) ``stance`` fits whole within ``limit`` → ``(stance, False)``.
         Only consulted when (a) and (b) both produced nothing.
      d) soft clause-boundary truncation of ``quote`` (last ``, ; — –`` before
         ``limit``) + '…' → ``(fragment, True)``.
      e) the same clause truncation applied to ``stance`` → ``(fragment, False)``.
      f) both empty → ``('', False)``.

    Whitespace is normalized (any run → single space, ends stripped) before
    measuring. Sentence splitting is a simple regex — hero quotes are speech
    text, so abbreviation edge cases ("u.c.") are tolerated rather than solved.
    """
    q = _normalize_ws(quote or "")
    s = _normalize_ws(stance or "")

    if q:
        # (a) whole quote fits.
        if len(q) <= limit:
            return (q, True)
        # (b) leading full sentence(s) that fit together.
        sentences = [seg.strip() for seg in _SENTENCE_SPLIT_RE.split(q) if seg.strip()]
        acc = ""
        for seg in sentences:
            candidate = f"{acc} {seg}".strip() if acc else seg
            if len(candidate) <= limit:
                acc = candidate
            else:
                break
        # Only accept (b) if the accepted run actually ends on a sentence
        # boundary — a single over-long first sentence yields acc="" and we
        # fall through to (c)/(d).
        if acc and acc[-1] in ".!?…":
            return (acc, True)

    # (c) stance fits whole — only when quote gave nothing usable above.
    if s and len(s) <= limit:
        return (s, False)

    # (d) soft clause truncation of quote.
    if q:
        return (_clause_truncate(q, limit), True)

    # (e) soft clause truncation of stance.
    if s:
        return (_clause_truncate(s, limit), False)

    # (f) nothing to show.
    return ("", False)


def _photo_data_uri(slug: str) -> str | None:
    """Read `assets/photos/<slug>.jpg` and return a base64 data URI, or None."""
    path = ASSETS_DIR / "photos" / f"{slug}.jpg"
    if not path.exists():
        return None
    import base64
    return "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode()


# ── Cross-page domain helpers ───────────────────────────────────────


def _bill_slug(document_nr: str) -> str:
    """'1315/Lp14' -> '1315-lp14'.

    Used by `_fetch_bills` / `_fetch_bill_detail` (F3e bills.py target)
    and `_fetch_politician_detail` (F3b politicians.py — links a
    politician's involved bills back to their bill detail page).
    Promoted to `_common` so neither sub-page module imports from the
    other (F4 leaf rule).
    """
    return document_nr.lower().replace("/", "-")


def _get_last_activity(db: sqlite3.Connection, politician_id: int, politician_name: str = "") -> dict | None:
    """Get the most recent activity for a politician across all sources.

    Used by `_fetch_personas` (F3b personas.py target) and
    `_fetch_party_detail` (F3c parties.py target). Promoted to `_common`
    so personas + parties stay leaf-clean of each other.

    Returns the single most recent of: last claim, last Saeima vote,
    last X post (authored), last X mention, last news mention. None if
    none exists.
    """
    name_enc = _quote(politician_name, safe="")
    candidates: list[dict] = []

    # 1. Last claim (pozīcija)
    row = db.execute(
        "SELECT topic, source_url, stated_at FROM claims WHERE opponent_id = ? ORDER BY stated_at DESC LIMIT 1",
        (politician_id,),
    ).fetchone()
    if row:
        candidates.append({
            "date": _normalize_date(row["stated_at"]),
            "type": "claim",
            "label": row["topic"] or "Pozīcija",
            "source_url": row["source_url"] or "",
            "href": f"pozicijas.html?persona={name_enc}",
            "icon": "📌",
        })

    # 2. Last Saeima vote
    vote = db.execute("""
        SELECT sv.vote_date, sv.summary, sv.topic, siv.vote
        FROM saeima_individual_votes siv
        JOIN saeima_votes sv ON siv.vote_id = sv.id
        WHERE siv.politician_id = ?
        ORDER BY sv.vote_date DESC LIMIT 1
    """, (politician_id,)).fetchone()
    if vote:
        v = vote["vote"] or ""
        vote_label = {"Par": "Balsoja par", "Pret": "Balsoja pret", "Atturas": "Atturējās"}.get(v, "Balsoja")
        summary = (vote["summary"] or vote["topic"] or "")
        if len(summary) > 50:
            summary = summary[:47] + "…"
        candidates.append({
            "date": _normalize_date(vote["vote_date"]),
            "type": "vote",
            "label": f"{vote_label}: {summary}" if summary else vote_label,
            "source_url": "",
            "href": f"balsojumi.html?deputats={name_enc}",
            "icon": "🗳",
        })

    # 3. Last X post (authored by politician). Uses published_at (UTC ISO from
    # twikit, actual tweet post time) converted to LV-local, so cards show the
    # real post time — not the scrape run HH:MM that would collapse many
    # tweets onto the same minute. Matches _fetch_x_data (now in
    # src/render/x.py post-F3f.2; original ordering shipped in c197827).
    xpost = db.execute("""
        SELECT d.published_at, d.scraped_at, d.source_url FROM documents d
        JOIN document_politicians dp ON dp.document_id = d.id
        WHERE dp.politician_id = ? AND d.platform = 'twitter'
        ORDER BY COALESCE(d.published_at, d.scraped_at) DESC LIMIT 1
    """, (politician_id,)).fetchone()
    if xpost:
        candidates.append({
            "date": _format_tweet_time(xpost["published_at"], xpost["scraped_at"]),
            "type": "x_post",
            "label": "Rakstīja X",
            "source_url": xpost["source_url"] or "",
            "href": f"x.html?persona={name_enc}",
            "icon": "𝕏",
        })

    # 4. Last X mention — same published_at preference as xpost.
    xmention = db.execute("""
        SELECT d.published_at, d.scraped_at, d.source_url FROM documents d
        JOIN document_politicians dp ON dp.document_id = d.id
        WHERE dp.politician_id = ? AND dp.role = 'mention_target' AND d.platform = 'x_mention'
        ORDER BY COALESCE(d.published_at, d.scraped_at) DESC LIMIT 1
    """, (politician_id,)).fetchone()
    if xmention:
        candidates.append({
            "date": _format_tweet_time(xmention["published_at"], xmention["scraped_at"]),
            "type": "x_mention",
            "label": "Pieminēts X",
            "source_url": xmention["source_url"] or "",
            "href": f"x.html?persona={name_enc}&tab=mentions",
            "icon": "𝕏",
        })

    # 5. Last news mention
    news = db.execute("""
        SELECT d.scraped_at, d.source_url, d.source_domain FROM documents d
        JOIN document_politicians dp ON dp.document_id = d.id
        WHERE dp.politician_id = ? AND d.platform = 'web'
        ORDER BY d.scraped_at DESC LIMIT 1
    """, (politician_id,)).fetchone()
    if news:
        domain = (news["source_domain"] or "ziņas").replace("www.", "")
        candidates.append({
            "date": _normalize_date(news["scraped_at"]),
            "type": "news",
            "label": f"Pieminēts: {domain}",
            "source_url": news["source_url"] or "",
            "href": f"zinas.html?persona={name_enc}",
            "icon": "📰",
        })

    if not candidates:
        return None

    # Pick most recent by date
    candidates.sort(key=lambda c: c["date"], reverse=True)
    return candidates[0]


def _source_to_internal_link(source_url: str, politician_name: str, db: sqlite3.Connection) -> str | None:
    """Map an external source URL to an internal site link."""
    if not source_url:
        return None
    if "x.com" in source_url or "twitter.com" in source_url:
        return f"x.html?persona={_quote(politician_name)}"
    if "SaeimaLIVS" in source_url:
        vote = db.execute("SELECT id FROM saeima_votes WHERE url = ?", (source_url,)).fetchone()
        if vote:
            return f"balsojumi.html#vote-{vote['id']}"
    # Web news sources → ziņas page
    if source_url.startswith("http"):
        return f"zinas.html?persona={_quote(politician_name)}"
    return None


def _enrich_contradiction(d: dict[str, Any], db: sqlite3.Connection) -> None:
    """In-place enrichment for a contradiction row.

    Input dict must already contain: severity, politician_name, party,
    old_date, new_date, old_source, new_source. After this call the dict
    also has: severity_lv, slug, party_short, party_color, old_link,
    new_link, vote_summary, vote_id, severity_glyph, initials,
    old_source_domain, new_source_domain, delta_days. Dates are trimmed
    to 10-char ISO format.

    Safe to call on rows that already carry the SELECT-widened columns
    (salience, role, old_quote, new_quote) — those pass through.
    """
    # Contract: callers must supply the source columns this helper reads.
    for _k in ("severity", "politician_name", "old_date", "new_date"):
        if _k not in d:
            raise KeyError(f"_enrich_contradiction requires {_k!r} on input dict")
    d["severity_lv"] = SEVERITY_LV.get(d["severity"], d["severity"] or "")
    d["slug"] = _slugify(d["politician_name"])
    party = d.get("party") or ""
    d["party_short"] = _party_short_name(party) if party else ""
    d["party_color"] = PARTY_COLORS.get(party, "#8b8fa3")
    # Date trim must run before _delta_days so the delta uses normalized inputs.
    for key in ("old_date", "new_date"):
        if d[key] and len(d[key]) >= 10:
            d[key] = d[key][:10]
    # Chronological ordering: the left panel ("old" slot) must be the earlier
    # stated_at. DB old/new reflect detection order (contradiction-hunter pairs),
    # which can flip when saeima-tracker backfills a vote against an already-
    # stored public statement (e.g., pretruna #13 Mieriņa).
    old_d = d.get("old_date") or ""
    new_d = d.get("new_date") or ""
    if old_d and new_d and old_d > new_d:
        for k in ("stance", "date", "source", "quote", "claim_type"):
            ok, nk = f"old_{k}", f"new_{k}"
            d[ok], d[nk] = d.get(nk), d.get(ok)
    # Category label derived from the claim_type pair (order-independent).
    # Drives the main badge text; severity still drives color via CSS class.
    old_ct = d.get("old_claim_type") or "position"
    new_ct = d.get("new_claim_type") or "position"
    d["category"] = "_".join(sorted([old_ct, new_ct]))
    d["category_label"] = CATEGORY_LV.get(d["category"], d["severity_lv"])
    # Panel labels: chronological for same-type pairs, claim-type-named for mixed.
    if old_ct == new_ct:
        d["old_label"] = "Iepriekš"
        d["new_label"] = "Pašlaik"
    else:
        d["old_label"] = CLAIM_TYPE_LABEL.get(old_ct, "Iepriekš")
        d["new_label"] = CLAIM_TYPE_LABEL.get(new_ct, "Pašlaik")
    d["old_link"] = _source_to_internal_link(d.get("old_source"), d["politician_name"], db)
    d["new_link"] = _source_to_internal_link(d.get("new_source"), d["politician_name"], db)
    d["vote_summary"] = None
    d["vote_id"] = None
    if d.get("new_source") and "SaeimaLIVS" in (d["new_source"] or ""):
        vote = db.execute(
            "SELECT id, summary FROM saeima_votes WHERE url = ?",
            (d["new_source"],),
        ).fetchone()
        if vote:
            d["vote_summary"] = vote["summary"]
            d["vote_id"] = vote["id"]
    d["severity_glyph"] = _SEVERITY_GLYPHS.get(d["severity"], "·")
    d["initials"] = _initials_from_name(d["politician_name"])
    d["has_photo"] = (ASSETS_DIR / "photos" / f"{d['slug']}.jpg").exists()
    d["old_source_domain"] = _domain_from_url(d.get("old_source"))
    d["new_source_domain"] = _domain_from_url(d.get("new_source"))
    d["delta_days"] = _delta_days(d.get("old_date"), d.get("new_date"))
    # Normalize paraphrase text to Latvian-style quotes; leave verbatim quotes alone.
    for key in ("summary", "old_stance", "new_stance"):
        if key in d:
            d[key] = _latvian_quotes(d[key])
    # Lift bracketed context notes out of summary so the UI can render them
    # as a distinct block rather than inline square brackets.
    clean, ctx = _split_summary(d.get("summary"))
    d["summary"] = clean
    d["context_note"] = ctx


# ── Sidecar JSON emission ───────────────────────────────────────────


def _emit_json_compressed(payload: bytes, dest: Path) -> Path:
    """Write ``payload`` to ``dest`` plus pre-compressed ``.br``/``.gz`` siblings.

    Shared compress-and-write core for the render package's JSON sidecars
    (pozicijas-data, balsojumi-matrica, saites-data, sg-index). Callers pass
    the already-encoded ``payload`` bytes and the ``.json`` destination path;
    this writes ``dest``, ``dest + ".br"`` (brotli quality 11) and
    ``dest + ".gz"`` (gzip level 9). Brotli + gzip variants let the htaccess
    ``*.json`` rewrite pick the best for the Accept-Encoding header on the
    LiteSpeed shared host, which does not auto-compress application/json.
    Idempotent — overwrites each render. Does NOT create parent dirs or log;
    callers own ``mkdir`` and any ``logger.info``. Returns ``dest``.
    """
    dest.write_bytes(payload)
    dest.with_suffix(dest.suffix + ".br").write_bytes(_brotli.compress(payload, quality=11))
    dest.with_suffix(dest.suffix + ".gz").write_bytes(_gzip.compress(payload, compresslevel=9))
    return dest


# ── Asset versioning + downloads ────────────────────────────────────


def _download_chart_js(dest: Path) -> None:
    """Download Chart.js from CDN.

    Used by `generate_public_site` (index page chart) AND
    `generate_statistika` (CSP dashboard charts). Promoted to `_common`
    so the F3d statistika.py module does not have to back-import from
    src.generate (cycle).
    """
    try:
        import httpx
        resp = httpx.get(
            "https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js",
            follow_redirects=True,
            timeout=30,
        )
        resp.raise_for_status()
        dest.write_bytes(resp.content)
        _logger.info("Downloaded chart.min.js")
    except Exception as e:
        _logger.warning("Could not download chart.min.js: %s", e)
        # Write a stub so the page doesn't break
        dest.write_text(
            "// Chart.js not available — download from https://cdn.jsdelivr.net/npm/chart.js@4\n"
            "window.Chart = window.Chart || function() { console.warn('Chart.js not loaded'); };\n",
            encoding="utf-8",
        )


def _download_annotation_plugin(dest: Path) -> None:
    """Download chartjs-plugin-annotation from CDN.

    Used by `generate_public_site` AND `generate_statistika` — same
    rationale as `_download_chart_js`.
    """
    try:
        import httpx
        resp = httpx.get(
            "https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3/dist/chartjs-plugin-annotation.min.js",
            follow_redirects=True,
            timeout=30,
        )
        resp.raise_for_status()
        dest.write_bytes(resp.content)
        _logger.info("Downloaded chartjs-plugin-annotation.min.js")
    except Exception as e:
        _logger.warning("Could not download chartjs-plugin-annotation.min.js: %s", e)
        dest.write_text("/* chartjs-plugin-annotation unavailable */", encoding="utf-8")


def _resolve_assets_version() -> str:
    """Cache-bust version string for `?v=` query on style.css + every top-level assets/*.js.

    Defaults to ``max(mtime)`` across the versioned assets — Opera and
    some Chromium builds were serving a stale ``style.css`` against
    fresh HTML, leaving new hero-v2 classes unstyled. Picking max(mtime)
    across the bundle means a JS-only change still busts every ``?v=``
    query.

    Override via the ``ATMINA_ASSETS_VERSION`` env var to force a stable
    value — used by ``tests/test_render_chars.py`` so HTML byte-baselines
    do not drift on a fresh worktree where assets/* mtimes are
    arbitrary timestamps from the checkout.

    Empty-string semantics: ``ATMINA_ASSETS_VERSION=""`` is treated as
    unset and falls through to mtime. To force a literal empty/zero
    cache-bust value, set the variable to ``"0"`` (or any non-empty
    token); only truthy strings short-circuit the fallback.
    """
    forced = os.environ.get("ATMINA_ASSETS_VERSION")
    if forced:
        return forced
    # style.css + every top-level *.js in assets/ (glob so new JS files are
    # auto-versioned without touching this list). The cuelume/ subdir is
    # intentionally NOT versioned — it is imported by module URL, not a ?v= tag.
    versioned = [ASSETS_DIR / "style.css", *sorted(ASSETS_DIR.glob("*.js"))]
    mtimes = [int(p.stat().st_mtime) for p in versioned if p.exists()]
    return str(max(mtimes)) if mtimes else "0"


# ── Page primitive ──────────────────────────────────────────────────


def _render_page(
    env: Environment,
    template_name: str,
    output_path: Path,
    context: dict[str, Any],
) -> None:
    """Render a Jinja2 template to a file.

    Auto-injects ``canonical_url`` into the template context based on the
    path of ``output_path`` relative to the deploy root (the last ``atmina``
    directory in the path). Callers can override by setting ``canonical_url``
    in ``context`` explicitly.
    """
    if "canonical_url" not in context:
        parts = output_path.parts
        for i in range(len(parts) - 1, -1, -1):
            if parts[i] == "atmina":
                rel = "/".join(parts[i + 1:])
                canonical = f"{BASE_URL}/{rel}"
                if canonical.endswith("/index.html"):
                    canonical = canonical[: -len("index.html")]
                context["canonical_url"] = canonical
                break
    template = env.get_template(template_name)
    html = template.render(**context)
    output_path.write_text(html, encoding="utf-8")
