"""Operatora lēmumi 2026-11-04 pēc c065 triāžas (`docs/audits/2026-11-04-c065-triaza/parbaude.md`).

Pretruna #17 atsaukta, #123 marķēta; #11210 un #548302 dzēstas; 18 stance
pārrakstīti; 5 rindām marķieris noņemts; balsojumam 8644 Saeimas etiķete.

    --write-rollback   uzraksta data/rollback_c065_followups_2026-11-04.sql
    --apply            izpilda vienā transakcijā; bez iecommitota rollback atsaka

Pēc --apply: scripts/reembed_claims.py ar izdrukātajiem id.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import sqlite_vec

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from src.db import get_db, withdraw_contradiction  # noqa: E402
from src.lv_style import lint_lv_style  # noqa: E402
from src.quality import validate_lv_diacritics  # noqa: E402

ROLLBACK = ROOT / "data" / "rollback_c065_followups_2026-11-04.sql"
TAG = " (c065 triāža 2026-11-04). "
DAY = "2026-11-04"

NOTE_17 = (
    "Atsaukts 2026-11-04. Saglabātajā avotā nav Evikas Siliņas pašas izteikuma par sadarbību "
    "pēc vēlēšanām: tur žurnālists secina par trim partijām. Kopsavilkumā pēdiņās lietotie vārdi "
    "«piekāpšanu» un «negarantē» avotos nav atrasti, un 30. marts ir raksta ielādes, ne izteikuma datums."
)
SIGN_123 = "redzamajā avota tekstā nav Siliņas izteikuma, raksts aiz maksas sienas"
DELETE = {11210: (None, 23039), 548302: (None, 53312)}

# id: (jaunais stance, jaunā confidence)
STANCE = {
    7474: ("Komisijas sēdē norāda, ka ZZS frakcijas grozījumos Ceļu satiksmes likumā, kas trešo valstu pilsoņiem pēc pusgada uzturēšanās prasa Latvijā izsniegtu transportlīdzekļa vadītāja apliecību, plānots izņēmums traktortehnikai, jo prasība varētu ietekmēt darbaspēka pieejamību lauksaimniecības nozarēs.", 0.65),
    20390: ("Pauž, ka NA jaunajā valdībā būtu gatava strādāt arī tad, ja tās izveidi uzticētu citam politiskajam spēkam, ja vien tiek īstenoti valstij svarīgi uzdevumi.", 0.65),
    520874: ("Uzskata, ka dronu laikmetā pretdronu spējas nevarēs palikt tikai armijas kompetencē — būs jāiesaista arī policija un ugunsdzēsēji; visa valsts vairāk vai mazāk kļūst par frontes līniju, un robeža starp civilo un militāro aizsardzību izzūd.", 0.65),
    527901: ("Rosinājis pastiprināt drošības prasības Imigrācijas likumā: uzturēšanās atļauju varēs atteikt, ja ārzemnieks atzīts par vainīgu noziedzīga nodarījuma izdarīšanā Latvijā vai ārvalstīs, par ko Latvijas likumos paredzēts kriminālsods; paredzēti arī izņēmumi, piemēram, ja sodāmība ir dzēsta vai noņemta.", 0.65),
    531967: ("Uzskata, ka latviešu valodu zina pietiekamā līmenī un ka «viss būs kārtībā»; no Saeimas tribīnes un komisiju sēdēs nerunā latviski, jo viņam nepatīkot to darīt; ja Saeima viņu nosūtīs uz valsts valodas pārbaudi, darīs visu, lai to nokārtotu.", 0.65),
    548397: ("Kā Rīgas mēra kandidāts uz jautājumu par rīcību neierobežotu finanšu iespēju gadījumā atbild, ka būtu jābūvē jaunas viesnīcas, jāattīsta biznesa vide un jāatdzīvina Brīvības iela, nevis jābūvē jauni pieminekļi, jo tie esot dārgi.", 0.65),
    11079: ("Uzskata, ka par IT sistēmu funkcionalitātes nodrošināšanu atbild Vides aizsardzības un reģionālās attīstības ministrijas paspārnē esošā Valsts digitālās attīstības aģentūra un pats ministrs; ja jau pusgadu pirms vēlēšanām no viņiem ir atrunas, tas kļūst par nacionālās drošības jautājumu.", 0.65),
    20817: ("Vērtē, ka līdz šim apspriestie ASV rīcības scenāriji pret Irānu, visticamāk, ir mainījušies — speciālo spēku reids kodolinfrastruktūras sagrābšanai izskatās arvien mazāk ticams, jo urāns varētu atrasties dziļi pazemē zem kalna, tāpēc arvien ticamāki kļūst divi citi scenāriji, kas varētu tikt īstenoti kombinēti: masīvs militārs trieciens un ierobežota sauszemes operācija Hormuza šauruma atbrīvošanai. Iznākums lielā mērā būtu atkarīgs no pretošanās kustības aktivizēšanas Irānā (Afganistānas analoģija); ja tas neizdotos, situācija kļūtu sarežģītāka un riskantāka, un viņš šaubās, vai amerikāņi būtu gatavi ilgstošai operācijai.", 0.65),
    527826: ("Uzskata, ka četri mēneši ir pārāk īss laiks pašvaldību finanšu izlīdzināšanas jautājuma risināšanai; nodokļu «Pandoras lādes» atvēršana četros mēnešos nav prātīga, tāpēc šajā laikā jāmeklē iespējas esošajā regulējumā.", 0.65),
    704352: ("Uzskata, ka kompensācijas pirmām kārtām būs nepieciešamas par zaudējumiem pašvaldību īpašumiem un dienestu papildu izmaksām, bet valsts nevarēs kompensēt pilnīgi visus privātpersonu zaudējumus — lauksaimniekiem būtiska nozīme būs apdrošināšanai.", 0.65),
    532016: ("Būs Saeimas Vidzemes deputātu grupas vadītājs; uzsver, ka grupai Saeimā jāaktualizē Vidzemes cilvēku vajadzības un ka svarīgi mazināt plaisu starp iedzīvotājiem un lēmumu pieņēmējiem.", 0.65),
    548282: ("Kā reģionālās attīstības ministrs pieprasīs Ogres novada pašvaldībai rakstisku skaidrojumu par Valsts kontroles revīzijā konstatētajiem pārkāpumiem (vismaz 434 000 eiro neatbilstoša izlietošana, krāpšanas risku pazīmes iepirkumos).", 0.6),
    11244: ("Uzsver, atsaucoties uz Latvijas un sabiedroto izlūkdienestu vērtējumu, ka Krievija šobrīd nav spējīga īstenot militāru uzbrukumu NATO valstīm, tostarp Baltijas reģionam — visas tās militārās spējas ir pavērstas pret Ukrainu.", 0.65),
    553947: ("Iebilst pret likumprojekta par Krievijas un Baltkrievijas izcelsmes preču importa aizliegumu tūlītēju pieņemšanu otrajā, galīgajā lasījumā, tāpēc tiek noteikts 15 minūšu priekšlikumu iesniegšanas termiņš.", 0.65),
    709264: ("Komentējot ziņas par jaunu ceļotāju grupu Nepālā, norāda, ka Satversme paredz Latvijas pilsoņiem tiesības izbraukt no valsts un neviens to nevar aizliegt; aicina aizbraukušos vismaz reģistrēties konsulārajā reģistrā.", 0.65),
    7196: ("Kijivā tiekoties ar Zelenski, pārrunā Latvijas ieguldījumu programmā PURL, kuras ietvaros sabiedrotie pērk ASV raķetes un citu militāro aprīkojumu Ukrainas vajadzībām.", 0.6),
    7336: ("Norāda, ka degvielas tirgotāju solidaritātes maksājuma likumprojekts, ņemot vērā Saeimas sesijas pārtraukumu, nodots otrajā saskaņošanas aplī, lai nevalstiskās organizācijas līdz 10. aprīlim varētu iesniegt iebildumus.", 0.6),
    7494: ("Kritizē «Progresīvo» politiku Rīgā: tā vairāk balstoties uz ideoloģiskiem uzsvariem un simboliskiem pilsētvides projektiem, piemēram, veloceliņiem, nevis uz ekonomikas attīstību.", 0.65),
}
KEEP_OK = (689604, 615823, 689223, 532505, 532513)  # stance atbilst, c → 0,65
STILL_REVIEW = {548282: "avots ir ministra padomniece, ne pats ministrs"}


def sql(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return repr(v)
    return "'" + str(v).replace("'", "''") + "'"


def strip_marker(reasoning: str) -> tuple[str, str]:
    """(pazīme, atlikušais pamatojums) no `NEEDS_REVIEW: <pazīme> (c065 …). <vecais>`."""
    assert reasoning.startswith("NEEDS_REVIEW: ") and TAG in reasoning, reasoning[:120]
    head, rest = reasoning.split(TAG, 1)
    return head[len("NEEDS_REVIEW: "):], rest


def new_reasoning(cid: int, old: str) -> str:
    if cid == 532016:  # jau izvērtēta rinda bez marķiera
        return f"{old} Izvērtēts {DAY}: stance precizēts pret avotu («vadītājs būs»)."
    sign, rest = strip_marker(old)
    if cid in STILL_REVIEW:
        return f"NEEDS_REVIEW: {STILL_REVIEW[cid]}{TAG}{rest}".rstrip()
    if cid in KEEP_OK:
        return f"Izvērtēts {DAY}: stance atbilst avotam. {rest}".rstrip()
    return f"Izvērtēts {DAY}: stance pārrakstīts pret avotu ({sign}). {rest}".rstrip()


def gates() -> None:
    bad = []
    for cid, (stance, _) in STANCE.items():
        ok, why = validate_lv_diacritics(stance)
        if not ok:
            bad.append((cid, why))
        hits = lint_lv_style(stance)
        if hits:
            bad.append((cid, hits))
    ok, why = validate_lv_diacritics(NOTE_17)
    if not ok:
        bad.append(("note17", why))
    if bad:
        raise SystemExit(f"LV vārti: {bad}")
    print(f"LV vārti: {len(STANCE)} stance + piezīme, 0 atrādījumu")


def write_rollback() -> None:
    db = get_db()
    cols = [c[1] for c in db.execute("PRAGMA table_info(claims)")
            if c[1] not in ("review_status", "review_status_at")]
    lines = [
        "-- Rollback: scripts/fix_c065_followups_2026-11-04.py (apply 2026-11-04).",
        "-- Pretruna #17 atjaunota, #123, stance, confidence un 8644 atgriezti, #11210 un #548302 ievietotas.",
        "-- Pēc tam: scripts/reembed_claims.py " + " ".join(map(str, [*STANCE, *DELETE])),
        "BEGIN;",
        "UPDATE contradictions SET confirmed = 1, withdrawn_at = NULL, withdrawn_note = NULL WHERE id = 17;",
    ]
    for cid in (123, *STANCE, *KEEP_OK):
        r = db.execute("SELECT stance, confidence, reasoning FROM claims WHERE id=?", (cid,)).fetchone()
        lines.append(f"UPDATE claims SET stance = {sql(r[0])}, confidence = {r[1]!r}, reasoning = {sql(r[2])} WHERE id = {cid};")
    for cid in DELETE:
        r = db.execute(f"SELECT {', '.join(cols)} FROM claims WHERE id=?", (cid,)).fetchone()
        assert r is not None, cid
        lines.append(f"INSERT INTO claims ({', '.join(cols)}) VALUES ({', '.join(sql(v) for v in r)});")
    v = db.execute("SELECT result, result_source FROM saeima_votes WHERE id=8644").fetchone()
    lines.append(f"UPDATE saeima_votes SET result = {sql(v[0])}, result_source = {sql(v[1])} WHERE id = 8644;")
    lines += ["COMMIT;", ""]
    ROLLBACK.write_text("\n".join(lines), encoding="utf-8")
    print("rollback:", ROLLBACK.name, len(lines), "rindas")


def apply() -> None:
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", str(ROLLBACK)], cwd=ROOT, capture_output=True).returncode == 0
    dirty = subprocess.run(["git", "status", "--short", str(ROLLBACK)], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if not tracked or dirty:
        raise SystemExit("rollback nav iecommitots")
    db = get_db()
    db.enable_load_extension(True)
    sqlite_vec.load(db)  # DELETE no claim_vectors (vec0)
    nr_before = db.execute("SELECT COUNT(*) FROM claims WHERE review_status='needs_review'").fetchone()[0]
    with db:
        withdraw_contradiction(17, NOTE_17, db=db)
        old = db.execute("SELECT reasoning FROM claims WHERE id=123").fetchone()[0]
        n = db.execute("UPDATE claims SET confidence=0.6, reasoning=? WHERE id=123 AND confidence=0.65",
                       (f"NEEDS_REVIEW: {SIGN_123}{TAG}{old}",)).rowcount
        assert n == 1
        for cid, (stance, conf) in STANCE.items():
            old = db.execute("SELECT reasoning FROM claims WHERE id=?", (cid,)).fetchone()[0]
            n = db.execute("UPDATE claims SET stance=?, confidence=?, reasoning=? WHERE id=?",
                           (stance, conf, new_reasoning(cid, old), cid)).rowcount
            assert n == 1, cid
        for cid in KEEP_OK:
            old = db.execute("SELECT reasoning FROM claims WHERE id=?", (cid,)).fetchone()[0]
            n = db.execute("UPDATE claims SET confidence=0.65, reasoning=? WHERE id=?",
                           (new_reasoning(cid, old), cid)).rowcount
            assert n == 1, cid
        for cid in DELETE:
            db.execute("DELETE FROM claim_vectors WHERE claim_id=?", (cid,))
            assert db.execute("DELETE FROM claims WHERE id=?", (cid,)).rowcount == 1, cid
        n = db.execute("UPDATE saeima_votes SET result='Paziņojums', result_source='agenda_label' "
                       "WHERE id=8644 AND result='Pieņemts' AND result_source='computed'").rowcount
        assert n == 1
    q = db.execute
    print("pretruna 17:", q("SELECT confirmed FROM contradictions WHERE id=17").fetchone()[0])
    print("needs_review:", nr_before, "→", q("SELECT COUNT(*) FROM claims WHERE review_status='needs_review'").fetchone()[0])
    print("reembed:", " ".join(map(str, STANCE)))


if __name__ == "__main__":
    gates()
    if "--write-rollback" in sys.argv:
        write_rollback()
    elif "--apply" in sys.argv:
        apply()
