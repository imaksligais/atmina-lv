"""Verdikts 3 (docs/verdikti-2026-11-03.md): pārrēķina glabāto `claims.salience` saeima_vote rindām.

Kods labots 2026-10-18 (lasījuma/nodošanas formas) un 2026-11-03 (termiņa balsojumi = 0,4),
bet glabātās rindas nesa veco noteikumu. Savienojums claims.source_url = _resolve_vote_url(
saeima_votes.url) — kā docs/audits/2026-10-18-vote-salience/salience_denominator.py.
URL ar vairākiem motīviem, kas dod dažādu salience, izlaiž un saskaita (neminē).
stance/topic nemainās → idempotences atslēga un vektori neskarti (saeima_vote rindām vektoru nav).

Bez karoga: tikai skaita. `--apply`: saglabā vecās vērtības tabulā `_salience_old_2026_11_03`
un raksta jaunās vienā transakcijā. Rollback: data/rollback_vote_salience_2026-11-03.sql
"""
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.db import get_db  # noqa: E402
from src.saeima.claims import _vote_salience  # noqa: E402
from src.saeima.votes import _resolve_vote_url  # noqa: E402

BACKUP_TABLE = "_salience_old_2026_11_03"
# 0,3 / 0,6 ielikusi 2026-04-05 ielāde; neviena _vote_salience versija tās nedod — atstāj (T18/T19).
LEGACY = (0.3, 0.6)


def plan(db):
    url2sal: dict[str, set[float]] = {}
    for url, motif in db.execute("SELECT url, motif FROM saeima_votes WHERE url IS NOT NULL"):
        url2sal.setdefault(_resolve_vote_url(url), set()).add(_vote_salience(motif or ""))
    changes, stats = [], Counter()
    for cid, src, sal in db.execute(
            "SELECT id, source_url, salience FROM claims WHERE claim_type='saeima_vote'"):
        s = url2sal.get(src)
        if sal in LEGACY:
            stats["legacy"] += 1
        elif not s:
            stats["unmatched"] += 1
        elif len(s) > 1:
            stats["ambiguous"] += 1
        else:
            new = next(iter(s))
            if sal is None or abs(new - sal) > 1e-9:
                changes.append((new, cid, sal))
                stats[(sal, new)] += 1
            else:
                stats["same"] += 1
    return changes, stats


def main(apply: bool) -> None:
    db = get_db()
    changes, stats = plan(db)
    total = db.execute("SELECT count(*) FROM claims WHERE claim_type='saeima_vote'").fetchone()[0]
    print(f"saeima_vote kopā {total}; mainīsies {len(changes)}; nemainās {stats['same']}; "
          f"bez balsojuma {stats['unmatched']}; divdomīgi {stats['ambiguous']}; "
          f"mantotās 0,3/0,6 (neaiztiek) {stats['legacy']}")
    for k, n in sorted(((k, n) for k, n in stats.items() if isinstance(k, tuple)), key=lambda x: -x[1]):
        print(f"  {k[0]} -> {k[1]}: {n}")
    if not apply:
        return
    if db.execute("SELECT count(*) FROM sqlite_master WHERE name=?", (BACKUP_TABLE,)).fetchone()[0]:
        sys.exit(f"STOP: {BACKUP_TABLE} jau eksistē (atkārtots apply?)")
    with db:
        db.execute(f"CREATE TABLE {BACKUP_TABLE} (id INTEGER PRIMARY KEY, salience REAL)")
        db.executemany(f"INSERT INTO {BACKUP_TABLE} VALUES (?, ?)", [(c, o) for _, c, o in changes])
        n = db.executemany("UPDATE claims SET salience=? WHERE id=?",
                           [(new, cid) for new, cid, _ in changes]).rowcount
    saved = db.execute(f"SELECT count(*) FROM {BACKUP_TABLE}").fetchone()[0]
    print(f"rakstīts {n}/{len(changes)}; rezerves tabulā {saved}")
    if n != len(changes) or saved != len(changes):
        sys.exit("STOP: skaits nesakrīt")


if __name__ == "__main__":
    main("--apply" in sys.argv)
