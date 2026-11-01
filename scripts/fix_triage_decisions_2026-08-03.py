# -*- coding: utf-8 -*-
"""Triāžas B/C lēmumu piemērošana 2026-08-03 (operatora apstiprināts AskUserQuestion).

Trīs bloki vienā transakcijā:
  1) DZĒŠANAS (7): 615799, 615833, 615858, 548550, 553938, 555886, 555773
     — claim rinda + claim_vectors rinda kopā (vektoru bāreņu nepieļaušana).
  2) C-LABOJUMI (11 stance/quote): 548558, 555653, 555677, 555644, 554003,
     555835, 615809, 555824, 554004, 555760, 555877 — stance precizēts līdz
     avota robežām; #548558 quote->NULL (žurnālista atstāstījums) + conf 0.8->0.6;
     #555824 quote atjaunots pret pašreizējo avota redakciju (doc pārrakstīts
     pēc claim izveides — pārbaudīts ar substring pret documents.content).
  3) TĒMU MIGRĀCIJAS (5): 553940 ES politika->Imigrācija; 615883 Korupcija un
     KNAB->Valsts pārvalde; 615811/615837/615801 Aizsardzība un drošība->
     Imigrācija (noteikums: tēmu nosaka izteikuma nosauktais pamatojums, ne
     instruments). Kolīziju priekšpārbaude katram (idempotences trijnieks).

Marķieri: labotajām/migrētajām needs_review rindām NEEDS_REVIEW -> "Izvērtēts
2026-08-03" + pievienots lēmuma teikums; 615837/615801 (bez marķiera) — tikai
migrācijas piezīme. review_status uztur trigeris, ar roku nerakstām.

PĒC skripta OBLIGĀTI: .venv/Scripts/python.exe scripts/reembed_claims.py
  --ids-from data/fix_triage_decisions_2026-08-03.ids
(15 rindas ar mainītu topic/stance; #555824 mainīts tikai quote — tur NAV).

Rollback: data/rollback_triage_decisions_2026-08-03.sql (ģenerē --emit-rollback
PIRMS --apply; dzēstajām — pilnas INSERT rindas; vektori atjaunojami ar to pašu
reembed recepti, hex netiek glabāts — elektr 2026-08-03 precedents).
"""
from __future__ import annotations

import argparse
import io
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DB = 'data/atmina.db'
ROLLBACK = Path('data/rollback_triage_decisions_2026-08-03.sql')
IDS_OUT = Path('data/fix_triage_decisions_2026-08-03.ids')

DELETE_IDS = [615799, 615833, 615858, 548550, 553938, 555886, 555773]

# (id, jauns_stance | None, jauns_quote | 'KEEP' | None, jauna_conf | None, lēmuma piezīme)
EDITS = [
    (548558,
     "Norāda, ka regulatori (Eiropas Centrālā banka un Igaunijas centrālā banka), "
     "vērtējot Ungārijas 'OTP Bank' iespējamo 'Luminor' iegādi, pēc viņa teiktā "
     "noteikti ņems vērā Valsts drošības dienesta atzinumu par 'OTP Group' darbību Krievijā.",
     None, 0.6,
     "quote bija žurnālista atstāstījums, ne runātāja vārdi — noņemts; prognozes forma atjaunota pēc avota."),
    (555653, None, 'KEEP', None,
     "svītrots avotā neesošais 'eksporta'; tēma paliek pēc granulu klastera precedenta."),
    (555677, None, 'KEEP', None,
     "avota 'varbūt vēlas komentēt?' nav prasība — 'prasa' aizstāts ar 'aicina komentēt'."),
    (555644, None, 'KEEP', None,
     "avotā nav prasības — nosacītā neticība nepārvēršas par pieprasījumu; klauzula nogriezta."),
    (554003,
     "Vienojies ar pārējiem Baltijas valstu tieslietu ministriem drīzumā tikties, lai kopīgi "
     "stiprinātu valstu institūciju un tiesu sistēmas noturību; uzskata ciešu reģionālo "
     "sadarbību par galveno drošības resursu.",
     'KEEP', None,
     "avotā viena gaidāma tikšanās, ne regulārs formāts — konkrētais notikums atjaunots."),
    (555835,
     "Vēlas, lai kokrūpnieku lietas ierobežotas pieejamības dokumentu izvērtēšanas process "
     "būtu sabiedrībai caurspīdīgs; kā tieslietu ministrs ir uzrunājis Zemkopības ministriju "
     "un norāda, ka jautājums ir adresējams arī ģenerālprokuroram.",
     'KEEP', None,
     "avotā 'ir adresējams' (nav noticis) un vēlējuma forma — pabeigtības apgalvojumi noņemti."),
    (615809,
     "Uzskata, ka pilsoniskais aktīvisms ir katra cilvēka paša uzdevums, nevis valdību, "
     "NVO vai memoranda padomju pienākums.",
     'KEEP', None,
     "norādāmā 'šo' referents (citāttvīts) korpusā nav — otrā daļa nogriezta."),
    (555824, None, 'DOC_REFRESH', None,
     "citāts atjaunots pret pašreizējo avota redakciju — raksts pārrakstīts pēc claim izveides."),
    (554004, None, 'KEEP', None,
     "avota 'Izskatās, ka' ir minējums — 'Apgalvo' aizstāts ar 'Pieļauj'."),
    (555760,
     "Pārmet pašvaldībai un Valsts policijai, ka Priekules uzbrukumā bojāgājušā pedagoga bēru "
     "izdevumiem tiek vākti sabiedrības ziedojumi — uzskata, ka atbildība par cieņpilnu "
     "apbedīšanu jāuzņemas institūcijām, un ziedojumu vākšanu vērtē kā pazemojošu pret "
     "bojāgājušā ģimeni.",
     'KEEP', None,
     "faktu kļūda: bojāgājušais bija skolas pedagogs, ne iestāžu darbinieks; pārmetuma forma atjaunota."),
    (555877,
     "Iebilst pret Nacionālās apvienības deputāta Anša Pūpola pausto, ka Latvijai nav "
     "pienākuma palīdzēt Spānijai cīņā pret robežpārkāpējiem; norāda, ka Latviju šobrīd "
     "sargā aptuveni 800 Spānijas karavīru, un pauž cerību, ka ārlietas nekad nenonāks "
     "Nacionālās apvienības rokās.",
     'KEEP', None,
     "persona nevis partija; atjaunots nomests kvalifikators un vēlējuma forma."),
]

INLINE_REPLACES = {
    555653: ("kad ilgtermiņa eksporta līgumi kļūst neizdevīgi",
             "kad ilgtermiņa līgumi kļūst neizdevīgi"),
    555677: ("un prasa Altum skaidrojumu par konkrētu atbalstīto projektu",
             "un aicina Altum komentēt konkrētu atbalstīto projektu"),
    555644: ("videonovērošanas ieraksti — pieprasa ierakstu publiskošanu kā ticamības priekšnoteikumu.",
             "videonovērošanas ieraksti."),
    554004: ("Apgalvo, ka Jaunās Vienotības", "Pieļauj, ka Jaunās Vienotības"),
    555824: ("lielā daļā valsts pārvaldes šādā veidā no reģioniem deputātiem",
             "šādā veidā deputātiem no reģioniem"),
}

MIGRATIONS = [
    (553940, 'Imigrācija', "tēma migrēta: SAVE EUROPE ACT priekšmets ir imigrācija (precedenti #531935, #615818, #532726)."),
    (615883, 'Valsts pārvalde', "tēma migrēta: kompensāciju lieta bez izmeklēšanas iestādes pēc precedenta (#555824, #532001) pieder Valsts pārvaldei."),
    (615811, 'Imigrācija', "tēma migrēta pēc pamatojuma noteikuma (izteikuma nosauktais pamatojums ir nelegālā migrācija)."),
    (615837, 'Imigrācija', "Tēma migrēta 2026-08-03 uz Imigrācija pēc pamatojuma noteikuma (operatora lēmums)."),
    (615801, 'Imigrācija', "Tēma migrēta 2026-08-03 uz Imigrācija pēc pamatojuma noteikuma (operatora lēmums)."),
]
NO_MARKER_IDS = {615837, 615801}

REEMBED_IDS = sorted({e[0] for e in EDITS if e[0] != 555824} | {m[0] for m in MIGRATIONS})


def esc(s: str) -> str:
    return s.replace("'", "''")


def emit_rollback(con: sqlite3.Connection) -> None:
    cols = [r[1] for r in con.execute("PRAGMA table_info(claims)")]
    lines = [
        "-- Rollback for: scripts/fix_triage_decisions_2026-08-03.py",
        "-- (7 dzēšanas + 11 C-labojumi + 5 tēmu migrācijas; operatora apstiprināts 2026-08-03).",
        "-- Dzēstajām rindām: pilnas INSERT rindas. PĒC šī rollback OBLIGĀTI pārrēķināt vektorus:",
        "--   .venv/Scripts/python.exe scripts/reembed_claims.py --ids-from data/rollback_triage_decisions_2026-08-03.ids",
        "-- (dzēstajām vektors jāuzbūvē no jauna; labotajām/migrētajām — jāatgriež vecais teksts).",
        "-- Apply date: 2026-08-03.",
        "BEGIN;",
    ]
    all_ids = []
    for cid in DELETE_IDS:
        row = con.execute(f"SELECT {', '.join(cols)} FROM claims WHERE id=?", (cid,)).fetchone()
        assert row is not None, f"delete pre-image: {cid} nav DB"
        vals = []
        for v in row:
            if v is None:
                vals.append('NULL')
            elif isinstance(v, (int, float)):
                vals.append(str(v))
            else:
                vals.append(f"'{esc(str(v))}'")
        lines.append(f"INSERT INTO claims ({', '.join(cols)}) VALUES ({', '.join(vals)});")
        all_ids.append(cid)
    for cid in [e[0] for e in EDITS] + [m[0] for m in MIGRATIONS]:
        row = con.execute("SELECT topic, stance, quote, confidence, reasoning FROM claims WHERE id=?", (cid,)).fetchone()
        assert row is not None, f"edit pre-image: {cid} nav DB"
        topic, stance, quote, confidence, reasoning = row
        q = 'NULL' if quote is None else f"'{esc(quote)}'"
        lines.append(
            f"UPDATE claims SET topic = '{esc(topic)}', stance = '{esc(stance)}', "
            f"quote = {q}, confidence = {confidence}, reasoning = '{esc(reasoning)}' WHERE id = {cid};"
        )
        all_ids.append(cid)
    lines.append("COMMIT;")
    ROLLBACK.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    Path('data/rollback_triage_decisions_2026-08-03.ids').write_text(
        '\n'.join(str(i) for i in sorted(set(all_ids))) + '\n', encoding='utf-8')
    print(f"rollback: {ROLLBACK} ({len(DELETE_IDS)} INSERT + {len(EDITS) + len(MIGRATIONS)} UPDATE)")


def resolve_marker(reasoning: str, note: str, cid: int) -> str:
    if cid in NO_MARKER_IDS:
        return reasoning + ' ' + note
    assert 'NEEDS_REVIEW' in reasoning, f"{cid}: nav marķiera, bet gaidīts"
    out = reasoning.replace('NEEDS_REVIEW', 'Izvērtēts 2026-08-03')
    return out + ' Lēmums 2026-08-03: ' + note


def apply(con: sqlite3.Connection) -> None:
    from src.quality import validate_lv_diacritics

    cur = con.cursor()
    # kolīziju priekšpārbaude migrācijām
    for cid, new_topic, _ in MIGRATIONS:
        opp, url = cur.execute("SELECT opponent_id, source_url FROM claims WHERE id=?", (cid,)).fetchone()
        hit = cur.execute(
            "SELECT id FROM claims WHERE opponent_id=? AND source_url=? AND topic=? AND id<>?",
            (opp, url, new_topic, cid)).fetchone()
        assert hit is None, f"KOLĪZIJA: {cid} -> {new_topic} sadurtos ar #{hit[0]}"
    print("kolīziju priekšpārbaude: 5/5 brīvi")

    cur.execute("BEGIN")
    # 1) dzēšanas
    for cid in DELETE_IDS:
        cur.execute("DELETE FROM claim_vectors WHERE claim_id=?", (cid,))
        cur.execute("DELETE FROM claims WHERE id=?", (cid,))
    # 2) labojumi
    for cid, new_stance, quote_mode, new_conf, note in EDITS:
        topic, stance, quote, confidence, reasoning = cur.execute(
            "SELECT topic, stance, quote, confidence, reasoning FROM claims WHERE id=?", (cid,)).fetchone()
        if cid in INLINE_REPLACES:
            old_seg, new_seg = INLINE_REPLACES[cid]
            target = quote if quote_mode == 'DOC_REFRESH' else stance
            assert target and target.count(old_seg) == 1, f"{cid}: segments nav atrasts tieši 1x"
            if quote_mode == 'DOC_REFRESH':
                quote = target.replace(old_seg, new_seg)
                doc_id = cur.execute("SELECT document_id FROM claims WHERE id=?", (cid,)).fetchone()[0]
                content = cur.execute("SELECT content FROM documents WHERE id=?", (doc_id,)).fetchone()[0]
                assert quote[:80] in content, f"{cid}: atjaunotais citāts nav avota dokumentā"
            else:
                stance = target.replace(old_seg, new_seg)
        if new_stance is not None:
            stance = new_stance
        if quote_mode is None:
            quote = None
        if new_conf is not None:
            confidence = new_conf
        reasoning = resolve_marker(reasoning, note, cid)
        for label, txt in (('stance', stance), ('reasoning', reasoning)):
            ok, why = validate_lv_diacritics(txt)
            assert ok, f"{cid} {label}: diakritikas vārti — {why}"
        cur.execute("UPDATE claims SET stance=?, quote=?, confidence=?, reasoning=? WHERE id=?",
                    (stance, quote, confidence, reasoning, cid))
    # 3) migrācijas
    for cid, new_topic, note in MIGRATIONS:
        reasoning = cur.execute("SELECT reasoning FROM claims WHERE id=?", (cid,)).fetchone()[0]
        reasoning = resolve_marker(reasoning, note, cid)
        ok, why = validate_lv_diacritics(reasoning)
        assert ok, f"{cid} reasoning: diakritikas vārti — {why}"
        cur.execute("UPDATE claims SET topic=?, reasoning=? WHERE id=?", (new_topic, reasoning, cid))
    con.commit()

    # verifikācija
    n_del = cur.execute(f"SELECT COUNT(*) FROM claims WHERE id IN ({','.join('?' * len(DELETE_IDS))})", DELETE_IDS).fetchone()[0]
    assert n_del == 0, f"dzēšana nepilnīga: {n_del} palikuši"
    for cid, new_topic, _ in MIGRATIONS:
        t = cur.execute("SELECT topic FROM claims WHERE id=?", (cid,)).fetchone()[0]
        assert t == new_topic, f"{cid}: topic {t!r}"
    leftover = cur.execute(
        f"SELECT COUNT(*) FROM claims WHERE id IN ({','.join('?' * (len(EDITS) + len(MIGRATIONS)))}) AND review_status='needs_review'",
        [e[0] for e in EDITS] + [m[0] for m in MIGRATIONS]).fetchone()[0]
    assert leftover == 0, f"{leftover} rindas joprojām needs_review"
    IDS_OUT.write_text('\n'.join(str(i) for i in REEMBED_IDS) + '\n', encoding='utf-8')
    print(f"piemērots: -{len(DELETE_IDS)} claims, {len(EDITS)} laboti, {len(MIGRATIONS)} migrēti; "
          f"re-embed saraksts ({len(REEMBED_IDS)}): {IDS_OUT}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--emit-rollback', action='store_true')
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()
    con = sqlite3.connect(DB)
    # claim_vectors ir vec0 virtuālā tabula — bez paplašinājuma DELETE krīt ar
    # "no such module: vec0" (get_db() to arī neielādē; zināmā klase).
    import sqlite_vec
    con.enable_load_extension(True)
    sqlite_vec.load(con)
    con.enable_load_extension(False)
    try:
        if args.emit_rollback:
            emit_rollback(con)
        elif args.apply:
            assert ROLLBACK.exists(), "vispirms --emit-rollback (un komitē!)"
            apply(con)
        else:
            print(__doc__)
    finally:
        con.close()


if __name__ == '__main__':
    main()
