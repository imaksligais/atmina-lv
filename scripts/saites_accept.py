"""Accept or reject a TypeSafe Saites proposal.

accept: writes political_tensions via store_tension (diacritic + source_url
guards apply) and marks the proposal. The Latvian description is written by
the agent/operator, not by the model; the relation type is the proposal's
unless --type overrides it (spriedze vs uzbrukums is the human's call).

decided_at is written with SQL CURRENT_TIMESTAMP (UTC) — the whole table is
UTC like political_tensions; never now_lv() here (CLAUDE.md § Timestamp
columns).

Usage:
  .venv/Scripts/python.exe scripts/saites_accept.py <id> --topic "Iekšlietas" --description "..." [--type spriedze]
  .venv/Scripts/python.exe scripts/saites_accept.py <id> --reject
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db import get_db, store_tension  # noqa: E402


def accept(db_path: str | None, proposal_id: int, topic: str, description: str,
           tension_type: str | None = None) -> int:
    db = get_db(db_path)
    p = db.execute("SELECT * FROM tension_proposals WHERE id = ? AND status = 'pending'", (proposal_id,)).fetchone()
    if p is None:
        db.close()
        raise SystemExit(f"proposal {proposal_id} not found or not pending")
    url = db.execute("SELECT source_url FROM documents WHERE id = ?", (p["document_id"],)).fetchone()["source_url"]
    db.close()
    tid = store_tension(p["source_pid"], p["target_pid"], topic, description,
                        tension_type=tension_type or p["relation"], source_url=url, db_path=db_path)
    db = get_db(db_path)
    db.execute("UPDATE tension_proposals SET status = 'accepted', tension_id = ?, decided_at = CURRENT_TIMESTAMP "
               "WHERE id = ?", (tid, proposal_id))
    db.commit()
    db.close()
    return tid


def reject(db_path: str | None, proposal_id: int) -> None:
    db = get_db(db_path)
    cur = db.execute("UPDATE tension_proposals SET status = 'rejected', decided_at = CURRENT_TIMESTAMP "
                     "WHERE id = ? AND status = 'pending'", (proposal_id,))
    db.commit()
    db.close()
    if cur.rowcount == 0:
        raise SystemExit(f"proposal {proposal_id} not found or not pending")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("proposal_id", type=int)
    ap.add_argument("--topic")
    ap.add_argument("--description")
    ap.add_argument("--type", choices=["atbalsts", "uzbrukums", "spriedze"])
    ap.add_argument("--reject", action="store_true")
    a = ap.parse_args()
    if a.reject:
        reject(None, a.proposal_id)
        print(f"proposal {a.proposal_id} rejected")
        return 0
    if not a.topic or not a.description:
        ap.error("--topic and --description are required to accept")
    tid = accept(None, a.proposal_id, a.topic, a.description, a.type)
    print(f"proposal {a.proposal_id} accepted -> political_tensions #{tid}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
