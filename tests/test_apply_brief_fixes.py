"""End-to-end test for scripts/apply_brief_fixes.py (QR fixes to a stored brief).

Failures named first:
1. A fix reaches live rows without a way back or against the rules — `--apply`
   runs with no committed rollback or with one written for an older DB text; a
   pair whose old text exists nowhere is skipped silently; a fix adds a lint
   defect; an already published (append-only) context note is rewritten.
2. A fix lands in one place of three (14.11.: «daudzus» → «visus» in one of two
   places), moves an older daily brief's `created_at` (drops backdated claims
   from a later day's brief), or the rollback cannot restore the text byte for
   byte once git has turned the file's line ends into CRLF.
"""

import json

import pytest

import src.db
from scripts import apply_brief_fixes as abf
from src.db import get_db, init_db

OLD = "Šlesers apgalvo, ka viņam ir 17 deputātu balsis"
NEW = "Šlesers saka, ka daļa LPV deputātu varētu atbalstīt premjeru"
BRIEF_CREATED = "2026-10-13 23:40:00"
BRIEF = (
    "# Dienas analīze — 2026-10-13\n\n## Galvenais\n\n"
    f"- **Koalīcijas sarunas.** {OLD} ([lsm.lv](https://lsm.lv/a)).\n\n"
    "## Aktīvākie politiķi\n\n| Politiķis | Partija | Pozīcijas |\n|---|---|---|\n"
    "| Ainārs Šlesers | Latvija Pirmajā Vietā | 3 |\n\n## Galvenās tēmas\n\n"
    + "Šī rindkopa aizpilda pārskatu līdz prasītajam garumam ar latviešu tekstu. " * 60
    + "\n\n## Koalīcija vs Opozīcija\n\n| Bloks | Pozīcijas |\n|---|---|\n| Opozīcija | 3 |\n"
)
NOTE = f"Piezīme par sarunām.\n\n- {OLD}.\n- Otrs punkts paliek."
TENSION = f"Dombrava atbild Šleseram: {OLD}."


@pytest.fixture
def env(tmp_path, monkeypatch):
    path = str(tmp_path / "t.db")
    init_db(path)
    db = get_db(path)
    db.execute("INSERT INTO tracked_politicians (id, name, party) VALUES (1, 'Ainārs Šlesers', 'LPV')")
    db.execute("INSERT INTO tracked_politicians (id, name, party) VALUES (2, 'Jānis Dombrava', 'NA')")
    db.execute(
        "INSERT INTO context_notes (id, topic, note_type, content, source, created_at) "
        "VALUES (50, 'dienas analīze 2026-10-13', 'daily_brief', ?, 'atmina analīze', ?)",
        (BRIEF, BRIEF_CREATED),
    )
    db.execute(
        "INSERT INTO context_notes (id, topic, note_type, content, created_at) "
        "VALUES (51, 'Koalīcija un partijas', 'context', ?, '2026-10-13 22:30:00')", (NOTE,),
    )
    db.execute(  # UTC column; 19:30 UTC is inside the routine day in any test timezone
        "INSERT INTO political_tensions (id, source_pid, target_pid, topic, description, created_at) "
        "VALUES (60, 2, 1, 'Koalīcija un partijas', ?, '2026-10-13 19:30:00')", (TENSION,),
    )
    db.commit()
    db.close()
    monkeypatch.setattr(src.db, "DB_PATH", path)
    monkeypatch.setattr(abf, "DATA_DIR", tmp_path)
    monkeypatch.setattr(abf, "current_routine_day", lambda: "2026-10-14")
    monkeypatch.setattr(abf, "is_git_tracked", lambda p: True)
    fixes = tmp_path / "fixes.json"
    fixes.write_text(json.dumps([[OLD, NEW]], ensure_ascii=False), encoding="utf-8")
    return {"path": path, "fixes": str(fixes), "tmp": tmp_path,
            "rollback": tmp_path / "rollback_qr_fixes_2026-10-13_r1.sql"}


def _state(path):
    db = get_db(path)
    out = {
        "brief": tuple(db.execute("SELECT content, created_at FROM context_notes WHERE id = 50").fetchone()),
        "note": db.execute("SELECT content FROM context_notes WHERE id = 51").fetchone()[0],
        "tension": db.execute("SELECT description FROM political_tensions WHERE id = 60").fetchone()[0],
    }
    db.close()
    return out


def _run(env, *extra, fixes=None):
    return abf.main(["--note", "50", "--fixes", fixes or env["fixes"], "--tag", "r1", *extra])


def test_refuses_and_writes_nothing(env, monkeypatch):
    before = _state(env["path"])

    assert _run(env, "--apply") == 2  # no rollback file
    assert _run(env, "--write-rollback") == 0
    monkeypatch.setattr(abf, "is_git_tracked", lambda p: False)
    assert _run(env, "--apply") == 2  # rollback present, not committed
    monkeypatch.setattr(abf, "is_git_tracked", lambda p: True)

    db = get_db(env["path"])  # DB text moves on after the rollback was written
    db.execute("UPDATE political_tensions SET description = description || ' Papildināts.' WHERE id = 60")
    db.commit()
    db.close()
    assert _run(env, "--apply") == 2  # rollback holds an older text
    db = get_db(env["path"])
    db.execute("UPDATE political_tensions SET description = ? WHERE id = 60", (TENSION,))
    db.commit()
    db.close()

    def fixes(name, pairs):
        p = env["tmp"] / name
        p.write_text(json.dumps(pairs, ensure_ascii=False), encoding="utf-8")
        return str(p)

    assert _run(env, fixes=fixes("missing.json", [[OLD, NEW], ["šāda teksta nav nekur", "x"]])) == 2
    assert _run(env, fixes=fixes("lint.json", [[OLD, "Šlesers saka, ka 51% deputātu viņu atbalsta"]])) == 2

    db = get_db(env["path"])  # a deploy after the note was written makes the note published
    db.execute("INSERT INTO logs (timestamp, action, status) VALUES ('2026-10-13 23:55:00', 'deploy', 'success')")
    db.commit()
    db.close()
    assert _run(env) == 2  # dry-run already refuses: note 51 is append-only now

    assert _state(env["path"]) == before


def test_applies_everywhere_keeps_created_at_and_rollback_survives_crlf(env):
    before = _state(env["path"])
    assert _run(env, "--write-rollback") == 0
    assert _run(env, "--apply") == 0

    after = _state(env["path"])
    assert after["brief"] == (BRIEF.replace(OLD, NEW), BRIEF_CREATED)  # older brief: stamp kept
    assert after["note"] == NOTE.replace(OLD, NEW)
    assert after["tension"] == TENSION.replace(OLD, NEW)

    rb = env["rollback"].read_text(encoding="utf-8")
    assert NEW not in rb
    db = get_db(env["path"])
    db.executescript(rb.replace("\n", "\r\n"))  # as git checks the file out on Windows
    db.close()
    assert _state(env["path"]) == before
