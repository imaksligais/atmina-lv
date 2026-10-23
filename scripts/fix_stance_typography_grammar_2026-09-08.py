"""Trīs `claims.stance` labojumi pēc @quality-reviewer 2026-09-08 (rutīnas diena 2026-09-07).

- #709108 Sprūds  — jauktas pēdiņu zīmes “Archer”/“Morana” -> «Archer»/«Morana»
- #709175 Batņa   — jauktas pēdiņu zīmes „…“ -> «…»  (citātu TEKSTS nemainās)
- #709128 Pūpols  — skaitļa nesaskaņa: `reformai` … `tās ir … pārmaiņas` -> `reformām`

`stance` ir daļa no iegultnes (`f"{topic}: {stance}"`), tāpēc katrai rindai
seko re-embed (CLAUDE.md § Escalation Rules 8). Neviena no rindām nav
`saeima_vote`, tāpēc re-embed ir atļauts.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.db import get_db

ROLLBACK = ROOT / "data" / "rollback_stance_typography_709108_709128_709175_2026-09-08.sql"

EDITS = {
    709108: [("“Archer”", "«Archer»"), ("“Morana”", "«Morana»")],
    709175: [("„palika kā ideja“", "«palika kā ideja»"), ("„rokas bija par īsām“", "«rokas bija par īsām»")],
    709128: [("Pauž atbalstu izglītības reformai,", "Pauž atbalstu izglītības reformām,")],
}


def sql_quote(db, value):
    return db.execute("SELECT quote(?)", (value,)).fetchone()[0]


with get_db() as db:
    rows = {
        r["id"]: r["stance"]
        for r in db.execute(
            f"SELECT id, stance FROM claims WHERE id IN ({','.join('?' * len(EDITS))})",
            list(EDITS),
        ).fetchall()
    }
    if len(rows) != len(EDITS):
        raise SystemExit(f"gaidītas {len(EDITS)} rindas, saņemtas {len(rows)}")

    lines = [
        "-- ROLLBACK for: stance tipogrāfijas + gramatikas labojumi 2026-09-08.",
        "-- Atsauc: #709108, #709175 pēdiņu zīmes un #709128 skaitļa saskaņu.",
        "-- Uz priekšu vērstās izmaiņas piemērošanas datums: 2026-09-08.",
        "-- Pēc šī SQL palaišanas OBLIGĀTI: "
        ".venv/Scripts/python.exe scripts/reembed_claims.py 709108 709128 709175",
        "BEGIN;",
    ]
    for cid in sorted(rows):
        lines.append(f"UPDATE claims SET stance={sql_quote(db, rows[cid])} WHERE id={cid};")
    lines.append("COMMIT;")
    ROLLBACK.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if ROLLBACK.stat().st_size < 500:
        raise SystemExit("rollback nav droši uzrakstīts")

    applied = {}
    for cid, pairs in EDITS.items():
        new = rows[cid]
        for old, repl in pairs:
            if old not in new:
                raise SystemExit(f"#{cid}: nav atrasts fragments {old!r}")
            new = new.replace(old, repl)
        if new == rows[cid]:
            raise SystemExit(f"#{cid}: teksts nemainījās")
        db.execute("UPDATE claims SET stance=? WHERE id=?", (new, cid))
        applied[cid] = len(pairs)
    db.commit()

    left = db.execute(
        f"SELECT COUNT(*) FROM claims WHERE id IN ({','.join('?' * len(EDITS))}) "
        "AND (stance LIKE '%“%' OR stance LIKE '%„%' OR stance LIKE '%reformai, ko virza%')",
        list(EDITS),
    ).fetchone()[0]

print(json.dumps({
    "rollback": ROLLBACK.name,
    "rollback_bytes": ROLLBACK.stat().st_size,
    "intended_rows": len(EDITS),
    "stored_rows": len(applied),
    "substitutions_per_row": applied,
    "rows_still_defective": left,
}, ensure_ascii=False, indent=2))
raise SystemExit(0 if left == 0 and len(applied) == len(EDITS) else 1)
