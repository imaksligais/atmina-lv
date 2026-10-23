"""Dienas pārskata #174 (2026-04-28) labojums: Pūpola Ģertrūdes laukuma nostājas virziens.

Pārskatā bija rakstīts, ka Pūpols «sešu dienu laikā pāriet no kompromisa uz pilnīgu
projekta apturēšanas prasību pēc koalīcijas vienošanās». Pēc avotiem virziens ir
pretējs: 22.04. tvīts «nav vairs jāmeklē kompromiss» (doc 23428) → 24.04. paša
kompromiss (doc 25307) → NRA 28.04. kompromiss (doc 27536). Delfi 28.04. (doc 27508)
tikai atkārtoja 22.04. citātu; pozīcija no tā DB vairs nav, tāpēc tabulas rinda un
skaitļi (-1) tiek izņemti. UPDATE, ne pārrakstīšana; DB rinda + wiki/dailies fails.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.db import get_db  # noqa: E402

NOTE_ID = 174
WIKI = ROOT / "wiki" / "dailies" / "2026-04-28.md"
ROLLBACK = ROOT / "data" / "rollback_brief_174_pupols_2026-09-27.sql"

DELFI_ROW = (
    "| Ansis Pūpols | Nacionālā apvienība | Pēc koalīcijas vienošanās cietina nostāju — vairs nemeklē kompromisu Ģertrūdes l | "
    "[delfi.lv](https://www.delfi.lv/193/politics/120116385/rigas-domes-koalicija-vienojas-pirmo-gadu-pec-remonta-darbdienas-saglabat-satiksmi-ap-gertrudes-baznicu) |\n"
)

EDITS: list[tuple[str, str, str]] = [
    ("E1 dienas kopsavilkums",
     "- **Pilsētvide eskalē koalīcijā:** Pūpols (NA) sešu dienu laikā pāriet no Ģertrūdes laukuma kompromisa uz pilnīgu projekta apturēšanas prasību pēc Rīgas domes koalīcijas vienošanās.",
     "- **Pilsētvide koalīcijā:** Pūpols (NA) NRA intervijā piedāvā Ģertrūdes laukuma kompromisu — slēgt satiksmi tikai brīvdienās, bet darbadienās to mierināt, lai gan 22. aprīlī vēl aicināja projektu «likt mierā»."),
    ("E2 konteksta bloks",
     "2026-04-22→04-28: Pūpola (NA, Rīgas dome) Ģertrūdes laukuma nostāja sašaurinās 6 dienu laikā. NRA intervijā (04-22) viņš piedāvā kompromisu — slēgt satiksmi tikai brīvdienās, darbadienās 20 km/h ar stabiņiem un puķupodiem. Pēc koalīcijas vienošanās (Delfi 04-28) Pūpols cietina nostāju FB ierakstā un noraida tālākus kompromisus. Eskalācija notiek koalīcijas iekšienē, ne starpjautā ar opozīciju — fix-iks visupirms procedurāls (koalīcijas disciplīna), ne sabiedrisks.",
     "2026-04-22→04-28: Pūpola (NA, Rīgas dome) nostāja par Ģertrūdes laukumu mīkstinās. 22. aprīlī viņš raksta, ka «nav vairs jāmeklē kompromiss», un aicina projektu apturēt. 24. aprīlī un NRA intervijā 28. aprīlī viņš pats piedāvā kompromisu — slēgt satiksmi tikai brīvdienās, bet darbadienās noteikt 20 km/h un sašaurināt joslu ar stabiņiem un puķupodiem. Delfi 28. aprīļa raksts par koalīcijas vienošanos citē viņa 22. aprīļa ierakstu, nevis jaunu izteikumu. Diskusija notiek koalīcijas iekšienē. Labots 2026-09-27: iepriekš šeit un dienas kopsavilkumā bija rakstīts, ka Pūpols pēc koalīcijas vienošanās nostāju cietinājis; tas balstījās uz Delfi atkārtoto 22. aprīļa citātu."),
    ("E3 Delfi rinda", DELFI_ROW, ""),
    ("E4 tēmas skaits", "### Pilsētvide (4 pozīcijas)", "### Pilsētvide (3 pozīcijas)"),
    ("E5 koalīcijas bloks",
     "| Koalīcija | 19 | PRO, JV, ZZS, NA | Melnis (3), Sprūds (2), Pūpols (2) |",
     "| Koalīcija | 18 | PRO, JV, ZZS, NA | Melnis (3), Sprūds (2), Pūpols (1) |"),
    ("E6 iekšējā statistika", "· 24 pozīcijas ·", "· 23 pozīcijas ·"),
]


def sql_quote(db, value):
    return db.execute("SELECT quote(?)", (value,)).fetchone()[0]


with get_db() as db:
    row = db.execute("SELECT content FROM context_notes WHERE id=?", (NOTE_ID,)).fetchone()
    if row is None:
        raise SystemExit(f"nav context_notes #{NOTE_ID}")
    old = row["content"]
    if WIKI.read_text(encoding="utf-8").strip() != old.strip():
        raise SystemExit("DB un wiki fails atšķiras JAU PIRMS labojuma — apstājos")

    ROLLBACK.write_text(
        "\n".join([
            "-- ROLLBACK for: dienas pārskata #174 (2026-04-28) labojums — Pūpola Ģertrūdes nostājas virziens.",
            "-- Atsauc: scripts/fix_brief_174_pupols_2026-09-27.py (6 labojumi). Piemērots: 2026-09-27.",
            "-- NB: pēc šī SQL jāatjauno arī wiki/dailies/2026-04-28.md un jāpārrenderē blog.",
            "BEGIN;",
            f"UPDATE context_notes SET content={sql_quote(db, old)} WHERE id={NOTE_ID};",
            "COMMIT;",
        ]) + "\n",
        encoding="utf-8",
    )
    if ROLLBACK.stat().st_size < 1000:
        raise SystemExit("rollback nav droši uzrakstīts")

    new = old
    for label, src, dst in EDITS:
        n = new.count(src)
        if n != 1:
            raise SystemExit(f"{label}: gaidīts 1 trāpījums, atrasti {n}")
        new = new.replace(src, dst, 1)

    db.execute("UPDATE context_notes SET content=? WHERE id=?", (new, NOTE_ID))
    db.commit()
    stored = db.execute("SELECT content FROM context_notes WHERE id=?", (NOTE_ID,)).fetchone()[0]

WIKI.write_text(stored if stored.endswith("\n") else stored + "\n", encoding="utf-8")

print(json.dumps({
    "rollback": ROLLBACK.name,
    "intended_edits": len(EDITS),
    "db_matches_new": stored == new,
    "wiki_matches_db": WIKI.read_text(encoding="utf-8").strip() == stored.strip(),
    "chars_before": len(old),
    "chars_after": len(stored),
}, ensure_ascii=False))
