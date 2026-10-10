"""Atsauc #729774 (Krištopans, RT no @taukacs — trešās puses vārdi, ne paša) — operatora lēmums 2026-10-03.

Tajā pašā solī izņem tās rindu no publicētā 2026-10-02 pārskata (#672) tabulas.
Avota dokuments 122078 paliek (paša RT ir X apakšcilnē kā spogulis; CLAUDE.md § Deleting a claim).
Bez karoga: pārbauda + uzraksta rollback (komitē PIRMS apply). `--apply`: dzēš + labo #672.
Rollback: data/rollback_withdraw_kristopans_rt_2026-10-03.sql (pēc tā reembed_claims.py 729774).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import get_db  # noqa: E402

CID = 729774
NOTE_ID = 672
URL = "https://x.com/Chapis/status/2105928451635007662"
ROLLBACK = ROOT / "data/rollback_withdraw_kristopans_rt_2026-10-03.sql"


def lit(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return repr(v)
    return "'" + str(v).replace("'", "''") + "'"


def strip_row(text: str) -> str:
    lines = text.split("\n")
    hits = [i for i, ln in enumerate(lines) if URL in ln]
    if len(hits) != 1 or not lines[hits[0]].lstrip().startswith("|"):
        sys.exit(f"STOP: #{NOTE_ID} sagaidīta 1 tabulas rinda ar URL, atrastas {len(hits)}")
    del lines[hits[0]]
    return "\n".join(lines)


def main(apply: bool) -> None:
    db = get_db(None)
    import sqlite_vec
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)

    cols = [r[1] for r in db.execute("PRAGMA table_info(claims)")]
    row = db.execute(f"SELECT {','.join(cols)} FROM claims WHERE id=?", (CID,)).fetchone()
    refs = db.execute(
        "SELECT count(*) FROM contradictions WHERE claim_old_id=? OR claim_new_id=?", (CID, CID)
    ).fetchone()[0]
    nvec = db.execute("SELECT count(*) FROM claim_vectors WHERE claim_id=?", (CID,)).fetchone()[0]
    note = db.execute("SELECT content FROM context_notes WHERE id=?", (NOTE_ID,)).fetchone()[0]
    new_note = strip_row(note)
    print(f"claim {'1' if row else '0'}/1, vektori {nvec}, pretrunu atsauces {refs}, "
          f"#{NOTE_ID} {len(note)} → {len(new_note)} zīmes")
    if not row or refs:
        sys.exit("STOP: trūkst rindas vai ir pretrunu atsauces")

    if not apply:
        d = dict(zip(cols, row))
        ins_cols = [c for c in cols if c not in ("review_status", "review_status_at")]
        ROLLBACK.write_text(
            "\n".join([
                "-- Rollback: scripts/_fix_withdraw_kristopans_rt_2026_10_03.py (apply 2026-10-03).",
                f"-- Forward: DELETE claim #{CID} (+ vektors); izņemta tās rinda no context_notes #{NOTE_ID}.",
                f"-- Pēc šī: .venv/Scripts/python.exe scripts/reembed_claims.py {CID}",
                "BEGIN;",
                f"INSERT INTO claims ({', '.join(ins_cols)}) VALUES ({', '.join(lit(d[c]) for c in ins_cols)});",
                f"UPDATE context_notes SET content = {lit(note)} WHERE id = {NOTE_ID};",
                "COMMIT;",
            ]) + "\n",
            encoding="utf-8",
        )
        print(f"rollback uzrakstīts: {ROLLBACK.relative_to(ROOT)} — komitē, tad --apply")
        return

    if not ROLLBACK.exists():
        sys.exit("STOP: nav rollback faila")
    with db:
        db.execute("DELETE FROM claim_vectors WHERE claim_id=?", (CID,))
        db.execute("DELETE FROM claims WHERE id=?", (CID,))
        db.execute("UPDATE context_notes SET content=? WHERE id=?", (new_note, NOTE_ID))
    left = db.execute("SELECT count(*) FROM claims WHERE id=?", (CID,)).fetchone()[0]
    still = URL in db.execute("SELECT content FROM context_notes WHERE id=?", (NOTE_ID,)).fetchone()[0]
    print(f"dzēsts {1 - left}/1; URL #{NOTE_ID}: {'PALIEK' if still else 'izņemts'}")
    if left or still:
        sys.exit("STOP")


if __name__ == "__main__":
    main("--apply" in sys.argv)
