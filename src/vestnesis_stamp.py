"""Vēstneša paraksta-pāru zīmogs — atzīmē (pid, doc) pārus, kur politiķis ir tikai parakstītājs.

Vēstnesis ir apzināti ārpus dienas ekstrakcijas rindas, bet bez atzīmes tā
`subject` pāri paliek «neizskatīti» uz visiem laikiem (2026-10-05: 872 doki;
vēsturiskais sweep no tiem ieguva 25 pozīcijas — lielākā daļa ir paraksts zem
kolektīva akta). Šis modulis atzīmē TIKAI tos pārus, kur akts ir rutīnas tipā
un politiķa uzvārds tekstā parādās tieši vienreiz, uzreiz pēc iniciāļa —
paraksta rinda, ne runa.

**Noteikums ir kopēts burtiski** no
`docs/audits/2026-10-05-backlog-sweep/vestnesis_signature_rule_eval.py` —
virsraksta regulārā izteiksme, `stem = uzvārds[:max(4, len-2)]`, «tieši viens
trāpījums» un 6 zīmju logs pirms tā. Mērīts 2026-10-05: 423 no 851 tukšajiem
Vēstneša pāriem noķerti; **0 no 21** tās dienas un **0 no 49** visu laiku
Vēstneša pozīciju pāriem noķerti kļūdaini (T16 — katrs zars pārbaudīts pret
pozīciju nesošajiem pāriem, ne pret vienprātību). Jebkurš «uzlabojums» (vārdu
robežas, `.match`, organizāciju izņēmums) šo mērījumu padara nederīgu — pirms
tam pārmēri. Uzvārds = vārda pēdējais vārds arī organizācijām; tā tas tika
mērīts.

**Raksta tikai `document_politicians.extracted_at` tam pārim** — NEKAD
`documents.reviewed_at`: MK protokolā, ko parakstījis premjers, var būt cita
ministra atsevišķais viedoklis, un dokumenta zīmogs to paslēptu.

Populācija: Vēstneša pāri ar `role='subject'`, `extracted_at IS NULL`, bez
NEVIENA claim šim (pid, doc) (stingrāk nekā mērījuma `claim_type='position'` —
drošāk), rindas politiķu tvērumā (`queue_politician_sql`). `since` sašaurina
pēc `documents.scraped_at` (LV laika kolonna, salīdzina tieši).
"""

from __future__ import annotations

import re

from src.db import get_db, now_lv
from src.scope import queue_politician_sql

ROUTINE = re.compile(
    r'^(Grozījum[is]|Grozījumi un papildinājum|Noteikumi|Par apropriācijas pārdali'
    r'|Par finanšu līdzekļu piešķiršanu|Par .{0,60}komandējumu|Par .{0,40}pienākumu izpildītāj'
    r'|Par valsts .{0,30}mantas|Par .{0,60}atvaļinājum|Likums|.{0,40}likums$'
    r'|Par .{0,40}pilsonības|Amatu konkursu ziņas)'
)
_INITIAL_BEFORE = re.compile(r'[A-ZĀČĒĢĪĶĻŅŠŪŽ]\.\s*$')


def is_signature_only(name: str, content: str, title: str) -> bool:
    """True, ja akts ir rutīnas tipā un uzvārds parādās tikai paraksta rindā."""
    if not ROUTINE.search(title or ''):
        return False
    content = content or ''
    sur = name.split()[-1]
    stem = sur[:max(4, len(sur) - 2)]
    hits = [m.start() for m in re.finditer(re.escape(stem), content)]
    if len(hits) != 1:
        return False
    i = hits[0]
    return bool(_INITIAL_BEFORE.search(content[max(0, i - 6):i]))


def candidate_pairs(db, since: str | None = None) -> list:
    """Vēstneša `subject` pāri bez ekstrakcijas un bez claim, rindas tvērumā."""
    sql = f"""SELECT dp.politician_id AS pid, tp.name, d.id AS doc_id,
                     d.title, d.content, d.scraped_at
              FROM document_politicians dp
              JOIN documents d ON d.id = dp.document_id
              JOIN tracked_politicians tp ON tp.id = dp.politician_id
              WHERE d.platform = 'vestnesis'
                AND dp.role = 'subject'
                AND dp.extracted_at IS NULL
                AND NOT EXISTS (SELECT 1 FROM claims c
                                WHERE c.opponent_id = dp.politician_id
                                  AND c.document_id = dp.document_id)
                AND {queue_politician_sql()}"""
    params: list = []
    if since:
        sql += " AND d.scraped_at >= ?"
        params.append(since)
    sql += " ORDER BY d.id, dp.politician_id"
    return db.execute(sql, params).fetchall()


def stamp_signature_only_pairs(db=None, dry_run: bool = True, since: str | None = None) -> dict:
    """Atzīmē paraksta-pārus ar `extracted_at`; atgriež ``{examined, stamped, pairs}``.

    ``examined`` = visi kandidātu pāri (saucējs), ``stamped`` = noteikumam
    atbilstošie (dry_run gadījumā — tie, kas TIKTU atzīmēti). ``pairs`` =
    ``[{pid, name, doc_id, title}]``. ``db`` pieder izsaucējam, ja padots.
    """
    own = db is None
    if own:
        db = get_db()
    try:
        rows = candidate_pairs(db, since)
        pairs = [
            {"pid": r["pid"], "name": r["name"], "doc_id": r["doc_id"], "title": r["title"]}
            for r in rows
            if is_signature_only(r["name"], r["content"], r["title"])
        ]
        if pairs and not dry_run:
            ts = now_lv()
            with db:
                for p in pairs:
                    db.execute(
                        "UPDATE document_politicians SET extracted_at = ? "
                        "WHERE document_id = ? AND politician_id = ? "
                        "AND role = 'subject' AND extracted_at IS NULL",
                        (ts, p["doc_id"], p["pid"]),
                    )
        return {"examined": len(rows), "stamped": len(pairs), "pairs": pairs}
    finally:
        if own:
            db.close()
