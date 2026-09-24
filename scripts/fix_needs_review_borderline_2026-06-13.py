"""NEEDS_REVIEW borderline resolution (2026-06-13, follow-up to fix_needs_review_triage).

Operator decision on the 9 BORDERLINE claims:
  - 2 MOVE (current topic is a factual mismatch, alternative clearly less wrong):
      #527841 Pūce    Sabiedriskie mediji -> Kultūra (komercprese veikalos, NE sabiedriskā apraide)
      #14486  Seržants Ārpolitika -> Kultūra (iekšzemes ideoloģiska polemika pret marksismu, NE ārpolitika)
  - 7 KEEP (tēmas patiesi līdzvērtīgas; pašreizējā aizstāvama): 531926, 527838, 527824, 521946, 521001, 20387, 17962
  - De-flag ALL 9 (operatora izskatīts): reasoning 'NEEDS_REVIEW' -> 'REVIEWED 2026-06-13'.

Touches ONLY claims.topic (2) + claims.reasoning (9). Paired rollback regenerated from live pre-state.
Dry-run by default; --apply to write.
"""
import sys, os
sys.path.insert(0, os.getcwd())
import sqlite3

DB = 'data/atmina.db'
APPLY = '--apply' in sys.argv

MOVES = {527841: 'Kultūra', 14486: 'Kultūra'}
ALL9 = [531926, 527841, 527838, 527824, 521946, 521001, 20387, 17962, 14486]


def q(s):
    return 'NULL' if s is None else "'" + s.replace("'", "''") + "'"


db = sqlite3.connect(DB)
db.row_factory = sqlite3.Row

roll = ["-- Rollback: reverš scripts/fix_needs_review_borderline_2026-06-13.py",
        "-- Atjauno 2 MOVE topic + 9 de-flag reasoning. Apply date: 2026-06-13.", ""]
for cid in MOVES:
    old = db.execute('SELECT topic FROM claims WHERE id=?', (cid,)).fetchone()['topic']
    roll.append(f"UPDATE claims SET topic={q(old)} WHERE id={cid};")
new_reason = {}
for cid in ALL9:
    old = db.execute('SELECT reasoning FROM claims WHERE id=?', (cid,)).fetchone()['reasoning']
    new_reason[cid] = (old or '').replace('NEEDS_REVIEW', 'REVIEWED 2026-06-13')
    roll.append(f"UPDATE claims SET reasoning={q(old)} WHERE id={cid};")

with open('data/rollback_needs_review_borderline_2026-06-13.sql', 'w', encoding='utf-8') as f:
    f.write('\n'.join(roll) + '\n')

still = db.execute("SELECT COUNT(*) FROM claims c JOIN tracked_politicians t ON t.id=c.opponent_id "
                   "WHERE c.reasoning LIKE '%NEEDS_REVIEW%' AND c.claim_type='position' "
                   "AND t.relationship_type!='inactive'").fetchone()[0]
print(f'pre: {still} active NEEDS_REVIEW | MOVE {len(MOVES)} + de-flag {len(ALL9)} | rollback written')
if not APPLY:
    print('[DRY-RUN]')
    sys.exit(0)
for cid, t in MOVES.items():
    db.execute('UPDATE claims SET topic=? WHERE id=?', (t, cid))
for cid, r in new_reason.items():
    db.execute('UPDATE claims SET reasoning=? WHERE id=?', (r, cid))
db.commit()
after = db.execute("SELECT COUNT(*) FROM claims c JOIN tracked_politicians t ON t.id=c.opponent_id "
                   "WHERE c.reasoning LIKE '%NEEDS_REVIEW%' AND c.claim_type='position' "
                   "AND t.relationship_type!='inactive'").fetchone()[0]
print(f'APPLIED. active NEEDS_REVIEW {still} -> {after} (expected 5 = re-ingest only).')
