"""@quality-reviewer 2. kārta (2026-09-23 vakars) — labojumi pirms publicēšanas.

Piezīme #637 un pārskats #639 — tā pati rutīnas diena, nav deployoti (inv. 8,
otrais izņēmums). Spriedzes #370/#371/#373/#378 apraksti (vienā rindā — tabulas
šūna). Spriedžu teksts pārskatā #639 ir verbatim, tāpēc labo arī tur.

Rollback: data/rollback_routine_2026-09-23_vakars_r2.sql
"""
from src.db import get_db

BRIEF_ONLY = [
    ("Kučinskis (AS) Budžeta komisijā iezīmē trīs scenārijus bez nodokļu celšanas, bet",
     "Kučinskis (AS) Budžeta komisijā iezīmē trīs budžeta scenārijus un iesaka variantu bez nodokļu celšanas, bet"),
    ("pārmetumus sauc par nepamatotiem un «premjera necienīgiem».",
     "pārmetumus sauc par nepamatotiem un saka, ka šāda rīcība «nav premjerministra cienīga»."),
    ("Dombrava (NA) sola trešo valstu kvotas pārskatīt reizi gadā",
     "Dombrava (NA) skaidro, ka trešo valstu kvotas plānots pārskatīt reizi gadā"),
    ("Rokpelnis (ZZS) norāda, ka izdevumu samazinājums šovasar nav rasts, savukārt Vītols (AS) atbildību liek uz desmit gadus valdījušajiem.",
     "Rokpelnis (ZZS) norāda, ka izdevumu samazinājums šovasar nav rasts. Vītols (AS) atbildību par budžeta plaisu liek uz desmit gadus valdījušajiem."),
    ("publiski strīdas par sankciju lēmumu, Valainis (ZZS) nacionālās sankcijas sauc par politisku žestu, un Patmalnieks (JV)",
     "publiski strīdas par sankciju lēmumu. Valainis (ZZS) nacionālās sankcijas sauc par politisku žestu, bet Patmalnieks (JV)"),
]
NOTE637 = [
    ("premjera pārmetumi ir nepamatoti un «premjera necienīgi»;",
     "premjera pārmetumi ir nepamatoti, un šāda rīcība «nav premjerministra cienīga»;"),
]
TENSIONS = {
    370: ("Braže X ierakstā iebilst premjera Kulberga TV3 paustajam pārmetumam Ārlietu ministrijai, ka Latvijai vajadzēja ātrāk, kā pārējām Baltijas valstīm, piekrist divu oligarhu izņemšanai no ES sankciju saraksta; to sauc par sev nepatīkamu jaunumu.",
          "Braže X ierakstā iebilst premjera Kulberga TV3 paustajiem pārmetumiem Ārlietu ministrijai; pēc viņas atstāsta, premjers uzskata, ka Latvijai tāpat kā pārējām Baltijas valstīm vajadzēja ātrāk piekrist divu oligarhu izņemšanai no ES sankciju saraksta, un to viņa sauc par sev nepatīkamu jaunumu."),
    371: ("premjers visu uzzinājis pēdējais,",
          "premjers, «kā izskatās», visu uzzinājis pēdējais,"),
    373: ("Vaidere X ierakstā pievienojas Rinkēviča ANO paustajam, ka Latvija darīs visu, lai Krievijas deportētie Ukrainas bērni atgrieztos dzimtenē.",
          "Vaidere X ierakstā piekrīt Rinkēvičam, ka ANO jāspēj nodrošināt starptautisko tiesību pamatprincipu ievērošanu un agresoru saukšanu pie atbildības."),
    378: ("Braže premjera Kulberga izteikumus par Ārlietu ministrijas rīcību ES sankciju pagarināšanas jautājumā nodēvē par premjera necienīgiem.",
          "Braže par premjera Kulberga izteikumiem par Ārlietu ministrijas rīcību ES sankciju pagarināšanas jautājumā saka, ka šāda rīcība «nav premjerministra cienīga»."),
}


def sub(text, old, new, where):
    n = text.count(old)
    assert n >= 1, (where, old)
    return text.replace(old, new)


db = get_db()
with db:
    b = db.execute("SELECT content FROM context_notes WHERE id=639").fetchone()[0]
    n = db.execute("SELECT content FROM context_notes WHERE id=637").fetchone()[0]
    for o, w in BRIEF_ONLY:
        b = sub(b, o, w, 639)
    for o, w in NOTE637:
        n = sub(n, o, w, 637)
        b = sub(b, o, w, 639)  # kastīte pārskatā = piezīme verbatim
    for tid, (o, w) in TENSIONS.items():
        d = db.execute("SELECT description FROM political_tensions WHERE id=?", (tid,)).fetchone()[0]
        d = sub(d, o, w, tid)
        assert "\n" not in d
        db.execute("UPDATE political_tensions SET description=? WHERE id=?", (d, tid))
        b = sub(b, o, w, f"639/{tid}")
    db.execute("UPDATE context_notes SET content=? WHERE id=637", (n,))
    db.execute("UPDATE context_notes SET content=? WHERE id=639", (b,))
print("ok")
