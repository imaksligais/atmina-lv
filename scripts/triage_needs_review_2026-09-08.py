"""NEEDS_REVIEW triāža 2026-09-08 (2026-09-07 rutīnas dienas 12 atvērtās rindas).

Operatora lēmums 2026-09-08: 1 dzēst (#709165 sauklis bez instrumenta),
1 labot citātu un tad izvērtēt (#709151), 10 izvērtēt bez izmaiņām.

`review_status` ir DERIVĒTA kolonna — skripts raksta TIKAI `reasoning`,
trigeri klasifikāciju uztur paši (CLAUDE.md § Escalation Rules 2).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import sqlite_vec

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.db import get_db

DELETE_ID = 709165
ROLLBACK = ROOT / "data" / "rollback_triage_needs_review_709110_709180_2026-09-08.sql"
MARKER = "Izvērtēts 2026-09-08: "

# #709151 — glabātais citāts bija par AfD/Trampu, kas ar tēmu «Imigrācija»
# nesakrita. Jaunais citāts ir VERBATIM no dokumenta 103554 (pašretvīts).
NEW_QUOTE_709151 = (
    "Vajadzībai pēc darbaspēka nav nekāda sakara ar tiešu un konkrētu "
    "kaujas vecuma nelegāļu iepludināšanu, savas kultūras atvēršanu islāma "
    "okupācijai, noziegumu piesegšanu ziņās utt."
)

RESOLUTIONS = {
    709110: "Tēma «Vēlēšanas» apstiprināta — izteikuma kodols ir Vācijas vēlēšanu rezultāts un tā pārnesums uz Latvijas priekšvēlēšanu situāciju, ne imigrācija.",
    709112: "Paturēta — LSM ir pirmavots un epizode nosaukta konkrēti («airBaltic» ziņojums un tam sekojošais balsojums); pārstāsts bez citāta šeit ir pietiekams.",
    709116: "Paturēta pēc 2026-08-11 precedenta — amatpersonas paša skaidrojums ētikas jautājumā ir pozīcija, tēma «Valsts pārvalde» apstiprināta.",
    709127: "Tēma «Budžets un finanses» apstiprināta — eksportam un ārējai tirdzniecībai atsevišķas kanoniskās grupas nav, un ministra pamatojums ir ekonomiska izaugsme.",
    709128: "Paturēta — nostāja par reformas atbalstu ir droša arī bez saites satura, un formulējums pareizi palicis vispārīgs.",
    709150: "Paturēta — iebildums pret publisku finansējumu ir skaidrs; nenosauktā organizācija ir avota, ne mūsu robeža.",
    709151: "Citāts nomainīts uz imigrācijas teikumu, kas atbilst glabātajai tēmai; tēma «Imigrācija» apstiprināta. stated_at paliek pašretvīta diena, jo oriģinālizteikuma datums nav nosakāms.",
    709160: "Paturēta — instruments nosaukts konkrēti (300 % tarifs) un sakrīt ar tās pašas dienas LETA versiju, tāpēc nogrieztais Delfi avots pozīciju neapdraud.",
    709162: "Paturēta blakus #709049 — 7. septembra avots fiksē jaunu faktu, ka premjera kritizētais formulējums plānā paliek; rinda ir arī dienas Dombrava–Kulbergs spriedzes enkurs.",
    709177: "Paturēta — darbības vārds pareizi nav pastiprināts un formulējums paliek avota ciešamās kārtas robežās.",
    709180: "Paturēta — tēma «Valsts pārvalde» apstiprināta pēc izteikuma paša pamatojuma (uzticēšanās valsts institūcijām).",
}


def sql_quote(db, value):
    return db.execute("SELECT quote(?)", (value,)).fetchone()[0]


with get_db() as db:
    db.enable_load_extension(True)
    sqlite_vec.load(db)

    touched = sorted(set(RESOLUTIONS) | {DELETE_ID})
    rows = {
        r["id"]: r
        for r in db.execute(
            f"SELECT * FROM claims WHERE id IN ({','.join('?' * len(touched))})", touched
        ).fetchall()
    }
    missing = [i for i in touched if i not in rows]
    if missing:
        raise SystemExit(f"trūkst rindu pirms mutācijas: {missing}")
    if len(rows) != 12:
        raise SystemExit(f"gaidītas 12 rindas, saņemtas {len(rows)}")

    claim_cols = [
        r[1] for r in db.execute("PRAGMA table_info(claims)").fetchall()
        if r[1] not in ("review_status", "review_status_at")
    ]
    dead = rows[DELETE_ID]
    lines = [
        "-- ROLLBACK for: NEEDS_REVIEW triāža 2026-09-08 (2026-09-07 rutīnas diena).",
        "-- Atsauc: #709165 dzēšanu, #709151 citāta maiņu un 11 marķieru izvērtēšanu.",
        "-- Uz priekšu vērstās izmaiņas piemērošanas datums: 2026-09-08.",
        "-- Pēc šī SQL palaišanas: .venv/Scripts/python.exe scripts/reembed_claims.py 709165",
        "BEGIN;",
        f"INSERT INTO claims ({', '.join(claim_cols)}) VALUES "
        f"({', '.join(sql_quote(db, dead[c]) for c in claim_cols)});",
    ]
    for cid in sorted(RESOLUTIONS):
        r = rows[cid]
        lines.append(
            f"UPDATE claims SET reasoning={sql_quote(db, r['reasoning'])}, "
            f"quote={sql_quote(db, r['quote'])} WHERE id={cid};"
        )
    lines.append("COMMIT;")
    ROLLBACK.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if ROLLBACK.stat().st_size < 1000:
        raise SystemExit("rollback nav droši uzrakstīts")

    vec_before = db.execute(
        "SELECT COUNT(*) FROM claim_vectors WHERE claim_id=?", (DELETE_ID,)
    ).fetchone()[0]
    db.execute("DELETE FROM claim_vectors WHERE claim_id=?", (DELETE_ID,))
    db.execute("DELETE FROM claims WHERE id=?", (DELETE_ID,))

    for cid, decision in RESOLUTIONS.items():
        old = rows[cid]["reasoning"]
        if not old.startswith("NEEDS_REVIEW: "):
            raise SystemExit(f"#{cid}: negaidīts marķieris — {old[:60]!r}")
        new = MARKER + old[len("NEEDS_REVIEW: "):].rstrip() + " " + decision
        if cid == 709151:
            db.execute(
                "UPDATE claims SET reasoning=?, quote=? WHERE id=?",
                (new, NEW_QUOTE_709151, cid),
            )
        else:
            db.execute("UPDATE claims SET reasoning=? WHERE id=?", (new, cid))
    db.commit()

    still_open = db.execute(
        "SELECT COUNT(*) FROM claims WHERE review_status='needs_review'"
    ).fetchone()[0]
    resolved = db.execute(
        f"SELECT COUNT(*) FROM claims WHERE id IN ({','.join('?' * len(RESOLUTIONS))}) "
        "AND review_status='reviewed'",
        list(RESOLUTIONS),
    ).fetchone()[0]
    result = {
        "rollback": ROLLBACK.name,
        "rollback_bytes": ROLLBACK.stat().st_size,
        "deleted_claim_rows": 1 - db.execute(
            "SELECT COUNT(*) FROM claims WHERE id=?", (DELETE_ID,)
        ).fetchone()[0],
        "vector_rows_before": vec_before,
        "vector_rows_after": db.execute(
            "SELECT COUNT(*) FROM claim_vectors WHERE claim_id=?", (DELETE_ID,)
        ).fetchone()[0],
        "intended_resolved": len(RESOLUTIONS),
        "stored_resolved": resolved,
        "needs_review_open_after": still_open,
        "quote_709151": db.execute(
            "SELECT quote FROM claims WHERE id=709151"
        ).fetchone()[0],
    }

print(json.dumps(result, ensure_ascii=False, indent=2))
raise SystemExit(0 if result["stored_resolved"] == result["intended_resolved"] else 1)
