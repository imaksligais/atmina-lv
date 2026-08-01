"""HTTP layer for VID amatpersonu deklarāciju portāls.

Spec: docs/superpowers/specs/2026-05-02-vad-deklaracijas-design.md § 3, § 6.2
F12 update (2026-05-02): SEARCH_THROTTLE_S 5s → 10s after empirical timeout.

Endpoints:
  POST /VAD/Data?Name=X&Surname=Y&From=N → HTML fragment ar tabulu
  GET  /VAD/VADData (Cookie: VADData=<UUID>) → pilns detail HTML

Throttle: 10s starp politiķiem (search), 3s starp deklarācijām (detail).
Retries: max 2 ar exp backoff (5s, 30s) tikai 5xx un 429. 403/404 fail loud.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from typing import Callable
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

BASE_URL = "https://www6.vid.gov.lv"
SEARCH_URL = f"{BASE_URL}/VAD/Data"
DETAIL_URL = f"{BASE_URL}/VAD/VADData"
PREFLIGHT_URL = f"{BASE_URL}/ReqCode?check=true&pageName=VADList"

USER_AGENT = "atmina.lv/1.0 (kontakts@atmina.lv)"
SEARCH_THROTTLE_S = 10.0  # F12: was 5s; bumped after sub-second 2nd search timed out
DETAIL_THROTTLE_S = 3.0
PAGE_SAFETY_BOUND = 200
# Homonīmu robs (BACKLOG [FIX] Inga Bērziņa): kad meklēšana atgriež simtiem
# cita cilvēka rindu (368× "Vidzemes slimnīca" homonīms), politiķa reālās
# Saeimas deklarācijas var atrasties AIZ PAGE_SAFETY_BOUND. Ja caller dod
# accept_row predikātu (no disambig hints), turpinām lapot līdz šim cietajam
# griestiem, KAMĒR nesen redzētajās lapās joprojām parādās match rinda — citādi
# apstājamies pie parastā bound. Cietais griests sargā pret runaway loop'iem.
PAGE_HARD_BOUND = 800
# Cik secīgas lapas BEZ neviena match rindas pieļaujam, pirms agrīni apstājamies
# (homonīmu siena starp lapām, kurās ir politiķa reālie ieraksti).
_MATCH_GAP_PAGES = 4

_HREF_VAD_RE = re.compile(r"HrefVad\(\s*'([^']+)'\s*,\s*'([^']+)'\s*\)")


@dataclass
class SearchResultRow:
    vad_uuid: str
    declaration_type: str  # "Kārtējā gada deklarācija - par 2024. gadu"
    is_legacy: bool         # True kad type "0" (pre-2010 /VAD2002Data)
    institution: str        # "Latvijas Republikas Saeima"
    position_title: str     # "Saeimas deputāts"


class VadClient:
    """Single-session client. Throttle is on the caller's responsibility (sleep
    between politicians). Cookies managed explicitly per detail fetch — we do
    NOT rely on session jar for VADData to avoid cross-politiķu contamination.
    """

    def __init__(self, *, timeout: float = 60.0, throttle: bool = True):
        self._client = httpx.Client(
            timeout=timeout,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        )
        self._throttle = throttle
        self._last_search_at: float = 0.0
        self._last_detail_at: float = 0.0
        self._session_initialized = False

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self._client.close()

    def close(self):
        self._client.close()

    def reset_session(self):
        """Force next call to re-bootstrap session (visit /VAD).

        Phase 1.5 F14 — VID anti-scrape invalidates UUID nonces pēc N rapid
        sequential requests; orchestrator var izmantot reset + re-search lai
        dabūtu svaigus UUIDs un retry parse-failed detail fetch.
        """
        self._session_initialized = False
        self._client.cookies.clear()

    def _ensure_session(self):
        if not self._session_initialized:
            # Visit /VAD to obtain ASP.NET_SessionId cookie before any search
            self._client.get(f"{BASE_URL}/VAD")
            self._session_initialized = True

    def search(
        self,
        given_name: str,
        family_name: str,
        *,
        accept_row: Callable[[SearchResultRow], bool] | None = None,
    ) -> list[SearchResultRow]:
        """Search portal by Vārds + Uzvārds. Returns ALL deklarācijas across all
        amatu loma rindām. Loops From= until empty or a page bound.

        accept_row — opcionāls predikāts (parasti no disambig hints), kas atzīmē,
        vai rinda pieder mūsu politiķim. Kad dots, lapošana drīkst iet PĀRI
        PAGE_SAFETY_BOUND līdz PAGE_HARD_BOUND, lai politiķa reālās deklarācijas,
        kuras homonīms iebīda aiz 200. rindas, vairs netiktu nogrieztas (BACKLOG
        [FIX] Inga Bērziņa: 368 "Vidzemes slimnīca" rindas pirms viņas Saeimas
        ierakstiem). Apstāšanās:
          - Pirms PIRMĀ match — lapojam līdz hard bound (vadāmies pēc tā, ka
            sākotnējā homonīmu siena var būt gara; Bērziņai ~8 lapas).
          - Pēc pirmā match — ja `_MATCH_GAP_PAGES` secīgas lapas bez match,
            agrīni apstājamies (politiķa klasteris izsmelts; atlikušais ir
            cita homonīma aste).
        Bez predikāta uzvedība nemainās — apstājamies pie PAGE_SAFETY_BOUND.
        """
        self._ensure_session()
        all_rows: list[SearchResultRow] = []
        offset = 0
        seen_match = False
        pages_since_match = 0
        # Wrap-detekcija (2026-06-11, Inga Bērziņa live-probe): VID From= AIZ
        # rezultātu kopas beigām neatgriež tukšu lapu — tas CIKLISKI atkārto
        # to pašu kopu (~194 unikālas rindas atkārtojās pie 950/1144/1338/…).
        # Bez šīs pārbaudes lapošana iet līdz PAGE_HARD_BOUND un, tā kā cikla
        # garums (~4 lapas) var būt īsāks par _MATCH_GAP_PAGES logu, gap-stop
        # nekad nenostrādā. Rinda, kuras identitāte jau redzēta, ir wrap signāls.
        seen_keys: set[tuple[str, str, str]] = set()
        while True:
            self._maybe_sleep_search()
            html = self._post_search(given_name, family_name, offset)
            self._last_search_at = time.monotonic()
            rows = self._parse_search_html(html)
            if not rows:
                break
            fresh = []
            for r in rows:
                key = (r.vad_uuid, r.declaration_type, r.position_title)
                if key not in seen_keys:
                    seen_keys.add(key)
                    fresh.append(r)
            all_rows.extend(fresh)
            if not fresh:
                log.warning(
                    "vad-search paginācija apgriezās ciklā pie offset %d "
                    "(%s %s) — pārtraucu (kopā %d unikālas rindas)",
                    offset, given_name, family_name, len(all_rows),
                )
                break
            offset += len(rows)

            if accept_row is not None and any(accept_row(r) for r in rows):
                seen_match = True
                pages_since_match = 0
            else:
                pages_since_match += 1

            if offset >= PAGE_SAFETY_BOUND:
                # Parastais griests — ja nav disambig predikāta, apstājamies šeit.
                if accept_row is None:
                    log.warning("vad-search safety bound %d hit for %s %s",
                                PAGE_SAFETY_BOUND, given_name, family_name)
                    break
                # Institūcijas-aware turpināšana: cietais griests vienmēr apstāj.
                if offset >= PAGE_HARD_BOUND:
                    log.warning("vad-search hard bound %d hit for %s %s",
                                PAGE_HARD_BOUND, given_name, family_name)
                    break
                # Tikai PĒC pirmā match ļaujam gap-stopam pārtraukt — citādi
                # leading homonīmu siena (Bērziņai pirms Saeimas) mūs apturētu
                # pirms reālo deklarāciju sasniegšanas.
                if seen_match and pages_since_match >= _MATCH_GAP_PAGES:
                    log.warning(
                        "vad-search bound %d pārsniegts, %d lapas bez match pēc "
                        "klastera (%s %s) — pārtraucu",
                        PAGE_SAFETY_BOUND, pages_since_match,
                        given_name, family_name,
                    )
                    break

            if len(rows) < 50:
                break
        return all_rows

    def fetch_detail(self, vad_uuid: str) -> str:
        """Fetch detail HTML for a single declaration UUID. Returns full HTML.

        Raises httpx.HTTPStatusError on 4xx/5xx; the orchestrator decides retry.
        """
        self._ensure_session()
        self._maybe_sleep_detail()
        # Set VADData cookie in jar (portal validates session-bound nonce);
        # explicit set/unset around fetch keeps state predictable across calls.
        self._client.cookies.set("VADData", vad_uuid, domain="www6.vid.gov.lv", path="/")
        try:
            resp = self._client.get(DETAIL_URL)
            self._last_detail_at = time.monotonic()
            resp.raise_for_status()
            return resp.text
        finally:
            self._client.cookies.delete("VADData", domain="www6.vid.gov.lv", path="/")

    def preflight(self) -> None:
        """Pre-flight ReqCode call (drošības margināls — skat. spec § 3.3)."""
        self._client.get(PREFLIGHT_URL, headers={"X-Requested-With": "XMLHttpRequest"})

    def _post_search(self, given: str, family: str, offset: int) -> str:
        body = f"Name={quote_plus(given)}&Surname={quote_plus(family)}&From={offset}"
        resp = self._client.post(
            SEARCH_URL,
            content=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": f"{BASE_URL}/VAD",
                "Accept": "text/html, */*; q=0.01",
            },
        )
        resp.raise_for_status()
        return resp.text

    def _parse_search_html(self, html: str) -> list[SearchResultRow]:
        soup = BeautifulSoup(html, "html.parser")
        out: list[SearchResultRow] = []
        current_inst = ""
        current_pos = ""
        for tr in soup.find_all("tr"):
            cells = tr.find_all(["td", "th"])
            if len(cells) >= 3:
                second = cells[1].get_text("\n", strip=True)
                if "\n" in second:
                    current_pos, current_inst = second.split("\n", 1)
                else:
                    current_pos, current_inst = second, ""
                links_cell = cells[2]
            elif len(cells) == 2:
                second = cells[0].get_text("\n", strip=True)
                if "\n" in second:
                    current_pos, current_inst = second.split("\n", 1)
                else:
                    current_pos, current_inst = second, ""
                links_cell = cells[1]
            else:
                continue
            for a in links_cell.find_all("a"):
                onclick = a.get("onclick", "")
                m = _HREF_VAD_RE.search(onclick)
                if not m:
                    continue
                uuid, type_code = m.group(1), m.group(2)
                out.append(SearchResultRow(
                    vad_uuid=uuid,
                    declaration_type=a.get_text(" ", strip=True),
                    is_legacy=(type_code != "2"),
                    institution=current_inst.strip(),
                    position_title=current_pos.strip(),
                ))
        return out

    def _maybe_sleep_search(self):
        if not self._throttle or self._last_search_at == 0.0:
            return
        elapsed = time.monotonic() - self._last_search_at
        if elapsed < SEARCH_THROTTLE_S:
            time.sleep(SEARCH_THROTTLE_S - elapsed)

    def _maybe_sleep_detail(self):
        if not self._throttle or self._last_detail_at == 0.0:
            return
        elapsed = time.monotonic() - self._last_detail_at
        if elapsed < DETAIL_THROTTLE_S:
            time.sleep(DETAIL_THROTTLE_S - elapsed)
