"""Operatora verdikti 2026-10-01 (docs/verdikti-2026-10-01.md C4, C6, C7) — stance izlases atlikumi.

Avoti: docs/audits/2026-09-30-stance-izlase/README.md § Blakusatradumi,
docs/HANDOFF-2026-09-30-claim-extractor-parbuve.md § Atvērtie operatora jautājumi.

C4 — dublikāti (paturēts pilnākais; tikai tur, kur viena stance ir otras apakškopa):
  #6802 ⊂ #6683 (tas pats LETA teksts pmo.ee; #6683 un #6734 paliek — #6734 nes JV pienākumu);
  #6844 ~ #425 (tas pats tvīts; #6844 piebilst tikai pēdējo teikumu, verifikators piedāvāja atsaukt);
  #11211 ⊂ #11172 (tas pats LETA teksts diena.lv; #11172 pilnāks);
  #428 = #411 (tas pats tvīts, divas `documents` rindas 6048/6130; #411 no paša plūsmas, conf 0,88).
  NEaiztikti (atšķirīgs saturs vai neviennozīmīgi — operatoram): #6677/#6678, #43/#6902,
  #7469/#7507, #7301/#11039; #7040 ir C8 HOLD.
C6 — datu posti bez viedokļa: #254, #7397, #310, #21.
C7 — tēma: #6659 airBaltic → Valsts kapitālsabiedrības (glabātajā tekstā airBaltic nav nosaukts);
  #11043 Sociālā politika → Veselības aprūpe. Sadursmes vaicājums (opponent_id, source_url, jaunā tēma)
  pārbaudīts skriptā; pēc --apply: scripts/reembed_claims.py 6659 11043.
C3 (15 U) NAV šeit: backfill_truncated_docs.py atlasa tikai platform='web', visi 15 ir tvīti.

Avota dokumenti paliek (CLAUDE.md § Deleting a claim). Pretrunu atsauces pārbauda skripts (STOP, ja >0).
Rollback: data/rollback_stance_leftovers_2026-10-01.sql (INSERT + topic UPDATE; pēc tā
`scripts/reembed_claims.py` visiem rollback galvenē minētajiem id).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import get_db  # noqa: E402

WITHDRAW = {
    "C4": (6802, 6844, 11211, 428),
    "C6": (254, 7397, 310, 21),
}
TOPIC = {  # id: (vecā tēma, jaunā tēma)
    6659: ("airBaltic", "Valsts kapitālsabiedrības"),
    11043: ("Sociālā politika", "Veselības aprūpe"),
}
ROLLBACK = ROOT / "data/rollback_stance_leftovers_2026-10-01.sql"


def lit(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return repr(v)
    return "'" + str(v).replace("'", "''") + "'"


def main(apply: bool) -> None:
    db = get_db(None)
    import sqlite_vec
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)

    from src.topic_map import normalize_topic

    wd = tuple(i for ids in WITHDRAW.values() for i in ids)
    allids = wd + tuple(TOPIC)
    ph = ",".join("?" * len(wd))
    pha = ",".join("?" * len(allids))
    cols = [r[1] for r in db.execute("PRAGMA table_info(claims)")]
    rows = db.execute(f"SELECT {','.join(cols)} FROM claims WHERE id IN ({ph})", wd).fetchall()
    refs = db.execute(
        f"SELECT count(*) FROM contradictions WHERE claim_old_id IN ({pha}) OR claim_new_id IN ({pha})",
        allids + allids,
    ).fetchone()[0]
    nvec = db.execute(f"SELECT count(*) FROM claim_vectors WHERE claim_id IN ({ph})", wd).fetchone()[0]
    for cls, ids in WITHDRAW.items():
        print(f"{cls}: atsaukt {len(ids)} — {', '.join('#' + str(i) for i in ids)}")
    print(f"atsaucamās claims atrastas {len(rows)}/{len(wd)}, vektori {nvec}, "
          f"pretrunu atsauces {refs} (pārbaudīti {len(allids)} id)")
    if len(rows) != len(wd) or refs:
        sys.exit("STOP: trūkst rindu vai ir pretrunu atsauces")

    for cid, (old, new) in TOPIC.items():
        r = db.execute("SELECT opponent_id, source_url, topic, claim_type FROM claims WHERE id=?", (cid,)).fetchone()
        if r is None or r["topic"] != old or r["claim_type"] != "position":
            sys.exit(f"STOP: #{cid} nav gaidītajā stāvoklī ({None if r is None else dict(r)})")
        if normalize_topic(new) != new:
            sys.exit(f"STOP: '{new}' nav kanoniska tēma")
        coll = db.execute(
            "SELECT id FROM claims WHERE opponent_id=? AND source_url=? AND topic=? AND id!=?",
            (r["opponent_id"], r["source_url"], new, cid),
        ).fetchall()
        print(f"C7: #{cid} tēma '{old}' → '{new}'; sadursmes {len(coll)}")
        if coll:
            sys.exit(f"STOP: #{cid} jaunā tēma sadurtos ar {[c[0] for c in coll]}")
    if not apply:
        print("(dry-run — nekas nav rakstīts; --apply lai rakstītu)")
        return

    # review_status/_at atvasina trigeri no reasoning — INSERT tos neraksta.
    ins_cols = [c for c in cols if c not in ("review_status", "review_status_at")]
    reembed = " ".join(map(str, wd + tuple(TOPIC)))
    lines = ["-- Rollback: scripts/_fix_stance_leftovers_2026-10-01.py (apply 2026-10-01).",
             f"-- Forward: atsauktas {len(rows)} claims (C4 {WITHDRAW['C4']}, C6 {WITHDRAW['C6']}); "
             f"tēma mainīta #6659, #11043 (C7).",
             f"-- Pēc rollback: .venv/Scripts/python.exe scripts/reembed_claims.py {reembed}",
             "BEGIN;"]
    for r in rows:
        d = dict(zip(cols, r))
        lines.append(f"INSERT INTO claims ({', '.join(ins_cols)}) VALUES ({', '.join(lit(d[c]) for c in ins_cols)});")
    for cid, (old, _new) in TOPIC.items():
        lines.append(f"UPDATE claims SET topic = {lit(old)} WHERE id = {cid};")
    lines.append("COMMIT;")
    ROLLBACK.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"rollback uzrakstīts PIRMS izmaiņām: {ROLLBACK.relative_to(ROOT)}")

    with db:
        db.execute(f"DELETE FROM claim_vectors WHERE claim_id IN ({ph})", wd)
        db.execute(f"DELETE FROM claims WHERE id IN ({ph})", wd)
        for cid, (old, new) in TOPIC.items():
            db.execute("UPDATE claims SET topic=? WHERE id=? AND topic=?", (new, cid, old))

    left = db.execute(f"SELECT count(*) FROM claims WHERE id IN ({ph})", wd).fetchone()[0]
    for cls, ids in WITHDRAW.items():
        p = ",".join("?" * len(ids))
        n = db.execute(f"SELECT count(*) FROM claims WHERE id IN ({p})", ids).fetchone()[0]
        print(f"{cls}: dzēsts {len(ids) - n}/{len(ids)}")
    tok = sum(
        1 for cid, (_o, new) in TOPIC.items()
        if db.execute("SELECT topic FROM claims WHERE id=?", (cid,)).fetchone()[0] == new
    )
    print(f"C7: tēma mainīta {tok}/{len(TOPIC)}; tagad: .venv/Scripts/python.exe scripts/reembed_claims.py "
          + " ".join(map(str, TOPIC)))
    if left or tok != len(TOPIC):
        sys.exit("STOP: saglabāts != iecerēts")


if __name__ == "__main__":
    main("--apply" in sys.argv)
