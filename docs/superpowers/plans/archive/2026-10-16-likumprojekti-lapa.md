# Sadaļa «Likumi»: Pamatlikumi + Likumprojekti — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Likumprojektus pārcelt no paslēptas `balsojumi.html` cilnes uz savu lapu `likumprojekti.html`. Tā kopā ar `likumi.html` veido sadaļu «Likumi» ar kopīgu joslu. Likumprojektu lapā ir josla «Kur likumprojekti ir tagad» un saraksts «Biežāk grozītie likumi».

**Architecture:** Divas atsevišķas lapas (katra ielādē tikai savu saturu), kopīga saišu josla `_likumi_tabs.html.j2`. Visi jaunie atvasinājumi (posma grupa, grozāmais likums, etiķetes) notiek renderēšanā — DB nemainās. Filtru JS no `assets/blv1.js` pārceļ uz jaunu `assets/lpv1.js`.

**Tech Stack:** Python 3.12, Jinja2, vanilla JS (stingrā CSP), pytest + Playwright (Chromium).

**Spec:** `docs/audits/2026-10-16-matrica-likumprojekti/kritika.md` (ar § Papildinājums), `astra.md`, `astra-plans.md` (9 atradumi — visi iestrādāti šajā versijā). Matricas izņemšana NAV šajā plānā.

## Global Constraints

- UI valoda latviski; katrai jaunai virknei gramatikas + stilistikas pārbaude (CLAUDE.md § Output Conventions). Skaitītājs «Rāda N no M» (tāpat kā `pozicijas.html`).
- JS tikai `assets/*.js`; nekādu inline skriptu vai `on*=` atribūtu (`tests/test_no_inline_js.py` skenē automātiski). Inline `style=` ir atļauts (`assets/_headers:11` `style-src 'self' 'unsafe-inline'`).
- Python vienmēr `.venv/Scripts/python.exe`.
- Helperi NEDRĪKST: `git stash`, `git checkout --`, `git restore`, `git reset`. Commit ar `git commit -F <fails>`.
- DB netiek mainīta.
- Neko nedeploy. Deploy = operatora apstiprinājums (escalation 7).
- Testi: viens e2e katrai redzamai uzvedībai; unit testi tikai tīrai loģikai ar robežgadījumiem (`_stage_bucket`, `amended_law_name`). Esošos testus pārceļ, nevis dublē.
- `data-bill-type` vērtības (`Lp14`, `Lm14`, `P14`) paliek nemainīgas — mainās tikai redzamais teksts.
- Galvenajā izvēlnē jauna rinda NETIEK pievienota: `likumprojekti.html` lieto `active_page = "likumi"`.

## Datu fakti (2026-10-16, `data/atmina.db` mode=ro)

- Lp14 = 399. Grupas «kur tagad»: iesniegti 21 · pieņemti 1. lasījumā 59 · pieņemti 2. lasījumā 93 · kļuvuši par likumu 146 · noraidīti 61 · nav posma datu 19.
- 36 Lp ar `current_stage='2.lasījums'`, `current_status='pieņemts'` = steidzamie/ratifikācijas, pieņemti kā likums 2. lasījumā (`stage_result='Likums'`, motīvs «…, 2.lasījums, steidzams»).
- Dati sākas `min(first_seen_at)` = 2026-04-27; 67 Lp ir 3. lasījums bez 1. lasījuma → kumulatīvu piltuvi NERĀDĪT.
- 343 no 348 «Grozījumi …» nosaukumiem dod grozāmo likumu; 192 dažādi; top: «Par iedzīvotāju ienākuma nodokli» 13, Saeimas vēlēšanu likums 8, Izglītības likums 8, Krimināllikums 7. Sasaiste ar 33 pamatlikumu lapām jau pilna (67 sakritības, 0 trūkst).
- `tiesneša_amats` aptver iecelšanu UN atbrīvošanu (`src/saeima/bills.py:146-148`).

## Review Focus

1. **Vecā saite `balsojumi.html?tab=bills`** → nonāk `likumprojekti.html` (Task 4 Step 1).
2. **Meklēšana bez garumzīmēm** (Task 1 Step 1).
3. **`likumprojekti.html` blakus mapei `likumprojekti/`** — precedents `likumi.html` + `likumi/` strādā dzīvajā vietnē; pēc deploy `curl -sI https://atmina.lv/likumprojekti.html` → 200 (Task 5 Step 6).
4. **Nezināma stadija** — kartīte rāda izejas vērtību; posmu joslā tā krīt «Nav posma datu» (Task 1 Step 1, Task 3 Step 1).
5. **Vairāki sasaukumi** (`Lp15` + `Lp14` 15. Saeimas pārejā) — sasaukumu pieliek tikai, ja tas pats veids ir no ≥2 sasaukumiem; pogas pareizā secībā, aplaužas (Task 1 Step 1, Step 7).

---

### Task 1: Likumprojektu lapa `likumprojekti.html`

**Files:**
- Create: `templates/likumprojekti-index.html.j2`, `assets/lpv1.js`, `tests/test_likumprojekti_page.py`
- Modify: `src/saeima/convocation.py` (+`bill_type_filter_label`)
- Modify: `src/render/bills.py` (+`_stage_label`, `stage_label` laukā, `render_bills_index`)
- Modify: `src/render/laws.py` (+`laws_index_count()`)
- Modify: `templates/_bill_card.html.j2:1,20`
- Modify: `src/render/_orchestrator.py` (importi ap 57/71, bloks ap 466–479, sitemap ap 654–658)
- Modify: `assets/style.css` (beigās, tikai `.lpv1`)
- Modify: `tests/test_generate_bills.py:491-519` (tipu pogu testi pārceļas uz jauno lapu — Astra #1)

**Interfaces:**
- Produces: `bill_type_filter_label(bill_type: str, show_convocation: bool = False) -> str`; `laws_index_count(laws_dir: Path | None = None) -> int`; `render_bills_index(env, bills: list[dict], laws_count: int, atmina_dir: Path) -> None`; `_fetch_bills()` dict + `"stage_label": str | None`; DOM `#bills-grid`, `#bill-search`, `#bills-count` (`role="status"`), `#bills-empty-state`, `.bill-type-filter`, `.bill-status-filter`, `#bill-topic-select`; `window.lpv1Apply`.
- Consumes: `_fetch_bills(db)`, `_render_page` (`src/render/_common/assets.py:163`), `bill_type_sort_key`, `load_laws_index`, `window.atminaMultiSelect` (`assets/msv1.js:65`).

- [ ] **Step 1: E2E tests (failing)**

`tests/test_likumprojekti_page.py`:

```python
"""likumprojekti.html — likumprojektu katalogs savā lapā (2026-10-16).

Kļūmes, ko ķer: (1) meklēšana bez garumzīmēm neatrada neko; (2) pogas un
kartītes rādīja iekšējos kodus (Lp14, «tiesneša_amats»); (3) nebija redzams,
cik rezultātu palika («Rāda N no M»); (4) filtri nefiltrēja. Renderē caur
īsto render_bills_index() un atver Chromium."""

import functools
import shutil
import threading
from http.server import ThreadingHTTPServer

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from src.db import get_db
from src.render.bills import _fetch_bills, render_bills_index
from tests.test_generate_bills import db_with_bills  # noqa: F401 — fixture
from tests.test_multiselect_dropdown import _QuietHandler
from tests.test_profile_topic_deeplink import _env


def _serve(out):
    handler = functools.partial(_QuietHandler, directory=str(out))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


def _visible_nrs(page):
    return page.eval_on_selector_all(
        "#bills-grid .bill-card",
        "els => els.filter(e => e.offsetParent !== null)"
        ".map(e => e.querySelector('.badge').textContent.trim())")


def test_bills_page(db_with_bills, tmp_path):  # noqa: F811
    out = tmp_path / "site"
    out.mkdir()
    db = get_db(db_with_bills)
    bills = _fetch_bills(db)
    db.close()
    # Cita sasaukuma Lp + nezināma stadija (Review Focus 4, 5).
    bills.append(dict(bills[0], id=999, document_nr="1/Lp15", slug="1-lp15",
                      bill_type="Lp15", title="Jauns likums", topic=None,
                      current_stage="jauna_stadija", stage_label="jauna_stadija",
                      current_status="procesā"))
    render_bills_index(_env(), bills, 33, out)
    shutil.copytree("assets", out / "assets", dirs_exist_ok=True)

    html = (out / "likumprojekti.html").read_text(encoding="utf-8")
    # Lp no diviem sasaukumiem → ar sasaukumu; Lm/P tikai no viena → bez.
    assert 'data-bill-type="Lp14">Likumprojekti (14. Saeima)<' in html
    assert 'data-bill-type="Lp15">Likumprojekti (15. Saeima)<' in html
    assert 'data-bill-type="Lm14">Lēmumu projekti<' in html
    assert 'data-bill-type="P14">Paziņojumi<' in html
    order = [html.index(f'data-bill-type="{t}"') for t in ("Lp15", "Lp14", "Lm14", "P14")]
    assert order == sorted(order)
    assert "tiesneša_amats" not in html and "lēmums par tiesneša amatu" in html
    assert "paziņojuma_balsojums" not in html and "balsojums par paziņojumu" in html
    assert "jauna_stadija" in html  # nezināmu rāda, kā ir

    server, base = _serve(out)
    try:
        with sync_api.sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except Exception as exc:  # pragma: no cover
                pytest.skip(f"Chromium nav pieejams: {exc}")
            page = browser.new_page(viewport={"width": 390, "height": 844})
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"{base}/likumprojekti.html")
            n = len(bills)
            assert page.inner_text("#bills-count") == f"Rāda {n} no {n}"

            # Meklēšana bez garumzīmēm.
            page.fill("#bill-search", "aizsardzibas likuma")
            assert _visible_nrs(page) == ["1315/Lp14"]
            assert page.inner_text("#bills-count") == f"Rāda 1 no {n}"
            page.fill("#bill-search", "zzzz-nav-tada")
            assert page.inner_text("#bills-count") == f"Rāda 0 no {n}"
            assert page.is_visible("#bills-empty-state")
            page.fill("#bill-search", "")

            # Statuss.
            page.click('.bill-status-filter [data-status="noraidīts"]')
            want = {b["document_nr"] for b in bills if b["current_status"] == "noraidīts"}
            assert set(_visible_nrs(page)) == want
            page.click('.bill-status-filter [data-status=""]')

            # Tips: izslēdz Lp14.
            page.click('.bill-type-filter [data-bill-type="Lp14"]')
            assert not any(nr.endswith("/Lp14") for nr in _visible_nrs(page))
            page.click('.bill-type-filter [data-bill-type="Lp14"]')
            assert page.inner_text("#bills-count") == f"Rāda {n} no {n}"
            assert errors == [], errors
            browser.close()
    finally:
        server.shutdown()
```

Fixture `db_with_bills` (`tests/test_generate_bills.py:22-49`): 1315/Lp14 «Grozījumi Aizsardzības likumā», 952/Lm14 `tiesneša_amats`, P14 `paziņojuma_balsojums`, viens Lp14 `noraidīts`. Tests lieto burtiskus kodus, nevis `SAEIMA_CONVOCATION`.

Šajā taskā DZĒS `tests/test_generate_bills.py::test_bill_type_filter_buttons_follow_data` un `::test_render_votes_passes_bill_types_to_template` (`:491-519`): tipu secību un etiķetes tagad pārbauda `test_bills_page` caur reāli renderētām pogām.

- [ ] **Step 2: Palaid — jākrīt**

Run: `.venv/Scripts/python.exe -m pytest tests/test_likumprojekti_page.py -v`
Expected: FAIL — `ImportError: cannot import name 'render_bills_index'`.

- [ ] **Step 3: Etiķetes**

`src/saeima/convocation.py`, aiz `_KIND_ORDER`:

```python
_KIND_PLURALS = {"Lp": "Likumprojekti", "Lm": "Lēmumu projekti", "P": "Paziņojumi"}


def bill_type_filter_label(bill_type: str, show_convocation: bool = False) -> str:
    """Filtra pogas teksts: «Likumprojekti». Ja tas pats veids sarakstā ir no
    vairākiem sasaukumiem (14. un 15. Saeimas pārejā), pieliek «(14. Saeima)».
    Nezināmu tipu atdod nemainītu."""
    m = _BILL_TYPE_RE.fullmatch(bill_type or "")
    if not m:
        return bill_type or ""
    label = _KIND_PLURALS[m.group(1)]
    return f"{label} ({int(m.group(2))}. Saeima)" if show_convocation else label
```

`src/render/bills.py` — importi augšā: `import re`; `from collections import Counter`; `from src.render._common.assets import _render_page`; `from src.saeima.convocation import bill_kind` → `bill_kind, bill_type_filter_label, bill_type_sort_key`. Virs `_fetch_bills`:

```python
# Kartītes stadijas teksts. Atslēgas = saeima_bills.current_stage vērtības
# (2026-10-16: SELECT DISTINCT current_stage). Nezināmu vērtību rāda, kā ir.
# tiesneša_amats = iecelšana UN atbrīvošana (src/saeima/bills.py:146-148).
_STAGE_LABELS = {
    "1.lasījums": "1. lasījums",
    "2.lasījums": "2. lasījums",
    "3.lasījums": "3. lasījums",
    "tiesneša_amats": "lēmums par tiesneša amatu",
    "paziņojuma_balsojums": "balsojums par paziņojumu",
    "procesuāls": "procedūras balsojums",
    "nezināms": None,
}
_LM_OTHER_RE = re.compile(r"^Lm\d+ cits$")


def _stage_label(stage: str | None) -> str | None:
    if not stage:
        return None
    if _LM_OTHER_RE.match(stage):
        return "lēmums"
    return _STAGE_LABELS.get(stage, stage)
```

`_fetch_bills` vārdnīcā aiz `"current_stage"`: `"stage_label": _stage_label(r["current_stage"]),`.

Pārbaude, ka karte aptver visu: `.venv/Scripts/python.exe -c "import sqlite3;c=sqlite3.connect('file:data/atmina.db?mode=ro',uri=True);print(c.execute('select distinct current_stage from saeima_bills').fetchall())"` — katra vērtība ir kartē, `None`, vai atbilst `Lm\d+ cits`.

`templates/_bill_card.html.j2`: 1. rindas komentārā `/balsojumi.html#bills-list` → `/likumprojekti.html`; 20. rindu aizstāj ar:

```jinja
      {% set stage = bill.stage_label if bill.stage_label is defined else bill.current_stage %}
      {% if stage %}{{ stage }}{% if bill.current_status %} · {% endif %}{% endif %}{{ bill.current_status or '' }}
```

- [ ] **Step 4: Pamatlikumu skaits bez DB (Astra #4)**

`src/render/laws.py`, aiz `render_laws`:

```python
def laws_index_count(laws_dir: Path | None = None) -> int:
    """Pamatlikumu skaits — tā pati kopa, ko rāda likumi.html (wiki/laws/*.md),
    lai «Pamatlikumi (N)» sakrīt neatkarīgi no tā, vai renderē arī likumi."""
    from src.saeima import load_laws_index
    return len(load_laws_index((laws_dir or LAWS_DIR).parent))
```

- [ ] **Step 5: Renderētājs + šablons**

`src/render/bills.py` beigās:

```python
def render_bills_index(
    env: Environment,
    bills: list[dict[str, Any]],
    laws_count: int,
    atmina_dir: Path,
) -> None:
    """Render likumprojekti.html — visu likumprojektu katalogs (līdz
    2026-10-16 paslēpta balsojumi.html cilne, 77 % no tās HTML)."""
    types = sorted({b["bill_type"] for b in bills if b.get("bill_type")}, key=bill_type_sort_key)
    # Veids («Likumprojekts») → cik sasaukumu tas aptver šajā sarakstā.
    kinds = Counter(k[0] for k in map(bill_kind, types) if k)
    _render_page(env, "likumprojekti-index.html.j2", atmina_dir / "likumprojekti.html", {
        "bills": bills,
        "bill_types": [(t, bill_type_filter_label(t, bool(bill_kind(t)) and kinds[bill_kind(t)[0]] > 1))
                       for t in types],
        "bill_topics": sorted({b["topic"] for b in bills if b.get("topic")}),
        "laws_count": laws_count,
    })
```

`templates/likumprojekti-index.html.j2`:

```jinja
{% extends "base.html.j2" %}
{% set active_page = "likumi" %}
{% block title %}Likumprojekti — Politiskā atmiņa{% endblock %}
{% block description %}Saeimas likumprojekti, lēmumu projekti un paziņojumi: stadija, iesniedzēji un balsojumi.{% endblock %}
{% from "_bill_card.html.j2" import bill_card %}
{% block content %}
<section class="lpv1">
<div class="page-header">
  <h1>Likumprojekti</h1>
  <p class="muted">Likumprojekti, lēmumu projekti un paziņojumi Saeimā. Katram ir sava lapa ar gaitu un balsojumiem.</p>
</div>

<div class="filter-bar">
  <label for="bill-search" class="sr-only">Meklēt pēc nosaukuma vai dokumenta numura</label>
  <input type="search" id="bill-search" placeholder="Meklēt pēc nosaukuma vai dokumenta numura…" class="bill-search-input" autocomplete="off">

  <div class="multi-select" id="bill-topic-select">
    <div class="multi-select-trigger" role="button" tabindex="0" aria-haspopup="listbox" aria-expanded="false" id="bill-topic-trigger">
      <span>Visas tēmas</span><span class="arrow">&#9660;</span>
    </div>
    <div class="multi-select-dropdown" role="listbox" aria-multiselectable="true">
      <input type="text" class="multi-select-search" aria-label="Meklēt tēmas" placeholder="Meklēt...">
      {% for topic in bill_topics %}
      <div class="multi-select-option" role="option" aria-selected="false" tabindex="-1" data-value="{{ topic }}">
        <span class="checkbox"></span><span>{{ topic }}</span>
      </div>
      {% endfor %}
      <div class="multi-select-clear" role="button" tabindex="-1">Notīrīt izvēli</div>
    </div>
  </div>

  <div class="bill-status-filter">
    <button class="link-filter-btn active" aria-pressed="true" data-status="">Visi</button>
    <button class="link-filter-btn" aria-pressed="false" data-status="procesā">Procesā</button>
    <button class="link-filter-btn" aria-pressed="false" data-status="pieņemts">Pieņemts</button>
    <button class="link-filter-btn" aria-pressed="false" data-status="noraidīts">Noraidīts</button>
  </div>

  <div class="bill-type-filter">
    {% for code, label in bill_types %}
    <button class="link-filter-btn active" aria-pressed="true" data-bill-type="{{ code }}">{{ label }}</button>
    {% endfor %}
  </div>
</div>

<p id="bills-count" class="muted" role="status" aria-live="polite">Rāda {{ bills|length }} no {{ bills|length }}</p>

<div class="bill-card-grid" id="bills-grid">
  {% for b in bills %}{{ bill_card(b) }}{% endfor %}
</div>
<div id="bills-empty-state" class="votes-empty-state" style="display:none;">
  <span class="empty-icon">&#9638;</span>
  <p>Nav likumprojektu, kas atbilst filtriem</p>
</div>
<p style="margin-top:1.5rem; padding-top:1rem; border-top:1px solid var(--border); font-size:0.9rem;">
  <a href="balsojumi.html" class="muted-link">Saeimas balsojumi →</a>
</p>
</section>
{% endblock %}

{% block scripts %}
<script src="assets/ms-a11y.js?v={{ assets_version }}"></script>
<script src="assets/msv1.js?v={{ assets_version }}"></script>
<script src="assets/lpv1.js?v={{ assets_version }}"></script>
{% endblock %}
```

(`laws_count` kontekstā izmanto Task 2 josla.)

- [ ] **Step 6: `assets/lpv1.js`**

```js
// lpv1.js — likumprojektu kataloga filtri (likumprojekti.html). Izcelts no
// blv1.js 2026-10-16, kad likumprojekti pārcēlās no balsojumi.html cilnes.
// Meklēšana bez garumzīmēm — tas pats fold kā bmv1.js::foldText. Teksts
// normalizēts vienreiz ielādē, ievadē — tikai vaicājums.
(function () {
  var selectedTopics = new Set();
  var selectedStatus = '';
  var hiddenTypes = new Set();

  function fold(s) {
    return (s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  }

  var cards = Array.prototype.slice.call(document.querySelectorAll('#bills-grid .bill-card'));
  cards.forEach(function (c) { c._hay = fold(c.dataset.search); });
  var total = cards.length;

  function apply() {
    var q = fold(document.getElementById('bill-search').value).trim();
    var visible = 0;
    cards.forEach(function (card) {
      var ok = (selectedTopics.size === 0 || selectedTopics.has(card.dataset.topic)) &&
        (!selectedStatus || card.dataset.status === selectedStatus) &&
        !hiddenTypes.has(card.dataset.billType) &&
        (!q || card._hay.indexOf(q) !== -1);
      card.style.display = ok ? '' : 'none';
      if (ok) visible++;
    });
    document.getElementById('bills-count').textContent = 'Rāda ' + visible + ' no ' + total;
    document.getElementById('bills-empty-state').style.display = visible === 0 ? 'block' : 'none';
  }

  document.querySelector('.bill-status-filter').addEventListener('click', function (e) {
    var btn = e.target.closest('[data-status]');
    if (!btn) return;
    document.querySelectorAll('.bill-status-filter .link-filter-btn').forEach(function (b) {
      b.classList.toggle('active', b === btn);
      b.setAttribute('aria-pressed', b === btn ? 'true' : 'false');
    });
    selectedStatus = btn.dataset.status;
    apply();
  });

  document.querySelector('.bill-type-filter').addEventListener('click', function (e) {
    var btn = e.target.closest('[data-bill-type]');
    if (!btn) return;
    var on = btn.classList.toggle('active');
    btn.setAttribute('aria-pressed', on ? 'true' : 'false');
    if (on) hiddenTypes.delete(btn.dataset.billType); else hiddenTypes.add(btn.dataset.billType);
    apply();
  });

  document.getElementById('bill-search').addEventListener('input', apply);

  atminaMultiSelect({ root: 'bill-topic-select', selected: selectedTopics,
    allLabel: 'Visas tēmas', pluralLabel: 'tēmas izvēlētas', onChange: apply });
})();
```

- [ ] **Step 7: CSS (izmanto `good-css` skill)**

`assets/style.css` beigās:

```css
/* likumprojekti.html — pieskāriena zonas ≥44 px, ievade 16 px (iOS netuvina),
   pogas aplaužas (garās etiķetes, vairāki sasaukumi). */
.lpv1 .bill-search-input { font-size: 1rem; min-block-size: 44px; inline-size: 100%; }
.lpv1 .link-filter-btn { min-block-size: 44px; }
.lpv1 .bill-type-filter,
.lpv1 .bill-status-filter { flex-wrap: wrap; }
```

- [ ] **Step 8: Orķestrators + sitemap**

`src/render/_orchestrator.py`: importā `from src.render.bills import _fetch_bills, render_bills` → `+ render_bills_index`; `from src.render.laws import render_laws` → `+ laws_index_count`. Bloks ap 466–479:

```python
    # 4. Likumi/Likumprojekti/Balsojumi.
    if _want("likumi"):
        render_laws(env, db, atmina_dir)
    if _want("bills"):
        bill_count = render_bills(env, db, atmina_dir)
        render_bills_index(env, bills, laws_index_count(), atmina_dir)
        logger.info("Generated %d bill pages + likumprojekti.html", bill_count)
    if _want("balsojumi"):
        render_votes(env, db, atmina_dir, votes, bills, laws_index_count())
```

(Balsojumu izsaukumu vienkāršo Task 4.) Pārbaudi, ka `"bills"` ir domēnu sarakstā: `grep -n '"bills"' src/render/_orchestrator.py`.

Sitemap `root_pages` (ap 657) aiz `"likumi.html",` pievieno `"likumprojekti.html",`.

- [ ] **Step 9: Palaid — jāiziet; mutācijas**

Run: `.venv/Scripts/python.exe -m pytest tests/test_likumprojekti_page.py tests/test_generate_bills.py tests/test_no_inline_js.py -v` — PASS.

Mutācijas (katrai jākrīt, tad atjauno): (a) `fold` bez `.normalize(...)`; (b) `_stage_label` atgriež `stage`; (c) `apply()` izņem tipa nosacījumu; (d) `render_bills_index` vienmēr padod `show_convocation=False` → Lp15/Lp14 etiķešu pārbaude krīt.

- [ ] **Step 10: Commit**

```bash
git add templates/likumprojekti-index.html.j2 assets/lpv1.js assets/style.css tests/test_likumprojekti_page.py tests/test_generate_bills.py src/saeima/convocation.py src/render/bills.py src/render/laws.py templates/_bill_card.html.j2 src/render/_orchestrator.py
git commit -F .scratch/commitmsg.txt   # «Likumprojekti savā lapā: meklēšana bez garumzīmēm, skaitītājs, cilvēku etiķetes»
```

---

### Task 2: Kopīgā josla «Pamatlikumi | Likumprojekti»

**Files:**
- Create: `templates/_likumi_tabs.html.j2`
- Modify: `templates/likumi-index.html.j2`, `templates/likumprojekti-index.html.j2`
- Modify: `src/render/laws.py::render_laws` (kontekstā `bills_count`)
- Modify: `assets/style.css`
- Test: `tests/test_likumprojekti_page.py` (paplašina), `tests/test_likumi_index.py:82-107` (pārraksta beigas)

**Interfaces:**
- Consumes: `laws_count` (Task 1 konteksts), `bills|length`.
- Produces: makro `likumi_tabs(active: str, laws_count: int, bills_count: int)`; DOM `nav.likumi-tabs a[aria-current="page"]`.

- [ ] **Step 1: Testi (failing)**

`test_bills_page` beigās, pirms `assert errors == []`:

```python
            # Sadaļas josla: šī lapa aktīva, saite uz pamatlikumiem.
            assert page.get_attribute('nav.likumi-tabs a[href="likumprojekti.html"]', "aria-current") == "page"
            assert page.inner_text('nav.likumi-tabs a[href="likumi.html"]') == "Pamatlikumi (33)"
            assert page.inner_text('nav.likumi-tabs a[href="likumprojekti.html"]') == f"Likumprojekti ({n})"
```

Otru lapu pārbauda ESOŠAIS pilnā cauruļvada tests `tests/test_likumi_index.py::test_likumi_index_html_generated_by_full_pipeline` (`:82-107`) — jaunu testu neveido. Tajā `only={"likumi", "balsojumi"}` → `only={"likumi", "bills"}`, un pēdējās četras rindas (balsojumu kājenes saite «Visi pamatlikumi», ko Task 4 izņem) aizstāj ar:

```python
    # Sadaļas josla abās lapās (Task 2).
    assert '<a href="likumi.html" aria-current="page">Pamatlikumi (' in content
    assert '<a href="likumprojekti.html">Likumprojekti (1)</a>' in content
    bills_page = (site / "likumprojekti.html").read_text(encoding="utf-8")
    assert '<a href="likumprojekti.html" aria-current="page">Likumprojekti (1)</a>' in bills_page
```

Docstring: «Renders the likumi + bills domains…». Tas pārbauda arī orķestratora pieslēgumu (Task 1 Step 8).

- [ ] **Step 2: Palaid — jākrīt**

Run: `.venv/Scripts/python.exe -m pytest tests/test_likumprojekti_page.py tests/test_likumi_index.py -v` — FAIL (nav `nav.likumi-tabs`).

- [ ] **Step 3: Makro + iekļaušana**

`templates/_likumi_tabs.html.j2`:

```jinja
{# Sadaļas «Likumi» josla: divas atsevišķas lapas, nevis paslēptas cilnes —
   katra ielādē tikai savu saturu. Saites, ne role=tab. #}
{% macro likumi_tabs(active, laws_count, bills_count) %}
<nav class="likumi-tabs" aria-label="Likumu sadaļa">
  <a href="likumi.html"{% if active == "likumi" %} aria-current="page"{% endif %}>Pamatlikumi ({{ laws_count }})</a>
  <a href="likumprojekti.html"{% if active == "likumprojekti" %} aria-current="page"{% endif %}>Likumprojekti ({{ bills_count }})</a>
</nav>
{% endmacro %}
```

`templates/likumprojekti-index.html.j2`: augšā `{% from "_likumi_tabs.html.j2" import likumi_tabs %}`; tieši pirms `<div class="page-header">`: `{{ likumi_tabs("likumprojekti", laws_count, bills|length) }}`.

`templates/likumi-index.html.j2`: tas pats imports; pirms `<div class="page-header">`: `{{ likumi_tabs("likumi", metrics.total, bills_count) }}`.

`src/render/laws.py::render_laws` kontekstā: `"bills_count": db.execute("SELECT COUNT(*) FROM saeima_bills").fetchone()[0],`.

CSS (`assets/style.css` beigās; skaties esošo `.subtab-bar`/`.subtab-btn` stilu un lieto tos pašus mainīgos):

```css
.likumi-tabs { display: flex; flex-wrap: wrap; gap: 0.25rem; border-block-end: 1px solid var(--border); margin-block-end: 1rem; }
.likumi-tabs a { padding: 0.6rem 1rem; min-block-size: 44px; display: inline-flex; align-items: center; color: var(--text-muted); text-decoration: none; border-block-end: 2px solid transparent; }
.likumi-tabs a[aria-current="page"] { color: var(--text); border-block-end-color: var(--accent); font-weight: 600; }
```

- [ ] **Step 4: Palaid — jāiziet**

Run: `.venv/Scripts/python.exe -m pytest tests/test_likumprojekti_page.py tests/test_likumi_index.py -v` — PASS. Mutācija: makro izņem `aria-current` → krīt.

- [ ] **Step 5: Commit**

```bash
git add templates/_likumi_tabs.html.j2 templates/likumi-index.html.j2 templates/likumprojekti-index.html.j2 src/render/laws.py assets/style.css tests/test_likumprojekti_page.py tests/test_likumi_index.py
git commit -F .scratch/commitmsg.txt   # «Sadaļa Likumi: kopīga josla Pamatlikumi | Likumprojekti»
```

---

### Task 3: Josla «Kur likumprojekti ir tagad» + «Biežāk grozītie likumi»

**Files:**
- Modify: `src/render/bills.py` (+`BUCKETS`, `_stage_bucket`, `amended_law_name`; lauki `bucket`, `law`; konteksts `buckets`, `lp_total`, `top_laws`, `data_since`)
- Modify: `templates/_bill_card.html.j2` (`data-bucket`, `data-law`)
- Modify: `templates/likumprojekti-index.html.j2`, `assets/lpv1.js`, `assets/style.css`
- Create: `tests/test_bill_stage_bucket.py` (unit, tīra loģika)
- Modify: `tests/test_likumprojekti_page.py` (e2e paplašinājums)

**Interfaces:**
- Produces: `BUCKETS: list[tuple[str, str]]`; `_stage_bucket(bill_type, stage, status) -> str` (atslēga no `BUCKETS` vai `""` ne-Lp tipiem); `amended_law_name(title: str) -> str | None`.
- Consumes: Task 1 `apply()` (tajā pašā IIFE).

- [ ] **Step 1: Testi (failing)**

`tests/test_bill_stage_bucket.py`:

```python
"""Tīrā loģika: likumprojekta grupa joslā «kur tagad» un grozāmā likuma
nosaukums no virsraksta. Kļūmes: steidzams likums (pieņemts 2. lasījumā)
krita «pieņemti 2. lasījumā»; lēmumi/paziņojumi iejaucās likumprojektu joslā;
locījums «Krimināllikumā» parādījās kā likuma nosaukums."""

import pytest

from src.render.bills import _stage_bucket, amended_law_name


@pytest.mark.parametrize("bt,stage,status,want", [
    ("Lp14", "3.lasījums", "pieņemts", "pienemts"),
    ("Lp14", "2.lasījums", "pieņemts", "pienemts"),   # steidzams / ratifikācija
    ("Lp14", "iesniegts", "noraidīts", "noraidits"),
    ("Lp14", "1.lasījums", "noraidīts", "noraidits"),
    ("Lp14", "iesniegts", "procesā", "iesniegts"),
    ("Lp14", "1.lasījums", "procesā", "pec1"),
    ("Lp14", "2.lasījums", "procesā", "pec2"),
    ("Lp14", "3.lasījums", "procesā", "pec2"),
    ("Lp14", None, "procesā", "nav"),
    ("Lp14", "procesuāls", "procesā", "nav"),
    ("Lp15", "jauna_stadija", "procesā", "nav"),
    ("Lm14", "tiesneša_amats", "pieņemts", ""),
    ("P14", "paziņojuma_balsojums", "noraidīts", ""),
])
def test_stage_bucket(bt, stage, status, want):
    assert _stage_bucket(bt, stage, status) == want


@pytest.mark.parametrize("title,want", [
    ("Grozījumi Krimināllikumā", "Krimināllikums"),
    ("Grozījums Krimināllikumā", "Krimināllikums"),
    ("Grozījumi Ceļu satiksmes likumā", "Ceļu satiksmes likums"),
    ("Grozījumi likumā “Par iedzīvotāju ienākuma nodokli”", "«Par iedzīvotāju ienākuma nodokli»"),
    ("Grozījumi Militārā poligona “Sēlija” izveides likumā", "Militārā poligona “Sēlija” izveides likums"),
    ("Grozījumi Saeimas kārtības rullī", None),
    ("Grozījums Latvijas Republikas Satversmē", None),
    ("Valsts sporta fonda likums", None),
    ("Grozījumi Administratīvo sodu likumā par pārkāpumiem pārvaldes jomā", None),
])
def test_amended_law_name(title, want):
    assert amended_law_name(title) == want
```

E2E paplašinājums `test_bills_page` (pirms sadaļas joslas pārbaudēm):

```python
            # Posmu josla: «Kļuvuši par likumu» atstāj tikai pieņemtos Lp;
            # otrs klikšķis izvēli noņem.
            page.click('.lpv1-stages [data-bucket="pienemts"]')
            want = {b["document_nr"] for b in bills
                    if b["bill_type"].startswith("Lp") and b["current_status"] == "pieņemts"}
            assert want and set(_visible_nrs(page)) == want
            assert page.get_attribute('.lpv1-stages [data-bucket="pienemts"]', "aria-pressed") == "true"
            page.click('.lpv1-stages [data-bucket="pienemts"]')
            assert page.inner_text("#bills-count") == f"Rāda {n} no {n}"
```

Šajā testā pievienotā `Lp{other}` kartīte ir izveidota ar `dict(bills[0], …)` — tai pēc Step 3 ir mantots `bucket`. Pievieno arī `bucket="nav", law=None` tās `dict(...)` izsaukumā.

«Biežāk grozītie likumi» fixture datos nav ≥3 grozījumu vienam likumam — tā daļu pārbauda unit tests un Task 5 Step 3 ar īstajiem datiem.

- [ ] **Step 2: Palaid — jākrīt**

Run: `.venv/Scripts/python.exe -m pytest tests/test_bill_stage_bucket.py tests/test_likumprojekti_page.py -v` — FAIL (`ImportError`).

- [ ] **Step 3: Loģika**

`src/render/bills.py`, aiz `_stage_label`:

```python
# Josla «Kur likumprojekti ir tagad» — tikai Lp (lēmumiem/paziņojumiem nav
# lasījumu). Grupa = kur likumprojekts ir TAGAD, ne cik posmu tas izgāja:
# dati sākas 2026-04-27, agrākie posmi DB trūkst (67 Lp ar 3. bez 1. las.).
BUCKETS = [
    ("iesniegts", "Iesniegti"),
    ("pec1", "Pieņemti 1. lasījumā"),
    ("pec2", "Pieņemti 2. lasījumā"),
    ("pienemts", "Kļuvuši par likumu"),
    ("noraidits", "Noraidīti"),
    ("nav", "Nav posma datu"),
]


def _stage_bucket(bill_type: str | None, stage: str | None, status: str | None) -> str:
    if not (bill_type or "").startswith("Lp"):
        return ""
    if status == "pieņemts":       # ietver steidzamos: likums jau 2. lasījumā
        return "pienemts"
    if status == "noraidīts":
        return "noraidits"
    return {"iesniegts": "iesniegts", "1.lasījums": "pec1",
            "2.lasījums": "pec2", "3.lasījums": "pec2"}.get(stage or "", "nav")


_LAW_QUOTED_RE = re.compile(r"^Grozījum[si] likumā [“\"](.+?)[”\"]$")
_LAW_LOCATIVE_RE = re.compile(r"^Grozījum[si] (.+likum)ā$")


def amended_law_name(title: str) -> str | None:
    """Grozāmā likuma nosaukums nominatīvā no «Grozījumi … likumā» virsraksta.
    Citas formas (Satversme, kārtības rullis, garš apraksts) → None."""
    t = (title or "").strip()
    m = _LAW_QUOTED_RE.match(t)
    if m:
        return f"«{m.group(1)}»"
    m = _LAW_LOCATIVE_RE.match(t)
    if m and " par " not in m.group(1):
        return m.group(1) + "s"
    return None
```

`_fetch_bills` vārdnīcā: `"bucket": _stage_bucket(r["bill_type"], r["current_stage"], r["current_status"]),` un `"law": amended_law_name(r["title"]),`.

`render_bills_index` kontekstam pievieno:

```python
    lp = [b for b in bills if b.get("bucket")]
    counts = Counter(b["bucket"] for b in lp)
    law_counts = Counter(b["law"] for b in bills if b.get("law"))
    # ... kontekstā:
        "buckets": [(k, label, counts.get(k, 0)) for k, label in BUCKETS],
        "lp_total": len(lp),
        "top_laws": [(name, k) for name, k in law_counts.most_common(10) if k >= 3],
        "data_since": min((b["first_seen_at"] for b in bills if b.get("first_seen_at")), default=None),
```

Pārbaude pret «Datu fakti» — vienreizējs skripts `.scratch/check_buckets.py` (NEKOMITĒ): `_fetch_bills` uz `data/atmina.db` (mode=ro) → `Counter(bucket)` Lp14 = 21/59/93/146/61/19; `amended_law_name` nav `None` ≥ 340 Lp.

`templates/_bill_card.html.j2` `<a class="bill-card"` atribūtiem: `data-bucket="{{ bill.bucket or '' }}"` un `data-law="{{ bill.law or '' }}"`.

- [ ] **Step 4: Šablons**

`templates/likumprojekti-index.html.j2`, starp `.page-header` un `.filter-bar`:

```jinja
{% if lp_total %}
<div class="lpv1-stages">
  <h2>Kur likumprojekti ir tagad</h2>
  <div class="lpv1-stagebar" aria-hidden="true">
    {% for key, label, n in buckets if n %}<span class="lpv1-seg lpv1-seg-{{ key }}" style="flex-grow: {{ n }}"></span>{% endfor %}
  </div>
  <div class="lpv1-stage-btns">
    {% for key, label, n in buckets if n %}
    <button type="button" class="link-filter-btn" aria-pressed="false" data-bucket="{{ key }}"><span class="lpv1-dot lpv1-seg-{{ key }}" aria-hidden="true"></span>{{ label }} <b>{{ n }}</b></button>
    {% endfor %}
  </div>
  <p class="muted lpv1-note">{{ lp_total }} {{ lp_total|lv_plural("likumprojekts", "likumprojekti") }}{% if data_since %}, dati kopš {{ data_since|lv_date }}{% endif %}. Steidzamus likumprojektus un starptautiskus līgumus Saeima pieņem divos lasījumos.</p>
</div>
{% endif %}

{% if top_laws %}
<div class="lpv1-laws">
  <h2>Biežāk grozītie likumi</h2>
  <div class="lpv1-law-btns">
    {% for name, k in top_laws %}
    <button type="button" class="link-filter-btn" aria-pressed="false" data-law="{{ name }}">{{ name }} <b>{{ k }}</b></button>
    {% endfor %}
  </div>
</div>
{% endif %}
```

- [ ] **Step 5: JS**

`assets/lpv1.js` — IIFE augšā: `var selectedBucket = ''; var selectedLaw = '';`. `apply()` nosacījumam pievieno:

```js
        (!selectedBucket || card.dataset.bucket === selectedBucket) &&
        (!selectedLaw || card.dataset.law === selectedLaw) &&
```

Pirms `atminaMultiSelect(...)`:

```js
  // Viena izvēle grupā; otrs klikšķis uz tās pašas pogas izvēli noņem.
  function bindSingle(sel, attr, set) {
    var box = document.querySelector(sel);
    if (!box) return;
    box.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-' + attr + ']');
      if (!btn) return;
      var on = btn.getAttribute('aria-pressed') !== 'true';
      box.querySelectorAll('[data-' + attr + ']').forEach(function (b) {
        var me = b === btn && on;
        b.setAttribute('aria-pressed', me ? 'true' : 'false');
        b.classList.toggle('active', me);
      });
      set(on ? btn.dataset[attr] : '');
      apply();
    });
  }
  bindSingle('.lpv1-stages', 'bucket', function (v) { selectedBucket = v; });
  bindSingle('.lpv1-laws', 'law', function (v) { selectedLaw = v; });
```

- [ ] **Step 6: CSS (`good-css` skill)**

```css
.lpv1-stages, .lpv1-laws { margin-block: 1rem 1.5rem; }
.lpv1-stages h2, .lpv1-laws h2 { font-size: 1rem; margin-block-end: 0.5rem; }
.lpv1-stagebar { display: flex; block-size: 12px; border-radius: 6px; overflow: hidden; gap: 2px; margin-block-end: 0.5rem; }
.lpv1-stage-btns, .lpv1-law-btns { display: flex; flex-wrap: wrap; gap: 0.4rem; }
.lpv1-dot { display: inline-block; inline-size: 0.7em; block-size: 0.7em; border-radius: 50%; margin-inline-end: 0.35em; }
.lpv1-seg-iesniegts { background: var(--text-muted); }
.lpv1-seg-pec1 { background: color-mix(in oklab, var(--accent) 45%, transparent); }
.lpv1-seg-pec2 { background: color-mix(in oklab, var(--accent) 80%, transparent); }
.lpv1-seg-pienemts { background: var(--green); }
.lpv1-seg-noraidits { background: var(--red); }
.lpv1-seg-nav { background: var(--border); }
.lpv1-note { font-size: 0.85rem; margin-block-start: 0.5rem; }
```

(`--green`, `--red` definēti abām tēmām: `assets/style.css:128,130,209,211`.)

- [ ] **Step 7: Palaid — jāiziet; mutācijas**

Run: `.venv/Scripts/python.exe -m pytest tests/test_bill_stage_bucket.py tests/test_likumprojekti_page.py tests/test_no_inline_js.py -v` — PASS.
Mutācijas: (a) `_stage_bucket` bez `status == "pieņemts"` zara → krīt; (b) `bindSingle` otrajā klikšķī neatiestata → e2e krīt.

- [ ] **Step 8: Commit**

```bash
git add src/render/bills.py templates/_bill_card.html.j2 templates/likumprojekti-index.html.j2 assets/lpv1.js assets/style.css tests/test_bill_stage_bucket.py tests/test_likumprojekti_page.py
git commit -F .scratch/commitmsg.txt   # «Likumprojekti: josla «Kur tagad» un biežāk grozītie likumi»
```

---

### Task 4: Izņem cilni no `balsojumi.html`

**Files:**
- Modify: `templates/balsojumi.html.j2:28,164-207`, `templates/politician.html.j2:578`
- Modify: `assets/blv1.js`
- Modify: `src/render/votes.py` (`render_votes` bez `bills`, `laws_index_count`; dzēš `_bill_types_for_filter`)
- Modify: `src/render/_orchestrator.py`, `scripts/render_balsojumi_only.py:40,45`
- Modify: `tests/test_balsojumi_client_render.py` (`_MINIMAL_CTX`), `tests/test_generate_bills.py:349-378` (dzēš), `tests/test_render_votes_matrix_json.py:494`, `tests/test_multiselect_dropdown.py:161-205`, `tests/test_toggle_aria_pressed.py:87-97`, `tests/test_tabs_keyboard.py:104`

**Interfaces:**
- Consumes: Task 1 `render_bills_index`, `likumprojekti.html` DOM.
- Produces: `render_votes(env, db, atmina_dir, votes)`.

- [ ] **Step 1: Pielāgo esošos testus**

`tests/test_toggle_aria_pressed.py` — aiz `(out / "balsojumi.html").write_text(...)`: `render_bills_index(_env(), [], 0, out)` (`from src.render.bills import render_bills_index`). Bloku «Balsojumi: likumprojektu statusa filtrs + apakšcilnes» aizstāj ar (Astra #6):

```python
            # Balsojumos likumprojektu cilnes vairs nav.
            page.goto(f"{base}/balsojumi.html")
            assert page.locator('.subtab-btn[data-tab="bills-list"]').count() == 0
            assert page.locator("#bills-list-tab").count() == 0
            # Vecā saite uz cilni ved uz likumprojektu lapu.
            page.goto(f"{base}/balsojumi.html?tab=bills")
            page.wait_for_url("**/likumprojekti.html")
            status_sel = ".bill-status-filter .link-filter-btn"
            _assert_group_in_sync(page, status_sel, "active")
            page.click(f'{status_sel}[data-status="procesā"]')
            assert page.get_attribute(f'{status_sel}[data-status="procesā"]', "aria-pressed") == "true"
            assert page.get_attribute(f'{status_sel}[data-status=""]', "aria-pressed") == "false"
            _assert_group_in_sync(page, status_sel, "active")
```

`tests/test_multiselect_dropdown.py::test_bill_topic_select_updates_label` — renderē likumprojektu lapu (`from tests.test_profile_topic_deeplink import _env`; `from src.render.bills import render_bills_index`) ar 3 kartītēm un pārbauda ARĪ filtrēšanu (Astra #7):

```python
    bills = [dict(id=i, document_nr=f"{i}/Lp14", slug=f"{i}-lp14", bill_type="Lp14",
                  title=f"Likums {i}", summary=None, topic=t, current_stage="iesniegts",
                  stage_label="iesniegts", current_status="procesā", bucket="iesniegts", law=None,
                  institutional_submitter=None, submitter_count=0, first_seen_at="2026-05-01")
             for i, t in enumerate(["Ekonomika", "Izglītība", "Veselība"], 1)]
    render_bills_index(_env(), bills, 0, out)
```

`page.goto(f"{base}/likumprojekti.html")`; pēc «Izglītība» atlases `assert page.inner_text("#bills-count") == "Rāda 1 no 3"`; pēc notīrīšanas `== "Rāda 3 no 3"`. Docstring: «Likumprojektu tēmu filtrs (`likumprojekti.html`)…». Izņem nelietotos `_MINIMAL_CTX`/`_balsojumi_env` importus.

`tests/test_tabs_keyboard.py:104` (Astra #2) — Balsojumos paliek 2 cilnes:

```python
                want = 2 if path == "balsojumi.html" else 3
                assert len(state) >= want, f"{path}: tikai {len(state)} cilnes — vārti nevar krist"
```

(`End` jau lieto `len(state) - 1` — pārējais tests der.)

`tests/test_generate_bills.py::test_balsojumi_renders_bills_subtab` (`:349-378`) — DZĒS. `tests/test_render_votes_matrix_json.py:494` — izsaukumā dzēš `bills=[]` un `laws_index_count=…`. `tests/test_balsojumi_client_render.py::_MINIMAL_CTX` — izņem `bills`, `bill_topics`, `laws_index_count`.

- [ ] **Step 2: Palaid — jākrīt**

Run: `.venv/Scripts/python.exe -m pytest tests/test_toggle_aria_pressed.py -v` — FAIL (cilnes poga vēl ir).

- [ ] **Step 3: Izņem cilni**

`templates/balsojumi.html.j2`: dzēs 28. rindu (`subtab-bills-list` poga) un visu `<!-- ═══ TAB 3: Bills list ═══ -->` bloku līdz tā `</div>` pirms `</section>`. Aiz `.subtab-bar` aizverošā `</div>` (ārpus `role="tablist"`):

```jinja
  <p class="muted" style="margin:0.5rem 0 0; font-size:0.9rem;"><a href="likumprojekti.html" class="muted-link">Likumprojekti un lēmumi →</a></p>
```

`assets/blv1.js` ir viena IIFE. Kā tās PIRMO apgalvojumu:

```js
  // Likumprojekti 2026-10-16 pārcēlās uz savu lapu; vecā cilnes saite ved turp.
  if (new URLSearchParams(location.search).get('tab') === 'bills') {
    location.replace('likumprojekti.html');
    return;
  }
```

Dzēs «Bills list filters» sadaļu (`var selectedBillTopics` … `switchTab('bills-list')` bloks) un trīs deleģētos klausītājus (`.bill-status-filter`, `.bill-type-filter`, `#bill-search`). `switchTab` izņem `bills-list` paneli. Pārbaude: `grep -n "bill" assets/blv1.js` → tikai pāradresācija.

`src/render/votes.py`: `render_votes(env, db, atmina_dir, votes)`; dzēs `bill_topics`, konteksta atslēgas `bills`, `bill_types`, `bill_topics`, `laws_index_count`, funkciju `_bill_types_for_filter` un nelietoto `bill_type_sort_key` importu; atjauno docstring.

`src/render/_orchestrator.py`: `render_votes(env, db, atmina_dir, votes)`.

`scripts/render_balsojumi_only.py` (Astra #8): `:40` → `render_votes(env, db, atmina_dir, votes)` (dzēs nelietotos `bills`/`laws_index_count` aprēķinus); `:45` kopēšanā pievieno `blv1.js` blakus `bmv1.js`; docstring: «likumprojekti.html renderē `--only=bills`».

Pārbaude: `grep -rn "_bill_types_for_filter\|render_votes(" src scripts tests` — tikai 4 argumentu izsaukumi.

`templates/politician.html.j2:578` («Visi Jāņa Bērziņa balsojumi» prasītu ģenitīvu, tāpēc bez vārda):

```jinja
      Rādīti jaunākie {{ votes|length }} no {{ votes_total }} balsojumiem. <a href="{{ assets_prefix }}balsojumi.html?deputats={{ politician.name|urlencode }}">Visi balsojumi ↗</a>
```

- [ ] **Step 4: Palaid — jāiziet; mutācija**

Run: `.venv/Scripts/python.exe -m pytest tests/test_toggle_aria_pressed.py tests/test_multiselect_dropdown.py tests/test_tabs_keyboard.py tests/test_generate_bills.py tests/test_balsojumi_client_render.py tests/test_render_votes_matrix_json.py tests/test_likumprojekti_page.py tests/test_politician_vote_cap.py -v` — PASS.
Mutācija: izņem pāradresācijas `if` → `test_filter_buttons_expose_pressed_state` krīt.

- [ ] **Step 5: Commit**

```bash
git add templates/balsojumi.html.j2 templates/politician.html.j2 assets/blv1.js src/render/votes.py src/render/_orchestrator.py scripts/render_balsojumi_only.py tests/test_toggle_aria_pressed.py tests/test_multiselect_dropdown.py tests/test_tabs_keyboard.py tests/test_generate_bills.py tests/test_balsojumi_client_render.py tests/test_render_votes_matrix_json.py
git commit -F .scratch/commitmsg.txt   # «Balsojumi: likumprojektu cilne izņemta, ?tab=bills → likumprojekti.html»
```

---

### Task 5: Pārbaude un dokumentācija (orķestrators)

- [ ] **Step 1:** `bash scripts/check.sh` — zaļš (ja «os error 1455»: `CHECK_PYTEST_WORKERS=3`).
- [ ] **Step 2:** Šaurs renders ar sitemap un profiliem (Astra #3): `.venv/Scripts/python.exe -m src.render --only=bills,balsojumi,likumi,static,politiki`, tad `.venv/Scripts/python.exe scripts/check_output.py` — `likumprojekti.html` ir sitemap, 0 kļūdu.
- [ ] **Step 3:** Skaitļi pret «Datu fakti»: `grep -c 'class="bill-card"' output/atmina/likumprojekti.html` == `SELECT COUNT(*) FROM saeima_bills`; posmu pogas 21/59/93/146/61/19 (vai jaunāki skaitļi, kas summējas uz Lp kopskaitu); «Biežāk grozītie likumi» pirmais = «Par iedzīvotāju ienākuma nodokli». `wc -c output/atmina/balsojumi.html` (gaidāms ~130 KB; bija 565 921 B).
- [ ] **Step 4:** Paskaties ar acīm: T3 priekšskatījums 390 × 844 un 1280 × 800, gaišā + tumšā tēma — `likumprojekti.html` (josla, posma klikšķis, likuma klikšķis), `likumi.html` (josla), `balsojumi.html`, `balsojumi.html?tab=bills`, profils ar >N balsojumiem. Ekrānuzņēmumus parādi operatoram.
- [ ] **Step 5:** `wiki/CHANGELOG.md` ieraksts ≤5 rindas (kas; kāpēc — 77 % HTML svara; josla rāda «kur tagad», ne piltuvi, jo dati kopš 27.04.; `?tab=bills` pāradresācija; audits `docs/audits/2026-10-16-matrica-likumprojekti/`). `backlog/vietne-ui.md` — matricas izņemšana kā nākamais solis (saraksts jāiemāca atvērt vecu `#vote-`).
- [ ] **Step 6:** Pirms publicēšanas — PILNS renders (josla un saites maina vairākas lapas). Deploy TIKAI pēc operatora apstiprinājuma; pēc tā `curl -sI https://atmina.lv/likumprojekti.html` → 200 un `?tab=bills` pāradresē.
