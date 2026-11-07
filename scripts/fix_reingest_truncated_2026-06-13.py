"""Re-ingest resolution for 5 truncated-source NEEDS_REVIEW claims (2026-06-13).

Full articles fetched + verified (workflow wf_8843f299): all 5 verdicts CONFIRM/REFINE,
zero REVERSE — the truncated ledes were accurate, just thin. We refine each stance to the
verified full-body position and de-flag (NEEDS_REVIEW -> REVIEWED). #527881 Rokpelnis came
back diacritic-degraded from tvnet/pmo.ee, so its stance is a clean hand-rewrite from the body.

Touches ONLY claims.stance (5) + claims.reasoning (5 de-flag). Every new stance is diacritic-
validated before write. documents.content is intentionally NOT changed (cache; the claim is
authoritative and the source_url already points to the full article). Paired rollback regenerated.
Dry-run by default; --apply to write.
"""
import sys, os
sys.path.insert(0, os.getcwd())
import sqlite3
from src.quality import validate_lv_diacritics

DB = 'data/atmina.db'
APPLY = '--apply' in sys.argv

STANCE = {
    531904: 'Sarunās par ES daudzgadu budžetu 2028.–2034. gadam Braže iestājas, lai budžets atspoguļotu jauno drošības situāciju Eiropā: paredz pietiekamu finansējumu drošībai un aizsardzībai, mērķētu papildu atbalstu dalībvalstīm pie ES austrumu robežas (kuras robežojas ar Krieviju un Baltkrieviju), finansējumu stratēģiskai infrastruktūrai, tostarp "Rail Baltica" un militārajai mobilitātei, kā arī taisnīgu lauksaimniecības tiešmaksājumu izlīdzināšanu.',
    527902: 'Uzskata, ka AST jānodrošina stratēģiskas avārijas rezerves infrastruktūras bojājumu novēršanai, tostarp mobilo balstu un mobilo apakšstaciju iegāde ātrākai elektroapgādes atjaunošanai pēc vētrām un ārkārtas notikumiem; kā prioritāti izvirza Baltijas valstu ciešāku sadarbību kopīgu energosistēmas rezervju veidošanā un kritiskās infrastruktūras aizsardzībā, piesaistot ES finansējumu.',
    527893: 'Atzīst, ka daudzgadu budžetā 2027. gadam nav paredzēts finansējums Latvijas dalībai Eiropas Kosmosa aģentūrā, un norāda, ka dalība jāturpina, bet nepieciešamie vairāk nekā seši miljoni eiro jāmeklē; pauž pārsteigumu, ieraugot, ka līdzdalības maksājuma ailītē nav līdzekļu.',
    527890: 'Uzskata, ka "Rail Baltica" Baltijas valstīm jāīsteno kopīgi, nevis atrauti, un pauž gatavību projektu pabeigt 2030. gadā, ja saskan visi nosacījumi; šaubās, vai Igaunijai izdosies sasniegt savu 2030. gada mērķi. Apgalvo, ka viņam ir ideja projekta lētākai īstenošanai, ko vēl nepublisko un pārrunās ar ekspertiem, bet termiņus un finansējumu drīzumā skars sarunā ar Eiropas Komisijas prezidenti Urzulu fon der Leienu, mērķējot uz izdevīgāko scenāriju ar samazinātām izmaksām.',
    527881: 'Aizstāv e-cigarešu un aromatizēto šķidrumu aizliegumus kā līdzsvaru starp sabiedrības veselību un nodokļu ieņēmumiem; atzīst, ka ierobežojumi likumsakarīgi veicina nelegālo apriti un ka kontrabandu pilnībā izskaust nebūs iespējams, taču uzstāj, ka atbildīgajām iestādēm pret to jācīnās, nevis jāsūdzas; ietekmi uz sabiedrības veselību vērtēs pēc tam, kad ierobežojumi būs darbojušies samērīgu laiku.',
}


def q(s):
    return 'NULL' if s is None else "'" + s.replace("'", "''") + "'"


db = sqlite3.connect(DB)
db.row_factory = sqlite3.Row

# validate diacritics first — abort before any write if any stance is degraded
for cid, st in STANCE.items():
    ok, reason = validate_lv_diacritics(st)
    if not ok:
        print(f'ABORT: stance #{cid} fails diacritic gate: {reason}')
        sys.exit(1)

roll = ["-- Rollback: reverš scripts/fix_reingest_truncated_2026-06-13.py",
        "-- Atjauno 5 claims stance + reasoning uz pirms-re-ingest vērtībām. Apply date: 2026-06-13.", ""]
new_reason = {}
for cid in STANCE:
    r = db.execute('SELECT stance, reasoning FROM claims WHERE id=?', (cid,)).fetchone()
    new_reason[cid] = (r['reasoning'] or '').replace('NEEDS_REVIEW', 'REVIEWED 2026-06-13 (re-ingested, pilns teksts apstiprina)')
    roll.append(f"UPDATE claims SET stance={q(r['stance'])}, reasoning={q(r['reasoning'])} WHERE id={cid};")

with open('data/rollback_reingest_truncated_2026-06-13.sql', 'w', encoding='utf-8') as f:
    f.write('\n'.join(roll) + '\n')

still = db.execute("SELECT COUNT(*) FROM claims c JOIN tracked_politicians t ON t.id=c.opponent_id "
                   "WHERE c.reasoning LIKE '%NEEDS_REVIEW%' AND c.claim_type='position' "
                   "AND t.relationship_type!='inactive'").fetchone()[0]
print(f'pre: {still} active NEEDS_REVIEW | refine {len(STANCE)} stances + de-flag | diacritics OK | rollback written')
if not APPLY:
    print('[DRY-RUN]')
    sys.exit(0)
for cid, st in STANCE.items():
    db.execute('UPDATE claims SET stance=?, reasoning=? WHERE id=?', (st, new_reason[cid], cid))
db.commit()
after = db.execute("SELECT COUNT(*) FROM claims c JOIN tracked_politicians t ON t.id=c.opponent_id "
                   "WHERE c.reasoning LIKE '%NEEDS_REVIEW%' AND c.claim_type='position' "
                   "AND t.relationship_type!='inactive'").fetchone()[0]
print(f'APPLIED. active NEEDS_REVIEW {still} -> {after} (expected 0).')
