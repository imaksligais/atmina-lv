"""Seed pid=109 Ingmārs Līdaka negative_patterns + clean false-positive junctions.

Background: 2026-05-03 audit (claim-extractor 7-misc agent) atklāja, ka
pid=109 Ingmārs Līdaka name_forms ["Ingmārs Līdaka", "Līdaka", "Līdaka, Ingmārs"]
liek matcher'am bare-surname "Līdaka" salinkt rakstus par citiem publiski
pazīstamiem cilvēkiem ar to pašu uzvārdu — konkrēti:
- Gunta Līdaka (Finanšu ministrijas pārstāve, "ka dubultot darba ražīgumu")
- Gunta Līdaka (Kultūras ministrijas mediju politikas darbiniece, Puntuļa tweet)

Fix:
- Pievieno tracked_politicians.negative_patterns ar 5 variantiem "Gunta Līdaka"
- DELETE 2 false-positive document_politicians junction rows (29378, 7363)

Idempotent — atkārtota palaišana neproducē jaunus DELETE (junction rows jau
nav).
"""
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

DB_PATH = Path("data/atmina.db")
PID = 109
NEGATIVE_PATTERNS = [
    "Gunta Līdaka",
    "Guntas Līdakas",
    "G. Līdaka",
    "G.Līdaka",
    "Gunta Līdakas",
]
FALSE_POSITIVE_DOCS = [29378, 7363]


def main():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    # 1. Set negative_patterns (idempotent — overwrites with canonical list)
    con.execute(
        "UPDATE tracked_politicians SET negative_patterns = ? WHERE id = ?",
        (json.dumps(NEGATIVE_PATTERNS, ensure_ascii=False), PID),
    )
    print(f"[1/2] pid={PID} negative_patterns set: {NEGATIVE_PATTERNS}")

    # 2. Delete known false-positive junctions (idempotent — DELETE matching nothing is OK)
    cur = con.execute(
        "DELETE FROM document_politicians WHERE politician_id = ? AND document_id IN ({})".format(
            ",".join("?" * len(FALSE_POSITIVE_DOCS))
        ),
        (PID, *FALSE_POSITIVE_DOCS),
    )
    print(f"[2/2] DELETE document_politicians rows: {cur.rowcount} (target docs: {FALSE_POSITIVE_DOCS})")

    con.commit()
    con.close()
    print("done")


if __name__ == "__main__":
    main()
