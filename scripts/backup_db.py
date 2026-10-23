"""Ārējā DB kopija reizi nedēļā: momentuzņēmums → zstd → gpg → atjaunošanas
pārbaude → augšupielāde → sha256 pārbaude galamērķī → retention.

Konfigurācija TIKAI no `.env.backup` (gitignorēts; paraugs `.env.backup.example`):
    BACKUP_DEST             local:<mape>  vai  ssh:<ssh-host-alias>:<attālā mape>
    BACKUP_PASSPHRASE_FILE  fails ar gpg paroles frāzi, ĀRPUS repo
    BACKUP_KEEP             cik jaunākos datumus paturēt (noklusējums 4)

Lietošana:
    .venv/Scripts/python.exe scripts/backup_db.py            # reizi nedēļā
    .venv/Scripts/python.exe scripts/backup_db.py --dry-run  # tikai plāns
    .venv/Scripts/python.exe scripts/backup_db.py --force    # apiet nedēļas griestus

Izejas kodi: 0 = kopija gatava un pārbaudīta; 1 = kļūda (nekas netika atzīmēts
kā izdevies); 3 = atteikts, jo pēdējā kopija ir jaunāka par 7 dienām.

Atjaunošanas pārbaude notiek KATRĀ skrējienā, pirms augšupielādes: izveidotais
fails tiek atšifrēts, atspiests, `PRAGMA integrity_check` jābūt `ok`, un
`claims`/`documents`/`contradictions`/`context_notes` rindu skaitiem jāsakrīt ar
momentuzņēmumu. Jebkura neatbilstība → nekas netiek augšupielādēts.
"""

from __future__ import annotations

import argparse
import hashlib
import math
import re
import shlex
import shutil
import sqlite3
import subprocess
import sys
import time
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import src.db as dbmod  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TMP = REPO_ROOT / ".scratch" / "backup_tmp"  # E: disks — C: ir mazs
COUNTED_TABLES = ("claims", "documents", "contradictions", "context_notes")
CAP_DAYS = 7
EXIT_CAP = 3
# Viena `zstd | gpg` posma griesti sekundēs (.env.backup: BACKUP_PIPE_TIMEOUT_S).
# Mērīts 2026-10-21 uz kopijas: 2,95 GB → šifrēšana 19,1 s, atšifrēšana 8,3 s.
# 1800 s ≈ 94× rezerve: der arī ~100× lielākai DB tajā pašā ātrumā vai daudz
# lēnākam diskam, bet iesprūdis gpg-agent vairs neaptur kopiju uz visiem laikiem.
PIPE_TIMEOUT_S = 1800
NAME_RE = re.compile(r"^(atmina|csp)-(\d{4}-\d{2}-\d{2})\.(db\.zst\.gpg|sha256)$")


class BackupError(RuntimeError):
    pass


# --- konfigurācija -----------------------------------------------------------

def read_env(path: Path) -> dict:
    if not path.exists():
        raise BackupError(f"{path} nav atrasts — nokopē .env.backup.example un aizpildi.")
    env = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def _inside_repo(p: Path) -> bool:
    try:
        p.resolve().relative_to(REPO_ROOT.resolve())
        return True
    except ValueError:
        return False


def make_dest(spec: str):
    kind, _, rest = spec.partition(":")
    if kind == "local" and rest:
        d = Path(rest)
        if _inside_repo(d):
            raise BackupError("BACKUP_DEST local: mape ir repo kokā — kopijai jābūt citur.")
        return LocalDest(d)
    if kind == "ssh" and ":" in rest:
        host, _, rdir = rest.partition(":")
        if not host or not rdir:
            raise BackupError("BACKUP_DEST ssh: forma ir ssh:<alias>:<mape>.")
        if "public_html" in rdir.lower():
            raise BackupError("Attālā mape ir publiskajā tīmekļa saknē (public_html) — atteikts.")
        if re.search(r"[\s'\"\\]", rdir):
            raise BackupError("Attālajā mapē nedrīkst būt atstarpes, pēdiņas vai '\\'.")
        return SshDest(host, rdir.rstrip("/"))
    raise BackupError("BACKUP_DEST jābūt 'local:<mape>' vai 'ssh:<alias>:<mape>'.")


def passphrase_file(env: dict) -> Path:
    raw = env.get("BACKUP_PASSPHRASE_FILE")
    if not raw:
        raise BackupError("BACKUP_PASSPHRASE_FILE nav norādīts.")
    p = Path(raw)
    if not p.is_file() or p.stat().st_size == 0:
        raise BackupError("BACKUP_PASSPHRASE_FILE neeksistē vai ir tukšs.")
    if _inside_repo(p):
        tracked = subprocess.run(["git", "-C", str(REPO_ROOT), "ls-files", "--error-unmatch",
                                  str(p.resolve())], capture_output=True)
        if tracked.returncode == 0:
            raise BackupError("Paroles fails ir git izsekots — atteikts.")
    return p


# --- galamērķi ---------------------------------------------------------------

class LocalDest:
    kind = "local"

    def __init__(self, root: Path):
        self.root = root

    def describe(self) -> str:
        return f"local:{self.root}"

    def list(self) -> list[str]:
        return [p.name for p in self.root.iterdir()] if self.root.is_dir() else []

    def put(self, src: Path, name: str) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        part = self.root / (name + ".part")
        shutil.copyfile(src, part)
        if sha256_file(part) != sha256_file(src):
            part.unlink()
            raise BackupError(f"{name}: sha256 galamērķī nesakrīt pēc kopēšanas.")
        part.replace(self.root / name)

    def sha256(self, name: str) -> str:
        return sha256_file(self.root / name)

    def remove(self, name: str) -> None:
        (self.root / name).unlink()


class SshDest:
    """Attālais galamērķis caur OpenSSH host alias (~/.ssh/config).

    NAV testēts pret īstu serveri (2026-10-12: atslēga vēl nav autorizēta).
    `list()` izveido attālo mapi (mkdir -p) — arī pie --dry-run.
    """
    kind = "ssh"

    def __init__(self, host: str, rdir: str):
        self.host, self.rdir = host, rdir

    def describe(self) -> str:
        return f"ssh:{self.host}:{self.rdir}"

    def _ssh(self, cmd: str) -> str:
        r = subprocess.run(["ssh", "-o", "BatchMode=yes", self.host, cmd],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise BackupError(f"ssh komanda neizdevās ({r.returncode}): {r.stderr.strip()[:300]}")
        return r.stdout

    def _path(self, name: str) -> str:
        return shlex.quote(f"{self.rdir}/{name}")

    def list(self) -> list[str]:
        out = self._ssh(f"mkdir -p {shlex.quote(self.rdir)} && ls -1A {shlex.quote(self.rdir)}")
        return [ln.strip() for ln in out.splitlines() if ln.strip()]

    def put(self, src: Path, name: str) -> None:
        r = subprocess.run(["scp", "-q", "-o", "BatchMode=yes", str(src),
                            f"{self.host}:{self.rdir}/{name}.part"], capture_output=True, text=True)
        if r.returncode != 0:
            raise BackupError(f"scp neizdevās ({r.returncode}): {r.stderr.strip()[:300]}")
        remote = self._ssh(f"sha256sum {self._path(name + '.part')}").split()[0]
        if remote != sha256_file(src):
            self._ssh(f"rm -f {self._path(name + '.part')}")
            raise BackupError(f"{name}: sha256 galamērķī nesakrīt pēc augšupielādes.")
        self._ssh(f"mv -f {self._path(name + '.part')} {self._path(name)}")

    def sha256(self, name: str) -> str:
        return self._ssh(f"sha256sum {self._path(name)}").split()[0]

    def remove(self, name: str) -> None:
        self._ssh(f"rm -f {self._path(name)}")


# --- palīgi ------------------------------------------------------------------

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _gpg_base(passfile: Path) -> list[str]:
    # --no-symkey-cache: bez tā gpg-agent atceras frāzi, un atjaunošanas
    # pārbaude «izdotos» arī ar nepareizu paroles failu.
    return ["gpg", "--batch", "--quiet", "--yes", "--no-symkey-cache",
            "--pinentry-mode", "loopback", "--passphrase-file", str(passfile)]


def _pipe(first: list[str], second: list[str], out: Path, timeout: float) -> None:
    """first | second > out; abu kodi tiek pārbaudīti.

    `timeout` sekundes abiem kopā: iesprūdis gpg-agent (2026-10-17…21) lika gpg
    gaidīt mūžīgi — un līdz ar to skriptu un check.sh. Pārsniedzot limitu, abi
    procesi tiek nogalināti un kļūda nonāk parastajā KĻŪDA ceļā (izejas kods 1).
    """
    deadline = time.monotonic() + timeout
    with open(out, "wb") as fout:
        p1 = subprocess.Popen(first, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
        p2 = subprocess.Popen(second, stdin=p1.stdout, stdout=fout, stderr=subprocess.PIPE)
        p1.stdout.close()
        try:
            _, err2 = p2.communicate(timeout=timeout)
            rc1 = p1.wait(timeout=max(deadline - time.monotonic(), 0.1))
        except subprocess.TimeoutExpired:
            stuck = [Path(c[0]).name for p, c in ((p1, first), (p2, second)) if p.poll() is None]
            for p in (p1, p2):
                p.kill()
            for p in (p1, p2):
                p.wait()
                p.stderr.close()
            raise BackupError(
                f"{', '.join(stuck)} neatbild {timeout:g} s — apturēts. Ja tas ir gpg, pārbaudi "
                "gpg-agent: `gpg-connect-agent /bye`; ja neatbild — `gpgconf --kill gpg-agent`. "
                "Limitu maina BACKUP_PIPE_TIMEOUT_S (.env.backup).") from None
        err1 = p1.stderr.read()
        p1.stderr.close()
    if rc1 != 0 or p2.returncode != 0:
        raise BackupError(f"{first[0]} rc={rc1} / {second[0]} rc={p2.returncode}: "
                          f"{(err1 or err2).decode(errors='replace').strip()[:300]}")


def snapshot(src: Path, out: Path) -> None:
    """Tiešsaistes kopija ar SQLite backup API — dzīvo failu nekad nekopē."""
    if not src.is_file() or src.stat().st_size == 0:
        raise BackupError(f"Avota DB nav vai tā ir tukša: {src.name}")
    s = sqlite3.connect(f"file:{src.as_posix()}?mode=ro", uri=True, timeout=60)
    d = sqlite3.connect(out)
    try:
        s.backup(d)
    finally:
        d.close()
        s.close()


def _ro(p: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{p.as_posix()}?immutable=1", uri=True)


def table_counts(p: Path, tables: tuple[str, ...] | None) -> dict:
    db = _ro(p)
    try:
        if tables is None:
            tables = tuple(r[0] for r in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"))
        return {t: db.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in tables}
    finally:
        db.close()


def check_restored(restored: Path, expected: dict) -> None:
    """Atjaunošanas pārbaude: integrity_check == ok un skaiti == momentuzņēmums."""
    db = _ro(restored)
    try:
        res = [r[0] for r in db.execute("PRAGMA integrity_check")]
    finally:
        db.close()
    if res != ["ok"]:
        raise BackupError(f"{restored.name}: integrity_check = {res[:3]}")
    got = table_counts(restored, tuple(expected))
    if got != expected:
        raise BackupError(f"{restored.name}: rindu skaiti nesakrīt — {got} pret {expected}")


def _dates(names: list[str]) -> list[str]:
    return sorted({m.group(2) for n in names if (m := NAME_RE.match(n))})


def last_logged_backup(db_path: Path) -> str | None:
    db = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    try:
        row = db.execute("SELECT MAX(timestamp) FROM logs WHERE action='db_backup' "
                         "AND status='success'").fetchone()
    except sqlite3.OperationalError:
        return None
    finally:
        db.close()
    return row[0][:10] if row and row[0] else None


# --- galvenais ---------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--env", default=str(REPO_ROOT / ".env.backup"))
    ap.add_argument("--db", default=None, help="noklusējums: src.db.DB_PATH")
    ap.add_argument("--csp", default=str(REPO_ROOT / "data" / "csp.db"))
    ap.add_argument("--tmp", default=str(DEFAULT_TMP))
    ap.add_argument("--force", action="store_true", help="apiet 7 dienu griestus")
    ap.add_argument("--dry-run", action="store_true", help="tikai parāda plānu")
    a = ap.parse_args(argv)

    t0 = time.monotonic()
    work = None
    try:
        env = read_env(Path(a.env))
        dest = make_dest(env.get("BACKUP_DEST", ""))
        pf = passphrase_file(env)
        keep = int(env.get("BACKUP_KEEP") or 4)
        if keep < 1:
            raise BackupError("BACKUP_KEEP jābūt >= 1.")
        raw_timeout = env.get("BACKUP_PIPE_TIMEOUT_S") or PIPE_TIMEOUT_S
        try:
            pipe_timeout = float(raw_timeout)
        except ValueError:
            raise BackupError(f"BACKUP_PIPE_TIMEOUT_S nav skaitlis: {raw_timeout!r}.") from None
        if not math.isfinite(pipe_timeout) or pipe_timeout <= 0:
            raise BackupError("BACKUP_PIPE_TIMEOUT_S jābūt galīgam skaitlim > 0.")
        src = Path(a.db or dbmod.DB_PATH)
        if not src.is_absolute():
            src = REPO_ROOT / src
        csp = Path(a.csp)
        day = dbmod.today_lv().isoformat()

        existing = dest.list()
        last_dest = (_dates([n for n in existing if n.startswith("atmina-")]) or [None])[-1]
        last_log = last_logged_backup(src)
        newest = max(filter(None, [last_dest, last_log]), default=None)
        age = (date.fromisoformat(day) - date.fromisoformat(newest)).days if newest else None

        files = [("atmina", src)] + ([("csp", csp)] if csp.is_file() else [])
        if not csp.is_file():
            print(f"⚠ {csp.name} nav atrasts — kopija būs bez tā.")
        print(f"Plāns: {', '.join(f'{n} ({p.stat().st_size / 1e9:.2f} GB)' for n, p in files)}"
              f" → {dest.kind}; paturēt {keep} datumus; pēdējā kopija: "
              f"{newest or 'nav'}{f' ({age} d)' if age is not None else ''}")
        if age is not None and age < CAP_DAYS and not a.force:
            print(f"ATTEIKTS: pēdējā kopija ir {age} d veca (< {CAP_DAYS}). Lieto --force, "
                  "ja tiešām vajag.")
            return EXIT_CAP
        if a.dry_run:
            print(f"(dry-run) Galamērķis: {dest.describe()}; nekas netiek darīts.")
            return 0

        work = Path(a.tmp) / f"run-{datetime.now():%Y%m%d-%H%M%S}"
        work.mkdir(parents=True)
        artifacts, details = [], {"dest_kind": dest.kind, "date": day, "files": {}}
        for name, path in files:
            snap = work / f"{name}.db"
            print(f"[{name}] momentuzņēmums …", flush=True)
            snapshot(path, snap)
            expected = table_counts(snap, COUNTED_TABLES if name == "atmina" else None)
            out = work / f"{name}-{day}.db.zst.gpg"
            print(f"[{name}] zstd + gpg …", flush=True)
            _pipe(["zstd", "-q", "-c", "-T0", "-3", str(snap)],
                  [*_gpg_base(pf), "--symmetric", "--cipher-algo", "AES256"], out, pipe_timeout)
            print(f"[{name}] atjaunošanas pārbaude …", flush=True)
            restored = work / f"{name}.restored.db"
            _pipe([*_gpg_base(pf), "--decrypt", str(out)], ["zstd", "-q", "-d", "-c"], restored,
                  pipe_timeout)
            check_restored(restored, expected)
            restored.unlink()
            snap_size = snap.stat().st_size
            snap.unlink()
            digest = sha256_file(out)
            artifacts.append((out, digest))
            details["files"][name] = {"db_bytes": snap_size, "gpg_bytes": out.stat().st_size,
                                      "sha256": digest, "counts": expected}

        sums = work / f"atmina-{day}.sha256"
        # newline="\n": ar CRLF `sha256sum -c` atjaunošanā neatrod failus.
        sums.write_text("".join(f"{d}  {p.name}\n" for p, d in artifacts), encoding="utf-8",
                        newline="\n")
        print(f"Augšupielāde uz {dest.kind} …", flush=True)
        for p, d in [*artifacts, (sums, sha256_file(sums))]:
            dest.put(p, p.name)
            if dest.sha256(p.name) != d:
                raise BackupError(f"{p.name}: sha256 galamērķī nesakrīt.")

        names = dest.list()
        dates = _dates(names)
        stale = set(dates[:-keep]) if len(dates) > keep else set()
        removed = [n for n in names if (m := NAME_RE.match(n)) and m.group(2) in stale]
        for n in removed:
            dest.remove(n)

        details["duration_s"] = round(time.monotonic() - t0, 1)
        details["removed_dates"] = sorted(stale)
        dbmod.log_action("db_backup", details=details, db_path=str(src),
                         duration_ms=int(details["duration_s"] * 1000))
        for name, f in details["files"].items():
            print(f"✓ {name}: {f['db_bytes'] / 1e9:.2f} GB → {f['gpg_bytes'] / 1e9:.3f} GB, "
                  f"integrity ok, skaiti {f['counts'] if name == 'atmina' else len(f['counts'])}")
        print(f"✓ Gatavs {details['duration_s']} s; dzēsti datumi: {sorted(stale) or 'nav'}")
        return 0
    except (BackupError, OSError, sqlite3.Error, ValueError) as e:
        print(f"KĻŪDA: {e}\nNekas netika atzīmēts kā izdevies.", file=sys.stderr)
        return 1
    finally:
        if work is not None:
            shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
