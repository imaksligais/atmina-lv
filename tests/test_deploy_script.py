"""deploy.sh transporta zars: wrangler, nevis rsync; preflight paliek priekšā."""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "deploy.sh"
# Windows CreateProcess meklē System32 PIRMS PATH, tāpēc kails "bash" ir WSL
# bash bez Windows env mainīgajiem; shutil.which iet pa PATH un atrod Git Bash.
_BASH = shutil.which("bash") or "bash"


def _run(tmp_path: Path, *flags: str, env_text: str | None = None) -> subprocess.CompletedProcess:
    env_file = tmp_path / "env"
    env_file.write_text(
        env_text if env_text is not None
        else "CLOUDFLARE_API_TOKEN=t\nCLOUDFLARE_ACCOUNT_ID=a\n",
        encoding="utf-8",
    )
    env = dict(os.environ)
    # Git Bash pieņem "E:/x/y" formu; Windows atpakaļslīpsvītras tas apēd.
    env["DEPLOY_ENV_FILE"] = env_file.as_posix()
    env["WRANGLER_CMD"] = "echo WRANGLER-STUB"
    return subprocess.run(
        [_BASH, _SCRIPT.relative_to(_ROOT).as_posix(), "--no-output-check", *flags],
        capture_output=True, text=True, cwd=_ROOT, env=env, check=False,
    )


@pytest.mark.skipif(not (_ROOT / "output" / "atmina").is_dir(), reason="nav output/atmina")
def test_deploy_calls_wrangler_deploy(tmp_path):
    r = _run(tmp_path)
    assert r.returncode == 0, r.stderr
    assert "WRANGLER-STUB deploy" in r.stdout


@pytest.mark.skipif(not (_ROOT / "output" / "atmina").is_dir(), reason="nav output/atmina")
def test_dry_run_never_calls_wrangler(tmp_path):
    r = _run(tmp_path, "--dry-run")
    assert r.returncode == 0, r.stderr
    assert "WRANGLER-STUB" not in r.stdout
    assert "faili kokā:" in r.stdout


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
