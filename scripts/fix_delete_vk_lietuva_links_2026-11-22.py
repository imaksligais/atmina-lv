"""T1 (handoff 20.11.): «Valsts kontrole» (pid 241) piesaistīta Lietuvas Valsts kontroles dokiem.

162340 (diena.lv: Lietuvas VK vadītāja Segalovičiene par Lietuvas aizsardzību) un 162337
(diena.lv: Nausēda par Lietuvas divīziju) — role='subject', 0 pozīciju. DELETE ieraksta
`document_politician_suppressions` (režīms 'record'), tāpēc saites neatgriezīsies.
`name_forms`/`negative_patterns` nemaina (operatora lēmums).

    .venv/Scripts/python.exe scripts/fix_delete_vk_lietuva_links_2026-11-22.py          # dry-run + rollback
    .venv/Scripts/python.exe scripts/fix_delete_vk_lietuva_links_2026-11-22.py --apply

Rollback: data/rollback_delete_vk_lietuva_links_2026-11-22.sql (tiešs INSERT atceļ apslāpēšanu).
"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import get_db  # noqa: E402

LINKS = [(162340, 241), (162337, 241)]
ROLLBACK = ROOT / "data/rollback_delete_vk_lietuva_links_2026-11-22.sql"


def lit(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return repr(v)
    return "'" + str(v).replace("'", "''") + "'"


def main(apply: bool) -> None:
    db = get_db(None)
    lcols = [r[1] for r in db.execute("PRAGMA table_info(document_politicians)")]
    lines = ["-- Rollback: scripts/fix_delete_vk_lietuva_links_2026-11-22.py (apply 2026-11-22).",
             "-- Forward: DELETE document_politicians 162340/241, 162337/241 (Lietuvas VK, T1).",
             "BEGIN;"]
    for d, p in LINKS:
        row = db.execute("SELECT * FROM document_politicians WHERE document_id=? AND politician_id=?",
                         (d, p)).fetchone()
        if row is None:
            sys.exit(f"STOP: saite {d}/{p} nav atrasta")
        if db.execute("SELECT 1 FROM claims WHERE document_id=? AND opponent_id=?", (d, p)).fetchone():
            sys.exit(f"STOP: saitei {d}/{p} ir pozīcijas")
        lines.append(f"INSERT INTO document_politicians ({', '.join(lcols)}) VALUES "
                     f"({', '.join(lit(row[c]) for c in lcols)});")
    lines.append("COMMIT;")
    ROLLBACK.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"rollback uzrakstīts: {ROLLBACK.relative_to(ROOT)}; saites {len(LINKS)}")
    if not apply:
        return
    with db:
        for d, p in LINKS:
            db.execute("DELETE FROM document_politicians WHERE document_id=? AND politician_id=?", (d, p))
    left = sum(db.execute("SELECT COUNT(*) FROM document_politicians WHERE document_id=? AND politician_id=?",
                          lk).fetchone()[0] for lk in LINKS)
    supp = sum(db.execute("SELECT COUNT(*) FROM document_politician_suppressions WHERE document_id=? AND politician_id=?",
                          lk).fetchone()[0] > 0 for lk in LINKS)
    print(f"atlikušas saites {left}; apslāpētas {supp} no {len(LINKS)}")


if __name__ == "__main__":
    main("--apply" in sys.argv)
