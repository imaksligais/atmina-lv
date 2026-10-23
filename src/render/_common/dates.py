"""``_common`` datumu / formāta lapu-funkcijas.

Izgriezts no vienfaila ``src/render/_common.py`` 2026-09-05 (plāna 5.8).
Audita § 1.3 klasteris "Date/format leaves" — bez DB, bez māsu-moduļiem.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Optional
from urllib.parse import urlparse

from src.db import today_lv, utc_to_lv
from src.render._common.constants import _PARTY_LOWERCASE_WORDS

def trailing_days_cutoff(days: int = 7) -> str:
    """ISO date that opens a window of exactly ``days`` calendar days ending
    TODAY (LV), inclusive — for ``col >= cutoff`` filters.

    ``today - timedelta(days=7)`` with ``>=`` spans EIGHT calendar days: the
    landing «/ 7d» and «Visaktīvākie (7 dienās)» counted one day too many
    until 2026-09-28. The contradiction sparkline's ``series[-7:]`` is the
    same 7-day window (today-6 … today).
    """
    return (today_lv() - timedelta(days=days - 1)).isoformat()


def _confidence_tier(c: float | None) -> str:
    """Map a numeric confidence (0.0–1.0) to the Pozīcijas V2 tier label.
    None falls through to 'merena' — conservative default for any future
    rows where extraction didn't record confidence."""
    if c is None:
        return "merena"
    if c >= 0.9:
        return "augsta"
    if c >= 0.75:
        return "laba"
    return "merena"


def _normalize_date(raw: str) -> str:
    """Normalize '26.03.2026' or '2026-03-26 ...' to 'YYYY-MM-DD'."""
    d = (raw or "")[:10]
    if "." in d and len(d) == 10:
        parts = d.split(".")
        if len(parts) == 3:
            return f"{parts[2]}-{parts[1]}-{parts[0]}"
    return d


def _date_sort_key(date_str: str | None) -> str:
    """Normalize date strings for sorting: handles both ISO (2026-04-01) and EU (01.04.2026) formats."""
    if not date_str:
        return ""
    s = date_str.strip()
    # EU format: dd.mm.yyyy
    if len(s) >= 10 and s[2] == "." and s[5] == ".":
        return s[6:10] + "-" + s[3:5] + "-" + s[0:2] + s[10:]
    return s


def _format_tweet_time(published_at: Optional[str], scraped_at: Optional[str]) -> str:
    """Return 'YYYY-MM-DD HH:MM' for the X feed.

    Prefers published_at (actual tweet post time, UTC ISO from twikit) converted
    to Latvia local time. Falls back to scraped_at (already LV-local) when the
    published_at is missing or unparseable. Without this, every tweet shows the
    scrape-run HH:MM instead of when it was posted.
    """
    if published_at:
        try:
            dt = datetime.fromisoformat(published_at)
            if dt.tzinfo is not None:
                dt = utc_to_lv(dt)
            return dt.strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            pass
    return (scraped_at or "")[:16]


def _titlecase_party_name(name: str) -> str:
    """Capitalize first letter of each word, lowercasing the rest.
    Conjunctions like 'un' stay lowercase unless they're the first word.
    '/' is also a word boundary — joint lists ("Suverēnā vara/Jaunlatvieši")
    otherwise come out as "Vara/jaunlatvieši"."""
    words = name.split(" ")
    out = []
    for i, w in enumerate(words):
        if not w:
            out.append(w)
            continue
        segs = []
        for j, seg in enumerate(w.split("/")):
            if not seg:
                segs.append(seg)
                continue
            ls = seg.lower()
            stripped = ls.rstrip(",.!?;:")
            if (i > 0 or j > 0) and stripped in _PARTY_LOWERCASE_WORDS:
                segs.append(ls)
            else:
                segs.append(ls[0].upper() + ls[1:])
        out.append("/".join(segs))
    return " ".join(out)


def _initials_from_name(name: str | None) -> str:
    """Two-letter initials for avatar chip; '?' fallback."""
    if not name:
        return "?"
    parts = [p for p in name.split() if p]
    if not parts:
        return "?"
    return "".join(p[0].upper() for p in parts[:2])


def _delta_days(old_date: str | None, new_date: str | None) -> int | None:
    """Absolute day diff between two ISO dates; None if either missing/malformed."""
    if not old_date or not new_date:
        return None
    try:
        d_old = date.fromisoformat(old_date[:10])
        d_new = date.fromisoformat(new_date[:10])
        return abs((d_new - d_old).days)
    except (ValueError, TypeError):
        return None


# Datums, pēc kura nāk beigas vai laiks («T09:30», « 09:30:00», «T7:53:00+03:00» —
# viencipara stunda ir dzīvajos documents.published_at), ar/bez laika joslas.
_ISO_DATE_PREFIX = re.compile(r"(\d{4})-(\d{2})-(\d{2})(?=$|[T ]\d{1,2}:\d{2})")
# ISO datums brīvā tekstā (virsrakstos «Dienas analīze — 2026-10-20»).
_ISO_DATE_IN_TEXT = re.compile(r"(?<!\d)\d{4}-\d{2}-\d{2}(?!\d)")
_LV_FULL_DATE = re.compile(r"\d{2}\.\d{2}\.\d{4}")
# Nedēļas pārskata periods (src/render/blog.py display_date): «A — B».
_ISO_RANGE = re.compile(r"(\d{4}-\d{2}-\d{2}) — (\d{4}-\d{2}-\d{2})")


def lv_date(value: str | date | None) -> str:
    """Redzamais datums `DD.MM.YYYY` — vienīgais formatētājs (Jinja filtrs `lv_date`).

    Līgums (tests/test_lv_date.py): `None`/`""` → `""`; ISO datums vai
    datums+laiks (`T`/atstarpe, ar laika joslu vai bez) → uzrakstītā datuma daļa
    `DD.MM.YYYY` (bez laika joslas pārrēķina — pulksteni izvēlas izsaucējs, T17);
    `date`/`datetime` → `DD.MM.YYYY`; nedēļas periods «A — B» → abi gali;
    viss cits (ne-ISO teksts, jau latvisks datums, neeksistējošs datums,
    datums ar tekstu aiz atstarpes) → nemainīts teksts.
    """
    if value is None or value == "":
        return ""
    if isinstance(value, date):  # arī datetime (apakšklase)
        return value.strftime("%d.%m.%Y")
    s = str(value)
    rng = _ISO_RANGE.fullmatch(s)
    if rng:
        a, b = lv_date(rng[1]), lv_date(rng[2])
        return f"{a} — {b}" if a != rng[1] and b != rng[2] else s
    m = _ISO_DATE_PREFIX.match(s)
    if not m:
        return s
    try:
        d = date(int(m[1]), int(m[2]), int(m[3]))
    except ValueError:
        return s
    return d.strftime("%d.%m.%Y")


def lv_date_short(value: str | date | None) -> str:
    """Šaura kolonna (X plūsma): `DD.MM.` — tas pats līgums kā `lv_date`.

    Ja `lv_date` ievadi atpazīst kā datumu → `DD.MM.`; citādi (periods, ne-ISO
    teksts, tukšs) → tieši `lv_date` rezultāts, nekas netiek griezts.
    """
    full = lv_date(value)
    return full[:6] if _LV_FULL_DATE.fullmatch(full) else full


def lv_dates_in_text(text: str | None) -> str:
    """Katrs ISO datums tekstā → `DD.MM.YYYY` (`lv_date`); pārējais teksts nemainās.

    Mūsu ģenerētiem virsrakstiem («Dienas analīze — 2026-10-20», nedēļas
    «… — 2026-10-05 līdz 2026-10-11»). NE prozai un NE `claims.quote`.
    Neeksistējošs datums (`2026-13-45`) paliek kā rakstīts.
    """
    if not text:
        return ""
    return _ISO_DATE_IN_TEXT.sub(lambda m: lv_date(m[0]), str(text))


_LV_MONTHS_LOC = (
    "janvārī", "februārī", "martā", "aprīlī", "maijā", "jūnijā",
    "jūlijā", "augustā", "septembrī", "oktobrī", "novembrī", "decembrī",
)


def lv_date_locative(iso: str | None, with_year: bool = False) -> str:
    """'2026-10-06' → «6. oktobrī» (ar ``with_year`` — «2026. gada 6. oktobrī»;
    «6. oktobrī, 2026» ir kalks, operatora lēmums 2026-10-21)."""
    try:
        d = date.fromisoformat((iso or "")[:10])
    except ValueError:
        return ""
    label = f"{d.day}. {_LV_MONTHS_LOC[d.month - 1]}"
    return f"{d.year}. gada {label}" if with_year else label


def _lv_count(n: int, one: str, many: str) -> str:
    """LV skaitļa forma: 1, 21, 101 → vienskaitlis; 11 → daudzskaitlis."""
    return f"{n} {one if n % 10 == 1 and n % 100 != 11 else many}"


def lv_gap_label(days: int | None) -> str:
    """Starpība starp datumiem: «7 dienas», «21 diena»; no 60 dienām — mēneši."""
    if days is None:
        return ""
    if days == 0:
        return "tajā pašā dienā"
    if days < 60:
        return _lv_count(days, "diena", "dienas")
    return _lv_count(days // 30, "mēnesis", "mēneši")


def _domain_from_url(url: str | None) -> str | None:
    """Hostname with leading 'www.' stripped; None on empty/invalid."""
    if not url:
        return None
    try:
        netloc = urlparse(url).netloc
    except (ValueError, TypeError):
        return None
    if not netloc:
        return None
    return netloc.removeprefix("www.")


def _domain_label(source_domain: str | None, source_url: str | None) -> str | None:
    """Izdevēja etiķete claim rindai: ``documents.source_domain`` ir noteicošais.

    Hosts URL-ā ne vienmēr ir izdevējs. TVNET raksti daļēji tiek pasniegti no
    partnera hosta ``pmo.ee`` (2 125 doki, 176 pozīcijas, mērīts 2026-09-06) —
    ievākšanas brīdī ``documents.source_domain`` tiem visiem ir ``tvnet.lv`` un
    tas ir pareizs, bet virsmas etiķeti atvasināja no URL, tāpēc lasītājs redzēja
    ``pmo.ee``. URL netiek migrēts — tas ietilpst ``store_claim()`` idempotences
    trijniekā —, tāpēc labojums dzīvo tikai etiķetes atvasināšanā.

    Atkāpšanās uz URL hostu paliek rindām bez dokumenta (``saeima_vote`` claims
    glabā ``document_id`` NULL) un vēsturiskām rindām bez ``source_domain``.
    """
    if source_domain:
        return source_domain.removeprefix("www.")
    return _domain_from_url(source_url)
