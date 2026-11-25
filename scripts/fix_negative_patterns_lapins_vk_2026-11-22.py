"""negative_patterns Lapiņam (218) un Valsts kontrolei (241) + saite 133481→241 (operatora uzdevums 2026-11-22).

Dry-run pret visiem 218/241 saistītajiem un 2026-09+ «Lapiņ/Lapin» dokiem (1 415 doki):
- 218: atmet 4 citu Lapiņu dokus (32013, 117426, 133403, 150439), 0 īstu saišu.
- 241: «Segalovič»/«Segalovic» (Lietuvas valsts kontroliere) atmet 133481, 162340, 0 LV saišu.
  «Lietuvas Valsts kontrol» NEliek — vetotu LV stenogrammu 141308; «Seim» vetotu 3 LV dokus.
Saite 133481→241 (Delfi par Lietuvas VK renovācijas revīziju, 0 pozīciju) noņemta (DELETE
ieraksta apslāpēšanu).

    .venv/Scripts/python.exe scripts/fix_negative_patterns_lapins_vk_2026-11-22.py          # dry-run + rollback
    .venv/Scripts/python.exe scripts/fix_negative_patterns_lapins_vk_2026-11-22.py --apply

Rollback: data/rollback_negative_patterns_lapins_vk_2026-11-22.sql.
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import get_db  # noqa: E402

NEW = {
    218: ["Raimonds Lapiņš", "Raimonda Lapiņa", "Raimonda „Lapiņa", "R. Lapiņš", "Artis Lapiņš",
          "Arta Lapiņa", "A. Lapiņš", "A. Lapiņa", "Jānis Lapiņš", "Jāņa Lapiņa",
          # + 3 formas (X lietotājs; 2026-11-22 piemērotas) — privātā piezīmē docs/plans/2026-11-25-privatas-piezimes.md
          "Salvis Lapiņš", "Raimonds Lapins", "R. Lapins", "Artis Lapins",
          "A. Lapins", "Janis Lapins", "Salvis Lapins"],
    241: ["Segalovič", "Segalovic"],
}
LINKS = [(133481, 241)]
ROLLBACK = ROOT / "data/rollback_negative_patterns_lapins_vk_2026-11-22.sql"


def lit(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return repr(v)
    return "'" + str(v).replace("'", "''") + "'"


def main(apply: bool) -> None:
    db = get_db(None)
    lcols = [r[1] for r in db.execute("PRAGMA table_info(document_politicians)")]
    lines = ["-- Rollback: scripts/fix_negative_patterns_lapins_vk_2026-11-22.py (apply 2026-11-22).",
             "-- Forward: negative_patterns pid 218, 241; DELETE document_politicians 133481/241.",
             "BEGIN;"]
    old = {}
    for pid in NEW:
        old[pid] = db.execute("SELECT negative_patterns FROM tracked_politicians WHERE id=?", (pid,)).fetchone()[0]
        lines.append(f"UPDATE tracked_politicians SET negative_patterns = {lit(old[pid])} WHERE id = {pid};")
    for d, p in LINKS:
        row = db.execute("SELECT * FROM document_politicians WHERE document_id=? AND politician_id=?", (d, p)).fetchone()
        if row is None:
            sys.exit(f"STOP: saite {d}/{p} nav atrasta")
        if db.execute("SELECT 1 FROM claims WHERE document_id=? AND opponent_id=?", (d, p)).fetchone():
            sys.exit(f"STOP: saitei {d}/{p} ir pozīcijas")
        lines.append(f"INSERT INTO document_politicians ({', '.join(lcols)}) VALUES "
                     f"({', '.join(lit(row[c]) for c in lcols)});")
    lines.append("COMMIT;")
    ROLLBACK.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"rollback: {ROLLBACK.relative_to(ROOT)}; vecās vērtības {old}")
    if not apply:
        return
    with db:
        for pid, pats in NEW.items():
            merged = list(dict.fromkeys((json.loads(old[pid]) if old[pid] else []) + pats))
            db.execute("UPDATE tracked_politicians SET negative_patterns = ? WHERE id = ?",
                       (json.dumps(merged, ensure_ascii=False), pid))
        for d, p in LINKS:
            db.execute("DELETE FROM document_politicians WHERE document_id=? AND politician_id=?", (d, p))
    for pid in NEW:
        print(pid, db.execute("SELECT negative_patterns FROM tracked_politicians WHERE id=?", (pid,)).fetchone()[0])
    print("saite atlikusi:", db.execute("SELECT COUNT(*) FROM document_politicians WHERE document_id=133481 AND politician_id=241").fetchone()[0])


if __name__ == "__main__":
    main("--apply" in sys.argv)
