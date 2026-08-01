"""Text quality guardrails for atmina write boundaries.

Validates that Latvian text fields preserve diacritics. Prevents agent
context-drift from silently corrupting the database with stripped text
(see docs/ for the 2026-04-16 incident analysis).
"""

import logging

logger = logging.getLogger(__name__)

# One-shot flag so the "fasttext unavailable → gate degraded" warning is stated
# once per process instead of once per validated string (this runs in bulk loops).
_FT_UNAVAILABLE_WARNED = False

LV_DIACRIT = set("āēīūņļķģšžčĀĒĪŪŅĻĶĢŠŽČ")

# Strip table: maps each Latvian diacritic to its ASCII equivalent.
# Used to detect stopwords whether the input has diacritics or not.
_STRIP_DIACRITICS = str.maketrans(
    "āčēģīķļņōŗšūžĀČĒĢĪĶĻŅŌŖŠŪŽ",
    "acegiklnorsuzACEGIKLNORSUZ",
)

# Common Latvian function words (stored in diacritic-stripped form so we
# match against the stripped text uniformly).
LV_STOPWORDS = {
    "un", "ar", "kas", "no", "uz", "par", "lai", "ka", "bet", "tikai",
    "ir", "tas", "ta", "vai", "nav", "var", "tad", "tam", "tos", "tik",
    "kur", "kad", "kam", "ko", "to", "tie", "ari", "pec",
    "pirms", "starp", "caur", "lidz", "bez", "pret", "zem", "virs",
    "del", "tikko", "vel", "jau", "tomer", "tomet", "ne", "jo",
    "vinas", "vinu", "vins", "vini", "musu", "jusu", "savu", "savs",
    "ari", "tikko",
}

# Distinctive Latvian word-ending fingerprints (stripped form). These
# don't appear in English and rarely in other Latin-script languages.
# Used as a secondary Latvian-ness signal when stopwords are sparse
# (terse headlines, summary briefs).
LV_DISTINCTIVE_ENDINGS = (
    "ums", "iba", "iem", "asanu", "asanas", "asana", "ais", "isim",
    "ajiem", "ojam", "ojot", "asot", "ana", "anas", "iba", "ibas",
    "saanu", "ssana", "asana",
)

# English-distinctive markers that do not overlap with Latvian vocabulary.
# Used to detect predominantly English text so we skip Latvian diacritic
# validation (false-positive source: Rinkēvičs/Braže post in English, our
# LV stopword "to" also happens to be the English preposition).
EN_MARKERS = {
    "the", "and", "is", "are", "was", "were", "been", "being",
    "of", "for", "with", "from", "this", "that", "these", "those",
    "have", "has", "had", "will", "would", "could", "should",
    "which", "what", "when", "where", "who", "whose",
    "it", "its", "he", "his", "she", "her", "they", "them", "their",
    "we", "our", "you", "your", "my", "me",
    "or", "but", "not", "new", "now", "by", "as", "an",
    "if", "so", "do", "does", "did", "done",
    "there", "here", "such", "only", "also", "just",
    "about", "after", "before", "between", "into", "onto",
    "still", "then", "than", "because",
    # 2026-04-23 expansion: tokens missed by the original set that caused
    # false-positives on English tweets (e.g. M. Krusts's 'Latvian exports
    # to Russia remain at 70.5 million...' — contained 'to' twice hitting
    # LV_STOPWORDS but only 'this' as an EN marker).
    "at", "while", "already", "yet", "ever", "never",
    "most", "more", "less", "few", "many", "much", "some", "all",
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "times", "time", "remain", "remains", "fall", "falls", "rise", "rises",
    "reach", "reaches", "become", "becomes", "continues", "continue",
    "keep", "keeps", "every", "each", "own", "same", "other", "another",
    "both", "per", "via", "against", "across", "during", "within",
    "without", "through", "over", "under", "above", "below",
}


def validate_lv_diacritics(
    text: str | None,
    *,
    min_letters: int = 40,
    ratio_threshold: float = 0.015,
    min_lv_markers: int = 2,
) -> tuple[bool, str]:
    """Validate that a Latvian text field has plausible diacritic ratio.

    Returns ``(ok, reason)``. Designed to be called at write boundaries
    (``store_claim``, ``store_analysis``, ``store_tension``,
    ``store_context_note``) to refuse writes that look like agent
    context-drift output (Latvian text with diacritics stripped).

    Skips validation for:
      - empty / very short text (cannot reliably classify)
      - Cyrillic-heavy text (Russian)
      - text without enough Latvian function-word markers (English, brand names)

    For text classified as Latvian, requires diacritic ratio above
    ``ratio_threshold`` (default 1.5%). Genuine Latvian prose runs ~5-15%.
    """
    if not text:
        return True, "empty"
    text = str(text)
    letters = sum(1 for c in text if c.isalpha())
    if letters < min_letters:
        return True, "too short to classify"

    # Primary language-ID via fasttext (added 2026-04-23). Confident non-LV
    # classifications short-circuit the token-matcher, fixing false-positives
    # where short English tweets tripped the LV_STOPWORDS 'to'/'no' overlap.
    # Stripped Latvian ('Daudz tiek runats...') is misclassified by fasttext
    # as fr/sr/hr at LOW confidence (<0.50), so the 0.70 threshold preserves
    # the guardrail: stripped LV falls through to the token matcher and
    # gets correctly rejected below.
    ft_lang: str | None = None
    try:
        from src.ingest import _detect_language
        lang, conf = _detect_language(text)
        ft_lang = lang
        if lang in ("en", "ru", "de", "fr", "es", "pl", "it") and conf >= 0.70:
            return True, f"non-Latvian per fasttext ({lang} {conf:.2f})"
    except Exception as exc:
        # fasttext unavailable (model download error, import issue) — fall
        # through to the token matcher, as src/ingest.py::_get_ft_model does.
        #
        # But NOT silently. With `ft_lang is None` the marker escape at the
        # bottom of this function is granted regardless of diacritics, so the
        # one input class this gate exists to catch — fully de-diacritised
        # Latvian, i.e. T4 context drift — walks straight through at a WRITE
        # boundary. The gate degrades OPEN, and a gate that opens without
        # saying so is the "silent success" class (CLAUDE.md § Working
        # Conventions). The repair is a reliable model load (BACKLOG §
        # fasttext lid-modeļa pārejoša nepieejamība), never new language
        # detection here. Warn once per process: this runs in bulk loops.
        global _FT_UNAVAILABLE_WARNED
        if not _FT_UNAVAILABLE_WARNED:
            _FT_UNAVAILABLE_WARNED = True
            logger.warning(
                "validate_lv_diacritics: fasttext lang-ID unavailable (%s) — "
                "the diacritic gate is DEGRADED (stripped-Latvian detection is "
                "off) for the rest of this process",
                exc,
            )

    # Skip Cyrillic-heavy text (Russian quotes from politicians)
    cyrillic = sum(1 for c in text if "А" <= c <= "я" or c in "ёЁ")
    if cyrillic / letters > 0.3:
        return True, "non-Latvian (Cyrillic)"

    # Require Latvian-ness. Combine two signals (both work on stripped text):
    #   1) Common function words (un, ar, kas, ...).
    #   2) Distinctive Latvian word endings (-ums, -iba, -asanu, ...) that
    #      don't appear in English/Russian/brand names.
    words = [
        w.strip(".,;:!?\"'()[]").translate(_STRIP_DIACRITICS)
        for w in text.lower().split()
    ]
    stopword_hits = sum(1 for w in words if w in LV_STOPWORDS)
    ending_hits = sum(
        1 for w in words
        if len(w) >= 5 and any(w.endswith(end) for end in LV_DISTINCTIVE_ENDINGS)
    )
    lv_score = stopword_hits + ending_hits

    # Computed up here because the marker escape below needs it: zero diacritics
    # is the stripping signature, and telling that apart from merely
    # diacritic-light Latvian is the difference between catching context drift
    # and refusing a legitimate claim at a write boundary.
    diacrit_count = sum(1 for c in text if c in LV_DIACRIT)

    # Skip predominantly English text (Rinkēvičs/Braže etc. post in English).
    # LV stopwords overlap slightly with English ("to", "no") which inflates
    # lv_score for English text. Combine two English signals:
    #   (a) EN function words (the, and, is, ...) outnumber LV markers
    #   (b) EN-distinctive word endings (-ing, -tion, -ed) present at all,
    #       since these don't occur in Latvian morphology
    en_hits = sum(1 for w in words if w in EN_MARKERS)
    en_ending_hits = sum(
        1 for w in words
        if len(w) >= 4 and (
            w.endswith("ing") or w.endswith("tion") or w.endswith("ed")
            or w.endswith("ly") or w.endswith("ness")
        )
    )
    # ...UNLESS fasttext already called it Latvian. The EN branches exist to
    # rescue genuinely English text from the LV_STOPWORDS 'to'/'no' overlap —
    # they must never overrule a positive `lv` verdict, at ANY confidence.
    #
    # This gap shipped 11 fully de-diacritised stances to the live site
    # (2026-04-09..04-16, fixed 2026-08-02). fasttext returned ('lv', 0.32) for
    # them — below the 0.70 short-circuit above, so execution reached here — and
    # short stances dense with acronyms (IT, SM, VK, EM, NA, AS) pushed
    # `en_hits >= lv_score`, so the gate returned OK on text that was 0%
    # diacritics. Note the direction: fasttext being UNSURE is not evidence of
    # English, and stripped Latvian is exactly the input it is least sure about.
    if ft_lang != "lv":
        if en_hits >= 2 and en_hits >= lv_score:
            return True, f"non-Latvian (English — {en_hits} EN markers vs {lv_score} LV)"
        if en_hits >= 1 and en_ending_hits >= 1 and ending_hits == 0:
            return True, (
                f"non-Latvian (English — {en_hits} markers + {en_ending_hits} EN endings, "
                "no LV endings)"
            )

    # This escape — not the EN branch — is what actually let 10 of the 11
    # stripped stances through (measured 2026-08-02; the earlier diagnosis
    # blamed the EN branch and was wrong). The heuristic counts function words
    # and distinctive endings, and a short noun-dense stance ("Atsedz Rigas
    # Siltuma valdes locekles 7 dienu komandejumu...") scores 0-1, so it exited
    # here as "probably not Latvian" and never reached the ratio check — the
    # only test that can see stripping at all.
    #
    # It is now withheld only for the exact stripping signature: ZERO diacritics
    # in a text long enough to classify. Rationale for each half —
    #   * fasttext being UNSURE is not evidence of NOT-Latvian. Stripped Latvian
    #     is precisely the input it is least sure about; it returned fr/lt/pl/sl/ur
    #     at 0.13-0.19 for these eleven. So an unconfident verdict must not buy
    #     an escape that only the absence of LV markers justifies.
    #   * requiring zero, not "below the ratio", keeps naturally diacritic-light
    #     Latvian safe. Claim #1563 ("Panācis Satversmes tiesas spriedumu — krievu
    #     valoda sabiedriskajos medijos neatbilst Satversmei") is correct Latvian
    #     with 1 diacritic in 84 letters = 1.19%, under the 1.5% floor. An earlier
    #     version of this fix rejected it — a real false positive on a legitimate
    #     claim, which at a write boundary means a refused row, not a warning.
    # Genuine English is unaffected: it short-circuits at fasttext >=0.70, and
    # low-confidence English still exits via the EN branches above.
    if lv_score < min_lv_markers and (ft_lang is None or diacrit_count > 0):
        return True, (
            f"not enough Latvian markers ({stopword_hits} stopwords + "
            f"{ending_hits} distinctive endings)"
        )

    # It IS Latvian — diacritic ratio MUST be plausible
    diacrit = diacrit_count
    ratio = diacrit / letters
    if ratio < ratio_threshold:
        reason = (
            f"Latvian text but only {diacrit}/{letters} = {ratio:.1%} "
            f"diacritics — likely stripped (agent context-drift?)"
        )
        logger.warning("validate_lv_diacritics rejected: %s — text[:80]=%r", reason, text[:80])
        return False, reason
    return True, "ok"


def restore_text_from_source(
    stripped: str | None,
    source: str | None,
    *,
    min_length: int = 10,
) -> str | None:
    """Restore diacritics in stripped Latvian text by matching against source.

    When the agent emits a quote without diacritics but the source document
    preserves them (verified for X tweets, news articles, Saeima records),
    we can recover the original by:
      1. Strip diacritics from both quote and source.
      2. Find the stripped quote as a substring in the stripped source
         (case-insensitive).
      3. Extract from the *original* source at the matched position.

    Returns the restored text on success, ``None`` if no match (paraphrased
    quote, or source/quote diverged).

    The diacritic-strip translation is 1-to-1 character mapping, so positions
    are preserved between stripped and original — slicing the original at the
    match position yields the correctly diacritic-bearing version.

    ``min_length`` rejects very short fragments that could match coincidentally
    anywhere in the source.
    """
    if not stripped or not source:
        return None
    if len(stripped) < min_length:
        return None

    stripped_normalized = stripped.translate(_STRIP_DIACRITICS).lower()
    source_normalized = source.translate(_STRIP_DIACRITICS).lower()

    pos = source_normalized.find(stripped_normalized)
    if pos == -1:
        return None

    # Length-preserving extraction from original (with diacritics)
    return source[pos:pos + len(stripped)]


def validate_quote_against_source(
    quote: str | None, source: str | None
) -> tuple[bool, str]:
    """Validate a VERBATIM quote by comparing it to the source document.

    Returns ``(ok, reason)``. This is the right question to ask of
    ``claims.quote``, where ``validate_lv_diacritics`` asks the wrong one:
    CLAUDE.md makes the quote verbatim and the diacritic gate a check on OUR
    words, so a ratio test on a citation both refuses authentic low-diacritic
    Latvian (claim #555664 — and refusing meant storing no quote, silently
    dropping provenance) and passes a diacritic-rich sentence with one damaged
    word (a ratio cannot see a single character).

    Rejects EXACTLY ONE condition: the quote is absent from the source but
    present once diacritics are folded away. That difference can only be
    diacritics, so the stored text is provably not what the document says —
    either we stripped a mark, or we "corrected" the speaker's own spelling,
    and CLAUDE.md forbids both. The reason carries the source wording, because
    the fix is always to restore it.

    Deliberately does NOT reject when the quote is simply absent. Measured over
    the live DB (2026-08-03, 4735 checkable rows): 1408 quotes do not match on
    a character-exact basis — English quotes, elisions marked ``(..)``,
    typographic-quote differences, and re-fetched bodies whose wording changed.
    Rejecting those would block real claims at a write boundary, so "cannot
    verify" resolves to allow.

    Case differences alone are allowed too (45 live rows): extractors routinely
    capitalise the first letter of a mid-sentence fragment, which is a quoting
    convention, not a corruption.

    Scope note: this reuses ``restore_text_from_source``, whose match is
    character-exact modulo diacritics and case. That is stricter than a
    punctuation-normalising comparison and so catches 20 of the 31 live
    corruptions rather than all 31 — the 11 it misses differ in punctuation or
    whitespace as well, where the source span cannot be identified with
    confidence. The miss direction is deliberate: this gate refuses only what
    it can prove.
    """
    if not quote or not source:
        return True, "no quote or no source to compare against"

    restored = restore_text_from_source(quote, source)
    if restored is None:
        return True, "quote not located in source (cannot verify)"
    if restored == quote:
        return True, "verbatim"
    if restored.lower() == quote.lower():
        return True, "differs only in capitalisation"

    return False, (
        f"quote differs from the source document by diacritics only — the "
        f"document says {restored!r}, not {quote!r}. A quote is VERBATIM "
        f"(CLAUDE.md): restore the source wording rather than editing it."
    )
