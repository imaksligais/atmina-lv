"""deploy.sh transporta zars: wrangler, nevis rsync; preflight paliek priekšā."""
import json
import os
import re
import shutil
import sqlite3
import subprocess
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "deploy.sh"
# Windows CreateProcess meklē System32 PIRMS PATH, tāpēc kails "bash" ir WSL
# bash bez Windows env mainīgajiem; shutil.which iet pa PATH un atrod Git Bash.
_BASH = shutil.which("bash") or "bash"


_VERSION = "1b933ae4-5069-4df8-b6b7-35c3663f2311"


def _log_db(tmp_path: Path, approvals: tuple[str, ...] = ()) -> Path:
    """Minimāla DB ar `logs` + `publish_approvals` — deploy log NEdrīkst trāpīt dzīvajā DB."""
    path = tmp_path / "log.db"
    db = sqlite3.connect(path)
    db.execute(
        "CREATE TABLE logs (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TIMESTAMP,"
        " action TEXT NOT NULL, source_id INTEGER, opponent_id INTEGER, status TEXT,"
        " duration_ms INTEGER, error_message TEXT, details TEXT, claude_model TEXT,"
        " prompt_hash TEXT)"
    )
    db.execute("CREATE TABLE publish_approvals (subject_key TEXT PRIMARY KEY, approved_at TEXT NOT NULL)")
    db.executemany("INSERT INTO publish_approvals VALUES (?, '2026-09-23 23:00:00')",
                   [(a,) for a in approvals])
    db.commit()
    db.close()
    return path


def _deploy_rows(path: Path) -> list:
    db = sqlite3.connect(path)
    try:
        return db.execute("SELECT timestamp, details FROM logs WHERE action='deploy'").fetchall()
    finally:
        db.close()


def _run(tmp_path: Path, *flags: str, env_text: str | None = None,
         wrangler: str = "echo WRANGLER-STUB", log_db: Path | None = None) -> subprocess.CompletedProcess:
    env_file = tmp_path / "env"
    env_file.write_text(
        env_text if env_text is not None
        else "CLOUDFLARE_API_TOKEN=t\nCLOUDFLARE_ACCOUNT_ID=a\n",
        encoding="utf-8",
    )
    env = dict(os.environ)
    # Git Bash pieņem "E:/x/y" formu; Windows atpakaļslīpsvītras tas apēd.
    env["DEPLOY_ENV_FILE"] = env_file.as_posix()
    env["WRANGLER_CMD"] = wrangler
    # Nekad dzīvā data/atmina.db: bez eksplicītas DB — neesošs ceļš (log krīt,
    # deploy tomēr beidzas ar 0).
    env["ATMINA_DEPLOY_LOG_DB"] = (log_db or tmp_path / "nav" / "log.db").as_posix()
    return subprocess.run(
        [_BASH, _SCRIPT.relative_to(_ROOT).as_posix(), "--no-output-check", *flags],
        capture_output=True, text=True, cwd=_ROOT, env=env, check=False,
    )


@pytest.mark.skipif(not (_ROOT / "output" / "atmina").is_dir(), reason="nav output/atmina")
def test_deploy_calls_wrangler_deploy_and_logs_it(tmp_path):
    blog = sorted(p.stem for p in (_ROOT / "output" / "atmina" / "blog").glob("*.html"))
    assert blog, "denominators 0: output/atmina/blog/ bez lapām"
    db = _log_db(tmp_path, approvals=(blog[-1], "1999-01-01"))
    r = _run(tmp_path, wrangler=f"echo WRANGLER-STUB Current Version ID: {_VERSION}", log_db=db)
    assert r.returncode == 0, r.stderr
    # Stub = echo: VESELA rinda, kas beidzas ar saņemto argumentu `deploy`, pierāda,
    # ka apakškomanda tika PADOTA. Substring nederētu — `>> $WRANGLER_CMD deploy (…)`
    # rinda satur to pašu tekstu.
    assert f"WRANGLER-STUB Current Version ID: {_VERSION} deploy" in r.stdout.splitlines()
    assert ">> Done." in r.stdout
    rows = _deploy_rows(db)
    assert len(rows) == 1, (rows, r.stdout, r.stderr)
    details = json.loads(rows[0][1])
    assert details["version_id"] == _VERSION
    assert details["files"] > 0
    # Tikai atļaujas, kurām kokā ir lapa — "1999-01-01" nav blog/.
    assert details["approved_slugs"] == [blog[-1]]


@pytest.mark.skipif(not (_ROOT / "output" / "atmina").is_dir(), reason="nav output/atmina")
def test_deploy_log_failure_never_fails_the_deploy(tmp_path):
    r = _run(tmp_path)  # log DB ceļš neeksistē → log_action krīt
    assert r.returncode == 0, r.stderr
    assert "deploy log neizdevās" in r.stderr
    assert ">> Done." in r.stdout


@pytest.mark.skipif(not (_ROOT / "output" / "atmina").is_dir(), reason="nav output/atmina")
def test_dry_run_never_calls_wrangler(tmp_path):
    db = _log_db(tmp_path)
    r = _run(tmp_path, "--dry-run", log_db=db)
    assert r.returncode == 0, r.stderr
    assert "WRANGLER-STUB" not in r.stdout
    assert "faili kokā:" in r.stdout
    assert _deploy_rows(db) == [], "dry-run nedrīkst rakstīt deploy log"


@pytest.mark.skipif(not (_ROOT / "output" / "atmina").is_dir(), reason="nav output/atmina")
def test_legacy_delete_flags_are_accepted_noops(tmp_path):
    r = _run(tmp_path, "--no-delete", "--dry-run")
    assert r.returncode == 0, r.stderr
    assert "no-op" in r.stdout + r.stderr


def test_missing_token_stops_before_anything(tmp_path):
    r = _run(tmp_path, env_text="CLOUDFLARE_ACCOUNT_ID=a\n")
    assert r.returncode != 0
    assert "CLOUDFLARE_API_TOKEN" in r.stderr
    assert "WRANGLER-STUB" not in r.stdout


def test_no_rsync_left_in_script():
    text = _SCRIPT.read_text(encoding="utf-8")
    assert "rsync" not in text.split("# --- transports", 1)[-1]


def test_deploy_log_follows_wrangler_and_is_non_fatal():
    """Grep: log tikai PĒC īstā deploy izsaukuma, un kļūme ir ietīta `||`."""
    text = _SCRIPT.read_text(encoding="utf-8")
    body = text.split("# --- transports", 1)[-1]
    call = re.search(r"^\s*\$WRANGLER_CMD deploy", body, re.M)
    assert call, "wrangler deploy izsaukums nav atrasts"
    log_at = body.find("log_action('deploy'")
    assert log_at > call.start(), "log_action('deploy' jābūt aiz wrangler deploy"
    dry_exit = body.find("DRY RUN beidzas")
    assert 0 <= dry_exit < call.start() < log_at
    tail = body[log_at:]
    assert re.search(r"\|\|\s*echo \">> WARNING: deploy log neizdevās\"", tail), (
        "log_action kļūmei jābūt ietītai `|| echo WARNING`"
    )
