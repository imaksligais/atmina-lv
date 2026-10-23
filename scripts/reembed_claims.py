"""Pārrēķina `claim_vectors` konkrētām `claims` rindām.

**Kāpēc šis skripts eksistē.** `store_claim()` iegulst `f"{topic}: {stance}"`
(`src/db.py:818`), tāpēc jebkurš tiešs `UPDATE claims SET topic` vai
`SET stance` atstāj `claim_vectors` ar vektoru, kas uzbūvēts no VECĀ teksta.
Nekas neizmet kļūdu — `search_similar_claims()` vienkārši klusi turpina ranžēt
rindu pēc tā, ko tā agrāk teica. CLAUDE.md eskalācijas 8. noteikums to prasa
novērst, bet līdz 2026-08-02 palaižama rīka tam nebija, un vismaz divas
vēsturiskas migrācijas (2026-06-13 topic-drift, 2026-07-28 „elektr", kopā
~9 000 rindu) aizgāja bez pārrēķina.

Lietojums (VIENMĒR no repo saknes, ar projekta interpretatoru):

    .venv/Scripts/python.exe scripts/reembed_claims.py 615826 615827
    .venv/Scripts/python.exe scripts/reembed_claims.py --dry-run 615826
    .venv/Scripts/python.exe scripts/reembed_claims.py --ids-from data/rollback_X.ids

`--ids-from` ir bulk gadījumam: 4 000 id pozicionāli ir ~28 tūkst. rakstzīmju
komandrindā, kas uz Windows atduras pret ~32 tūkst. limitu. Rollback fails, kas
prasa pārrēķinu, glabā savu id sarakstu blakus kā `.ids` failu.

Sausā palaide ir noklusējums TIKAI ar `--dry-run`; bez tā skripts raksta.
Katrai rindai tas izdrukā, vai vektors tiešām mainījās — nemainīgs vektors pēc
`stance` labojuma nozīmē, ka kaut kas nav aiztikts, un to ir vērts pamanīt.

**NB (2026-08-21 verdikts):** `saeima_vote` claims vairs NEPĀRRTĪES glabā
vektorus — store_claim tos vairs neauto-embedo. Šis rīks uz balsojuma claimu
tomēr IZVEIDOSU vektoru; masveida skrējienos neiedod balsojumu id (sk.
CLAUDE.md eskalāciju 8). Vienam claimam tīši izveidots vektors ir atgriezenams:
DELETE FROM claim_vectors WHERE claim_id = ?.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db import _float_list_to_bytes, get_db  # noqa: E402
from src.embeddings import embed_text  # noqa: E402


def reembed(claim_ids: list[int], dry_run: bool = False) -> int:
    db = get_db()
    import sqlite_vec

    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)

    changed = 0
    # Denominators pirmajā rindā — pārbaude, kas neziņo, cik rindu tā aptaustīja,
    # nav pierādījums (CLAUDE.md § Working Conventions).
    print(f"pieprasītas {len(claim_ids)} rindas")

    for cid in claim_ids:
        row = db.execute(
            "SELECT topic, stance FROM claims WHERE id = ?", (cid,)
        ).fetchone()
        if row is None:
            print(f"  {cid}: NAV TĀDAS RINDAS — izlaists")
            continue

        new_bytes = _float_list_to_bytes(embed_text(f"{row['topic']}: {row['stance']}"))
        old = db.execute(
            "SELECT embedding FROM claim_vectors WHERE claim_id = ?", (cid,)
        ).fetchone()
        old_bytes = old["embedding"] if old else None

        state = (
            "jauns vektors (rindai vektora nebija)"
            if old_bytes is None
            else ("MAINĪJĀS" if bytes(old_bytes) != new_bytes else "nemainīgs")
        )
        print(f"  {cid}: {state}  [{row['topic']}]")

        if dry_run:
            continue

        db.execute("DELETE FROM claim_vectors WHERE claim_id = ?", (cid,))
        db.execute(
            "INSERT INTO claim_vectors (claim_id, embedding) VALUES (?, ?)",
            (cid, new_bytes),
        )
        changed += 1

    if not dry_run:
        db.commit()
    db.close()
    print(f"pārrakstītas {changed} rindas" + (" (SAUSĀ palaide)" if dry_run else ""))
    return changed


def read_ids_file(path: str) -> list[int]:
    """Nolasa claim id sarakstu no faila — viens id rindā, tukšās un `#` izlaiž.

    Eksistē tāpēc, ka pozicionālie argumenti nesedz bulk gadījumu: 4 087 id ir
    ~28 tūkst. rakstzīmju komandrindā, kas uz Windows atduras pret ~32 tūkst.
    limitu. Rollback faili, kas prasa pārrēķinu, tāpēc glabā savu id sarakstu
    blakus kā `.ids` failu (paraugs: `data/rollback_dup_saeima_vote_claims_*.ids`).
    """
    ids: list[int] = []
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            ids.append(int(line))
    return ids


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("claim_ids", nargs="*", type=int)
    ap.add_argument("--ids-from", metavar="PATH",
                    help="fails ar claim id sarakstu, viens rindā (bulk gadījumam)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    ids = list(args.claim_ids)
    if args.ids_from:
        ids.extend(read_ids_file(args.ids_from))
    if not ids:
        ap.error("nav neviena claim id — padod tos pozicionāli vai ar --ids-from")

    reembed(ids, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
