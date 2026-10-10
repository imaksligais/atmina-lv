"""TypeSafe pass proposing politician-to-politician links for the Saites tab.

One request per document that links 2–5 tracked persons: for each ordered
pair (A speaker candidate, B target) a choice question rel_{a}_{b}
(atbalsts / uzbrukums / spriedze / none) and per speaker a noul speaks_{a}.
Confident pairs land in `tension_proposals` (status 'pending'); a human
accepts them into `political_tensions` with scripts/saites_accept.py.
Nothing here writes `political_tensions`.

Validated 2026-09-17 with this exact request shape
(E:/typesafe/tension_pilot_batched.py) on recorded tensions whose target is
named in the source document: link detected 133/149 (p_link >= 0.7: 131/149).
spriedze vs uzbrukums is blurry (28/87, 52/60 exact) — `relation` is a hint.
"""
from __future__ import annotations

import logging
from itertools import permutations

from src.db import lv_cutoff
from src.matcher import extract_twitter_author_handle
from src.typesafe_client import TypeSafeUnavailable, system_one

log = logging.getLogger(__name__)

MIN_P_LINK = 0.7
MIN_P_SPEAKS = 0.7
DOC_CHARS = 6000
MAX_POLS_PER_DOC = 5
RELATIONS = ("atbalsts", "uzbrukums", "spriedze")
_TRACKED_KINDS = ("tracked", "neutral", "journalist")

_REL_INSTR = (
    "In `document`, does `politicians.{a}` (speaking or acting in their own name) take a "
    "stance TOWARD `politicians.{b}` personally or toward B's actions, statements, or "
    "decisions? Classify with atmina's link types. Only A's stance toward B counts, not "
    "B's toward A, and not two people merely appearing in the same article."
)
_REL_CRITERIA = {
    "atbalsts": "A explicitly supports, defends, praises, endorses, or sides with B or B's action.",
    "uzbrukums": "A directly attacks, accuses, ridicules, demands resignation of, or sharply criticises B by name.",
    "spriedze": "A disagrees with, objects to, or is in visible conflict with B's position or decision, without a direct personal attack.",
    "none": "A takes no stance toward B here: A does not speak, or B is only mentioned in passing, or the text is about both without A addressing B.",
}
_SPEAKS_INSTR = (
    "Does `politicians.{a}` speak or act in their own name in `document` "
    "(own post, direct quote, or reported statement attributed to them)?"
)
_SPEAKS_CRITERIA = {"true": "A is a speaker or actor in the document.",
                    "false": "A is only mentioned or discussed by others."}


def _is_bare_retweet(content: str) -> bool:
    return (content or "").lstrip().startswith("RT @")


def candidate_docs(db, days: int) -> list[int]:
    """Docs in the window linking 2..MAX_POLS_PER_DOC tracked persons, not yet judged, not bare RTs."""
    kinds = ",".join("?" * len(_TRACKED_KINDS))
    rows = db.execute(
        f"""SELECT d.id, d.content FROM documents d
            JOIN document_politicians dp ON dp.document_id = d.id
            JOIN tracked_politicians p ON p.id = dp.politician_id
            WHERE d.scraped_at >= ?
              AND p.relationship_type IN ({kinds})
              AND d.id NOT IN (SELECT document_id FROM tension_judged)
            GROUP BY d.id HAVING COUNT(DISTINCT dp.politician_id) BETWEEN 2 AND ?
            ORDER BY d.id""", (lv_cutoff(days), *_TRACKED_KINDS, MAX_POLS_PER_DOC)).fetchall()
    return [r["id"] for r in rows if not _is_bare_retweet(r["content"])]


def _pairs(db, doc_id: int, platform: str | None, source_url: str | None) -> list[tuple[int, int]]:
    kinds = ",".join("?" * len(_TRACKED_KINDS))
    rows = db.execute(
        f"""SELECT dp.politician_id AS pid, dp.role FROM document_politicians dp
            JOIN tracked_politicians p ON p.id = dp.politician_id
            WHERE dp.document_id = ? AND p.relationship_type IN ({kinds})""",
        (doc_id, *_TRACKED_KINDS)).fetchall()
    pids = sorted({r["pid"] for r in rows})
    speakers = {r["pid"] for r in rows if r["role"] == "subject"}
    if platform == "twitter" and source_url:
        author = extract_twitter_author_handle(source_url)
        if author:
            own = {r["opponent_id"] for r in db.execute(
                "SELECT opponent_id FROM social_accounts WHERE platform = 'twitter' AND lower(handle) = ?",
                (author,))}
            speakers |= own & set(pids)
    a_side = sorted(speakers) or pids  # relay tweets/articles: anyone may be the speaker
    return [(a, b) for a, b in permutations(pids, 2) if a in a_side]


def _entity_type(rel: str | None) -> str:
    return {"journalist": "journalist / commentator", "neutral": "expert or analyst"}.get(rel, "politician")


def _judge(db, doc_id: int) -> tuple[list[dict], dict]:
    """One request. Returns (proposals, usage). Raises TypeSafeUnavailable (caller decides).
    Marks the doc judged only after a successful answer."""
    d = db.execute("SELECT id, title, content, platform, source_domain, source_url, published_at "
                   "FROM documents WHERE id = ?", (doc_id,)).fetchone()
    if d is None or not d["content"]:
        return [], {}
    pairs = _pairs(db, doc_id, d["platform"], d["source_url"])
    if not pairs:
        return [], {}
    pols: dict[str, dict] = {}
    for pid in {p for pair in pairs for p in pair}:
        r = db.execute("SELECT name, party, role, relationship_type FROM tracked_politicians WHERE id = ?",
                       (pid,)).fetchone()
        pols[str(pid)] = {"name": r["name"], "party": r["party"], "role": r["role"],
                          "entity_type": _entity_type(r["relationship_type"])}
    text = d["content"] if len(d["content"]) <= DOC_CHARS else d["content"][:DOC_CHARS] + "…"
    state = {"politicians": pols,
             "document": {"title": d["title"], "platform": d["platform"],
                          "source": d["source_domain"] or d["platform"], "url": d["source_url"],
                          "published_at": (d["published_at"] or "")[:10], "text": text}}
    questions: dict[str, dict] = {}
    for a, b in pairs:
        questions[f"rel_{a}_{b}"] = {"type": "choice",
                                     "instructions": _REL_INSTR.replace("{a}", str(a)).replace("{b}", str(b)),
                                     "criteria": _REL_CRITERIA}
    for a in {a for a, _ in pairs}:
        questions[f"speaks_{a}"] = {"type": "noul", "instructions": _SPEAKS_INSTR.replace("{a}", str(a)),
                                    "criteria": _SPEAKS_CRITERIA}
    resp = system_one(state, questions)
    ans = resp["answers"]
    out = []
    for a, b in pairs:
        rel, spk = ans.get(f"rel_{a}_{b}"), ans.get(f"speaks_{a}")
        if not rel or not spk:
            continue
        probs = rel.get("probabilities") or {}
        p_link = 1.0 - float(probs.get("none", 1.0))
        p_spk = float(spk["noul"])
        if p_link < MIN_P_LINK or p_spk < MIN_P_SPEAKS:
            continue
        relation = max(RELATIONS, key=lambda k: probs.get(k, 0.0))
        out.append({"document_id": doc_id, "source_pid": a, "target_pid": b, "relation": relation,
                    "p_link": round(p_link, 3), "p_relation": round(float(probs.get(relation, 0.0)), 3),
                    "p_speaks": round(p_spk, 3), "snippet": d["content"][:220].replace("\n", " ")})
    db.execute("INSERT OR IGNORE INTO tension_judged (document_id) VALUES (?)", (doc_id,))
    db.commit()
    return out, resp.get("usage", {}) or {}


def judge_document(db, doc_id: int) -> list[dict]:
    """One request; proposals that pass MIN_P_LINK + MIN_P_SPEAKS. Raises TypeSafeUnavailable."""
    return _judge(db, doc_id)[0]


def write_proposals(db, proposals: list[dict]) -> int:
    n = 0
    for p in proposals:
        cur = db.execute(
            """INSERT OR IGNORE INTO tension_proposals
               (document_id, source_pid, target_pid, relation, p_link, p_relation, p_speaks, snippet)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (p["document_id"], p["source_pid"], p["target_pid"], p["relation"],
             p["p_link"], p["p_relation"], p["p_speaks"], p["snippet"]))
        n += cur.rowcount
    db.commit()
    return n


def run(db, days: int = 1) -> dict:
    docs = candidate_docs(db, days)
    judged = proposed = errors = tokens = 0
    for doc_id in docs:
        try:
            props, usage = _judge(db, doc_id)
        except TypeSafeUnavailable as e:
            log.warning("saites proposals: doc %s skipped: %s", doc_id, e)
            errors += 1
            continue
        judged += 1
        tokens += int(usage.get("input_tokens", 0))
        proposed += write_proposals(db, props)
    return {"docs": len(docs), "judged": judged, "proposed": proposed, "errors": errors, "input_tokens": tokens}
