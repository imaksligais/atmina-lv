"""TypeSafe veto for surname-only politician matches.

match_politicians() (src/matcher.py) calls judge_candidate() for candidates
whose matched forms contain neither the first name nor a registered @handle —
the class where namesakes, prefix bombs (Kols-in-Kolumbus) and common-word
surnames live. Full-name and handle matches are never sent, and neither are
institutional entities (`relationship_type` journalist / organization): the
question is person-shaped, and the A0 re-check showed the model correctly
answering "not a person" for Latvijas Banka, NBS, LVM, LDDK, Valsts kontrole
— 13 tracked-organization gold links it would have dropped for the wrong
reason.

Pilot 2026-09-17 (E:/typesafe/matcher_pilot.py, 60 gold): threshold 0.6
rejected 32/32 known false links and kept 60/60 gold links.
A0 re-check 2026-09-18 (--gold 300 --seed 2): 32/32 false links rejected at
0.6; gold kept 286/300, of which 13 drops are the organizations above
(excluded by the institutional exemption) and 1 is a mislabelled gold row
(Kleinbergs, doc 188 — the article never names him; a stray claim, no
junction row). Person gold effectively 286/286 kept. VETO_THRESHOLD = 0.6.

Fail-open: on TypeSafeUnavailable judge_candidate returns None and the
caller keeps the candidate. Events go to logs/typesafe_veto.jsonl because the
caller usually holds an open write transaction (a `log_action()` there would
open a second connection and wait on the 30 s busy timeout).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from src.db import get_db
from src.typesafe_client import TypeSafeUnavailable, system_one

log = logging.getLogger(__name__)

VETO_THRESHOLD = 0.6
WINDOW = 350
MAX_WINDOWS = 3
LOG_PATH = Path(__file__).resolve().parent.parent / "logs" / "typesafe_veto.jsonl"

_INSTRUCTIONS = (
    "The document passages were linked to `tracked_politician` by a substring match "
    "on `tracked_politician.matched_name_forms`. Is the person (or word) that "
    "triggered the match in `document.passages_mentioning_the_name` actually this "
    "Latvian politician, considering first name, role, party, and the topic of the "
    "text? Answer for the politician identity, not the substring. "
    "`tracked_politician.role` is the CURRENT role; the document may be older or "
    "newer and name a previous or later office of the same person. A different "
    "office alone is not evidence of a different person."
)
_CRITERIA = {
    "true": "The passages refer to the tracked politician themself (as speaker, subject, or a person mentioned).",
    "false": "The match is a different person with the same or similar surname, or the name form is "
             "part of another word or a common noun, place, or organisation.",
}

_pol_cache: dict[int, dict] = {}


def clear_cache() -> None:
    _pol_cache.clear()


def _politician(pid: int) -> dict | None:
    if pid not in _pol_cache:
        db = get_db()
        r = db.execute("SELECT name, party, role, name_forms FROM tracked_politicians WHERE id = ?", (pid,)).fetchone()
        db.close()
        if r is None:
            return None
        forms = json.loads(r["name_forms"] or "[]") or [r["name"].split()[-1]]
        _pol_cache[pid] = {"name": r["name"], "party": r["party"] or "bezpartejisks / nav zināma",
                           "role": r["role"], "matched_name_forms": forms}
    return _pol_cache[pid]


def _stem(form: str) -> str:
    f = form.strip()
    return f[:-1] if len(f) > 4 and f[-1] in "sšaeiu" else f


def text_windows(text: str, forms: list[str]) -> list[str]:
    """Windows of ±WINDOW chars around occurrences of any form or its stem.
    No diacritic folding — mirrors the matcher. Falls back to the lead."""
    hits: list[int] = []
    for form in forms:
        for needle in {form, _stem(form)}:
            if len(needle) < 3:
                continue
            start = 0
            while (i := text.find(needle, start)) >= 0:
                hits.append(i)
                start = i + 1
    out: list[str] = []
    last_end = -1
    for i in sorted(set(hits)):
        if i < last_end:
            continue
        a, b = max(0, i - WINDOW), min(len(text), i + WINDOW)
        out.append(("…" if a > 0 else "") + text[a:b] + ("…" if b < len(text) else ""))
        last_end = b
        if len(out) >= MAX_WINDOWS:
            break
    return out or [text[: 2 * WINDOW] + ("…" if len(text) > 2 * WINDOW else "")]


def judge_candidate(text: str, pid: int) -> float | None:
    p = _politician(pid)
    if p is None:
        return None
    state = {
        "tracked_politician": p,
        "document": {"passages_mentioning_the_name": text_windows(text, p["matched_name_forms"] + [p["name"]])},
    }
    questions = {"same_person": {"type": "noul", "instructions": _INSTRUCTIONS, "criteria": _CRITERIA}}
    try:
        return float(system_one(state, questions)["answers"]["same_person"]["noul"])
    except TypeSafeUnavailable as e:
        log.warning("typesafe veto unavailable for pid %s: %s", pid, e)
        return None
    except (KeyError, TypeError, ValueError) as e:
        log.warning("typesafe veto malformed answer for pid %s: %s", pid, e)
        return None


def record(event: dict) -> None:
    """Append one JSON line (adds `ts`). Never raises — the veto is observability, not a gate."""
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": datetime.now().isoformat(timespec="seconds"), **event},
                                ensure_ascii=False) + "\n")
    except OSError as e:
        log.warning("typesafe veto log write failed: %s", e)
