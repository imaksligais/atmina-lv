"""Replace the English web-method calque in claim 704223."""
import sqlite3
DB=r"E:\atmina\data\atmina.db"
CID=704223
OLD_STANCE='Norāda, ka no partiju reitingu aptaujām nevajadzētu izdarīt tālejošus secinājumus, jo šogad aptauja veikta tikai ar web metodi un 1200 respondentiem, kamēr 2022. gadā pirms vēlēšanām — ar kombinētām metodēm un 1800 respondentiem, un toreiz aptaujas rezultāti atšķīrās no faktiskajiem Saeimas vēlēšanu rezultātiem.'
NEW_STANCE='Norāda, ka no partiju reitingu aptaujām nevajadzētu izdarīt tālejošus secinājumus, jo šogad aptauja veikta tikai tīmeklī, aptaujājot 1200 respondentus, kamēr 2022. gadā pirms vēlēšanām — ar kombinētām metodēm un 1800 respondentiem, un toreiz aptaujas rezultāti atšķīrās no faktiskajiem Saeimas vēlēšanu rezultātiem.'
OLD_REASONING='Hermanis tvītā 2026-08-27 brīdina neizdarīt tālejošus secinājumus no reitingu aptaujām, salīdzinot šī gada augusta aptauju (tikai web, 1200 respondenti) ar 2022. gada pirmsvēlēšanu aptauju (kombinētas metodes, 1800 respondenti) un norādot uz atšķirību starp toreizējiem aptaujas rezultātiem un faktiskajiem Saeimas vēlēšanu rezultātiem. Pozīcija par reitingu ticamību vēlēšanu kontekstā; formulēta kā aicinājums kritiski vērtēt, ne kategorisks apgalvojums — tāpēc confidence 0.6 un quote=null (pozīcija izriet no visa tvīta salīdzinājuma).'
NEW_REASONING='Hermanis tvītā 2026-08-27 brīdina neizdarīt tālejošus secinājumus no reitingu aptaujām, salīdzinot šī gada augusta aptauju (tikai tīmeklī, 1200 respondenti) ar 2022. gada pirmsvēlēšanu aptauju (kombinētas metodes, 1800 respondenti) un norādot uz atšķirību starp toreizējiem aptaujas rezultātiem un faktiskajiem Saeimas vēlēšanu rezultātiem. Pozīcija par reitingu ticamību vēlēšanu kontekstā; formulēta kā aicinājums kritiski vērtēt, ne kategorisks apgalvojums — tāpēc confidence 0.6 un quote=null (pozīcija izriet no visa tvīta salīdzinājuma).'
db=sqlite3.connect(DB)
row=db.execute("select stance,reasoning from claims where id=?",(CID,)).fetchone()
assert row==(OLD_STANCE,OLD_REASONING), row
with db:
    n=db.execute("update claims set stance=?, reasoning=? where id=?",(NEW_STANCE,NEW_REASONING,CID)).rowcount
assert n==1
print("OK: corrected claim 704223 terminology")
