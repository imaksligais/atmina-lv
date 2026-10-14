"""@quality-reviewer 2026-09-23 (rīta daļa) atradumu labojumi pirms deploy.

#717988 stance gramatika (BLOKĒJA); #717997, #532213 stance stils; #717948, #20689 reasoning
atsauces uz dzēstiem claims (#18137 -> #18275, #18101 -> #18217); #717978 reasoning pēc
operatora labojuma; spriedze #365 apraksts. Re-embed: 717988 717997 532213.
Rollback: data/rollback_quality_review_2026-09-23.sql
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "atmina.db"
RB = ROOT / "data" / "rollback_quality_review_2026-09-23.sql"


def lit(v):
    return "NULL" if v is None else "'" + str(v).replace("'", "''") + "'"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    db = sqlite3.connect(DB)
    g = lambda cid, col: db.execute(f"SELECT {col} FROM claims WHERE id=?", (cid,)).fetchone()[0]  # noqa: E731
    old = {
        (717988, "stance"): g(717988, "stance"),
        (717997, "stance"): g(717997, "stance"),
        (532213, "stance"): g(532213, "stance"),
        (717948, "reasoning"): g(717948, "reasoning"),
        (20689, "reasoning"): g(20689, "reasoning"),
        (717978, "reasoning"): g(717978, "reasoning"),
    }
    t365 = db.execute("SELECT description FROM political_tensions WHERE id=365").fetchone()[0]
    new = {
        (717988, "stance"): "Norāda, ka tikšanās reizēs ar vēstniekiem, arī Tuvo Austrumu valstu, apspriež Latvijas veselības intereses — medicīnas izglītības iespējas, zinātnes un citu sadarbību ES līmenī un veselības tūrismu; atzīst, ka Ēģiptes vēstniece par veselības tūrismu interesi neizrādīja, jo lidojums ir ilgāks un medicīna Ēģiptē ir lētāka nekā Latvijā.",
        (717997, "stance"): old[(717997, "stance")].replace("(publicēts 23.09.; pēc ieraksta — 16. septembris)", "(ieraksts par 16. septembri, publicēts 23.09.)"),
        (532213, "stance"): old[(532213, "stance")].replace("jaunus atļaut tikai ar finanšu ministra atļauju", "jaunus pieļaut tikai ar finanšu ministra atļauju"),
        (717948, "reasoning"): old[(717948, "reasoning")].replace("#18137", "#18275"),
        (20689, "reasoning"): old[(20689, "reasoning")].replace("#18101", "#18217"),
        (717978, "reasoning"): old[(717978, "reasoning")].replace("kā #715773. avots ir", "kā #715773. Avots ir").replace(" — operatoram jāizlemj, vai glabāt", ""),
    }
    for k in new:
        assert new[k] != old[k], f"nav mainījies: {k}"
    t365_new = "Kulbergs TV3 raidījumā «900 sekundes» norāda, ka Ārlietu ministrijai bija jānokoordinē Latvijas pozīcija ES sankciju jautājumā, lai Latvija nepaliktu pēdējā Eiropā."
    RB.write_text(
        "-- Rollback: scripts/fix_quality_review_2026-09-23.py (piemērots 2026-09-23)\n"
        "-- PĒC TAM: .venv/Scripts/python.exe scripts/reembed_claims.py 717988 717997 532213\nBEGIN;\n"
        + "".join(f"UPDATE claims SET {c}={lit(v)} WHERE id={i};\n" for (i, c), v in old.items())
        + f"UPDATE political_tensions SET description={lit(t365)} WHERE id=365;\nCOMMIT;\n", encoding="utf-8")
    with db:
        for (i, c), v in new.items():
            db.execute(f"UPDATE claims SET {c}=? WHERE id=?", (v, i))
        db.execute("UPDATE political_tensions SET description=? WHERE id=365", (t365_new,))
    for (i, c) in new:
        print(i, c, "ok" if g(i, c) == new[(i, c)] else "FAIL")


if __name__ == "__main__":
    main()
