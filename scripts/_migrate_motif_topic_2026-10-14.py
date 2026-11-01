"""Verdikti 2026-10-14 § C3 — 1. fāze: sagatavo balsojumu tēmu migrāciju.

Lasa dzīvo DB (tikai SELECT) un uzraksta divus failus:
  data/fix_verdikti_h3_2026-10-14.sql       — forward UPDATE (NEPIEMĒRO šis skripts)
  data/rollback_verdikti_h3_2026-10-14.sql  — pāra rollback pa claim id

Migrācijas saraksts = balsojumi, kuriem `_map_motif_text(motif)` (vecā kartēšana)
≠ `_motif_to_topic(motif)` (nogriež nodošanas klauzulu) — TIKAI klauzulas dēļ.
Glabātais `topic` sarakstu neizvēlas (104 «drift» rindas nav migrācija); ja
glabātais ≠ vecais atvasinātais, skripts apstājas.

Pārbaudes (katra apstādina, ja krīt): url unikāls; katrs claims.topic ==
saeima_votes.topic; kolīzijas uz (opponent_id, source_url, jaunā tēma) — ja > 0,
skripts apstājas (dedup lēmums operatoram, ne šim skriptam).
Bez re-embed: `saeima_vote` rindām vektora nav.

    PYTHONUTF8=1 .venv/Scripts/python.exe scripts/_migrate_motif_topic_2026-10-14.py
    ... --verify   # pēc 2. fāzes: saglabāts == iecerēts (25 balsojumi, 2 181 claims)
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

# Vēsturisks vienreizējs skripts: tēmu atvasina no motīva, tāpēc pēc tēmu partijām
# (scripts/vote_topics.py) atkārtots skrējiens radītu T2 dublikātus vai pārrakstītu tēmas.
if __name__ == "__main__" and "--i-know" not in sys.argv[1:]:
    sys.exit("vēsturisks skripts — nepalaist pēc 2026-10-21 tēmu partijām (apzināti: --i-know)")
sys.argv = [a for a in sys.argv if a != "--i-know"]

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import PRODUCTION_DB_PATH  # noqa: E402
from src.saeima.claims import _map_motif_text, _motif_to_topic  # noqa: E402

FIX = ROOT / "data" / "fix_verdikti_h3_2026-10-14.sql"
ROLLBACK = ROOT / "data" / "rollback_verdikti_h3_2026-10-14.sql"
EXPECTED_VOTES, EXPECTED_CLAIMS = 25, 2181


def _q(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def main() -> int:
    verify = "--verify" in sys.argv[1:]
    db = sqlite3.connect(f"file:{PRODUCTION_DB_PATH}?mode=ro", uri=True)
    rows = db.execute(
        "SELECT id, motif, topic, url FROM saeima_votes WHERE motif LIKE '%komisij%' ORDER BY id"
    ).fetchall()
    plan, problems = [], []
    for vid, motif, stored, url in rows:
        old, new = _map_motif_text(motif), _motif_to_topic(motif)
        if old == new:
            continue
        if verify:
            got = db.execute(
                "SELECT COUNT(*) FROM claims WHERE claim_type='saeima_vote' AND source_url = ? AND topic = ?",
                (url, new),
            ).fetchone()[0]
            total = db.execute(
                "SELECT COUNT(*) FROM claims WHERE claim_type='saeima_vote' AND source_url = ?", (url,)
            ).fetchone()[0]
            plan.append((vid, stored == new, got, total))
            continue
        if stored != old:
            problems.append(f"vote {vid}: glabātais {stored!r} ≠ vecais atvasinātais {old!r}")
        n_url = db.execute("SELECT COUNT(*) FROM saeima_votes WHERE url = ?", (url,)).fetchone()[0]
        if n_url != 1:
            problems.append(f"vote {vid}: url nav unikāls ({n_url})")
        claims = db.execute(
            "SELECT id, opponent_id, topic FROM claims WHERE claim_type='saeima_vote' AND source_url = ?",
            (url,),
        ).fetchall()
        off = [c for c in claims if c[2] != stored]
        if off:
            problems.append(f"vote {vid}: {len(off)} claims ar topic ≠ balsojuma topic")
        collisions = db.execute(
            "SELECT c.id FROM claims c JOIN claims o ON o.opponent_id = c.opponent_id "
            "AND o.source_url = c.source_url WHERE c.claim_type='saeima_vote' AND c.source_url = ? "
            "AND o.topic = ? AND o.id <> c.id",
            (url, new),
        ).fetchall()
        if len({c[1] for c in claims}) != len(claims):
            problems.append(f"vote {vid}: viens deputāts ar >1 claim — UPDATE radītu dublikātu")
        plan.append((vid, motif, old, new, [c[0] for c in claims], len(collisions)))
    db.close()

    if verify:
        ok_votes = sum(1 for p in plan if p[1])
        got, total = sum(p[2] for p in plan), sum(p[3] for p in plan)
        print(f"verify: balsojumi ar jauno tēmu {ok_votes}/{len(plan)}; claims ar jauno tēmu {got}/{total}")
        good = (ok_votes, len(plan), got, total) == (EXPECTED_VOTES,) * 2 + (EXPECTED_CLAIMS,) * 2
        print("OK" if good else "STOP: saglabāts ≠ iecerēts")
        return 0 if good else 2

    n_votes, n_claims = len(plan), sum(len(p[4]) for p in plan)
    n_coll = sum(p[5] for p in plan)
    print(f"saucējs: {len(rows)} balsojumi ar «komisij»; mainās {n_votes}; claims {n_claims}; kolīzijas {n_coll}")
    for vid, motif, old, new, ids, coll in plan:
        print(f"  {vid}: {old} → {new} ({len(ids)} claims, kolīzijas {coll}) | {motif[:90]}")
    if n_coll:
        problems.append(f"{n_coll} kolīzijas — dedup lēmums vajadzīgs PIRMS UPDATE")
    if (n_votes, n_claims) != (EXPECTED_VOTES, EXPECTED_CLAIMS):
        problems.append(f"skaits {n_votes}/{n_claims} ≠ gaidītais {EXPECTED_VOTES}/{EXPECTED_CLAIMS}")
    if problems:
        print("STOP:\n  " + "\n  ".join(problems))
        return 2

    head = (
        "-- Verdikti 2026-10-14 § C3: {what}\n"
        "-- Forward: {n} saeima_votes.topic + {c} saeima_vote claims.topic uz `_motif_to_topic()`\n"
        "-- ar nogrieztu nodošanas klauzulu (src/saeima/claims.py, 2026-10-14). Kolīzijas pirms UPDATE: 0.\n"
        "-- Bez re-embed (saeima_vote rindām vektora nav). Ģenerēts: scripts/_migrate_motif_topic_2026-10-14.py\n"
    )
    fwd = [head.format(what="forward (pāra rollback data/rollback_verdikti_h3_2026-10-14.sql)",
                       n=n_votes, c=n_claims), "BEGIN TRANSACTION;"]
    back = [head.format(what="ROLLBACK (atjauno vecās tēmas pa claim id)", n=n_votes, c=n_claims),
            "BEGIN TRANSACTION;"]
    for vid, _motif, old, new, ids, _ in plan:
        idl = ",".join(map(str, ids))
        fwd.append(f"-- vote {vid}: {old} → {new} ({len(ids)} claims)")
        fwd.append(f"UPDATE saeima_votes SET topic = {_q(new)} WHERE id = {vid} AND topic = {_q(old)};")
        fwd.append(f"UPDATE claims SET topic = {_q(new)} WHERE claim_type = 'saeima_vote' "
                   f"AND id IN ({idl}) AND topic = {_q(old)};")
        back.append(f"-- vote {vid}: {new} → {old} ({len(ids)} claims)")
        back.append(f"UPDATE saeima_votes SET topic = {_q(old)} WHERE id = {vid} AND topic = {_q(new)};")
        back.append(f"UPDATE claims SET topic = {_q(old)} WHERE claim_type = 'saeima_vote' "
                    f"AND id IN ({idl}) AND topic = {_q(new)};")
    fwd.append("COMMIT;")
    back.append("COMMIT;")
    FIX.write_text("\n".join(fwd) + "\n", encoding="utf-8")
    ROLLBACK.write_text("\n".join(back) + "\n", encoding="utf-8")
    print(f"uzrakstīts: {FIX.relative_to(ROOT)}, {ROLLBACK.relative_to(ROOT)} (NEPIEMĒROTS)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
