"""Delete claim 704258: source is the known Stendzenieks satire case."""
import sqlite3
import sqlite_vec
DB=r"E:\atmina\data\atmina.db"
CLAIM_ID=704258
EXPECTED_SOURCE='https://x.com/E_Stendzenieks/status/2092237283135021540'
EXPECTED_QUOTE='Ja vien mēs būtu bijuši pie varas, nekas tāds nenotiktu'
db=sqlite3.connect(DB)
db.enable_load_extension(True)
sqlite_vec.load(db)
db.enable_load_extension(False)
db.row_factory=sqlite3.Row
row=db.execute("select source_url,quote from claims where id=?",(CLAIM_ID,)).fetchone()
assert row is not None, "claim missing"
assert row['source_url']==EXPECTED_SOURCE and row['quote']==EXPECTED_QUOTE, dict(row)
refs=db.execute("select count(*) from contradictions where claim_old_id=? or claim_new_id=?",(CLAIM_ID,CLAIM_ID)).fetchone()[0]
assert refs==0, f"claim has {refs} contradiction refs"
with db:
    db.execute("delete from claim_vectors where claim_id=?",(CLAIM_ID,))
    deleted=db.execute("delete from claims where id=?",(CLAIM_ID,)).rowcount
assert deleted==1
assert db.execute("select 1 from claims where id=?",(CLAIM_ID,)).fetchone() is None
db.close()
print("OK: deleted known satire claim 704258 and vector")
