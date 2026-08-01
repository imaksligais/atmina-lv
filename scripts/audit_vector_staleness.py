"""Audit: `claim_vectors` novecošana — glabātais vektors pret `embed(f"{topic}: {stance}")`.

`/audit-integrity` 13. pārbaudes izpildāmā forma. `store_claim()` iegulst
`f"{topic}: {stance}"` un `embed_text` ir determinēts, tāpēc baitu salīdzinājums
ir tīrs pass/fail. Kails `UPDATE claims SET topic/stance` neko neceļ —
`search_similar_claims` vienkārši turpina ranžēt rindu pēc tā, ko tā agrāk
teica. 2026-08-04 šī klase atrasta divreiz vienā dienā (06-13 kopas 167/167 un
14/54 ar roku labotās rindās); līdz tam metode dzīvoja tikai vienreizējos
scratchpad skriptos.

KONTROLES KOPA IR METODES DAĻA, NE PAPILDINĀJUMS. Salauzts salīdzinājums ziņo
VISU kā stale — apgriezti "vārti, kas nevar nekrist". Tāpēc: (a) ja kontroles
rinda (zināma svaigi pārrēķināta) nesakrīt, viss skrējiens ir metodes artefakts;
(b) ja kontroles nav un sakritību ir nulle, rezultātam neuzticamies un to
sakām. Noklusētā kontrole: data/reembed_elektr_vectors_2026-08-03.ids izlase
(pārrēķināta un verificēta 2026-08-03/04).

Lietošana (no repo saknes, VIENMĒR .venv interpretators):
  .venv/Scripts/python.exe scripts/audit_vector_staleness.py                 # kandidāti no data/fix_*.sql
  .venv/Scripts/python.exe scripts/audit_vector_staleness.py --ids-from F    # eksplicīta kopa
  .venv/Scripts/python.exe scripts/audit_vector_staleness.py 123 456        # atsevišķi id

Izejas kods: 0 tīrs · 1 atrasti stale · 2 metode neapstiprināta (kontrole krita
vai nebija pieejama pie nulles sakritībām).
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))

from src.db import _float_list_to_bytes  # noqa: E402

# Tikai embedotie lauki: `reasoning` (un citi) vektoru neietekmē. `quote` arī
# neietilpst embed tekstā, bet quote labojumi bieži nāk kopā ar stance — lēts
# iekļaut, un sakritība tad vienkārši apstiprinās.
# Divas WHERE formas: `WHERE id = N` un bulk `WHERE id IN (N1, N2, …)` — IN
# saraksts var plūst pāri rindām (sk. data/fix_drone_topic_boundary_*.sql).
_ID_RE = re.compile(
    r"UPDATE claims\s+SET\s+(?:stance|topic|quote)[^;]*?"
    r"WHERE\s+id\s+(?:=\s*(\d+)|IN\s*\(([^)]*)\))",
    re.I | re.S,
)


def extract_fix_file_ids(data_dir: Path | str) -> list[int]:
    """Kandidātu kopa = visi claim id, ko `data/fix_*.sql` faili ir labojuši
    embedotajos laukos. Rollback faili apzināti netiek skenēti — tie satur
    pirms-stāvokli, ne piemērotu labojumu."""
    ids: set[int] = set()
    for f in sorted(Path(data_dir).glob("fix_*.sql")):
        text = f.read_text(encoding="utf-8", errors="replace")
        for single, in_list in _ID_RE.findall(text):
            if single:
                ids.add(int(single))
            if in_list:
                ids.update(int(n) for n in re.findall(r"\d+", in_list))
    return sorted(ids)


def _connect(db_path: str) -> sqlite3.Connection:
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    # get_db() sqlite_vec NEielādē (CLAUDE.md zināmā nianse) — darām paši.
    # Testos claim_vectors ir parasta tabula un ielādes kļūme nekait; dzīvajā
    # DB bez paplašinājuma vec0 vaicājums pats kritīs skaļi.
    try:
        import sqlite_vec

        db.enable_load_extension(True)
        sqlite_vec.load(db)
        db.enable_load_extension(False)
    except Exception:
        pass
    return db


def _sweep(db: sqlite3.Connection, ids, embed_fn) -> dict:
    checked = match = missing = 0
    stale_ids: list[int] = []
    for cid in ids:
        row = db.execute(
            "SELECT topic, stance FROM claims WHERE id = ?", (cid,)
        ).fetchone()
        if row is None:
            continue  # dzēsta rinda — uzskaitīta caur alive, ne šeit
        checked += 1
        vec = db.execute(
            "SELECT embedding FROM claim_vectors WHERE claim_id = ?", (cid,)
        ).fetchone()
        if vec is None:
            missing += 1
            continue
        expected = _float_list_to_bytes(embed_fn(f"{row['topic']}: {row['stance']}"))
        if bytes(vec[0]) == expected:
            match += 1
        else:
            stale_ids.append(cid)
    return {
        "checked": checked,
        "match": match,
        "stale": len(stale_ids),
        "stale_ids": stale_ids,
        "missing": missing,
    }


def run_audit(
    db_path: str,
    ids,
    sample: int = 300,
    control_ids=None,
    embed_fn=None,
) -> dict:
    if embed_fn is None:  # vēlā ielāde — modelis maksā sekundes
        from src.embeddings import embed_text as embed_fn

    ids = sorted(set(int(i) for i in ids))
    db = _connect(db_path)
    alive: list[int] = []
    if ids:
        ph = ",".join("?" * len(ids))
        alive = sorted(
            r[0]
            for r in db.execute(
                f"SELECT id FROM claims WHERE id IN ({ph})", ids
            ).fetchall()
        )
    picked = alive
    if sample and len(alive) > sample:
        picked = alive[:: max(1, len(alive) // sample)][:sample]

    main = _sweep(db, picked, embed_fn)
    control = _sweep(db, list(control_ids or []), embed_fn)
    db.close()

    method_ok = True
    note = ""
    if control["checked"]:
        if control["stale"] or control["missing"]:
            method_ok = False
            note = (
                "kontroles kopa NESAKRĪT — katrs zemāk redzamais 'stale' ir "
                "metodes artefakts, ne atradums; salabo salīdzinājumu, tad mēri"
            )
    elif main["checked"] and main["match"] == 0:
        method_ok = False
        note = (
            "nav kontroles kopas un sakritību ir nulle — 'viss stale' nav "
            "atšķirams no salauzta salīdzinājuma; vispirms verificē metodi"
        )
    return {
        "candidates": len(ids),
        "alive": len(alive),
        **main,
        "control": control,
        "method_ok": method_ok,
        "note": note,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ids", nargs="*", type=int, help="atsevišķi claim id")
    ap.add_argument("--ids-from", metavar="PATH", help="fails ar id pa rindai")
    ap.add_argument("--db", default=str(_REPO / "data" / "atmina.db"))
    ap.add_argument("--sample", type=int, default=300,
                    help="izlases lielums (0 = visa kopa)")
    ap.add_argument("--control-ids", metavar="PATH",
                    default=str(_REPO / "data" / "reembed_elektr_vectors_2026-08-03.ids"),
                    help="zināmi svaigu vektoru id (metodes kontrole)")
    ap.add_argument("--control-sample", type=int, default=25)
    args = ap.parse_args()

    ids = list(args.ids)
    if args.ids_from:
        ids += [int(x) for x in Path(args.ids_from).read_text().split()]
    if not ids:
        ids = extract_fix_file_ids(_REPO / "data")
        print(f"kandidāti no data/fix_*.sql: {len(ids)} id")

    control_ids: list[int] = []
    cpath = Path(args.control_ids) if args.control_ids else None
    if cpath and cpath.exists():
        control_ids = [int(x) for x in cpath.read_text().split()][: args.control_sample]

    rep = run_audit(args.db, ids, sample=args.sample, control_ids=control_ids)

    print(
        f"kandidāti={rep['candidates']} dzīvi={rep['alive']} "
        f"checked={rep['checked']} match={rep['match']} "
        f"stale={rep['stale']} missing={rep['missing']}"
    )
    print(
        f"kontrole: checked={rep['control']['checked']} "
        f"match={rep['control']['match']} stale={rep['control']['stale']}"
    )
    if rep["stale_ids"]:
        print(f"stale ids: {rep['stale_ids']}")
    if rep["note"]:
        print(f"NB: {rep['note']}")
    if not rep["method_ok"]:
        return 2
    return 1 if rep["stale"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
