"""Apply round-three QA fixes. Rollback in data/."""
import sqlite3
DB=r"E:\atmina\data\atmina.db"
FIXES={704249:('stance','Aicina 3. oktobrī balsot par MMN sarakstu Nr. 2, lai izdzenātu uzblīdušo valsts pārvaldi un panāktu iespēju balsot par konkrētiem cilvēkiem, nevis partiju sarakstiem; kā MMN galveno mērķi min individuālās atbildības noteikšanu valsts pārvaldē.','Aicina 3. oktobrī balsot par MMN sarakstu Nr. 2, lai izdzenātu uzblīdušo valsts pārvaldi un panāktu iespēju balsot par konkrētiem cilvēkiem, nevis partiju sarakstiem; kā vienu no MMN galvenajiem mērķiem min individuālās atbildības noteikšanu valsts pārvaldē.'),704251:('reasoning','RT @partijaMMN ar pašatribūcijas formu („Jānis Hermanis par latviešu zaudētajiem mūža gadiem“) — RT ķēde nosauc pašu politiķi kā citēto vārdu avotu, tātad pirmās personas pozīcija (689246 klase: conf 0.6, quote=None). Tēma: zaudēto mūža gadu rādītājs + veselības aprūpes sistēmas pārskatīšana → Veselības aprūpe (robežprecedents 689296/689498; paša 703940 veselīgā mūža ilguma klase). Aicinājuma verbu stiprums saglabāts no avota („aicina pārskatīt“). Sal 0.5.','NEEDS_REVIEW: RT @partijaMMN ar pašatribūcijas formu („Jānis Hermanis par latviešu zaudētajiem mūža gadiem“) — RT ķēde nosauc pašu politiķi kā citēto vārdu avotu, tātad pirmās personas pozīcija (689246 klase: conf 0.6, quote=None). Tēma: zaudēto mūža gadu rādītājs + veselības aprūpes sistēmas pārskatīšana → Veselības aprūpe (robežprecedents 689296/689498; paša 703940 veselīgā mūža ilguma klase). Aicinājuma verbu stiprums saglabāts no avota („aicina pārskatīt“). Sal 0.5.')}
conn=sqlite3.connect(DB)
conn.execute("BEGIN")
for cid,(field,old,new) in FIXES.items():
 row=conn.execute(f"select {field} from claims where id=?",(cid,)).fetchone()
 assert row and row[0]==old,(cid,row)
 conn.execute(f"update claims set {field}=? where id=?",(new,cid))
conn.commit()
conn.close()
print("OK: corrected round-three claims")
