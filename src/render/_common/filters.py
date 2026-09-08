"""``_common`` drošības + Jinja filtri un markdown satura palīgi.

Izgriezts no vienfaila ``src/render/_common.py`` 2026-09-05 (plāna 5.8).
Atkarīgs tikai no ``constants`` (``WIKI_DIR``) — nekādu māsu-moduļu
``src.render.*`` importu (``src/render/__init__.py:22-30``).
"""

from __future__ import annotations

import json
import re
from typing import Optional

import bleach
import markdown
import yaml
from markupsafe import Markup

from src.render._common.constants import WIKI_DIR

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


def _wrap_tables(html: str) -> str:
    """Wrap top-level tables in local horizontal-scroll containers."""
    out: list[str] = []
    pos = 0
    lower = html.lower()
    while True:
        start = lower.find("<table", pos)
        if start == -1:
            out.append(html[pos:])
            break
        depth = 0
        i = start
        end = -1
        while i < len(html):
            if lower.startswith("<table", i):
                depth += 1
                i += 6
            elif lower.startswith("</table>", i):
                depth -= 1
                i += 8
                if depth == 0:
                    end = i
                    break
            else:
                i += 1
        if end == -1:
            out.append(html[pos:])
            break
        preceding = html[pos:start]
        if re.search(r'class="[^"]*table-scroll[^"]*"[^>]*>\s*$', preceding):
            out.append(html[pos:end])
        else:
            out.append(html[pos:start])
            out.append('<div class="table-scroll">')
            out.append(html[start:end])
            out.append("</div>")
        pos = end
    return "".join(out)


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
    back-import from the then-monolithic renderer (F3-prep
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


def _salience_label(value: object) -> str:
    """Pretrunas ``salience`` (0–1) → lasītājam saprotams vārds.

    Sliekšņi: ≥0.7 «augsta», ≥0.5 «vidēja», citādi «zema». 0.5 ir tas pats
    slieksnis, ko profila Pārskata bloks B lieto atlasei (``salience>=0.5``),
    tāpēc «vidēja» un «augsta» = bloka B tvērums. Kailais skaitlis kartītē
    lasītājam neko neteica (2026-09-06 lēmums); detaļu lapa skaitli patur
    iekavās. Registered as Jinja filter ``salience_label``.
    """
    try:
        v = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return ""
    if v >= 0.7:
        return "augsta"
    if v >= 0.5:
        return "vidēja"
    return "zema"


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
