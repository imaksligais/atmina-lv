"""Sēžu manifesta ielasītājs — sēdes UN tā ģenerēšanas datums vienā elpas vilcienā.

`data/saeima_backfill_sessions.json` ir kalendāra momentuzņēmuma atvasinājums:
to raksta `scripts/_p3_extract_sessions_2026-05-26.py`, un to lasa parity
audits + abi P3 backfill skripti. Fails ir tikai tik patiess, cik svaigs ir
momentuzņēmums, no kura tas ģenerēts — bet līdz 2026-09-02 pats fails to
nepateica, un neviens lasītājs to nevarēja pajautāt.

Kas notika bez šī (2026-09-02): manifests pēdējoreiz ģenerēts 2026-08-01;
2026-08-20 sēdei bija divi sēžu UUID, un manifestā to nebija. `--dates
2026-08-20` nofiltrēja audita sarakstu līdz tukšam, un rīks izdrukāja
„trūkst 0" — kamēr DB tiešām trūka 25 balsojumu.

## Kāpēc apvalks, ne blakusfails

Divas formas bija iespējamas: `data/saeima_backfill_sessions.meta.json` blakus
vai apvalka objekts pašā failā. Izvēlēts APVALKS, jo blakusfails var
desinhronizēties — svaigs `.meta.json` blakus vecam manifestam dotu ZAĻU
gaismu tieši tajā gadījumā, kura dēļ vārti pastāv. Apvalkā datums un dati ir
viens ieraksts: pārrakstīt vienu, neaiztiekot otru, nav iespējams.

Jaunā forma:
    {"generated_at": "2026-09-02", "sessions": [ {...}, ... ]}

Vecā forma (kails saraksts) joprojām tiek nolasīta, lai neviens lasītājs
nesabruktu, bet tā atgriež `generated_at=None` — un auditam tas ir STOP, nevis
pieņēmums, ka viss kārtībā.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MANIFEST_PATH = REPO_ROOT / "data" / "saeima_backfill_sessions.json"


def load_manifest(path: Path | str | None = None) -> tuple[list[dict], str | None]:
    """Atgriež `(sessions, generated_at)`.

    `generated_at` ir ISO datums (`YYYY-MM-DD`) vai `None`, ja manifests ir
    vecajā (kailā saraksta) formā. `None` NAV „svaigs" — izsaucējam tas
    jāapstrādā kā nezināms vecums.
    """
    p = Path(path) if path is not None else MANIFEST_PATH
    payload = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload, None
    return list(payload.get("sessions") or []), payload.get("generated_at")
