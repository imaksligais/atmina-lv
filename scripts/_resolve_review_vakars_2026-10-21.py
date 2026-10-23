"""Atrisina 14 NEEDS_REVIEW pozīcijas no 2026-10-21 vakara ekstrakcijas.
Rollback: data/rollback_review_vakars_2026-10-21.sql (komitēts pirms apply).
Operatoram atstātas: 743356 (Stendzenieks), 743360 (Velps) — konteksts neredzams.
Palaišana: --write-rollback (raksta rollback failu) vai --apply."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")
from src.db import get_db

D = "Izvērtēts 2026-10-21: "
NEW = {
    743346: "paša garš tvīts pirmajā personā, nostāja skaidra; «Digitālā politika» ir tuvākā grupa MI rīku lietojumam.",
    743351: "paša tvīts, stance atkārto avota vārdus («krievi … lielākais ienaidnieks») bez interpretācijas; izteikums patstāvīgs («vienmēr esmu teicis»), konteksts nav vajadzīgs; asums nav iemesls atmest.",
    743355: "sarkasms izlasīts pareizi — tvīts atbalsta LTV darbiniekus, kas grib saglabāt divas redakcijas, un pateicas Neimanei; stance to saka ar «ironiski», citāta nav.",
    743357: "paša atbilde @MarkJCarney; pateicība Kanādai par brigādes vadību un aicinājums «Pivot away from unreliable Musk» ir paša vārdi, stance tos atstāsta burtiski.",
    743359: "paša tvīts; stance balstās tikai uz paša vārdiem («Kreisā politika ir civilizācijas puve!») un nosauc, ka gadījums nav redzams.",
    743361: "paša tvīts; prognoze par migrantiem Spānijā ir paša vārdi, stance tos atstāsta ar pēdiņām.",
    743364: "paša tvīts ar skaidru vērtējumu «Pozitīva ziņa» par NBS atbalstu Robežsardzei; konteksts ir pašā tvītā.",
    743366: "paša tvīts, viens patstāvīgs vērtējums par valsts pārvaldi; stance to atstāsta burtiski.",
    743375: "paša tvīts, viens patstāvīgs apgalvojums par liberālo Eiropu; stance to atstāsta burtiski.",
    743381: "paša tvīts; nostāja par Stambulas konvenciju («NESTRĀDĀ») un sašutums par aizrādījumu izteikti tieši; deputāts nav nosaukts ne avotā, ne stance.",
    743386: "sarkasms izlasīts pareizi — tvīts kritizē ZZS divus viedokļus, piemērs Stambulas konvencija; stance to saka ar «ironiski», citāta nav.",
    743388: "Delfi anonss ir pilns, Līdaka nosaukts ar atsauces verbu «sacīja»/«atzina»; stance atstāsta tieši abus apgalvojumus, abonēšanas teksts ir lapas rāmis, ne nogriezums.",
    743390: "paša tvīts; «šķiet» saglabāts, raksturojums ietīts atribūcijā («ko raksturo kā»); konteksts — tās pašas dienas Višvanatas pilsonības lieta.",
    743391: "@Arlietas citē ministres runu pēdiņās ar «uzsvēra … @Braze_Baiba», ministre to izplata savā kontā — tā ir viņas pašas tiešā runa, ne trešās puses viedoklis.",
}

def q(s):
    return "NULL" if s is None else "'" + s.replace("'", "''") + "'"

db = get_db()
if "--write-rollback" in sys.argv:
    out = ["-- Forward (apply 2026-10-21): claims " + ", ".join(map(str, NEW)) + " reasoning NEEDS_REVIEW -> «Izvērtēts 2026-10-21: … Sākotnēji: …».",
           "--   Topic/stance/quote nemainās (re-embed nav vajadzīgs). Skripts: scripts/_resolve_review_vakars_2026-10-21.py", "BEGIN;"]
    for cid in NEW:
        (r,) = db.execute("SELECT reasoning FROM claims WHERE id=?", (cid,)).fetchone()
        assert r.startswith("NEEDS_REVIEW: "), cid
        out.append(f"UPDATE claims SET reasoning={q(r)} WHERE id={cid};")
    out.append("COMMIT;")
    (ROOT / "data/rollback_review_vakars_2026-10-21.sql").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("rollback rakstīts:", len(NEW))
elif "--apply" in sys.argv:
    for cid, ev in NEW.items():
        (r,) = db.execute("SELECT reasoning FROM claims WHERE id=?", (cid,)).fetchone()
        assert r.startswith("NEEDS_REVIEW: "), cid
        db.execute("UPDATE claims SET reasoning=? WHERE id=?", (D + ev + " Sākotnēji: " + r.removeprefix("NEEDS_REVIEW: "), cid))
    db.commit()
    st = [db.execute("SELECT review_status FROM claims WHERE id=?", (c,)).fetchone()[0] for c in NEW]
    print("review_status:", st)
    print("atrisināti:", sum(s != "needs_review" for s in st), "/", len(NEW))
