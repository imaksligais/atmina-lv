"""Rutīna 2026-11-07: @quality-reviewer labojumi (1.–7.) pirms publicēšanas.

  --write-rollback  uzraksta data/rollback_quality_2026-11-07.sql no pašreizējām DB vērtībām
  --apply           izpilda forward (atsaka, ja rollback nav commitēts)

Claims 753300-grupa: stance labojumi (pēc --apply: scripts/reembed_claims.py 753318 753319 753301 753307 753334 753330).
Spriedze 610 apraksts; konteksta piezīme 801 (šīs rutīnas, nekad nedeployēta — CLAUDE.md inv #8 izņēmums);
dienas pārskats 803 caur store_context_note UPSERT.
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from src.db import get_db  # noqa: E402

RB = Path("data/rollback_quality_2026-11-07.sql")

CLAIMS = {
    753318: ("Kritizē ES augstos pārstāvjus Žuzepu Borelu un Kaju Kallasu par neierašanos KĀDP/KDAP starpparlamentārajā konferencē",
             "Kritizē ES augstos pārstāvjus — agrāk Žuzepu Borelu, tagad Kaju Kallasu — par to, ka viņi neierodas KĀDP/KDAP starpparlamentārajā konferencē"),
    753319: ("klausoties Īrijas prezidentūras uzslavās savam sankciju ierakstam",
             "klausoties, kā Īrijas prezidentūra slavē savu veikumu sankciju jomā"),
    753301: ("protestam pret graudiem Latvijā, ko viņš raksturo kā «okupantu asins graudus», uzsverot",
             "protestam «pret okupantu asins graudiem Latvijā», uzsverot"),
    753307: ("nevienu no migrantiem, ko raksturo kā Spānijas vai citu valstu «ievazātus»",
             "nevienu no Spānijas vai citu valstu «ievazātajiem migrantiem»"),
    753334: ("ko viņš raksturo kā «bezmugurkaula dižgarus»", "ko viņš sauc par bezmugurkaula dižgariem"),
    753330: ("viņus «audzinās»", "viņus audzinās"),
}
TENSION = (610, "Kulberga «atklāsmēm»", "Kulberga, viņa vārdiem, atklāsmēm")
NOTE801 = ("jautā, kā Igaunijai izdevies panākt izņēmumu", "jautā, vai taisnība, ka Igaunijai izdevies panākt izņēmumu")

BRIEF = [  # (old, new, expected count)
    ("jautā, kā Igaunijai izdevies panākt izņēmumu", "jautā, vai taisnība, ka Igaunijai izdevies panākt izņēmumu", 2),
    ("lemt par aizliegumu. Kristaps", "lemt par aizliegumu ([x.com](https://x.com/pucej/status/2119164810147311687)). Kristaps", 1),
    ("ap 130 miljoniem eiro gadā; Ainārs Šlesers (LPV) brīdina",
     "ap 130 miljoniem eiro gadā ([x.com](https://x.com/Chapis/status/2119116086771646965)). Ainārs Šlesers (LPV) brīdina", 1),
    ("protestēt pie Ministru kabineta.\n",
     "protestēt pie Ministru kabineta ([x.com](https://x.com/SlesersAinars/status/2119096539725353161)).\n", 1),
    ("par vismaz 600 miljoniem eiro.", "par vismaz 600 miljoniem eiro ([x.com](https://x.com/SlesersAinars/status/2119096539725353161)).", 1),
    ("Ārpolitikas pozīcijas savstarpēji nav saistītas. ", "", 1),
    ("pret Kozlovski un Bražu vērstās spriedzes nāk arī no koalīcijas partneres NA politiķa Pūpola",
     "daļa no tām nāk no koalīcijas partneres NA politiķa Pūpola", 1),
    (CLAIMS[753318][0], CLAIMS[753318][1], 1),
    (CLAIMS[753319][0], CLAIMS[753319][1], 1),
    (CLAIMS[753301][0], CLAIMS[753301][1], 1),
    (CLAIMS[753307][0], CLAIMS[753307][1], 1),
    (CLAIMS[753334][0], CLAIMS[753334][1], 2),
    (CLAIMS[753330][0], CLAIMS[753330][1], 1),
    (TENSION[1], TENSION[2], 1),
]
STANCE_TOO = {753318, 753319, 753301, 753307, 753334, 753330}


def _sql(s):
    return "'" + s.replace("'", "''") + "'"


def write_rollback(db):
    L = ["-- Rollback: rutīna 2026-11-07, @quality-reviewer labojumi (scripts/_fix_quality_2026-11-07.py)",
         "-- Forward: claims stance 753318/753319/753301/753307/753334/753330; political_tensions 610 description;",
         "--          context_notes 801 un 803 content. Apply date: 2026-11-07.",
         "-- Pēc rollback: scripts/reembed_claims.py 753318 753319 753301 753307 753334 753330", "BEGIN;"]
    for cid, (old, _) in CLAIMS.items():
        s = db.execute("SELECT stance FROM claims WHERE id=?", (cid,)).fetchone()[0]
        assert old in s, cid
        L.append(f"UPDATE claims SET stance={_sql(s)} WHERE id={cid};")
    d = db.execute("SELECT description FROM political_tensions WHERE id=?", (TENSION[0],)).fetchone()[0]
    assert TENSION[1] in d
    L.append(f"UPDATE political_tensions SET description={_sql(d)} WHERE id={TENSION[0]};")
    for nid in (801, 803):
        c = db.execute("SELECT content FROM context_notes WHERE id=?", (nid,)).fetchone()[0]
        L.append(f"UPDATE context_notes SET content={_sql(c)} WHERE id={nid};")
    L.append("COMMIT;")
    RB.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("rakstīts", RB)


def apply(db):
    from src.tools import store_context_note
    if subprocess.run(["git", "ls-files", "--error-unmatch", str(RB)], capture_output=True).returncode \
            or subprocess.run(["git", "diff", "--quiet", "HEAD", "--", str(RB)]).returncode:
        sys.exit(f"STOP: {RB} nav commitēts")
    brief = db.execute("SELECT content, topic, source FROM context_notes WHERE id=803").fetchone()
    content = brief[0]
    for old, new, n in BRIEF:
        assert content.count(old) == n, (old[:50], content.count(old), n)
        content = content.replace(old, new)
    for cid, (old, new) in CLAIMS.items():
        cur = db.execute("UPDATE claims SET stance=replace(stance, ?, ?) WHERE id=? AND instr(stance, ?)>0", (old, new, cid, old))
        assert cur.rowcount == 1, cid
    cur = db.execute("UPDATE political_tensions SET description=replace(description, ?, ?) WHERE id=?", (TENSION[1], TENSION[2], TENSION[0]))
    assert cur.rowcount == 1
    cur = db.execute("UPDATE context_notes SET content=replace(content, ?, ?) WHERE id=801 AND instr(content, ?)>0", (NOTE801[0], NOTE801[1], NOTE801[0]))
    assert cur.rowcount == 1
    db.commit()
    print(store_context_note(topic=brief[1], note_type="daily_brief", content=content, source=brief[2]))


if __name__ == "__main__":
    db = get_db()
    if "--write-rollback" in sys.argv:
        write_rollback(db)
    elif "--apply" in sys.argv:
        apply(db)
    else:
        print(__doc__)
