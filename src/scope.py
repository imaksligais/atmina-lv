"""Single definition of "whose documents are extraction work".

Truth source for the extraction queue's politician-side scope. Read via
``queue_politician_sql()`` — never re-type the predicate inline. Same shape as
``src.coalition`` (CLAUDE.md inv #10): one concept, one owner, every reader
goes through it.

**Why this module exists.** The question "does this politician's document count
as work?" was written independently in four places, and on 2026-08-02 they
drifted within a single commit. `83033c02` removed the 11 relay news accounts
from the extraction queue (`src/analyze.py`) but not from the routine status
(`src/routine.py`) or the published backlog figure (`src/wiki.py`). Measured
damage before the fix:

* `print_routine()` step 2 listed LETA as unanalyzed while the real queue
  correctly skipped it. A relay entity has a `role='subject'` document on
  **26 of any 30 days**, so step 2 could essentially never report green again
  — and a status that can never be green stops being read, exactly like a gate
  that can never fail (CLAUDE.md § Working Conventions).
* `wiki/index.md` published "Nepārskatīts backlog: 577 ziņu raksti" when the
  queue-semantics figure was **232**. 345 of those 577 (60%) were documents no
  extractor would ever be offered: 58 on inactive politicians, 287 on relay
  accounts. CLAUDE.md § Session Start tells every session to read that file
  first, so the inflated number was the first thing a session saw.

That second one is a repeat: `src/wiki.py`'s own comment records that this
metric was rewritten on 2026-04-10 to kill a *different* false-urgency
confusion (never-reviewed vs reviewed-and-empty). It was fixed for one
conflation and immediately grew another.

**Scope boundary — do not widen this.** Two `role='subject'` populations exist
and only one is the queue:

* queue semantics (this module): `src/analyze.py::get_pending_politicians`,
  `src/routine.py::_check_analysis`, `src/wiki.py` backlog counters.
* display semantics (NOT this module): `src/render/politicians.py` X subtab and
  `src/render/x.py` render a politician's OWN posts. A relay outlet's feed is
  legitimately shown there; applying this predicate would blank real content.

`src/analyze.py::get_politician_documents` is also deliberately excluded — it
takes an explicit pid and is the escape hatch for reviewing a relay slot on
purpose. Nothing becomes unreachable; it only stops being *proposed*.

**Third reader since 2026-09-07 (operatora verdikts 36): junction-WRITE
semantics.** `relay_media_pids()` below hands the same politician set to
`src/roles.py`, which stops a relay media slot from ever being written as
`role='subject'` in the first place. It is the same concept — "this slot never
holds a first-party position" — enforced one step earlier, so the queue filter
above and the junction writer cannot disagree. The display note still stands:
those renderers keep reading the junction table without this predicate, and the
historical `subject` rows they show are not touched.

**What this module does NOT own: the `platform='vestnesis'` filter.** That one
is document-side, not politician-side, so it stays typed at each of its three
call sites (`get_pending_politicians`, `get_politician_documents`,
`_check_analysis`) — `backlog/agenti-pipeline.md` described it as "mirrored in
`src/scope.py`", and it never was. Its rationale and its 2026-09-06
measurements live in the `get_pending_politicians` comment; the report that
keeps excluded acts visible is `src.routine.vestnesis_acts_for()`. If that
filter ever needs a fourth caller, move it here rather than retyping it — the
drift this module was built for is exactly that shape.
"""

# Politicians whose documents are never extraction work:
#   - 'inactive' — sentinel entries and retired deputies.
#   - relay news accounts — `relationship_type='organization'` AND a
#     `feed_type='relay'` social account (LETA, LTV Ziņas, Krustpunktā, +8).
#     Measured 2026-08-02: 11 entities, 1934 `role='subject'` documents in 90
#     days, and **0 position claims, ever**. Their documents still enter the
#     corpus on purpose — `link_politicians_to_documents` links the politicians
#     named in the text — but the relay slot itself never holds a first-party
#     position. LETA alone sat at the top of the queue in every window (310
#     pending) and burned 141 `analyses` passes on guaranteed-empty content.
#
#     Caveat worth keeping honest: of those 1934 documents only 30 (1.6%) also
#     carry a NON-relay `subject`, so for the rest the politicians named in the
#     text are linked as `mentioned` — and `mentioned` never enters the queue.
#     Excluding the relay slot therefore costs nothing (it produced 0 claims
#     either way), but it does NOT make that content reachable. That gap is the
#     `mentioned`-speaker class tracked separately in BACKLOG.md.
#
# The narrow AND is load-bearing. Filtering on 'organization' alone would also
# silence LDDK, NBS, LVM and Valsts kontrole — institutions whose positions are
# exactly why they were seeded. All four are `feed_type='first_party'`, so the
# AND leaves them in.
_QUEUE_POLITICIAN_TEMPLATE = """EXISTS (
    SELECT 1 FROM tracked_politicians _qsp
    WHERE _qsp.id = {politician_id}
      AND _qsp.relationship_type != 'inactive'
      AND NOT (
          _qsp.relationship_type = 'organization'
          AND EXISTS (SELECT 1 FROM social_accounts _qsa
                      WHERE _qsa.opponent_id = _qsp.id
                        AND _qsa.feed_type = 'relay')
      )
)"""


def queue_politician_sql(politician_id: str = "dp.politician_id") -> str:
    """Return a SQL boolean predicate for "this politician's docs are work".

    Args:
        politician_id: SQL expression yielding the politician id in the caller's
            query. Defaults to ``dp.politician_id`` (the ``document_politicians``
            alias every current caller uses). Pass the caller's own expression
            rather than editing the returned string — a hand-edited copy is the
            drift this module exists to prevent.

    The predicate is self-contained (its subqueries use ``_qsp``/``_qsa``
    aliases that cannot collide with caller aliases), so it can be dropped into
    any ``WHERE``/``AND`` position.
    """
    return _QUEUE_POLITICIAN_TEMPLATE.format(politician_id=politician_id)


_RELAY_MEDIA_PIDS_SQL = """
SELECT _qsp.id FROM tracked_politicians _qsp
WHERE _qsp.relationship_type = 'organization'
  AND EXISTS (SELECT 1 FROM social_accounts _qsa
              WHERE _qsa.opponent_id = _qsp.id
                AND _qsa.feed_type = 'relay')
"""


def relay_media_pids(db) -> frozenset[int]:
    """Ids of the relay MEDIA slots — the Python twin of the ``NOT (...)``
    clause inside ``_QUEUE_POLITICIAN_TEMPLATE``.

    Same narrow AND, same reason (see the module comment): 'organization'
    alone would also catch LDDK, NBS, LVM, Valsts kontrole and Latvijas Banka,
    which are `feed_type='first_party'` institutions with live position claims
    — NBS alone stored 22 in August 2026.

    ``db`` is an OPEN connection owned by the caller; nothing is closed here.
    A fixture/fork DB without ``social_accounts`` yields an empty set rather
    than raising, matching ``_load_politician_forms``' tolerance.
    """
    import sqlite3

    try:
        rows = db.execute(_RELAY_MEDIA_PIDS_SQL).fetchall()
    except sqlite3.OperationalError:
        return frozenset()
    return frozenset(r[0] for r in rows if r[0] is not None)
