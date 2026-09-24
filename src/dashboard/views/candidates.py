"""Pretrunu KANDIDĀTU paneļa skats — noraidītie kandidāti no medību logiem.

Kāpēc šis panelis eksistē (operatora lūgums 2026-09-04): `store_contradiction()`
raksta tikai ATRADUMUS. Kandidāti, ko `@contradiction-hunter` izvērtēja un
noraidīja, līdz šim dzīvoja vienīgi apakšaģenta atskaitē — tā aiziet
orkestratoram un pazūd līdz ar sesiju. 2026-09-04 tā pazuda seši pilnībā
izvērtēti kandidāti ar pamatojumu, tostarp viens (Jurēvics / zelta vīzas), kas
bija tuvākais reālajam atradumam visā dienā.

**Kāpēc `logs.details`, nevis jauna tabula.** `log_action('contradiction_hunt')`
jau tagad ir obligāts rutīnas solis, kas iet KATRU dienu, arī nulles ražas
dienā — tieši tas atšķir godīgu nulli no «netika palaists» (`src/routine.py`
`_check_contradictions` to lasa). Piekabinot kandidātus šim izsaukumam, tvērums
manto jau ieviestu, pārbaudītu ieradumu. Atsevišķa tabula būtu JAUNS solis, un
šī repo vēsture saka, ka izvēles izskata soļus zem slodzes klusi izlaiž (T11).

**Zināmā šī nesēja robeža:** `logs` ir liela tabula un `details` ir JSON, tāpēc
retrospektīvs griezums («visi kandidāti par Jurēvicu kopš jūnija») ir skenējums,
ne vaicājums. Ja tāds lasījums kļūst par ikdienu, tas ir arguments pārcelt šo uz
`contradiction_candidates` tabulu — sk. `backlog/agenti-pipeline.md`.

**Šis panelis ir localhost-only pēc uzbūves.** Noraidīts kandidāts ir
nepierādīts apgalvojums par nosauktu cilvēku: `serve.py` klausās tikai
127.0.0.1, tāpēc virsma ir privāta pēc konstrukcijas, nevis tāpēc, ka kāds
atceras to izslēgt. Publiskajā renderī šai atslēgai lasītāja NAV, un
`tests/test_dashboard_candidates.py` to notur.
"""
from __future__ import annotations

import json
import time
from datetime import date as _date, timedelta
from typing import Any

from src.db import get_db, today_lv

_CACHE_TTL_SECONDS = 30
_CACHE: dict[str, Any] = {"key": None, "ts": None, "result": None}

# Minimālais lauku komplekts, bez kura ieraksts nav izsekojams. `claim_new` un
# `why` ir obligāti: bez claim id operators nevar pārbaudīt avotu, un bez
# pamatojuma rinda ir apsūdzība bez konteksta. Pārējie lauki ir papildinājumi.
_REQUIRED = ("claim_new", "why")

_KIND_LV = {
    "rhetoric_vs_vote": "retorika↔balsojums",
    "position_over_time": "pozīcija↔pozīcija",
}


def _coerce(entry: Any, day: str) -> dict[str, Any] | None:
    """Return a normalized candidate dict, or None if the entry is unusable.

    The writer is an LLM agent, so the payload WILL drift. A bad entry is
    dropped from the list but counted in `malformed` — a silent drop here
    would make a lossy day look like a clean one.
    """
    if not isinstance(entry, dict):
        return None
    if any(entry.get(k) in (None, "") for k in _REQUIRED):
        return None

    def _int_or_none(v):
        try:
            return int(v)
        except (TypeError, ValueError):
            return None

    kind = str(entry.get("kind") or "")
    return {
        "date": day,
        "claim_old": _int_or_none(entry.get("claim_old")),
        "claim_new": _int_or_none(entry.get("claim_new")),
        "politician_id": _int_or_none(entry.get("politician_id")),
        "politician": str(entry.get("politician") or "?"),
        "topic": str(entry.get("topic") or "?"),
        "kind": kind,
        "kind_lv": _KIND_LV.get(kind, kind or "—"),
        "severity_guess": str(entry.get("severity_guess") or "—"),
        "fp_class": str(entry.get("fp_class") or "—"),
        "why": str(entry["why"]),
    }


def _compute(days: int, today: str, db_path: str | None) -> dict[str, Any]:
    cutoff = (_date.fromisoformat(today) - timedelta(days=days)).isoformat()

    db = get_db(db_path) if db_path else get_db()
    try:
        rows = db.execute(
            """SELECT timestamp, details
                 FROM logs
                WHERE action = 'contradiction_hunt'
                  AND DATE(timestamp) >= ?
                ORDER BY timestamp DESC""",
            (cutoff,),
        ).fetchall()
    finally:
        db.close()

    candidates: list[dict[str, Any]] = []
    malformed = 0
    hunts_scanned = 0
    hunts_with_candidates = 0
    claims_checked = 0

    for r in rows:
        hunts_scanned += 1
        try:
            details = json.loads(r["details"]) if r["details"] else {}
        except (ValueError, TypeError):
            malformed += 1
            continue
        if not isinstance(details, dict):
            malformed += 1
            continue

        try:
            claims_checked += int(details.get("claims_checked") or 0)
        except (TypeError, ValueError):
            pass

        day = str(details.get("date") or str(r["timestamp"])[:10])
        raw = details.get("rejected_candidates")
        if raw is None:
            continue
        if not isinstance(raw, list):
            malformed += 1
            continue

        got = 0
        for entry in raw:
            coerced = _coerce(entry, day)
            if coerced is None:
                malformed += 1
                continue
            candidates.append(coerced)
            got += 1
        if got:
            hunts_with_candidates += 1

    return {
        "days": days,
        "candidates": candidates,
        "total": len(candidates),
        # Saucēji — bez tiem tukšs panelis nozīmē divas pilnīgi dažādas lietas.
        "hunts_scanned": hunts_scanned,
        "hunts_with_candidates": hunts_with_candidates,
        "claims_checked": claims_checked,
        "malformed": malformed,
        "never_ran": hunts_scanned == 0,
    }


def get_candidates_context(
    days: int = 14,
    db_path: str | None = None,
    today: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    if today is None:
        today = today_lv().isoformat()

    key = (days, today, db_path)
    now = time.time()
    if (
        not force
        and _CACHE["key"] == key
        and _CACHE["ts"] is not None
        and (now - _CACHE["ts"]) < _CACHE_TTL_SECONDS
        and _CACHE["result"] is not None
    ):
        return _CACHE["result"]

    result = _compute(days, today, db_path)
    _CACHE["key"] = key
    _CACHE["ts"] = now
    _CACHE["result"] = result
    return result
