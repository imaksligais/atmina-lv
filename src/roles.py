"""Who may hold ``role='subject'`` on a ``document_politicians`` row.

One concept, one owner (same shape as ``src.coalition`` and ``src.scope``):
the matcher decides **who is in the text**, this module decides **who counts
as the speaker**. Every junction writer routes through
``enforce_subject_guards()``; nothing re-types the predicate inline.

Why the split matters. ``matcher.match_politicians()`` hands its highest-count
candidate ``role='subject'`` purely from string presence, and that role is what
the extraction queue walks (``analyze.get_pending_politicians``). Two measured
classes were therefore filling the queue with documents that can never yield a
position, and — because ``documents.reviewed_at`` is per-DOCUMENT — closing
them for the people who really did speak there:

* **Relay media slots (operatora verdikts 36, 2026-09-07).** «aģentūrai LETA
  pastāstīja …» in a closing credit line made LETA (pid=195) the subject of
  **934 unreviewed web documents** measured 2026-09-06 — 14 % of the whole
  6 493-document web backlog, on a slot with 0 position claims ever. The slot
  set is ``scope.relay_media_pids()``; see that module for why the AND with
  ``feed_type='relay'`` is load-bearing (NBS/LVM/LDDK/VK/LB are organizations
  too, and they DO produce claims).

* **Office-voice retweets (operatora verdikts 38, 2026-09-07).** A bare
  ``RT @Brivibas36: …`` on the prime minister's own timeline is the Cabinet's
  communications account writing about him in the third person; twikit stores
  it under HIS status URL, so both ``social._store_tweets`` and
  ``matcher.link_politicians_to_documents`` read the author handle as his and
  award ``subject``. 2026-08-26 produced four such documents in one sweep
  (95102, 95110, 95111, 95112), all correctly extracted empty. This is the
  mechanical form of the Biroja balss convention in
  ``.claude/agents/claim-extractor.md`` Step 3c.

**Deliberately NOT covered — read before widening.** The guard is a demotion,
never a promotion: a document whose only ``subject`` was a relay slot ends up
with ``mentioned`` rows only and leaves the queue, which is the point. Nothing
here touches historical rows, and nothing here removes a document — the
relay's text is still linked, still rendered, still searchable.

``OFFICE_VOICE_HANDLES`` is an explicit constant, not a query, because
@Brivibas36 is not a tracked entity and must not become one: registering it in
``social_accounts`` would add ``brivibas36`` to a politician's H-match handle
set (``matcher._load_politician_forms``) and hand pid=10 a ``subject`` on the
13 documents that account actually authored — the opposite of the verdict. Add
another office account (a ministry's communications handle) only with the same
test coverage; a JOURNALIST's or a party's handle does not belong here.
"""

from __future__ import annotations

import re

from src.scope import relay_media_pids

# Institutional office accounts whose bare retweets are never the retweeter
# speaking. Lowercase, no leading '@'.
OFFICE_VOICE_HANDLES = frozenset({"brivibas36"})

# twikit stores a bare retweet verbatim as "RT @handle: <original text>".
# Anchored at the start on purpose: a quote-tweet or a comment ABOVE the
# quoted text is the politician speaking and must keep its role.
_RETWEET_PREFIX = re.compile(r"^\s*RT @([A-Za-z0-9_]{1,15})\s*:")


def office_voice_retweet_handle(content: str | None) -> str | None:
    """Return the office handle a bare retweet relays, else ``None``."""
    if not content:
        return None
    m = _RETWEET_PREFIX.match(content)
    if not m:
        return None
    handle = m.group(1).lower()
    return handle if handle in OFFICE_VOICE_HANDLES else None


def enforce_subject_guards(
    db,
    politician_links: list[tuple[int, str]] | None,
    content: str | None = None,
) -> list[tuple[int, str]] | None:
    """Demote every ``subject`` a non-speaker would receive.

    Args:
        db: OPEN connection, owned by the caller (nothing is closed here).
        politician_links: ``[(politician_id, role), …]`` as the caller built
            them. ``None``/empty passes straight through.
        content: the document text, needed for the office-voice retweet rule.

    Returns the links with ``subject`` rewritten to ``mentioned`` wherever the
    politician is a relay media slot, or the whole document is a bare retweet
    of an office voice. Order is preserved and duplicates collapsed — a pid
    holding BOTH roles would otherwise leave two identical rows after the
    rewrite (the junction PK is (document_id, politician_id, role), so
    INSERT OR IGNORE would not catch it).
    """
    if not politician_links:
        return politician_links
    office_voice = office_voice_retweet_handle(content) is not None
    blocked = relay_media_pids(db) if any(
        role == "subject" for _, role in politician_links
    ) else frozenset()
    out: list[tuple[int, str]] = []
    seen: set[tuple[int, str]] = set()
    for pid, role in politician_links:
        if role == "subject" and (office_voice or pid in blocked):
            role = "mentioned"
        if (pid, role) in seen:
            continue
        seen.add((pid, role))
        out.append((pid, role))
    return out
