"""Balsojumu īsais saraksts pozīcijai — retorika pret balsojumu, atlase ar kodu.

Kāpēc: deputātam ir mediāna 3 192 balsojumi 1 156 likumprojektos. `@contradiction-hunter`
tos izlasīt nevar, tāpēc katru dienu pats izdomāja SQL atlasi — pārklājums nebija
ne atkārtojams, ne izmērīts (`docs/audits/2026-11-13-pretrunu-faktu-parbaude/`).

Vienība ir likumprojekts (`document_nr`), ne balsojums: ķēdi lasa kopā (T14).
Rangs = 0,75·kosinuss(pozīcija, likumprojekta apraksts) + 0,25·leksiskais pārklājums
+ tēmas sakritība + tuvums laikā. Tēma ir PIESKAITĪJUMS, ne vārti: 3 no 13 publicētajām
balsojumu pretrunām abām pusēm ir dažādas tēmas (#56, #65, #66).

Tas ir LASĪŠANAS SECĪBA ar izmērītu pilnīgumu (`eval_vote_candidates.py`), ne verdikts,
un tukšs saraksts nepierāda, ka neatbilstību nav — T9 strukturālā pārbaude paliek.
Neraksta DB; vektoru kešs ir fails.
"""

from __future__ import annotations

import hashlib
import math
import os
import re
import sqlite3
import struct
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np

from src.party_contradictions import ensure_vec, is_procedural, lexical_overlap

CACHE_PATH = Path("data/_bill_vectors.npz")
DEFAULT_TOP = 10
COSINE_WEIGHT = 0.75
LEXICAL_WEIGHT = 0.25
TOPIC_BONUS = 0.03
RECENCY_BONUS = 0.04
RECENCY_DAYS = 45  # e-kāpinātāja mērogs: pēc 45 dienām piemaksa ir 37 % no pilnās
_CAST = ("Par", "Pret", "Atturas")
_TEXT_LIMIT = 1500
# Sēdes vadība (pārtraukums, debašu laiks, kvorums, klātbūtne) nav nostāja. Tikai
# šim sarakstam: kopīgais `is_procedural` (T14) to nesedz, un tā mainīšana skartu
# faktu pārbaudi un balsojumu lapas. Uzticības balsojumi bez numura paliek.
# 13.11. rutīnā 6 šādas rindas 2 no 11 sarakstiem (HANDOFF-2026-11-13).
_SESSION_MOTIF_RE = re.compile(
    r"^\s*(par\s+)?(sēdes\s+(pārtraukum|turpināšan|sākšan|slēgšan)|tehnisko\s+pārtraukum"
    r"|debašu\s+laika|kvoruma\s+pārbaud|deputātu\s+klātbūtnes\s+reģistrācij|izmaiņām\s+darba\s+kārtībā)",
    re.IGNORECASE,
)


def _is_session_procedure(motif: str | None) -> bool:
    return bool(motif and _SESSION_MOTIF_RE.search(motif))


def load_bills(db: sqlite3.Connection) -> dict[str, dict[str, Any]]:
    """Visi likumprojekti: atslēga `document_nr` vai `vote:<id>` balsojumam bez numura."""
    bills: dict[str, dict[str, Any]] = {}
    for v in db.execute(
        "SELECT id, document_nr, motif, summary, topic, vote_date FROM saeima_votes ORDER BY vote_date, vote_time"
    ):
        key = v["document_nr"] or f"vote:{v['id']}"
        b = bills.setdefault(key, {"key": key, "text": "", "topic": v["topic"], "substantive": False,
                                   "first": v["vote_date"], "last": v["vote_date"]})
        b["last"] = v["vote_date"]
        b["substantive"] = b["substantive"] or not (is_procedural(v["motif"]) or _is_session_procedure(v["motif"]))
        if len(v["summary"] or "") > len(b["text"]):
            b["text"] = v["summary"]  # apraksts pieder likumprojektam (T20) — garākais ir pilnākais
        if not b["text"]:
            b["text"] = v["motif"] or ""
    return bills


def _embed(texts: list[str]) -> np.ndarray:
    from src.embeddings import _get_model

    return _get_model().encode([f"passage: {t}" for t in texts], normalize_embeddings=True, batch_size=32,
                               show_progress_bar=False)


def bill_vectors(
    bills: dict[str, dict[str, Any]],
    cache_path: Path | None = None,
    embed: Callable[[list[str]], np.ndarray] | None = None,
) -> dict[str, np.ndarray]:
    """Likumprojektu vektori; kešā pēc teksta jaucējkoda, tāpēc embedē tikai jaunos un mainītos."""
    cache_path = cache_path or CACHE_PATH  # izsaukuma brīdī, lai tests var novirzīt
    embed = embed or _embed
    digest = {k: hashlib.sha1(b["text"][:_TEXT_LIMIT].encode("utf-8")).hexdigest() for k, b in bills.items()}
    cached: dict[str, np.ndarray] = {}
    if cache_path.exists():
        with np.load(cache_path, allow_pickle=False) as z:
            cached = dict(zip(z["digests"].tolist(), z["vecs"], strict=True))
    missing = sorted({d for d in digest.values() if d not in cached})
    if missing:
        text_of = {digest[k]: bills[k]["text"][:_TEXT_LIMIT] for k in bills}
        for d, vec in zip(missing, embed([text_of[d] for d in missing]), strict=True):
            cached[d] = np.asarray(vec, dtype=np.float32)
        keep = sorted(set(digest.values()))
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = cache_path.with_name(f"{cache_path.stem}.{os.getpid()}.tmp.npz")
        np.savez(tmp, digests=np.array(keep), vecs=np.stack([cached[d] for d in keep]))
        os.replace(tmp, cache_path)  # vesels fails vai vecais — paralēls skrējiens neredz pusrakstītu
    return {k: cached[d] for k, d in digest.items()}


def _claim_vector(db: sqlite3.Connection, claim_id: int) -> np.ndarray | None:
    row = db.execute("SELECT embedding FROM claim_vectors WHERE claim_id = ?", (claim_id,)).fetchone()
    if row is None or row[0] is None:
        return None
    blob = bytes(row[0])
    return np.array(struct.unpack(f"{len(blob) // 4}f", blob), dtype=np.float32)


def deputy_ballots(db: sqlite3.Connection, pid: int) -> dict[str, list[dict[str, Any]]]:
    """Likumprojekts → šī deputāta NODOTĀS balsis (`Nebalsoja` nav nostāja)."""
    out: dict[str, list[dict[str, Any]]] = {}
    for r in db.execute(
        """SELECT sv.id, sv.document_nr, sv.vote_date, sv.motif, sv.url, siv.vote
           FROM saeima_individual_votes siv JOIN saeima_votes sv ON sv.id = siv.vote_id
           WHERE siv.politician_id = ? AND siv.vote IN (?, ?, ?)
           ORDER BY sv.vote_date, sv.vote_time""",
        (pid, *_CAST),
    ):
        out.setdefault(r["document_nr"] or f"vote:{r['id']}", []).append(dict(r))
    return out


def _days_apart(a: str | None, b: str | None) -> int | None:
    try:
        return abs((date.fromisoformat((a or "")[:10]) - date.fromisoformat((b or "")[:10])).days)
    except ValueError:
        return None


def score(cos: float, lex: float, same_topic: bool, days: int | None) -> float:
    recency = RECENCY_BONUS * math.exp(-days / RECENCY_DAYS) if days is not None else 0.0
    return COSINE_WEIGHT * cos + LEXICAL_WEIGHT * lex + (TOPIC_BONUS if same_topic else 0.0) + recency


def shortlist(
    db: sqlite3.Connection,
    pid: int,
    position_ids: list[int],
    top: int = DEFAULT_TOP,
    vectors: dict[str, np.ndarray] | None = None,
    bills: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Katrai pozīcijai `top` tuvākie likumprojekti, par kuriem deputāts ir balsojis.

    Atgriež `{"positions": [...], "stats": {...}}`; `stats` ir saucēji — cik likumprojektu
    bija izvēlē un cik pozīciju izlaistas bez vektora vai datuma.
    """
    ensure_vec(db)
    bills = bills if bills is not None else load_bills(db)
    vectors = vectors if vectors is not None else bill_vectors(bills)
    ballots = {k: v for k, v in deputy_ballots(db, pid).items() if k in bills and bills[k]["substantive"]}
    stats = {"bills_voted": len(ballots), "positions_in": len(position_ids), "no_vector": 0, "top": top}
    out = []
    for cid in position_ids:
        pos = db.execute(
            "SELECT id, topic, stance, quote, stated_at FROM claims WHERE id = ? AND opponent_id = ? AND claim_type = 'position'",
            (cid, pid),
        ).fetchone()
        vec = _claim_vector(db, cid) if pos else None
        if pos is None or vec is None:
            stats["no_vector"] += 1
            continue
        text = f"{pos['stance'] or ''} {pos['quote'] or ''}"
        ranked = []
        for key, own in ballots.items():
            b = bills[key]
            days = min((d for d in (_days_apart(pos["stated_at"], v["vote_date"]) for v in own) if d is not None), default=None)
            s = score(float(np.dot(vec, vectors[key])), lexical_overlap(text, b["text"]), b["topic"] == pos["topic"], days)
            ranked.append((s, key))
        ranked.sort(reverse=True)
        out.append({
            "claim_id": cid, "topic": pos["topic"], "stated_at": pos["stated_at"], "stance": pos["stance"],
            "quote": pos["quote"],
            "bills": [{"key": key, "score": round(s, 3), "topic": bills[key]["topic"], "text": bills[key]["text"],
                       "ballots": ballots[key]} for s, key in ranked[:top]],
        })
    return {"positions": out, "stats": stats}


def positions_for_votes(
    db: sqlite3.Connection,
    pid: int,
    vote_day: str,
    top: int = DEFAULT_TOP,
    vectors: dict[str, np.ndarray] | None = None,
    bills: dict[str, dict[str, Any]] | None = None,
    only_keys: set[str] | None = None,
) -> dict[str, Any]:
    """Pretējais virziens: dienas balsojumi pret VISĀM deputāta pozīcijām.

    Sēdes dienā jaunais ir balsojums, ne izteikums (#56: izteikums 16.09.,
    balsojums 08.10.), un `shortlist()` ar dienas pozīcijām to neredz.
    Katram likumprojektam, par kuru deputāts `vote_day` nodevis saturisku balsi,
    atgriež `top` tuvākās viņa pozīcijas. `only_keys` — tikai zelta testam.
    """
    from src.contradiction_candidates import load_position_vectors

    bills = bills if bills is not None else load_bills(db)
    vectors = vectors if vectors is not None else bill_vectors(bills)
    ballots = {k: v for k, v in deputy_ballots(db, pid).items() if k in bills and bills[k]["substantive"]}
    todays = {k: v for k, v in ballots.items() if any(b["vote_date"] == vote_day for b in v)}
    if only_keys is not None:
        todays = {k: v for k, v in ballots.items() if k in only_keys}
    ids, matrix = load_position_vectors(db, pid)
    meta = {}
    if ids:
        q = f"SELECT id, topic, stance, quote, stated_at FROM claims WHERE id IN ({','.join('?' * len(ids))})"
        meta = {r["id"]: r for r in db.execute(q, ids)}
    out = []
    for key, own in todays.items():
        b = bills[key]
        cos = matrix @ vectors[key] if ids else np.zeros(0)
        ranked = []
        for cid, c in zip(ids, cos, strict=True):
            m = meta[cid]
            days = min((d for d in (_days_apart(m["stated_at"], v["vote_date"]) for v in own) if d is not None), default=None)
            text = f"{m['stance'] or ''} {m['quote'] or ''}"
            ranked.append((score(float(c), lexical_overlap(text, b["text"]), b["topic"] == m["topic"], days), cid))
        ranked.sort(reverse=True)
        out.append({"key": key, "topic": b["topic"], "text": b["text"], "ballots": own,
                    "positions": [{"claim_id": cid, "score": round(s, 3), "stated_at": meta[cid]["stated_at"],
                                   "topic": meta[cid]["topic"], "stance": meta[cid]["stance"]} for s, cid in ranked[:top]]})
    return {"bills": out, "stats": {"bills_today": len(todays), "positions": len(ids), "top": top}}


# --- Jev priekššķirotājs pārim (pozīcija, likumprojekts ar paša balsi) ---------------------
# Uz API iet tikai publisku avotu teksts: izteikums, likumprojekta apraksts, balss. Bez vārda.
VOTE_CONTEXT = {"politician": "izteikumu ir teicis un balsi nodevis viens un tas pats deputāts"}
VOTE_INSTRUCTIONS = (
    "Vai `{row}.statement` (deputāta paša izteikums) un `{row}.ballot` (viņa balss par `{row}.bill`) "
    "ir nesavienojami — viens un tas pats cilvēks par vienu un to pašu konkrēto lietu ar vārdiem "
    "saka vienu, bet ar balsi dara pretējo, vai arī vēlāk noliedz vai nožēlo to, par ko pats balsoja?"
)
# v2 (2026-11-13): v1 prasīja «balsojis pretēji tam, ko saka» un zelta testā pie θ=0,2 paturēja 6/13 —
# tas neredzēja apgriešanos PĒC balsojuma (#59–#64: balsoja par, tad prasa atcelt) un «mēs vienmēr bijām pret» (#68).
VOTE_CRITERIA = {
    "true": ("izteikums un likumprojekts ir par vienu un to pašu konkrēto lēmumu, personu vai pasākumu, UN: "
             "saka, ka iebilst vai vienmēr iebildis — bet balsoja par; vai saka, ka atbalsta, prasa vai sola — "
             "bet balsoja pret vai atturējās; vai balsoja par lēmumu un pēc tam to sauc par kļūdu, prasa atcelt "
             "vai balso par tā atcelšanu; vai solīja atbalstīt un pēc tam balsoja par atcelšanu"),
    "false": ("likumprojekts ir par citu lietu nekā izteikums, kopīga tikai plašā tēma; vai balss saskan ar "
              "izteikumu; vai izteikums ir vispārīgs vērtējums vai kritika, ko šī konkrētā balss neapgāž"),
}


def main_ballot(ballots: list[dict[str, Any]]) -> dict[str, Any]:
    """Balss par likumprojektu kopumā: pēdējais balsojums, kas nav par atsevišķu priekšlikumu."""
    whole = [b for b in ballots if not (b["motif"] or "").lstrip().startswith("Par priekšlikumu")]
    return (whole or ballots)[-1]


def pair_state(position: dict[str, Any], bill: dict[str, Any]) -> dict[str, Any]:
    """Jev `state` vienam pārim; `position` un `bill` — kā `shortlist()` rezultātā."""
    main = main_ballot(bill["ballots"])
    # Balsis par atsevišķiem priekšlikumiem Jev nedod: izmēģināts 2026-11-13, #68 nokrita no 0,72 uz 0,30
    # (jaukta ķēde sajauc), #65 pacēlās tikai no 0,09 uz 0,14. Priekšlikumu pretrunas šis filtrs neredz.
    ballot = main["vote"]
    return {
        "statement": {"text": position["stance"], "quote": position.get("quote"), "date": (position["stated_at"] or "")[:10]},
        "bill": {"text": bill["text"][:700], "voted": main["vote_date"], "motif": (main["motif"] or "")[:200]},
        "ballot": ballot,
        "order": "izteikums PĒC balsojuma" if (position["stated_at"] or "")[:10] > (main["vote_date"] or "") else "izteikums PIRMS balsojuma",
    }
