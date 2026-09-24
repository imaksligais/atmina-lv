"""Labo publicēto dienas pārskatu #562 (2026-09-08) un #570 (2026-09-10) faktu
kļūdu: «valdība apstiprina 300 % tarifu». Avoti (tvnet 103908, LSM 103953 un
105309, Kulberga X 105417) rāda, ka 8. septembrī Ministru kabinets apstiprināja
ZM sagatavotos MK noteikumu grozījumus par graudu IZCELSMES PĀRBAUDĒM (PVD
paraugi); 300 % tarifs palika plānā, un likumprojekta grozījums uz MK gāja
15. septembrī. Atrada `@quality-reviewer` nedēļas pārskata #584 pārbaudē
2026-09-14 (nedēļas sintēze bija mantojusi kļūdu no #562 → #570).

Četras vietas #562 (ievads, konteksta kastītes virsraksts + teksts, Galvenā
tēze = lapas H1) un viena #570 (konteksta kastītes teksts). Konteksta
piezīmes #557/#569, no kurām kastītes ir KOPIJAS, NAV aiztiktas — tās ir
publicētas un no agrākas dienas, tāpēc append-only (CLAUDE.md inv. #8).
`wiki/dailies/` kopijas labo tas pats skripts. Rakstīšana caur
`store_context_note()` UPSERT (pārparsē visual_brief_json — H1/og:title seko).
Pāra rollback: data/rollback_daily_562_570_tarifs_2026-09-14.sql (pilns
oriģinālais content + visual_brief_json). Pēc apply: render
--only=blog,dashboard,static + deploy --no-delete.
"""
from __future__ import annotations


import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DB = ROOT / "data" / "atmina.db"
ROLLBACK = ROOT / "data" / "rollback_daily_562_570_tarifs_2026-09-14.sql"

EDITS = {
    562: [
        ("- **Graudu tranzīts:** valdība apstiprina 300 % tarifu; premjers Kulbergs (AS) skaidro,",
         "- **Graudu tranzīts:** valdība apstiprina graudu izcelsmes pārbaudes, 300 % tarifs paliek plānā; premjers Kulbergs (AS) skaidro,"),
        ("**Tarifs apstiprināts, strīds pāriet uz izpildes ātrumu** · 08.09.2026",
         "**Izcelsmes pārbaudes apstiprinātas, strīds pāriet uz izpildes ātrumu** · 08.09.2026"),
        ("8. septembrī valdība tarifu apstiprina, un iebildums pārceļas no mēroga uz izpildi.",
         "8. septembrī valdība apstiprina graudu izcelsmes pārbaudes, tarifs paliek plānā, un iebildums pārceļas no mēroga uz izpildi."),
        ("- **Galvenā tēze:** Valdība apstiprina 300 % tarifu Krievijas graudiem",
         "- **Galvenā tēze:** Valdība apstiprina Krievijas graudu izcelsmes pārbaudes, 300 % tarifs paliek plānā"),
    ],
    570: [
        # NB: DB tekstā rindkopas sākuma «8\.» ir markdown-eskepēts (lai nekļūtu par <ol>)
        (r"8\. septembra piezīme fiksēja, ka tarifs ir apstiprināts un strīds pārceļas uz izpildes ātrumu;",
         r"8\. septembra piezīme fiksēja, ka apstiprinātas graudu izcelsmes pārbaudes un strīds pārceļas uz izpildes ātrumu;"),
    ],
}
WIKI = {562: ROOT / "wiki/dailies/2026-09-08.md", 570: ROOT / "wiki/dailies/2026-09-10.md"}


def _q(s: str) -> str:
    return s.replace("'", "''")


def main(apply: bool) -> int:
    from src.tools import store_context_note

    c = sqlite3.connect(DB)
    rows = {}
    for nid in EDITS:
        r = c.execute("SELECT id, note_type, topic, content, source, visual_brief_json "
                      "FROM context_notes WHERE id=?", (nid,)).fetchone()
        assert r and r[1] == "daily_brief", nid
        rows[nid] = r
    c.close()

    # 1. rollback FIRST (escalation rule 8) — full pre-image of both rows
    out = ["-- ROLLBACK for: dienas pārskatu #562 (2026-09-08) un #570 (2026-09-10) «300 % tarifs apstiprināts» faktu labojums.",
           "-- Uz priekšu vērstā izmaiņa: scripts/fix_daily_562_570_tarifs_2026-09-14.py, piemērots 2026-09-14.",
           "-- Atsauc content UN visual_brief_json abām rindām (pilns pre-image). Pēc SQL: render --only=blog,dashboard,static + deploy.",
           "BEGIN;"]
    for nid, r in rows.items():
        vb = "NULL" if r[5] is None else f"'{_q(r[5])}'"
        out.append(f"UPDATE context_notes SET content='{_q(r[3])}', visual_brief_json={vb} WHERE id={nid};")
    out.append("COMMIT;")
    # Never overwrite an existing rollback: a re-run after a partial apply
    # (2026-09-14 — #562 written, #570 assertion failed on the escaped «8\.»)
    # would capture the already-fixed text as the "pre-image".
    if ROLLBACK.exists():
        print(f"rollback jau eksistē, NEpārrakstu: {ROLLBACK.name} ({ROLLBACK.stat().st_size} B)")
    else:
        ROLLBACK.write_text("\n".join(out) + "\n", encoding="utf-8")
        print(f"rollback: {ROLLBACK.name} ({ROLLBACK.stat().st_size} B)")

    # 2. edits — every old string must occur exactly once (or already be applied)
    def _apply(text: str, edits, label: str) -> str:
        for old, new in edits:
            if text.count(old) == 0 and text.count(new) == 1:
                print(f"  {label}: jau piemērots — {new[:48]}…")
                continue
            assert text.count(old) == 1, (label, text.count(old), old[:60])
            text = text.replace(old, new)
        return text

    for nid, r in rows.items():
        content = _apply(r[3], EDITS[nid], f"#{nid}")
        wiki = WIKI[nid]
        wtxt = open(wiki, encoding="utf-8").read() if wiki.exists() else None
        if wtxt is not None:
            wtxt = _apply(wtxt, EDITS[nid], wiki.name)
        print(f"#{nid}: {len(EDITS[nid])} labojumi DB tekstā; wiki kopija: {'jā' if wtxt is not None else 'nav'}")
        if apply:
            res = store_context_note(topic=r[2], note_type="daily_brief", content=content, source=r[4])
            print(f"  store_context_note → {res}")
            assert '"success"' in res, res
            if wtxt is not None:
                open(wiki, "w", encoding="utf-8", newline="\n").write(wtxt)

    if apply:
        c = sqlite3.connect(DB)
        for nid in EDITS:
            vb = c.execute("SELECT visual_brief_json FROM context_notes WHERE id=?", (nid,)).fetchone()[0]
            print(f"  #{nid} visual_brief_json: {vb[:120]}…")
        left = c.execute("SELECT id FROM context_notes WHERE id IN (562,570) AND "
                         "(content LIKE '%apstiprina 300 %%' OR content LIKE '%tarifu apstiprina%' "
                         "OR content LIKE '%tarifs ir apstiprināts%')").fetchall()
        print(f"  atlikušas vecās formas: {len(left)} (jābūt 0)")
        c.close()
    else:
        print("DRY RUN — nekas nav rakstīts (palaid ar --apply)")
    return 0


if __name__ == "__main__":
    sys.exit(main(apply="--apply" in sys.argv))
