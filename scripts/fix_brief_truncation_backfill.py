"""Backfill: aizstāj apgrieztās tabulu šūnas vēsturiskajos daily_brief.

2026-06-10 operatora noteikums (sk. src/briefs.py no-truncation komentāru
un commit a79bc04): publicētā pārskatā nedrīkst būt apgriezts teksts. Kods
turpmākajiem salabots; šis skripts salabo vēsturi — visas `daily_brief`
context_notes rindas:

  1. Pozīciju/pretrunu šūnas, kas beidzas ar "…" → pilnais claims.stance /
     contradictions.summary pirmais paragrāfs (prefiksa sakritība, unikāla).
  2. Spriedžu Apraksts šūnas, kas apgrieztas ar kailo [:120] (bez elipses) →
     pilnais political_tensions.description (prefiksa sakritība, unikāla).
  3. Aktīvāko politiķu tēmu saraksti ar "…" — IZLAIŽ (agregāts, droši
     nerekonstruējams) un ziņo.

Šūnas, kam DB nav unikāla prefiksa sakritība (piem., aģenta rediģēts teksts),
netiek aiztiktas — tiek ziņotas. Aizvietojums, kas satur '|' vai '\n',
tiek izlaists (salauztu markdown tabulu).

Rollback: data/rollback_brief_truncation_backfill_2026-06-11.sql (oriģinālie
content visām mainītajām rindām; ģenerē šis pats skripts).

Lietošana: .venv/Scripts/python.exe scripts/fix_brief_truncation_backfill.py [--dry-run]
"""
from __future__ import annotations

import io
import sqlite3
import sys

DB_PATH = "data/atmina.db"
ROLLBACK_PATH = "data/rollback_brief_truncation_backfill_2026-06-11.sql"

# Spriedžu [:120] griezums: šūna tieši šajā garumā bez "…" beigās ir aizdomīga.
TENSION_CUT_LEN = 120


def _sql_quote(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def _like_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _unique_full(db, sql: str, prefix: str) -> str | None:
    """Atgriež pilno vērtību, ja prefiksam ir TIEŠI viena distinct sakritība."""
    rows = db.execute(sql, (_like_escape(prefix) + "%",)).fetchall()
    vals = {r[0] for r in rows}
    if len(vals) != 1:
        return None
    return next(iter(vals))


def _fix_cell(db, cell: str, stats: dict) -> str | None:
    """Mēģina atjaunot pilno tekstu vienai šūnai; None = neaiztikt."""
    cell = cell.strip()
    if cell.endswith("…"):
        prefix = cell[:-1].rstrip()
        if len(prefix) < 40:  # par īsu drošai prefiksa identifikācijai
            stats["skipped_short"] += 1
            return None
        # 1) claims.stance
        full = _unique_full(
            db, "SELECT DISTINCT stance FROM claims WHERE stance LIKE ? ESCAPE '\\'", prefix)
        if full is None:
            # 2) contradictions.summary (pirmais paragrāfs)
            full = _unique_full(
                db, "SELECT DISTINCT summary FROM contradictions WHERE summary LIKE ? ESCAPE '\\'", prefix)
            if full is not None:
                full = full.split("\n\n", 1)[0].strip()
        if full is None:
            stats["skipped_nomatch"] += 1
            return None
        full = full.strip()
        if "|" in full or "\n" in full or not full.startswith(prefix[:40]):
            stats["skipped_unsafe"] += 1
            return None
        stats["fixed_ellipsis"] += 1
        return full
    # Kailais spriedzes [:120] griezums — bez elipses, tieši 120 simboli.
    if len(cell) == TENSION_CUT_LEN:
        full = _unique_full(
            db, "SELECT DISTINCT description FROM political_tensions WHERE description LIKE ? ESCAPE '\\'", cell)
        if full is None or full.strip() == cell:
            return None
        full = full.strip()
        if "|" in full or "\n" in full:
            stats["skipped_unsafe"] += 1
            return None
        stats["fixed_bare_cut"] += 1
        return full
    return None


def main() -> None:
    dry = "--dry-run" in sys.argv
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    notes = db.execute(
        "SELECT id, topic, content FROM context_notes "
        "WHERE note_type = 'daily_brief' ORDER BY id").fetchall()

    rollback_parts = [
        "-- Rollback: daily_brief tabulu šūnu truncation backfill\n"
        "-- Forward: scripts/fix_brief_truncation_backfill.py (apgrieztās šūnas →\n"
        "--   pilnais DB teksts; sk. commit a79bc04 koda fix). Apply date: 2026-06-11\n"
    ]
    changed_topics: list[str] = []
    for note in notes:
        stats = {"fixed_ellipsis": 0, "fixed_bare_cut": 0,
                 "skipped_nomatch": 0, "skipped_short": 0, "skipped_unsafe": 0,
                 "skipped_topics_aggregate": 0}
        lines = note["content"].split("\n")
        in_active_table = False
        for i, line in enumerate(lines):
            if line.startswith("## "):
                in_active_table = line.startswith("## Aktīvākie politiķi")
            if not (line.startswith("|") and line.count("|") >= 3):
                continue
            if set(line) <= {"|", "-", " "}:
                continue  # tabulas atdalītājrinda
            cells = line.split("|")
            row_changed = False
            for j in range(1, len(cells) - 1):
                cell = cells[j].strip()
                if in_active_table and cell.endswith("…"):
                    stats["skipped_topics_aggregate"] += 1  # agregāts — neaiztiekam
                    continue
                fixed = _fix_cell(db, cell, stats)
                if fixed is not None and fixed != cell:
                    cells[j] = f" {fixed} "
                    row_changed = True
            if row_changed:
                lines[i] = "|".join(cells)
        new_content = "\n".join(lines)
        if new_content != note["content"]:
            rollback_parts.append(
                f"UPDATE context_notes SET content = {_sql_quote(note['content'])} "
                f"WHERE id = {note['id']};\n")
            if not dry:
                db.execute("UPDATE context_notes SET content = ? WHERE id = ?",
                           (new_content, note["id"]))
            changed_topics.append(note["topic"] or "")
            print(f"note {note['id']} ({note['topic']}): {stats}")
        elif any(stats[k] for k in ("skipped_nomatch", "skipped_short",
                                    "skipped_unsafe", "skipped_topics_aggregate")):
            print(f"note {note['id']} ({note['topic']}): bez izmaiņām, skipped: {stats}")

    if not dry and len(rollback_parts) > 1:
        open(ROLLBACK_PATH, "w", encoding="utf-8", newline="\n").write(
            "".join(rollback_parts))
        db.commit()
        print(f"\nRollback: {ROLLBACK_PATH}")
    print(f"\n{'DRY RUN — ' if dry else ''}mainītas {len(changed_topics)} no {len(notes)} daily_brief rindām")


if __name__ == "__main__":
    main()
