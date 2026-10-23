"""Atrisina NEEDS_REVIEW 743356 (Stendzenieks) un 743360 (Velps): konteksts no X vecāktvīta/citāta
(nav DB). Maina stance (+ re-embed) un reasoning. Rollback: data/rollback_review_stendz_velps_2026-10-21.sql.
--write-rollback | --apply"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")
from src.db import get_db  # noqa: E402

NEW = {
    743356: (
        "Atbildot Latvijas Zinātņu akadēmijas īstenajam loceklim Gundaram Bērziņam, kurš aicina akadēmiju "
        "Višvanatas pilsonības lietā rīkoties ātri un atbildīgi, kritizē akadēmijas «bailīgo lavierēšanu» un "
        "nekā nepateikšanu un uzskata, ka tā beigās sagraus, viņa vārdiem, «akadēmisko virsotņu tusiņu».",
        "Izvērtēts 2026-10-21: vecāktvīts x.com/gundars_berzins/status/2112810247211626873 (21.10, nav DB) — "
        "Bērziņš raksta, ka Višvanatas pilsonības lieta kaitējusi LZA reputācijai, «jārīkojas ātri un atbildīgi»; "
        "Stendzenieka «jūsu akadēmisko virsotņu tusiņu» adresēts LZA. Retoriskie jautājumi par kopsapulci un "
        "prezidenta nomaiņu stance netiek ietverti. Sākotnēji: ",
    ),
    743360: (
        "Citējot tvītu ar Krievijas ārlietu ministra Sergeja Lavrova apgalvojumu, ka Rietumi vairs nekad nebūs "
        "galvenais spēlētājs, uzskata, ka «šeit viņam ir liela daļa taisnības», jo pierādījusies Rietumu "
        "mazdūšība un vājums pret agresoriem, un norāda, ka svarīgi, vai to izlabos pāris Eiropas valstu.",
        "Izvērtēts 2026-10-21: citētais tvīts x.com/Maks_NAFO_FELLA (20.10 20:57 UTC, nav DB) — «Lavrov: The West "
        "will never again be the main player calling the tune»; «viņam» = Lavrovs. Paša vārdi, piekrišana daļēja "
        "(«liela daļa»). Sākotnēji: ",
    ),
}


def q(s):
    return "NULL" if s is None else "'" + s.replace("'", "''") + "'"


db = get_db()
cur = {cid: db.execute("SELECT stance, reasoning FROM claims WHERE id=?", (cid,)).fetchone() for cid in NEW}
assert all(r[1].startswith("NEEDS_REVIEW: ") for r in cur.values())
if "--write-rollback" in sys.argv:
    out = ["-- Forward (apply 2026-10-21): claims 743356, 743360 stance + reasoning (NEEDS_REVIEW -> Izvērtēts);",
           "--   pēc rollback: scripts/reembed_claims.py 743356 743360. Skripts: scripts/_resolve_review_stendz_velps_2026-10-21.py",
           "BEGIN;"]
    out += [f"UPDATE claims SET stance={q(s)}, reasoning={q(r)} WHERE id={cid};" for cid, (s, r) in cur.items()]
    out.append("COMMIT;")
    (ROOT / "data/rollback_review_stendz_velps_2026-10-21.sql").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("rollback rakstīts")
elif "--apply" in sys.argv:
    for cid, (stance, prefix) in NEW.items():
        db.execute("UPDATE claims SET stance=?, reasoning=? WHERE id=?",
                   (stance, prefix + cur[cid][1].removeprefix("NEEDS_REVIEW: "), cid))
    db.commit()
    print([db.execute("SELECT review_status FROM claims WHERE id=?", (c,)).fetchone()[0] for c in NEW])
