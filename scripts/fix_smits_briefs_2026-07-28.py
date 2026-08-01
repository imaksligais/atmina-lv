# -*- coding: utf-8 -*-
"""Šmita partijas etiķetes labojums publicētajos pārskatos (BACKLOG § Šmita
partijas kļūda; operatora lēmums 2026-07-28 = variants (c): labot visus).

Fakti (data/fix_smits_party_2026-07-26.sql): Didzis Šmits (id=150) NEKAD nav
bijis Stabilitātei! — viņš ir Saeimas deputāts ĀRPUS FRAKCIJĀM (AS frakcija
līdz 2025-02, tad NULL); 'ST' etiķete bija skrāpera artefakts 17 rindās vienā
sēžu logā. Kļūda bija iesalusi 17 context_notes (backloga 16 + šeit atrastā
#195) un 16 wiki/dailies|weeklies failos (DB un wiki virsmas vietām diverģē —
05-26 un 07-23 wiki failos ir formas, kuru DB piezīmēs nav).

Labo TIKAI etiķetes un balsojuma ieraksta teikumus (229 — tā pati kļūdu klase
kā note #373 Kiršteins: balsojumā 5754 Šmitam faction=NULL, ST! frakcijas rindu
tur nav vispār). Bloku skaitļus apzināti NEPĀRRĒĶINA — bloku sastāvs paliek kā
publicēts, etiķete kļūst patiesa ("ārpus frakcijām").

Idempotents: atkārtots skrējiens neatrod vairs nevienu no vecajām formām.
Paired rollback: data/rollback_smits_briefs_2026-07-28.sql (pilns vecais
saturs 17 piezīmēm; wiki failiem rollback = git vēsture).
Apply date: 2026-07-28.
"""
import sqlite3
import sys
from pathlib import Path

NOTE_IDS = [173, 193, 195, 200, 204, 221, 222, 225, 226, 227, 229, 239,
            271, 287, 289, 365, 371]

# Secība svarīga: specifiskie teikumi pirms vispārīgajiem catch-all.
RULES = [
    # 229 — balsojuma ieraksta teikumi (vote 5754: Šmits faction=NULL, Par)
    ("Stabilitātei! sadalījās — Šmits par, 9 pret, Igors Judins un Saļimovs nebalsoja.",
     "Stabilitātei! deputāti 9 pret (Igors Judins un Saļimovs nebalsoja); ārpusfrakciju deputāts Didzis Šmits balsoja par."),
    ("| Opozīcija | Stabilitātei! | 1 (Šmits) | 9 | 2 (Igors Judins, Saļimovs) |",
     "| Opozīcija | Stabilitātei! | 0 | 9 | 2 (Igors Judins, Saļimovs) |"),
    ("| Citi | Bezpartejiski / ZZS bez frakcijas | 4 | 0 | 0 |",
     "| Citi | Bezpartejiski (t.sk. Šmits — par) / ZZS bez frakcijas | 5 | 0 | 0 |"),
    ("noturēja monolītu pretbalsojumu, izņemot Didzi Šmitu (ST!), kas balsoja par, un Igoru Judinu un Amilu Saļimovu (ST!), kuri klātesoši atturējās no balsošanas.",
     "noturēja monolītu pretbalsojumu, izņemot Igoru Judinu un Amilu Saļimovu (ST!), kuri klātesoši atturējās no balsošanas; ārpusfrakciju deputāts Didzis Šmits balsoja par."),
    # Bespoke teikumi ar bloka apgalvojumu
    ("Opozīcijas balsis (Kulbergs, Šmits)", "Opozīcijas un ārpusfrakciju balsis (Kulbergs, Šmits)"),
    ("ST! (Šmits) iezīmējas", "ārpusfrakciju deputāts Šmits iezīmējas"),
    ("kamēr opozīcija Velps, Mežals, Šmits un Šlesers konsolidē",
     "kamēr Velps, Mežals un Šlesers (opozīcija) un ārpusfrakciju deputāts Šmits konsolidē"),
    ("Opozīcija sašķēlusies: Šlesers prasa premjera amatu sev, Šmits virza Kučinski",
     "Vienotības ārpus koalīcijas nav: Šlesers prasa premjera amatu sev, Šmits virza Kučinski"),
    ("Opozīcijā vienotības par alternatīvu nav: LPV (Šlesers) un S! (Šmits) virza savus kandidātus",
     "Ārpus koalīcijas vienotības par alternatīvu nav: Šlesers (LPV) un ārpusfrakciju deputāts Šmits virza savus kandidātus"),
    ("un Stabilitātei (Šmits) atrod", "un ārpusfrakciju deputāts Šmits atrod"),
    ("savukārt Šmits (S!) un Mežals (LPV) iezīmē", "savukārt ārpusfrakciju deputāts Šmits un Mežals (LPV) iezīmē"),
    ("Didzis Šmits (S!, opozīcija) abi iebilst", "Didzis Šmits (ārpus frakcijām) abi iebilst"),
    ("bet Šmits (S!) no opozīcijas puses pamato", "bet Šmits (ārpus frakcijām) pamato"),
    ("Kulbergs no koalīcijas un Šmits (S!) no opozīcijas nonāk",
     "Kulbergs no koalīcijas un ārpusfrakciju deputāts Šmits nonāk"),
    ("savukārt opozīcijas Šmits (S!) turnīru aizstāv", "savukārt ārpusfrakciju deputāts Šmits turnīru aizstāv"),
    ("Šmits (S!) no opozīcijas puses atbalsta", "Šmits (ārpus frakcijām) atbalsta"),
    ("Opozīcija nerunā vienā balsī: Šmits (S!) un Stendzenieks (LPV)",
     "Ārpus koalīcijas nerunā vienā balsī: Šmits (ārpus frakcijām) un Stendzenieks (LPV)"),
    # Tabulu ailes
    ("| Didzis Šmits | Stabilitātei! |", "| Didzis Šmits | Ārpus frakcijām |"),
    ("AS, LPV, S!", "AS, LPV, ārpus frakcijām"),
    ("LPV, AS, S!", "LPV, AS, ārpus frakcijām"),
    # Vispārīgie catch-all (pēdējie)
    ("Didzis Šmits (Stabilitātei!)", "Didzis Šmits (ārpus frakcijām)"),
    ("Šmits (S!)", "Šmits (ārpus frakcijām)"),
    ("Šmits (ST!)", "Šmits (ārpus frakcijām)"),
]

LEFTOVER = ["Šmits (S!", "Šmits (ST!", "Šmitu (ST!", "ST! (Šmits)", "S! (Šmits)",
            "Stabilitātei (Šmits)", "Šmits (Stabilitātei!)",
            "Didzis Šmits | Stabilitātei!", "AS, LPV, S!", "LPV, AS, S!"]


def apply_rules(text: str) -> str:
    for old, new in RULES:
        text = text.replace(old, new)
    return text


def main(dry_run: bool = True) -> int:
    db = sqlite3.connect("data/atmina.db")
    c = db.cursor()
    rollback = ["-- Rollback for scripts/fix_smits_briefs_2026-07-28.py "
                "(apply date 2026-07-28).\n"
                "-- Atjauno 17 context_notes pilno veco saturu (ar Šmita "
                "'Stabilitātei!' kļūdu —\n-- tas ir vēsturiskais stāvoklis). "
                "Wiki failu rollback = git vēsture.\n\nBEGIN TRANSACTION;\n"]
    changed = 0
    for nid in NOTE_IDS:
        (old,) = c.execute("SELECT content FROM context_notes WHERE id=?", (nid,)).fetchone()
        new = apply_rules(old)
        left = [p for p in LEFTOVER if p in new]
        if left:
            print(f"!! note {nid}: paliek {left}")
            return 1
        if new != old:
            changed += 1
            rollback.append(
                f"UPDATE context_notes SET content = '{old.replace(chr(39), chr(39)*2)}' "
                f"WHERE id = {nid};\n")
            if not dry_run:
                c.execute("UPDATE context_notes SET content=? WHERE id=?", (new, nid))
    rollback.append("\nCOMMIT;\n")
    if not dry_run:
        Path("data/rollback_smits_briefs_2026-07-28.sql").write_text(
            "".join(rollback), encoding="utf-8")
        db.commit()
    print(f"DB: {changed}/{len(NOTE_IDS)} piezīmes {'mainītos' if dry_run else 'mainītas'}")

    wiki_changed = 0
    for f in sorted(list(Path("wiki/dailies").glob("*.md")) +
                    list(Path("wiki/weeklies").glob("*.md"))):
        old = f.read_text(encoding="utf-8")
        new = apply_rules(old)
        left = [p for p in LEFTOVER if p in new]
        if left:
            print(f"!! {f}: paliek {left}")
            return 1
        if new != old:
            wiki_changed += 1
            if not dry_run:
                f.write_text(new, encoding="utf-8")
    print(f"Wiki: {wiki_changed} faili {'mainītos' if dry_run else 'mainīti'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(dry_run="--apply" not in sys.argv))
