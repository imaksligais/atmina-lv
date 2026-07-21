"""One-time (idempotent) seed of institutional media X/Twitter accounts.

A 'media source' here = institutional newsroom X/Twitter account (e.g.
@ltvzinas for LTV Ziņas) whose timeline serves as a news feed — tweets
typically report third-party quotes/events rather than expressing the
outlet's own opinion. Seeded as relationship_type='journalist' (reuses
the existing audience category with priority=3 in fetch_all_twitter)
AND social_accounts.feed_type='relay' (see 2026-04-23 CHANGELOG entry).

Pipeline effect (post-2026-04-23 relay logic):
- fetch_all_twitter() iterates social_accounts, pulls the outlet's
  tweets. _store_tweets sees feed_type='relay' and inserts documents
  with empty politician_links (no author-as-subject junction row).
- link_politicians_to_documents() precomputes relay_handles from
  social_accounts.feed_type='relay'. When a Twitter doc's URL author
  is a relay handle, the Twitter subject-downgrade is skipped — so
  quoted tracked politicians keep their 'subject' role (first match
  from match_politicians wins, as with RSS articles).
- Quoted politicians therefore reach their own extraction queue via
  get_pending_politicians(). claim-extractor attributes each claim
  to the quoted politician as first-party: opponent_id=<quoted>,
  speaker_id=NULL, claim_type='position', source_url=<outlet tweet>.
  No commentary-style 'X apgalvo par Y' framing.

Re-running this script is safe: SELECT-then-INSERT guards, same pattern
as scripts/seed_commentators.py. Not parallel-safe.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db import get_db, now_lv  # noqa: E402

MEDIA_SOURCES = [
    {
        "name": "LTV Ziņas",
        "x_handle": "ltvzinas",
        "feed_type": "relay",
        "notes": "Latvijas Televīzijas ziņu dienesta oficiālais X konts. "
                 "Publicē ziņas ar politiķu citātiem — citāti jāekstraktē "
                 "kā first-party claims attiecīgajam politiķim (speaker_id=NULL), "
                 "nevis kā LTV komentāri. feed_type='relay' izlaiž autora-subject "
                 "junction link _store_tweets un atļauj citētajiem politiķiem "
                 "kļūt subject caur link_politicians_to_documents teksta skenēšanu.",
    },
]


def main() -> None:
    db = get_db()
    with db:
        for m in MEDIA_SOURCES:
            feed_type = m.get("feed_type", "first_party")

            existing = db.execute(
                "SELECT id, relationship_type FROM tracked_politicians WHERE name = ?",
                (m["name"],),
            ).fetchone()
            if existing:
                pid = existing["id"]
                if existing["relationship_type"] != "journalist":
                    db.execute(
                        "UPDATE tracked_politicians SET relationship_type = 'journalist' WHERE id = ?",
                        (pid,),
                    )
                    print(f"updated {m['name']} -> relationship_type=journalist (id={pid})")
                else:
                    print(f"skip {m['name']} — already journalist (id={pid})")
            else:
                db.execute(
                    "INSERT INTO tracked_politicians (name, relationship_type, x_handle, notes, created_at) "
                    "VALUES (?, 'journalist', ?, ?, ?)",
                    (m["name"], m["x_handle"], m["notes"], now_lv()),
                )
                pid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
                print(f"inserted {m['name']} (id={pid})")

            account = db.execute(
                "SELECT id, feed_type FROM social_accounts "
                "WHERE opponent_id = ? AND platform = 'twitter' AND handle = ?",
                (pid, m["x_handle"]),
            ).fetchone()
            if account is None:
                db.execute(
                    "INSERT INTO social_accounts (opponent_id, platform, handle, active, feed_type) "
                    "VALUES (?, 'twitter', ?, 1, ?)",
                    (pid, m["x_handle"], feed_type),
                )
                print(f"  + social_accounts row for @{m['x_handle']} (feed_type={feed_type})")
            else:
                existing_ft = (account["feed_type"] or "first_party")
                if existing_ft != feed_type:
                    db.execute(
                        "UPDATE social_accounts SET feed_type = ? WHERE id = ?",
                        (feed_type, account["id"]),
                    )
                    print(f"  ~ @{m['x_handle']} feed_type: {existing_ft} -> {feed_type}")
                else:
                    print(f"  skip @{m['x_handle']} — social_accounts row exists (feed_type={feed_type})")


if __name__ == "__main__":
    main()
