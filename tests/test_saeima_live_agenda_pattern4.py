"""Paterns 4 (`drawDKP_Pr` 21. arguments) — dzīvās darba kārtības balsojumu URL.

Robs, kas to prasīja (2026-09-10, mērīts). Dzīvā (`IsActual="1"`) darba kārtība
nerenderē NEVIENU balsojuma saiti: visi trīs kanoniskie paterni
(`_STATIC_VOTE_RE`, `_ADD_VOTES_RE`, `_VOTING_READFORM_RE`) atgrieza **0**, tātad
`_extract_vote_urls_from_agenda()` dienu, kurā notika 16 balsojumi, nolasīja kā
tukšu. Balsojuma GUID stāv `drawDKP_Pr(...)` 21. argumentā; no tā uzbūvējams tas
pats `Voting?ReadForm&parentID={GUID}` URL, ko dod paterns 3.

Līdz 2026-09-16 paterns 4 dzīvoja TIKAI `.claude/agents/saeima-tracker.md`
promptā — helperis to neprata, un katrs uz tā būvētais rīks (arī paritātes
audits) bija akls pret tās pašas dienas sēdi.

**Mutācijas vārti (šī faila galvenais tests):** vārts, kuru neviens nav redzējis
KRĪTAM, nav pierādījums. `test_mutating_pattern4_makes_the_live_agenda_empty`
nomaina paterna 4 regulāro izteiksmi pret nekad-nesakrītošu un pieprasa, lai tā
pati dzīvā darba kārtība atkal atgrieztu `[]` — t.i. testu komplekts KĻŪST SARKANS,
ja paternu 4 no helpera izņem.
"""

from __future__ import annotations

import re

import pytest

from scripts.p3_backfill_year_urllib import (
    SAEIMA_BASE,
    _extract_vote_urls_from_agenda,
)

# Divi dzīvās darba kārtības balsojumi. GUID ir 21. arguments (0-bāzēti: [20]).
GUID_1 = "8f1c2a3e-4b5d-6e7f-8091-a2b3c4d5e6f7"
GUID_2 = "1A2B3C4D-5E6F-7081-92A3-B4C5D6E7F809"  # titania mēdz sūtīt abos reģistros


def _draw_call(fn: str, guid: str | None, item_hex: str = "0" * 32) -> str:
    """`drawDKP_*(...)` izsaukums ar 21 argumentu (dzīvās lapas izkārtojums)."""
    args = [
        "1", "", "Groz%C4%ABjumi", "1104/Lm14", "1",
        item_hex, "Komisija", "",
        "par 64, pret 16, atturas 0 &nbsp; <b>Pie&#326;emts</b>",
        "3", "x", "", "5156B", "6", "", "", "1", "", "", "",
        "" if guid is None else guid,
    ]
    assert len(args) == 21, "fikstūrai jātur tieši 21 arguments"
    return f'{fn}(' + ",".join(f'"{a}"' for a in args) + ');\n'


# Dzīvā darba kārtība: NEVIENAS balsojuma saites — tikai JS zīmēšanas izsaukumi.
LIVE_AGENDA = (
    '<script>var actualXML_DkId="ABCDEF0123456789ABCDEF0123456789";</script>\n'
    'drawDKP_Hd("Saeimas 2026. gada 10. septembra s&#275;de","","","IsActual","1");\n'
    + _draw_call("drawDKP_Pr", GUID_1, item_hex="A" * 32)
    + _draw_call("drawDKP_Pr", GUID_2, item_hex="B" * 32)
)


def test_live_agenda_has_no_pattern_1_2_3_link():
    """Saucējs: fikstūra ir godīga tikai tad, ja vecie trīs paterni tur NEKO neatrod."""
    assert "?OpenDocument" not in LIVE_AGENDA
    assert "addVotesLink" not in LIVE_AGENDA
    assert "Voting?ReadForm" not in LIVE_AGENDA


def test_live_agenda_yields_both_parent_id_urls_in_page_order():
    urls = _extract_vote_urls_from_agenda(LIVE_AGENDA)
    assert urls == [
        f"{SAEIMA_BASE}/Voting?ReadForm&parentID={GUID_1}",
        f"{SAEIMA_BASE}/Voting?ReadForm&parentID={GUID_2}",
    ]


def test_mutating_pattern4_makes_the_live_agenda_empty(monkeypatch):
    """MUTĀCIJAS VĀRTI: bez paterna 4 tā pati dzīvā diena atkal ir „tukša".

    Šis ir vienīgais tests, kas pierāda, ka iepriekšējais NAV nejaušs — ja kāds
    paternu 4 izņem, helperis klusi atgriežas pie 2026-09-10 uzvedības, un šim
    testam JĀNOSARKST.
    """
    import scripts.p3_backfill_year_urllib as p3

    never = re.compile(r"(?!)")
    monkeypatch.setattr(p3, "_DRAW_DKP_PR_RE", never)
    assert p3._extract_vote_urls_from_agenda(LIVE_AGENDA) == []


def test_duplicate_guid_is_deduped_once():
    agenda = LIVE_AGENDA + _draw_call("drawDKP_Pr", GUID_1, item_hex="C" * 32)
    urls = _extract_vote_urls_from_agenda(agenda)
    assert len(urls) == 2, urls
    assert urls[0] == f"{SAEIMA_BASE}/Voting?ReadForm&parentID={GUID_1}"


@pytest.mark.parametrize(
    "value",
    [
        "",                       # punkts bez balsojuma — visbiežākais gadījums
        "   ",
        "0",
        "Komisija",
        "A" * 32,                 # UNID (32 hex) NAV parentID GUID — sk. helpera komentāru
        "8f1c2a3e-4b5d-6e7f-8091-a2b3c4d5e6",   # par īsu (35)
    ],
)
def test_missing_or_non_guid_21st_arg_is_skipped_silently(value):
    """Daudziem `drawDKP_*` punktiem balsojuma nav — tukšs 21. arguments nav robs."""
    assert _extract_vote_urls_from_agenda(_draw_call("drawDKP_Pr", value)) == []


def test_pattern4_does_not_fire_on_the_old_14_argument_layout():
    """Vecā (2026-07-23) darba kārtība: `drawDKP_Pr` ar 14 argumentiem, bez 21.

    Fikstūra ir tā pati, ko lieto `extract_agenda_result_labels` tests — ja
    paterns 4 tur kaut ko atrastu, tas nozīmētu, ka indekss nobīdījies.
    """
    from tests.test_saeima import TestExtractAgendaResultLabels as Old

    old_only_pattern4 = [
        u for u in _extract_vote_urls_from_agenda(Old.AGENDA)
        if "parentID=" in u
    ]
    assert old_only_pattern4 == []
    # ...un vecie paterni turpat joprojām strādā (saucējs, ne tikai nulle).
    assert len(_extract_vote_urls_from_agenda(Old.AGENDA)) == 3


def test_pattern_order_is_1_then_4():
    """Apvienība saglabā paternu kārtību 1→2→3→4, katrā — lapas kārtību."""
    static_hex = "D" * 32
    agenda = f'<a href="./0/{static_hex}?OpenDocument">x</a>\n' + LIVE_AGENDA
    urls = _extract_vote_urls_from_agenda(agenda)
    assert urls == [
        f"{SAEIMA_BASE}/0/{static_hex}?OpenDocument",
        f"{SAEIMA_BASE}/Voting?ReadForm&parentID={GUID_1}",
        f"{SAEIMA_BASE}/Voting?ReadForm&parentID={GUID_2}",
    ]


def test_registration_item_drawn_by_another_dkp_helper_is_not_dropped():
    """Paterns 4 ir APZINĀTI platāks par prompta `drawDKP_Pr`.

    2026-09-10 sēdē 16 balsojumu vidū bija 2 klātbūtnes reģistrācijas, un
    reģistrācijas punktu titania zīmē ar `drawDKP_UT(...)`, ne `_Pr`. Šaurāks
    paterns tos klusi izmestu — tieši T8 klase. Pārmērīga iekļaušana maksā
    vienu redzamu `SKIP … empty data` rindiņu; izlaišana maksā balsojumu.
    """
    guid = "99887766-5544-3322-1100-aabbccddeeff"
    urls = _extract_vote_urls_from_agenda(_draw_call("drawDKP_UT", guid))
    assert urls == [f"{SAEIMA_BASE}/Voting?ReadForm&parentID={guid}"]
