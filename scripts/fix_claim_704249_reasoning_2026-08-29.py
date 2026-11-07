"""Restore the source qualifier in claim 704249 reasoning."""
import sqlite3
DB=r"E:\atmina\data\atmina.db"
OLD='Mielavs savā pirmās personas tvītā 2026-08-29 identificējas kā MMN biedrs, nosauc partijas galveno mērķi (individuālās atbildības noteikšana valsts pārvaldē) un aicina balsot 3. oktobrī par sarakstu Nr. 2. Stance saglabā avota kvalifikatorus: konkrētais datums, saraksta numurs, formulējums par balsošanu par konkrētiem cilvēkiem, nevis partiju sarakstiem.'
NEW='Mielavs savā pirmās personas tvītā 2026-08-29 identificējas kā MMN biedrs, nosauc vienu no partijas galvenajiem mērķiem (individuālās atbildības noteikšana valsts pārvaldē) un aicina balsot 3. oktobrī par sarakstu Nr. 2. Stance saglabā avota kvalifikatorus: konkrētais datums, saraksta numurs, formulējums par balsošanu par konkrētiem cilvēkiem, nevis partiju sarakstiem.'
conn=sqlite3.connect(DB)
row=conn.execute("select reasoning from claims where id=704249").fetchone()
assert row and row[0]==OLD
conn.execute("update claims set reasoning=? where id=704249",(NEW,))
conn.commit()
conn.close()
print("OK: corrected claim 704249 reasoning")
