"""Aizklātie balsojumi ir zināms fakts, ne robs — un to nedrīkst pārprast.

Divi virzieni, kurus šie vārti tur. (1) Saraksts nedrīkst klusi paplašināties:
katra rinda te nozīmē, ka parity audits KONKRĒTU balsojumu vairs neskaita par
trūkstošu, tāpēc kļūdaina rinda paslēptu īstu robu. (2) Kandidātu sadalījums
nedrīkst tikt sajaukts ar deputātu balsojumu — tie ir dažāda līmeņa dati, un
tieši tāpēc `tally` apzināti neiet `saeima_individual_votes` shēmā.

Verificēts pret titania: 16 ierakstiem 2026-08-01, trim 2026-06-04 ierakstiem
2026-08-18 — visiem 19 `voteFullListByNames` ir `[""]`.
"""

from __future__ import annotations

import re

from src.saeima.unloadable import (
    KINDS,
    UNLOADABLE_VOTES,
    is_unloadable,
    lookup,
)

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TIME_RE = re.compile(r"^\d{2}:\d{2}:\d{2}$")


def test_the_list_is_exactly_the_audited_records():
    """19 = 5 (2022) + 11 (2023) + 3 (2026). Ja skaits mainās, kāds pievienojis rindu.

    2026. gada trīs ieraksti pievienoti 2026-08-18: līdz tam tie DB dzīvoja kā
    tukšas `saeima_votes` čaulas (id 5831–5833), kuras tajā pašā solī dzēstas
    (`data/{fix,rollback}_secret_ballot_shells_2026-08-18.sql`).
    """
    assert len(UNLOADABLE_VOTES) == 19
    by_year: dict[str, int] = {}
    for vote_date, _t in UNLOADABLE_VOTES:
        by_year[vote_date[:4]] = by_year.get(vote_date[:4], 0) + 1
    assert by_year == {"2022": 5, "2023": 11, "2026": 3}


def test_keys_are_date_time_not_url():
    """titania pārarhivē lapas ar jauniem UNID — URL atslēga te novecotu."""
    for vote_date, vote_time in UNLOADABLE_VOTES:
        assert _DATE_RE.match(vote_date), vote_date
        assert _TIME_RE.match(vote_time), vote_time


def test_every_entry_is_an_election_style_secret_ballot():
    """Aizklāta ir tikai amatpersonu ievēlēšana — ne parasts likumprojekts."""
    for key, rec in UNLOADABLE_VOTES.items():
        motif = rec["motif"]
        assert ("vēlēšanas" in motif or "iecelšanu" in motif), (
            f"{key}: {motif!r} neizskatās pēc aizklātas amatpersonu balsošanas — "
            "parasts balsojums šeit paslēptu īstu robu"
        )


def test_kinds_are_known_and_tally_matches_the_kind():
    for key, rec in UNLOADABLE_VOTES.items():
        assert rec["kind"] in KINDS, f"{key}: nezināms kind {rec['kind']!r}"
        if rec["kind"] == "sealed_no_data":
            assert rec["tally"] == [], f"{key}: no_data nedrīkst nest sadalījumu"
        else:
            assert rec["tally"], f"{key}: with_tally bez sadalījuma"


def test_tally_rows_are_candidate_par_pret():
    """Lauku nozīme nolasīta no lapas renderētāja: Kandidāts | Par | Pret."""
    for key, rec in UNLOADABLE_VOTES.items():
        for row in rec["tally"]:
            assert len(row) == 3, f"{key}: {row!r}"
            name, par, pret = row
            assert isinstance(name, str) and name.strip(), f"{key}: tukšs kandidāts"
            assert isinstance(par, int) and isinstance(pret, int), f"{key}: {row!r}"
            assert 0 <= par <= 100 and 0 <= pret <= 100, (
                f"{key}: {row!r} — Saeimā ir 100 deputātu, tāpēc neviens skaitlis "
                "nevar pārsniegt 100"
            )


def test_known_results_match_the_public_record():
    """Ja kāds pārraksta skaitļus, tas parādās te, ne publicētā tekstā."""
    smiltens = dict((n, (p, pr)) for n, p, pr in
                    lookup("2022-11-01", "15:36:05")["tally"])
    assert smiltens["Edvards Smiltēns"] == (82, 11)

    # 3. kārta: Pinto vairs nekandidē, viņas 10 balsis aizgāja Rinkēvičam.
    r2 = dict((n, p) for n, p, _ in lookup("2023-05-31", "12:31:01")["tally"])
    r3 = dict((n, p) for n, p, _ in lookup("2023-05-31", "13:50:21")["tally"])
    assert "Elīna Pinto" not in r3
    assert r3["Edgars Rinkēvičs"] == 52
    assert r2["Edgars Rinkēvičs"] + r2["Elīna Pinto"] == r3["Edgars Rinkēvičs"]

    mierina = dict((n, (p, pr)) for n, p, pr in
                   lookup("2023-09-20", "15:44:46")["tally"])
    assert mierina["Daiga Mieriņa"] == (55, 34)


def test_lookup_and_is_unloadable_agree():
    assert is_unloadable("2022-11-01", "15:36:05")
    assert lookup("2022-11-01", "15:36:05")["motif"].startswith("Saeimas priekšsēdētāja")
    # Parasts balsojums nedrīkst tikt noklusēts
    assert not is_unloadable("2026-01-15", "12:45:48")
    assert lookup("2026-01-15", "12:45:48") is None


def test_no_ordinary_vote_date_is_swallowed_wholesale():
    """Atslēga ir (datums, LAIKS) — visa diena nedrīkst pazust no audita.

    2023-09-20 tajā pašā dienā notika arī parasti balsojumi; ja kāds kādreiz
    saīsinātu atslēgu līdz datumam, tie klusi izkristu no parity mērījuma.
    """
    dates = {d for d, _t in UNLOADABLE_VOTES}
    for d in dates:
        times = {t for dd, t in UNLOADABLE_VOTES if dd == d}
        assert all(_TIME_RE.match(t) for t in times)
    assert not is_unloadable("2023-09-20", "09:00:00")
