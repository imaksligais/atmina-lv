"""Unit tests for ``src.render._common.hero_excerpt``.

The homepage hero "Uzmanības centrā" panes used to chop quotes with
``|truncate(120)``, producing mid-word fragments ("Esmu…", "…un tikai…").
``hero_excerpt`` replaces that with sentence-boundary-aware selection plus a
stance fallback and soft clause truncation. These tests pin each selection
branch (a–f) with exact expected strings.
"""

from __future__ import annotations

from src.render._common import hero_excerpt


def test_a_short_quote_returned_whole():
    """(a) A quote that fits within the limit is returned verbatim as a quote."""
    q = "Esmu gatavs uzņemties atbildību."
    assert hero_excerpt(q, "kaut kāda parafrāze", 140) == (q, True)


def test_b_first_full_sentences_kept():
    """(b) An over-length quote yields its leading run of FULL sentences that
    together fit. Here the first two sentences fit (135 chars), the third
    ("Esmu gatavs…") would overflow → it is dropped."""
    q = (
        "Aicinu Valsts prezidentu izteikt premjerei Siliņai neuzticību! "
        "Latvijai ir vajadzīga rīcībspējīga un atbildīga valdība, kas spēj rīkoties! "
        "Esmu gatavs uzņemties atbildību par valsts nākotni un drošību."
    )
    assert len(q) > 140  # guard: must exercise (b), not (a)
    text, is_quote = hero_excerpt(q, None, 140)
    assert is_quote is True
    assert text == (
        "Aicinu Valsts prezidentu izteikt premjerei Siliņai neuzticību! "
        "Latvijai ir vajadzīga rīcībspējīga un atbildīga valdība, kas spēj rīkoties!"
    )
    assert len(text) <= 140
    # Ends on a sentence boundary, not mid-word.
    assert text.endswith("!")


def test_b_only_first_sentence_when_second_overflows():
    """(b) When only the first sentence fits, just that sentence is returned."""
    q = (
        "Latvijai ir vajadzīga rīcībspējīga un atbildīga valdība! "
        "Tieši tāpēc es aicinu visus koalīcijas partnerus nekavējoties atbalstīt "
        "šo iniciatīvu un rīkoties saskaņoti."
    )
    assert len(q) > 140
    text, is_quote = hero_excerpt(q, None, 140)
    assert (text, is_quote) == (
        "Latvijai ir vajadzīga rīcībspējīga un atbildīga valdība!",
        True,
    )


def test_b_lowercase_midsentence_quote_kept():
    """(b) A quote lifted from mid-sentence (starts lowercase) is NOT discarded
    when it forms a complete sentence within the limit."""
    q = (
        "neviens cits neesot bijis informēts par šo lēmumu. "
        "Tas ir absolūti nepieņemami un prasa tūlītēju un rūpīgu izmeklēšanu "
        "no visu atbildīgo institūciju puses."
    )
    assert len(q) > 140
    text, is_quote = hero_excerpt(q, None, 140)
    assert (text, is_quote) == (
        "neviens cits neesot bijis informēts par šo lēmumu.",
        True,
    )


def test_c_stance_fallback_when_quote_has_no_sentence_end():
    """(c) Quote is over-length and has NO sentence boundary, so (a)+(b) give
    nothing; the stance fits → it is returned (is_quote False)."""
    q = (
        "un tikai tad kad visi būs vienisprātis par šo jautājumu mēs varēsim "
        "virzīties uz priekšu ar konkrētiem soļiem un reālu rīcību bez liekas kavēšanās"
    )
    stance = "Atbalsta reformu tikai ar nosacījumiem."
    assert len(q) > 140
    assert hero_excerpt(q, stance, 140) == (stance, False)


def test_d_quote_clause_truncation_when_both_long():
    """(d) Quote over-length with no sentence end AND stance over-length →
    soft clause-boundary truncation of the quote, ending in '…'."""
    q = (
        "un tikai tad kad visi būs vienisprātis par šo jautājumu mēs varēsim "
        "virzīties uz priekšu ar konkrētiem soļiem un reālu rīcību bez liekas kavēšanās"
    )
    text, is_quote = hero_excerpt(q, None, 140)
    assert is_quote is True
    assert text.endswith("…")
    assert len(text) <= 141  # 140 window + ellipsis
    # Cut at a clause/word boundary — no partial word before the ellipsis.
    assert text == (
        "un tikai tad kad visi būs vienisprātis par šo jautājumu mēs varēsim "
        "virzīties uz priekšu ar konkrētiem soļiem un reālu rīcību bez liekas…"
    )


def test_e_stance_clause_truncation_when_quote_empty():
    """(e) No quote at all, stance over-length → soft clause truncation of
    the stance, is_quote False."""
    stance = (
        "Politiķis uzsver, ka reforma jāatbalsta tikai ar stingriem "
        "nosacījumiem, kas garantē caurspīdīgumu, atbildību un sabiedrības "
        "interešu aizsardzību ilgtermiņā."
    )
    assert len(stance) > 140
    text, is_quote = hero_excerpt(None, stance, 140)
    assert is_quote is False
    assert text.endswith("…")
    assert len(text) <= 141


def test_f_both_empty():
    """(f) Both inputs empty/None → ('', False)."""
    assert hero_excerpt(None, None) == ("", False)
    assert hero_excerpt("", "") == ("", False)
    assert hero_excerpt("   ", "  \n ") == ("", False)


def test_whitespace_is_normalized():
    """Internal whitespace runs collapse to a single space; ends are stripped."""
    q = "  Esmu   gatavs\n\nuzņemties    atbildību.  "
    assert hero_excerpt(q, None, 140) == ("Esmu gatavs uzņemties atbildību.", True)


def test_latvian_ordinal_dates_do_not_split_sentences():
    """Digit periods in Latvian ordinal dates ("2028. gadam", "3. oktobra")
    are NOT sentence boundaries — the splitter only breaks before an
    uppercase/quote-opening next sentence. Without this, an excerpt could
    end "…līdz 2028." and look exactly as broken as the |truncate bug
    this helper replaces."""
    q = (
        "Budžets ir pieņemts līdz 2028. gadam un tas ir līdzsvarots. "
        "Tālākā budžeta veidošana pēc 3. oktobra vēlēšanām ir jaunās Saeimas "
        "un jaunās valdības uzdevums, nevis mūsu."
    )
    assert len(q) > 140
    text, is_quote = hero_excerpt(q, None, 140)
    assert (text, is_quote) == (
        "Budžets ir pieņemts līdz 2028. gadam un tas ir līdzsvarots.",
        True,
    )


def test_ellipsis_terminator_is_a_sentence_boundary():
    """A sentence ending in '…' counts as complete; the run of dots is not
    left orphaned by the clause-truncation path."""
    q = (
        "Mēs to apsvērsim ļoti rūpīgi… "
        "Taču galīgais lēmums vēl nav pieņemts, un to nevar steidzināt "
        "nekādā gadījumā bez papildu konsultācijām ar partneriem."
    )
    assert len(q) > 140
    text, is_quote = hero_excerpt(q, None, 140)
    assert (text, is_quote) == ("Mēs to apsvērsim ļoti rūpīgi…", True)
