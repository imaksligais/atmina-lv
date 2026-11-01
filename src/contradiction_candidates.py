"""Kandidātu pāri retorika-pret-retoriku pretrunu meklēšanai + Jev jautājums.

Kāpēc kNN, ne visi pāri: 170 politiķiem visi pāri = 532 250 (2026-09-18);
politiķim ar 570 pozīcijām vien 162 165. Kosinusa slieksnis neko nefiltrē
(hunter prompts § threshold), bet RELATĪVĀ kaimiņu secība tur informāciju:
no 23 zelta position↔position pretrunām 21 ir viena otras top-40 kaimiņos,
22 top-100 (#37 rank 82), #4 (rank 132) — ne. Tāpēc k ir pilnīguma
griesti, un katrs skripts to drukā kā denominatoru.

Jev vērtē pāri, ne meklē: šis modulis dod pārus + `state`, `src.jev_filter`
tos sūta. Neviens ceļš šeit neraksta DB.

Pozīcijas bez `stated_at` netiek iekļautas kandidātu kopā: virziens (kas ir agrākais,
kas vēlākais izteikums) ir pretrunas kā apgriešanās priekšnoteikums, un bez datuma
tas nav zināms (lēmums 2026-09-18); `undated_positions()` dod izlaisto skaitu kā
denominatoru skriptiem.
"""
from __future__ import annotations

import sqlite3
from typing import Optional

import numpy as np

from src.db import get_db
from src.party_contradictions import ensure_vec

DEFAULT_K = 40

# Uz API iet tikai šie lauki — publisku avotu teksts, bez vārda un bez reasoning.
PAIR_CONTEXT = {"politician": "abus izteikumus ir teicis viens un tas pats politiķis",
                "old": "agrākais izteikums", "new": "vēlākais izteikums"}
# Jautājums v2 (2026-09-18): NESAVIENOJAMĪBA, ne burtiska pretstatīšana. v1 («vai new
# nostāja ir pretēja old nostājai tajā pašā konkrētajā jautājumā») zelta testā deva 2/18
# apstiprināto pretrunu virs 0,5 — atmina pretruna ir plašāka: mainīts vērtējums par
# partneri (#17), nodoms → rīcība (#44), šaubas → pretējs lēmums (#38). v2 pilotā
# (21 zelta + 1000 nejauši pāri): pie θ=0,3 zelts 16/18, nejaušo paliek 6,7 %;
# pie θ=0,22 18/18 un 32 %. Divi zem 0,3: #36 (nosacījums ir pretrunas kopsavilkumā,
# ne pozīcijās — datu robs) un #17 (robežgadījums). CHANGELOG 2026-09-18 (2).
OPPOSITE_INSTRUCTIONS = (
    "Vai `{row}.new` (vēlākais izteikums vai rīcība) ir nesavienojams ar `{row}.old` "
    "(agrākais izteikums) — politiķis ir mainījis nostāju, vērtējumu vai nodomu par to pašu "
    "lietu, personu vai partneri?"
)
OPPOSITE_CRITERIA = {
    "true": ("new apgriež, atsauc vai padara neticamu to, ko old apgalvoja, vērtēja vai solīja: "
             "agrāk atbalstīja — tagad iebilst; agrāk izslēdza — tagad pieļauj vai dara; "
             "agrāk nosodīja — tagad sadarbojas vai attaisno; agrāk šaubījās vai noliedza — "
             "tagad paziņo pretējo; agrāk solīja — tagad dara citādi"),
    "false": ("abi izteikumi var būt spēkā vienlaikus: precizējums, papildinājums, cita lieta "
              "vai cits jautājums, tas pats viedoklis citiem vārdiem, vai atšķirība ir tikai "
              "tonī vai detaļās"),
}
DEFAULT_THRESHOLD = 0.3   # zelta tests 2026-09-18: 16/18 apstiprināto, 6,7 % kandidātu paliek

_POSITIONS_SQL = """
    SELECT c.id, v.embedding
      FROM claims c JOIN claim_vectors v ON v.claim_id = c.id
     WHERE c.opponent_id = ? AND c.claim_type = 'position'
       AND (c.speaker_id IS NULL OR c.speaker_id = c.opponent_id)
       AND c.stated_at IS NOT NULL
     ORDER BY c.id
"""

_UNDATED_POSITIONS_SQL = """
    SELECT COUNT(*)
      FROM claims c
     WHERE c.opponent_id = ? AND c.claim_type = 'position'
       AND (c.speaker_id IS NULL OR c.speaker_id = c.opponent_id)
       AND c.stated_at IS NULL
"""


def load_position_vectors(db: sqlite3.Connection, opponent_id: int) -> tuple[list[int], np.ndarray]:
    """Pirmās puses `position` pozīcijas ar vektoru; matrica L2-normēta (dot == cos)."""
    ensure_vec(db)
    rows = db.execute(_POSITIONS_SQL, (opponent_id,)).fetchall()
    if not rows:
        return [], np.zeros((0, 384), dtype=np.float32)
    ids = [int(r[0]) for r in rows]
    M = np.vstack([np.frombuffer(r[1], dtype=np.float32) for r in rows])
    norms = np.linalg.norm(M, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return ids, M / norms


def undated_positions(db: sqlite3.Connection, opponent_id: int) -> int:
    """Cik pirmās puses `position` pozīciju šim politiķim ir bez `stated_at` — tās
    neiet kandidātu pāros, jo bez datuma nav zināms virziens (sk. modula docstring).
    Šī ir rindiņa, ko skripti drukā kā denominatoru: "pozīcijas bez datuma izlaistas N"."""
    row = db.execute(_UNDATED_POSITIONS_SQL, (opponent_id,)).fetchone()
    return int(row[0])


def _order_key(db: sqlite3.Connection, ids: list[int]) -> dict[int, tuple[str, int]]:
    q = f"SELECT id, stated_at FROM claims WHERE id IN ({','.join('?' * len(ids))})"
    return {int(i): (str(s), int(i)) for i, s in db.execute(q, ids).fetchall()}


def candidate_pairs(opponent_id: int, *, k: int = DEFAULT_K,
                    db_path: Optional[str] = None) -> list[tuple[int, int]]:
    """Unikāli `(old_id, new_id)` pāri: katrai pozīcijai tās top-k kaimiņi pēc kosinusa.

    Pozīcijas bez `stated_at` netiek ņemtas vērā — virziens ir pretrunas priekšnoteikums."""
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")
    db = get_db(db_path)
    try:
        ids, M = load_position_vectors(db, opponent_id)
        if len(ids) < 2:
            return []
        sims = M @ M.T
        np.fill_diagonal(sims, -np.inf)
        kk = min(k, len(ids) - 1)
        seen: set[frozenset[int]] = set()
        for i in range(len(ids)):
            top = np.argpartition(-sims[i], kk - 1)[:kk] if kk < len(ids) - 1 else np.arange(len(ids))
            for j in top:
                if j != i:
                    seen.add(frozenset((ids[i], ids[int(j)])))
        order = _order_key(db, ids)
        pairs = [tuple(sorted(p, key=lambda cid: order[cid])) for p in seen]
        return sorted(pairs, key=lambda ab: (order[ab[0]], order[ab[1]]))
    finally:
        db.close()


def pair_states(db: sqlite3.Connection, pairs: list[tuple[int, int]]) -> list[dict]:
    """Jev `state` katram pārim — tikai stance/quote/topic/date, bez vārda un reasoning."""
    wanted = sorted({cid for ab in pairs for cid in ab})
    if not wanted:
        return []
    q = (f"SELECT id, stance, quote, topic, COALESCE(SUBSTR(stated_at, 1, 10), '') "
         f"FROM claims WHERE id IN ({','.join('?' * len(wanted))})")
    by_id = {int(r[0]): {"stance": r[1], "quote": r[2], "topic": r[3], "date": r[4]}
             for r in db.execute(q, wanted).fetchall()}
    return [{"old": by_id[a], "new": by_id[b]} for a, b in pairs]
