"""Ārējā DB kopija (scripts/backup_db.py) un tās rinda rutīnas statusā.

Kļūme, ko šie testi nosauc: kopija, kas izskatās izdevusies, bet nav
atjaunojama (vai nekad nav bijusi). Tāpēc E2E tests atšifrē rezultātu PATS,
neatkarīgi no skripta palīgfunkcijām; verifikācijas tests pierāda, ka bojāts
artefakts netiek augšupielādēts; rutīnas tests pierāda, ka brīdinājums
nostrādā arī tad, ja kopija nav taisīta nekad.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import shutil
import sqlite3
import subprocess
from datetime import date, timedelta
from pathlib import Path

import pytest

from src.db import get_db, init_db, now_lv

TOOLS_MISSING = not shutil.which("gpg") or not shutil.which("zstd")
needs_tools = pytest.mark.skipif(TOOLS_MISSING, reason="gpg vai zstd nav PATH")

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "backup_db.py"
COUNTED = {"claims": 3, "documents": 2, "contradictions": 1, "context_notes": 2}


def _load_script():
    spec = importlib.util.spec_from_file_location("backup_db_under_test", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _seed_source(path: Path) -> None:
    init_db(str(path))
    db = sqlite3.connect(path)
    db.execute("INSERT INTO tracked_politicians (id, name, party) VALUES (1, 'Test Politiķis', 'TP')")
    for i in range(COUNTED["documents"]):
        db.execute("INSERT INTO documents (id, platform, source_url, content, content_hash) "
                   "VALUES (?, 'web', ?, 'x', ?)", (i + 1, f"https://example.lv/{i}", f"h{i}"))
    for i in range(COUNTED["claims"]):
        db.execute("INSERT INTO claims (id, opponent_id, topic, stance, source_url, document_id) "
                   "VALUES (?, 1, 'NATO', 'Atbalsta', ?, 1)", (i + 1, f"https://example.lv/c{i}"))
    db.execute("INSERT INTO contradictions (opponent_id, claim_old_id, claim_new_id, topic, summary) "
               "VALUES (1, 1, 2, 'NATO', 's')")
    for i in range(COUNTED["context_notes"]):
        db.execute("INSERT INTO context_notes (topic, note_type, content) VALUES (?, 'context', 'c')",
                   (f"t{i}",))
    db.commit()
    db.close()


def _decrypt(src: Path, out: Path, passfile: Path) -> None:
    """Atjaunošana tieši tā, kā to apraksta wiki — bez skripta koda."""
    gpg = subprocess.run(
        ["gpg", "--batch", "--quiet", "--no-symkey-cache", "--pinentry-mode", "loopback",
         "--passphrase-file", str(passfile), "--decrypt", str(src)],
        capture_output=True, check=True)
    subprocess.run(["zstd", "-q", "-d", "-o", str(out)], input=gpg.stdout, check=True)


def _counts(path: Path) -> dict:
    db = sqlite3.connect(f"file:{path.as_posix()}?immutable=1", uri=True)
    try:
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        return {t: db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in COUNTED}
    finally:
        db.close()


@pytest.fixture
def setup(tmp_path):
    src = tmp_path / "src.db"
    _seed_source(src)
    csp = tmp_path / "csp.db"
    c = sqlite3.connect(csp)
    c.execute("CREATE TABLE reports (id INTEGER PRIMARY KEY, body TEXT)")
    c.execute("INSERT INTO reports (body) VALUES ('r')")
    c.commit()
    c.close()
    passfile = tmp_path / "pass.txt"
    passfile.write_text("vienreizēja-testa-frāze\n", encoding="utf-8")
    dest = tmp_path / "dest"
    dest.mkdir()
    env = tmp_path / ".env.backup"
    env.write_text(f"BACKUP_DEST=local:{dest.as_posix()}\n"
                   f"BACKUP_PASSPHRASE_FILE={passfile.as_posix()}\nBACKUP_KEEP=2\n",
                   encoding="utf-8")
    argv = ["--env", str(env), "--db", str(src), "--csp", str(csp),
            "--tmp", str(tmp_path / "work")]
    return {"src": src, "dest": dest, "pass": passfile, "argv": argv, "tmp": tmp_path}


def _backup_rows(src: Path) -> list:
    db = sqlite3.connect(src)
    try:
        return db.execute("SELECT status, details FROM logs WHERE action='db_backup'").fetchall()
    finally:
        db.close()


@needs_tools
def test_weekly_backup_restores_and_respects_cap_and_retention(setup):
    mod = _load_script()
    mod.REPO_ROOT = setup["tmp"] / "repo"  # testa tmp_path ir zem īstā repo (.pytest-tmp)
    dest, src = setup["dest"], setup["src"]
    old = [f"atmina-{d}.db.zst.gpg" for d in ("2026-01-05", "2026-01-12", "2026-01-19")]
    for n in old:
        (dest / n).write_bytes(b"old")
    (dest / "piezimes.txt").write_text("nav kopija", encoding="utf-8")

    # 1) Pirmais skrējiens: kopija atjaunojama, skaiti sakrīt, .sha256 sakrīt.
    assert mod.main(setup["argv"]) == 0
    day = now_lv()[:10]
    main_file = dest / f"atmina-{day}.db.zst.gpg"
    restored = setup["tmp"] / "restored.db"
    _decrypt(main_file, restored, setup["pass"])
    assert _counts(restored) == COUNTED
    _decrypt(dest / f"csp-{day}.db.zst.gpg", setup["tmp"] / "csp_r.db", setup["pass"])
    sums = (dest / f"atmina-{day}.sha256").read_bytes().decode()
    assert "\r" not in sums, "CRLF salauž `sha256sum -c` atjaunošanā"
    for name in (main_file.name, f"csp-{day}.db.zst.gpg"):
        digest = hashlib.sha256((dest / name).read_bytes()).hexdigest()
        assert f"{digest}  {name}" in sums
    rows = _backup_rows(src)
    assert [r[0] for r in rows] == ["success"]
    details = json.loads(rows[0][1])
    assert details["dest_kind"] == "local"
    assert str(dest.as_posix()) not in rows[0][1] and "pass.txt" not in rows[0][1]
    assert not (setup["tmp"] / "work").exists() or not any((setup["tmp"] / "work").iterdir())

    # 2) Otrais skrējiens tajā pašā nedēļā bez --force: atteikums, nekas nemainās.
    before = sorted(p.name for p in dest.iterdir())
    assert mod.main(setup["argv"]) == mod.EXIT_CAP
    assert sorted(p.name for p in dest.iterdir()) == before
    assert len(_backup_rows(src)) == 1

    # 3) Ar --force: skrien, un retention atstāj BACKUP_KEEP=2 datumus; svešs fails paliek.
    assert mod.main([*setup["argv"], "--force"]) == 0
    names = sorted(p.name for p in dest.iterdir())
    dates = {re.search(r"\d{4}-\d{2}-\d{2}", n).group() for n in names if n != "piezimes.txt"}
    assert dates == {"2026-01-19", day}, names
    assert "piezimes.txt" in names
    assert len(_backup_rows(src)) == 2


@needs_tools
def test_failed_restore_drill_uploads_nothing(setup, monkeypatch):
    """Ja atjaunotā kopija nav vesela, galamērķis paliek neskarts un žurnālā nekā."""
    mod = _load_script()
    mod.REPO_ROOT = setup["tmp"] / "repo"
    real = mod.check_restored

    def corrupted(restored, expected):
        return real(restored, {**expected, "claims": expected.get("claims", 0) + 1})

    monkeypatch.setattr(mod, "check_restored", corrupted)
    assert mod.main(setup["argv"]) != 0
    assert list(setup["dest"].iterdir()) == []
    assert _backup_rows(setup["src"]) == []


def _print_with(tmp_path, monkeypatch, capsys, stamp):
    import src.db as dbmod
    import src.routine as routine
    tmp_path.mkdir(exist_ok=True)
    path = str(tmp_path / "r.db")
    init_db(path)
    if stamp:
        db = get_db(path)
        db.execute("INSERT INTO logs (timestamp, action, status) VALUES (?, 'db_backup', 'success')",
                   (stamp,))
        db.commit()
        db.close()
    monkeypatch.setattr(dbmod, "DB_PATH", path)
    monkeypatch.setattr(routine, "check_routine", lambda d: {"all_complete": True, "steps": {}})
    routine.print_routine("2026-09-23")
    return [ln for ln in capsys.readouterr().out.splitlines() if "Ārējā DB kopija" in ln]


def test_routine_line_warns_without_backup_and_not_with_recent(tmp_path, monkeypatch, capsys):
    never = _print_with(tmp_path, monkeypatch, capsys, None)
    assert len(never) == 1 and "⚠" in never[0] and "NAV" in never[0], never

    recent = (date.fromisoformat(now_lv()[:10]) - timedelta(days=2)).isoformat()
    ok = _print_with(tmp_path / "b", monkeypatch, capsys, f"{recent} 12:00:00")
    assert len(ok) == 1 and "⚠" not in ok[0] and f"2 d (pēdējā {recent})" in ok[0], ok
