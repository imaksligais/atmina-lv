"""Labo claim #555865 stilistiku + pārrēķina embedding.

Divas problēmas MŪSU tekstā (`stance`, nevis citātā — verbatim izņēmums šeit
nav piemērojams):

1. "ekspektācijām" — svešvārds tur, kur latviski ir "gaidas". CLAUDE.md
   stilistikas vārti aizliedz kalkus un anglicismus mūsu pašu tekstā.
2. "apgalvojums par bērnu neatļaušanos" — smaga substantivizācija; "neatļauties
   bērnus" nepārvēršas lietvārdā "neatļaušanās".

Atrasts 2026-07-31 dienas rutīnas korektūrā, pirms publicēšanas. Operators
apstiprināja labojumu.

`store_claim()` iegulst `f"{topic}: {stance}"`, tāpēc stance maiņa PRASA
claim_vectors pārrēķinu.

Skripts atjaunina arī dienas pārskata piezīmi #396, jo pārskata tabulas rāda
`stance` burtiski — citādi DB un publicētais teksts atšķirtos (tā pati klase, kas
šodien tika atrasta ar #555872).

Rollback: data/rollback_claim_555865_stils_2026-07-31.sql
"""

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db import get_db  # noqa: E402
from src.embeddings import embed_text  # noqa: E402
from src.preflight import ensure_embeddings_live  # noqa: E402
from src.tools import store_context_note  # noqa: E402

CLAIM_ID = 555865
BRIEF_TOPIC = "dienas analīze 2026-07-31"

OLD = ("Uzskata, ka mūsdienu apgalvojums par bērnu neatļaušanos skaidrojams ar "
       "augušajām ekspektācijām, nevis ar labklājības trūkumu: atzīst par "
       "pamatotu gan vecāko paaudžu teikto, ka bērnus audzināja arī ar niecīgiem "
       "ienākumiem, gan Z paaudzes teikto, ka bērnus nevar atļauties.")
NEW = ("Uzskata, ka mūsdienu apgalvojumi par nespēju atļauties bērnus skaidrojami "
       "ar augstākām gaidām, nevis ar labklājības trūkumu: atzīst par pamatotu "
       "gan vecāko paaudžu teikto, ka bērnus audzināja arī ar niecīgiem "
       "ienākumiem, gan Z paaudzes teikto, ka bērnus nevar atļauties.")

ROLLBACK = Path(__file__).resolve().parent.parent / "data" / \
    "rollback_claim_555865_stils_2026-07-31.sql"


def main() -> int:
    ensure_embeddings_live()
    db = get_db()

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

    brief = db.execute(
        "SELECT id, content FROM context_notes WHERE note_type='daily_brief' AND topic=?",
        (BRIEF_TOPIC,),
    ).fetchone()
    if brief is None:
        print("STOP: dienas pārskats nav atrasts")
        return 1
    if brief["content"].count(OLD) != 1:
        print(f"STOP: pārskatā vecais teksts atrasts "
              f"{brief['content'].count(OLD)} reizes, gaidīts 1")
        return 1

    # Rollback PIRMS jebkādas rakstīšanas.
    ROLLBACK.write_text(
        "-- Atceļ: claim #555865 stilistikas labojumu (ekspektācijas -> gaidas,\n"
        "--        'bērnu neatļaušanās' -> 'nespēja atļauties bērnus')\n"
        "-- Piemērots: 2026-07-31\n"
        "-- Atjauno stance tekstu un baitu identisku veco embedding.\n"
        "-- NB: dienas pārskata piezīmes #396 tekstu šis rollback NEATGRIEŽ —\n"
        "--     to atsvaidzina nākamā pārskata ģenerēšana vai roku labojums.\n"
        "-- NB: claim_vectors ir vec0 virtuālā tabula — vajag sqlite_vec ielādētu.\n\n"
        f"UPDATE claims SET stance = {OLD!r} WHERE id = {CLAIM_ID};\n"
        f"DELETE FROM claim_vectors WHERE claim_id = {CLAIM_ID};\n"
        f"INSERT INTO claim_vectors (claim_id, embedding) VALUES "
        f"({CLAIM_ID}, X'{old_hex}');\n",
        encoding="utf-8",
    )
    print(f"rollback uzrakstīts: {ROLLBACK}")

    new_vec = embed_text(f"{topic}: {NEW}")
    new_bytes = struct.pack(f"{len(new_vec)}f", *new_vec)

    db.execute("UPDATE claims SET stance = ? WHERE id = ?", (NEW, CLAIM_ID))
    db.execute("DELETE FROM claim_vectors WHERE claim_id = ?", (CLAIM_ID,))
    db.execute(
        "INSERT INTO claim_vectors (claim_id, embedding) VALUES (?, ?)",
        (CLAIM_ID, new_bytes),
    )
    db.commit()

    # Pārskats rāda stance burtiski — sinhronizē, lai DB un publicētais sakrīt.
    store_context_note(note_type="daily_brief", topic=BRIEF_TOPIC,
                       content=brief["content"].replace(OLD, NEW))

    check = db.execute(
        "SELECT stance FROM claims WHERE id = ?", (CLAIM_ID,)
    ).fetchone()["stance"]
    n_vec = db.execute(
        "SELECT COUNT(*) AS n FROM claim_vectors WHERE claim_id = ?", (CLAIM_ID,)
    ).fetchone()["n"]
    rows = db.execute(
        "SELECT id, content FROM context_notes WHERE note_type='daily_brief' AND topic=?",
        (BRIEF_TOPIC,),
    ).fetchall()

    print(f"stance: {check}")
    print(f"claim_vectors rindas: {n_vec} (jābūt 1)")
    print(f"daily_brief rindas: {len(rows)} (jābūt 1), id={rows[0]['id']}")
    print(f"vecais teksts pārskatā: {rows[0]['content'].count(OLD)} (jābūt 0)")

    Path(r"E:\atmina\wiki\dailies\2026-07-31.md").write_text(
        rows[0]["content"], encoding="utf-8")
    print("wiki/dailies/2026-07-31.md pārrakstīts")

    ok = (check == NEW and n_vec == 1 and len(rows) == 1
          and rows[0]["content"].count(OLD) == 0)
    print("OK" if ok else "PĀRBAUDE NEIZDEVĀS")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
