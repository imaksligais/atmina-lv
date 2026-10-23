"""Operatora verdikti 2026-10-01 C1 + C5 (`docs/verdikti-2026-10-01.md`): `claims.quote` labojumi.

C1 — citāts no cita dokumenta (`docs/audits/2026-09-30-citatu-triaza.md` § OPERATOR, 14 rindas):
3 jau pārsaistītas 09-30 (#14346, #7489, #18375), 2 atsauktas 09-30 (#7044, #6899 —
`data/rollback_stance_grades_2026-09-30.sql`), 9 dzīvas. Pārsaista (`document_id` + `source_url` +
`stated_at` = mērķa `published_at`) tikai tad, ja mērķis atbalsta pozīciju, politiķis tajā ir `subject`,
nav idempotences sadursmes `(opponent_id, source_url, topic)` un citāts ir burtiska mērķa apakšvirkne.
Citādi `quote = NULL`, claim paliek savā dokumentā.

C5 — citāts nav politiķa vārdi (`docs/audits/2026-09-30-stance-izlase/` aprīļa `vout*.json` +
`verify_out*.json` lv_notes, 41 rinda): 11 atsauktas 09-30, #1538 ārpus klases (citāts ir viņas pašas
tvīta pirmā rinda), 29 → `quote = NULL`. Stance šīm rindām verificēts 09-30 (`support` burtiski);
skripts pārbauda, ka stance kopš tā nav mainījies.

`claims.quote` ir VERBATIM: jauns citāts ir tikai burtiska avota apakšvirkne, nekad pārrakstīšana.
Re-embed nav vajadzīgs: `store_claim()` iegulst `topic: stance`, tie nemainās.
Rollback tiek uzrakstīts PIRMS UPDATE: `data/rollback_quotes_c1c5_2026-10-01.sql`.

    .venv/Scripts/python.exe scripts/_fix_quotes_c1c5_2026-10-01.py           # dry-run
    .venv/Scripts/python.exe scripts/_fix_quotes_c1c5_2026-10-01.py --apply
"""
import json
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db import get_db  # noqa: E402

ROLLBACK = ROOT / "data/rollback_quotes_c1c5_2026-10-01.sql"
STANCE_AUDIT = ROOT / "docs/audits/2026-09-30-stance-izlase"

# C1: claim -> pašreizējais document_id (citāts tajā nav; pozīciju dokuments atbalsta).
C1_NULL = {19: 2635, 18095: 32765, 18295: 34062}
# C1: claim -> (pašreizējais document_id, mērķa document_id, jaunais citāts | None = esošais ir burtisks mērķī).
C1_REPOINT = {
    548524: (71421, 71406, None),
    548058: (65843, 65819, None),
    11143: (22131, 22132, None),
    689539: (85857, 86486,
             'Šodien bija vētraina Saeimas Aizsardzības komisijas sēde par "zelta vīzām" apmaiņā pret '
             'nekustamo īpašumu. \nNezinu, kāpēc prezidents gribēja, lai Saeima to atkal skata. Pēc visas tās '
             'sliktās pieredzes, kas mums te ar TUA tirgošanu Šlesera programmas ietvaros ir bijusi. \nJā, '
             'šoreiz Krievija netika piedāvāta, taču bija NVS utml. Sēdē rosināju šo priekšlikumu noraidīt, '
             'ko komisija arī izdarīja.'),
    11018: (20978, 20967,
            "Demokrātiskā valstī valsts vara ir leģitīma tikai tad, ja tā izriet no tautas gribas, kas brīvi "
            "izteikta vēlēšanās."),
    18007: (31459, 31541,
            "Tāpat esmu uzdevis veikt dienesta pārbaudi, lai izvērtētu vakardienas reaģēšanu, šūnu apraides "
            "aktivizēšanu un nepieciešamos uzlabojumus."),
}
C5_NULL = (186, 7417, 93, 115, 11240, 7460, 6964, 11313, 7473, 7464, 6623, 11034, 1594, 7187, 6645,
           11412, 7349, 464, 14381, 6686, 6716, 7336, 11055, 14414, 403, 6680, 7199, 7375, 11157)


def nfc(s):
    return unicodedata.normalize("NFC", s or "")


def lit(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return repr(v)
    return "'" + str(v).replace("'", "''") + "'"


def stated(published_at):
    # Kā 09-30 pārsaistīšanā (`_fix_stance_b_rewrite_2026_09_30.py`): published_at bez zonas pārrēķina.
    return datetime.fromisoformat(published_at).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")


def doc_text(db, doc_id):
    row = db.execute("SELECT coalesce(title,'') || char(10) || coalesce(content,'') FROM documents WHERE id=?",
                     (doc_id,)).fetchone()
    return nfc(row[0]) if row else None


def main(apply: bool) -> None:
    db = get_db(None)
    final = {}
    for f in sorted(STANCE_AUDIT.glob("aprilis/vout*.json")) + sorted(STANCE_AUDIT.glob("verify_out*.json")):
        final.update({r["id"]: r["final_stance"] for r in json.loads(f.read_text(encoding="utf-8"))})
    problems, plan = [], {}  # plan: id -> (old (doc, url, stated, quote), new (doc, url, stated, quote))

    def current(cid):
        return db.execute("SELECT opponent_id, topic, stance, quote, document_id, source_url, stated_at "
                          "FROM claims WHERE id=?", (cid,)).fetchone()

    for cid, old_doc in C1_NULL.items():
        c = current(cid)
        if c is None or c[4] != old_doc or c[3] is None or nfc(c[3]) in (doc_text(db, old_doc) or ""):
            problems.append(f"C1 #{cid}: nav, cits dokuments, citāts jau NULL vai jau burtisks savā avotā")
            continue
        plan[cid] = (tuple(c[4:7]) + (c[3],), tuple(c[4:7]) + (None,))

    for cid, (old_doc, did, new_quote) in C1_REPOINT.items():
        c = current(cid)
        if c is None or c[4] != old_doc or c[3] is None or nfc(c[3]) in (doc_text(db, old_doc) or ""):
            problems.append(f"C1 #{cid}: nav, cits dokuments, citāts jau NULL vai jau burtisks savā avotā")
            continue
        opp, topic, quote = c[0], c[1], c[3]
        url, pub = db.execute("SELECT source_url, published_at FROM documents WHERE id=?", (did,)).fetchone()
        new_quote = quote if new_quote is None else new_quote
        if nfc(new_quote) not in doc_text(db, did):
            problems.append(f"C1 #{cid}: citāts nav burtiska doc {did} apakšvirkne")
        roles = {r[0] for r in db.execute("SELECT role FROM document_politicians WHERE document_id=? "
                                          "AND politician_id=?", (did, opp))}
        if roles != {"subject"}:
            problems.append(f"C1 #{cid}: doc {did} loma {roles}, ne subject")
        if db.execute("SELECT id FROM claims WHERE opponent_id=? AND source_url=? AND topic=?",
                      (opp, url, topic)).fetchone():
            problems.append(f"C1 #{cid}: idempotences sadursme uz {url}")
        plan[cid] = (tuple(c[4:7]) + (quote,), (did, url, stated(pub), new_quote))

    for cid in C5_NULL:
        c = current(cid)
        if c is None or c[3] is None or nfc(c[2]).strip() != nfc(final.get(cid)).strip():
            problems.append(f"C5 #{cid}: nav, citāts jau NULL vai stance mainījies kopš 09-30 verifikācijas")
            continue
        plan[cid] = (tuple(c[4:7]) + (c[3],), tuple(c[4:7]) + (None,))

    done = [i for i in (7044, 6899) if db.execute("SELECT 1 FROM claims WHERE id=?", (i,)).fetchone()]
    if done:
        problems.append(f"C1: {done} nav atsaukti, kā gaidīts")
    for cid in (14346, 7489, 18375):
        q, d = db.execute("SELECT quote, document_id FROM claims WHERE id=?", (cid,)).fetchone()
        if q is not None and nfc(q) not in doc_text(db, d):
            problems.append(f"C1 #{cid}: 09-30 pārsaistīšana — citāts nav burtisks savā avotā")

    n_null = sum(new[3] is None for _, new in plan.values())
    print(f"C1 ievade 14 (3 pārsaistītas 09-30, 2 atsauktas 09-30, 9 dzīvas): NULL {len(C1_NULL)}, "
          f"pārsaistīt {len(C1_REPOINT)}; C5 ievade 41 (11 atsauktas 09-30, 1 ārpus klases): NULL {len(C5_NULL)}")
    print(f"plāns {len(plan)} rindas: quote=NULL {n_null}, pārsaistīšana {len(plan) - n_null}")
    for cid, (old, new) in plan.items():
        if old[0] != new[0]:
            print(f"  #{cid}: doc {old[0]} -> {new[0]}, stated {old[2]} -> {new[2]}, "
                  f"citāts {'paliek' if new[3] == old[3] else 'burtisks no mērķa'}")
    if problems:
        sys.exit("STOP:\n  " + "\n  ".join(problems))
    if not apply:
        return

    lines = ["-- Rollback: scripts/_fix_quotes_c1c5_2026-10-01.py (apply 2026-10-01; verdikti C1 + C5).",
             f"-- Forward: {n_null} claims.quote -> NULL, {len(plan) - n_null} pārsaistīšanas (document_id, "
             "source_url, stated_at, quote). Atjauno visas 4 kolonnas. Re-embed nav vajadzīgs.",
             "BEGIN;"]
    lines += [f"UPDATE claims SET document_id = {old[0]}, source_url = {lit(old[1])}, stated_at = {lit(old[2])}, "
              f"quote = {lit(old[3])} WHERE id = {cid};" for cid, (old, _) in plan.items()]
    lines.append("COMMIT;")
    ROLLBACK.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with db:
        for cid, (_, new) in plan.items():
            db.execute("UPDATE claims SET document_id=?, source_url=?, stated_at=?, quote=? WHERE id=?", new + (cid,))
    got = sum(
        db.execute("SELECT document_id IS ? AND source_url IS ? AND stated_at IS ? AND quote IS ? FROM claims "
                   "WHERE id=?", new + (cid,)).fetchone()[0]
        for cid, (_, new) in plan.items()
    )
    print(f"pārbaude: {got}/{len(plan)} rindas sakrīt ar plānu; rollback {ROLLBACK.relative_to(ROOT)}")
    if got != len(plan):
        sys.exit("STOP: saglabāto skaits != plānotais")


if __name__ == "__main__":
    main("--apply" in sys.argv)
