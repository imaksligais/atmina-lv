"""Stance B_REWRITE 2026-09-30: 17 pārrakstījumi + 3 pārsaistīšanas (citātu triāžas stance karogi).

Ievade: docs/audits/2026-09-30-citatu-triaza/b_rewrite_verdicts.json (Opus verifikators, read-only;
orķestrators pārbaudīja LV vārtus). ACCEPT/ADJUST → `stance = final_stance`; WITHDRAW → claim +
vektors dzēsti (pretrunu atsauces = 0). Pārsaistīšana (#14346 → doc 26915, #7489 → 16619,
#18375 → 34583): `document_id` + `source_url` + `stated_at` (mērķa published_at) un
`quote` — paliek, ja ir burtiska mērķa teksta apakšvirkne, citādi verifikatora burtiskā apakšvirkne
vai NULL. Pirms raksta: idempotences trijnieka `(opponent_id, source_url, topic)` sadursmes pārbaude.

Rollback: data/rollback_stance_b_rewrite_2026-09-30.sql (pēc tā reembed_claims.py visiem ID).
Pēc apply: reembed_claims.py stance mainītajiem ID (skripts tos izdrukā).

    .venv/Scripts/python.exe scripts/_fix_stance_b_rewrite_2026_09_30.py            # dry-run
    .venv/Scripts/python.exe scripts/_fix_stance_b_rewrite_2026_09_30.py --apply
"""
import json
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import get_db  # noqa: E402

HERE = ROOT / "docs/audits/2026-09-30-citatu-triaza"
ROLLBACK = ROOT / "data/rollback_stance_b_rewrite_2026-09-30.sql"
REPOINT = {14346: 26915, 7489: 16619, 18375: 34583}
# Verifikators: stance pieņemams, bet balstās video auto-transkriptā (tvītā tikai saite) — stance netiek
# mainīts, reasoning saņem NEEDS_REVIEW marķieri, līdz operators pārbauda video.
HOLD = {689653: "NEEDS_REVIEW: stance un citāts balstās video auto-transkriptā, glabātajā tvītā ir tikai "
                "saite — jāpārbauda video (stance vērtējums 2026-09-30). "}


def lit(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return repr(v)
    return "'" + str(v).replace("'", "''") + "'"


def nfc(s):
    return unicodedata.normalize("NFC", s or "")


def stated(published_at):
    # Kā esošās X claims (#7489 pirms pārsaistīšanas): published_at laiks bez zonas pārrēķina.
    return datetime.fromisoformat(published_at).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")


def main(apply: bool) -> None:
    verdicts = {v["id"]: v for v in json.loads((HERE / "b_rewrite_verdicts.json").read_text(encoding="utf-8"))}
    inputs = {r["id"]: r for r in json.loads((HERE / "b_rewrite_input.json").read_text(encoding="utf-8"))}
    if set(verdicts) != set(inputs):
        sys.exit(f"STOP: verdiktu ID {sorted(verdicts)} != ievades ID {sorted(inputs)}")
    db = get_db(None)
    import sqlite_vec
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)
    cols = [r[1] for r in db.execute("PRAGMA table_info(claims)")]

    withdraw = tuple(i for i, v in verdicts.items() if v["verdict"] == "WITHDRAW")
    stance = {i: nfc(v["final_stance"]).strip() for i, v in verdicts.items() if v["verdict"] in ("ACCEPT", "ADJUST") and i not in HOLD}
    hold = {i: db.execute("SELECT reasoning FROM claims WHERE id=?", (i,)).fetchone()[0] for i in HOLD}
    problems = []
    for i in stance:
        cur = db.execute("SELECT stance FROM claims WHERE id=?", (i,)).fetchone()
        if cur is None or cur[0] != inputs[i]["current_stance"]:
            problems.append(f"{i}: claim nav vai stance mainījies kopš ievades")
        if not stance[i]:
            problems.append(f"{i}: tukšs final_stance")
    ph = ",".join("?" * len(withdraw)) or "NULL"
    wrows = db.execute(f"SELECT {','.join(cols)} FROM claims WHERE id IN ({ph})", withdraw).fetchall()
    refs = db.execute(f"SELECT count(*) FROM contradictions WHERE claim_old_id IN ({ph}) OR claim_new_id IN ({ph})",
                      withdraw + withdraw).fetchone()[0]
    if len(wrows) != len(withdraw) or refs:
        problems.append(f"withdraw atrasti {len(wrows)}/{len(withdraw)}, pretrunu atsauces {refs}")

    repoints = {}
    for cid, did in REPOINT.items():
        if cid in withdraw:
            continue
        v = verdicts[cid]
        if not v.get("repoint_ok"):
            problems.append(f"{cid}: verifikators repoint_ok != true")
            continue
        opp, topic, quote, old_doc, old_url, old_stated = db.execute(
            "SELECT opponent_id, topic, quote, document_id, source_url, stated_at FROM claims WHERE id=?", (cid,)).fetchone()
        url, pub, title, content = db.execute(
            "SELECT source_url, published_at, title, content FROM documents WHERE id=?", (did,)).fetchone()
        text = nfc(f"{title or ''}\n{content or ''}")
        if db.execute("SELECT id FROM claims WHERE opponent_id=? AND source_url=? AND topic=?", (opp, url, topic)).fetchone():
            problems.append(f"{cid}: idempotences sadursme uz {url}")
        if quote is not None and nfc(quote) in text:
            new_quote = quote
        else:
            new_quote = v.get("proposed_quote")
            if new_quote is not None and nfc(new_quote) not in text:
                problems.append(f"{cid}: proposed_quote nav burtiska mērķa apakšvirkne")
        repoints[cid] = dict(doc=did, url=url, stated=stated(pub), quote=new_quote,
                             old=(old_doc, old_url, old_stated, quote))

    print(f"withdraw {len(withdraw)} {list(withdraw)}; stance {len(stance)}; repoint {len(repoints)}; "
          f"NEEDS_REVIEW {list(hold)}")
    for cid, r in repoints.items():
        print(f"  #{cid}: doc {r['old'][0]} -> {r['doc']}, stated {r['old'][2]} -> {r['stated']}, "
              f"quote {'paliek' if r['quote'] == r['old'][3] else ('NULL' if r['quote'] is None else 'jauns burtisks')}")
    if problems:
        sys.exit("STOP:\n  " + "\n  ".join(problems))
    if not apply:
        return

    reembed = sorted(set(stance) | set(withdraw))
    ins_cols = [c for c in cols if c not in ("review_status", "review_status_at")]
    lines = ["-- Rollback: scripts/_fix_stance_b_rewrite_2026_09_30.py (apply 2026-09-30).",
             f"-- Atjauno {len(wrows)} dzēstās claims, {len(stance)} stance, {len(repoints)} pārsaistīšanas. Pēc tam: "
             ".venv/Scripts/python.exe scripts/reembed_claims.py " + " ".join(map(str, reembed)),
             "BEGIN;"]
    for r in wrows:
        d = dict(zip(cols, r))
        lines.append(f"INSERT INTO claims ({', '.join(ins_cols)}) VALUES ({', '.join(lit(d[c]) for c in ins_cols)});")
    lines += [f"UPDATE claims SET stance = {lit(inputs[i]['current_stance'])} WHERE id = {i};" for i in stance]
    for cid, r in repoints.items():
        od, ou, os_, oq = r["old"]
        lines.append(f"UPDATE claims SET document_id = {od}, source_url = {lit(ou)}, stated_at = {lit(os_)}, "
                     f"quote = {lit(oq)} WHERE id = {cid};")
    lines += [f"UPDATE claims SET reasoning = {lit(r)} WHERE id = {i};" for i, r in hold.items()]
    lines.append("COMMIT;")
    ROLLBACK.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with db:
        db.execute(f"DELETE FROM claim_vectors WHERE claim_id IN ({ph})", withdraw)
        db.execute(f"DELETE FROM claims WHERE id IN ({ph})", withdraw)
        for i, s in stance.items():
            db.execute("UPDATE claims SET stance = ? WHERE id = ?", (s, i))
        for cid, r in repoints.items():
            db.execute("UPDATE claims SET document_id=?, source_url=?, stated_at=?, quote=? WHERE id=?",
                       (r["doc"], r["url"], r["stated"], r["quote"], cid))
        for i, r in hold.items():
            db.execute("UPDATE claims SET reasoning = ? WHERE id = ?", (HOLD[i] + r, i))
    left = db.execute(f"SELECT count(*) FROM claims WHERE id IN ({ph})", withdraw).fetchone()[0]
    ok_s = sum(db.execute("SELECT stance = ? FROM claims WHERE id = ?", (s, i)).fetchone()[0] for i, s in stance.items())
    ok_h = sum(db.execute("SELECT reasoning = ? FROM claims WHERE id = ?", (HOLD[i] + r, i)).fetchone()[0]
               for i, r in hold.items())
    ok_r = sum(db.execute("SELECT document_id = ? AND source_url = ? AND quote IS ? FROM claims WHERE id = ?",
                          (r["doc"], r["url"], r["quote"], cid)).fetchone()[0] for cid, r in repoints.items())
    print(f"dzēsts {len(withdraw) - left}/{len(withdraw)}, stance {ok_s}/{len(stance)}, repoint {ok_r}/{len(repoints)}; "
          f"NEEDS_REVIEW {ok_h}/{len(hold)}; rollback {ROLLBACK.relative_to(ROOT)}")
    print("REEMBED:", " ".join(map(str, sorted(stance))))
    if left or ok_s != len(stance) or ok_r != len(repoints) or ok_h != len(hold):
        sys.exit("STOP: saglabāto skaits != plānotais")


if __name__ == "__main__":
    main("--apply" in sys.argv)
