"""NEEDS_REVIEW triāža 2026-09-27 (7 pozīcijas, operatora uzdevums «izskati ar advisor»).

Aizstāj `NEEDS_REVIEW:` marķieri ar `Izvērtēts 2026-09-27: ...` (review_status
atvasina trigeris). #724951 stance sašaurināts līdz tieši teiktajam → pēc
palaišanas OBLIGĀTI `scripts/reembed_claims.py 724951`.

Lietojums:
    .venv/Scripts/python.exe scripts/fix_needs_review_triage_2026-09-27.py --rollback   # raksta rollback failu
    .venv/Scripts/python.exe scripts/fix_needs_review_triage_2026-09-27.py --apply
Rollback: data/rollback_needs_review_triage_2026-09-27.sql
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.db import get_db  # noqa: E402

ROLLBACK = Path("data/rollback_needs_review_triage_2026-09-27.sql")

# id -> (jaunā izvērtējuma klauzula, jaunā confidence vai None, jaunais stance vai None)
FIXES = {
    724951: ("stance sašaurināts līdz tieši teiktajam; lasījums par atsevišķu kandidātu izvēli "
             "(sal. #704003) tvītā nav teikts, tāpēc izņemts no stance; paša vārdi, 0,7.",
             0.7,
             "Aicina mainīt vēlēšanu kārtību; retoriskos jautājumos pretstata «noteiktu kastu» "
             "izvēli «labāko ābolu» izlasīšanai."),
    724953: ("skaidrs atribuēts atstāsts LSM (910 vārdi, «Savukārt Šlesers uzskata»); "
             "izteikuma vieta un laiks nav norādīti, bet tā ir izcelsmes detaļa, ne šaubas par saturu — 0,65.",
             0.65, None),
    724957: ("burtisks citāts ar normatīvu apgalvojumu par valsts uzdevumu; svinīgais ierāmējums "
             "to nemazina (kā #724929) — 0,7.",
             0.7, None),
    724961: ("teksts ir pilns LETA kopsavilkums (4 rindkopas, 120 vārdi, virs stub sliekšņa) ar "
             "atribūcijas verbiem — skaidrs atribuēts atstāsts, 0,65.",
             0.65, None),
    724970: ("atribūcija redakcionālā avotā skaidra, stance saglabā «pieļauj/varētu»; pirmavots ir "
             "TV3 «Nekā personīga» sižets, nav pārbaudīts, tāpēc confidence paliek 0,6.",
             None, None),
    724976: ("paša tvīts, burtisks citāts, stance saglabā «tieši nepasakot»; Kulberga izteikums, uz "
             "ko tas atbild, korpusā nav atrasts — confidence paliek 0,6.",
             None, None),
    718094: ("vēstules esamību 27.09. apstiprina EK («carefully assessing», saņemšana apstiprināta) un "
             "līdzparakstītājs Lietuvas aizsardzības ministrs Kauns publiski atklāja tās detaļas "
             "(https://balticnews.com/ec-says-it-is-carefully-assessing-baltic-request-for-e500-million-in-drone-defences/) — 0,65.",
             0.65, None),
}


def q(s):
    return "NULL" if s is None else "'" + str(s).replace("'", "''") + "'"


def main():
    db = get_db()
    rows = {r["id"]: r for r in db.execute(
        f"SELECT id, opponent_id, topic, stance, confidence, reasoning FROM claims "
        f"WHERE id IN ({','.join('?' * len(FIXES))})", list(FIXES)).fetchall()}
    assert set(rows) == set(FIXES), set(FIXES) - set(rows)
    for cid, r in rows.items():
        assert "NEEDS_REVIEW" in r["reasoning"], cid

    if "--rollback" in sys.argv:
        out = [
            "-- ROLLBACK: NEEDS_REVIEW triāža 2026-09-27 (7 pozīcijas)",
            "-- Atceļ: scripts/fix_needs_review_triage_2026-09-27.py --apply — NEEDS_REVIEW marķieris",
            "--   aizstāts ar 'Izvērtēts 2026-09-27: ...', confidence mainīts 5 rindām, #724951 stance sašaurināts.",
            "-- Piemērots: 2026-09-27",
            "-- Pēc šī rollback OBLIGĀTI: .venv/Scripts/python.exe scripts/reembed_claims.py 724951",
            "--   (embedding = topic + stance). review_status atvasina trigeris.",
            f"-- Skartie id: {', '.join(map(str, FIXES))}",
            "",
            "BEGIN;",
        ]
        for cid in FIXES:
            r = rows[cid]
            out.append(f"-- #{cid} (opponent_id={r['opponent_id']}, topic={r['topic']})")
            out.append(f"UPDATE claims SET stance = {q(r['stance'])}, confidence = {r['confidence']}, "
                       f"reasoning = {q(r['reasoning'])} WHERE id = {cid};")
        out += ["COMMIT;", ""]
        ROLLBACK.write_text("\n".join(out), encoding="utf-8")
        print(f"rollback: {ROLLBACK} ({len(FIXES)} rindas)")
        return

    if "--apply" in sys.argv:
        assert ROLLBACK.exists(), "vispirms --rollback"
        with db:
            for cid, (clause, conf, stance) in FIXES.items():
                r = rows[cid]
                rest = r["reasoning"].replace("NEEDS_REVIEW:", "").replace("NEEDS_REVIEW", "").strip()
                reasoning = f"Izvērtēts 2026-09-27: {clause} Sākotnējā piezīme: {rest}"
                assert "NEEDS_REVIEW" not in reasoning
                db.execute("UPDATE claims SET reasoning=?, confidence=?, stance=? WHERE id=?",
                           (reasoning, conf if conf is not None else r["confidence"],
                            stance if stance is not None else r["stance"], cid))
        got = db.execute(
            f"SELECT id, review_status, confidence FROM claims WHERE id IN ({','.join('?' * len(FIXES))})",
            list(FIXES)).fetchall()
        ok = sum(1 for g in got if g["review_status"] == "reviewed")
        for g in got:
            print(dict(g))
        print(f"pārbaudīti {len(got)}, reviewed {ok}")
        assert ok == len(FIXES)


if __name__ == "__main__":
    main()
