"""Fix claim 704247 percent spacing. Rollback in data/."""
import sqlite3
DB=r"E:\atmina\data\atmina.db"
OLD='Kritizē to, ka MMN atstumta no valsts mediju un Delfi debatēm, par ieganstu izmantojot Kaktiņa aptaujas rādītājus (partijai esot zem 2%), un ironizē par šāda reitingu sliekšņa patvaļīgumu, sakot, ka debašu pielaišanas noteikumus varot mainīt pēc pašu iegribas.'
NEW='Kritizē to, ka MMN atstumta no valsts mediju un Delfi debatēm, par ieganstu izmantojot Kaktiņa aptaujas rādītājus (partijai esot zem 2 %), un ironizē par šāda reitingu sliekšņa patvaļīgumu, sakot, ka debašu pielaišanas noteikumus varot mainīt pēc pašu iegribas.'
conn=sqlite3.connect(DB)
row=conn.execute("select stance from claims where id=704247").fetchone()
assert row and row[0]==OLD, (row[0] if row else None)
conn.execute("update claims set stance=? where id=704247",(NEW,))
conn.commit()
conn.close()
print("OK: corrected claim 704247")
