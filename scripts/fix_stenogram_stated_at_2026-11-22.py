"""Vēstneša Saeimas stenogrammu pozīcijām `stated_at` = sēdes diena (backlog/avoti.md 2026-11-20).

Noteikums `.claude/references/claim-extractor/datumi-dublikati.md` § 3 (operators 2026-10-21):
stenogrammai `stated_at` = sēdes diena. Mērīts 2026-11-22: 130 stenogrammu pozīcijas
(dokumenta virsraksts «… Saeimas … sēde …», URL vestnesis.lv), 101 ar `stated_at` ≠ sēdes
dienai — visas 101 = Vēstneša `published_at`, visas izveidotas 2026-10 (pēdējās 40 — 21.10.
vakarā, pirms noteikums sasniedza ekstraktoru), 0 pretrunās. Sēdes diena = PĒDĒJAIS datums
virsrakstā (turpinājuma sēde: «… 17. septembra … sēdes turpinājums 2026. gada 24. septembrī»;
pārbaudīts 6 turpinājumu doku galvenēs).

    .venv/Scripts/python.exe scripts/fix_stenogram_stated_at_2026-11-22.py          # dry-run + rollback
    .venv/Scripts/python.exe scripts/fix_stenogram_stated_at_2026-11-22.py --apply

Rollback: data/rollback_stenogram_stated_at_2026-11-22.sql. Re-embed nav vajadzīgs (vektors
ir `topic: stance`).
"""
import re
import sqlite3
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.db import PRODUCTION_DB_PATH  # noqa: E402

ROLLBACK = ROOT / "data/rollback_stenogram_stated_at_2026-11-22.sql"
MONTHS = {"janvār": 1, "februār": 2, "mart": 3, "aprīl": 4, "maij": 5, "jūnij": 6,
          "jūlij": 7, "august": 8, "septembr": 9, "oktobr": 10, "novembr": 11, "decembr": 12}
EXPECTED = 101


def sitting_day(title: str) -> str | None:
    ms = list(re.finditer(r"(\d{4})\. gada (\d{1,2})\. (\w+)", title))
    if not ms:
        return None
    y, d, word = ms[-1].groups()
    mon = next((v for k, v in MONTHS.items() if word.startswith(k)), None)
    return f"{y}-{mon:02d}-{int(d):02d}" if mon else None


def main(apply: bool) -> None:
    db = sqlite3.connect(PRODUCTION_DB_PATH)
    rows = db.execute(
        """SELECT cl.id, cl.stated_at, d.title, substr(d.published_at, 1, 10)
           FROM claims cl JOIN documents d ON d.id = cl.document_id
           WHERE d.title LIKE '%Saeimas%sēde%' AND d.source_url LIKE '%vestnesis.lv%'
             AND cl.claim_type = 'position'"""
    ).fetchall()
    todo = []
    for cid, st, title, pub in rows:
        day = sitting_day(title)
        if day is None:
            sys.exit(f"STOP: {cid} virsrakstā nav datuma: {title!r}")
        if not st.startswith(day):
            if st[:10] != pub:
                sys.exit(f"STOP: {cid} stated_at {st} nav ne sēdes, ne publicēšanas diena")
            todo.append((cid, st, f"{day} 00:00:00"))
    print(f"stenogrammu pozīcijas {len(rows)}, labojamas {len(todo)}")
    if len(todo) != EXPECTED:
        sys.exit(f"STOP: gaidīts {EXPECTED}, atrasts {len(todo)}")
    lines = ["-- Rollback: scripts/fix_stenogram_stated_at_2026-11-22.py (apply 2026-11-22).",
             f"-- Forward: claims.stated_at = sēdes diena {len(todo)} stenogrammu pozīcijām.",
             "BEGIN;"]
    lines += [f"UPDATE claims SET stated_at = '{old}' WHERE id = {cid};" for cid, old, _ in todo]
    lines.append("COMMIT;")
    ROLLBACK.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"rollback: {ROLLBACK.relative_to(ROOT)}")
    if not apply:
        return
    with db:
        n = sum(db.execute("UPDATE claims SET stated_at = ? WHERE id = ? AND stated_at = ?",
                           (new, cid, old)).rowcount for cid, old, new in todo)
        if n != len(todo):
            raise SystemExit(f"STOP: mainītas {n} no {len(todo)} — atcelts")
    print(f"mainītas {n} rindas")


if __name__ == "__main__":
    main("--apply" in sys.argv)
