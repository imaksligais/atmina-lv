"""QR 1. kārtas labojumi 2026-09-15 vakara rutīnā (pirms deploy, nepublicēts).

Bloķējošais B1: piezīme #594 «trijos likumos» → «divos likumos un vēlēšanu debatēs»
(trešais elements ir ASL kampaņas kartīte, ne likums). Ieteicamie: #593 «pat frakcijā»
→ «arī koalīcijas iekšienē»; spriedze #307 «atbild» → «raksta» (Šlesera tvīts
Jurēvicu nenosauc); #710947 stance atgūst divus avota kvalifikatorus; pārskats #595
(un `wiki/dailies/2026-09-15.md`) — tie paši teksti + valodas/lasāmības labojumi.

Inv. 8 otrais izņēmums (tās pašas rutīnas nepublicēta piezīme) — labo in-place.
Rollback: data/rollback_qr_round1_2026-09-15.sql (pilns pre-image, rakstīts PIRMS
piemērošanas). Pēc apply: `.venv/Scripts/python.exe scripts/reembed_claims.py 710947`;
pēc rollback — tas pats.

Lietojums (no repo saknes): .venv/Scripts/python.exe scripts/fix_qr_round1_2026-09-15.py [--apply]
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.briefs import daily_brief_topic  # noqa: E402
from src.db import get_db  # noqa: E402
from src.lv_style import lint_lv_style  # noqa: E402
from src.tools import store_context_note  # noqa: E402

ROLLBACK = Path("data/rollback_qr_round1_2026-09-15.sql")
WIKI = Path("wiki/dailies/2026-09-15.md")

NOTE_594_REPS = [
    ("Tendence (2026-09-15, valodas prasība vienā dienā trijos likumos):",
     "Tendence (2026-09-15, valodas prasība vienā dienā divos likumos un vēlēšanu debatēs):"),
    ("un debatēs atgriežas krievu skolu jautājums.",
     "un ASL kampaņas kartītē no TV24 debatēm atgriežas krievu skolu jautājums."),
    ("\nValodas jautājums iet no skolām uz medijiem un patēriņu.", ""),
]
NOTE_593_REPS = [
    ("un priekšlikumi atšķiras pat frakcijā.", "un priekšlikumi atšķiras arī koalīcijas iekšienē."),
]
TENSION_307_REPS = [
    ("Šlesers (LPV) nākamajā dienā atbild, ka", "Šlesers (LPV) nākamajā dienā raksta, ka"),
]
CLAIM_710947_REPS = [
    ("uzskata, ka ar spēcīgu zinātnisku pamatojumu jābūt iespējai mainīt aizsargājamo teritoriju robežas, un ka politisks lēmums, kas atšķiras no zinātniskā vērtējuma, jānosauc par politisku.",
     "uzskata, ka ar spēcīgu zinātnisku pamatojumu jābūt iespējai mainīt aizsargājamo teritoriju robežas (kas nenozīmē to vieglu atcelšanu), un ka politisks lēmums, kas atšķiras no zinātniskā vērtējuma, jānosauc par politisku, uzņemoties atbildību par sekām."),
]
BRIEF_REPS = [
    ("**Valodas prasība vienā dienā trijos likumos**", "**Valodas prasība vienā dienā divos likumos un vēlēšanu debatēs**"),
    ("un debatēs atgriežas krievu skolu jautājums.", "un ASL kampaņas kartītē no TV24 debatēm atgriežas krievu skolu jautājums."),
    ("\nValodas jautājums iet no skolām uz medijiem un patēriņu.\n", "\n"),
    ("un priekšlikumi atšķiras pat frakcijā.", "un priekšlikumi atšķiras arī koalīcijas iekšienē."),
    ("nākamajā dienā atbild, ka", "nākamajā dienā raksta, ka"),  # ×2: Galvenais + spriedžu tabula
    ("Ārpus kompensāciju debates", "Ārpus kompensāciju debatēm"),
    ("un prognozē tai zem 5 % 3. oktobrī.", "un prognozē, ka 3. oktobrī tā paliks zem 5 %."),
    ("- **Degvielas nodokļi:**", "- **Degviela un gāzes apgāde:**"),
    ("*Koalīcija dienā šķiras pa jautājumiem, ne pa partiju līnijām:", "*Koalīcija dienā šķiras pa jautājumiem:"),
    ("Eiropas Parlamentā uzskaita 189 Krievijas uzbrukumus", "Eiropas Parlamentā min 189 Krievijas uzbrukumus"),
    # Lasāmība: Aizsardzība (69 vārdu teikums → trīs) un Veselība (48 → trīs)
    ("pievienojas paziņojumam par ES iesaistes stiprināšanu Arktikā; Ašeradens (JV)",
     "pievienojas paziņojumam par ES iesaistes stiprināšanu Arktikā. Ašeradens (JV)"),
    ("gaida risinājumu par «Starlink»; Ratnieks (NA)", "gaida risinājumu par «Starlink». Ratnieks (NA)"),
    ("par atvasinātām publiskām personām; Švinka (PRO)", "par atvasinātām publiskām personām. Švinka (PRO)"),
    ("reģioniem vismaz desmit gadiem; Patmalnieks (JV)", "reģioniem vismaz desmit gadiem. Patmalnieks (JV)"),
]


def sql_str(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def apply_reps(text: str, reps: list[tuple[str, str]], label: str, expect: dict[str, int] | None = None) -> str:
    for a, b in reps:
        n = text.count(a)
        want = (expect or {}).get(a, 1)
        assert n == want, f"{label}: {a[:50]!r} sagaidīts {want}, atrasts {n}"
        text = text.replace(a, b)
    return text


def main() -> int:
    apply = "--apply" in sys.argv
    db = get_db()
    n593 = db.execute("SELECT content FROM context_notes WHERE id=593").fetchone()[0]
    n594 = db.execute("SELECT content FROM context_notes WHERE id=594").fetchone()[0]
    t307 = db.execute("SELECT description FROM political_tensions WHERE id=307").fetchone()[0]
    c947 = db.execute("SELECT stance FROM claims WHERE id=710947").fetchone()[0]
    brief_row = db.execute(
        "SELECT id, content FROM context_notes WHERE note_type='daily_brief' AND topic=? ORDER BY id DESC LIMIT 1",
        (daily_brief_topic("2026-09-15"),),
    ).fetchone()
    assert brief_row["id"] == 595, brief_row["id"]
    b595 = brief_row["content"]

    new593 = apply_reps(n593, NOTE_593_REPS, "#593")
    new594 = apply_reps(n594, NOTE_594_REPS, "#594")
    new307 = apply_reps(t307, TENSION_307_REPS, "#307")
    new947 = apply_reps(c947, CLAIM_710947_REPS, "#710947")
    new595 = apply_reps(b595, BRIEF_REPS, "#595", expect={"nākamajā dienā atbild, ka": 2})

    for label, txt in (("#593", new593), ("#594", new594), ("#307", new307), ("#710947", new947)):
        n = len(txt.split())
        assert n <= 120, (label, n)
        assert lint_lv_style(txt) == [], (label, lint_lv_style(txt))
        print(f"{label}: {n} vārdi, lint tīrs")
    assert "\n" not in new307
    assert lint_lv_style(new595) == [], lint_lv_style(new595)
    print(f"#595: {len(b595)} → {len(new595)} zīmes, lint tīrs")

    if ROLLBACK.exists():
        print(f"{ROLLBACK} jau eksistē — nepārrakstu")
    else:
        lines = [
            "-- Rollback: scripts/fix_qr_round1_2026-09-15.py (QR 1. kārta: #593, #594, spriedze #307, claim #710947, pārskats #595)",
            "-- Apply date: 2026-09-15. Pēc rollback: .venv/Scripts/python.exe scripts/reembed_claims.py 710947",
            "-- wiki/dailies/2026-09-15.md atjauno no #595 satura (vai git).",
            "BEGIN;",
            f"UPDATE context_notes SET content = {sql_str(n593)} WHERE id = 593;",
            f"UPDATE context_notes SET content = {sql_str(n594)} WHERE id = 594;",
            f"UPDATE political_tensions SET description = {sql_str(t307)} WHERE id = 307;",
            f"UPDATE claims SET stance = {sql_str(c947)} WHERE id = 710947;",
            f"UPDATE context_notes SET content = {sql_str(b595)} WHERE id = 595;",
            "COMMIT;",
        ]
        ROLLBACK.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"rollback rakstīts: {ROLLBACK}")

    if not apply:
        print("sausā palaide — --apply, lai rakstītu")
        return 0
    with db:
        db.execute("UPDATE context_notes SET content=? WHERE id=593", (new593,))
        db.execute("UPDATE context_notes SET content=? WHERE id=594", (new594,))
        db.execute("UPDATE political_tensions SET description=? WHERE id=307", (new307,))
        db.execute("UPDATE claims SET stance=? WHERE id=710947", (new947,))
    r = store_context_note(topic=daily_brief_topic("2026-09-15"), note_type="daily_brief",
                           content=new595, source="atmina analīze 2026-09-15")
    print("brief:", r)
    open(WIKI, "w", encoding="utf-8", newline="\n").write(new595)
    chk = db.execute("SELECT content FROM context_notes WHERE id=595").fetchone()[0]
    assert chk == new595 == WIKI.read_text(encoding="utf-8")
    print("piemērots; tagad: .venv/Scripts/python.exe scripts/reembed_claims.py 710947")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
