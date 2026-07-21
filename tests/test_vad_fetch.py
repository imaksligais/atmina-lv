import httpx

from src.vad.fetch import (
    PAGE_HARD_BOUND,
    PAGE_SAFETY_BOUND,
    VadClient,
)

SEARCH_HTML_2_ROWS = """
<table>
<thead><tr><th>Vārds</th><th>Amats</th><th>Saites</th></tr></thead>
<tbody>
  <tr>
    <td>AINĀRS ŠLESERS</td>
    <td>Saeimas deputāts<br>LATVIJAS REPUBLIKAS SAEIMA</td>
    <td>
      <a href="#" onclick="return HrefVad('uuid-modern-1', '2');">par 2024. gadu</a>
      <a href="#" onclick="return HrefVad('uuid-modern-2', '2');">par 2023. gadu</a>
    </td>
  </tr>
  <tr>
    <td colspan="0"></td>
    <td>Ministrs<br>Valsts kanceleja</td>
    <td>
      <a href="#" onclick="return HrefVad('uuid-legacy-1', '0');">par 2008. gadu</a>
    </td>
  </tr>
</tbody>
</table>
"""

# 50 rows in a single <tr> so the pagination loop sees a full page and fetches again.
_50_ROW_LINKS = "\n".join(
    f'<a href="#" onclick="return HrefVad(\'p-uuid-{i}\', \'2\');">par {2024 - i}. gadu</a>'
    for i in range(50)
)
SEARCH_HTML_50_ROWS = f"""
<table>
<thead><tr><th>Vārds</th><th>Amats</th><th>Saites</th></tr></thead>
<tbody>
  <tr>
    <td>POLITIĶIS</td>
    <td>Saeimas deputāts<br>LATVIJAS REPUBLIKAS SAEIMA</td>
    <td>{_50_ROW_LINKS}</td>
  </tr>
</tbody>
</table>
"""

DETAIL_HTML_STUB = "<html><body><h1>VAD detail stub</h1></body></html>"


def _make_client(handler):
    """Build VadClient ar custom MockTransport (no throttle, no live HTTP)."""
    transport = httpx.MockTransport(handler)
    c = VadClient(throttle=False)
    c._client.close()
    c._client = httpx.Client(transport=transport, headers={"User-Agent": "test"})
    c._session_initialized = True  # bypass /VAD warmup
    return c


def test_search_parses_html_to_rows():
    def handler(request):
        assert request.url.path == "/VAD/Data"
        assert request.method == "POST"
        body = request.content.decode()
        assert "Name=Ain%C4%81rs" in body
        assert "Surname=%C5%A0lesers" in body
        return httpx.Response(200, text=SEARCH_HTML_2_ROWS)
    c = _make_client(handler)
    rows = c.search("Ainārs", "Šlesers")
    assert len(rows) == 3
    assert rows[0].vad_uuid == "uuid-modern-1"
    assert rows[0].is_legacy is False
    assert rows[2].is_legacy is True
    assert rows[0].institution.upper().endswith("SAEIMA")


def test_search_pagination_stops_on_empty():
    """Full page (50 rows) → loop fetches a follow-up; empty response stops loop."""
    call_count = [0]
    def handler(request):
        call_count[0] += 1
        if call_count[0] == 1:
            return httpx.Response(200, text=SEARCH_HTML_50_ROWS)
        return httpx.Response(200, text="<table></table>")
    c = _make_client(handler)
    rows = c.search("Ainārs", "Šlesers")
    assert len(rows) == 50
    assert call_count[0] == 2


def test_fetch_detail_sets_cookie_header():
    captured_cookie = []
    def handler(request):
        captured_cookie.append(request.headers.get("cookie", ""))
        return httpx.Response(200, text=DETAIL_HTML_STUB)
    c = _make_client(handler)
    html = c.fetch_detail("abc-uuid")
    assert "VADData=abc-uuid" in captured_cookie[0]
    assert html == DETAIL_HTML_STUB


def test_fetch_detail_raises_on_404():
    def handler(request):
        return httpx.Response(404, text="not found")
    c = _make_client(handler)
    try:
        c.fetch_detail("missing")
        assert False, "expected HTTPStatusError"
    except httpx.HTTPStatusError:
        pass


def test_reset_session_clears_initialized_flag():
    """After reset_session, next call _ensure_session() must re-visit /VAD.

    Phase 1.5 F14 — anti-scrape mehanisms invalidates UUID nonces pēc N rapid
    sequential requests; reset + re-search nodrošina svaigus UUIDs.
    """
    client = VadClient(throttle=False)
    client._session_initialized = True
    client.reset_session()
    assert client._session_initialized is False


# ----- Homonīmu robs (BACKLOG [FIX] Inga Bērziņa) -----


def _homonym_page(institution: str, start_idx: int, n: int = 50) -> str:
    """50-row page, visas ar doto institution (simulē homonīmu sienu / reālos).

    50 rindas vienā <tr>, lai lapošanas cilpa redz pilnu lapu un turpina.
    """
    links = "\n".join(
        f'<a href="#" onclick="return HrefVad(\'u-{start_idx + i}\', \'2\');">par {2024 - i}. gadu</a>'
        for i in range(n)
    )
    return f"""
<table>
<thead><tr><th>Vārds</th><th>Amats</th><th>Saites</th></tr></thead>
<tbody>
  <tr>
    <td>INGA BĒRZIŅA</td>
    <td>Amats<br>{institution}</td>
    <td>{links}</td>
  </tr>
</tbody>
</table>
"""


def test_search_pages_past_safety_bound_when_accept_row_matches():
    """Homonīmu siena (Vidzemes slimnīca) iebīda reālās Saeimas rindas aiz
    PAGE_SAFETY_BOUND; ar accept_row predikātu search turpina lapot un tās ķer.

    Lapas 1-7 (350 rindas) = homonīms; 8. lapa = Saeima; 9. lapa = tukša.
    Bez accept_row search apstātos pie 200 (4. lapa) un palaistu garām Saeimu.
    """
    SAEIMA = "Latvijas Republikas Saeima"
    HOMONYM = "Vidzemes slimnīca"
    pages = [
        _homonym_page(HOMONYM, start_idx=i * 50) for i in range(7)
    ] + [
        _homonym_page(SAEIMA, start_idx=700),  # 8. lapa — reālās deklarācijas
        "<table></table>",                      # 9. lapa — tukša, apstāj
    ]
    call_count = [0]

    def handler(request):
        idx = call_count[0]
        call_count[0] += 1
        return httpx.Response(200, text=pages[idx])

    c = _make_client(handler)
    rows = c.search(
        "Inga", "Bērziņa",
        accept_row=lambda r: SAEIMA.lower() in r.institution.lower(),
    )
    # Visas 7×50 homonīmi + 50 Saeima = 400 rindas atgrieztas (filtrēšana
    # notiek augstāk declarations.py slānī; search atgriež visu).
    assert len(rows) == 400
    assert any(r.institution == SAEIMA for r in rows)
    # Lapoja pāri 200. rindas bound, jo accept_row turpināja saskaņot.
    assert PAGE_SAFETY_BOUND < 400


def test_search_stops_at_safety_bound_without_accept_row():
    """Bez accept_row uzvedība nemainās — apstājas pie PAGE_SAFETY_BOUND (200)."""
    def handler(request):
        # Pilna 50-rindu lapa ar SVAIGIEM uuid katrā lapā (citādi nostrādātu
        # wrap-detekcija, ne bound) → cilpa apstājas tikai pie bound.
        idx = handler.calls
        handler.calls += 1
        return httpx.Response(200, text=_homonym_page("Vidzemes slimnīca", idx * 50))
    handler.calls = 0

    c = _make_client(handler)
    rows = c.search("Inga", "Bērziņa")
    assert len(rows) == PAGE_SAFETY_BOUND  # 200, 4×50


def test_search_stops_when_pagination_wraps():
    """VID From= aiz rezultātu kopas beigām CIKLISKI atkārto to pašu kopu
    (2026-06-11 live-probe: ~194 unikālas rindas atkārtojās ik 950/1144/…).
    Wrap-detekcija (jau redzēta rindas identitāte) pārtrauc lapošanu un
    atgriež tikai unikālās rindas — bez tās cilpa ietu līdz PAGE_HARD_BOUND,
    jo cikla garums var būt īsāks par _MATCH_GAP_PAGES logu.
    """
    SAEIMA = "Latvijas Republikas Saeima"
    # Patiesā kopa = 2 lapas (100 rindas); 3.+ lapa atkārto 1./2. lapu pēc kārtas.
    true_pages = [
        _homonym_page("Vidzemes slimnīca", 0),
        _homonym_page(SAEIMA, 50),
    ]

    def handler(request):
        idx = handler.calls
        handler.calls += 1
        return httpx.Response(200, text=true_pages[idx % 2])
    handler.calls = 0

    c = _make_client(handler)
    rows = c.search(
        "Inga", "Bērziņa",
        accept_row=lambda r: SAEIMA.lower() in r.institution.lower(),
    )
    # Tikai unikālās 100 rindas; cilpa apstājās pirmajā pilnībā dublētajā lapā,
    # nevis skrēja līdz PAGE_HARD_BOUND.
    assert len(rows) == 100
    assert handler.calls == 3  # 2 patiesās lapas + 1 wrap lapa


def test_search_early_stops_after_match_gap_past_bound():
    """Pāri bound, ja _MATCH_GAP_PAGES secīgas lapas bez match → agrīni apstājas
    (homonīmu siena bezgalīga; nelaiž līdz hard bound velti)."""
    SAEIMA = "Latvijas Republikas Saeima"
    # Lapas 1-3 = Saeima (match), tad nebeidzama homonīmu siena.
    def handler(request):
        idx = handler.calls
        handler.calls += 1
        if idx < 3:
            return httpx.Response(200, text=_homonym_page(SAEIMA, idx * 50))
        return httpx.Response(200, text=_homonym_page("Vidzemes slimnīca", idx * 50))
    handler.calls = 0

    c = _make_client(handler)
    rows = c.search(
        "Inga", "Bērziņa",
        accept_row=lambda r: SAEIMA.lower() in r.institution.lower(),
    )
    # Apstājas pirms hard bound: 3 match lapas + 4 gap lapas pāri 200 robežas
    # pārbaudes (gap skaitītājs sāk tikšķēt tikai aiz bound logikas).
    assert len(rows) < PAGE_HARD_BOUND
    assert len(rows) >= PAGE_SAFETY_BOUND
