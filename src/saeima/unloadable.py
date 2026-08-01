"""Balsojumi, kuriem individuālais roll-call NEEKSISTĒ un nekad neeksistēs.

Aizklātā balsošana (Saeimas vadības, Valsts prezidenta, valsts kontroliera
vēlēšanas) pēc definīcijas neatstāj ieraksta par to, kā balsoja konkrēts
deputāts. Tas nav skrāpja robs un nav ielādējams: titania lapa būvē tabulu ar
JS, un tur `voteFullListByNames` ir `[""]` — tukšs pēc dizaina. `saeima_votes` /
`saeima_individual_votes` tāpēc te nav ko likt.

Kāpēc šis fails vispār eksistē: bez tā `audit_saeima_agenda_parity.py` katrā
skrējienā skaita šos 19 par „trūkstošiem", un katra nākamā sesija no jauna
izmeklē to pašu un nonāk pie tā paša secinājuma. Tas nav robs, ko aizpildīt;
tas ir zināms un pierakstīts fakts.

**Kas TOMĒR eksistē.** Lapa nav tukša: `voteShortListByNames` nes kandidātu
sadalījumu, un lauku nozīme ir nolasīta no pašas lapas renderētāja
(`redrawMainTableShort` galvenes: `Kandidāts | Par | Pret`), nevis uzminēta.
Tāpēc `tally` te ir glabāts kā fakts — tas ir kandidātu, ne deputātu līmeņa
dati, tāpēc tas apzināti NEIET `saeima_individual_votes` shēmā. Ja kādreiz
vajadzēs to publiskā virsmā, dati jau ir savākti un pārbaudīti.

Divi stāvokļi, un tos nedrīkst jaukt:
  `sealed_with_tally` — roll-call nav, kandidātu sadalījums IR (13 ieraksti)
  `sealed_no_data`    — titania nav publicējusi nekādus rezultātus (6 ieraksti:
                        3 × 2023-09-20 un 3 × 2026-06-04; tur arī
                        `voteShortListByNames` ir `[""]`)

Atslēga ir `(vote_date, vote_time)`, NEVIS URL — titania pārarhivē balsojumu
lapas ar jauniem UNID ~nedēļu pēc sēdes, tāpēc URL atslēga te novecotu tieši
tāpat, kā tā padara aklu `store_vote()` dedup (sk. audita docstring).

Savākts un verificēts 2026-08-01 (16 ieraksti). Skaitļi sakrīt ar publisko
vēsturi: Smiltēns 82:11 ievēlēts par priekšsēdētāju, Mieriņa 55:34, Rinkēvičs
52 balsis 3. kārtā, Korčagins 90:1. Trīs 2026-06-04 ieraksti pievienoti
2026-08-18 (operatora verdikts 2026-08-17), un tie ir vienīgie, kuriem PIRMS
tam DB bija tukša čaulas rinda — sk. komentāru pie tiem.
"""

from __future__ import annotations

# (vote_date, vote_time) -> {motif, kind, tally: [(kandidāts, par, pret)]}
UNLOADABLE_VOTES: dict[tuple[str, str], dict] = {
    # --- 2022-11-01: 14. Saeimas pirmā sēde, vadības vēlēšanas ---
    ("2022-11-01", "15:36:05"): dict(
        motif="Saeimas priekšsēdētāja vēlēšanas",
        kind="sealed_with_tally",
        tally=[("Aleksejs Rosļikovs", 11, 82), ("Edvards Smiltēns", 82, 11)],
    ),
    ("2022-11-01", "16:31:17"): dict(
        motif="Saeimas priekšsēdētāja biedra vēlēšanas",
        kind="sealed_with_tally",
        tally=[("Nataļja Marčenko-Jodko", 11, 87), ("Zanda Kalniņa-Lukaševica", 87, 11)],
    ),
    ("2022-11-01", "17:25:17"): dict(
        motif="Saeimas priekšsēdētāja biedra vēlēšanas",
        kind="sealed_with_tally",
        tally=[("Jānis Grasbergs", 86, 12), ("Viktorija Pleškāne", 12, 86)],
    ),
    ("2022-11-01", "18:20:04"): dict(
        motif="Saeimas sekretāra vēlēšanas",
        kind="sealed_with_tally",
        tally=[("Armands Krauze", 87, 12), ("Svetlana Čulkova", 12, 87)],
    ),
    ("2022-11-01", "19:13:07"): dict(
        motif="Saeimas sekretāra biedra vēlēšanas",
        kind="sealed_with_tally",
        tally=[("Antoņina Ņenaševa", 79, 19), ("Linda Liepiņa", 9, 89),
               ("Svetlana Čulkova", 10, 88)],
    ),

    # --- 2023-05-31: Valsts prezidenta vēlēšanas, trīs kārtas ---
    # 1. un 2. kārtai sadalījums ir IDENTISKS — tā nav kļūda, bet strupceļš:
    # neviens balss nepārgāja. 3. kārtā Pinto vairs nekandidēja, un viņas 10
    # balsis aizgāja Rinkēvičam (42+10=52), kas ir vēsturiskais ievēlēšanas
    # skaitlis. Nelabot un neuzskatīt par dublikātu.
    ("2023-05-31", "11:10:57"): dict(
        motif="Valsts prezidenta vēlēšanas",
        kind="sealed_with_tally",
        tally=[("Edgars Rinkēvičs", 42, 45), ("Elīna Pinto", 10, 77),
               ("Uldis Pīlēns", 25, 62)],
    ),
    ("2023-05-31", "12:31:01"): dict(
        motif="Valsts prezidenta vēlēšanas",
        kind="sealed_with_tally",
        tally=[("Edgars Rinkēvičs", 42, 45), ("Elīna Pinto", 10, 77),
               ("Uldis Pīlēns", 25, 62)],
    ),
    ("2023-05-31", "13:50:21"): dict(
        motif="Valsts prezidenta vēlēšanas",
        kind="sealed_with_tally",
        tally=[("Edgars Rinkēvičs", 52, 35), ("Uldis Pīlēns", 25, 62)],
    ),

    # --- 2023-09-20: priekšsēdētāja vēlēšanas pēc Smiltēna atkāpšanās ---
    ("2023-09-20", "11:04:29"): dict(
        motif="Saeimas priekšsēdētāja vēlēšanas",
        kind="sealed_with_tally",
        tally=[("Gunārs Kūtris", 26, 59), ("Māris Sprindžuks", 23, 62)],
    ),
    ("2023-09-20", "12:29:57"): dict(
        motif="Saeimas priekšsēdētāja vēlēšanas",
        kind="sealed_with_tally",
        tally=[("Gunārs Kūtris", 26, 61), ("Māris Sprindžuks", 25, 62)],
    ),
    ("2023-09-20", "13:17:30"): dict(
        motif="Saeimas priekšsēdētāja vēlēšanas",
        kind="sealed_with_tally",
        tally=[("Gunārs Kūtris", 18, 60)],
    ),
    ("2023-09-20", "15:44:46"): dict(
        motif="Saeimas priekšsēdētāja vēlēšanas",
        kind="sealed_with_tally",
        tally=[("Aleksejs Rosļikovs", 9, 80), ("Daiga Mieriņa", 55, 34)],
    ),
    # Šiem trim titania nav publicējusi NEKĀDUS rezultātus — arī
    # voteShortListByNames ir [""]. Tas nav tas pats, kas aizklāts ar sadalījumu.
    ("2023-09-20", "16:41:26"): dict(
        motif="Saeimas priekšsēdētāja biedra vēlēšanas",
        kind="sealed_no_data",
        tally=[],
    ),
    ("2023-09-20", "17:28:54"): dict(
        motif="Saeimas sekretāra vēlēšanas",
        kind="sealed_no_data",
        tally=[],
    ),
    ("2023-09-20", "17:58:51"): dict(
        motif="Saeimas sekretāra biedra vēlēšanas",
        kind="sealed_no_data",
        tally=[],
    ),

    # --- 2023-12-06 ---
    ("2023-12-06", "14:47:20"): dict(
        motif="Par valsts kontroliera iecelšanu",
        kind="sealed_with_tally",
        tally=[("Edgars Korčagins", 90, 1)],
    ),

    # --- 2026-06-04: vadības vēlēšanas, kurās neviens netika ievēlēts ---
    # Šie trīs LĪDZ 2026-08-18 DZĪVOJA DIVĀS FORMĀS: bez roll-call, bet ar
    # tukšām čaulas rindām `saeima_votes` (id 5831/5832/5833, 0/0/0/0, nulle
    # individuālo balsu, 0 claims). Operatora verdikts 2026-08-17 — čaulas
    # dzēst, notikumu pierakstīt te, lai viena notikuma forma ir viena.
    # Migrācija: data/{fix,rollback}_secret_ballot_shells_2026-08-18.sql.
    # Verificēts pret dzīvo titania 2026-08-18: visiem trim gan
    # `voteFullListByNames`, gan `voteShortListByNames` ir `[""]` — tāpēc
    # `sealed_no_data`, nevis `sealed_with_tally`.
    ("2026-06-04", "18:08:46"): dict(
        motif="Saeimas priekšsēdētājas biedra vēlēšanas",
        kind="sealed_no_data",
        tally=[],
    ),
    ("2026-06-04", "19:12:24"): dict(
        motif="Saeimas sekretāra vēlēšanas",
        kind="sealed_no_data",
        tally=[],
    ),
    ("2026-06-04", "19:45:17"): dict(
        motif="Saeimas sekretāra biedra vēlēšanas (1015/Lm14)",
        kind="sealed_no_data",
        tally=[],
    ),
}

KINDS = {"sealed_with_tally", "sealed_no_data"}


def is_unloadable(vote_date: str, vote_time: str) -> bool:
    """Vai šim (datums, laiks) roll-call neeksistē pēc dizaina?"""
    return (vote_date, vote_time) in UNLOADABLE_VOTES


def lookup(vote_date: str, vote_time: str) -> dict | None:
    return UNLOADABLE_VOTES.get((vote_date, vote_time))
