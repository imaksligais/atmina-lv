#!/usr/bin/env python
"""Vienreizējs: Saeimas stenogrammu runātāji → `subject` (operatora lēmums 2026-10-21).

Tvērums = TIKAI jaunās saites: (doks, pid), kur pid ir pārbaudīts stenogrammas
runātājs (`src.matcher.transcript_speaker_pids`, tas pats noteikums, ko lieto
`_filter_vestnesis_strict`), matcher viņu atrod tekstā, un dokā viņam vēl NAV
nevienas junction rindas. Lomu izlemj `src.roles.enforce_subject_guards`
(platform='vestnesis'), raksta `src.db.link_document_politicians` (apspiestās
saites netiek atjaunotas). Esošās `mentioned` runātāju rindas NETIEK mainītas —
tikai saskaitītas (atsevišķs operatora lēmums). Nav `rescan_all`.

Bez `--apply` = sausā palaide: viss notiek transakcijā, kas beigās tiek atritināta.
`--apply` prasa `--rollback <fails>` un atsaka, ja faila pāru kopa ≠ šīs palaides kopa.

Lietošana:
    .venv/Scripts/python.exe scripts/_apply_speakers_subject_2026-10-21.py --db .scratch/kopija.db
    .venv/Scripts/python.exe scripts/_apply_speakers_subject_2026-10-21.py --db data/atmina.db \
        --apply --rollback data/rollback_speakers_subject_2026-10-21.sql
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import src.db as db_mod  # noqa: E402
import src.matcher as matcher  # noqa: E402
from src.roles import enforce_subject_guards  # noqa: E402
from src.vestnesis import extract_transcript_speakers  # noqa: E402

SOURCE = "speakers_subject_2026-10-21"
_PAIR_RE = re.compile(r"document_id = (\d+) AND politician_id = (\d+) AND role = 'subject'")


def survey(db) -> dict:
    """Stenogrammu runātāju pāri: jaunie / esošie (pēc lomas)."""
    docs = [
        r for r in db.execute(
            "SELECT id, content FROM documents WHERE platform = 'vestnesis' "
            "AND content LIKE '%Sēdes vadītāj%' ORDER BY id"
        ).fetchall()
        if extract_transcript_speakers(r["content"])
    ]
    new, existing = [], {"mentioned": [], "subject": [], "other": []}
    for d in docs:
        text = d["content"]
        speakers = matcher.transcript_speaker_pids(text)
        kept = {pid for pid, _ in matcher._filter_vestnesis_strict(matcher.match_politicians(text), text)}
        roles: dict[int, set[str]] = {}
        for pid, role in db.execute(
            "SELECT politician_id, role FROM document_politicians WHERE document_id = ?", (d["id"],)
        ).fetchall():
            roles.setdefault(pid, set()).add(role)
        for pid in sorted(speakers & kept):
            have = roles.get(pid)
            if not have:
                new.append((d["id"], pid, text))
            elif "subject" in have:
                existing["subject"].append((d["id"], pid))
            elif "mentioned" in have:
                existing["mentioned"].append((d["id"], pid))
            else:
                existing["other"].append((d["id"], pid))
    return {"docs": [d["id"] for d in docs], "new": new, "existing": existing}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--rollback")
    ap.add_argument("--json-out")
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")

    db_mod.DB_PATH = args.db  # matcher forms read the SAME db
    matcher._clear_politician_cache()
    db = db_mod.get_db(args.db)
    db.isolation_level = None
    db.execute("BEGIN IMMEDIATE")
    try:
        s = survey(db)
        before = db.execute("SELECT COUNT(*) FROM document_politicians").fetchone()[0]
        written, suppressed, non_subject = [], 0, []
        for doc_id, pid, text in s["new"]:
            links = enforce_subject_guards(db, [(pid, "mentioned")], text, platform="vestnesis")
            if links != [(pid, "subject")]:
                non_subject.append((doc_id, pid, links))
                continue
            suppressed += db_mod.link_document_politicians(db, doc_id, links, source=SOURCE)
            written.append((doc_id, pid))
        after = db.execute("SELECT COUNT(*) FROM document_politicians").fetchone()[0]
        pairs = sorted(written)
        print(f"stenogrammas: {len(s['docs'])}")
        print(f"jaunie runātāju pāri: {len(s['new'])} (dokos: {len({d for d, _, _ in s['new']})}); "
              f"ierakstīti subject: {after - before}; apspiesti: {suppressed}; ne-subject: {len(non_subject)}")
        print(f"esošie runātāju pāri: mentioned {len(s['existing']['mentioned'])}, "
              f"subject {len(s['existing']['subject'])}, cits {len(s['existing']['other'])}")
        print(f"document_politicians: {before} -> {after}")
        if non_subject:
            print("ne-subject (netiek rakstīti):", non_subject)
        if args.json_out:
            Path(args.json_out).write_text(json.dumps({
                "docs": s["docs"], "new": pairs, "existing": s["existing"],
            }, ensure_ascii=False, indent=1), encoding="utf-8")
        if (after - before) != len(pairs) - suppressed:
            raise SystemExit("STOP: ierakstīto skaits ≠ plānotais")
        if args.apply:
            if not args.rollback:
                raise SystemExit("STOP: --apply prasa --rollback")
            planned = sorted((int(a), int(b)) for a, b in
                             _PAIR_RE.findall(Path(args.rollback).read_text(encoding="utf-8")))
            if planned != pairs:
                raise SystemExit(f"STOP: rollback pāri ({len(planned)}) ≠ šīs palaides ({len(pairs)})")
            db.execute("COMMIT")
            print("APPLIED")
        else:
            db.execute("ROLLBACK")
            print("DRY-RUN (atritināts)")
    except BaseException:
        if db.in_transaction:
            db.execute("ROLLBACK")
        raise
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
