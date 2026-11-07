"""Vienreizējs labojums 2026-09-29 pēc @quality-reviewer FAIL (3 citātu kļūdas + 2 ievadi).

Labo: konteksta piezīmes #657–#659 (tās pašas rutīnas dienas, nepublicētas — CLAUDE.md inv 8
otrais izņēmums), claims 725047/725070/725074 `stance` (pēc tam re-embed), pārskats #660
(DB + wiki/dailies). Pirms rakstīšanas raksta data/rollback_quality_2026-09-29.sql ar vecajām
vērtībām. Katrai aizvietošanai jāatrod precīzi gaidītais trāpījumu skaits, citādi STOP.
"""
import sys
from pathlib import Path
from src.db import get_db

CLAIMS = {
    725074: [("ja ministriju funkcijas netiks «ravētas», ietaupījuma nebūs",
              "ja ministriju funkcijas netiks ravētas, ietaupījuma nebūs")],
    725047: [("ne tikai no «Vienotības», bet", "ne tikai no Vienotības (ierakstā — «V»), bet")],
    725070: [("TV24 raidījumā «Ziņu TOP», atbildot uz jautājumu, vai tēva pilsonība un darbība Krievijā ietekmējusi viņas politiskos uzskatus, uz jautājumu tieši neatbild, bet pauž",
              "TV24 raidījumā «Ziņu TOP» uz jautājumu, vai tēva pilsonība un darbība Krievijā ietekmējusi viņas politiskos uzskatus, tieši neatbild, bet pauž")],
}
NOTES = {
    657: [("kāpēc tranzīts nav aizliegts; opozīcija valdības lēmumus sauc par neefektīviem.",
           "kāpēc tranzīts nav aizliegts; X ierakstā valdības lēmumus kritizē arī opozīcijas deputāts Šuvajevs."),
          ("; tās tiesības ir infrastruktūras maksa", "; tā drīkst piemērot infrastruktūras maksu"),
          ("Andris Šuvajevs (Progresīvie) —", "Andris Šuvajevs (PRO) —")],
    658: [("«kaut kam jāatņem»", "«kaut kam ir jāatņem»")],
    659: [("pauž solidaritāti ar Igauniju un aicina nemazināt atbalstu Ukrainai.",
           "pauž solidaritāti ar Igauniju; Rinkēvičs un Braže uzsver, ka atbalsts Ukrainai jāturpina.")],
}
BRIEF_EXTRA = [
    ("ZZS frakcijas vadītājs Rokpelnis ZZS priekšlikuma samazināt degvielas PVN izskatīšanas atlikšanu Budžeta komisijā raksturo kā vājas plānošanas rezultātu. Kulberga ieraksts par akcīzes samazinājumu ir no viņa 24. septembra dienasgrāmatas, bet Dombrovskis (JV) runā par REPowerEU nozīmi ES energodrošībā.",
     "ZZS frakcijas vadītājs Rokpelnis vāju plānošanu saskata tajā, ka Budžeta komisija kvoruma trūkuma dēļ atlika ZZS priekšlikumu samazināt degvielas PVN. Kulberga ieraksts par akcīzes samazinājumu ir no viņa 24. septembra dienasgrāmatas; Dombrovskis (JV) runā par REPowerEU nozīmi ES energodrošībā."),
    ("Koalīcijas iekšējās atšķirības dienā redzamas graudu tranzītā (Vitenbergs norāda, ka partneri NA prasību neatbalstīja), imigrācijā (Dombrava — partneri vīzu jautājumu nebija gatavi iekļaut 29. septembra valdības sēdē) un degvielas PVN (Rokpelnis par neizskatīto ZZS priekšlikumu).",
     "Koalīcijas iekšējās atšķirības dienā redzamas trijās tēmās. Graudu tranzītā Vitenbergs norāda, ka partneri NA prasību neatbalstīja; imigrācijā Dombrava saka, ka partneri vīzu jautājumu nebija gatavi iekļaut 29. septembra valdības sēdē; degvielas PVN jomā Rokpelnis runā par neizskatīto ZZS priekšlikumu."),
]
BRIEF_ID = 660
WIKI = Path("wiki/dailies/2026-09-29.md")
ROLLBACK = Path("data/rollback_quality_2026-09-29.sql")


def q(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def sub(text, pairs, label, expect_min=1):
    for old, new in pairs:
        n = text.count(old)
        if n < expect_min:
            sys.exit(f"STOP: {label}: nav atrasts {old[:60]!r} (trāpījumi {n})")
        text = text.replace(old, new)
    return text


def main(apply: bool):
    db = get_db(None)
    claims = {i: db.execute("SELECT stance FROM claims WHERE id=?", (i,)).fetchone()[0] for i in CLAIMS}
    notes = {i: db.execute("SELECT content FROM context_notes WHERE id=?", (i,)).fetchone()[0] for i in list(NOTES) + [BRIEF_ID]}
    assert WIKI.read_text(encoding="utf-8") == notes[BRIEF_ID], "wiki/dailies != DB — STOP"

    new_claims = {i: sub(claims[i], CLAIMS[i], f"claim {i}") for i in CLAIMS}
    new_notes = {i: sub(notes[i], NOTES[i], f"note {i}") for i in NOTES}
    brief = notes[BRIEF_ID]
    for i in CLAIMS:
        brief = sub(brief, CLAIMS[i], f"brief/claim {i}")
    for i in NOTES:
        brief = sub(brief, NOTES[i], f"brief/note {i}")
    brief = sub(brief, BRIEF_EXTRA, "brief/extra")
    for old, _ in [p for ps in list(CLAIMS.values()) + list(NOTES.values()) for p in ps] + BRIEF_EXTRA:
        assert old not in brief, f"atlikums pārskatā: {old[:50]!r}"

    if not apply:
        print("dry-run OK:", len(new_claims), "claims,", len(new_notes), "notes, brief", len(notes[BRIEF_ID]), "->", len(brief))
        return

    lines = ["-- Rollback: scripts/_fix_quality_2026_09_29.py (apply 2026-09-29).",
             "-- Atjauno claims 725047/725070/725074 stance, context_notes 657/658/659/660 content.",
             "-- Pēc rollback: scripts/reembed_claims.py 725047 725070 725074; wiki/dailies/2026-09-29.md no 660.",
             "BEGIN;"]
    lines += [f"UPDATE claims SET stance = {q(claims[i])} WHERE id = {i};" for i in CLAIMS]
    lines += [f"UPDATE context_notes SET content = {q(notes[i])} WHERE id = {i};" for i in notes]
    lines.append("COMMIT;")
    ROLLBACK.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with db:
        for i, s in new_claims.items():
            db.execute("UPDATE claims SET stance=? WHERE id=?", (s, i))
        for i, s in new_notes.items():
            db.execute("UPDATE context_notes SET content=? WHERE id=?", (s, i))
        db.execute("UPDATE context_notes SET content=? WHERE id=?", (brief, BRIEF_ID))
    WIKI.write_text(brief, encoding="utf-8")
    print("applied; rollback ->", ROLLBACK)


if __name__ == "__main__":
    main("--apply" in sys.argv)
