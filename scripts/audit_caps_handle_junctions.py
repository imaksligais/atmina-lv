"""Sauss skrējiens: ko matchera C pakete (ffcba51f) pievienotu/noņemtu
vēsturiskajās `document_politicians` rindās.

TIKAI LASA. DB tiek atvērta `mode=ro`; visi matchera `get_db()` izsaukumi
tiek pārvirzīti uz read-only savienojumu. Nekas netiek rakstīts DB.

Ko mēra
-------
Katram dokumentam ar saturu salīdzina VECO matcheri (`ffcba51f~1:src/matcher.py`,
ielādēts no git blob pagaidu direktorijā) ar JAUNO (`src.matcher`), piemērojot
tos pašus platformas noteikumus, ko `link_politicians_to_documents`:
projekta X konts (PROJECT_X_HANDLES) → izlaist; vestnesis → `_filter_vestnesis_strict`;
x_mention subject → mention_target; twitter subject ne-autoram → mentioned;
`src.roles.enforce_subject_guards`.

* ADD kandidāts = (doks, pid), ko jaunais linkers dotu, vecais nedeva, un
  dokumentam šim pid NAV nevienas junction rindas.
* REMOVAL = vecais deva, jaunais nedod (tikai atskaitei; dzēšanas netiek gatavotas).

ADD cēlonis (ablācija uz jaunā moduļa, tādā secībā):
* ``caps``          — pazūd, ja izslēdz LIELO burtu ceļu (_caps_form → None,
                       _with_caps → identitāte).
* ``handle_whole``  — pazūd, ja @handle atkal meklē kā apakšvirkni.
* ``handle_unique`` — pid ir handle-apstiprināts un visas tā formas ir kopīgo
                       uzvārdu kopā (vecais to lika shared-only grozā).
* ``other``         — neviens no augstāk minētajiem (negaidīts — jālasa).

Lietošana::

    PYTHONUTF8=1 ATMINA_TYPESAFE_VETO=off .venv/Scripts/python.exe \
        scripts/audit_caps_handle_junctions.py --out <scratch> [--workers 6] [--limit N]

Izvade (``--out``): adds.jsonl, removals.jsonl, summary.json, progress.txt.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import multiprocessing as mp
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

OLD_REV = "ffcba51f~1"
DEFAULT_DB = REPO / "data" / "atmina.db"

_W: dict = {}  # per-worker state


def _ro_connect(db_path: str) -> sqlite3.Connection:
    uri = "file:" + Path(db_path).resolve().as_posix() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn


def _write_old_matcher() -> str:
    src = subprocess.run(
        ["git", "-C", str(REPO), "show", f"{OLD_REV}:src/matcher.py"],
        capture_output=True, check=True,
    ).stdout
    d = tempfile.mkdtemp(prefix="atmina_old_matcher_")
    p = os.path.join(d, "matcher_old.py")
    with open(p, "wb") as fh:
        fh.write(src)
    return p


def _init_worker(db_path: str, old_path: str) -> None:
    os.environ["ATMINA_TYPESAFE_VETO"] = "off"
    logging.disable(logging.WARNING)  # "Ambiguous … shared surname" spam
    import src.db as sdb
    import src.roles as roles

    def ro_get_db(db_path_arg=None, _allow_empty=False):  # noqa: ARG001
        return _ro_connect(db_path)

    sdb.get_db = ro_get_db
    import src.matcher as new
    new.get_db = ro_get_db
    spec = importlib.util.spec_from_file_location("matcher_old", old_path)
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    old.get_db = ro_get_db
    assert new.TYPESAFE_VETO_MODE == "off" and old.TYPESAFE_VETO_MODE == "off"

    db = _ro_connect(db_path)
    relay = roles.relay_media_pids(db)
    roles.relay_media_pids = lambda _db: relay  # cache: same answer every doc
    pid_to_handles: dict[int, set[str]] = {}
    for sa in db.execute(
        "SELECT handle, opponent_id FROM social_accounts WHERE platform = 'twitter'"
    ):
        pid_to_handles.setdefault(sa["opponent_id"], set()).add(sa["handle"].lower())
    new._load_politician_forms()
    old._load_politician_forms()
    _W.update(db=db, new=new, old=old, roles=roles, handles=pid_to_handles,
              forms={pid: f for pid, f, _, _ in new._load_politician_forms()})


def _linker(mod, content: str, platform: str | None, source_url: str | None):
    """What link_politicians_to_documents would write: {pid: role} (or None)."""
    matches = mod.match_politicians(content)
    if not matches:
        return {}
    if platform == "twitter" and mod.is_project_account_url(source_url):
        return {}
    if platform == "vestnesis":
        matches = mod._filter_vestnesis_strict(matches, content)
        if not matches:
            return {}
    author = (mod.extract_twitter_author_handle(source_url)
              if platform == "twitter" else None)
    resolved = []
    for pid, role in matches:
        if platform == "x_mention" and role == "subject":
            role = "mention_target"
        elif (platform == "twitter" and role == "subject" and author is not None
              and author not in _W["handles"].get(pid, set())):
            role = "mentioned"
        resolved.append((pid, role))
    out: dict[int, str] = {}
    for pid, role in _W["roles"].enforce_subject_guards(_W["db"], resolved, content):
        out.setdefault(pid, role)
    return out


def _pids_with(patches: dict, content, platform, url) -> set[int]:
    new = _W["new"]
    saved = {k: getattr(new, k) for k in patches}
    try:
        for k, v in patches.items():
            setattr(new, k, v)
        return set(_linker(new, content, platform, url))
    finally:
        for k, v in saved.items():
            setattr(new, k, v)


def _classify(pid: int, content, platform, url) -> str:
    new = _W["new"]
    if pid not in _pids_with({"_caps_form": lambda f: None,
                              "_with_caps": lambda s: set(s)},
                             content, platform, url):
        return "caps"
    if pid not in _pids_with({"_handle_in": lambda low, h: ("@" + h) in low},
                             content, platform, url):
        return "handle_whole"
    low = content.lower()
    aux = (new._politician_aux_cache or {}).get(pid, {})
    handle_conf = any(new._handle_in(low, h) for h in aux.get("handles") or ())
    matched = [f for f in _W["forms"].get(pid, []) if new._occurrences(content, f)]
    if handle_conf and all(f in new._shared_surname_set for f in matched):
        return "handle_unique"
    return "other"


def _removal_cause(pid: int, content, platform, url) -> str:
    """Which part of C makes the new matcher drop a pid the old one linked."""
    if pid in _pids_with({"_handle_in": lambda low, h: ("@" + h) in low},
                         content, platform, url):
        return "handle_whole"
    if pid in _pids_with({"_caps_form": lambda f: None,
                          "_with_caps": lambda s: set(s)},
                         content, platform, url):
        return "caps_veto_or_negative"
    return "other"


def _snippet(pid: int, content: str, cls: str) -> str:
    new = _W["new"]
    idx = -1
    if cls.startswith("handle"):
        aux = (new._politician_aux_cache or {}).get(pid, {})
        low = content.lower()
        for h in sorted(aux.get("handles") or ()):
            i = low.find("@" + h)
            if i != -1:
                idx = i
                break
    if idx == -1:
        hits = []
        for f in _W["forms"].get(pid, []):
            occ = new._occurrences(content, f)
            if cls == "caps":
                occ = [i for i in occ if new._is_caps_at(content, i, f)] or occ
            hits.extend(occ)
        idx = min(hits) if hits else 0
    s = content[max(0, idx - 160): idx + 160]
    return " ".join(s.split())


def _work(id_range: tuple[int, int]) -> dict:
    lo, hi = id_range
    db = _W["db"]
    adds, removals = [], []
    scanned = 0
    both_no_row = 0
    new_only_with_row = 0
    rows = db.execute(
        """SELECT id, content, platform, source_url, reviewed_at, scraped_at
           FROM documents WHERE id >= ? AND id < ?
             AND content IS NOT NULL AND content != ''""",
        (lo, hi),
    ).fetchall()
    for r in rows:
        scanned += 1
        content, platform, url = r["content"], r["platform"], r["source_url"]
        new_l = _linker(_W["new"], content, platform, url)
        old_l = _linker(_W["old"], content, platform, url)
        if not new_l and not old_l:
            continue
        existing = {
            x[0]: x[1] for x in db.execute(
                "SELECT politician_id, group_concat(role) FROM document_politicians "
                "WHERE document_id = ? GROUP BY politician_id", (r["id"],))
        }
        # Pre-existing gap: both matchers link the pid, no row stored. Not
        # caused by this change, not part of the fix.
        both_no_row += sum(1 for p in new_l.keys() & old_l.keys() if p not in existing)
        if new_l.keys() == old_l.keys():
            continue
        for pid in new_l.keys() - old_l.keys():
            if pid in existing:
                new_only_with_row += 1  # matcher now re-derives a stored link
                continue
            cls = _classify(pid, content, platform, url)
            adds.append({
                "document_id": r["id"], "politician_id": pid, "class": cls,
                "linker_role": new_l[pid], "platform": platform,
                "source_url": url, "reviewed_at": r["reviewed_at"],
                "scraped_at": r["scraped_at"],
                "doc_existing_pids": sorted(existing),
                "snippet": _snippet(pid, content, cls),
            })
        for pid in old_l.keys() - new_l.keys():
            removals.append({
                "document_id": r["id"], "politician_id": pid,
                "cause": _removal_cause(pid, content, platform, url),
                "platform": platform, "old_role": old_l[pid],
                "row_exists": pid in existing,
                "existing_role": existing.get(pid),
            })
    return {"scanned": scanned, "adds": adds, "removals": removals,
            "both_no_row": both_no_row, "new_only_with_row": new_only_with_row}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--out", required=True, help="output dir (scratch, not the repo)")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    ap.add_argument("--chunk", type=int, default=1000)
    ap.add_argument("--limit", type=int, default=0, help="only the first N doc ids (smoke)")
    args = ap.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    old_path = _write_old_matcher()
    db = _ro_connect(args.db)
    max_id = db.execute("SELECT MAX(id) FROM documents").fetchone()[0]
    total = db.execute(
        "SELECT COUNT(*) FROM documents WHERE content IS NOT NULL AND content != ''"
    ).fetchone()[0]
    db.close()
    hi_bound = args.limit if args.limit else max_id + 1
    ranges = [(i, min(i + args.chunk, hi_bound)) for i in range(0, hi_bound, args.chunk)]

    t0 = time.time()
    scanned = 0
    adds: list[dict] = []
    removals: list[dict] = []
    both_no_row = new_only_with_row = 0
    prog = out / "progress.txt"
    with mp.get_context("spawn").Pool(
        args.workers, initializer=_init_worker, initargs=(args.db, old_path)
    ) as pool:
        for i, res in enumerate(pool.imap_unordered(_work, ranges), 1):
            scanned += res["scanned"]
            adds.extend(res["adds"])
            removals.extend(res["removals"])
            both_no_row += res["both_no_row"]
            new_only_with_row += res["new_only_with_row"]
            prog.write_text(
                f"chunks {i}/{len(ranges)} docs {scanned}/{total} "
                f"adds {len(adds)} removals {len(removals)} "
                f"elapsed {time.time() - t0:.0f}s\n", encoding="utf-8")

    adds.sort(key=lambda a: (a["document_id"], a["politician_id"]))
    removals.sort(key=lambda a: (a["document_id"], a["politician_id"]))
    with open(out / "adds.jsonl", "w", encoding="utf-8") as fh:
        for a in adds:
            fh.write(json.dumps(a, ensure_ascii=False) + "\n")
    with open(out / "removals.jsonl", "w", encoding="utf-8") as fh:
        for a in removals:
            fh.write(json.dumps(a, ensure_ascii=False) + "\n")
    by_class: dict[str, int] = {}
    for a in adds:
        by_class[a["class"]] = by_class.get(a["class"], 0) + 1
    summary = {
        "old_rev": OLD_REV, "docs_with_content": total, "docs_scanned": scanned,
        "adds": len(adds), "adds_by_class": by_class,
        "adds_by_linker_role": _count(adds, "linker_role"),
        "adds_by_platform": _count(adds, "platform"),
        "adds_on_reviewed_docs": sum(1 for a in adds if a["reviewed_at"]),
        "new_only_pairs_row_already_exists": new_only_with_row,
        "both_link_no_row_preexisting_gap": both_no_row,
        "removals": len(removals),
        "removals_by_cause": _count(removals, "cause"),
        "removals_with_existing_row": sum(1 for r in removals if r["row_exists"]),
        "removals_by_platform": _count(removals, "platform"),
        "elapsed_s": round(time.time() - t0),
    }
    (out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if scanned != (total if not args.limit else scanned) or scanned == 0:
        print(f"DENOMINATOR MISMATCH: scanned {scanned} vs {total}", file=sys.stderr)
        return 1
    return 0


def _count(rows: list[dict], key: str) -> dict:
    out: dict = {}
    for r in rows:
        out[str(r[key])] = out.get(str(r[key]), 0) + 1
    return out


if __name__ == "__main__":
    sys.exit(main())
