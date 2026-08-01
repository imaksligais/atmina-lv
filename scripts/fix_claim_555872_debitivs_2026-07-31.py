"""Labo claim #555872 debitīva locījumu + pārrēķina embedding.

Kļūda: `stance` saturēja "vēstījumus jābalsta" — debitīvs latviešu valodā prasa
nominatīvu ("vēstījumi jābalsta"). Atrasts 2026-07-31 dienas rutīnā, kad
@brief-writer dienas pārskatā (piezīme #396) uzrakstīja pareizo formu, bet DB
palika nepareizā — t.i. publicētais pārskats un politiķa profila lapa būtu
rādījuši atšķirīgu tekstu.

Tas ir MŪSU teksts (stance), nevis citāts, tāpēc CLAUDE.md gramatikas vārti to
attiecas; `claims.quote` verbatim izņēmums šeit nav piemērojams.

`store_claim()` iegulst `f"{topic}: {stance}"`, tāpēc stance maiņa PRASA
claim_vectors pārrēķinu — citādi semantiskā meklēšana turpinātu atrast rindu pēc
vecā teksta.

Rollback: data/rollback_claim_555872_debitivs_2026-07-31.sql (ģenerē šis skripts
PIRMS izmaiņas, ar baitu identisku veco embedding hex literālī).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db import get_db  # noqa: E402
from src.embeddings import embed_text  # noqa: E402
from src.preflight import ensure_embeddings_live  # noqa: E402

CLAIM_ID = 555872
OLD = ("Uzskata, ka stratēģiskajā komunikācijā vēstījumus jābalsta ar reālām "
       "darbībām; degošās rūpnīcas Krievijā par Ukrainas spējām pasakot vairāk "
       "nekā jebkādi vārdi")
NEW = ("Uzskata, ka stratēģiskajā komunikācijā vēstījumi jābalsta ar reālām "
       "darbībām; degošās rūpnīcas Krievijā par Ukrainas spējām pasakot vairāk "
       "nekā jebkādi vārdi")

ROLLBACK = Path(__file__).resolve().parent.parent / "data" / \
    "rollback_claim_555872_debitivs_2026-07-31.sql"


def main() -> int:
    ensure_embeddings_live()
    db = get_db()

    # claim_vectors ir vec0 virtuālā tabula — get_db() paplašinājumu neielādē,
    # to dara katrs rakstītājs pats (sal. src/db.py store_claim).
    import sqlite_vec
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)

    row = db.execute(
        "SELECT topic, stance FROM claims WHERE id = ?", (CLAIM_ID,)
    ).fetchone()
    if row is None:
        print(f"STOP: claim #{CLAIM_ID} neeksistē")
        return 1
    topic, stance = row["topic"], row["stance"]
    if stance != OLD:
        print(f"STOP: stance neatbilst gaidītajam vecajam tekstam.\n"
              f"  DB : {stance!r}\n  gaid: {OLD!r}")
        return 1

    vec_row = db.execute(
        "SELECT embedding FROM claim_vectors WHERE claim_id = ?", (CLAIM_ID,)
    ).fetchone()
    if vec_row is None:
        print(f"STOP: claim #{CLAIM_ID} nav claim_vectors rindas")
        return 1
    old_hex = vec_row["embedding"].hex()

    # Rollback PIRMS izmaiņas — noteikums prasa, lai tas eksistē agrāk par rakstīšanu.
    ROLLBACK.write_text(
        "-- Atceļ: claim #555872 stance debitīva labojumu (vēstījumus -> vēstījumi)\n"
        "-- Piemērots: 2026-07-31\n"
        "-- Atjauno gan stance tekstu, gan baitu identisku veco embedding.\n"
        "-- NB: claim_vectors ir vec0 virtuālā tabula — vajag sqlite_vec ielādētu.\n\n"
        f"UPDATE claims SET stance = {OLD!r} WHERE id = {CLAIM_ID};\n"
        f"DELETE FROM claim_vectors WHERE claim_id = {CLAIM_ID};\n"
        f"INSERT INTO claim_vectors (claim_id, embedding) VALUES "
        f"({CLAIM_ID}, X'{old_hex}');\n",
        encoding="utf-8",
    )
    print(f"rollback uzrakstīts: {ROLLBACK}")

    import struct
    new_vec = embed_text(f"{topic}: {NEW}")
    new_bytes = struct.pack(f"{len(new_vec)}f", *new_vec)

    db.execute("UPDATE claims SET stance = ? WHERE id = ?", (NEW, CLAIM_ID))
    db.execute("DELETE FROM claim_vectors WHERE claim_id = ?", (CLAIM_ID,))
    db.execute(
        "INSERT INTO claim_vectors (claim_id, embedding) VALUES (?, ?)",
        (CLAIM_ID, new_bytes),
    )
    db.commit()

    check = db.execute(
        "SELECT stance FROM claims WHERE id = ?", (CLAIM_ID,)
    ).fetchone()["stance"]
    n_vec = db.execute(
        "SELECT COUNT(*) AS n FROM claim_vectors WHERE claim_id = ?", (CLAIM_ID,)
    ).fetchone()["n"]
    print(f"stance: {check}")
    print(f"claim_vectors rindas: {n_vec} (jābūt 1)")
    print("OK" if check == NEW and n_vec == 1 else "PĀRBAUDI NEIZDEVĀS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
