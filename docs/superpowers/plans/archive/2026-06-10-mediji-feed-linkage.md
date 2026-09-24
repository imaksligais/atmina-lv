# Mediji ↔ feed-profilu savienojuma implementācijas plāns

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Savienot /mediji caurskatāmības lapas ar mediju X-feed profiliem un sašķelt Profilu "Iestādes un mediji" grozu — pēc spec `docs/superpowers/specs/2026-06-10-mediji-feed-linkage-design.md`.

**Architecture:** Savienojums dzīvo `sources.yaml` (`x_feeds:` saraksts pie outleta) — bez DB migrācijas. Render laikā join pret `social_accounts.handle` (autoritatīvais; NE `tp.x_handle`). Divi jauni helperi `src/render/_common.py` (`_outlet_feed_map`, `_split_org_category`), kurus lieto mediji/politicians/personas/search_index renderētāji.

**Tech Stack:** Python 3.11, sqlite3, Jinja2, pytest. Verifikācija: `bash scripts/check.sh`.

**Svarīgi izpildītājam:**
- Repo: `~\atmina`. UI valoda — latviešu; katru jaunu LV stringu pārbaudi pret gramatikas+stilistikas gate (CLAUDE.md Output Conventions).
- `sources.yaml` outlets bloks sākas ap 165. rindu; lauku kontrakts `src/outlets.py`.
- Testus dzen `python -m pytest tests/<fails> -v` no repo saknes.

---

### Task 1: `x_feeds` ekspozīcija `src/outlets.py`

**Files:**
- Modify: `src/outlets.py` (funkcija `load_outlets`, dict-bilde ap 62.–74. rindu)
- Test: `tests/test_outlets.py`

- [ ] **Step 1: Papildini testa fixture un uzraksti krītošo testu**

`tests/test_outlets.py` — `_write_yaml` lsm-ierakstā pēc rindas `website: "https://www.lsm.lv"` pievieno:

```yaml
            x_feeds: ["ltvzinas", "@ltvpanorama", ""]
```

(ar `@` un tukšo stringu — testē normalizāciju). Faila beigās pievieno:

```python
def test_load_outlets_exposes_x_feeds(tmp_path):
    by = {o["short_name"]: o for o in load_outlets(_write_yaml(tmp_path))}
    # '@' nostrippots, tukšais izmests, secība saglabāta
    assert by["lsm"]["x_feeds"] == ["ltvzinas", "ltvpanorama"]
    # outlets bez x_feeds -> tukšs saraksts (ne KeyError)
    assert by["nra"]["x_feeds"] == []
```

- [ ] **Step 2: Pārliecinies, ka tests krīt**

Run: `python -m pytest tests/test_outlets.py::test_load_outlets_exposes_x_feeds -v`
Expected: FAIL ar `KeyError: 'x_feeds'`

- [ ] **Step 3: Implementē**

`src/outlets.py` — `outlets.append({...})` dict-ā pēc `"x_handle": o.get("x_handle"),` pievieno:

```python
            "x_feeds": [str(h).strip().lstrip("@")
                        for h in (o.get("x_feeds") or [])
                        if str(h).strip().lstrip("@")],
```

Moduļa docstring (1.–11. rinda) papildini ar teikumu: `x_feeds saraksta X kontus (tracked org-feedus), kas pieder outletam — savienojums uz social_accounts.handle.`

- [ ] **Step 4: Testi zaļi**

Run: `python -m pytest tests/test_outlets.py -v`
Expected: visi PASS (arī vecie trīs)

- [ ] **Step 5: Commit**

```bash
git add src/outlets.py tests/test_outlets.py
git commit -m "feat(outlets): x_feeds lauks — outleta X kontu saraksts no sources.yaml"
```

---

### Task 2: Helperi `_outlet_feed_map` + `_split_org_category` (`_common.py`)

**Files:**
- Modify: `src/render/_common.py` (pievieno aiz `_persona_category`, ~398. rinda)
- Create: `tests/test_feed_linkage.py`

- [ ] **Step 1: Uzraksti krītošos testus**

Create `tests/test_feed_linkage.py`:

```python
from src.db import get_db, init_db
from src.render._common import _outlet_feed_map, _split_org_category

OUTLETS = [
    {"short_name": "lsm", "slug": "lsm", "name": "LSM",
     "x_feeds": ["ltvzinas", "ltvpanorama"]},
    {"short_name": "nra", "slug": "nra", "name": "Neatkarīgā", "x_feeds": []},
]


def _seed(db_path):
    init_db(db_path)
    db = get_db(db_path)
    db.execute("INSERT INTO tracked_politicians (id,name,relationship_type) "
               "VALUES (170,'LTV Ziņas','organization')")
    db.execute("INSERT INTO tracked_politicians (id,name,relationship_type) "
               "VALUES (204,'Latvijas armija (NBS)','organization')")
    # handle DB-ā ar citu burtu reģistru nekā x_feeds -> case-insensitive match
    db.execute("INSERT INTO social_accounts (opponent_id,platform,handle,feed_type) "
               "VALUES (170,'x','LTVzinas','relay')")
    db.execute("INSERT INTO social_accounts (opponent_id,platform,handle,feed_type) "
               "VALUES (204,'x','Latvijas_armija','first_party')")
    db.commit()
    return db


def test_outlet_feed_map_matches_case_insensitive(tmp_path):
    db = _seed(str(tmp_path / "t.db"))
    m = _outlet_feed_map(db, OUTLETS)
    assert set(m) == {170}                      # NBS handle nav nevienā x_feeds
    assert m[170] == {"short_name": "lsm", "name": "LSM", "slug": "lsm"}


def test_outlet_feed_map_empty_without_x_feeds(tmp_path):
    db = _seed(str(tmp_path / "t.db"))
    assert _outlet_feed_map(db, [{"short_name": "nra", "slug": "nra",
                                  "name": "NRA", "x_feeds": []}]) == {}


def test_split_org_category():
    assert _split_org_category("Iestādes un mediji", 170, {170}) == "Mediji"
    assert _split_org_category("Iestādes un mediji", 204, {170}) == "Iestādes"
    # ne-org kategorijas iziet cauri nemainītas
    assert _split_org_category("Deputāti", 1, {170}) == "Deputāti"
```

- [ ] **Step 2: Pārliecinies, ka testi krīt**

Run: `python -m pytest tests/test_feed_linkage.py -v`
Expected: FAIL ar `ImportError: cannot import name '_outlet_feed_map'`

- [ ] **Step 3: Implementē `_common.py`**

Aiz `_persona_category` pievieno:

```python
def _outlet_feed_map(
    db: sqlite3.Connection,
    outlets: list[dict[str, Any]] | None = None,
) -> dict[int, dict[str, str]]:
    """opponent_id -> {short_name, name, slug} outletam, kuram pieder profila
    X konts (sources.yaml ``x_feeds`` x social_accounts.handle join).

    Handle salīdzinājums case-insensitive; join iet caur social_accounts.handle
    (autoritatīvais), NE tracked_politicians.x_handle (legacy, klusi diverģē —
    sk. CLAUDE.md schema invariants). Dublēts handle divos outletos -> pirmais
    uzvar + stderr brīdinājums. outlets=None ielādē no sources.yaml.
    """
    if outlets is None:
        from src.outlets import load_outlets
        outlets = load_outlets()
    handle_to_outlet: dict[str, dict[str, Any]] = {}
    for o in outlets:
        for h in o.get("x_feeds") or []:
            hl = h.lower()
            if hl in handle_to_outlet and handle_to_outlet[hl]["short_name"] != o["short_name"]:
                print(f"[mediji] @{h} divos outletos — paliek "
                      f"{handle_to_outlet[hl]['short_name']}", file=sys.stderr)
                continue
            handle_to_outlet.setdefault(hl, o)
    if not handle_to_outlet:
        return {}
    m: dict[int, dict[str, str]] = {}
    for pid, handle in db.execute(
            "SELECT opponent_id, handle FROM social_accounts WHERE platform = 'x'"):
        o = handle_to_outlet.get((handle or "").lower())
        if o is not None:
            m.setdefault(pid, {"short_name": o["short_name"],
                               "name": o["name"], "slug": o["slug"]})
    return m


def _split_org_category(category: str, pid: int, media_feed_ids: set[int]) -> str:
    """'Iestādes un mediji' -> 'Mediji' (outleta feeds) vai 'Iestādes' (pārējie).
    Citas kategorijas iziet cauri nemainītas. Sk. spec 2026-06-10."""
    if category != "Iestādes un mediji":
        return category
    return "Mediji" if pid in media_feed_ids else "Iestādes"
```

Pārbaudi `_common.py` importus augšā: vajag `import sys` un `import sqlite3` (ja vēl nav — pievieno; `Any` no typing tur jau ir).

- [ ] **Step 4: Testi zaļi**

Run: `python -m pytest tests/test_feed_linkage.py -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add src/render/_common.py tests/test_feed_linkage.py
git commit -m "feat(render): _outlet_feed_map + _split_org_category helperi feed-savienojumam"
```

---

### Task 3: `x_feeds` reālajā `sources.yaml`

**Files:**
- Modify: `sources.yaml` (outlets bloks, ~165. rinda)

- [ ] **Step 1: Pievieno x_feeds trim esošajiem outletiem**

`lsm` ierakstā pēc `x_handle: "ltvzinas"`:

```yaml
    x_feeds: ["ltvzinas", "ltvpanorama", "ltvdefacto", "Krustpunkta", "KNL_LTV1"]
```

`leta` ierakstā pēc tā `x_handle` rindas:

```yaml
    x_feeds: ["letanewslv"]
```

`nra` ierakstā pēc tā `x_handle` rindas:

```yaml
    x_feeds: ["nralv"]
```

- [ ] **Step 2: Pārbaudi, ka viss vēl ielādējas un handles atbilst DB**

Run: `PYTHONIOENCODING=utf-8 python -c "from src.outlets import load_outlets; [print(o['short_name'], o['x_feeds']) for o in load_outlets()]"`
Expected: lsm 5 feedi, leta 1, nra 1, pārējiem `[]`

Run (handle sakritības pārbaude pret DB; jāatgriež 7 rindas):

```bash
PYTHONIOENCODING=utf-8 python -c "
import sqlite3
from src.outlets import load_outlets
db = sqlite3.connect('data/atmina.db')
want = {h.lower() for o in load_outlets() for h in o['x_feeds']}
have = {h.lower() for (h,) in db.execute(\"SELECT handle FROM social_accounts WHERE platform='x'\")}
print('match:', len(want & have), 'no', len(want)); print('truksts DB:', want - have)"
```

Expected: `match: 7 no 7`, `truksts DB: set()`

- [ ] **Step 3: Commit**

```bash
git add sources.yaml
git commit -m "data(sources): x_feeds savienojums lsm/leta/nra outletiem"
```

---

### Task 4: "X konti un raidījumi" sadaļa outlet lapā

**Files:**
- Modify: `src/render/mediji.py`
- Modify: `templates/medijs.html.j2` (pēc Caurskatāmības `{% endif %}`, 44. rinda)
- Modify: `assets/style.css` (pie `.fact-card` bloka, ~5207. rinda)
- Test: `tests/test_render_mediji.py`

- [ ] **Step 1: Uzraksti krītošos testus**

`tests/test_render_mediji.py`: OUTLETS fixture lsm-dict papildini ar `"x_feeds": ["tv3zinas_x"]` un nra-dict ar `"x_feeds": []`. (Apzināti izmantojam fixture politiķi id=3 'TV3 Ziņas'; handle izdomāts testam.) `_seed` beigās pirms `db.commit()` pievieno:

```python
    db.execute("INSERT INTO social_accounts (opponent_id,platform,handle,feed_type) "
               "VALUES (3,'twitter','TV3zinas_X','relay')")
```

(`platform='twitter'` — reālā DB vēsturiski glabā šo vērtību, ne `'x'`; atklāts Task 3 verifikācijā.)

Faila beigās pievieno:

```python
def test_fetch_outlet_feeds(tmp_path):
    from src.render.mediji import _fetch_outlet_feeds
    db = _seed(str(tmp_path / "t.db"))
    feeds = _fetch_outlet_feeds(db, OUTLETS)
    assert [f["name"] for f in feeds["lsm"]] == ["TV3 Ziņas"]
    assert feeds["lsm"][0]["pubs"] == 1        # doc10 junction rinda
    assert feeds["lsm"][0]["slug"] == "tv3-zinas"
    assert feeds["nra"] == []


def test_render_mediji_feed_section(tmp_path):
    from src.render.mediji import render_mediji
    db = _seed(str(tmp_path / "t.db"))
    out = tmp_path / "site"
    out.mkdir()
    render_mediji(_env(), db, out, OUTLETS)
    lsm = (out / "mediji" / "lsm.html").read_text(encoding="utf-8")
    assert "X konti un raidījumi" in lsm
    assert "../politiki/tv3-zinas.html" in lsm
    nra = (out / "mediji" / "nra.html").read_text(encoding="utf-8")
    assert "X konti un raidījumi" not in nra
```

- [ ] **Step 2: Pārliecinies, ka testi krīt**

Run: `python -m pytest tests/test_render_mediji.py -v`
Expected: divi jaunie FAIL (`ImportError: ... '_fetch_outlet_feeds'`), vecie PASS

- [ ] **Step 3: Implementē `mediji.py`**

Importu blokā: `import sys` un `_common` importam pievieno `ASSETS_DIR`. Aiz `_fetch_coverage` pievieno:

```python
def _fetch_outlet_feeds(db: sqlite3.Connection,
                        outlets: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """short_name -> outleta X feedu kartītes (vārds, slug, handle, publikāciju
    skaits, foto), kārtotas pēc publikācijām dilstoši. Join caur
    social_accounts.handle (case-insensitive); x_feeds handle bez DB rindas ->
    stderr brīdinājums + izlaists (validation-level skip, ne kļūda)."""
    handle_to_short: dict[str, str] = {}
    for o in outlets:
        for h in o.get("x_feeds") or []:
            handle_to_short.setdefault(h.lower(), o["short_name"])
    feeds: dict[str, list[dict[str, Any]]] = {o["short_name"]: [] for o in outlets}
    if not handle_to_short:
        return feeds
    photo_dir = ASSETS_DIR / "photos"
    matched: set[str] = set()
    for handle, name, pubs in db.execute(
        """SELECT sa.handle, tp.name,
                  (SELECT COUNT(*) FROM document_politicians dp
                   WHERE dp.politician_id = tp.id) AS pubs
           FROM social_accounts sa
           JOIN tracked_politicians tp ON tp.id = sa.opponent_id
           WHERE sa.platform IN ('twitter', 'x')"""):
        short = handle_to_short.get((handle or "").lower())
        if short is None:
            continue
        matched.add((handle or "").lower())
        slug = _slugify(name)
        feeds[short].append({
            "name": name, "slug": slug, "handle": handle, "pubs": pubs,
            "has_photo": (photo_dir / f"{slug}.jpg").exists(),
        })
    for h, short in handle_to_short.items():
        if h not in matched:
            print(f"[mediji] x_feeds @{h} ({short}) nav social_accounts rindas — izlaists",
                  file=sys.stderr)
    for lst in feeds.values():
        lst.sort(key=lambda f: -f["pubs"])
    return feeds
```

`render_mediji` sākumā pēc `cov = _fetch_coverage(db, outlets)` pievieno `feeds = _fetch_outlet_feeds(db, outlets)`, un detaļlapas `_render_page` kontekstā pievieno `"feeds": feeds[o["short_name"]],`.

UZMANĪBU: `_fetch_coverage` uzliek `db.row_factory = sqlite3.Row` — `_fetch_outlet_feeds` tuple-unpacking strādā arī ar Row, bet izsauc to PIRMS `_fetch_coverage` vai atstāj unpacking pēc indeksiem nemainīgu (Row atbalsta gan vienu, gan otru; nekas nav jāmaina, piezīme drošībai).

- [ ] **Step 4: Templates + CSS**

`templates/medijs.html.j2` — starp Caurskatāmības `{% endif %}` (44. rinda) un `<div class="medijs-cover-head">` ievieto:

```jinja
  {% if feeds %}
  <h2 class="medijs-h2">X konti un raidījumi</h2>
  <div class="feed-grid">
    {% for f in feeds %}
    <a class="feed-card" href="../politiki/{{ f.slug }}.html">
      {% if f.has_photo %}
      <img class="feed-avatar" src="../assets/photos/{{ f.slug }}.jpg" alt="{{ f.name }}" loading="lazy" decoding="async" width="40" height="40">
      {% else %}
      <span class="feed-avatar feed-avatar-ph" aria-hidden="true">{{ f.name[0]|upper }}</span>
      {% endif %}
      <span class="feed-ident">
        <span class="feed-name">{{ f.name }}</span>
        <span class="feed-sub">@{{ f.handle }}{% if f.pubs %} · {{ f.pubs }} publikācijas{% endif %}</span>
      </span>
    </a>
    {% endfor %}
  </div>
  {% endif %}
```

`assets/style.css` — aiz `.fact-foot` bloka (atrodams tūlīt aiz ~5215. rindas; tie paši `--surface`/`--border` tokeni kā `.fact-card`, lai sadaļa vizuāli pieder lapai):

```css
.feed-grid {
  display:grid; grid-template-columns:repeat(auto-fill, minmax(230px, 1fr));
  gap:0.75rem; margin-bottom:1.5rem;
}
.feed-card {
  display:flex; align-items:center; gap:0.7rem; padding:0.7rem 0.9rem;
  background:var(--surface); border:1px solid var(--border); border-radius:var(--radius);
  text-decoration:none; color:inherit; transition:border-color .15s ease;
}
.feed-card:hover { border-color:var(--accent-brand); }
.feed-avatar { width:40px; height:40px; border-radius:50%; object-fit:cover; flex:none; }
.feed-avatar-ph {
  display:flex; align-items:center; justify-content:center;
  background:var(--border); color:var(--text-muted);
  font-weight:600; font-size:0.95rem;
}
.feed-ident { display:flex; flex-direction:column; min-width:0; }
.feed-name { font-size:0.9rem; font-weight:600; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.feed-sub { font-size:0.75rem; color:var(--text-muted); }
```

- [ ] **Step 5: Testi zaļi**

Run: `python -m pytest tests/test_render_mediji.py -v`
Expected: visi PASS

- [ ] **Step 6: Commit**

```bash
git add src/render/mediji.py templates/medijs.html.j2 assets/style.css tests/test_render_mediji.py
git commit -m "feat(mediji): X kontu un raidijumu sadala outlet lapa"
```

---

### Task 5: Outlet čips feed-profila galvenē

**Files:**
- Modify: `src/render/politicians.py` (renderēšanas cikls, ~979.–1012. rinda)
- Modify: `templates/politician.html.j2:44-48`

- [ ] **Step 1: Implementē kontekstu**

`politicians.py` — `_common` importam pievieno `_outlet_feed_map`. `render_politicians` funkcijā PIRMS `for idx, p in enumerate(politicians):` cikla pievieno:

```python
    feed_outlets = _outlet_feed_map(db)  # opponent_id -> outlet {name, slug}
```

`_render_page` kontekstā (pie `"politician": p,`) pievieno:

```python
            "feed_outlet": feed_outlets.get(p["id"]),
```

- [ ] **Step 2: Templates čips**

`templates/politician.html.j2` 44.–48. rinda — esošo `{% if party_meta %}...{% else %}...{% endif %}` aizstāj ar:

```jinja
          {% if party_meta %}
          <a href="../partijas/{{ party_meta.short_name|lower }}.html" class="profile-party-tag">{{ politician.party }}</a>
          {% elif feed_outlet %}
          <a href="../mediji/{{ feed_outlet.slug }}.html" class="profile-party-tag">{{ feed_outlet.name }}</a>
          {% else %}
          <span class="profile-party-tag">{{ politician.party or 'Nav norādīts' }}</span>
          {% endif %}
```

(Partijas zaru NEMAINI — tikai iesprauž `elif`. Nulle jauna CSS — `profile-party-tag` jau ir saites stils.)

- [ ] **Step 3: Smoke pārbaude**

Run: `PYTHONIOENCODING=utf-8 python -c "from src.generate import generate_public_site; generate_public_site(only={'politiki'})"`
(`only` ir `set[str]`; domēns `politiki` ir `KNOWN_DOMAINS` — `src/render/_orchestrator.py:98`)

```bash
grep -c "mediji/lsm.html" output/atmina/politiki/ltv-zinas.html
grep -c "Nav norādīts" output/atmina/politiki/ltv-zinas.html
```

Expected: pirmais ≥1, otrais 0. Pretpārbaude — NBS paliek bez čipa saites: `grep -c "mediji/" output/atmina/politiki/latvijas-armija-nbs.html` → 0 (faila vārdu pārbaudi ar `ls output/atmina/politiki/ | grep armija`).

- [ ] **Step 4: Commit**

```bash
git add src/render/politicians.py templates/politician.html.j2
git commit -m "feat(politiki): outlet saite partijas slota org-feediem (Nav noradits -> mediji/<slug>)"
```

---

### Task 6: Profilu groza šķelšana Mediji / Iestādes + rail tilts

**Files:**
- Modify: `src/render/personas.py` (`_fetch_personas` ~73. rinda; `_CATEGORY_ORDER` ~120. rinda)
- Modify: `templates/personas.html.j2` (rail cikls, ~49.–51. rinda)
- Modify: `assets/style.css`
- Test: `tests/test_feed_linkage.py` (papildina)

- [ ] **Step 1: Uzraksti krītošo testu**

`tests/test_feed_linkage.py` beigās (izmanto Task 2 `_seed`). Monkeypatch mērķis ir vārds, ko `personas.py` importē (`from src.render._common import _outlet_feed_map` → patcho `personas_mod._outlet_feed_map`), jo bez tā `_fetch_personas` ielādētu reālo `sources.yaml`:

```python
def test_fetch_personas_splits_org_bucket(tmp_path, monkeypatch):
    import src.render.personas as personas_mod
    db = _seed(str(tmp_path / "t.db"))
    monkeypatch.setattr(
        personas_mod, "_outlet_feed_map",
        lambda d: {170: {"short_name": "lsm", "name": "LSM", "slug": "lsm"}})
    rows = personas_mod._fetch_personas(db)
    cats = {p["name"]: p["category"] for p in rows}
    assert cats["LTV Ziņas"] == "Mediji"
    assert cats["Latvijas armija (NBS)"] == "Iestādes"
```

- [ ] **Step 2: Pārliecinies, ka tests krīt**

Run: `python -m pytest tests/test_feed_linkage.py::test_fetch_personas_splits_org_bucket -v`
Expected: FAIL (`AttributeError` vai kategorija == "Iestādes un mediji")

- [ ] **Step 3: Implementē `personas.py`**

Importam no `_common` pievieno `_outlet_feed_map, _split_org_category`. `_fetch_personas` — pēc `coalition_map = get_coalition_map(db)` pievieno:

```python
    media_feed_ids = set(_outlet_feed_map(db))
```

un pēc `p["category"] = _persona_category(...)` izsaukuma:

```python
        p["category"] = _split_org_category(p["category"], p["id"], media_feed_ids)
```

`render_personas` — `_CATEGORY_ORDER` ierakstu `"Iestādes un mediji"` aizstāj ar diviem: `"Mediji", "Iestādes"`:

```python
    _CATEGORY_ORDER = [
        "Deputāti", "Amatpersonas", "Žurnālisti", "Analītiķi",
        "Ietekmētāji", "Mediji", "Iestādes", "Citi",
    ]
```

Moduļa docstring rindu `(Deputāti, Amatpersonas, Žurnālisti, Ietekmētāji, Analītiķi, Citi)` papildini ar `Mediji, Iestādes`.

- [ ] **Step 4: Rail tilts uz /mediji**

`templates/personas.html.j2` — rail ciklā (49.–51. rinda) aiz `</button>`... cikla ķermenī:

```jinja
          {% for cat, cnt in category_counts.items() %}
          <button type="button" class="pnv1-rail-row" data-axis="category" data-value="{{ cat }}">
            ... (esošais saturs nemainās)
          </button>
          {% if cat == 'Mediji' %}
          <a class="pnv1-rail-sublink" href="mediji.html">Mediju caurskatāmība →</a>
          {% endif %}
          {% endfor %}
```

`assets/style.css` (pie pnv1 rail stiliem — atrodi `.pnv1-rail-row` bloku un pievieno aiz tā):

```css
.pnv1-rail-sublink {
  display:none; padding:0.3rem 0.75rem 0.3rem 1.5rem;
  font-size:0.78rem; color:var(--text-muted); text-decoration:none;
}
.pnv1-rail-sublink:hover { color:var(--accent-brand); }
.pnv1-rail-row.is-active + .pnv1-rail-sublink { display:block; }
```

(CSS-only atklāšana: saite redzama tikai, kad blakus esošais "Mediji" rail-row ir `is-active` — `pnv1.js` NAV jāaiztiek.)

- [ ] **Step 5: Testi zaļi + personas regresijas**

Run: `python -m pytest tests/test_feed_linkage.py tests/test_personas_v2.py -v`
Expected: visi PASS (`test_personas_v2` izmanto `_persona_category` tieši — tā nemainījās)

- [ ] **Step 6: Commit**

```bash
git add src/render/personas.py templates/personas.html.j2 assets/style.css tests/test_feed_linkage.py
git commit -m "feat(personas): Iestades un mediji -> Mediji/Iestades skelsana + rail tilts uz mediji.html"
```

---

### Task 7: search_index — kategoriju kartējums

**Files:**
- Modify: `src/render/search_index.py` (`_CATEGORY_TO_CAT` 57.–65. rinda; `_fetch_search_index` ~97. rinda; docstring 16.–19. rinda)
- Test: `tests/test_search_index.py` (apskati esošo paternu; pievieno vienu testu)

- [ ] **Step 1: Implementē**

`_CATEGORY_TO_CAT` papildini (veco atslēgu ATSTĀJ — drošības tīkls):

```python
_CATEGORY_TO_CAT = {
    "Deputāti": 0,
    "Amatpersonas": 0,
    "Žurnālisti": 1,
    "Analītiķi": 1,
    "Ietekmētāji": 1,
    "Citi": 1,
    "Iestādes un mediji": 2,
    "Mediji": 2,
    "Iestādes": 2,
}
```

Importam no `_common` pievieno `_outlet_feed_map, _split_org_category` (boundary "imports only from _common and stdlib" saglabājas). `_fetch_search_index` — pirms politicians cikla:

```python
    media_feed_ids = set(_outlet_feed_map(db))
```

un pēc `category = _persona_category(...)`:

```python
        category = _split_org_category(category, r["id"], media_feed_ids)
```

Docstring 16.–19. rindu papildini: `2 = iestāde/medijs (Mediji, Iestādes; vēsturiski "Iestādes un mediji")`.

- [ ] **Step 2: Testi**

Run: `python -m pytest tests/test_search_index.py -v`
Expected: visi PASS (cat vērtības nemainās — abas jaunās kartējas uz 2; ja kāds tests pin-o kategoriju label, atjaunini to)

- [ ] **Step 3: Commit**

```bash
git add src/render/search_index.py tests/test_search_index.py
git commit -m "fix(search): Mediji/Iestades kategorijas karte uz cat=2 (typeahead sekcija nemainas)"
```

---

### Task 8: wiki — ģenerēta `mediji.md` + indeksa saite

**Files:**
- Modify: `src/wiki.py` (indeksa bloks 1029.–1037. rinda; `wiki_sync` ķermenis + docstring 1081.–1091. rinda)

- [ ] **Step 1: Lapas builderis**

`src/wiki.py` — pievieno moduļa līmenī (pie pārējiem `_build_*` helperiem; atrodi tos ar grep `def _build_`):

```python
def _build_mediji_page() -> str:
    """wiki/mediji.md — konfigurācijas spogulis no sources.yaml outlets:.
    Tikai config (load_outlets), BEZ DB joiniem — skaitļi dzīvo publiskajā
    lapā mediji.html; šī ir operatora reģistrs (spec 2026-06-10)."""
    from src.outlets import load_outlets
    outlets = load_outlets()
    lines = [
        "# Mediji",
        "",
        f"_Konfigurācijas spogulis no `sources.yaml` (`outlets:`); atjaunots: {now_lv()}_",
        "",
        "Caurskatāmības fakti un pārklājums dzīvo publiskajā vietnē "
        "(`mediji.html`, `mediji/<slug>.html`); šī lapa ir operatora reģistrs.",
        "",
        "| Medijs | Tips | Hosti | X feedi |",
        "|---|---|---|---|",
    ]
    for o in outlets:
        feeds = ", ".join(f"@{h}" for h in o.get("x_feeds") or []) or "—"
        lines.append(f"| {o['name']} | {o['type'] or '—'} | "
                     f"{', '.join(o['hosts'])} | {feeds} |")
    return "\n".join(lines) + "\n"
```

(`now_lv` jau ir importēts wiki.py — pārbaudi ar grep; ja nav, importē no `src.db`.)

- [ ] **Step 2: Indeksa saite + rakstīšana**

Indeksa blokā (1029.–1037. rinda) komentāru un rindu aizstāj ar:

```python
    # Mediji — config-driven (sources.yaml outlets:); wiki/mediji.md ir
    # wiki_sync ģenerēts konfigurācijas spogulis (sk. _build_mediji_page).
    from src.outlets import load_outlets
    n_outlets = len(load_outlets())
    if n_outlets:
        lines.append(
            f"- [[mediji|Mediji]] — {n_outlets} mediju caurskatāmības profili "
            "(publiskā vietne `mediji.html`)"
        )
```

`wiki_sync` ķermenī — atrodi vietu, kur tiek rakstīts `index.md` (grep `index.md` wiki.py), un blakus pievieno:

```python
    (wiki / "mediji.md").write_text(_build_mediji_page(), encoding="utf-8")
```

`wiki_sync` docstring "FULLY overwritten" sarakstā pievieno `wiki/mediji.md`.

- [ ] **Step 3: Smoke**

Run: `PYTHONIOENCODING=utf-8 python -c "from src.wiki import wiki_sync; wiki_sync()"`
Expected: `wiki/mediji.md` eksistē ar 9 tabulas rindām; `wiki/index.md` satur `[[mediji|Mediji]]`. Pārbaudi arī, ka wiki_lint (ja check.sh to dzen) neflagē orphan — saite no index to sedz.

- [ ] **Step 4: Commit**

```bash
git add src/wiki.py
git commit -m "feat(wiki): generets mediji.md konfiguracijas spogulis + indeksa wikilink"
```

---

### Task 9: TV3 + IR outleti (operatora gate) + CHANGELOG + pilnā verifikācija

**Files:**
- Modify: `sources.yaml` (divi jauni outlet ieraksti — no @outlet-researcher rezultātiem, PĒC operatora apstiprinājuma)
- Modify: `wiki/CHANGELOG.md`

- [ ] **Step 1: OPERATORA GATE — TV3 + IR YAML review**

@outlet-researcher bloki (IR gatavs, TV3 gaidāms) jāparāda operatoram; tikai pēc apstiprinājuma ievieto `sources.yaml` outlets blokā alfabētiskā loģikā pie pārējiem. NEDEPLOY personas-šķelšanu pirms šī soļa — citādi TV3 Ziņas/IR žurnāls nonāk "Iestādēs" (spec 4. sadaļas priekšnoteikums).

- [ ] **Step 2: CHANGELOG ieraksts**

`wiki/CHANGELOG.md` augšā (zem virsraksta, esošo ierakstu stilā) pievieno sadaļu `## 2026-06-10 — Mediji ↔ feed-profilu savienojums`: x_feeds lauks; outlet čips partijas slotā; "Iestādes un mediji" (2026-06-09) sašķelts par Mediji/Iestādes (sg cat=2 nemainās); ģenerēta wiki/mediji.md; TV3+IR outleti. Atsauce uz spec failu.

- [ ] **Step 3: Pilnā verifikācija**

Run: `bash scripts/check.sh`
Expected: ruff + pytest + generate smoke visi zaļi. Ja kas krīt — labo pirms commit.

- [ ] **Step 4: Vizuālā pārbaude (pirms deploy — cilvēka acs)**

Run: `PYTHONIOENCODING=utf-8 python -c "from src.generate import generate_public_site; generate_public_site(only={'mediji','personas','politiki'})"` (šaurais scope — pilnais render tikai release/baseline) un atver lokāli: `output/atmina/mediji/lsm.html` (feed kartes), `output/atmina/politiki/ltv-zinas.html` (čips), `output/atmina/personas.html` (raila Mediji/Iestādes + sublink). Paziņo operatoram screenshot-review pirms deploy (`--no-delete` default).

- [ ] **Step 5: Commit**

```bash
git add sources.yaml wiki/CHANGELOG.md
git commit -m "data(sources): TV3 + IR outleti (outlet-researcher, operatora apstiprinats) + CHANGELOG"
```
