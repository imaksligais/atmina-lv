"""Rutīnas 2026-11-08 kvalitātes vārtu labojumi (@quality-reviewer, pirms publicēšanas).

Pārskats 808 (melnraksts), piezīme 807 (šīs rutīnas dienas, nedeployota — labo uz vietas,
operatora lēmums 2026-09-09), spriedzes #615–#617, pozīcijas 753339/753341/753344.
Pozīciju stance kopijas pārskatā labo tāpat.

    .venv/Scripts/python.exe scripts/fix_brief_qa_2026-11-08.py          # dry-run + rollback
    .venv/Scripts/python.exe scripts/fix_brief_qa_2026-11-08.py --apply

Rollback: data/rollback_brief_qa_2026-11-08.sql; pēc tam re-embed 753339 753341 753344.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from src.db import get_db  # noqa: E402

ROLLBACK = ROOT / "data/rollback_brief_qa_2026-11-08.sql"
DRAFT = ROOT / ".scratch/brief-2026-11-08/draft.md"
BRIEF_ID, NOTE_ID = 808, 807

NOTE_EDITS = [
    ("Smiltēna aicinājums par pusi samazināt deputātu kompensācijas raisa iebildumus no divām pusēm.",
     "Deputātu kompensāciju pārmaiņas kritizē no divām pusēm."),
    ("- Juris Pūce (LA) — ņemot vērā deputātu algas, kompensācijas būtu jāatceļ pavisam",
     "- Juris Pūce (LA) — atbildot uz Smiltēna aicinājumu kompensācijas samazināt par 50 %, uzskata, ka tās būtu jāatceļ pavisam"),
]
TENSION = {
    615: ("Kučinskis intervijā LETA saka, ka Oļegam Burovam atkal uzticētu Pašvaldību komisiju.",
          "Kučinskis intervijā LETA saka, ka komisiju var uzticēt arī opozīcijai, un kā piemēru min Oļegu Burovu, kuram atkal uzticētu Pašvaldību komisiju."),
    616: ("Smiltēns TV24 «Kārtības rullī» piedāvā Stepaņenko braukt uz Ukrainu un viņas nostāju par Ukrainu min kā būtisku iemeslu, kāpēc «Suverēnā vara» nevarētu būt Saeimas prezidijā.",
          "Smiltēns TV24 raidījumā «Kārtības rullis» (la.lv par to raksta kopš 7. novembra) piedāvāja Stepaņenko braukt uz Ukrainu un viņas nostāju par Ukrainu minēja kā būtisku iemeslu, kāpēc «Suverēnā vara» nevarētu būt Saeimas prezidijā."),
    617: ("Stepaņenko «Kārtības rullī» apšauba Smiltēna minētos «smagos, nepopulāros lēmumus» un kritizē vienādas kompensācijas visiem ārpus Rīgas deklarētajiem deputātiem.",
          "Stepaņenko TV24 raidījumā «Kārtības rullis» jautāja, kam ir smagi Smiltēna pieminētie lēmumi, un kritizēja vienādu kompensāciju visiem ārpus Rīgas deklarētajiem deputātiem."),
}
CLAIM = {
    753344: ("Budžeta un Tautsaimniecības komisiju noteikti vadīs", "Budžeta un Tautsaimniecības komisijas noteikti vadīs"),
    753341: ("ko raksturo kā «progresīvo ākstu»", "ko viņš raksturo kā «progresīvo ākstu»"),
    753339: ("pieļāva Rail Baltica projekta", "pieļāva «Rail Baltica» projekta"),
}
BRIEF_ONLY = [
    ("Ministru prezidents Andris Kulbergs (AS) partneriem jautās",
     "Ministru prezidents Andris Kulbergs (AS) potenciālajiem koalīcijas partneriem jautās"),
    ("([tvnet.lv](https://pmo.ee/8579656)); Ainārs Šlesers (LPV) apgalvo",
     "([tvnet.lv](https://pmo.ee/8579656)). Ainārs Šlesers (LPV) apgalvo"),
    ("— dienā skaidro, kā izvēlējušies savus palīgus.",
     "— TVNET skaidro, kā izvēlējušies savus palīgus."),
    ("izsakās politiķi no dažādām pusēm, bet Smiltēns un Stepaņenko strīdas par Ukrainu.",
     "izsakās politiķi no dažādām pusēm. Smiltēns un Stepaņenko strīdas par Ukrainu."),
    ("- Smiltēns TV24 raidījumā «Kārtības rullis» piedāvā noorganizēt Stepaņenko braucienu uz Ukrainu; viņa atbild, ka jāpievēršas cilvēkiem Latvijā.",
     "- TV24 raidījumā «Kārtības rullis», par kuru la.lv raksta kopš 7. novembra, Smiltēns piedāvāja noorganizēt Stepaņenko braucienu uz Ukrainu; viņa atbildēja, ka jāpievēršas cilvēkiem Latvijā."),
    ("Valkas novadā, un Mārtiņš Brencis (AS) apgalvo",
     "Valkas novadā. Mārtiņš Brencis (AS) apgalvo"),
    ("Tēmā nav kopīga pavediena. Filips Rajevskis jautā, vai kāds var aprēķināt lēmuma finansiālās sekas, Aleksandrs",
     "Filips Rajevskis jautā, vai kāds var aprēķināt kāda nenosaukta lēmuma finansiālās sekas. Aleksandrs"),
]


def lit(v):
    return "NULL" if v is None else "'" + str(v).replace("'", "''") + "'"


def once(text, old, where):
    n = text.count(old)
    if n != 1:
        sys.exit(f"STOP: {where}: '{old[:60]}…' atrasts {n}×")


def main(apply: bool) -> None:
    db = get_db(None)
    brief = db.execute("SELECT content FROM context_notes WHERE id=? AND note_type='daily_brief'",
                       (BRIEF_ID,)).fetchone()[0]
    note = db.execute("SELECT content FROM context_notes WHERE id=? AND note_type='context'",
                      (NOTE_ID,)).fetchone()[0]
    tens = {i: db.execute("SELECT description FROM political_tensions WHERE id=?", (i,)).fetchone()[0]
            for i in TENSION}
    stances = {i: db.execute("SELECT stance FROM claims WHERE id=?", (i,)).fetchone()[0] for i in CLAIM}
    if DRAFT.read_text(encoding="utf-8") != brief:
        print("piezīme: draft.md atšķiras no DB; avots ir DB")

    new_brief, new_note = brief, note
    for old, new in NOTE_EDITS:
        once(note, old, "piezīme 807")
        once(brief, old, "pārskats 808 (piezīme)")
        new_note = new_note.replace(old, new)
        new_brief = new_brief.replace(old, new)
    for i, (old, new) in TENSION.items():
        if tens[i] != old:
            sys.exit(f"STOP: spriedze #{i} teksts neatbilst")
        once(brief, old, f"pārskats 808 (#{i})")
        new_brief = new_brief.replace(old, new)
    new_stance = {}
    for i, (old, new) in CLAIM.items():
        once(stances[i], old, f"claim {i}")
        new_stance[i] = stances[i].replace(old, new)
        once(brief, stances[i], f"pārskats 808 (claim {i})")
        new_brief = new_brief.replace(stances[i], new_stance[i])
    for old, new in BRIEF_ONLY:
        once(brief, old, "pārskats 808")
        new_brief = new_brief.replace(old, new)

    ROLLBACK.write_text("\n".join([
        "-- Rollback: scripts/fix_brief_qa_2026-11-08.py (apply 2026-11-09, rutīnas diena 2026-11-08).",
        "-- Forward: pārskats 808 un piezīme 807 teksta labojumi; spriedzes #615–#617; stance 753339/753341/753344.",
        "-- Pēc tam: .venv/Scripts/python.exe scripts/reembed_claims.py 753339 753341 753344",
        "BEGIN;",
        f"UPDATE context_notes SET content={lit(brief)} WHERE id={BRIEF_ID};",
        f"UPDATE context_notes SET content={lit(note)} WHERE id={NOTE_ID};",
        *[f"UPDATE political_tensions SET description={lit(tens[i])} WHERE id={i};" for i in TENSION],
        *[f"UPDATE claims SET stance={lit(stances[i])} WHERE id={i};" for i in CLAIM],
        "COMMIT;",
    ]) + "\n", encoding="utf-8")
    print(f"rollback: {ROLLBACK.relative_to(ROOT)}; labojumi: piezīme {len(NOTE_EDITS)}, "
          f"spriedzes {len(TENSION)}, claims {len(CLAIM)}, tikai pārskatā {len(BRIEF_ONLY)}")
    if not apply:
        return
    with db:
        db.execute("UPDATE context_notes SET content=? WHERE id=?", (new_brief, BRIEF_ID))
        db.execute("UPDATE context_notes SET content=? WHERE id=?", (new_note, NOTE_ID))
        for i, (_o, new) in TENSION.items():
            db.execute("UPDATE political_tensions SET description=? WHERE id=?", (new, i))
        for i, s in new_stance.items():
            db.execute("UPDATE claims SET stance=? WHERE id=?", (s, i))
    DRAFT.write_text(new_brief, encoding="utf-8")
    print("pielietots; draft.md atjaunots")


if __name__ == "__main__":
    main("--apply" in sys.argv)
