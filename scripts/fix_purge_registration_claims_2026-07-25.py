"""Dzēš claims, kas ģenerēti no "Deputātu klātbūtnes reģistrācija" notikumiem.

Klātbūtnes reģistrācija nav balsojums: nav priekšlikuma, totāli ir 0:0:0, un
biļetena vērtības ir Reģistrējies/Nereģistrējies. `generate_claims_from_votes()`
tomēr taisīja claim uz katru sekoto deputātu, un stance nāca no atkāpšanās zara
ar neapstrādātu vērtību — "Re&#291;istr&#275;jies: Deputātu klātbūtnes
reģistrācija". Uzkrājās 30 376 claims (5,5% no visiem), visi tēmā "Valsts
pārvalde" ar confidence=1.0 un salience=0.7.

Publiski tie nekad nenoplūda (Data Contract #4 — render/brief filtrē
claim_type='position'; balsojumu sekcija tos izmet kopš 2026-07-17). Kaitējums
bija iekšējs: katra deputāta balsojumu claim skaits ~5% uzpūsts, 30 376 lieki
vektori `claim_vectors` indeksā, un jebkurš tiešs `claims` vaicājums dabūja
muļķību ar confidence=1.0.

Uz priekšu vārti jau ir `src/saeima/votes.py::generate_claims_from_votes`
(_REGISTRATION_MOTIF_PREFIX). Šis skripts tīra vēsturi.

Balsojumu un individuālo balsu rindas NETIEK aiztiktas — tās ir īsts ieraksts
par to, kas sēdē bija klāt.

Lietošana:
    python scripts/fix_purge_registration_claims_2026-07-25.py
    python scripts/fix_purge_registration_claims_2026-07-25.py --apply \
        --backup data/atmina.db.pre-registration-claims-purge-20260725.db

Rollback: data/rollback_purge_registration_claims_2026-07-25.sql
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

import sqlite_vec

REPO_ROOT = Path(__file__).parent.parent
DB_PATH = str(REPO_ROOT / "data" / "atmina.db")

# Prefiksi, NE '%reģistrācij%' — pēdējais noķertu īstus likumus (Civilstāvokļa
# aktu reģistrācijas likums). Tā pati izvēle kā src/render/votes.py:173 un
# src/saeima/votes.py::_REGISTRATION_MOTIF_PREFIX.
#
# "Kvoruma pārbaude" pievienota pēc pirmās palaišanas: tā ir tā pati procedūra
# citā vārdā, un tai palika 100 claims ar to pašu nedekodēto stance formu.
# Ārpus šīm divām klasēm DB nav neviena Reģistrējies/Nereģistrējies biļetena.
MOTIF_PREFIXES = ("Deputātu klātbūtnes reģistrācija", "Kvoruma pārbaude")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="bez tā — sausā palaide")
    ap.add_argument("--backup", help="pirms-dzēšanas DB kopijas ceļš (obligāts ar --apply)")
    args = ap.parse_args()

    if args.apply:
        if not args.backup:
            print("ATTEIKUMS: --apply prasa --backup (CLAUDE.md — datu mutācija "
                  "nāk ar atgriešanās ceļu; 30k rindu INSERT dump nav repo mērogā, "
                  "tāpēc atgriešanās ceļš ir DB kopija).")
            return 2
        if not Path(args.backup).exists():
            print(f"ATTEIKUMS: kopija neeksistē: {args.backup}")
            return 2

    db = sqlite3.connect(DB_PATH)
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)

    where = " OR ".join("motif LIKE ?" for _ in MOTIF_PREFIXES)
    urls = [r[0] for r in db.execute(
        f"SELECT url FROM saeima_votes WHERE {where}",
        [p + "%" for p in MOTIF_PREFIXES])]
    if not urls:
        print("Nav procedurālo klātbūtnes notikumu — nekas nav darāms.")
        return 0
    qs = ",".join("?" * len(urls))

    by_type = db.execute(
        f"SELECT claim_type, COUNT(*) FROM claims WHERE source_url IN ({qs}) "
        f"GROUP BY claim_type", urls).fetchall()
    total = sum(n for _, n in by_type)
    vectors = db.execute(
        f"SELECT COUNT(*) FROM claim_vectors WHERE claim_id IN "
        f"(SELECT id FROM claims WHERE source_url IN ({qs}))", urls).fetchone()[0]

    print(f"Procedurālie klātbūtnes notikumi: {len(urls)}")
    print(f"Dzēšamie claims: {total}  {dict(by_type)}")
    print(f"Dzēšamie vektori: {vectors}")

    # Cietie vārti: šai atlasei nekad nedrīkst trāpīties pozīcija. Ja trāpās,
    # prefiksa filtrs ir kļūdains un dzēšana apturama, nevis "gandrīz pareiza".
    positions = dict(by_type).get("position", 0)
    if positions:
        print(f"\nSTOP: atlasē ir {positions} claim ar claim_type='position'. "
              f"Prefiksa filtrs ķer ko citu, nekā domāts — nekas nav dzēsts.")
        return 1

    if not args.apply:
        print("\n(sausā palaide — nekas nav dzēsts; pievieno --apply un --backup)")
        return 0

    db.execute(
        f"DELETE FROM claim_vectors WHERE claim_id IN "
        f"(SELECT id FROM claims WHERE source_url IN ({qs}))", urls)
    db.execute(f"DELETE FROM claims WHERE source_url IN ({qs})", urls)
    db.commit()

    left_c = db.execute(
        f"SELECT COUNT(*) FROM claims WHERE source_url IN ({qs})", urls).fetchone()[0]
    left_v = db.execute(
        f"SELECT COUNT(*) FROM claim_vectors WHERE claim_id IN "
        f"(SELECT id FROM claims WHERE source_url IN ({qs}))", urls).fetchone()[0]
    print(f"\nDzēsts. Palikuši claims: {left_c}, vektori: {left_v} (abiem jābūt 0)")
    print(f"claims kopā tagad: {db.execute('SELECT COUNT(*) FROM claims').fetchone()[0]}")
    print(f"claim_vectors kopā tagad: "
          f"{db.execute('SELECT COUNT(*) FROM claim_vectors').fetchone()[0]}")
    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
