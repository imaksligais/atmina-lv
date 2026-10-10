"""Labo divu 2026-09-24 balsojumu pārmantoto kopsavilkumu (votes 8321, 8322) + to claims.

`ingest_saeima_missing_votes.py` tiem ielika māsas kopsavilkumu ar CITA balsojuma
iznākumu (`backlog/saeima.md` [FIX]): 8321 nesa 17.09. frakciju sadalījumu
(«AS atturējās, bet NA nebalsoja» — faktiski abas par), 8322 nesa termiņa
balsojuma teikumu, bet balsojums ir par 2. lasījuma priekšlikumu Nr. 3.
Mainās tikai noslēguma teikums; `topic` nemainās, `saeima_vote` netiek embedēti.
Rollback: data/rollback_fix_inherited_vote_summaries_2026-09-24.sql
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.db import get_db  # noqa: E402

FIXES = {
    8321: ("Šis balsojums izšķīra tikai jautājuma iekļaušanu sēdes darba kārtībā; par balsoja ZZS, LPV un daļa pie frakcijām nepiederošo, pret — Jaunā Vienotība un Progresīvie, AS atturējās, bet NA nebalsoja.",
           "Šis balsojums izšķīra tikai jautājuma iekļaušanu nākamās kārtējās sēdes darba kārtībā."),
    8322: ("Šis balsojums izšķīra tikai to, vai priekšlikumu iesniegšanas termiņš otrajam lasījumam būtu viena diena.",
           "Šis balsojums bija par otrā lasījuma priekšlikumu Nr. 3, nevis par likumprojektu kopumā."),
}
CLAIM_IDS = (724774, 724918)


def main() -> int:
    apply = "--apply" in sys.argv
    db = get_db(None)
    for vid, (old, new) in FIXES.items():
        s = db.execute("SELECT summary FROM saeima_votes WHERE id=?", (vid,)).fetchone()[0]
        assert s.endswith(old), vid
        n = db.execute(
            "SELECT COUNT(*) FROM claims WHERE id BETWEEN ? AND ? AND stance LIKE ?",
            (*CLAIM_IDS, f"%{old}"),
        ).fetchone()[0]
        print(f"vote {vid}: summary 1, claims {n}")
        if apply:
            db.execute("UPDATE saeima_votes SET summary=? WHERE id=?", (s[: -len(old)] + new, vid))
            db.execute(
                "UPDATE claims SET stance = substr(stance, 1, length(stance) - ?) || ? "
                "WHERE id BETWEEN ? AND ? AND stance LIKE ?",
                (len(old), new, *CLAIM_IDS, f"%{old}"),
            )
    if apply:
        db.commit()
    print("applied" if apply else "dry-run")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
