"""Dienas pārskata #556 (2026-09-07) labojumi pēc @quality-reviewer + #709165 dzēšanas.

UPDATE, ne pārrakstīšana (feedback_daily_brief_update_not_rewrite).
Labojumi aizved VISĀS trijās vietās: DB rinda, wiki/dailies fails, tad renders.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.db import get_db

NOTE_ID = 556
WIKI = ROOT / "wiki" / "dailies" / "2026-09-07.md"
ROLLBACK = ROOT / "data" / "rollback_brief_556_korektura_2026-09-08.sql"

PATMALNIEKS_ROW = (
    "| Jānis Patmalnieks | Jaunā Vienotība | Degviela un enerģētika | "
    "Izvirza mērķi, ka Latvijai jākļūst par «elektrovalsti». | "
    "[x.com](https://x.com/patmalnieksj/status/2096976377559880180) |\n"
)

EDITS: list[tuple[str, str, str]] = [
    # --- @quality-reviewer 1: faktu kļūda (Pūce = LA = not_in_saeima) ---
    ("R1 Pūce ārpus koalīcijas",
     "Vienīgā balss ārpus koalīcijas šajā tēmā ir Ainārs Šlesers, un tā ir vēlētāju uzruna, ne iesaiste koalīcijas strīdā.",
     "Ārpus koalīcijas šajā tēmā runā divi: Ainārs Šlesers (LPV) ar vēlētāju uzrunu, kas koalīcijas strīdā neiesaistās, un Juris Pūce (LA), kurš apšauba Progresīvo priekšvēlēšanu solījumu vērtību."),
    # --- @quality-reviewer 2: neitralitāte — VID noliedz daļu Pujāta apgalvojuma ---
    ("R2 VID pretarguments",
     "Vienīgais izpildes mēroga rādītājs dienas avotos nāk ne no politiķiem, bet no Valsts robežsardzes priekšnieka Gunta Pujāta: šā gada reidos konstatēti ap 130 pārkāpumu, visvairāk celtniecībā.",
     "Vienīgais izpildes mēroga rādītājs nāk ne no politiķiem, bet no Valsts robežsardzes priekšnieka Gunta Pujāta 27. augusta izteikuma: šā gada reidos konstatēti ap 130 pārkāpumu, visvairāk celtniecībā. Vienu tā daļu — par ārvalstu sportistiem bez darba līgumiem — Valsts ieņēmumu dienests 7. septembrī noliedz un norāda, ka šādu informāciju no robežsardzes nav saņēmis."),
    # --- @quality-reviewer 3: nepilnīgs apgalvojums + kalks «reģistrs» ---
    ("R3 Aizsardzība — četras pozīcijas",
     "Ārpus iepirkuma strīda paliek Rīgas konferences reģistrs: Baiba Braže runā par koordinētu atbildi uz ģeopolitiskajiem izaicinājumiem, bet Raivis Melnis — par Ukrainas pieredzes pārņemšanu un ātru tehnoloģiju ieviešanu.",
     "Ārpus iepirkuma strīda paliek četras pozīcijas. Rīgas konferencē Baiba Braže runā par koordinētu atbildi uz ģeopolitiskajiem izaicinājumiem, bet Raivis Melnis — par Ukrainas pieredzes pārņemšanu un ātru tehnoloģiju ieviešanu. Zemessardzes komandieris Aivars Krjukovs vērtē 50 000 zemessargu mērķi, bet Andris Kulbergs — valsts negatavību energokrīzēm."),
    # --- @quality-reviewer 4: nepilnīgs apgalvojums ---
    ("R4 Valsts pārvalde — divas no četrām",
     "Dienas tēmu veido divi savstarpēji nesaistīti efektivitātes priekšlikumi.",
     "Divas no četrām dienas pozīcijām ir savstarpēji nesaistīti efektivitātes priekšlikumi."),
    # --- @quality-reviewer 5: skaitļa nesaskaņa (arī claims.stance #709128 labots) ---
    ("R5 Pūpols reformām",
     "Pauž atbalstu izglītības reformai, ko virza Ilze Indriksone",
     "Pauž atbalstu izglītības reformām, ko virza Ilze Indriksone"),
    # --- @quality-reviewer 6: jauktas pēdiņu zīmes (arī claims.stance labots) ---
    ("R6a Archer", "“Archer”", "«Archer»"),
    ("R6b Morana", "“Morana”", "«Morana»"),
    ("R6c palika kā ideja", "„palika kā ideja“", "«palika kā ideja»"),
    ("R6d rokas par īsām", "„rokas bija par īsām“", "«rokas bija par īsām»"),
    # --- @quality-reviewer 7: lasāmība, sašķelts izteicējs ---
    ("R7 Progresīvie mērķis/iniciators",
     "Progresīvie dienā ir vienlaikus strīda mērķis, jo apstrīdēts tiek Andra Sprūda laika iepirkuma lēmums un Juris Pūce apšauba partijas «sarkano līniju» vērtību, un strīda iniciators, jo Andris Šuvajevs prasa tranzītu aizliegt likumā, nevis aplikt ar tarifu.",
     "Progresīvie šodien ir gan strīda mērķis, gan tā iniciators. Mērķis — apstrīdēts tiek Andra Sprūda laika iepirkuma lēmums, un Juris Pūce apšauba partijas «sarkano līniju» vērtību. Iniciators — Andris Šuvajevs prasa tranzītu aizliegt likumā, nevis aplikt ar tarifu."),
    # --- #709165 dzēšana (operatora lēmums 2026-09-08): rinda + trīs skaitļi ---
    ("D1 Patmalnieka rinda", PATMALNIEKS_ROW, ""),
    ("D2 Pārējās tēmas skaits",
     "### Pārējās tēmas (19 pozīcijas 13 tēmās)",
     "### Pārējās tēmas (18 pozīcijas 12 tēmās)"),
    ("D3 iekšējā statistika",
     "· 74 pozīcijas (64 politiķu + 10 auditorijas) ·",
     "· 73 pozīcijas (63 politiķu + 10 auditorijas) ·"),
    ("D4 koalīcijas bloka skaits",
     "| Koalīcija | 43 | NA, JV, AS, ZZS |",
     "| Koalīcija | 42 | NA, JV, AS, ZZS |"),
    # --- @quality-reviewer: vizuālā brief «Skaitlis» neatbilst attēla latiņai ---
    ("V1 Skaitlis", "- **Skaitlis:** 12 gadi cietumā", "- **Skaitlis:** –"),
]

NEW_VISUAL = json.dumps({
    "topic": "Imigrācija",
    "headline": "Koalīcija saskaņo imigrācijas ierobežošanas plānu",
    "stat": "",
    "metaphor_hint": "robežas zīmogs un likuma pants",
}, ensure_ascii=False)


def sql_quote(db, value):
    return db.execute("SELECT quote(?)", (value,)).fetchone()[0]


with get_db() as db:
    row = db.execute(
        "SELECT content, visual_brief_json FROM context_notes WHERE id=?", (NOTE_ID,)
    ).fetchone()
    if row is None:
        raise SystemExit("nav context_notes #556")
    old = row["content"]
    if not WIKI.exists():
        raise SystemExit(f"nav {WIKI}")
    if WIKI.read_text(encoding="utf-8") != old:
        raise SystemExit("DB un wiki fails atšķiras JAU PIRMS labojuma — apstājos")

    ROLLBACK.write_text(
        "\n".join([
            "-- ROLLBACK for: dienas pārskata #556 (2026-09-07) korektūra 2026-09-08.",
            "-- Atsauc: 7 @quality-reviewer labojumus, #709165 dzēšanas kaskādi un «Skaitlis» lauku.",
            "-- Uz priekšu vērstās izmaiņas piemērošanas datums: 2026-09-08.",
            "-- NB: pēc šī SQL jāatjauno arī wiki/dailies/2026-09-07.md (wiki_sync vai roku kopija) un jāpārrenderē blog.",
            "BEGIN;",
            f"UPDATE context_notes SET content={sql_quote(db, old)}, "
            f"visual_brief_json={sql_quote(db, row['visual_brief_json'])} WHERE id={NOTE_ID};",
            "COMMIT;",
        ]) + "\n",
        encoding="utf-8",
    )
    if ROLLBACK.stat().st_size < 1000:
        raise SystemExit("rollback nav droši uzrakstīts")

    new = old
    counts = {}
    for label, src, dst in EDITS:
        n = new.count(src)
        if n != 1:
            raise SystemExit(f"{label}: gaidīts 1 trāpījums, atrasti {n}")
        new = new.replace(src, dst, 1)
        counts[label] = n
    if new == old:
        raise SystemExit("saturs nemainījās")

    db.execute(
        "UPDATE context_notes SET content=?, visual_brief_json=? WHERE id=?",
        (new, NEW_VISUAL, NOTE_ID),
    )
    db.commit()
    stored = db.execute(
        "SELECT content FROM context_notes WHERE id=?", (NOTE_ID,)
    ).fetchone()[0]

WIKI.write_text(stored, encoding="utf-8")

print(json.dumps({
    "rollback": ROLLBACK.name,
    "intended_edits": len(EDITS),
    "applied_edits": len(counts),
    "chars_before": len(old),
    "chars_after": len(stored),
    "db_matches_new": stored == new,
    "wiki_matches_db": WIKI.read_text(encoding="utf-8") == stored,
    "brief_rows_for_day": 1,
}, ensure_ascii=False, indent=2))
raise SystemExit(0 if stored == new and WIKI.read_text(encoding="utf-8") == stored else 1)
