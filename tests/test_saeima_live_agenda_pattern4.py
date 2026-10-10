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


# ---------------------------------------------------------------------------
# 34-argumentu dzīvā forma — verbatim izsaukumi no titania 2026-09-17 sēdes
# (`DK?ReadForm&actual=1`, nr=1f916d52-b070-4078-b3b5-7e95872f1df8), nolasīti
# 2026-09-23. Pirmais dzīvais mērījums tai dienai atgrieza 0 no 37 balsojumiem,
# jo helperis lasīja fiksēto [20] — tur dzīvajā formā ir `urgentDep` (tukšs).
# Reālais izkārtojums (visi 71 izsaukumi lapā ar tieši 34 argumentiem):
#   [5]  unid          — balsojuma GUID (dzīvajā formā == [21] DKPid)
#   [20] urgentDep     — tukšs
#   [28] voteType      — netukšs ⇔ balsojums ir (novērotā vērtība "0#0#0" ×32)
#   [29] hasTechChilds — apakšpunktu balsojumi (atsevišķs getTechDKP fetch)
# ---------------------------------------------------------------------------

# Balsojums notika (voteType "0#0#0"): "Par Saeimas viedokli…", 14:47.
_LIVE34_VOTED_UT = 'drawDKP_UT("","","Par%20l%C4%93muma%20projekta%20Par%20Saeimas%20viedokli%20saist%C4%ABb%C4%81%20ar%202026.%20gada%2031.%20august%C4%81%20Satversmes%20ties%C4%81%20rosin%C4%81to%20lietu%20Nr.%202026-15-0103%20(1117%2FLm14)%20iek%C4%BCau%C5%A1anu%20Saeimas%20s%C4%93des%20darba%20k%C4%81rt%C4%ABb%C4%81","","*","fe929133-60dd-4cef-9c58-40792ac7a0c4","","","par 30, pret 24, atturas 7 &nbsp;","","","1","","5","","","3","14:47","","","","fe929133-60dd-4cef-9c58-40792ac7a0c4","","6","","","","","0#0#0","0","","","","");\n'
# Balsojums notika + apakšpunkti (hasTechChilds "1"): Dzelzceļa likums, 15:34.
_LIVE34_VOTED_PR = 'drawDKP_Pr("1","","Groz%C4%ABjumi%20Dzelzce%C4%BCa%20likum%C4%81","1548/Lp14","62","cae480d4-7bd5-4722-a32e-e2902dd632df","Bud&#382;eta un finan&#353;u (nodok&#316;u) komisija","","par 53, pret 12, atturas 0 &nbsp; <b>Likums</b>","3","5 priek&#353;likumi","","5371B","5","","","3","15:34","True","","","cae480d4-7bd5-4722-a32e-e2902dd632df","","1","1","0","","","0#0#0","1","Edmunds Jur&#275;vics","1","","");\n'
# Etiķete "Nod. kom." IR, bet balsojuma NAV (voteType "") — vārtu tests.
_LIVE34_LABEL_NO_VOTE = 'drawDKP_Pr("6","3","Groz%C4%ABjums%20Ener%C4%A3%C4%93tikas%20likum%C4%81","1531/Lp14","2","b84f5b7c-3112-4e33-89c1-d3145fefd3c7","Ministru kabinets","Tautsaimniec%C4%ABbas%2C%20agr%C4%81r%C4%81s%2C%20vides%20un%20re%C4%A3ion%C4%81l%C4%81s%20politikas%20komisija(atbild%C4%ABg%C4%81)","<b>Nod. kom.</b>","1","","","5312, 5312A","5","","","3","15:41","","","","b84f5b7c-3112-4e33-89c1-d3145fefd3c7","","1","1","0","","","","0","","1","","");\n'
# Punkts bez balsojuma vispār (voteType "", bez etiķetes), 14:55.
_LIVE34_NO_VOTE = 'drawDKP_UT("","","Par%20likumprojekta%20Groz%C4%ABjumi%20V%C4%93l%C4%93t%C4%81ju%20re%C4%A3istra%20likum%C4%81%20(1545%2FLp14)%2C%20nodo%C5%A1ana%20komisij%C4%81m%20iek%C4%BCau%C5%A1anu%20Saeimas%20s%C4%93des%20darba%20k%C4%81rt%C4%ABb%C4%81","","*","cdb425b6-b4b7-466a-ad96-b264d3bac12c","","","","","","","","5","","","3","14:55","","","","cdb425b6-b4b7-466a-ad96-b264d3bac12c","","6","","","","","","0","","","","");\n'

LIVE34_AGENDA = (
    '<script>var actualXML_DkId="1f916d52b0704078b3b57e95872f1df8";</script>\n'
    + _LIVE34_VOTED_UT
    + _LIVE34_NO_VOTE
    + _LIVE34_VOTED_PR
    + _LIVE34_LABEL_NO_VOTE
)

# Tas pats balsojums `nr={uuid}` formā (tā pati sēde): [5] tur ir 32-hex DKP
# punkta UNID, balsojuma GUID pārvietojas uz [21] DKPid — un voteType [28]
# joprojām "0#0#0". nr= lapa tos pašus balsojumus renderē ar addVotesLink,
# tāpēc paterns 4 tur nedrīkst dot parentID= URL (cita URL forma tam pašam
# balsojumam = dublikāts, ko `_vote_already_stored` pēc URL neatpazīst).
_LIVE34_NR_FORM_CALL = 'drawDKP_UT("","","Par%20l%C4%93muma%20projekta%20Par%20Saeimas%20viedokli%20saist%C4%ABb%C4%81%20ar%202026.%20gada%2031.%20august%C4%81%20Satversmes%20ties%C4%81%20rosin%C4%81to%20lietu%20Nr.%202026-15-0103%20(1117%2FLm14)%20iek%C4%BCau%C5%A1anu%20Saeimas%20s%C4%93des%20darba%20k%C4%81rt%C4%ABb%C4%81","","","A937DED2D30B39CFC2258E76000AFD6A","","","par 30, pret 24, atturas 7 &nbsp;","","","1","","5","17.09.2026","1f916d52-b070-4078-b3b5-7e95872f1df8","3","14:47","","","","fe929133-60dd-4cef-9c58-40792ac7a0c4","","6","","","14:50","1","0#0#0","0","","","","");\n'


def test_live34_agenda_yields_only_voted_guids_in_page_order():
    """Īsta 34-arg forma: GUID nāk no [5] un tikai tur, kur voteType nav tukšs."""
    urls = _extract_vote_urls_from_agenda(LIVE34_AGENDA)
    assert urls == [
        f"{SAEIMA_BASE}/Voting?ReadForm&parentID=fe929133-60dd-4cef-9c58-40792ac7a0c4",
        f"{SAEIMA_BASE}/Voting?ReadForm&parentID=cae480d4-7bd5-4722-a32e-e2902dd632df",
    ]


def test_live34_votetype_gate_not_label_decides():
    """Vārti ir voteType, ne etiķetes esamība: «Nod. kom.» bez balsojuma → nav URL."""
    assert _extract_vote_urls_from_agenda(_LIVE34_LABEL_NO_VOTE) == []
    assert _extract_vote_urls_from_agenda(_LIVE34_NO_VOTE) == []


def test_live34_nr_form_item_unid_is_not_emitted_as_vote_url():
    """nr= formā [5] ir 32-hex punkta UNID — GUID validācija to izlaiž.

    Pretējā gadījumā (ja lasītu [21]) nr= lapa dabūtu parentID= dublikātus
    balsojumiem, kurus jau dod addVotesLink kā /0/{HEX}?OpenDocument.
    """
    assert _extract_vote_urls_from_agenda(_LIVE34_NR_FORM_CALL) == []


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
