"""Vienreizējs `DUP_DISTANCE_MAX` mērījums (2026-09-24, rutīnas uzlabojumu Task 5).

Mēra `claim_vectors` attālumu (sqlite-vec vec0 noklusējums = L2 uz
normalizētiem e5 vektoriem; tas pats, ko atdod `search_similar_claims`)
zināmiem dublikātu pāriem un negatīvajiem pāriem, un izvēlas slieksni θ ar
0 FP uz negatīvajiem un maksimālu recall uz pozitīvajiem.

**Pozitīvie** — 2026-09-23 backfill 1. partijas dublikāti
(`docs/audits/2026-09-23-backfill-batch1/README.md` § Dublikāti). Tie paši
dublikāti tika izdzēsti (`scripts/fix_backfill_batch1_old_claims_2026-09-23.py`),
tāpēc dzēstās puses vektors DB vairs nav. To atjauno no rollback faila
(`data/rollback_backfill_batch1_old_claims_2026-09-23.sql`): tā `topic` +
`stance` tiek iegulti ar to pašu `embed_text(f"{normalize_topic(topic)}:
{stance}")`, ko lieto `store_claim` — tātad tieši tas vektors, kas būtu
glabāts. Dzīvā puse lieto glabāto vektoru. Divi 2026-09-24 pāri
(#718086↔#718085 daļējs, #718081↔#718013 tā pati nostāja, cits izteikums)
ir **robežgadījumi**: tos izdrukā, bet θ izvēlē neiekļauj.

**Negatīvie** — 30 nejauši (seed=20260924) tā paša politiķa `position` pāri
ar `stated_at` ±5 d un DAŽĀDĀM tēmām, plus 10 tās pašas tēmas pāri ar
atšķirīgu nostāju, kas izvēlēti, izlasot stance (`SAME_TOPIC_NEGATIVES`).
`--candidates` izdrukā kandidātus šī saraksta sastādīšanai.

Tikai LASA dzīvo DB (read-only URI). Palaišana no repo saknes:

    PYTHONUTF8=1 .venv/Scripts/python.exe scripts/calibrate_dup_threshold.py
    PYTHONUTF8=1 .venv/Scripts/python.exe scripts/calibrate_dup_threshold.py --candidates
"""

from __future__ import annotations

import argparse
import random
import sqlite3
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DB_URI = f"file:{(ROOT / 'data' / 'atmina.db').as_posix()}?mode=ro"
ROLLBACK_SQL = ROOT / "data" / "rollback_backfill_batch1_old_claims_2026-09-23.sql"

POSITIVES = [
    (521141, 521099), (532362, 532334), (18230, 18229), (18230, 18231),
    (18101, 18217), (520852, 520851), (520852, 520843), (521161, 521160),
    (527812, 527813), (18137, 18275),
]
BORDERLINE = [(718086, 718085), (718081, 718013)]

# Izvēlēti 2026-09-24, izlasot `--candidates` izdruku: tā pati tēma, tas pats
# politiķis, ±5 d, bet cits apgalvojums (ne pārformulējums).
# Izlaisti kā NEtīri negatīvie (tā pati nostāja citā izteikumā — tā ir
# robežgadījumu klase, ne negatīvs): #718092↔#717920, #718109↔#718075,
# #718107↔#717914, #718096↔#717724, #718083↔#717870; #718104↔#717693 —
# B puse nolasīta nepilnīgi, izlaista.
SAME_TOPIC_NEGATIVES: list[tuple[int, int]] = [
    (718087, 717917),  # kvotas + readmisijas līgumi / pabalstu datu apmaiņa
    (718115, 717860),  # liegumu kontrole / NA atsevišķais viedoklis par ĀM
    (718099, 717845),  # atzinīgi par pagarinājumu / Latvija nevar piekrist
    (718087, 717859),  # kvotas / plāns kā pirmais mēģinājums, investori
    (718076, 717708),  # hibrīddraudi bīstami / kļūda tos saukt par hibrīdiem
    (718087, 717689),  # kvotas / izraidīšanas rīkojumu skaits
    (718077, 717833),  # atsakās stāstīt par tēva firmu / aizstāv dāvinājumu
    (718069, 532391),  # solījumu finansējuma avoti / Latgales investīcijas
    (718096, 717820),  # budžeta prognoze mīnusā / ietaupījumu saraksts
    (718117, 717808),  # akcīzes nobīde / tikai PVN samazinājums
]

N_RANDOM_NEGATIVES = 30
SEED = 20260924


def _connect() -> sqlite3.Connection:
    import sqlite_vec

    db = sqlite3.connect(DB_URI, uri=True)
    db.row_factory = sqlite3.Row
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)
    return db


def _deleted_claims() -> dict[int, dict]:
    """Dzēsto claims rindas no rollback faila (tikai INSERT daļa)."""
    mem = sqlite3.connect(":memory:")
    mem.row_factory = sqlite3.Row
    mem.execute(
        "CREATE TABLE claims (id INTEGER PRIMARY KEY, opponent_id, document_id, "
        "topic, stance, quote, confidence, reasoning, salience, source_url, "
        "stated_at, created_at, claim_type, speaker_id, party_id)"
    )
    for line in ROLLBACK_SQL.read_text(encoding="utf-8").splitlines():
        if line.startswith("INSERT INTO claims"):
            mem.execute(line)
    return {r["id"]: dict(r) for r in mem.execute("SELECT * FROM claims")}


def _unpack(blob: bytes) -> list[float]:
    return list(struct.unpack(f"{len(blob) // 4}f", blob))


def _l2(a: list[float], b: list[float]) -> float:
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


class VectorSource:
    def __init__(self, db: sqlite3.Connection):
        self.db = db
        self.deleted = _deleted_claims()
        self.origin: dict[int, str] = {}

    def claim(self, cid: int) -> dict | None:
        row = self.db.execute(
            "SELECT id, opponent_id, topic, stance, stated_at, claim_type "
            "FROM claims WHERE id = ?", (cid,)
        ).fetchone()
        if row:
            return dict(row)
        return self.deleted.get(cid)

    def vector(self, cid: int) -> list[float] | None:
        row = self.db.execute(
            "SELECT embedding FROM claim_vectors WHERE claim_id = ?", (cid,)
        ).fetchone()
        if row:
            self.origin[cid] = "db"
            return _unpack(row["embedding"])
        c = self.deleted.get(cid)
        if c is None:
            return None
        from src.embeddings import embed_text
        from src.topic_map import normalize_topic

        self.origin[cid] = "rollback"
        return embed_text(f"{normalize_topic(c['topic'])}: {c['stance']}")


def _pair_distance(vs: VectorSource, a: int, b: int) -> float | None:
    va, vb = vs.vector(a), vs.vector(b)
    if va is None or vb is None:
        return None
    return _l2(va, vb)


def _random_negatives(db: sqlite3.Connection) -> list[tuple[int, int]]:
    rows = db.execute(
        """SELECT a.id AS a, b.id AS b FROM claims a
           JOIN claims b ON b.opponent_id = a.opponent_id AND b.id < a.id
             AND b.claim_type = 'position' AND b.topic != a.topic
             AND ABS(julianday(a.stated_at) - julianday(b.stated_at)) <= 5
           WHERE a.claim_type = 'position' AND a.created_at >= '2026-08-01'
             AND a.id IN (SELECT claim_id FROM claim_vectors
                          WHERE claim_id >= 700000)
             AND b.id IN (SELECT claim_id FROM claim_vectors
                          WHERE claim_id >= 600000)"""
    ).fetchall()
    rng = random.Random(SEED)
    return [(r["a"], r["b"]) for r in rng.sample(rows, N_RANDOM_NEGATIVES)]


def _print_candidates(db: sqlite3.Connection) -> None:
    rows = db.execute(
        """SELECT a.id AS a, b.id AS b, a.topic, a.stance AS sa, b.stance AS sb
           FROM claims a JOIN claims b ON b.opponent_id = a.opponent_id
             AND b.id < a.id AND b.claim_type = 'position' AND b.topic = a.topic
             AND b.source_url != a.source_url
             AND ABS(julianday(a.stated_at) - julianday(b.stated_at)) <= 5
           WHERE a.claim_type = 'position' AND a.created_at >= '2026-09-01'
           ORDER BY a.id DESC LIMIT 60"""
    ).fetchall()
    vs = VectorSource(db)
    for r in rows:
        d = _pair_distance(vs, r["a"], r["b"])
        print(f"#{r['a']} vs #{r['b']}  [{r['topic']}]  d={d}")
        print(f"   A: {r['sa']}")
        print(f"   B: {r['sb']}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", action="store_true")
    args = ap.parse_args()
    db = _connect()
    if args.candidates:
        _print_candidates(db)
        return 0

    vs = VectorSource(db)

    def run(label: str, pairs: list[tuple[int, int]]) -> list[float]:
        print(f"\n== {label} ({len(pairs)} pāri) ==")
        out = []
        for a, b in pairs:
            ca, cb = vs.claim(a), vs.claim(b)
            d = _pair_distance(vs, a, b)
            if d is None or ca is None or cb is None:
                print(f"  #{a} vs #{b}: NAV VEKTORA / RINDAS — izlaists")
                continue
            dd = abs(db.execute(
                "SELECT julianday(?) - julianday(?)",
                (ca["stated_at"], cb["stated_at"]),
            ).fetchone()[0] or 0)
            print(
                f"  #{a}({vs.origin.get(a)}) vs #{b}({vs.origin.get(b)}): "
                f"d={d:.4f}  Δdienas={dd:.0f}  tēma={ca['topic']!r}/{cb['topic']!r}"
            )
            out.append(d)
        return out

    pos = run("POZITĪVIE", POSITIVES)
    run("ROBEŽGADĪJUMI (θ izvēlē neiekļauti)", BORDERLINE)
    neg_rand = run("NEGATĪVIE — dažādas tēmas", _random_negatives(db))
    neg_topic = run("NEGATĪVIE — tā pati tēma, cita nostāja", SAME_TOPIC_NEGATIVES)
    neg = neg_rand + neg_topic

    print(f"\npozitīvie: n={len(pos)}  min={min(pos):.4f}  max={max(pos):.4f}")
    print(f"negatīvie: n={len(neg)}  min={min(neg):.4f}  max={max(neg):.4f}")
    if neg_topic:
        print(f"  tā pati tēma: min={min(neg_topic):.4f}")
    theta_limit = min(neg)
    below = [d for d in pos if d < theta_limit]
    print(
        f"θ < {theta_limit:.4f} (tuvākais negatīvais) → recall "
        f"{len(below)}/{len(pos)} = {len(below) / len(pos):.0%}, FP 0/{len(neg)}"
    )
    if below:
        print(f"  lielākais pozitīvais zem robežas: {max(below):.4f}")

    _base_rate(db)
    return 0


def _base_rate(db: sqlite3.Connection) -> None:
    """Cik bieži vārts nostrādātu dzīvajos datos (precizitātes aplēsei).

    Katram `position` claim, kas izveidots kopš 2026-09-10, tuvākais tā paša
    politiķa AGRĀKAIS `position` claim ±5 d; izdrukā, cik no tiem ir ≤ θ.
    """
    from src.analyze import DUP_DISTANCE_MAX

    rows = db.execute(
        "SELECT id, opponent_id, stated_at FROM claims "
        "WHERE claim_type = 'position' AND created_at >= '2026-09-10' "
        "AND id IN (SELECT claim_id FROM claim_vectors WHERE claim_id >= 700000)"
    ).fetchall()
    nearest = []
    for r in rows:
        q = db.execute(
            """SELECT vec_distance_l2(va.embedding, vb.embedding) AS d
               FROM claims b JOIN claim_vectors vb ON vb.claim_id = b.id,
                    claim_vectors va
               WHERE va.claim_id = ? AND b.opponent_id = ?
                 AND b.claim_type = 'position' AND b.id < ?
                 AND ABS(julianday(b.stated_at) - julianday(?)) <= 5
               ORDER BY d LIMIT 1""",
            (r["id"], r["opponent_id"], r["id"], r["stated_at"]),
        ).fetchone()
        if q:
            nearest.append(q["d"])
    print(
        f"\n== BĀZES BIEŽUMS: {len(rows)} claims kopš 2026-09-10, "
        f"{len(nearest)} ar kaimiņu ±5 d =="
    )
    for t in (0.35, 0.37, 0.39, DUP_DISTANCE_MAX, 0.42):
        n = sum(1 for d in nearest if d <= t)
        print(f"  ≤{t:.3f}: {n} ({n / max(len(nearest), 1):.1%})")


if __name__ == "__main__":
    raise SystemExit(main())
