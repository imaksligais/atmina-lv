"""Jānis Hermanis (id=13): party NULL -> MMN, relationship_type neutral -> tracked.

T6 klases novecojis denormalizēts lauks. Viņš 2026-06-25 publiski paziņoja par
pievienošanos partijai MMN, bet `tracked_politicians.party` palika NULL un
`relationship_type` palika 'neutral' vēl 5 nedēļas.

PIERĀDĪJUMI (divi neatkarīgi avoti, abi pārbaudīti pirms izmaiņas):
1. Viņa paša pirmās personas verbatim izteikums savā X kontā @J_Hermanis
   (doc 58693, claim #532352, 2026-06-25):
   "Esmu pievienojies @partijaMMN, lai stiprinātu to ar savu pieredzi finanšu
   un tautsaimniecības politikas jautājumos."
   Doks piesaistīts id=13 ar role='subject'; tas NAV Alvja Hermaņa (id=29) doks.
2. CVK 2026. gada saraksta kandidātu reģistrs (operators, 2026-07-31):
   https://dati.cvk.lv/SV2026/kandidati/90240-janis-hermanis/

Uzmanību nākamajām sesijām: DB ir DIVI Hermaņi, un ABI ir MMN —
id=13 Jānis Hermanis (finanšu eksperts, @J_Hermanis) un
id=29 Alvis Hermanis (valdes priekšsēdētājs, @AlvisHermanis1).
Tas, ka abiem ir viena partija, NAV atribūcijas kļūdas pazīme.

`party` vērtība ir īsā forma 'MMN' apzināti — CLAUDE.md nosaka MMN/JKP kā divus
īso nosaukumu izņēmumus, un id=29 jau lieto to pašu formu. Jaukta forma vienā
partijā salauž virknes grupēšanu pārskatu blokos.

`relationship_type` -> 'tracked': partijas biedrs un vēlēšanu kandidāts nav
'neutral' komentētājs. Blakusefekts pēc šīs izmaiņas: viņš vairs neizkrīt no
dienas pārskata tēmu tabulām (`briefs.py` audience filtrs).

`role` ('Finanšu eksperts') APZINĀTI netiek mainīts — tas joprojām ir patiess, un
kandidāta saraksts/numurs no dotā avota nav nolasāms; minēšana šeit nav atļauta.

NEATRISINĀTS, operatora lēmums: 7 JAU PUBLICĒTI pārskati (piezīmes 294, 296, 297,
299, 305, 318, 336) viņu klasificē kā neitrālu runātāju. Šis skripts tos NEAIZTIEK
— iesaldētais teksts ir godīgs ieraksts par to, ko toreiz publicējām (sk. Šmita
precedentu, BACKLOG). Šīsvakara piezīme #396 vēl nav publicēta un tiek labota
atsevišķi.

Rollback: data/rollback_janis_hermanis_party_2026-07-31.sql
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db import get_db  # noqa: E402

PID = 13
OLD_PARTY = None
OLD_REL = "neutral"
NEW_PARTY = "MMN"
NEW_REL = "tracked"

ROLLBACK = Path(__file__).resolve().parent.parent / "data" / \
    "rollback_janis_hermanis_party_2026-07-31.sql"


def main() -> int:
    db = get_db()
    row = db.execute(
        "SELECT name, party, role, relationship_type FROM tracked_politicians WHERE id = ?",
        (PID,),
    ).fetchone()
    if row is None:
        print(f"STOP: id={PID} neeksistē")
        return 1
    if row["name"] != "Jānis Hermanis":
        print(f"STOP: id={PID} nav Jānis Hermanis, bet {row['name']!r}")
        return 1
    if row["party"] != OLD_PARTY or row["relationship_type"] != OLD_REL:
        print(f"STOP: lauki neatbilst gaidītajiem.\n"
              f"  party: {row['party']!r} (gaidīts {OLD_PARTY!r})\n"
              f"  relationship_type: {row['relationship_type']!r} (gaidīts {OLD_REL!r})")
        return 1

    # Kontrolpārbaude: pierādījuma doks tiešām pieder id=13, nevis id=29.
    ev = db.execute(
        """SELECT d.id FROM documents d
           JOIN document_politicians dp ON dp.document_id = d.id
           WHERE d.id = 58693 AND dp.politician_id = ? AND dp.role = 'subject'""",
        (PID,),
    ).fetchone()
    if ev is None:
        print("STOP: pierādījuma doks 58693 nav piesaistīts id=13 kā subject")
        return 1
    print("pierādījuma doks 58693 apstiprināts kā id=13 subject")

    ROLLBACK.write_text(
        "-- Atceļ: Jānis Hermanis (id=13) party NULL -> 'MMN',\n"
        "--        relationship_type 'neutral' -> 'tracked'\n"
        "-- Piemērots: 2026-07-31\n"
        "-- Pamatojums forward izmaiņai: viņa paša paziņojums 2026-06-25\n"
        "--   (doc 58693 / claim #532352) + CVK SV2026 kandidātu reģistrs.\n"
        "-- NB: NEATGRIEŽ dienas pārskata #396 tekstu — tas labots atsevišķi.\n\n"
        f"UPDATE tracked_politicians SET party = NULL, relationship_type = 'neutral' "
        f"WHERE id = {PID};\n",
        encoding="utf-8",
    )
    print(f"rollback uzrakstīts: {ROLLBACK}")

    db.execute(
        "UPDATE tracked_politicians SET party = ?, relationship_type = ? WHERE id = ?",
        (NEW_PARTY, NEW_REL, PID),
    )
    db.commit()

    after = db.execute(
        "SELECT name, party, role, relationship_type FROM tracked_politicians WHERE id = ?",
        (PID,),
    ).fetchone()
    print(f"pēc: {after['name']} | party={after['party']} | "
          f"role={after['role']} | rel={after['relationship_type']}")

    both = db.execute(
        "SELECT id, name, party, x_handle FROM tracked_politicians "
        "WHERE name LIKE '%Hermanis%' ORDER BY id"
    ).fetchall()
    print("abi Hermaņi pēc izmaiņas:")
    for b in both:
        print(f"  id={b['id']} {b['name']} | {b['party']} | @{b['x_handle']}")

    ok = after["party"] == NEW_PARTY and after["relationship_type"] == NEW_REL
    print("OK" if ok else "PĀRBAUDE NEIZDEVĀS")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
