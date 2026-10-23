"""Vēsturiski noņemtas junction saites, kas atkal ir DB (D2 audita (d), 23. pārbaude).

Metode no `docs/audits/2026-10-14-datu-kvalitate/_d2_scope.py`, pārcelta funkcijā,
lai to var izsaukt `scripts/audit_integrity.py` un testi. Katru
`data/rollback_*.sql`, kas skar `document_politicians`, izpilda pa vienam
priekšrakstam pret atmiņas kopiju no PAŠREIZĒJĀS junction tabulas (bez PK, lai
atjaunošanas INSERT/UPDATE nekonfliktē); AFTER INSERT / AFTER UPDATE OF role
trigeri pieraksta katru rindu, ko rollback atliktu atpakaļ = forward labojuma
noņemtā kopa. Rinda (doc, pid, role) ir ATGRIEZTA, ja produkcijā tā tagad ir ar
`created_at` (UTC) > rollback faila pirmā commit laiks (UTC) — rollback commito
PIRMS forward labojuma. Rinda ar momentuzņēmuma `created_at` nekad nav bijusi noņemta.
Izslēgtas: rindas, kuras vēlāks forward fails (`data/*.sql`, ne rollback_) apzināti
ievieto atpakaļ.

Atšķirība no oriģināla: SQL kļūdas vairs netiek norītas — katram failam
skaits + pirmais ziņojums. Atmiņas tabula tiek uzbūvēta vienreiz, katrs fails
izpildās savā SAVEPOINT un tiek atritināts. Kandidātu saraksts, ne automātiska
apspiešana (plāna 4. solis). Nekas netiek rakstīts.
"""

from __future__ import annotations

import os
import re
import sqlite3
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

_SKIP = re.compile(r"(BEGIN|COMMIT|END|ROLLBACK|SAVEPOINT|RELEASE)\b", re.I)
_LEAD_COMMENTS = re.compile(r"\A(\s*(--[^\n]*\n|/\*.*?\*/))*\s*", re.S)
_FWD_INSERT = re.compile(r"INTO\s+document_politicians\s*\(([^)]*)\)\s*VALUES\s*(.+?);", re.I | re.S)
_FWD_ROLE = re.compile(
    r"UPDATE\s+document_politicians\s+SET\s+role\s*=\s*'(\w+)'\s+WHERE\s+document_id\s*=\s*(\d+)"
    r"\s+AND\s+politician_id\s*=\s*(\d+)", re.I)


def git_commit_utc(path: Path) -> str:
    """Faila pirmā commit laiks (UTC); necommitētam — mtime. Ceļš absolūts:
    relatīvs ceļš pret `cwd=path.parent` git klusi neatrod, un viss krīt uz mtime."""
    path = Path(path).resolve()
    out = subprocess.run(["git", "log", "--diff-filter=A", "--format=%cI", "--", str(path)],
                         capture_output=True, text=True, cwd=path.parent).stdout.strip().splitlines()
    if out:
        return datetime.fromisoformat(out[-1]).astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    return datetime.fromtimestamp(os.path.getmtime(path), timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _statements(sql: str) -> list[str]:
    stmts, buf = [], ""
    for line in sql.splitlines(keepends=True):
        buf += line
        if sqlite3.complete_statement(buf):
            stmts.append(buf)
            buf = ""
    return stmts


def _memory_copy(cur: dict) -> sqlite3.Connection:
    m = sqlite3.connect(":memory:", isolation_level=None)
    m.execute("CREATE TABLE document_politicians (document_id INT, politician_id INT, role TEXT, "
              "created_at TEXT, extracted_at TEXT, suspect_at TEXT)")
    m.executemany("INSERT INTO document_politicians VALUES (?,?,?,?,NULL,NULL)",
                  [(d, p, r, c) for (d, p, r), c in cur.items()])
    m.execute("CREATE TABLE _log (kind TEXT, document_id INT, politician_id INT, role TEXT, created_at TEXT)")
    m.execute("CREATE TRIGGER _ti AFTER INSERT ON document_politicians BEGIN INSERT INTO _log VALUES "
              "('insert', new.document_id, new.politician_id, new.role, new.created_at); END")
    m.execute("CREATE TRIGGER _tu AFTER UPDATE OF role ON document_politicians WHEN old.role <> new.role "
              "BEGIN INSERT INTO _log VALUES ('role_update', new.document_id, new.politician_id, "
              "new.role, new.created_at); END")
    return m


def _restored_rows(m: sqlite3.Connection, text: str) -> tuple[list[tuple], int, str]:
    """Izpilda faila atbilstošos priekšrakstus savā SAVEPOINT; atgriež žurnālu,
    kļūdu skaitu un pirmo ziņojumu. Pēc tam viss tiek atritināts."""
    errs, first = 0, ""
    m.execute("SAVEPOINT f")
    try:
        for s in _statements(text):
            # Ievada komentārus atmet: faila galvene («-- Rollback … document_politicians»)
            # citādi ielaistu filtram cauri svešus priekšrakstus.
            code = s[_LEAD_COMMENTS.match(s).end():]
            if _SKIP.match(code):
                continue
            if ("document_politicians" not in code and "_grupaE_restore" not in code
                    and not re.search(r"create\s+temp", code, re.I)):
                continue
            try:
                m.execute(s)
            except sqlite3.Error as e:
                errs += 1
                first = first or f"{type(e).__name__}: {e} — {' '.join(code.split())[:80]}"
        rows = m.execute("SELECT kind, document_id, politician_id, role, created_at FROM _log").fetchall()
    finally:
        m.execute("ROLLBACK TO f")
        m.execute("RELEASE f")
    return rows, errs, first


def scan_readds(db: sqlite3.Connection, data_dir: Path,
                commit_time: Callable[[Path], str] | None = None) -> dict:
    """Atgriež kandidātus (atgrieztās rindas), izslēgtās, skaitus un kļūdas pa failiem."""
    commit_time = commit_time or git_commit_utc
    _t: dict[Path, str] = {}

    def T_of(p: Path) -> str:
        if p not in _t:
            _t[p] = commit_time(p)
        return _t[p]

    cur = {(d, p, r): c for d, p, r, c in db.execute(
        "SELECT document_id, politician_id, role, created_at FROM document_politicians")}
    files = [f for f in sorted(Path(data_dir).glob("rollback_*.sql"))
             if "document_politicians" in f.read_text(encoding="utf-8")]
    m = _memory_copy(cur)
    examined: list[tuple] = []
    errors: dict[str, dict] = {}
    for f in files:
        rows, errs, first = _restored_rows(m, f.read_text(encoding="utf-8"))
        if errs:
            errors[f.name] = {"kļūdas": errs, "pirmā": first}
        for kind, d, p, r, c in rows:
            examined.append((f, T_of(f), kind, d, p, r, c))
    m.close()

    fwd: dict[tuple, list[Path]] = defaultdict(list)
    fwd_unparsed = 0
    for f in Path(data_dir).glob("*.sql"):
        if f.name.startswith("rollback_"):
            continue
        txt = f.read_text(encoding="utf-8")
        for mm in _FWD_INSERT.finditer(txt):
            cols = [c.strip() for c in mm.group(1).split(",")]
            for tup in re.finditer(r"\(([^()]*)\)", mm.group(2)):
                vals = [v.strip().strip("'") for v in tup.group(1).split(",")]
                if len(vals) < 3:
                    continue
                dd = dict(zip(cols, vals))
                try:
                    fwd[(int(dd["document_id"]), int(dd["politician_id"]), dd["role"])].append(f)
                except (KeyError, ValueError):
                    fwd_unparsed += 1
        for mm in _FWD_ROLE.finditer(txt):
            fwd[(int(mm.group(2)), int(mm.group(3)), mm.group(1))].append(f)

    uniq: dict[tuple, tuple] = {}
    for f, T, kind, d, p, r, c in examined:
        if (d, p, r) not in uniq or T > uniq[(d, p, r)][1]:   # jaunākā noņemšana
            uniq[(d, p, r)] = (f, T, kind, c)

    readded, excluded, absent, never_removed = [], [], 0, 0
    for (d, p, r), (f, T, kind, c) in sorted(uniq.items()):
        now = cur.get((d, p, r))
        if now is None:
            absent += 1
        elif now > T and now != c:
            later = [x.name for x in fwd.get((d, p, r), []) if T_of(x) > T]
            row = {"document_id": d, "politician_id": p, "role": r, "created_at": now,
                   "fails": f.name, "rollback_commit": T}
            (excluded if later else readded).append({**row, "forward": later} if later else row)
        else:
            never_removed += 1
    return {
        "files": len(files), "logged": len(examined), "unique": len(uniq),
        "absent": absent, "never_removed": never_removed,
        "readded": readded, "excluded": excluded,
        "errors": errors, "error_total": sum(e["kļūdas"] for e in errors.values()),
        "fwd_unparsed": fwd_unparsed,
    }
