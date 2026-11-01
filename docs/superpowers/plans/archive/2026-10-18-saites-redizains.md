# Saites lapa (pārskatāma, sākas no partijas/politiķa) + wiki grafs — īstenošanas plāns

**STATUSS: IZPILDĪTS 2026-10-18** — CHANGELOG 2026-10-18. Saraksta izskats vēlāk mainīts: CHANGELOG 2026-10-21 (3).
Arhivēts 2026-10-21.

> **Aģentiem:** obligātā apakšprasme — `superpowers:subagent-driven-development` (ieteicams) vai `superpowers:executing-plans`. Soļi ar `- [ ]`. Palīgi uz Opus (`model: 'opus'`); neviens palīgs neizpilda `git stash`, `git checkout --`, `git restore`, `git reset`. UI uzdevumos palīga briefā VIENMĒR `good-css` prasme.

**Mērķis:** lasītājs Saites lapā vispirms redz saprotamu kopsavilkumu un izvēlas partiju vai politiķi (nevis 216 mezglu kamolu); pilnais tīkls atveras tikai pēc pieprasījuma; Spriedzes lapas filtrus var nosūtīt kā saiti; Obsidian grafā vairs nav operāciju trokšņa.

**Arhitektūra:** jaunu vizualizāciju NEbūvējam. Noklusējuma slānis = servera HTML bez JS (`<details>` pa partijām → pāru saraksts). «Ego-tīkls» = esošā profila Saites cilne (`templates/politician.html.j2:774+`, servera SVG, ≤8 kaimiņi) — Saites lapa uz to ved ar dziļo saiti. D3 grafs paliek, bet ielādējas tikai pēc pogas. Spriedzes lapa iegūst URL parametrus.

**Tehnoloģijas:** Python 3.12, Jinja2, vanilla JS `assets/*.js`, D3 v7 (pašmitināts), pytest + Playwright. Vienmēr `.venv/Scripts/python.exe`.

**Spec:** `docs/superpowers/specs/2026-10-18-saites-redizains-design.md` (problēmas ar pierādījumiem, lēmumi 1–8, wiki lēmumi). Izlasi PIRMS 0. uzdevuma.

## Globālie ierobežojumi

- Nav inline JS (`tests/test_no_inline_js.py`); jauns JS tikai `assets/*.js`; jauns ārējs hosts NAV vajadzīgs.
- Publiskā anonimitāte commit tekstos un lapās.
- LV gramatika + stilistika visam mūsu tekstam (UI virsraksti, paskaidrojumi). Šaubās — pārfrāzē.
- Neitralitāte: partijas alfabētiski, pāri pēc jaunākā ieraksta datuma (ne pēc skaita); katram skaitlim saucējs; nekādu «visvairāk uzbrūk» virsrakstu.
- Testi: viena e2e pārbaude katrai redzamai uzvedībai, uzrakstīta PIRMS koda; pierādīta ar mutāciju (atgriez labojumu → krīt). Pirms jauna testa nosauc esošo, kas jau sedz (ja ir — nepievieno).
- `tests/test_render_chars.py::test_saites_index_byte_identical` un spriedzes baseline drifts ir GAIDĀMS: `REGEN=1 .venv/Scripts/python.exe -m pytest tests/test_render_chars.py`, commit kopā ar maiņu. Cits faila drifts = STOP.
- Šaurs renders: `--only=` ar saites/spriedzes/politiki domēnu (skat. `wiki/operations/commands.md`); deploy TIKAI ar operatora atļauju, pirms tam `bash scripts/deploy.sh --dry-run --no-delete`.
- Wiki ģenerētās lapas labo `src/wiki*.py`, nekad ar roku. Sintēzēs wikilinki aizliegti.
- Commit ziņas caur failu (`git commit -F`), beigās `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Gala vārti: `bash scripts/check.sh` zaļš + ekrānuzņēmumi 390 px un 1400 px katrai mainītajai lapai, apskatīti.

## Review Focus

1. **Partija ir tikai adresāta pusē** (piem., AS spriedzēs galvenokārt kā Kulberga partija) — Spriedzes `?party=AS` rāda arī tās. Tests: A1.
2. **Nezināma vērtība URL** (`?party=Neesoša`, veca saite) — nerāda «0 spriedžu», bet ignorē vērtību un rāda visu. Tests: A1.
3. **Dziļā saite uz profilu, kura kartīte nav «anchor»** (otrā tā paša pāra kartīte) — `#saites-<pid>` atver Saites cilni un ritina uz pirmo pāra kartīti. Tests: A2.
4. **Telefonā (390 px) pirmajā ekrānā** redzams ievads, meklētājs un vismaz viena partija; nekas nepārklājas; D3 neielādējas. Tests: A3.
5. **Tips ar 0 saitēm** (šobrīd «Balsojumi») — poga nerenderējas; tips ar saitēm, bet bez pogas («Nostāju konflikts»), iegūst pogu. Tests: A4.

---

### Task 0: Sesijas sākums — divi vārti (bez koda)

- [ ] **1. solis:** izlasi spec. Uzdod operatoram VIENU jautājumu: «Vai Saites lapā tabulu (486 rindas) aizstājam ar saiti uz Spriedzes lapu? Noklusējums — jā.» Atbildi ieraksti plāna galā § Lēmumu žurnāls.
- [ ] **2. solis (T18 paraugs):** nejauši 10 rindas, kur Kulbergs ir adresāts, salīdzini `description` ar avota tekstu:

```bash
PYTHONUTF8=1 .venv/Scripts/python.exe -c "
import sqlite3
db=sqlite3.connect('file:data/atmina.db?mode=ro',uri=True); db.row_factory=sqlite3.Row
k=db.execute(\"select id from tracked_politicians where name='Andris Kulbergs'\").fetchone()[0]
for r in db.execute('''select t.id,s.name src,t.tension_type,t.description,t.source_url,
       (select substr(d.content,1,1500) from documents d where d.source_url=t.source_url) txt
       from political_tensions t join tracked_politicians s on s.id=t.source_pid
       where t.target_pid=? order by random() limit 10''',(k,)):
    print('='*80); print(dict(r))
"
```

Katrai rindai verdikts: «pareizi» / «nepareizs adresāts» / «nav avotā». Ieraksti `docs/audits/2026-10-18-kulbergs-saites-paraugs.md` (vaicājums + 10 verdikti + saucējs). **≥2 kļūdas no 10 → STOP**: ziņo operatoram, A3 nesāc (partiju saraksts šo nobīdi pastiprina); A1, A2, B drīkst turpināt.
- [ ] **3. solis:** commit audita failu.

---

### Task A1: Spriedzes — filtri URL adresē, partija = jebkurš galapunkts

**Faili:**
- Modificēt: `templates/spriedzes.html.j2:71` (kartītes atribūti), `assets/spv1.js`
- Tests: `tests/test_spriedzes_url_filters.py` (jauns; paraugs `tests/test_balsojumi_url_filters.py`)

**Interfeisi:**
- Producē: URL `spriedzes.html?type=<v,..>&party=<v,..>&person=<v,..>` — tie paši nosaukumi un komatu formāts kā `assets/sav1.js::syncUrl`. A3 uz to veido saites.

- [ ] **1. solis: krītošais e2e tests**

```python
"""Spriedzes filtri dzīvo URL; partija atbilst autoram VAI adresātam (2026-10-18).

Kļūme 1: `data-party` glabāja tikai autora partiju → «AS» filtrs slēpa spriedzes,
kur AS deputāts ir adresāts. Kļūme 2: filtri bija tikai lapas atmiņā → nosūtīta
saite atvēra visu sarakstu. Kļūme 3: nezināma vērtība adresē nedrīkst dot 0 kartīšu.
"""
import functools
import shutil
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import pytest

from src.db import get_db, init_db
from src.render.tensions import _fetch_tensions, render_tensions
from tests.test_balsojumi_client_render import _env

sync_api = pytest.importorskip("playwright.sync_api")

_SQL = """
INSERT INTO tracked_politicians (id, name, party, role, relationship_type) VALUES
  (1, 'Anna Ābele', 'JV', 'deputāte', 'tracked'),
  (2, 'Bruno Bērziņš', 'AS', 'deputāts', 'tracked'),
  (3, 'Cilda Cīrule', 'ZZS', 'deputāte', 'tracked');
INSERT INTO political_tensions (id, source_pid, target_pid, topic, description, tension_type, source_url, created_at) VALUES
  (1, 1, 2, 'Imigrācija', 'Ābele kritizē Bērziņu.', 'uzbrukums', 'https://ex.lv/1', '2026-10-01 10:00:00'),
  (2, 3, 1, 'Budžets un finanses', 'Cīrule atbalsta Ābeli.', 'atbalsts', 'https://ex.lv/2', '2026-10-02 10:00:00');
"""


class _Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def _site(tmp_path):
    out = tmp_path / "site"
    out.mkdir()
    path = str(tmp_path / "t.db")
    init_db(path)
    db = get_db(path)
    db.executescript(_SQL)
    db.commit()
    try:
        render_tensions(_env(), db, out, _fetch_tensions(db))   # īstā render funkcija
    finally:
        db.close()
    shutil.copytree("assets", out / "assets", dirs_exist_ok=True)
    return out


def _visible(page):
    return page.eval_on_selector_all(
        "#tensions-grid .card", "els => els.filter(e => e.offsetParent !== null).length")


def test_spriedzes_filters_round_trip_and_match_either_party(tmp_path):
    out = _site(tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Quiet, directory=str(out)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}/spriedzes.html"
    try:
        with sync_api.sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page()
            page.goto(base + "?party=AS")              # AS ir TIKAI adresāts
            assert _visible(page) == 1
            page.goto(base + "?party=JV")              # JV ir autors (1) un adresāts (2)
            assert _visible(page) == 2
            page.goto(base + "?party=Neesoša")         # nezināma vērtība → ignorē
            assert _visible(page) == 2
            page.goto(base)
            page.click("#type-select .multi-select-trigger")
            page.click("#type-select .multi-select-option[data-value='atbalsts']")
            assert parse_qs(urlparse(page.url).query) == {"type": ["atbalsts"]}
            assert _visible(page) == 1
            browser.close()
    finally:
        server.shutdown()
```

Ja veidne prasa filtru, kura nav `_env()` (`UndefinedError`/`TemplateAssertionError`), reģistrē to testa env tāpat kā `src/render/_orchestrator.py:364+` — NEmaini veidni testa dēļ.

- [ ] **2. solis:** `.venv/Scripts/python.exe -m pytest tests/test_spriedzes_url_filters.py -v` → FAIL (`?party=AS` dod 0).
- [ ] **3. solis: veidne** — `spriedzes.html.j2:71` `data-party="{{ t.source_party or '' }}"` → `data-source-party="{{ t.source_party or '' }}" data-target-party="{{ t.target_party or '' }}"`.
- [ ] **4. solis: `assets/spv1.js`** — `applyFilters()` partijai:

```js
const matchParty = selectedParties.size === 0
  || selectedParties.has(card.dataset.sourceParty)
  || selectedParties.has(card.dataset.targetParty);
```

un URL sinhronizācija (pēc `sav1.js:394–440` parauga): `syncUrl()` izsauc no `applyFilters()`; `applyFromUrl()` pirms pirmās filtrēšanas lasa `type`/`party`/`person`, paturot tikai vērtības, kurām lapā ir `.multi-select-option[data-value]`, un iestata tās caur `atminaMultiSelect` programmatisko izvēli (`assets/msv1.js:126`), lai trigera teksts sakrīt.
- [ ] **5. solis:** tests PASS; mutācija — atgriez 4. soļa partijas rindu → tests krīt; atjauno.
- [ ] **6. solis:** REGEN spriedzes baseline, `bash scripts/check.sh`, commit.

---

### Task A2: Profils — `#saites-<pid>` atver Saites cilni un ritina uz pāra kartīti

**Faili:**
- Modificēt: `assets/ppv1.js` (hash validācija)
- Tests: `tests/test_profile_saites_deeplink.py` (jauns)

**Interfeisi:**
- Producē: `politiki/<slug>.html#saites-<other_pid>` — atver cilni `saites`, ritina uz `#saites-<other_pid>`. A3 veido šīs saites. Kartītes `id` jau renderējas (`politician.html.j2:810/831/852`, tikai pāra pirmajai kartītei).

- [ ] **1. solis: krītošais e2e tests.** Renderē vienu profilu caur `src.render.politicians` ar `tests/test_render_chars.py::fixture_db` fikstūru (izvēlies politiķi ar ≥1 spriedzi: `SELECT source_pid FROM political_tensions LIMIT 1`), apkalpo ar to pašu `_Quiet` serveri, atver `…/politiki/<slug>.html#saites-<pid>` un pārbaudi:

```python
    assert page.get_attribute("#tab-btn-saites", "aria-selected") == "true"   # ppv1.js:96 + politician.html.j2:30
    box = page.locator(f"#saites-{other_pid}").bounding_box()
    assert box is not None and 0 <= box["y"] < page.viewport_size["height"]
```
- [ ] **2. solis:** FAIL (nezināms hash → noklusētā cilne).
- [ ] **3. solis:** `ppv1.js` hash lasītājā: ja `location.hash` atbilst `/^#saites-\d+$/` un cilne `saites` ir kopā, aktivizē `saites` un pēc tam `document.getElementById(hash.slice(1))?.scrollIntoView()`. Pārējā hash loģika nemainās.
- [ ] **4. solis:** PASS; mutācija (izņem regex zaru) → krīt; `check.sh`; commit.

---

### Task A3: Saites noklusējuma skats — ievads, meklētājs, partijas → pāri (0 JS)

*Bloķē:* Task 0 2. solis (T18), Task A2.

**Faili:**
- Modificēt: `src/render/links.py` (jauna `_party_pairs()` + konteksts), `templates/saites.html.j2`, `assets/style.css` (good-css)
- Tests: `tests/test_saites_default_view.py` (jauns)

**Interfeisi:**
- Consumes: `tensions` (no `_fetch_tensions`: `id, source_name, source_party, source_slug, target_name, target_party, target_slug, tension_type, date`), A2 dziļā saite. `_fetch_tensions` SELECT NAV `source_pid`/`target_pid` — 3. solī pievieno `t.source_pid, t.target_pid`; jaunās atslēgas maina saites inline JSON baitus (komentārs `tensions.py:50–54`) → baseline drifts gaidāms.
- Producē: `_party_pairs(tensions) -> list[dict]`: `[{"party": str, "count": int, "pairs": [{"a_name","a_slug","b_name","b_pid","types": {tips: n}, "n": int, "last": "YYYY-MM-DD"}]}]` — partijas alfabētiski (`""` → «Bez partijas» beigās), pāri pēc `last` dilstoši; pāris ir nevirzīts (`frozenset` pid), katrs pāris parādās ABU partiju sarakstos; `count` = partijas spriedžu skaits (jebkurā galā).

- [ ] **1. solis: krītošais e2e tests** — `render_links` ar reālu Jinja env (kā A1 `_env()`) un sīku DB (paraugs `tests/test_saites_sidecar.py:69` — `init_db` + `INSERT INTO tracked_politicians`/`political_tensions` 3 politiķiem, 2 partijām, 3 rindām, no tām 2 viena pāra), `tensions=_fetch_tensions(db)`; atver 390×844:

```python
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(base + "/saites.html")
    assert page.locator("#saites-search").is_visible()
    first = page.locator("details.saites-party").first
    assert first.bounding_box()["y"] < 844                      # pirmajā ekrānā
    assert not any("d3.v7" in r for r in requested)             # page.on("request") saraksts
    first.locator("summary").click()
    link = first.locator("a.saites-pair").first
    assert link.get_attribute("href").startswith("politiki/") and "#saites-" in link.get_attribute("href")
    assert link.locator(".saites-pair-n").inner_text() == "2"  # pāra 2 ieraksti saskaitīti
    page.goto(base + "/saites.html?party=AS")                    # veca filtra saite
    page.wait_for_url("**/spriedzes.html?party=AS")
```

- [ ] **2. solis:** FAIL.
- [ ] **3. solis: `_party_pairs()`** `links.py`:

```python
def _party_pairs(tensions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group tensions by party → undirected politician pairs (default Saites view)."""
    pairs: dict[frozenset, dict[str, Any]] = {}
    party_count: dict[str, int] = {}
    for t in tensions:
        key = frozenset((t["source_pid"], t["target_pid"]))
        p = pairs.setdefault(key, {"src": t, "types": {}, "n": 0, "last": ""})
        p["types"][t["tension_type"]] = p["types"].get(t["tension_type"], 0) + 1
        p["n"] += 1
        p["last"] = max(p["last"], t.get("date") or "")
        for party in {t.get("source_party") or "", t.get("target_party") or ""}:
            party_count[party] = party_count.get(party, 0) + 1
    by_party: dict[str, list[dict[str, Any]]] = {}
    for p in pairs.values():
        t = p["src"]
        row = {"a_name": t["source_name"], "a_slug": t["source_slug"],
               "b_name": t["target_name"], "b_pid": t["target_pid"],
               "types": p["types"], "n": p["n"], "last": p["last"]}
        for party in {t.get("source_party") or "", t.get("target_party") or ""}:
            by_party.setdefault(party, []).append(row)
    out = []
    for party in sorted(by_party, key=lambda s: (s == "", s)):
        rows = sorted(by_party[party], key=lambda r: r["last"], reverse=True)
        out.append({"party": party, "count": party_count[party], "pairs": rows})
    return out
```

Kontekstā: `"party_pairs": _party_pairs(tensions)`, `"politicians": sorted({(t["source_name"], t["source_slug"]) for t in tensions} | {(t["target_name"], t["target_slug"]) for t in tensions})`, `"recorded": (min(dates), max(dates))` — tas ir `created_at`, t.i., kad MĒS ierakstījām, ne notikuma datums (spec 7./Astra).
Zināms MVP ierobežojums: pāra partijas ņem no pāra pirmās rindas — partiju mainītājs pāri parādīs vienā partijā.
- [ ] **4. solis: veidne** — virs grafa (grafa bloks paliek A4 ziņā):
  - ievads 1–2 teikumos: «Saikne ir politiķa publisks izteikums par citu politiķi — uzbrukums, spriedze, atbalsts vai nostāju konflikts. {{ metrics.total }} saiknes starp {{ politician_count }} politiķiem, reģistrētas no {{ recorded[0] | lv_date }} līdz {{ recorded[1] | lv_date }}. Neaktīvie politiķi un komentētāji nav ieskaitīti.»
  - `<input id="saites-search" list="saites-politicians" …>` + `<datalist>`; izvēle ved uz `politiki/<slug>.html#saites` — to dara jaunais `assets/ssv1.js` (`change` → `location.href`). Tas pats fails pāradresē vecās filtru saites: ja `location.search` satur `type`, `party` vai `person` → `location.replace('spriedzes.html' + location.search)` (A1 parametru nosaukumi ir tie paši) — TIKAI, ja Task 0 lēmums = tabulu izņemt; citādi pāradresāciju un tās assert izlaid. Bez JS datalist paliek kā ieteikumu saraksts.
  - katrai partijai `<details class="saites-party"><summary>{{ party or 'Bez partijas' }} · {{ count }} saiknes</summary><ul>` ar `<li><a class="saites-pair" href="politiki/{{ a_slug }}.html#saites-{{ b_pid }}">{{ a_name }} ↔ {{ b_name }} · <span class="saites-pair-n">{{ n }}</span></a> · tipu žetoni · {{ last | lv_date }}</li>`.
  - CSS caur `good-css` (bez pārtraukumpunktu kāpnēm; `details` saraksts vienā kolonnā mobilajā, `grid-template-columns: repeat(auto-fill, minmax(min(100%, 20rem), 1fr))` datorā).
- [ ] **5. solis:** PASS; mutācija — izņem otro partiju no `for party in {…}` (pāris tikai autora partijā) → tests ar 2 partijām krīt (pievieno assert, ka pāris redzams ABĀS partijās, ja vēl nav).
- [ ] **6. solis:** REGEN saites baseline, `check.sh`, ekrānuzņēmumi 390/1400 no šaurā rendera, commit.

---

### Task A4: Pilnais tīkls pēc pieprasījuma, leģenda ārpus grafa, godīgas pogas

**Faili:**
- Modificēt: `templates/saites.html.j2`, `assets/sav1.js`, `src/render/links.py`
- Tests: papildini `tests/test_saites_default_view.py` (tā pati vietne)

**Interfeisi:**
- Producē: grafa JSON pārceļas no inline `#saites-data` uz `data/saites-graph.json` (ar `_emit_saites_json(..., basename="saites-graph")`); `sav1.js` eksponē `window.atminaSaitesGraph.open()`.

- [ ] **1. solis: krītošais tests:**

```python
def test_full_graph_loads_only_on_demand_and_buttons_are_honest(saites_site):
    page, requested = saites_site                      # A3 fikstūra, 390 px
    assert page.locator("#graph-svg circle").count() == 0
    assert page.locator("[data-link-type='vote']").count() == 0          # 0 balsojumu saišu
    assert page.locator("[data-link-type='politikas nostāju konflikts']").count() == 1  # ja fikstūrā ir 4. tips — pievieno to rindu A3 DB
    page.click("#saites-open-graph")
    page.wait_for_selector("#graph-svg circle")
    assert any("d3.v7" in r for r in requested)
    legend, svg = page.locator("#graph-legend").bounding_box(), page.locator("#graph-svg").bounding_box()
    assert legend["y"] >= svg["y"] + svg["height"] - 1                   # leģenda zem grafa
```

Precīzo 4. tipa vērtību ņem no `TENSION_TYPE_LV` (`src/render/_common/constants.py`).
- [ ] **2. solis:** FAIL.
- [ ] **3. solis: `links.py`** — `link_type_counts = Counter(l["tension_type"] if l["type"] in ("tension","support") else l["type"] for l in graph_data["links"])` kontekstā; uz `saites-graph.json` pārceļ VISUS trīs smagos laukus — `graph`, `tensions` (to lasa `sav1.js` saites detaļu panelis) un `contrasByPid`; inline paliek tikai `partyColors`, `tensionLabels`, `tensionBadges`. Ja kāds paliek inline, lapa paliek ~1,2 MB.
- [ ] **4. solis: veidne** — pogas ģenerē ciklā tikai tipiem ar `link_type_counts[t] > 0`, katrai skaits; grafa bloks paslēpts aiz `<button id="saites-open-graph">Rādīt visu tīklu ({{ politician_count }} politiķi)</button>`; `#graph-legend` pārcelts ārpus `.graph-pane` kā parasts bloks zem tā (inline `style` → klases `style.css`). `<script src="assets/d3.v7.min.js">` un `sav1.js` izņemti no lapas sākuma.
- [ ] **5. solis: `sav1.js`** — esošo `initGraph()` + filtru inicializāciju ietin `open()`; `ssv1.js` pogas klikšķis ielādē `d3.v7.min.js`, tad `sav1.js` (`document.createElement('script')`, `src` ar to pašu `?v=` — CSP `'self'` atļauj), tad `fetch('data/saites-graph.json')` → `open(data)`. Vecās `?type|party|person` saites jau pāradresē A3 (`ssv1.js`) uz Spriedzēm — grafs tās nelasa.
- [ ] **6. solis:** PASS; mutācija (atgriez pogu `{% if %}`) → krīt; izmēri pirms/pēc (`ls -la output/atmina/saites.html`) ieraksti commit ziņā; REGEN; `check.sh`; commit.

---

### Task A5: Tabula → saite uz Spriedzēm (tikai, ja Task 0 1. solis = jā)

**Faili:** `templates/saites.html.j2`, `assets/sav1.js` (`applyTableFilters`, `syncGraphWithTableTypes` — izņem tabulas daļu, grafa filtri paliek), `src/render/links.py` (konteksta atslēgas, ko lieto tikai tabula).

- [ ] **1. solis:** pirms dzēšanas — `grep -n "saites-table\|table-type-select\|party-select\|person-select" assets/*.js templates/*.j2 tests/*.py` un nosauc katru lietotāju.
- [ ] **2. solis:** tabulas + 3 multi-select vietā: `<a href="spriedzes.html">Visas {{ metrics.total }} saiknes sarakstā ar filtriem →</a>`. Grafa iekšējais persona/partija filtrs (ja vajag) paliek grafa panelī.
- [ ] **3. solis:** e2e: A3 testā pievieno `assert page.locator("#saites-table").count() == 0` un saites uz `spriedzes.html` esamību; mutācija; REGEN; `check.sh`; commit.

---

### Task A6: Pārbaude dzīvā renderā + publicēšanas vārti

- [ ] Šaurs renders; ekrānuzņēmumi 390/1400: `saites.html` (noklusējums, atvērta partija, atvērts grafs), `spriedzes.html?party=AS`, viens profils ar `#saites-<pid>`. Apskati pats; salīdzini ar `.scratch/saites-izpete/*.png` (ja vēl ir).
- [ ] LV gramatikas vārti jaunajiem tekstiem.
- [ ] `bash scripts/deploy.sh --dry-run --no-delete`; operatoram parādi ekrānuzņēmumus un izmēru starpību; deploy tikai pēc skaidras atļaujas.
- [ ] `wiki/CHANGELOG.md` ieraksts (≤5 rindas); `backlog/vietne-ui.md` rindu «Saites mini-grafs…» (45) atjaunini: balsojumu sakritības saišu jautājums paliek atvērts (9 034 pāri, 0 virs sliekšņiem — skat. spec 3. punktu).

---

### Task B1: Obsidian grafs bez operāciju trokšņa (konfigurācija)

**Faili:** `wiki/.obsidian/graph.json`, `wiki/politiki.base`

- [ ] **1. solis:** `graph.json` `"search"` = `-path:operations -path:log-ingest -file:CHANGELOG -file:log-ingest -file:project-brief`; `index.md` krāsas grupu (16498468, tā pati kā AS) nomaini uz neizmantotu krāsu; dzēs `colorGroups` ierakstus ar `path:operations`.
- [ ] **2. solis:** `politiki.base` jauns skats «Maz pārklāti»: filtrs `relationship_type == "tracked"` UN `positions < 5`, kārtots pēc `positions`. Lauku nosaukumus pārbaudi kādā `wiki/persons/*.md` frontmatter.
- [ ] **3. solis:** pārbaude ar `obsidian-cli` prasmi (grafa ekrānuzņēmums pirms/pēc) vai, ja Obsidian nav pieejams, — JSON derīgums (`python -c "import json;json.load(open(...))"`) un skaidri pasaki, ka vizuāli nav pārbaudīts. Commit.

---

### Task B2: Tēmu lapu `top_politicians` → saites (ģeneratorā)

**Faili:** `src/wiki_pages.py:390–413` (un `src/wiki.py:359`, ja tas raksta to pašu lauku), tests `tests/test_wiki.py`

- [ ] **1. solis:** nosauc esošo testu, kas sedz tēmu frontmatter (`grep -n top_politicians tests/test_wiki*.py`). Ja ir — papildini to; ja nav — viens jauns tests: pēc `wiki_sync` uz tmp DB tēmas lapas frontmatter `top_politicians` ir `"[[persons/<slug>|<Vārds>]]"` katram aktīvam politiķim un `wiki/persons/<slug>.md` eksistē; `inactive` politiķis paliek teksts.
- [ ] **2. solis:** FAIL → maini saraksta veidošanu (slugs ar to pašu funkciju, ko persons faili; inactive filtrs kā `src/wiki_pages.py` CHANGELOG 2026-10 ierakstā par `inactive` mērķiem) → PASS; mutācija.
- [ ] **3. solis:** `wiki_lint` (`src/wiki_lint.py`) — broken links 0; `check.sh`; commit.

---

### Task B3: Pārskatu saites — tikai, ja ir strukturēts avots

- [ ] **1. solis:** pārbaudi, vai DB pārskatam ir strukturēts dalībnieku saraksts (`context_notes` kolonnas: `PRAGMA table_info(context_notes)`; brief skeleton funkcijas `src/briefs*.py` — vai tās glabā claim/pid sarakstu pie pārskata).
- [ ] **2. solis:** ja IR — atsevišķs mazs uzdevums `src/wiki.py` eksportā: pārskata apakšā `## Politiķi` ar `[[persons/…]]` no šī saraksta; tests pēc B2 parauga. Ja NAV — nekādu teksta meklēšanu (T1); ieraksti `backlog/vietne-ui.md` vienu rindu «wiki pārskatiem nav strukturētu dalībnieku → grafā izolēti» un beidz.

---

## Ko šis plāns apzināti NEDARA

Pele bibliotēka (spec lēmums 7), partiju matrica (lēmums 6 — pēc MVP apskates), balsojumu sakritības saišu pārdizains, laika līnija (nav notikuma datuma — `backlog/dati-db.md:134`), wikilinki sintēzēs, Mermaid/Canvas tīklam, Obsidian kopienas spraudņi, `dailies`/`weeklies` vārdu sadursmes pārdēvēšana (nav nevienas saites, kas no tās ciestu).

## Lēmumu žurnāls

- 2026-10-18: tabulu Saites lapā aizstāt ar saiti uz Spriedzēm — JĀ (operatora noklusējums, jautāts sesijā, neiebilda; operators lūdza turpināt).
