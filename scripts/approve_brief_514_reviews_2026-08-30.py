"""Apply the operator's image and claim-review approvals for brief 514."""
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.graphics.storage import approve_image, get_approved_image

DB = ROOT / "data" / "atmina.db"
IMAGE_ID = 294
EXPECTED_IMAGE = "images/briefs/2026-08-29-dienas-parskats-5813e550.png"
REASONINGS = {704209: 'Izvērtēts 2026-08-30: Paša tvīts (2026-08-27, LV diena 08-27; dienas apskats). Pēc tikšanās ar Korejas Republikas Nacionālās asamblejas vicespīkeru premjers norāda, ka Dienvidkorejas uzņēmums plāno investīcijas metāna ražotnē un SMR tehnoloģijās un Latvijai ir vērts būt aktīvai jau no paša sākuma — pirmās personas vērtējums par konkrētu enerģētikas investīciju piesaistes jomu. Tēma Degviela un enerģētika — kodols ir enerģētikas investīcijas (metāns, SMR). Pārējās tvīta daļas ir jau glabātu nostāju atkārtojums: CSDD bezmaksas numurzīmju nomaiņa un cietušo informēšana (glabāta 2026-08-26), airBaltic valsts kā aizdevēja/obligacionāra loma un «nav automātiski 30 miljoni» (glabāta 2026-08-17..08-21), kriptoaktīvu centra mērķis ar MiCA (glabāta 2026-08-19) — tāpēc šeit ekstraktēta tikai Korejas enerģētikas investīciju nostāja.', 704246: 'Izvērtēts 2026-08-30: Retorisks jautājums ar iestrādātu atbildi (pēc 2026-08-10 precedenta, doc 84898) — pārmetums Jaunajai Vienotībai par mītiņa ar 10 000 cilvēku un mediju iesaistes rīkošanu, kuras mērķis ir grozīt Saeimas lēmumu atcelt Stambulas konvenciju; to raksturo kā iejaukšanos demokrātiskos procesos un politisku vardarbību, kam būtu jāpievēršas Valsts drošības dienestam. SK identificēta kā Stambulas konvencija pēc 2026-08-26/27 korpusa konteksta (denonsēšanas debates). Jautājuma forma, nevis tiešs apgalvojums — konfidence 0.55.', 704251: 'Izvērtēts 2026-08-30: RT @partijaMMN ar pašatribūcijas formu („Jānis Hermanis par latviešu zaudētajiem mūža gadiem“) — RT ķēde nosauc pašu politiķi kā citēto vārdu avotu, tātad pirmās personas pozīcija (689246 klase: conf 0.6, quote=None). Tēma: zaudēto mūža gadu rādītājs + veselības aprūpes sistēmas pārskatīšana → Veselības aprūpe (robežprecedents 689296/689498; paša 703940 veselīgā mūža ilguma klase). Aicinājuma verbu stiprums saglabāts no avota („aicina pārskatīt“). Sal 0.5.'}

db = sqlite3.connect(DB)
db.row_factory = sqlite3.Row
for cid, new_reasoning in REASONINGS.items():
    row = db.execute("SELECT reasoning, review_status FROM claims WHERE id=?", (cid,)).fetchone()
    assert row is not None and row["review_status"] == "needs_review", (cid, dict(row) if row else None)
    assert row["reasoning"].startswith("NEEDS_REVIEW: "), cid
    db.execute("UPDATE claims SET reasoning=? WHERE id=?", (new_reasoning, cid))
db.commit()
approve_image(db, IMAGE_ID)

for cid in REASONINGS:
    row = db.execute("SELECT reasoning, review_status FROM claims WHERE id=?", (cid,)).fetchone()
    assert row["review_status"] == "reviewed", (cid, dict(row))
    assert row["reasoning"].startswith("Izvērtēts 2026-08-30: "), cid
assert get_approved_image(db, 514) == EXPECTED_IMAGE
image = db.execute("SELECT approved, error_message FROM brief_images WHERE id=?", (IMAGE_ID,)).fetchone()
assert tuple(image) == (1, None), tuple(image)
db.close()
print("OK: approved image 294 and resolved claims 704209, 704246, 704251")
