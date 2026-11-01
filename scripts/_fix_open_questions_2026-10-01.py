"""Operatora verdikti 2026-10-01 § Atvērtie jautājumi 1–5 un 9 (`docs/verdikti-2026-10-01.md`).

Operatora atbilde 2026-10-01 vakarā: «ok, yes, save them for the next session» — 1–5 un 9 izpildīt.

1 (C3) — 15 tvītu stubi: atsaukt (neviens rīks nevar atjaunot vecāktvītu/saiti).
2 (C8) — #7040 atsaukt (#6657 dublikāts, tas pats doks 13008); #6650 atsaukt (līdzjūtības tvīts,
    nav pozīcija); #7391 atjaunot avota formulējumu ar atrunām + citāts = burtiska doka 15405
    apakšvirkne; #7420 ironijas formulējums, adresāts nav nosakāms (vecāktvīts nav pieejams).
3 — #19 Šuvajevs: stance sašaurināta uz pavediena 1. daļu (doks 2635), citāts no tās.
4 — 15 ne-politiķa citāti (C5 klase, `docs/audits/2026-09-30-stance-izlase/` grades*.json «quote flag»):
    `quote = NULL`; #11081 apgriezts līdz Čakšas burtiskajam teikumam dokā 20923.
5 — neskaidrie dublikātu pāri: paturēt abus — datu izmaiņu nav.
9 — Vēstneša «tikai uzvārda» `subject` slānis (`docs/audits/2026-10-01-vestnesis-saites-izlase.md`):
    54 junction rindas dzēst (nav par politiķi), 7 nepārbaudāmās → `suspect_at` (T19), 57293/6 paliek.

Avota dokumenti paliek (CLAUDE.md § Deleting a claim). Rollback tiek uzrakstīts PIRMS izmaiņām:
data/rollback_open_questions_2026-10-01.sql. Pēc --apply: scripts/reembed_claims.py 7391 7420 19.

    .venv/Scripts/python.exe scripts/_fix_open_questions_2026-10-01.py           # dry-run
    .venv/Scripts/python.exe scripts/_fix_open_questions_2026-10-01.py --apply
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import get_db, now_lv  # noqa: E402

ROLLBACK = ROOT / "data/rollback_open_questions_2026-10-01.sql"
TODAY = "2026-10-01"

WITHDRAW = {
    "1": (6794, 6640, 6938, 11068, 1556, 7419, 11184, 11094, 6629, 7446, 6803, 6836, 7329, 7442, 11243),
    "2": (7040, 6650),
}
# id: (document_id, jaunā stance, jaunais citāts | None = NULL, jaunais reasoning)
REWRITE = {
    7391: (15405,
           "Apgalvo, ka Jaunā Vienotība un Orbāns esot radījuši «identisku valsts korupcijas tīklojumu», "
           "kurā 15 gadu garumā savējie un pietuvinātie gūstot labumu no valsts pasūtījumiem; apgalvojums "
           "nav neatkarīgi pārbaudīts.",
           "jaunā vienotība un Orbāns ir radījuši identisku valsts korupcijas tīklojumu, kur abos gadījumos "
           "15 gadu garumā savējie un pietuvinātie caur valsts pasūtījumiem noslauc valsts “govi” un "
           "rezultāts ir vispārējs railbaltiks.",
           f"Izvērtēts {TODAY}: atjaunots avota formulējums «identisku valsts korupcijas tīklojumu» ar "
           "atrunu (iepriekšējā stance to mīkstināja līdz «līdzīgam pārvaldes modelim»); citāts aizstāts ar "
           "burtisku tvīta tekstu. Tvīts ir atbilde kontam @GeneralisAi; Hermaņa paša vārdi."),
    7420: (15977,
           "Ironizē par citētu frāzi «Sargā ekonomisko potenciālu ilgtermiņā…», atbildot, ka adresāts "
           "neatpazītu attīstību, pat ja tā viņam «klēpī apsēstos»; kam replika adresēta, nav zināms, jo "
           "sākotnējais ieraksts nav pieejams.",
           "Piedodiet, bet Jūs neatpazītu attīstību, pat ja tā Jums klēpī apsēstos",
           f"Izvērtēts {TODAY}: iepriekšējā stance («kritizē valdības ekonomiskās attīstības politiku») "
           "pieņēma adresātu, ko tvīts nenosauc; vecāktvīts nav pieejams, tāpēc stance apraksta tikai "
           "ironisko repliku. Zema ticamība — konteksts nav zināms."),
    19: (2635,
         "Uzskata, ka enerģijas cenas veicinās inflāciju un bremzēs izaugsmi, tāpēc valdībai jāizvirza "
         "divi mērķi: saglabāt iedzīvotāju pirktspēju un palielināt investīcijas enerģētiskajā neatkarībā.",
         "valdībai jāformulē divi mērķi: saglabāt iedzīvotāju pirktspēju; palielināt investīcijas "
         "energo-neatkarībā",
         f"Izvērtēts {TODAY}: stance sašaurināta uz pavediena 1. daļu (šis dokuments); 3./4. daļa "
         "(doki 2637/2638 — «taupīt» kā kļūda, kopīgi gāzes iepirkumi, tirgus uzraudzība) ir atsevišķi "
         "tvīti, kuros šis claim nav balstīts."),
}
QUOTE_NULL = (11062, 11311, 6943, 11356, 14537, 14504, 11079, 14445, 7396, 11096, 11186, 7412,
              11029, 520874)
QUOTE_TRIM = {11081: (20923, "Šis lēmums ir būtisks gan mūsu drošības stiprināšanai, gan kā skaidrs "
                             "signāls mūsu sabiedrotajiem NATO par Latvijas apņēmību ilgtermiņā ieguldīt "
                             "aizsardzībā.")}

_VEST = ("28188/83 28197/141 28205/83 32028/57 33173/64 33175/92 33722/83 33727/189 33730/83 34347/182 "
         "35137/18 35144/107 35624/83 37542/203 37547/203 37553/102 41950/18 43762/55 43763/55 45479/144 "
         "47286/220 49246/226 52229/144 52262/144 52905/80 57275/150 57293/6 57300/229 57309/92 59039/123 "
         "61465/141 64605/55 65189/51 65193/226 65803/218 66426/55 66432/234 66437/234 66445/220 67909/107 "
         "68647/205 69298/107 71307/2 71315/220 74341/144 74346/107 74349/64 79696/64 79994/234 81468/226 "
         "82511/25 85127/107 90243/226 90975/107 91724/189 91725/64 98645/221 99454/109 104572/109 "
         "105247/226 105248/226 118943/109")
VEST_ALL = [tuple(map(int, p.split("/"))) for p in _VEST.split()]
VEST_SUSPECT = {(28188, 83), (28205, 83), (32028, 57), (33722, 83), (33730, 83), (34347, 182), (35624, 83)}
VEST_KEEP = {(57293, 6)}
VEST_DELETE = [p for p in VEST_ALL if p not in VEST_SUSPECT | VEST_KEEP]


def lit(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return repr(v)
    return "'" + str(v).replace("'", "''") + "'"


def rollback_pairs() -> set[tuple[int, int]]:
    """(doc, pid) pāri, kas parādās citos data/rollback_*.sql (A2 krustpārbaude)."""
    out: set[tuple[int, int]] = set()
    for f in (ROOT / "data").glob("rollback_*.sql"):
        if f == ROLLBACK:
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        if "document_politicians" not in text:
            continue
        out |= {(int(a), int(b)) for a, b in re.findall(r"\((\d+)\s*,\s*(\d+)\s*[,)]", text)}
    return out


def main(apply: bool) -> None:
    db = get_db(None)
    import sqlite_vec
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)

    stop = []
    cols = [r[1] for r in db.execute("PRAGMA table_info(claims)")]
    wd = tuple(i for ids in WITHDRAW.values() for i in ids)
    touched = wd + tuple(REWRITE) + QUOTE_NULL + tuple(QUOTE_TRIM)
    ph = ",".join("?" * len(wd))
    pht = ",".join("?" * len(touched))
    rows = db.execute(f"SELECT {','.join(cols)} FROM claims WHERE id IN ({ph})", wd).fetchall()
    refs = db.execute(
        f"SELECT count(*) FROM contradictions WHERE claim_old_id IN ({pht}) OR claim_new_id IN ({pht})",
        touched + touched,
    ).fetchone()[0]
    print(f"1+2 atsaukt: atrastas {len(rows)}/{len(wd)}; pretrunu atsauces {refs} (pārbaudīti {len(touched)} id)")
    if len(rows) != len(wd) or refs:
        stop.append("trūkst atsaucamo rindu vai ir pretrunu atsauces")

    old = {}
    for cid, (doc, _st, quote, _rs) in REWRITE.items():
        r = db.execute("SELECT document_id, stance, quote, reasoning, claim_type FROM claims WHERE id=?",
                       (cid,)).fetchone()
        content = db.execute("SELECT content FROM documents WHERE id=?", (doc,)).fetchone()[0]
        ok = r is not None and r["document_id"] == doc and r["claim_type"] == "position" and quote in content
        print(f"2/3 pārrakstīt #{cid}: doks {doc}, citāts burtisks {quote in content}")
        if not ok:
            stop.append(f"#{cid} nav gaidītajā stāvoklī vai citāts nav burtisks")
        old[cid] = r
    for cid in QUOTE_NULL + tuple(QUOTE_TRIM):
        r = db.execute("SELECT document_id, quote FROM claims WHERE id=?", (cid,)).fetchone()
        old[cid] = r
        if r is None or r["quote"] is None:
            stop.append(f"#{cid} trūkst vai citāts jau NULL")
    for cid, (doc, quote) in QUOTE_TRIM.items():
        content = db.execute("SELECT content FROM documents WHERE id=?", (doc,)).fetchone()[0]
        if old[cid]["document_id"] != doc or quote not in content:
            stop.append(f"#{cid} apgrieztais citāts nav burtisks dokā {doc}")
    print(f"4 citāti: NULL {len(QUOTE_NULL)}, apgriezti {len(QUOTE_TRIM)}")

    vest_rows = {}
    for d, p in VEST_ALL:
        rr = db.execute(
            "SELECT d.role, d.created_at, d.extracted_at, d.suspect_at, doc.platform FROM document_politicians d "
            "JOIN documents doc ON doc.id = d.document_id WHERE d.document_id=? AND d.politician_id=?", (d, p),
        ).fetchall()
        ncl = db.execute("SELECT count(*) FROM claims WHERE document_id=? AND (opponent_id=? OR speaker_id=?)",
                         (d, p, p)).fetchone()[0]
        if len(rr) != 1 or rr[0]["role"] != "subject" or rr[0]["platform"] != "vestnesis" \
                or rr[0]["suspect_at"] is not None or ncl:
            stop.append(f"Vēstnesis {d}/{p} nav gaidītajā stāvoklī")
        else:
            vest_rows[(d, p)] = rr[0]
    rb = rollback_pairs() & set(VEST_ALL)
    print(f"9 Vēstnesis: {len(VEST_ALL)} pāri (dzēst {len(VEST_DELETE)}, suspect_at {len(VEST_SUSPECT)}, "
          f"paturēt {len(VEST_KEEP)}); gaidītajā stāvoklī {len(vest_rows)}/{len(VEST_ALL)}; "
          f"sakritības ar citiem rollback failiem {len(rb)} {sorted(rb)}")
    if rb:
        stop.append("Vēstneša pāri sakrīt ar rollback-atjaunotiem pāriem")
    if len(VEST_DELETE) != 54 or len(VEST_SUSPECT) != 7:
        stop.append("Vēstneša saraksta skaits != 54/7")
    if stop:
        sys.exit("STOP: " + "; ".join(stop))
    if not apply:
        print("(dry-run — nekas nav rakstīts; --apply lai rakstītu)")
        return

    ins_cols = [c for c in cols if c not in ("review_status", "review_status_at")]
    lines = ["-- Rollback: scripts/_fix_open_questions_2026-10-01.py (apply 2026-10-01).",
             f"-- Forward: atsauktas {len(wd)} claims (1: {WITHDRAW['1']}; 2: {WITHDRAW['2']}); stance/citāts "
             f"pārrakstīts #7391 #7420 #19; quote NULL {len(QUOTE_NULL)} + apgriezts #11081; Vēstnesis: "
             f"{len(VEST_DELETE)} subject junction dzēsti, {len(VEST_SUSPECT)} suspect_at.",
             "-- Pēc rollback: .venv/Scripts/python.exe scripts/reembed_claims.py "
             + " ".join(map(str, wd + tuple(REWRITE))),
             "BEGIN;"]
    for r in rows:
        dd = dict(zip(cols, r))
        lines.append(f"INSERT INTO claims ({', '.join(ins_cols)}) VALUES "
                     f"({', '.join(lit(dd[c]) for c in ins_cols)});")
    for cid in REWRITE:
        o = old[cid]
        lines.append(f"UPDATE claims SET stance = {lit(o['stance'])}, quote = {lit(o['quote'])}, "
                     f"reasoning = {lit(o['reasoning'])} WHERE id = {cid};")
    for cid in QUOTE_NULL + tuple(QUOTE_TRIM):
        lines.append(f"UPDATE claims SET quote = {lit(old[cid]['quote'])} WHERE id = {cid};")
    for d, p in VEST_DELETE:
        v = vest_rows[(d, p)]
        lines.append("INSERT INTO document_politicians (document_id, politician_id, role, created_at, "
                     f"extracted_at) VALUES ({d}, {p}, 'subject', {lit(v['created_at'])}, {lit(v['extracted_at'])});")
    for d, p in sorted(VEST_SUSPECT):
        lines.append(f"UPDATE document_politicians SET suspect_at = NULL WHERE document_id = {d} "
                     f"AND politician_id = {p} AND role = 'subject';")
    lines.append("COMMIT;")
    ROLLBACK.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"rollback uzrakstīts PIRMS izmaiņām: {ROLLBACK.relative_to(ROOT)}")

    stamp = now_lv()
    with db:
        db.execute(f"DELETE FROM claim_vectors WHERE claim_id IN ({ph})", wd)
        db.execute(f"DELETE FROM claims WHERE id IN ({ph})", wd)
        for cid, (_doc, st, quote, rs) in REWRITE.items():
            db.execute("UPDATE claims SET stance=?, quote=?, reasoning=? WHERE id=?", (st, quote, rs, cid))
        qn = ",".join("?" * len(QUOTE_NULL))
        db.execute(f"UPDATE claims SET quote=NULL WHERE id IN ({qn})", QUOTE_NULL)
        for cid, (_doc, quote) in QUOTE_TRIM.items():
            db.execute("UPDATE claims SET quote=? WHERE id=?", (quote, cid))
        for d, p in VEST_DELETE:
            db.execute("DELETE FROM document_politicians WHERE document_id=? AND politician_id=? AND role='subject'",
                       (d, p))
        for d, p in VEST_SUSPECT:
            db.execute("UPDATE document_politicians SET suspect_at=? WHERE document_id=? AND politician_id=? "
                       "AND role='subject'", (stamp, d, p))

    # saglabāts == iecerēts
    res = {}
    for cls, ids in WITHDRAW.items():
        p = ",".join("?" * len(ids))
        res[f"{cls} atsaukti"] = (len(ids) - db.execute(f"SELECT count(*) FROM claims WHERE id IN ({p})",
                                                        ids).fetchone()[0], len(ids))
    res["2/3 pārrakstīti"] = (sum(
        1 for cid, (_d, st, q, _r) in REWRITE.items()
        if tuple(db.execute("SELECT stance, quote, review_status FROM claims WHERE id=?", (cid,)).fetchone())
        == (st, q, "reviewed")), len(REWRITE))
    res["4 quote NULL"] = (db.execute(f"SELECT count(*) FROM claims WHERE quote IS NULL AND id IN ({qn})",
                                      QUOTE_NULL).fetchone()[0], len(QUOTE_NULL))
    res["4 apgriezti"] = (sum(1 for cid, (_d, q) in QUOTE_TRIM.items()
                              if db.execute("SELECT quote FROM claims WHERE id=?", (cid,)).fetchone()[0] == q),
                          len(QUOTE_TRIM))
    res["9 dzēsti"] = (sum(1 for d, p in VEST_DELETE if not db.execute(
        "SELECT 1 FROM document_politicians WHERE document_id=? AND politician_id=?", (d, p)).fetchone()),
        len(VEST_DELETE))
    res["9 suspect_at"] = (sum(1 for d, p in VEST_SUSPECT if db.execute(
        "SELECT suspect_at FROM document_politicians WHERE document_id=? AND politician_id=?",
        (d, p)).fetchone()[0]), len(VEST_SUSPECT))
    res["9 paturēts"] = (sum(1 for d, p in VEST_KEEP if db.execute(
        "SELECT 1 FROM document_politicians WHERE document_id=? AND politician_id=? AND role='subject' "
        "AND suspect_at IS NULL", (d, p)).fetchone()), len(VEST_KEEP))
    for k, (got, want) in res.items():
        print(f"{k}: {got}/{want}")
    print("tagad: .venv/Scripts/python.exe scripts/reembed_claims.py " + " ".join(map(str, REWRITE)))
    if any(got != want for got, want in res.values()):
        sys.exit("STOP: saglabāts != iecerēts")


if __name__ == "__main__":
    main("--apply" in sys.argv)
