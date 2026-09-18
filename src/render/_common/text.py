"""``_common`` teksta apstrāde — kopsavilkumu dalīšana, pēdiņas, izvilkumi.

Izgriezts no vienfaila ``src/render/_common.py`` 2026-09-05 (plāna 5.8).
Tīri teksta lapu-funkcijas: bez DB, bez konstantēm, bez māsu-moduļiem.
"""

from __future__ import annotations

import re

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
