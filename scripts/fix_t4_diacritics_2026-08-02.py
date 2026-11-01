"""Labo T4 laikmeta nodiakritizēto tekstu 18 claims rindās + pārrēķina 2 vektorus.

Trīs atšķirīgas klases, un tās NEDRĪKST apstrādāt vienādi:

1. `reasoning` (13 rindas) — MŪSU teksts, publiskā virsmā nenonāk (pārbaudīts:
   `NEEDS_REVIEW` neparādās nevienā uzbūvētā HTML lapā, un konkrētais teksts arī
   ne). Gramatikas vārti attiecas pilnā apmērā. Netiek iegults, tāpēc vektorus
   pārrēķināt NEVAJAG.

2. `stance` (2 rindas) — MŪSU teksts, bet TIEK iegults (`store_claim` iegulst
   `f"{topic}: {stance}"`), tāpēc katrai rindai jāpārrēķina `claim_vectors`.
   Šīs divas nes transliterācijas bojājumu („Shuvajevs"), ko diakritiku vārti
   NEREDZ: vārti ir attiecības tests, un pārējais teikums ir ar diakritiku, tāpēc
   attiecība iztur. Šī ir atsevišķa, agrāk nemērīta klase — sk. BACKLOG.

3. `quote` (3 rindas) — VERBATIM lauks. Šīs vērtības **netiek rakstītas ar roku**:
   skripts tās izvelk no paša avota dokumenta ar diakritiku salocīšanu abās pusēs
   un paplašina līdz teikuma robežai. Ja avotā tekstu neatrod, rinda tiek IZLAISTA,
   nevis uzminēta. Citāta „labošana" no galvas ir nepatiesa citēšana — tieši tā
   2026-08-02 gandrīz notika ar Kulberga `pavadam` -> `pavadām`.

NEAIZTIEK claim #1595 („Ir balts gulbis...") — tā teksts avota dokumentā ir
TIEŠI tāds, tātad zemā diakritika ir paša runātāja, ne mūsu bojājums. Tas ir
dokumentēts vārtu viltus pozitīvs.

Palaišana:  .venv/Scripts/python.exe scripts/fix_t4_diacritics_2026-08-02.py [--apply]
Bez --apply tikai izdrukā, ko darītu. Rollback tiek uzrakstīts PIRMS izmaiņas.
"""
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db import get_db  # noqa: E402
from src.embeddings import embed_text  # noqa: E402
from src.preflight import ensure_embeddings_live  # noqa: E402
from src.quality import validate_lv_diacritics  # noqa: E402

ROLLBACK = Path("data/rollback_t4_diacritics_2026-08-02.sql")

REASONING = {
    222: "Konkrēts politisks rezultāts — nostiprināta ES pretkrievijas nostāja finanšu jomā",
    233: "Filozofiska pieeja valsts samazināšanai — MMN kodola pozīcija",
    239: "MMN filozofiskā pamattēze — libertārisms pret valsts kontroli",
    263: "Principiāla enerģētikas pozīcija — saistīta ar ģeopolitisko drošību",
    6757: "Skaidrs aicinājums mainīt valdību — konkrēta politiska pozīcija",
    6762: "Konkrēta vēlēšanu integritātes pozīcija — biļetenu saglabāšana",
    6843: "Jurēvics tieši citēts Dienas rakstā kā JV frakcijas vadītājs.",
    6878: "Dienas raksts ziņo, ka Progresīvie balsoja pret. Šuvajevs ir frakcijas vadītājs.",
    6880: ("LSM raksts par Sprūda demisijas balsojumu — koalīcija (ieskaitot Progresīvos) "
           "atbalstīja ministru."),
    # Nebija nodiakritizēts, bet bija ANGLISKI — `reasoning` ir mūsu teksts, un
    # projekta valoda ir latviešu. Vārti to mūžīgi karotu kā „latviešu bez garumzīmēm".
    6917: "Tiešs tvīts NATO gadadienā, kas apstiprina apņemšanos par aizsardzības investīcijām.",
    532764: "Programmas pamatidejas un 3. sadaļas kultūras/identitātes vērtību nostāja.",
    532766: "Programmas 6. sadaļas nostāja par Krievijas un Ukrainas konfliktu.",
    532768: ("Programmas 7. sadaļas valsts pārvaldes un tiešās demokrātijas solījumi, "
             "konsolidēti."),
}

STANCE = {
    6878: ("Progresīvie (Šuvajevs kā frakcijas vadītājs) balsoja pret ZZS priekšlikumu "
           "samazināt koku galvenās cirtes vecumu"),
    6880: ("Progresīvie (Šuvajevs kā frakcijas vadītājs) balsoja pret opozīcijas pieprasīto "
           "aizsardzības ministra Sprūda demisiju"),
}

QUOTE_FROM_SOURCE = [222, 257, 6779]


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def restore_quote(stored: str, doc: str):
    """Return the source span matching `stored`, or None. Never invents text."""
    q, d = _norm(stored), _norm(doc)
    fq, fd = _fold(q), _fold(d)
    i = fd.find(fq)
    if i >= 0:
        return d[i:i + len(q)]
    # Stored text may itself be wrong at the tail (e.g. 'mezu' for 'mežus');
    # anchor on the longest matching prefix, then run to the sentence end.
    lo, hi, best = 0, len(fq), 0
    while lo <= hi:
        mid = (lo + hi) // 2
        if fq[:mid] and fd.find(fq[:mid]) >= 0:
            best, lo = mid, mid + 1
        else:
            hi = mid - 1
    if best < 40:
        return None
    j = fd.find(fq[:best])
    m = re.compile(r"[.!?](\s|$)").search(d, j + best - 5)
    end = m.end() - len(m.group(1)) if m else j + len(q)
    return d[j:end]


def q(s):
    return "'" + s.replace("'", "''") + "'"


def main() -> int:
    apply = "--apply" in sys.argv
    if apply:
        ensure_embeddings_live()

    db = get_db()
    import sqlite_vec
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)

    quotes = {}
    for cid in QUOTE_FROM_SOURCE:
        row = db.execute(
            "SELECT c.quote, d.content FROM claims c JOIN documents d ON d.id=c.document_id "
            "WHERE c.id=?", (cid,)).fetchone()
        got = restore_quote(row["quote"], row["content"]) if row else None
        if got is None:
            print(f"  IZLAISTS #{cid}: avotā neatrod — netiek minēts")
            continue
        quotes[cid] = got
        print(f"  #{cid} citāts no avota:\n      {got}")

    lines = [
        "-- ROLLBACK for scripts/fix_t4_diacritics_2026-08-02.py\n"
        "-- Restores the pre-fix reasoning/stance/quote text on 18 claims rows,\n"
        "-- and the byte-identical previous embeddings for the two stance rows.\n"
        "-- NB: claim_vectors is a vec0 virtual table — sqlite_vec must be loaded.\n"
        "-- Applied: 2026-08-02.\n\nBEGIN TRANSACTION;\n"
    ]
    for cid, _ in sorted(REASONING.items()):
        old = db.execute("SELECT reasoning FROM claims WHERE id=?", (cid,)).fetchone()[0]
        lines.append(f"UPDATE claims SET reasoning = {q(old)} WHERE id = {cid};")
    for cid, txt in sorted(quotes.items()):
        old = db.execute("SELECT quote FROM claims WHERE id=?", (cid,)).fetchone()[0]
        lines.append(f"UPDATE claims SET quote = {q(old)} WHERE id = {cid};")
    for cid, _ in sorted(STANCE.items()):
        old = db.execute("SELECT stance FROM claims WHERE id=?", (cid,)).fetchone()[0]
        vec = db.execute("SELECT embedding FROM claim_vectors WHERE claim_id=?", (cid,)).fetchone()
        lines.append(f"UPDATE claims SET stance = {q(old)} WHERE id = {cid};")
        if vec:
            lines.append(f"DELETE FROM claim_vectors WHERE claim_id = {cid};")
            lines.append(
                f"INSERT INTO claim_vectors (claim_id, embedding) VALUES "
                f"({cid}, X'{vec['embedding'].hex()}');")
    lines.append("\nCOMMIT;\n")
    ROLLBACK.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nrollback uzrakstīts: {ROLLBACK} ({ROLLBACK.stat().st_size} B)")

    # Language gate on everything we authored, before any write.
    for cid, txt in list(REASONING.items()) + list(STANCE.items()):
        ok, why = validate_lv_diacritics(txt)
        if not ok:
            print(f"STOP: #{cid} neiztur diakritiku vārtus: {why}")
            return 1

    if not apply:
        print("\nSAUSĀ PALAIDE — nekas nav ierakstīts. Palaid ar --apply.")
        return 0

    for cid, txt in REASONING.items():
        db.execute("UPDATE claims SET reasoning=? WHERE id=?", (txt, cid))
    for cid, txt in quotes.items():
        db.execute("UPDATE claims SET quote=? WHERE id=?", (txt, cid))
    for cid, txt in STANCE.items():
        topic = db.execute("SELECT topic FROM claims WHERE id=?", (cid,)).fetchone()[0]
        db.execute("UPDATE claims SET stance=? WHERE id=?", (txt, cid))
        emb = embed_text(f"{topic}: {txt}")
        import struct
        blob = struct.pack(f"{len(emb)}f", *emb)
        db.execute("DELETE FROM claim_vectors WHERE claim_id=?", (cid,))
        db.execute("INSERT INTO claim_vectors (claim_id, embedding) VALUES (?, ?)", (cid, blob))
        print(f"  #{cid} stance atjaunināts + vektors pārrēķināts")
    db.commit()

    bad = 0
    for cid in list(REASONING) + list(STANCE) + list(quotes):
        for f in ("reasoning", "stance", "quote"):
            v = db.execute(f"SELECT {f} FROM claims WHERE id=?", (cid,)).fetchone()[0]
            if v and len(v) > 60 and not validate_lv_diacritics(v)[0]:
                print(f"  vēl karo: #{cid}.{f}")
                bad += 1
    print(f"\nPABEIGTS. Atlikušie karogi skartajās rindās: {bad}")
    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
