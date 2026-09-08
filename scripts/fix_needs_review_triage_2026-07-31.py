"""NEEDS_REVIEW triāža 2026-07-31 — operatora apstiprināts labojumu komplekts.

Konteksts: 94 `NEEDS_REVIEW` claims pilnā pārskatīšana (sesija 2026-07-31).
Lielākā daļa bija leģitīmas tēmu robežas izvēles un paliek neskartas. Šis
skripts izpilda tikai tos gadījumus, kur ieraksts pārkāpj repo noteikumus.

DZĒŠ 3 claims (+ to `claim_vectors` rindas):
  #555673 Lato Lapsa, Vēlēšanas, conf 0.6, salience 0.85 — apgalvojums, ka
          vēlēšanu rezultāti tiks nozagti, ekstraktēts TIKAI no retvītota
          virsraksta; `quote=NULL`, raksta ķermenis korpusā nav. Pārkāpj
          claim-extractor truncated-stub noteikumu (pozīciju no parafrāzēta
          virsraksta neekstraktē). Augstākā salience visā NEEDS_REVIEW kopā,
          tātad tiešs kandidāts pārskata virsrakstam.
  #555795 Lato Lapsa, Koalīcija un partijas, conf 0.55 — apgalvo, ka ekonomikas
          ministru amatā ielicis Lembergs un ka viņa spēju līmenis atbilst
          "bārmenim". Ministrs vārdā NAV nosaukts, tikai amatā. Nenosaukts
          referents + nepārbaudīts apgalvojums par identificējamu personu =
          CLAUDE.md eskalācijas noteikums #1 un 2026-07-27 #555693 precedents.
  #555797 Guntars Vītols, Rail Baltica, conf 0.65 — dokumentā (doc 76506) vārdi
          "Rail Baltica" neparādās vispār; teksts ir atbilde sarunā par maršrutu
          līdz lidostai. Referents izsecināts no pavediena. TAJĀ PAŠĀ dienā tā
          paša pavediena cits tvīts (doc 76261) tika noraidīts tieši šī iemesla
          dēļ — divi pretēji lēmumi par vienu pavedienu, viens no tiem nepareizs.

PĀRTOPICĒ 1 claim (+ pārrēķina embedding):
  #555776 Kristaps Krištopans: 'Rail Baltica' -> 'Budžets un finanses'.
          Aģenta paša reasoning teica, ka projekts tvītā nav nosaukts un ka
          izvēlēta 'Budžets un finanses', bet DB bija ierakstīta 'Rail Baltica'.
          Saturs (20/80 ES līdzfinansējuma naudas plūsmas mehānika) ir derīga
          pozīcija arī bez projekta nosaukuma, tāpēc labo tēmu, nevis dzēš.
          NB: `store_claim` iegulst `f"{topic}: {stance}"`, tāpēc tēmas maiņa
          PRASA embedding pārrēķinu — citādi `claim_vectors` paliek novecojis
          un semantiskā meklēšana atgriež nepareizu kaimiņu (klusā desinhronizācija).
          Idempotences trijnieks (opponent_id, source_url, 'Budžets un finanses')
          pārbaudīts — sadursmes nav.

LABO reasoning tekstu 2 claims (embedding NEMAINĀS — reasoning netiek iegults):
  #555776, #555782 — abos aģents pārdomāja tēmu un atstāja novecojušu teikumu
          ("izvēlējos X"), kas ir pretrunā ar DB ierakstīto tēmu. Audita pēdas
          meloja, un tieši uz reasoning balstās @quality-reviewer.
          #555782 (Atis Švinka) saglabātā tēma 'Koalīcija un partijas' ir
          pareizā — izteikuma kodols ir NA politiķes un premjera rīcības
          vērtējums —, tāpēc labo tekstu, ne tēmu.

SEKOJOŠS SOLIS (piemērots ar roku uzreiz pēc --apply, to sedz tas pats rollback,
jo tas atjauno #555782 reasoning PILNĀ oriģinālajā redakcijā):
  #555782 reasoning sākumā palikušais "NEEDS_REVIEW: tēmas robeža neskaidra"
  aizstāts ar "REVIEWED 2026-07-31: tēmas robeža bija neskaidra", lai marķieris
  būtu konsekvents ar #555776 — abi ir pārskatīti, tāpēc ne vienam, ne otram
  nevajag palikt neizskatīto rindā.

KONVENCIJA: pārskatītam ierakstam `NEEDS_REVIEW:` tiek aizstāts ar
`REVIEWED <datums>:`. Tā NAV jauna — repo to lieto kopš 2026-04-28 (62 rindas,
lielākā daļa no vienīgā sweep 2026-06-13), tikai nekur nav dokumentēta. Šis
skripts sākotnēji ieviesa paralēlu `PĀRSKATĪTS` marķieri; abas rindas pārliktas
uz `REVIEWED`, lai `LIKE` vaicājumi neizlaistu daļu. Sk. BACKLOG.

NEAIZTIEK:
  #553938 Ašeradens — nav dublikāts ar #532114: 16.06. par priekšlikumu,
          23.07. par pieņemto likumu, atšķirīgi `stated_at`. Divi laika punkti.
  #555869 Seržants (conf 0.55) — CLAUDE.md eskalācijas noteikums #2 paredz tieši
          šo apstrādi (0.5-0.6 -> glabā ar needs_review), tātad ieraksts JAU ir
          noteikumiem atbilstošs. Atstāts operatora redzeslokā, ne dzēsts.
  NBS #555700/#555658/#555829 — atribūcijas politikas jautājums, ne datu defekts.
  Pārējie ~55 tēmas robežas gadījumi — korekti izlemti un pamatoti.

Rollback: data/rollback_needs_review_triage_2026-07-31.sql (ģenerēts PIRMS izmaiņām).

Lietošana:
    .venv/Scripts/python.exe scripts/fix_needs_review_triage_2026-07-31.py --emit-rollback
    .venv/Scripts/python.exe scripts/fix_needs_review_triage_2026-07-31.py --apply
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

# Skripts dzīvo scripts/, tāpēc sys.path[0] ir scripts/, nevis repo sakne —
# bez šī `import src.*` krīt ar ModuleNotFoundError arī tad, ja palaišanas
# darba mape ir pareiza.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DB_PATH = "data/atmina.db"
ROLLBACK_PATH = Path("data/rollback_needs_review_triage_2026-07-31.sql")

DELETE_IDS = [555673, 555795, 555797]
RETOPIC = {555776: ("Rail Baltica", "Budžets un finanses")}

# Novecojušais teikums -> labotais. Aizvieto burtiski, lai nesabojātu pārējo tekstu.
REASONING_FIXES = {
    555776: (
        "NEEDS_REVIEW: konkrētais projekts un līdzfinansējuma shēma tvītā nav "
        "nosaukta; izvēlējos Budžets un finanses, jo kodols ir ES līdzfinansējuma "
        "naudas plūsmas mehānika, nevis viens konkrēts infrastruktūras projekts.",
        "REVIEWED 2026-07-31: konkrētais projekts tvītā nav nosaukts, tāpēc tēma "
        "labota no 'Rail Baltica' uz 'Budžets un finanses' — kodols ir ES "
        "līdzfinansējuma naudas plūsmas mehānika, nevis viens konkrēts "
        "infrastruktūras projekts. Embedding pārrēķināts.",
    ),
    555782: (
        "Izvēlējos Aizsardzība un drošība, jo runātājs pats izteikumu ietvaro kā "
        "kaitējumu valsts drošībai un sabiedroto attiecībām.",
        "REVIEWED 2026-07-31: saglabātā tēma ir 'Koalīcija un partijas' un tā ir "
        "pareizā — izteikuma kodols ir NA politiķes un Ministru prezidenta rīcības "
        "vērtējums; valsts drošības arguments ir pamatojums, ne priekšmets. "
        "(Iepriekš šeit bija novecojis teikums par 'Aizsardzība un drošība'.)",
    ),
}


def _connect() -> sqlite3.Connection:
    import sqlite_vec

    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)
    return db


def _sql_str(v) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def emit_rollback(db: sqlite3.Connection) -> None:
    cols = [
        "id", "opponent_id", "document_id", "topic", "stance", "quote",
        "confidence", "reasoning", "salience", "source_url", "stated_at",
        "created_at", "claim_type", "speaker_id", "party_id",
    ]
    lines = [
        "-- Rollback: atceļ scripts/fix_needs_review_triage_2026-07-31.py",
        "-- Forward change (piemērots 2026-07-31): NEEDS_REVIEW triāžas labojumi —",
        "--   dzēsti claims 555673, 555795, 555797 (+ to claim_vectors rindas);",
        "--   #555776 tēma 'Rail Baltica' -> 'Budžets un finanses' (+ embedding pārrēķins);",
        "--   #555776 un #555782 reasoning teksts labots (novecojuši 'izvēlējos X' teikumi).",
        "-- Pamatojums katram gadījumam: skripta docstring.",
        "--",
        "-- SVARĪGI — `claim_vectors` ir vec0 virtuālā tabula: tīrs .sql to NEatjauno.",
        "-- Pēc šī faila palaišanas atjauno vektorus atjaunotajiem/mainītajiem claims:",
        "--   .venv/Scripts/python.exe -c \"import sqlite3,sqlite_vec;"
        "from src.db import _float_list_to_bytes;from src.embeddings import embed_text;"
        "db=sqlite3.connect('data/atmina.db');db.enable_load_extension(True);"
        "sqlite_vec.load(db);db.enable_load_extension(False);"
        "[db.execute('INSERT OR REPLACE INTO claim_vectors (claim_id, embedding) VALUES (?, ?)',"
        "(r[0], _float_list_to_bytes(embed_text(r[1]+': '+r[2])))) "
        "for r in db.execute('SELECT id, topic, stance FROM claims WHERE id IN "
        "(555673,555776,555782,555795,555797)').fetchall()];db.commit()\"",
        "",
        "BEGIN TRANSACTION;",
        "",
    ]

    for cid in DELETE_IDS:
        r = db.execute(
            f"SELECT {', '.join(cols)} FROM claims WHERE id = ?", (cid,)
        ).fetchone()
        if r is None:
            lines.append(f"-- claim {cid}: jau nav DB, nekas atjaunojams")
            continue
        vals = ", ".join(_sql_str(r[c]) for c in cols)
        lines.append(f"-- atjauno claim #{cid}")
        lines.append(
            f"INSERT OR IGNORE INTO claims ({', '.join(cols)})\nVALUES ({vals});"
        )
        lines.append("")

    for cid, (old_topic, _new) in RETOPIC.items():
        lines.append(f"-- atgriež #{cid} tēmu")
        lines.append(
            f"UPDATE claims SET topic = {_sql_str(old_topic)} WHERE id = {cid};"
        )
        lines.append("")

    for cid, (old_text, _new) in REASONING_FIXES.items():
        r = db.execute("SELECT reasoning FROM claims WHERE id = ?", (cid,)).fetchone()
        lines.append(f"-- atgriež #{cid} reasoning tekstu (pilns oriģināls)")
        lines.append(
            f"UPDATE claims SET reasoning = {_sql_str(r['reasoning'])} WHERE id = {cid};"
        )
        lines.append("")

    lines.append("COMMIT;")
    ROLLBACK_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Rollback uzrakstīts: {ROLLBACK_PATH}")


def apply(db: sqlite3.Connection) -> int:
    from src.db import _float_list_to_bytes
    from src.embeddings import embed_text

    # 1. Reasoning labojumi — burtiska teikuma aizvietošana, ar pārbaudi.
    for cid, (old_text, new_text) in REASONING_FIXES.items():
        cur = db.execute("SELECT reasoning FROM claims WHERE id = ?", (cid,)).fetchone()
        if cur is None:
            print(f"  ! #{cid}: nav DB, izlaists")
            continue
        if old_text not in cur["reasoning"]:
            print(f"  ! #{cid}: gaidītais teikums NAV atrasts — apturu, nekas nemainīts")
            return 1
        db.execute(
            "UPDATE claims SET reasoning = ? WHERE id = ?",
            (cur["reasoning"].replace(old_text, new_text), cid),
        )
        print(f"  ✓ #{cid} reasoning labots")

    # 2. Tēmas maiņa + OBLIGĀTS embedding pārrēķins (topic ir iegultajā tekstā).
    for cid, (old_topic, new_topic) in RETOPIC.items():
        r = db.execute(
            "SELECT opponent_id, source_url, topic, stance FROM claims WHERE id = ?",
            (cid,),
        ).fetchone()
        if r is None:
            print(f"  ! #{cid}: nav DB, izlaists")
            continue
        if r["topic"] != old_topic:
            print(f"  ! #{cid}: tēma jau ir {r['topic']!r}, gaidīju {old_topic!r} — apturu")
            return 1
        clash = db.execute(
            "SELECT COUNT(*) FROM claims WHERE opponent_id = ? AND source_url = ? "
            "AND topic = ? AND id != ?",
            (r["opponent_id"], r["source_url"], new_topic, cid),
        ).fetchone()[0]
        if clash:
            print(f"  ! #{cid}: idempotences sadursme ar esošu claim — apturu")
            return 1
        db.execute("UPDATE claims SET topic = ? WHERE id = ?", (new_topic, cid))
        blob = _float_list_to_bytes(embed_text(f"{new_topic}: {r['stance']}"))
        db.execute("DELETE FROM claim_vectors WHERE claim_id = ?", (cid,))
        db.execute(
            "INSERT INTO claim_vectors (claim_id, embedding) VALUES (?, ?)",
            (cid, blob),
        )
        print(f"  ✓ #{cid} tēma {old_topic!r} -> {new_topic!r}, embedding pārrēķināts")

    # 3. Dzēšana — vektors PIRMS claims rindas (kā fix_purge_registration_claims).
    for cid in DELETE_IDS:
        refs = db.execute(
            "SELECT COUNT(*) FROM contradictions WHERE claim_old_id = ? OR claim_new_id = ?",
            (cid, cid),
        ).fetchone()[0]
        if refs:
            print(f"  ! #{cid}: {refs} pretrunas atsaucas uz to — apturu, nedzēšu")
            return 1
        db.execute("DELETE FROM claim_vectors WHERE claim_id = ?", (cid,))
        n = db.execute("DELETE FROM claims WHERE id = ?", (cid,)).rowcount
        print(f"  ✓ #{cid} dzēsts ({n} rinda + vektors)")

    db.commit()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--emit-rollback", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if not (args.emit_rollback or args.apply):
        ap.error("norādi --emit-rollback vai --apply")

    db = _connect()
    try:
        if args.emit_rollback:
            emit_rollback(db)
            return 0
        if not ROLLBACK_PATH.exists():
            print(f"APTURU: {ROLLBACK_PATH} neeksistē. Palaid --emit-rollback pirms --apply.")
            return 1
        return apply(db)
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
