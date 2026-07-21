"""Text quality guardrails for atmina write boundaries.

Validates that Latvian text fields preserve diacritics. Prevents agent
context-drift from silently corrupting the database with stripped text
(see docs/ for the 2026-04-16 incident analysis).
"""

import logging

logger = logging.getLogger(__name__)

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
    try:
        from src.ingest import _detect_language
        lang, conf = _detect_language(text)
        if lang in ("en", "ru", "de", "fr", "es", "pl", "it") and conf >= 0.70:
            return True, f"non-Latvian per fasttext ({lang} {conf:.2f})"
    except Exception:
        # fasttext unavailable (model download error, import issue) —
        # silently fall through to the token matcher. Matches the tolerant
        # pattern used at src/ingest.py::_get_ft_model.
        pass

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
    if en_hits >= 2 and en_hits >= lv_score:
        return True, f"non-Latvian (English — {en_hits} EN markers vs {lv_score} LV)"
    if en_hits >= 1 and en_ending_hits >= 1 and ending_hits == 0:
        return True, f"non-Latvian (English — {en_hits} markers + {en_ending_hits} EN endings, no LV endings)"

    if lv_score < min_lv_markers:
        return True, (
            f"not enough Latvian markers ({stopword_hits} stopwords + "
            f"{ending_hits} distinctive endings)"
        )

    # It IS Latvian — diacritic ratio MUST be plausible
    diacrit = sum(1 for c in text if c in LV_DIACRIT)
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
