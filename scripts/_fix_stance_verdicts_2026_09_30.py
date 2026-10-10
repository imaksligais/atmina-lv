"""Stance pret avotu 2026-09-30: verificēto verdiktu piemērošana (izlase 300 + aprīļa pilnā pārbaude).

Ievade: viens vai vairāki `verify_out*.json` (Opus verifikators pret avotu + LV vārti, rubrika
`docs/audits/2026-09-30-stance-izlase/RUBRIKA.md`) un tiem atbilstošie `verify_in*.json` (tur ir
`current_stance`, pret ko pārbauda, ka rinda nav mainījusies). Verdikti:
  WITHDRAW → claim + vektors dzēsti (pretrunu atsauces = 0, citādi STOP);
  ACCEPT/ADJUST → `stance = final_stance`, pēc tam re-embed;
  KEEP/HOLD → netiek aiztikti (HOLD saraksts operatoram).
Avota dokumenti paliek (claim atsaukums nav dokumenta dzēšana).

    .venv/Scripts/python.exe scripts/_fix_stance_verdicts_2026_09_30.py <scope> <in.json:out.json> ...           # dry-run
    .venv/Scripts/python.exe scripts/_fix_stance_verdicts_2026_09_30.py <scope> <in.json:out.json> ... --apply

Rollback: data/rollback_stance_<scope>_2026-09-30.sql (+ `.ids` re-embed sarakstam).
"""
import json
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import get_db  # noqa: E402


def lit(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return repr(v)
    return "'" + str(v).replace("'", "''") + "'"


def main(scope: str, pairs: list[str], apply: bool) -> None:
    rollback = ROOT / f"data/rollback_stance_{scope}_2026-09-30.sql"
    verdicts, current = {}, {}
    for pair in pairs:
        fin, fout = pair.split(":")
        for r in json.loads((ROOT / fin).read_text(encoding="utf-8")):
            current[r["id"]] = r["current_stance"]
        for v in json.loads((ROOT / fout).read_text(encoding="utf-8")):
            if v["id"] in verdicts:
                sys.exit(f"STOP: {v['id']} divos verdiktu failos")
            verdicts[v["id"]] = v
    if set(verdicts) - set(current):
        sys.exit(f"STOP: verdikti bez ievades {sorted(set(verdicts) - set(current))}")
    missing_v = sorted(set(current) - set(verdicts))

    withdraw = tuple(i for i, v in verdicts.items() if v["verdict"] == "WITHDRAW")
    stance = {i: unicodedata.normalize("NFC", v["final_stance"] or "").strip()
              for i, v in verdicts.items() if v["verdict"] in ("ACCEPT", "ADJUST")}
    hold = sorted(i for i, v in verdicts.items() if v["verdict"] == "HOLD")
    unknown = sorted(i for i, v in verdicts.items() if v["verdict"] not in ("WITHDRAW", "ACCEPT", "ADJUST", "KEEP", "HOLD"))

    db = get_db(None)
    import sqlite_vec
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)
    cols = [r[1] for r in db.execute("PRAGMA table_info(claims)")]
    problems = [f"nezināms verdikts {unknown}"] if unknown else []
    for i in list(stance) + list(withdraw):
        cur = db.execute("SELECT stance FROM claims WHERE id=?", (i,)).fetchone()
        if cur is None or cur[0] != current[i]:
            problems.append(f"{i}: claim nav vai stance mainījies kopš ievades")
    problems += [f"{i}: tukšs final_stance" for i, s in stance.items() if not s]
    ph = ",".join("?" * len(withdraw)) or "NULL"
    wrows = db.execute(f"SELECT {','.join(cols)} FROM claims WHERE id IN ({ph})", withdraw).fetchall()
    refs = db.execute(f"SELECT claim_old_id, claim_new_id FROM contradictions WHERE claim_old_id IN ({ph}) OR claim_new_id IN ({ph})",
                      withdraw + withdraw).fetchall()
    if refs:
        problems.append(f"pretrunu atsauces uz atsaucamajiem: {[tuple(r) for r in refs]}")

    print(f"{scope}: verdikti {len(verdicts)} (bez verdikta {len(missing_v)}); WITHDRAW {len(withdraw)}, "
          f"stance {len(stance)}, KEEP {sum(v['verdict'] == 'KEEP' for v in verdicts.values())}, HOLD {len(hold)} {hold}")
    if problems:
        sys.exit("STOP:\n  " + "\n  ".join(problems))
    if not apply:
        return

    reembed = sorted(set(stance) | set(withdraw))
    ids_file = rollback.with_suffix(".ids")
    ids_file.write_text("\n".join(map(str, reembed)) + "\n", encoding="utf-8")
    ins_cols = [c for c in cols if c not in ("review_status", "review_status_at")]
    lines = [f"-- Rollback: scripts/_fix_stance_verdicts_2026_09_30.py {scope} (apply 2026-09-30).",
             f"-- Atjauno {len(wrows)} dzēstās claims un {len(stance)} stance. Pēc tam: "
             f".venv/Scripts/python.exe scripts/reembed_claims.py --ids-from {ids_file.relative_to(ROOT).as_posix()}",
             "BEGIN;"]
    for r in wrows:
        d = dict(zip(cols, r))
        lines.append(f"INSERT INTO claims ({', '.join(ins_cols)}) VALUES ({', '.join(lit(d[c]) for c in ins_cols)});")
    lines += [f"UPDATE claims SET stance = {lit(current[i])} WHERE id = {i};" for i in stance]
    lines.append("COMMIT;")
    rollback.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with db:
        db.execute(f"DELETE FROM claim_vectors WHERE claim_id IN ({ph})", withdraw)
        db.execute(f"DELETE FROM claims WHERE id IN ({ph})", withdraw)
        for i, s in stance.items():
            db.execute("UPDATE claims SET stance = ? WHERE id = ?", (s, i))
    left = db.execute(f"SELECT count(*) FROM claims WHERE id IN ({ph})", withdraw).fetchone()[0]
    ok = sum(db.execute("SELECT stance = ? FROM claims WHERE id = ?", (s, i)).fetchone()[0] for i, s in stance.items())
    print(f"dzēsts {len(withdraw) - left}/{len(withdraw)}, stance {ok}/{len(stance)}; rollback {rollback.relative_to(ROOT)}")
    stance_ids = rollback.with_name(rollback.stem + "_stance.ids")
    stance_ids.write_text("\n".join(map(str, sorted(stance))) + "\n", encoding="utf-8")
    print(f"REEMBED: --ids-from {stance_ids.relative_to(ROOT).as_posix()}")
    if left or ok != len(stance):
        sys.exit("STOP: saglabāto skaits != plānotais")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--apply"]
    main(args[0], args[1:], "--apply" in sys.argv)
