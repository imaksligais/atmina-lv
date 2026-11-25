"""Atvērto darbu labojumi 2026-11-22 (handoff 22.11. «Gaida operatoru» 2, 6; 20.11. 754770).

- 755930 (Ceriņš): NEEDS_REVIEW atrisināts — tvīta 3. attēls ir grafiks «Latvijas
  vispārējās valdības parāds 2010–2026», tātad «3x audzēts» = valdības parāds.
  Labo stance + reasoning («Izvērtēts 2026-11-22:»), pēc tam re-embed.
- 755905 (Žuravļevs): reasoning «Tetarenko-Supes 21.11. ieraksts» → «20.11.»
  (tvīta ID 2123758674858615289 = 2026-11-20 12:41 UTC).
- 754770 (Vitenbergs): reasoning «(komentēja LTV)» — rakstā Vitenbergu citē
  bez LTV; LTV saistīta tikai ar Avotu. Noņem.

Rollback: data/rollback_open_items_2026-11-22.sql (uzrakstīts PIRMS labojuma
no pašreizējām vērtībām). Lietojums: .venv/Scripts/python.exe scripts/fix_open_items_2026-11-22.py
"""
import sqlite3
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.db import PRODUCTION_DB_PATH  # noqa: E402

ROLLBACK = ROOT / "data" / "rollback_open_items_2026-11-22.sql"

C930_STANCE = (
    "Kritizē «Jaunās Vienotības» un citu retoriku, it kā tie būtu radījuši Šveici, "
    "un apgalvo, ka vispārējās valdības parāds kopš 2010. gada palielinājies trīs reizes "
    "(no 8,5 līdz ~21,6 miljardiem eiro), bet Dombrovska, Kariņa, Siliņas un Ašeradena "
    "algas šajā laikā bijušas «COSMOSS»."
)
C930_REASONING_PREFIX = (
    "Izvērtēts 2026-11-22: tvītam pievienoti 3 attēli (fxtwitter metadati); 3. attēls ir "
    "grafiks «Latvijas vispārējās valdības parāds 2010–2026 (kopš Vienotības valdīšanas "
    "sākuma)» — stabiņi no ~8,5 līdz ~21,6 mljrd. EUR, tātad «3x audzēts» = valdības "
    "parāds; stance precizēts. 1.–2. attēls: Siliņas 12.11. tvīts par budžetu un LTV "
    "par Dombrovska izaugsmes prognozi. Sākotnēji: "
)
OLD_930_MARK = "NEEDS_REVIEW: tvītam pievienots attēls vai saite (t.co), ko nevar redzēt; tvīts nenosauc, kas «3x audzēts» (no 8,5 līdz ~21,6 miljardiem). "


def q(s):
    return "NULL" if s is None else "'" + s.replace("'", "''") + "'"


def main():
    db = sqlite3.connect(PRODUCTION_DB_PATH)
    rows = {
        r[0]: (r[1], r[2])
        for r in db.execute(
            "SELECT id, stance, reasoning FROM claims WHERE id IN (755930, 755905, 754770)"
        )
    }
    assert len(rows) == 3, rows.keys()

    new = {}
    st, rs = rows[755930]
    assert rs.startswith(OLD_930_MARK), rs[:120]
    new[755930] = (C930_STANCE, C930_REASONING_PREFIX + rs[len(OLD_930_MARK):])

    st, rs = rows[755905]
    assert rs.count("Tetarenko-Supes 21.11. ieraksts") == 1
    new[755905] = (st, rs.replace("Tetarenko-Supes 21.11. ieraksts", "Tetarenko-Supes 20.11. ieraksts"))

    st, rs = rows[754770]
    assert rs.count(" (komentēja LTV)") == 1
    new[754770] = (st, rs.replace(" (komentēja LTV)", ""))

    lines = [
        "-- Rollback: scripts/fix_open_items_2026-11-22.py (apply 2026-11-22).",
        "-- Forward: 755930 stance+reasoning (NEEDS_REVIEW atrisināts), 755905 un 754770 reasoning.",
        "-- Pēc rollback: .venv/Scripts/python.exe scripts/reembed_claims.py 755930",
        "BEGIN;",
    ]
    for cid, (st, rs) in rows.items():
        lines.append(f"UPDATE claims SET stance = {q(st)}, reasoning = {q(rs)} WHERE id = {cid};")
    lines.append("COMMIT;")
    ROLLBACK.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("rollback:", ROLLBACK)

    if "--apply" not in sys.argv:
        for cid, (st, rs) in new.items():
            print(cid, "\n  S:", st, "\n  R:", rs[:300])
        print("dry-run; pass --apply")
        return
    with db:
        for cid, (st, rs) in new.items():
            n = db.execute(
                "UPDATE claims SET stance = ?, reasoning = ? WHERE id = ?", (st, rs, cid)
            ).rowcount
            assert n == 1
    for r in db.execute(
        "SELECT id, review_status FROM claims WHERE id IN (755930, 755905, 754770)"
    ):
        print(r)


if __name__ == "__main__":
    main()
