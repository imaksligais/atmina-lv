"""Rutīnas 2026-11-08 orķestratora labojumi pēc ekstrakcijas.

1. Dzēš 3 Delfi dublikātus (753386, 753388, 753389) — tas pats TV3 «Nekā personīga»
   sižets jau glabāts no pmo.ee (753393, 753394, 753395, tēma «Tieslietas»); Delfi
   rindām nederīga tēma «Saeimas darbs» (temas.md: tikai balsojumiem).
2. Tēmas «Saeimas darbs» → derīgas (kolīziju vaicājums: 0 katrai):
   753344, 753349 → «Koalīcija un partijas»; 753350 → «Valsts pārvalde».
3. Stance labojumi: 753355 (laiks «melo»), 753357 («LSM un tās»), 753347
   (meta-komentārs ārā), 753385 (neitrāls darbības vārds).
4. 13 dienas NEEDS_REVIEW → «Izvērtēts 2026-11-08: …» (solis 2c).

    .venv/Scripts/python.exe scripts/fix_routine_cleanup_2026-11-08.py          # dry-run + rollback
    .venv/Scripts/python.exe scripts/fix_routine_cleanup_2026-11-08.py --apply

Rollback: data/rollback_routine_cleanup_2026-11-08.sql; pēc tam re-embed
753344 753347 753349 753350 753355 753357 753385 753386 753388 753389.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from src.db import get_db  # noqa: E402

ROLLBACK = ROOT / "data/rollback_routine_cleanup_2026-11-08.sql"
DAY = "2026-11-08"

DELETE = [753386, 753388, 753389]
TOPIC = {753344: "Koalīcija un partijas", 753349: "Koalīcija un partijas",
         753350: "Valsts pārvalde"}
STANCE = {
    753355: "Apgalvo, ka «VISI» eksperti norāda, ka Kulbergs melojot un izlokoties.",
    753347: ("Saka, ka viņu šokē datu trūkums, un vaicā, vai tiešām neviens nevar aprēķināt, "
             "kas ko maksās, ja lēmums tiktu pieņemts, un vai Latvijas Banka ar saviem "
             "analītiķiem var uzmodelēt finansiālās sekas."),
    753385: ("Raksta, ka jāremontē sliedes, bet ES tiesa lai pāris gadus vērtē, vai remonts ir "
             "samērīgs, un pauž cerību, ka pēc pāris gadiem karš jau būs beidzies."),
}
STANCE_REPLACE = {753357: ("ļaus LSM ziņu redaktorei Braunai", "ļaus LSM un tās ziņu redaktorei Braunai")}
REVIEW = {
    753338: "stance nepārsniedz tvīta tekstu; protests nav nosaukts ne tekstā, ne stance, skaitļi un jautājums atstāti kā autora apgalvojumi",
    753340: "stance atkārto vienīgo teikumu ar «apgalvo»; kurš sarkanās līnijas dzēsis, stance nemin, tāpat kā teksts",
    753341: "visi apgalvojumi ir paša tvītā un ietīti ar «apgalvo» un «ko raksturo kā»; asums nav iemesls atmest (operatora lēmums 2026-10-06)",
    753346: "stance seko citātam bez papildinājumiem; lēmums nav nosaukts ne tekstā, ne stance",
    753347: "stance atstāj jautājumus jautājuma formā; paša vērtējums ir «mani šokē datu trūkums»; meta-komentārs izņemts no stance",
    753355: "stance atstāsta teikumu ar divkāršu atrunu un pēdiņām «VISI»; tās pašas dienas 753354 arī kritizē Kulbergu, tāpēc iespējamā ironija par «elspertiem» nostāju neapgriež; laiks izlabots uz «melojot»",
    753356: "stance atstāsta tikai tvītā teikto (apstiprināšanas datums, neatceras kritiku), latgaliskais citāts burtisks",
    753358: "vērtējums par BMW un VW ir pilns paša teksts, stance to nepaplašina",
    753362: "stance atstāsta vienīgo teikumu ar «apgalvo»; pagātnes rīcību Šleseram piedēvē pats autors",
    753363: "paša pirmās personas vērtējums «Es uzskatu»; persona un protests stance nav nosaukti, tāpat kā tekstā",
    753364: "stance nosauc ironiju («ironizē») un pretstatījumu, ko tvīts pats veido; apgalvojums nav pārvērsts faktā",
    753382: "jautājuma forma stance saglabāta («jautājuma formā pauž»)",
    753385: "ironija («Nu, ļoti labi.») nav izslēdzama, tāpēc stance pārrakstīts ar neitrālu «Raksta» bez «ierosina»; saturs ir paša teksts",
}
MARK = "NEEDS_REVIEW:"


def lit(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return repr(v)
    return "'" + str(v).replace("'", "''") + "'"


def main(apply: bool) -> None:
    db = get_db(None)
    import sqlite_vec
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)

    cols = [r[1] for r in db.execute("PRAGMA table_info(claims)")
            if r[1] not in ("review_status", "review_status_at")]
    touched = sorted(set(DELETE) | set(TOPIC) | set(STANCE) | set(STANCE_REPLACE) | set(REVIEW))
    rows = {r["id"]: r for r in db.execute(
        f"SELECT * FROM claims WHERE id IN ({','.join('?' * len(touched))})", touched)}
    missing = [i for i in touched if i not in rows]
    if missing:
        sys.exit(f"STOP: nav claims {missing}")
    refs = db.execute(
        f"SELECT id FROM contradictions WHERE claim_old_id IN ({','.join('?'*len(DELETE))}) "
        f"OR claim_new_id IN ({','.join('?'*len(DELETE))})", DELETE + DELETE).fetchall()
    if refs:
        sys.exit(f"STOP: dzēšamos claims atsaucas pretrunas {[r[0] for r in refs]}")
    for cid, topic in TOPIC.items():
        r = rows[cid]
        hit = db.execute("SELECT id FROM claims WHERE opponent_id=? AND source_url=? AND topic=?",
                         (r["opponent_id"], r["source_url"], topic)).fetchall()
        if hit:
            sys.exit(f"STOP: tēmas kolīzija {cid} → {topic}: {[h[0] for h in hit]}")
    for cid in REVIEW:
        if not (rows[cid]["reasoning"] or "").startswith(MARK):
            sys.exit(f"STOP: {cid} reasoning nesākas ar marķieri")
    for cid, (old, _new) in STANCE_REPLACE.items():
        if rows[cid]["stance"].count(old) != 1:
            sys.exit(f"STOP: {cid} stance neatrod '{old}'")

    lines = [
        "-- Rollback: scripts/fix_routine_cleanup_2026-11-08.py (apply 2026-11-08).",
        "-- Forward: DELETE 753386/753388/753389 (Delfi dublikāti); tēmas 753344/753349/753350;",
        "-- stance 753347/753355/753357/753385; 13 NEEDS_REVIEW → Izvērtēts.",
        "-- Pēc tam: .venv/Scripts/python.exe scripts/reembed_claims.py "
        "753344 753347 753349 753350 753355 753357 753385 753386 753388 753389",
        "BEGIN;",
    ]
    for cid in DELETE:
        r = rows[cid]
        lines.append(f"INSERT INTO claims ({', '.join(cols)}) VALUES "
                     f"({', '.join(lit(r[c]) for c in cols)});")
    for cid in sorted(set(TOPIC) | set(STANCE) | set(STANCE_REPLACE) | set(REVIEW)):
        r = rows[cid]
        lines.append(f"UPDATE claims SET topic={lit(r['topic'])}, stance={lit(r['stance'])}, "
                     f"reasoning={lit(r['reasoning'])} WHERE id={cid};")
    lines.append("COMMIT;")
    ROLLBACK.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"rollback uzrakstīts: {ROLLBACK.relative_to(ROOT)}")

    new_reason = {}
    for cid, ev in REVIEW.items():
        orig = rows[cid]["reasoning"][len(MARK):].strip()
        text = f"Izvērtēts {DAY}: {ev}. Sākotnēji: {orig}"
        if "NEEDS_REVIEW" in text:
            sys.exit(f"STOP: {cid} jaunajā reasoning paliek marķiera vārds")
        new_reason[cid] = text
    print(f"dzēst {len(DELETE)}, tēmas {len(TOPIC)}, stance {len(STANCE) + len(STANCE_REPLACE)}, "
          f"izvērtēt {len(REVIEW)}")
    if not apply:
        return

    before = db.execute("SELECT COUNT(*) FROM claims WHERE review_status='needs_review' "
                        "AND id>=753337").fetchone()[0]
    with db:
        for cid in DELETE:
            db.execute("DELETE FROM claim_vectors WHERE claim_id=?", (cid,))
            db.execute("DELETE FROM claims WHERE id=?", (cid,))
        for cid, topic in TOPIC.items():
            db.execute("UPDATE claims SET topic=? WHERE id=?", (topic, cid))
        for cid, stance in STANCE.items():
            db.execute("UPDATE claims SET stance=? WHERE id=?", (stance, cid))
        for cid, (old, new) in STANCE_REPLACE.items():
            db.execute("UPDATE claims SET stance=? WHERE id=?",
                       (rows[cid]["stance"].replace(old, new), cid))
        for cid, text in new_reason.items():
            db.execute("UPDATE claims SET reasoning=? WHERE id=?", (text, cid))
    after = db.execute("SELECT COUNT(*) FROM claims WHERE review_status='needs_review' "
                       "AND id>=753337").fetchone()[0]
    left = db.execute(f"SELECT COUNT(*) FROM claims WHERE id IN ({','.join('?'*len(DELETE))})",
                      DELETE).fetchone()[0]
    print(f"needs_review dienā: {before} → {after}; dzēstie palikuši: {left}")


if __name__ == "__main__":
    main("--apply" in sys.argv)
