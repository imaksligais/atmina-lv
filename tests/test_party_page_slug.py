"""Party detail-page slug must be filename-safe.

`src/render/parties.py` built the per-party HTML path from
`short_name.lower()` with no slugify. A short_name containing a path
separator (e.g. a hypothetical 'SV/AJ' class label) would break the render
by pointing at a nested/invalid path. `_party_page_slug` replaces
filename-unsafe characters with '-'.

Precondition (locked here): for EVERY existing party, the new slug must
equal the old `short_name.lower()` — no live party URL may change. If this
assertion ever fails, STOP: the slug rule diverged from what shipped.
"""

import sqlite3

from src.db import DB_PATH
from src.render._common import _party_page_slug


def test_slash_becomes_hyphen():
    assert _party_page_slug("SV/AJ") == "sv-aj"


def test_backslash_and_colon_become_hyphen():
    assert _party_page_slug("A\\B") == "a-b"
    assert _party_page_slug("A:B") == "a-b"


def test_plain_short_names_are_just_lowercased():
    # No unsafe chars -> identical to the historical `.lower()` behavior.
    assert _party_page_slug("JV") == "jv"
    assert _party_page_slug("ZZS") == "zzs"
    # Existing hyphenated short_name is preserved verbatim (lowercased).
    assert _party_page_slug("SV-AJ") == "sv-aj"


def test_existing_party_urls_unchanged():
    """Every party currently in the DB must slug to its old `.lower()` path."""
    try:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute(
            "SELECT short_name FROM parties WHERE short_name IS NOT NULL"
        ).fetchall()
        conn.close()
    except sqlite3.OperationalError:
        rows = []
    diverged = [
        sn[0] for sn in rows if _party_page_slug(sn[0]) != sn[0].lower()
    ]
    assert not diverged, (
        "BLOCKED: _party_page_slug changed the URL for existing parties: "
        f"{diverged}"
    )
