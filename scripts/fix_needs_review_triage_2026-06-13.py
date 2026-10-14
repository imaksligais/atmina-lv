"""NEEDS_REVIEW triage apply (2026-06-13).

Forward change:
  - 2 topic MOVEs (clearly mis-classified per claim-extractor boundary rules):
      #521079 Štāls   Valsts kapitālsabiedrības -> Sociālā politika (dzimumu kvotas privātās sabiedrībās)
      #521011 Kulbergs Droni -> Aizsardzība un drošība (drons tikai arguments)
  - De-flag 42 resolved claims (40 KEEP + 2 MOVE): reasoning marker
      'NEEDS_REVIEW' -> 'REVIEWED 2026-06-13', so they stop re-surfacing in the queue.
  - LEFT FLAGGED (still open): 9 BORDERLINE + 5 RE-INGEST (truncated-source).

Touches ONLY claims.topic (2 rows) + claims.reasoning (42 rows). No other fields.
Paired rollback: data/rollback_needs_review_triage_2026-06-13.sql (regenerated each run from live pre-state).
Dry-run by default; --apply to write.
"""
import sys, os
sys.path.insert(0, os.getcwd())
import sqlite3

DB = 'data/atmina.db'
APPLY = '--apply' in sys.argv

MOVES = {521079: 'Sociālā politika', 521011: 'Aizsardzība un drošība'}

LEAVE_FLAGGED = {
    # 9 BORDERLINE (operator call)
    531926, 527841, 527838, 527824, 521946, 521001, 20387, 17962, 14486,
    # 5 RE-INGEST (truncated-source — fix is full-article re-ingest, not re-topic)
    531904, 527902, 527893, 527890, 527881,
}

ALL56 = [531949, 531944, 531931, 531926, 531904, 527902, 527897, 527893, 527890, 527891,
         527881, 527841, 527838, 527836, 527824, 527817, 527782, 527778, 527759, 527701,
         521946, 521942, 521937, 521928, 521922, 521110, 521108, 521102, 521095, 521093,
         521079, 521043, 521038, 521011, 521001, 520891, 23010, 20633, 20568, 20570,
         20387, 18385, 18203, 18198, 18196, 18108, 17981, 17962, 17893, 17779,
         14496, 14486, 14482, 14435, 14431, 14395]

DEFLAG = [i for i in ALL56 if i not in LEAVE_FLAGGED]
assert len(DEFLAG) == 42, f'expected 42 de-flag, got {len(DEFLAG)}'


def q(s):
    if s is None:
        return 'NULL'
    return "'" + s.replace("'", "''") + "'"


db = sqlite3.connect(DB)
db.row_factory = sqlite3.Row

roll = ["-- Rollback: reverš scripts/fix_needs_review_triage_2026-06-13.py",
        "-- Atjauno 2 MOVE topic + 42 de-flag reasoning uz pirms-migrācijas vērtībām.",
        "-- Apply date: 2026-06-13. Skar tikai claims.topic + claims.reasoning.", ""]

for cid in MOVES:
    old = db.execute('SELECT topic FROM claims WHERE id=?', (cid,)).fetchone()['topic']
    roll.append(f"UPDATE claims SET topic={q(old)} WHERE id={cid};")

new_reason = {}
for cid in DEFLAG:
    old = db.execute('SELECT reasoning FROM claims WHERE id=?', (cid,)).fetchone()['reasoning']
    new = (old or '').replace('NEEDS_REVIEW', 'REVIEWED 2026-06-13')
    new_reason[cid] = new
    roll.append(f"UPDATE claims SET reasoning={q(old)} WHERE id={cid};")

with open('data/rollback_needs_review_triage_2026-06-13.sql', 'w', encoding='utf-8') as f:
    f.write('\n'.join(roll) + '\n')

still = db.execute("SELECT COUNT(*) FROM claims c JOIN tracked_politicians t ON t.id=c.opponent_id "
                   "WHERE c.reasoning LIKE '%NEEDS_REVIEW%' AND c.claim_type='position' "
                   "AND t.relationship_type!='inactive'").fetchone()[0]
print(f'pre-state: {still} active NEEDS_REVIEW | will MOVE {len(MOVES)} topics, de-flag {len(DEFLAG)} reasoning | leave {len(LEAVE_FLAGGED)} flagged')
print('rollback written: data/rollback_needs_review_triage_2026-06-13.sql')

if not APPLY:
    print('[DRY-RUN] pass --apply to write.')
    sys.exit(0)

for cid, newt in MOVES.items():
    db.execute('UPDATE claims SET topic=? WHERE id=?', (newt, cid))
for cid, new in new_reason.items():
    db.execute('UPDATE claims SET reasoning=? WHERE id=?', (new, cid))
db.commit()

after = db.execute("SELECT COUNT(*) FROM claims c JOIN tracked_politicians t ON t.id=c.opponent_id "
                   "WHERE c.reasoning LIKE '%NEEDS_REVIEW%' AND c.claim_type='position' "
                   "AND t.relationship_type!='inactive'").fetchone()[0]
m1 = db.execute('SELECT topic FROM claims WHERE id=521079').fetchone()['topic']
m2 = db.execute('SELECT topic FROM claims WHERE id=521011').fetchone()['topic']
print(f'APPLIED. active NEEDS_REVIEW {still} -> {after} (expected 14). #521079 topic={m1!r}, #521011 topic={m2!r}')
