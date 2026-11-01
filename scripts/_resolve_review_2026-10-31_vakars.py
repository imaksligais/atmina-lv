"""Rutīnas 2026-10-31 (vakars) solis 2c + Kola stance precizējumi.

  --write-rollback  raksta data/rollback_needs_review_2026-10-31_vakars.sql
                    un data/rollback_stance_kols_2026-10-31.sql ar SĀKOTNĒJĀM vērtībām
  --apply           izpilda forward (atsaka, ja rollback faili nav commitēti)

Pēc --apply: scripts/reembed_claims.py 752755 752756 (stance mainīts).
Atstātas operatoram (marķieris paliek): 752761 (nosaukta žurnāliste, apgalvojums
bez avota), 752771 (identificējama autore, faktu apgalvojumi, quote=None),
752773 (nevar noteikt atzinība vai skepse).
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from src.db import get_db  # noqa: E402

DAY = "2026-10-31"
RB_REVIEW = Path("data/rollback_needs_review_2026-10-31_vakars.sql")
RB_STANCE = Path("data/rollback_stance_kols_2026-10-31.sql")

# id -> pierādījums (paša teksts; stance saglabā atrunu / jautājuma formu)
EVIDENCE = {
    752760: "paša tvīts @akirstei; noslēguma apgalvojums «Visi klusē kā ūdeni mutē ieņēmuši!» ir burtisks, jautājumi stance atstāti kā jautājumi, apzīmējums ietīts «ko viņš raksturo kā»",
    752762: "paša tvīts; stance burtiski atkārto «Krieviem kaut kas nelāgs padomā, gatavo provokāciju», atruna «iespējams» saglabāta",
    752763: "paša tvīts pirmajā personā («Kāpēc es saku, ka …»); stance ir apgalvojums ar burtisku citātu un vārdu «arī»",
    752764: "paša tvīts; jautājuma forma saglabāta, asais apzīmējums ietīts atribūcijā, frakcijas stance nav nosauktas",
    752765: "paša tvīts; vērtējums par Krievijas ražošanas mērogu burtisks, jautājums par Eiropu atstāts kā jautājums",
    752766: "paša tvīts @zuravlevs; apgalvojums burtisks, «globālisti» ietīts «ko viņš dēvē par»",
    752767: "paša tvīts; nosacījums «ja tā turpināsies» saglabāts, apzīmējums ietīts atribūcijā",
    752768: "paša tvīts; «Federācijā nacionālas valstis nevar pastāvēt» burtisks, «bez brūnajiem» pēdiņās kā paša vārdi",
    752769: "paša tvīts; «nav tāda centrisma, tā ir kreisa pozīcija» burtisks; tēma ir piespiedu izvēle, ne kļūda",
    752770: "paša tvīts; «Tusks ir globālists, nekas neliecina …» burtisks, epistēmiskā atruna saglabāta",
    752772: "paša atbilde @instant_mk; «Ļoti trendīgi vainot visur progresīvos» burtisks, ironija stance nosaukta",
    752774: "paša tvīts; «ēnu ekonomika aug augumā tieši dēļ nejēdzīgiem lēmumiem» burtisks, stance pati norāda, ka lēmumi nav nosaukti",
    752776: "paša atbilde @AndrisKulbergs; «Tā mēs savu valodu pazaudēsim» burtisks, jautājums atstāts kā jautājums",
    752781: "paša tvīts; stance apraksta ironiju kā ironiju un nepiešķir viņam liberāļu nostāju, valsts nav nosaukta arī stance",
    752785: "paša tvīts; stance saglabā retorisko jautājumu formu, apgalvojums tikai par ministriju pārziņu",
    752789: "TV24 tvīts 147815 citē Ķirša paša vārdus raidījumā «Preses klubs», viņš to retvīto; runātājs ir viņš pats, atruna «iespējams» saglabāta",
    752790: "tiešs Petravičas citāts no Saeimas 29.10. debatēm la.lv rakstā («viņa vaicāja»); stance saglabā jautājuma formu",
}

STANCE = {
    752755: "Uzskata, ka ES ir tiesiski un politiski instrumenti, lai nepieļautu Krievijas komandu atgriešanos starptautiskajā hokejā, ka to izmantošana ir politiskās gribas jautājums un trūkstošie instrumenti jāizveido; uzskata arī, ka Kremlis katru atgūto privilēģiju izmantos kā kārtējo pierādījumu, ka pasaule, īpaši Rietumi, sākusi samierināties ar Krievijas agresijas karu.",
    752756: "Uzskata, ka Tuska valdībai jāsniedz Polijas sabiedrībai un sabiedrotajiem savas rīcības tiesiskais pamatojums, salīdzinot ar iedomātu situāciju, kurā Latvijas valdība mēģinātu atstādināt Satversmes tiesas priekšsēdētāju; uzskata, ka divdomīgi tvīti un lekcijas par «tiesiskuma atjaunošanu» šoreiz īsti nav pietiekams skaidrojums.",
}

MARK = "NEEDS_REVIEW:"


def q(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def new_reasoning(old: str, ev: str) -> str:
    assert old.startswith(MARK), old[:40]
    rest = old[len(MARK):].strip().replace("NEEDS_REVIEW", "marķieris")
    return f"Izvērtēts {DAY}: {ev}. Sākotnēji: {rest}"


def committed(p: Path) -> bool:
    r = subprocess.run(["git", "ls-files", "--error-unmatch", str(p)], capture_output=True)
    if r.returncode != 0:
        return False
    d = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", str(p)])
    return d.returncode == 0


def main() -> int:
    db = get_db()
    if "--write-rollback" in sys.argv:
        lines = [f"-- Forward: {DAY} vakars (rutīnas solis 2c): {len(EVIDENCE)} pozīcijām NEEDS_REVIEW → Izvērtēts.",
                 "-- Ids: " + ", ".join(map(str, EVIDENCE)), "-- Rollback atjauno sākotnējo reasoning.", "BEGIN;"]
        for cid in EVIDENCE:
            old = db.execute("SELECT reasoning FROM claims WHERE id=?", (cid,)).fetchone()[0]
            assert old.startswith(MARK), cid
            lines.append(f"UPDATE claims SET reasoning = {q(old)} WHERE id = {cid};")
        lines.append("COMMIT;")
        RB_REVIEW.write_text("\n".join(lines) + "\n", encoding="utf-8")
        lines = [f"-- Forward: {DAY} Kola stance precizējumi (752756 «Pieprasa»→«Uzskata, ka … jāsniedz»; 752755 bez avotā neesoša «jo»).",
                 "-- Rollback atjauno sākotnējo stance; pēc tam palaid scripts/reembed_claims.py 752755 752756.", "BEGIN;"]
        for cid in STANCE:
            old = db.execute("SELECT stance FROM claims WHERE id=?", (cid,)).fetchone()[0]
            lines.append(f"UPDATE claims SET stance = {q(old)} WHERE id = {cid};")
        lines.append("COMMIT;")
        RB_STANCE.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"rakstīts {RB_REVIEW}, {RB_STANCE}")
        return 0
    if "--apply" in sys.argv:
        for p in (RB_REVIEW, RB_STANCE):
            if not committed(p):
                print(f"ATSAKA: {p} nav commitēts")
                return 1
        with db:
            for cid, ev in EVIDENCE.items():
                old = db.execute("SELECT reasoning FROM claims WHERE id=?", (cid,)).fetchone()[0]
                db.execute("UPDATE claims SET reasoning=? WHERE id=?", (new_reasoning(old, ev), cid))
            for cid, st in STANCE.items():
                db.execute("UPDATE claims SET stance=? WHERE id=?", (st, cid))
        ids = list(EVIDENCE)
        rows = db.execute(f"SELECT id, review_status FROM claims WHERE id IN ({','.join('?'*len(ids))})", ids).fetchall()
        still = [r[0] for r in rows if r[1] == "needs_review"]
        print(f"izvērtēti {len(ids) - len(still)} no {len(ids)}; joprojām needs_review: {still}")
        return 1 if still else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
