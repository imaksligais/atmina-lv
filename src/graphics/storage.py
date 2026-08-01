"""DB helper module for the ``brief_images`` table.

Provides CRUD-style helpers used by the @graphics-designer agent and
routine step 11.  The render path uses the latest *approved* row per
note_id (``get_approved_image``); rejected rows are retained for audit.
Error rows (API call failures) are stored with ``approved=2`` and
``cost_usd=0.0`` so they appear in ``get_attempts`` history but do not
inflate the monthly budget total.

Do NOT import ``src.graphics.config`` here — config lazy-imports
``monthly_cost_usd`` from this module to avoid a circular import.
"""
from __future__ import annotations

import hashlib

from src.db import now_lv


# ---------------------------------------------------------------------------
# Filename helpers
# ---------------------------------------------------------------------------

def compute_filename(slug: str, png_bytes: bytes) -> str:
    """Return ``"{slug}-{hash8}.png"`` where hash8 is the first 8 hex chars
    of the SHA-256 digest of *png_bytes*."""
    hash8 = hashlib.sha256(png_bytes).hexdigest()[:8]
    return f"{slug}-{hash8}.png"


# ---------------------------------------------------------------------------
# Insert helpers
# ---------------------------------------------------------------------------

def save_image_row(
    db,
    note_id: int,
    image_path: str,
    prompt: str,
    model: str,
    seed,
    width: int | None,
    height: int | None,
    cost: float = 0.039,
    aspect: str = "16:9",
) -> int:
    """Insert a pending image row and return the new rowid.

    ``approved`` is set to 0 (pending).  ``generated_at`` is set via
    ``now_lv()`` so it reflects Latvia timezone, NOT UTC.
    """
    cur = db.execute(
        """
        INSERT INTO brief_images
            (note_id, image_path, prompt, model, seed, aspect,
             width, height, generated_at, cost_usd, approved)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        """,
        (note_id, image_path, prompt, model, seed, aspect,
         width, height, now_lv(), cost),
    )
    db.commit()
    return cur.lastrowid


def save_error_row(
    db,
    note_id: int,
    prompt: str,
    model: str,
    error_message: str,
) -> int:
    """Insert a failed-attempt row with ``approved=2``, empty ``image_path``,
    and ``cost_usd=0.0``.  Used when the API call itself fails."""
    cur = db.execute(
        """
        INSERT INTO brief_images
            (note_id, image_path, prompt, model, aspect,
             generated_at, cost_usd, approved, error_message)
        VALUES (?, '', ?, ?, '16:9', ?, 0.0, 2, ?)
        """,
        (note_id, prompt, model, now_lv(), error_message),
    )
    db.commit()
    return cur.lastrowid


# ---------------------------------------------------------------------------
# Status updates
# ---------------------------------------------------------------------------

def approve_image(db, image_id: int) -> None:
    """Set ``approved=1`` for the given row."""
    db.execute(
        "UPDATE brief_images SET approved=1 WHERE id=?", (image_id,)
    )
    db.commit()


def reject_image(db, image_id: int, reason: str) -> None:
    """Set ``approved=2`` and record *reason* in ``error_message``."""
    db.execute(
        "UPDATE brief_images SET approved=2, error_message=? WHERE id=?",
        (reason, image_id),
    )
    db.commit()


# ---------------------------------------------------------------------------
# Read helpers
# ---------------------------------------------------------------------------

def get_approved_image(db, note_id: int) -> str | None:
    """Return the ``image_path`` of the newest approved image for *note_id*,
    or ``None`` if no approved row exists."""
    row = db.execute(
        """
        SELECT image_path FROM brief_images
        WHERE note_id=? AND approved=1
        ORDER BY id DESC
        LIMIT 1
        """,
        (note_id,),
    ).fetchone()
    return row[0] if row else None


def get_attempts(db, note_id: int) -> list[dict]:
    """Return all rows for *note_id*, newest first.

    Each dict contains: id, image_path, prompt, approved, error_message,
    generated_at, cost_usd.
    """
    rows = db.execute(
        """
        SELECT id, image_path, prompt, approved, error_message,
               generated_at, cost_usd
        FROM brief_images
        WHERE note_id=?
        ORDER BY id DESC
        """,
        (note_id,),
    ).fetchall()
    keys = ("id", "image_path", "prompt", "approved", "error_message",
            "generated_at", "cost_usd")
    return [dict(zip(keys, row)) for row in rows]


# ---------------------------------------------------------------------------
# Budget tracking
# ---------------------------------------------------------------------------

def monthly_cost_usd(db) -> float:
    """Return the sum of ``cost_usd`` for all rows generated in the current
    Latvia-timezone month (prefix ``YYYY-MM`` match on ``generated_at``)."""
    month_prefix = now_lv()[:7]  # 'YYYY-MM'
    row = db.execute(
        "SELECT COALESCE(SUM(cost_usd), 0.0) FROM brief_images "
        "WHERE generated_at LIKE ? || '%'",
        (month_prefix,),
    ).fetchone()
    return float(row[0])
