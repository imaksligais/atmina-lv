"""social_drafts table CRUD: create / fetch / mark_* transitions."""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta

from src.db import get_db

_LV_OFFSET = timedelta(hours=3)


def _now_lv() -> str:
    return (datetime.now(timezone.utc) + _LV_OFFSET).strftime("%Y-%m-%d %H:%M:%S")


def create_draft(
    pillar: str,
    text: str,
    image_path: str | None,
    source_data: dict,
    score: float,
    db_path: str | None = None,
    parent_draft_id: int | None = None,
    revision_count: int = 0,
    telegram_chat_id: str | None = None,
) -> int:
    db = get_db(db_path)
    cur = db.execute(
        """
        INSERT INTO social_drafts (
            pillar, text, image_path, source_data_json, score, status,
            parent_draft_id, revision_count, telegram_chat_id, created_at
        )
        VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?)
        """,
        (
            pillar, text, image_path, json.dumps(source_data, ensure_ascii=False),
            score, parent_draft_id, revision_count, telegram_chat_id, _now_lv(),
        ),
    )
    db.commit()
    draft_id = cur.lastrowid
    db.close()
    return draft_id


def get_draft(draft_id: int, db_path: str | None = None) -> dict | None:
    db = get_db(db_path)
    row = db.execute("SELECT * FROM social_drafts WHERE id = ?", (draft_id,)).fetchone()
    db.close()
    return dict(row) if row else None


def list_pending_drafts(db_path: str | None = None) -> list[dict]:
    db = get_db(db_path)
    rows = db.execute(
        "SELECT * FROM social_drafts WHERE status = 'pending' ORDER BY score DESC"
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


def _set_status(draft_id: int, status: str, extras: dict, db_path: str) -> None:
    db = get_db(db_path)
    cols = ["status = ?"]
    vals: list = [status]
    for k, v in extras.items():
        cols.append(f"{k} = ?")
        vals.append(v)
    vals.append(draft_id)
    db.execute(f"UPDATE social_drafts SET {', '.join(cols)} WHERE id = ?", vals)
    db.commit()
    db.close()


def mark_approved(draft_id: int, db_path: str | None = None) -> None:
    _set_status(draft_id, "approved", {}, db_path)


def mark_rejected(draft_id: int, db_path: str | None = None) -> None:
    _set_status(draft_id, "rejected", {}, db_path)


def mark_posted(draft_id: int, tweet_id: str, db_path: str | None = None) -> None:
    _set_status(draft_id, "posted", {"tweet_id": tweet_id, "posted_at": _now_lv()}, db_path)


def mark_failed(draft_id: int, error_message: str, db_path: str | None = None) -> None:
    _set_status(draft_id, "failed", {"error_message": error_message}, db_path)


def mark_revising(parent_id: int, new_text: str, db_path: str | None = None) -> int:
    """Mark the parent as 'revising' and create a new pending draft inheriting its context.

    Returns the new child draft id.
    """
    parent = get_draft(parent_id, db_path=db_path)
    if parent is None:
        raise ValueError(f"No draft #{parent_id}")
    child_id = create_draft(
        pillar=parent["pillar"],
        text=new_text,
        image_path=parent["image_path"],  # reuse same image unless re-rendered separately
        source_data=json.loads(parent["source_data_json"]),
        score=parent["score"],
        db_path=db_path,
        parent_draft_id=parent_id,
        revision_count=parent["revision_count"] + 1,
        telegram_chat_id=parent["telegram_chat_id"],
    )
    _set_status(parent_id, "revising", {}, db_path)
    return child_id
