"""Extraction batching planner — which politicians/documents go to which
@claim-extractor sub-agent, in which round.

Until 2026-09-24 the orchestrator packed the queue by hand from the rule text
in `.claude/commands/dienas-rutina.md` § 2. This module is that rule as code;
the skill now calls `scripts/plan_extraction.py` and dispatches row by row.

Decision sources (operator):

* **2026-08-19 — pakošana.** Politicians with small queues (≤2 docs) share one
  sub-agent up to ≈8 docs (amortizes the 48 KB prompt); a larger queue gets its
  own agent; circuit breaker ≈12 docs per agent.
* **2026-08-25 — viens pid = viens aģents.** The same politician is never in two
  agents running at the same time: a queue over the cap is split into
  SEQUENTIAL rounds (2026-09-23 evening: Braže 18 and Rinkēvičs 14 docs).
* **2026-09-23 — RT pakošana.** 55 of 122 evening docs were pure retweets
  ("RT @…") and they yielded one position. Pure RTs of all politicians are
  packed into `kind="rt"` agents in a round AFTER every regular round, so no
  pid is ever in a regular agent and an RT agent at once.

The queue itself is NOT re-derived here: politicians come from
`src.analyze.get_pending_politicians` and documents from
`src.analyze.get_politician_documents` (same predicate, `src/scope.py`).
`get_politician_documents` caps at `max_results`; the planner asks for the
pending count and re-asks with the reported `queue_total` if it was cut, so a
queue over 20 docs is never silently truncated.
"""

from __future__ import annotations

from contextlib import contextmanager


def is_pure_retweet(content: str | None) -> bool:
    """True iff the text (after leading whitespace) starts with ``"RT @"``."""
    return bool(content) and content.lstrip().startswith("RT @")


@contextmanager
def _db_path(db):
    """Route the queue readers to ``db`` (a sqlite path) for this call.

    `src.db.get_db()` resolves `DB_PATH` at call time, so swapping the module
    global reaches every reader in `src.analyze` without a second query copy.
    """
    if db is None:
        yield
        return
    import src.db as dbmod
    old = dbmod.DB_PATH
    dbmod.DB_PATH = db
    try:
        yield
    finally:
        dbmod.DB_PATH = old


def _all_docs(pid: int, days: int, hint: int) -> list[dict]:
    from src.analyze import get_politician_documents
    want = max(hint, 1)
    docs = get_politician_documents(pid, days, max_results=want)
    total = max((d.get("queue_total", 0) for d in docs), default=0)
    if total > len(docs):
        docs = get_politician_documents(pid, days, max_results=total)
    return docs


def plan_extraction_batches(days: int = 1, pack_docs: int = 8, cap: int = 12,
                            rt_pack: int = 20, db=None) -> dict:
    """{"agents": [{"agent": int, "round": int, "kind": "solo"|"pack"|"rt",
                    "items": [{"pid": int, "name": str, "doc_ids": [int]}]}],
        "summary": {"pending": int, "politicians": int,
                    "dropped": [{"pid": int, "name": str, "reason": str}],
                    "docs": int, "pairs": int,
                    "rt_docs": int, "agents": int, "rounds": int}}

    ``pending`` = politicians in the queue; ``politicians`` = planned ones;
    ``dropped`` lists every pending politician that got no plannable document.

    ``db`` is an optional sqlite path (default: the live `src.db.DB_PATH`).
    """
    from src.analyze import get_pending_politicians

    with _db_path(db):
        pending = get_pending_politicians(days)
        queue = []  # (pid, name, regular_ids, rt_ids) in pending order
        dropped = []  # pending per get_pending_politicians, but no plannable doc
        for p in pending:
            docs = _all_docs(p["id"], days, p.get("doc_count") or 0)
            regular = [d["id"] for d in docs if not is_pure_retweet(d.get("content"))]
            rts = [d["id"] for d in docs if is_pure_retweet(d.get("content"))]
            if regular or rts:
                queue.append((p["id"], p["name"], regular, rts))
            else:
                # The two readers disagree (predicate drift, or a doc stamped
                # between the reads). Never drop silently: the plan is the
                # denominator the skill checks agent reports against.
                dropped.append({"pid": p["id"], "name": p["name"],
                                "reason": "get_politician_documents neatgrieza nevienu doku"})

    agents: list[dict] = []

    def add(rnd: int, kind: str, items: list[dict]) -> None:
        agents.append({"agent": 0, "round": rnd, "kind": kind, "items": items})

    # Regular docs. Small queues first-fit into packs; the rest solo, split
    # into sequential rounds of `cap` (one pid never twice in a round).
    packs: list[list[dict]] = []
    for pid, name, regular, _ in queue:
        if not regular:
            continue
        if len(regular) <= 2:
            for pk in packs:
                if sum(len(i["doc_ids"]) for i in pk) + len(regular) <= pack_docs:
                    pk.append({"pid": pid, "name": name, "doc_ids": regular})
                    break
            else:
                packs.append([{"pid": pid, "name": name, "doc_ids": regular}])
        else:
            for n, start in enumerate(range(0, len(regular), cap), start=1):
                add(n, "solo", [{"pid": pid, "name": name,
                                 "doc_ids": regular[start:start + cap]}])
    for pk in packs:
        add(1, "pack", pk)

    # Pure RTs: one round after every regular round. A pid's RTs are never
    # split across two RT agents (they run concurrently); a single pid with
    # more than `rt_pack` RTs gets one oversized RT agent instead.
    rt_round = max((a["round"] for a in agents), default=0) + 1
    rt_bins: list[list[dict]] = []
    for pid, name, _, rts in queue:
        if not rts:
            continue
        for b in rt_bins:
            if sum(len(i["doc_ids"]) for i in b) + len(rts) <= rt_pack:
                b.append({"pid": pid, "name": name, "doc_ids": rts})
                break
        else:
            rt_bins.append([{"pid": pid, "name": name, "doc_ids": rts}])
    for b in rt_bins:
        add(rt_round, "rt", b)

    order = {"solo": 0, "pack": 1, "rt": 2}
    agents.sort(key=lambda a: (a["round"], order[a["kind"]]))
    for n, a in enumerate(agents, start=1):
        a["agent"] = n

    pairs = [(i["pid"], d) for a in agents for i in a["items"] for d in i["doc_ids"]]
    rt_docs = {d for a in agents if a["kind"] == "rt" for i in a["items"] for d in i["doc_ids"]}
    return {
        "agents": agents,
        "summary": {
            "pending": len(pending),
            "politicians": len(queue),
            "dropped": dropped,
            "docs": len({d for _, d in pairs}),
            "pairs": len(pairs),
            "rt_docs": len(rt_docs),
            "agents": len(agents),
            "rounds": max((a["round"] for a in agents), default=0),
        },
    }


def format_plan_line(summary: dict) -> str:
    """One status line for `print_routine`."""
    s = summary
    line = (f"PLĀNS: {s['agents']} aģenti / {s['rounds']} kārtas "
            f"({s['politicians']} politiķi, {s['docs']} doki, RT {s['rt_docs']})")
    dropped = s.get("dropped") or []
    if dropped:
        line += (f" — IZMESTI {len(dropped)} no {s.get('pending', '?')} rindas politiķiem "
                 f"(nav plānojamu doku)")
    return line
