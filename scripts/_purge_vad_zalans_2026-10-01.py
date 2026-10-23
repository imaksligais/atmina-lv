"""VAD homonīma purge: Jānis Zalāns (pid=186) — 16 Jēkabpils cietuma apsarga deklarācijas.

Operatora «ok, do it» 2026-10-01 (BACKLOG § verdiktu atlikums, `backlog/dati-db.md` (c)).
Pierādījums (runbook `wiki/operations/vad-declarations.md` § Homonīmu piesārņojums, ģimenes-paraksts):
decl 2208–2223 nes māti Zinaīdu, tēvu Albertu, sievu Litu (jau 2005) un pilngadīgu dēlu Armandu
no deklarācijas par 2012. gadu; kandidāts dzimis 1987 (CVK SV2026 81830) — pilngadīgs dēls 2013. gadā
nav iespējams. 2215 bez ģimenes sadaļas, bet tā pati «Apsargs» līnija starp 2214 un 2216.
Decl 2224–2226 (radiosakaru inženieris, māte Silvija) — cits cilvēks, bet nepierādāms → paliek flagged.

Konvencija kā 2026-09-19 purge: data/purge_vad_zalans_2026-10-01.sql + data/rollback_vad_zalans_2026-10-01.sql
(INSERT OR REPLACE rezerve) + data/vad_denylist.json ieraksti. Annual rindām stabilā (kind, year) kāja
(gadi 2005–2018 nesakrīt ar atlikušajām 2019–2020 rindām), interim — tikai uuid (year=None kāja
bloķētu arī likumīgās interim deklarācijas).

    .venv/Scripts/python.exe scripts/_purge_vad_zalans_2026-10-01.py           # dry-run
    .venv/Scripts/python.exe scripts/_purge_vad_zalans_2026-10-01.py --apply
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import get_db  # noqa: E402

PID = 186
IDS = tuple(range(2208, 2224))
KEEP = (2224, 2225, 2226)
MOTHER = "ZINAĪDA ZALĀNE"
PURGE = ROOT / "data/purge_vad_zalans_2026-10-01.sql"
ROLLBACK = ROOT / "data/rollback_vad_zalans_2026-10-01.sql"
DENY = ROOT / "data/vad_denylist.json"


def lit(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return repr(v)
    return "'" + str(v).replace("'", "''") + "'"


def main(apply: bool) -> None:
    db = get_db(None)
    ph = ",".join("?" * len(IDS))
    decl = db.execute(f"SELECT * FROM vad_declarations WHERE id IN ({ph}) ORDER BY id", IDS).fetchall()
    stop = []
    if len(decl) != len(IDS) or any(r["opponent_id"] != PID for r in decl):
        stop.append(f"atrastas {len(decl)}/{len(IDS)} vai cits opponent_id")
    if any("Apsargs" not in (r["position_title"] or "") and "apsargs" not in (r["position_title"] or "")
           for r in decl):
        stop.append("ne visas rindas ir apsarga līnija")
    n_mother = sum(1 for r in decl if MOTHER in (r["raw_html"] or ""))
    other_mother = [r["id"] for r in db.execute(
        f"SELECT id, raw_html FROM vad_declarations WHERE id IN ({','.join('?' * len(KEEP))})", KEEP)
        if MOTHER in (r["raw_html"] or "")]
    child = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'vad_%'")
             if "declaration_id" in [c[1] for c in db.execute(f"PRAGMA table_info({r[0]})")]]
    counts = {t: db.execute(f"SELECT count(*) FROM {t} WHERE declaration_id IN ({ph})", IDS).fetchone()[0]
              for t in child}
    deny = json.loads(DENY.read_text(encoding="utf-8"))
    have = {(e["pid"], e["vad_uuid"]) for e in deny["entries"]}
    new_entries = []
    for r in decl:
        if (PID, r["vad_uuid"]) in have:
            continue
        e = {"pid": PID, "vad_uuid": r["vad_uuid"]}
        if r["declaration_kind"] == "annual" and r["declaration_year"] is not None:
            e["match"] = {"kind": "annual", "year": r["declaration_year"]}
        e["reason"] = (f"Jānis Zalāns: Jēkabpils cietuma apsargs (vārdabrālis; māte Zinaīda, pilngadīgs dēls "
                       f"no 2012 — kandidāts dz. 1987) (decl id {r['id']})")
        new_entries.append(e)
    print(f"deklarācijas {len(decl)}/{len(IDS)}; ar māti {MOTHER} {n_mother} (2215 bez ģimenes sadaļas); "
          f"paliekošajās {list(KEEP)} šī māte: {other_mother}")
    print("apakšrindas: " + ", ".join(f"{t}={n}" for t, n in counts.items() if n))
    print(f"denylist: {len(deny['entries'])} → +{len(new_entries)} "
          f"({sum(1 for e in new_entries if 'match' in e)} stabili, "
          f"{sum(1 for e in new_entries if 'match' not in e)} uuid-only)")
    if other_mother or n_mother < len(IDS) - 1:
        stop.append("ģimenes paraksts neatbilst gaidītajam")
    if stop:
        sys.exit("STOP: " + "; ".join(stop))
    if not apply:
        print("(dry-run — nekas nav rakstīts; --apply lai rakstītu)")
        return

    idlist = ",".join(map(str, IDS))
    rb = [f"-- ROLLBACK: scripts/_purge_vad_zalans_2026-10-01.py (apply 2026-10-01) — atjauno {len(IDS)} "
          "deklarācijas + apakšrindas; denylist ierakstus (decl id 2208–2223) izņem ar roku.", "BEGIN;"]
    for t in ["vad_declarations"] + child:
        key = "id" if t == "vad_declarations" else "declaration_id"
        cols = [c[1] for c in db.execute(f"PRAGMA table_info({t})")]
        for r in db.execute(f"SELECT {','.join(cols)} FROM {t} WHERE {key} IN ({ph})", IDS):
            rb.append(f"INSERT OR REPLACE INTO {t} ({','.join(cols)}) VALUES ({','.join(lit(v) for v in r)});")
    rb.append("COMMIT;")
    ROLLBACK.write_text("\n".join(rb) + "\n", encoding="utf-8")
    purge = [f"-- PURGE Zalāns (pid=186) apsarga tādvārdis, {len(IDS)} dekl. — ģimenes-paraksts (2026-10-01)",
             "BEGIN;", f"DELETE FROM vad_declarations WHERE id IN ({idlist});"]
    purge += [f"DELETE FROM {t} WHERE declaration_id IN ({idlist});" for t in child]
    purge.append("COMMIT;")
    PURGE.write_text("\n".join(purge) + "\n", encoding="utf-8")
    print(f"rollback + purge uzrakstīti PIRMS izmaiņām: {ROLLBACK.name}, {PURGE.name}")

    with db:
        db.execute(f"DELETE FROM vad_declarations WHERE id IN ({ph})", IDS)
        for t in child:
            db.execute(f"DELETE FROM {t} WHERE declaration_id IN ({ph})", IDS)
    deny["entries"].extend(new_entries)
    DENY.write_text(json.dumps(deny, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    left = db.execute(f"SELECT count(*) FROM vad_declarations WHERE id IN ({ph})", IDS).fetchone()[0]
    left_child = sum(db.execute(f"SELECT count(*) FROM {t} WHERE declaration_id IN ({ph})", IDS).fetchone()[0]
                     for t in child)
    kept = db.execute("SELECT count(*) FROM vad_declarations WHERE opponent_id=?", (PID,)).fetchone()[0]
    print(f"dzēstas {len(IDS) - left}/{len(IDS)}; apakšrindas atlikušas {left_child}; pid=186 paliek {kept} "
          f"(gaidīts {len(KEEP)}); denylist tagad {len(deny['entries'])}")
    if left or left_child or kept != len(KEEP):
        sys.exit("STOP: saglabāts != iecerēts")


if __name__ == "__main__":
    main("--apply" in sys.argv)
