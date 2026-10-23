# «Atradumi» — īso izmeklējumu sadaļa: īstenošanas plāns

> **Aģentiem:** obligātā apakšprasme — `superpowers:subagent-driven-development` (ieteicams) vai `superpowers:executing-plans`. Soļi ar `- [ ]` izsekošanai. Palīgi uz Opus; neviens palīgs neizpilda `git stash`, `git checkout --`, `git restore`, `git reset`.

**Mērķis:** vietnē parādās sadaļa «Atradumi» — īsas, avotiem piesaistītas izmeklējumu lapas (viens jautājums, 3–5 fakti, shēma), ko var pārsūtīt viena saite, nevis viss dienas pārskats.

**Arhitektūra:** jauna sistēma NETIEK būvēta. «Atradums» ir `content/analizes/*.md` fails ar `kind: atradums` frontmatter laukā. Esošais analīžu ceļš (`src/render/analyses.py` → `templates/blog-post.html.j2`, saraksts `templates/analizes.html.j2` dashboard domēnā) iegūst: tipa iezīmi, savu cilni sarakstā, saites no politiķu profiliem (tā pati `politicians` sasaiste kā sintēzēm) un satura vārtus, kas atsaka nepilnīgu atradumu.

**Tehnoloģijas:** Python 3.12, Jinja2, markdown, pytest, Playwright (shēmas PNG). Vienmēr `.venv/Scripts/python.exe`.

**Spec:** `backlog/vietne-ui.md` § «Atradumi» (2026-10-16) + šī plāna sadaļa «Lēmumi». Atsevišķa dizaina dokumenta nav — operators 2026-10-16 lūdza plānu tieši.

## Lēmumi (operatora sarunā 2026-10-16; pārbaudīt sesijas sākumā ar vienu jautājumu, ja kas mainījies)

1. **Kāpēc:** X izplatās īsi izmeklējumi (Toca 27 VID deklarācijas 09-19 ~25,8k skatījumu; turpinājums par 60 amatpersonām 09-20 ~10k; tiesas lieta par policijas izpostītu dārzu 09-09 ~5,6k; pilsonības lieta 10-16). Vietnē no tiem ir tikai `content/analizes/vad-izmeklesana-2026.md`.
2. **Forma:** virsraksts = jautājums; 3–5 fakti, katrs ar pirmavota saiti; shēma (attēls); obligāta sadaļa `## Ko mēs neapgalvojam`; datums; `## Labojumi` (var būt tukša līdz pirmajam labojumam).
3. **Rakstīts ar roku**, publicē tikai ar operatora atļauju (kā sintēzes un pārskati). Līdz atļaujai fails stāv ar `draft: true` (esošie T15 vārti, `tests/test_analyses_draft.py`).
4. **Privātpersonas:** augstāka latiņa — tikai oficiāli reģistri un tikai tas, kas tieši skar publisku lēmumu (balsojumu, piešķīrumu, spriedumu). Privātpersonas vārdu lapā raksta tikai, ja tas jau ir oficiālā publiskā lēmumā par viņu (piem., Saeimas lēmums par pilsonību); citādi apraksta («pensionāre Viļānu novadā»). Šaubās — operators izlemj.
5. **Pirmās trīs lapas:** pilsonības lieta (10-16), Toca deklarācijas (09-19), tiesas lieta par dārzu (09-09). Izejmateriāli: `docs/tweet_bank/2026-10-16-visvanati-pilsoniba-piezimes.md` + `-shema.html`; `docs/audits/2026-09-19-tocs-vad-izmeklesana.md` + `docs/tweet_bank/2026-09-19-tocs-vad-reply-social.md`; dārza lietai repo NAV nekā — tikai publiskais tvīts `https://x.com/AtminaLV/status/2097630586810548466` (teksts: `https://api.fxtwitter.com/status/2097630586810548466`), avoti jāatrod no jauna (Senāta 2022-04-21 spriedums, Administratīvās apgabaltiesas 2021-01 spriedums, mediji).

## Globālie ierobežojumi

- Publiskā anonimitāte: neviena operatora identificējoša informācija lapās, commit tekstā, docs (CLAUDE.md § Standing Decisions).
- Nav inline JavaScript; JS tikai `assets/*.js` (`tests/test_no_inline_js.py`). Jauns ārējs hosts → `assets/_headers` (šim darbam nevajag).
- UI darbā VIENMĒR `good-css` prasme un tās prasības katra palīga briefā; lapa pievilcīga mobilajā un datorā; ekrānuzņēmumi abos.
- LV gramatikas + stilistikas vārti visam mūsu tekstam; citāti verbatim.
- Narrow render (`--only=analizes,dashboard,politiki,static`); deploy tikai ar operatora atļauju; `bash scripts/deploy.sh --dry-run --no-delete` pirms.
- Pēc veidņu maiņas `tests/test_render_chars.py` baseline drifts ir GAIDĀMS — REGEN pēc faila galvenes instrukcijas un commit kopā ar maiņu; īsta regresija = STOP.
- Testi: viens e2e tests katrai redzamai uzvedībai, uzrakstīts PIRMS koda; pierādīts ar mutāciju (atgriez labojumu → tests krīt).
- Commit ziņas caur failu (`git commit -F`), beigās `Co-Authored-By` rinda.
- `_load_analyses()` iet KATRĀ renderā (`_orchestrator.py:401`, arī `--only=blog,dashboard,static`), tāpēc publicējams atradums, kas neiziet vārtus, aptur arī ikdienas rutīnas renderu — tas ir apzināti (stop beats write); NEietin to try/except. Autors tur `draft: true`, līdz vārti iziet. 2026-10-16: neviens esošais `content/analizes/*.md` nesatur `kind:`.

## Review Focus

1. **Atradums bez `## Ko mēs neapgalvojam` vai ar <2 ārējām saitēm** — renders apstājas ar kļūdu, kas nosauc failu (nevis klusi izlaiž vai publicē). Tests: Task 1.
2. **`draft: true` atradums** — nav ne sarakstā, ne sitemap, ne profilā, ne sākumlapā, un vārti to NEvērtē (melnrakstam drīkst trūkt sadaļu). Tests: Task 1.
3. **`politicians` vērtība, kas atbilst diviem politiķiem** (kopīgs uzvārds) — nesaista nevienu, brīdina stderr (esošā `_map_syntheses_to_politicians` uzvedība). Tests: Task 3.
4. **Tiešā saite `analizes.html#atradumi`** atver pareizo cilni (to dalīs sociālajos tīklos). Tests: Task 2.
5. **Vecās analīzes bez `kind`** paliek cilnē «Tematiskās» ar iezīmi «Tematiskā analīze» — nekas nepārvietojas. Tests: Task 2.

---

### Task 1: Ielāde — `kind`, `politicians` un atraduma satura vārti

**Faili:**
- Modificēt: `src/render/analyses.py` (`_load_analyses`, ~36–89)
- Tests: `tests/test_atradumi.py` (jauns)

**Interfeisi:**
- Producē: katram ierakstam `analysis["kind"]` ∈ {`"analysis"`, `"atradums"`} (noklusējums `"analysis"`), `analysis["politicians"]: list[str]` (noklusējums `[]`). Nederīgs publicējams atradums → `ValueError` ar faila nosaukumu un trūkstošo prasību.

- [ ] **1. solis: uzraksti krītošo testu**

```python
"""«Atradumi» — content/analizes/*.md ar kind: atradums (plāns 2026-10-16)."""
from __future__ import annotations

import pytest

from src.render import analyses

VALID_BODY = (
    "Teksts ar [avots A](https://www.lsm.lv/a) un [avots B](https://titania.saeima.lv/b).\n\n"
    "## Ko mēs neapgalvojam\n\nNeapgalvojam pārkāpumu.\n"
)


def _write(d, name, *, kind="atradums", draft=False, body=VALID_BODY, politicians=None):
    fm = [f"title: Vai {name}?", "date: 2026-10-17", "description: Apraksts"]
    if kind:
        fm.append(f"kind: {kind}")
    if draft:
        fm.append("draft: true")
    if politicians:
        fm.append("politicians: [" + ", ".join(politicians) + "]")
    (d / f"{name}.md").write_text("---\n" + "\n".join(fm) + "\n---\n\n" + body, encoding="utf-8")


@pytest.fixture
def analizes_dir(tmp_path, monkeypatch):
    d = tmp_path / "analizes"
    d.mkdir()
    monkeypatch.setattr(analyses, "CONTENT_DIR", tmp_path)
    return d


def test_kind_and_politicians_are_loaded(analizes_dir):
    _write(analizes_dir, "a1", politicians=["kulbergs"])
    _write(analizes_dir, "vecs", kind=None)
    by = {a["slug"]: a for a in analyses._load_analyses()}
    assert by["a1"]["kind"] == "atradums" and by["a1"]["politicians"] == ["kulbergs"]
    assert by["vecs"]["kind"] == "analysis" and by["vecs"]["politicians"] == []


def test_atradums_without_disclaimer_section_stops_render(analizes_dir):
    _write(analizes_dir, "bez", body="[a](https://a.lv/x) [b](https://b.lv/y)\n")
    with pytest.raises(ValueError, match="bez.md.*Ko mēs neapgalvojam"):
        analyses._load_analyses()


def test_atradums_with_one_source_stops_render(analizes_dir):
    _write(analizes_dir, "viens", body="[a](https://a.lv/x)\n\n## Ko mēs neapgalvojam\n\nx\n")
    with pytest.raises(ValueError, match="viens.md.*avot"):
        analyses._load_analyses()


def test_draft_atradums_is_not_validated_and_not_listed(analizes_dir):
    _write(analizes_dir, "melnraksts", draft=True, body="tikai sākums\n")
    assert analyses._load_analyses() == []
```

- [ ] **2. solis: palaid — jākrīt**

Run: `.venv/Scripts/python.exe -m pytest tests/test_atradumi.py -v -p no:cacheprovider`
Gaidāms: FAIL (`KeyError: 'kind'`, un `ValueError` netiek mests).

- [ ] **3. solis: minimālā īstenošana** — `_load_analyses()` iekšā PĒC `draft` pārbaudes (draft tiek izlaists pirms vārtiem) un pirms `analyses.append`:

```python
_EXT_LINK = re.compile(r"\]\((https?://[^)\s]+)\)")
ATRADUMS_MIN_SOURCES = 2

def _validate_atradums(name: str, body_md: str) -> None:
    """Publicējams atradums bez atrunas vai avotiem = STOP (CLAUDE.md «Stop beats write»)."""
    if not re.search(r"^##\s+Ko mēs neapgalvojam\s*$", body_md, flags=re.M):
        raise ValueError(f"{name}: atradumam trūkst sadaļas «## Ko mēs neapgalvojam»")
    n = len(set(_EXT_LINK.findall(body_md)))
    if n < ATRADUMS_MIN_SOURCES:
        raise ValueError(f"{name}: atradumam vajag ≥{ATRADUMS_MIN_SOURCES} dažādas ārējas avotu saites, atrastas {n}")
```

Un ierakstā: `kind = "atradums" if fm.get("kind") == "atradums" else "analysis"`; ja `kind == "atradums"` → `_validate_atradums(md_file.name, body)`; `"kind": kind, "politicians": [str(p) for p in (fm.get("politicians") or [])]`. Nezināma `kind` vērtība (ne `atradums`, ne tukša) → `ValueError` ar faila nosaukumu (drukas kļūda nedrīkst klusi kļūt par «analysis»).

- [ ] **4. solis: palaid — jāiziet;** tad mutācija: izkomentē `_validate_atradums` izsaukumu → abi vārtu testi krīt; atjauno.
- [ ] **5. solis: palaid `tests/test_analyses_draft.py`** — jāiziet (esošās analīzes nemainās).
- [ ] **6. solis: commit** — `src/render/analyses.py`, `tests/test_atradumi.py`.

### Task 2: Lapa, saraksta cilne «Atradumi» un sākumlapa

**Faili:**
- Modificēt: `src/render/analyses.py` (`render_analyses`, ~92–138): `type_label` = `"Atradums"`, `back_href` = `"../analizes.html#atradumi"` atradumiem.
- Modificēt: `src/render/dashboard.py` (`render_dashboard` ~472–486 un `analysis_items` ~285–317): sadala `analyses` divos sarakstos (`atradumi`, `analyses` bez atradumiem); `analysis_items` atradumam liek `kicker="Atradums"`, `kicker_href="analizes.html#atradumi"`, `cta="Lasīt atradumu"`.
- Modificēt: `templates/analizes.html.j2`: jauna cilne `tab-atradumi` / panelis `anal-atradumi` PIRMS «Sintēzes»; kartīte — tā pati `analysis-feat` struktūra ar kicker «Atradums» un CTA «Lasīt atradumu →».
- Modificēt: `assets/anv1.js`: `switchAnalTab` un hash saraksts papildināts ar `atradumi`.
- Modificēt: `assets/style.css` tikai, ja vajag (good-css; nekādu jaunu breakpoint kāpņu).
- Tests: `tests/test_atradumi.py` (e2e caur `generate_public_site`).

**Interfeisi:**
- Patērē: `analysis["kind"]` no Task 1.
- Producē: `analizes.html` satur `id="anal-atradumi"`; atraduma lapa `analizes/<slug>.html` ar iezīmi «Atradums».

- [ ] **1. solis: krītošais e2e tests** — pievieno `tests/test_atradumi.py`. Fixture DB un render palīgs: nokopē `fixture_db` un `_render` paraugu no `tests/test_render_saeima.py` (25–66), mainot `only={"analizes", "dashboard"}` un papildus `monkeypatch.setattr(analyses, "CONTENT_DIR", content_root)`.

```python
def test_atradums_has_own_tab_card_and_label(tmp_path, monkeypatch, fixture_db, analizes_dir):
    _write(analizes_dir, "a1")
    _write(analizes_dir, "vecs", kind=None, body="Vecā analīze.\n")
    out = _render_site(tmp_path, monkeypatch, fixture_db, only={"analizes", "dashboard"})
    listing = (out / "analizes.html").read_text(encoding="utf-8")
    panel = listing.split('id="anal-atradumi"', 1)[1].split('<div id="anal-', 1)[0]
    assert "analizes/a1.html" in panel and "analizes/vecs.html" not in panel
    tematic = listing.split('id="anal-tematic"', 1)[1].split('<div id="anal-', 1)[0]
    assert "analizes/vecs.html" in tematic and "analizes/a1.html" not in tematic
    page = (out / "analizes" / "a1.html").read_text(encoding="utf-8")
    assert "Atradums" in page and "analizes.html#atradumi" in page


def test_atradumi_hash_opens_tab():
    js = (Path(__file__).parents[1] / "assets" / "anv1.js").read_text(encoding="utf-8")
    assert "'atradumi'" in js and "anal-atradumi" in js
```

(`_render_site` = `_render` paraugs, kas atgriež `out / "atmina"`.) Pārbaudīts 2026-10-16: `generate_public_site(db_path=<fixture>, only={"dashboard", "analizes"})` no `load_render_fixture_sql()` uzrenderē `analizes.html`. Pēc testa: Playwright pārbaude ar rokām (nav tests) — atver `analizes.html#atradumi` lokāli, cilne aktīva, bultas strādā (`assets/tabs-v1.js`).

- [ ] **2. solis: palaid — jākrīt** (`anal-atradumi` nav).
- [ ] **3. solis: īsteno** sarakstā minētās izmaiņas. Cilnes skaitītājs `{{ atradumi|length }}`. Tukšam sarakstam cilni NErāda (`{% if atradumi %}`), lai pirms pirmās publicēšanas nav tukšas cilnes.
- [ ] **4. solis: palaid — jāiziet;** mutācija: atradumu atpakaļ sarakstā `analyses` → pirmais tests krīt.
- [ ] **5. solis: `test_render_chars` baseline** — palaid `.venv/Scripts/python.exe -m pytest tests/test_render_chars.py -q`; drifts tikai `analizes.html`/`index.html` → REGEN pēc faila instrukcijas, pārbaudi diff ar acīm.
- [ ] **6. solis: ekrānuzņēmumi** `analizes.html#atradumi` 1200 px un 390 px (gaišā + tumšā tēma) — skaties pats.
- [ ] **7. solis: commit.**

### Task 3: Saites no politiķu profiliem

**Faili:**
- Modificēt: `src/render/_orchestrator.py` (~401–403, ~540): `pid_to_atradumi = _map_syntheses_to_politicians([a for a in analyses if a["kind"] == "atradums"], politicians)`; nodod `render_politicians`.
- Modificēt: `src/render/politicians.py` (`render_politicians` ~1094, konteksts ~1197): jauns arguments `pid_to_atradumi: dict[int, list[dict]] | None = None`, konteksts `"atradumi": pid_to_atradumi.get(p["id"], [])`.
- Modificēt: `templates/politician.html.j2` (~936): bloks «Atradumi» virs «Saistītās sintēzes» — saraksts ar saiti `../analizes/{{ a.slug }}.html`, virsrakstu, datumu (thumb, ja ir attēls: `../images/analizes/{{ a.image_filename|image_variant('thumb') }}`).
- Tests: `tests/test_atradumi.py`.

**Interfeisi:**
- Patērē: `analysis["politicians"]`, `analysis["slug"]` (Task 1); `_map_syntheses_to_politicians(items, politicians) -> dict[int, list[dict]]` (`src/render/syntheses.py:262`, nemainīta — tā lasa tikai `slug` un `politicians`).

- [ ] **1. solis: krītošais tests** — no fixture DB paņem vienu aktīvu politiķi (slug), uzraksti atradumu ar `politicians: [<pilnais slug>]` un otru ar uzvārdu, kas fixture DB ir diviem politiķiem (ja tāda nav, pievieno testā otru `tracked_politicians` rindu ar to pašu uzvārdu caur `store_*`/fixture SQL). Render `only={"politiki"}`.

```python
def test_profile_lists_atradums_and_ambiguous_token_links_nobody(tmp_path, monkeypatch, fixture_db, analizes_dir, capsys):
    slug, other_slugs = _pick_politician_and_namesakes(fixture_db)
    _write(analizes_dir, "a1", politicians=[slug])
    _write(analizes_dir, "a2", politicians=[slug.rsplit("-", 1)[-1]])  # kopīgs uzvārds
    out = _render_site(tmp_path, monkeypatch, fixture_db, only={"politiki"})
    prof = (out / "politiki" / f"{slug}.html").read_text(encoding="utf-8")
    assert "../analizes/a1.html" in prof and "../analizes/a2.html" not in prof
    assert "a2" in capsys.readouterr().err
```

(`_pick_politician_and_namesakes` — palīgs testā: SQL uz fixture DB, atgriež slugu un namesake slugus; ja namesake nav, ievieto to.)

- [ ] **2. solis: jākrīt.** **3. solis: īsteno.** **4. solis: jāiziet;** mutācija: neieliec `atradumi` kontekstā → krīt.
- [ ] **5. solis: baseline** `test_render_chars` (politiķu lapas) — REGEN tikai, ja drifts ir šis bloks. **6. solis: commit.**

### Task 4: Shēmas PNG no HTML (bez rokas Playwright)

**Faili:**
- Izveidot: `scripts/render_shema.py`
- Modificēt: `.claude/commands/social-thread.md:48` (rokas soļa vietā — šī komanda)

**Interfeisi:** `render_shema.py <in.html> <out.png> [--width 1600 --height 900]` — atver failu Chromium caur `file://`, gaida fontus (`document.fonts.ready`), ekrānuzņēmums. Atradumam: `<out.png>` = `output/images/analizes/<slug>.png` (+ `-light.png`, ja ir gaišā versija); variantus renders izveido pats (`_ensure_image_variants`).

- [ ] **1. solis:** uzraksti skriptu (≤40 rindas, `playwright.sync_api`). Tests NEtiek rakstīts (plāns: plāna wrapper, ne loģika).
- [ ] **2. solis:** pārbaude ar rokām: `.venv/Scripts/python.exe scripts/render_shema.py docs/tweet_bank/2026-10-16-visvanati-shema.html .scratch/shema-test.png` → atver PNG, salīdzini ar `output/images/threads/2026-10-16-visvanati-shema.png` (fonti, izmērs 1600×900).
- [ ] **3. solis: commit.**

### Task 5: Satura vārti atradumiem (LV lints + pārlasīšana)

**Faili:**
- Izveidot: `scripts/lint_analysis.py` — `lint_lv_style_report()` (`src/lv_style.py`) pār md tekstu bez frontmatter un bez citātiem («…» iekš blockquote); izdrukā atradumus un saucējus (`coverage_pct`, `rules_run/rules_total`); izejas kods 1, ja atradumi > 0.
- Modificēt: `wiki/operations/quality-bars.md` § Sintēze un analīzes — viena rinda: «Atradumam (`kind: atradums`): `scripts/lint_analysis.py` = 0; § Ierāmējuma vārti attiecas uz virsrakstu; privātpersonas — Lēmumi 4.».
- Modificēt: `.claude/agents/quality-reviewer.md` — viena rinda § H: atradumu lapas pārlasa tāpat kā pārskatus, ar saucēju.

- [ ] **1. solis:** skripts; pārbaude ar rokām uz `content/analizes/vad-izmeklesana-2026.md` (saucējs > 0, izejas kods nozīmīgs). Tests netiek rakstīts — `lint_lv_style` jau testēts; šis ir wrapper.
- [ ] **2. solis:** docs rindas. **3. solis: commit.**

### Task 5b: OG kartīte atradumam mūsu stilā (operators 2026-10-17)

Operators: atraduma OG attēlam jābūt **mūsu stilā kā citām OG kartītēm** (sepija, Source Serif, `atmina.lv` kājene ar URL — paraugs `output/atmina/assets/og/pretruna-*.png`), nevis apgrieztai shēmai (`images/analizes/<slug>-og.jpg`, ko šobrīd dod `_ensure_image_variants`).

**Faili:**
- Modificēt: `src/render/analyses.py` (`render_analyses`) — katram atradumam OG darbs caur `src/render/_common/og_render.py::render_og_images` (inkrementāls, manifests `og-hashes.json`), izeja `assets/og/atradumi/<slug>.png`; `post_ctx` padod šo ceļu `blog-post.html.j2` og blokam (og:image + twitter:image).
- Izveidot vai paplašināt: OG veidne pēc `templates/og-section.html.j2` / `og-card.html.j2` parauga (`_og_base.html.j2`): kicker «Atradums», virsraksts-jautājums, datums, kājene `atmina.lv` + `atmina.lv/analizes/<slug>`.
- Tests: `tests/test_atradumi.py` — e2e caur `_render_site`: atraduma lapas `og:image` rāda uz `assets/og/atradumi/<slug>.png`, fails eksistē; vecā analīze (bez `kind`) paliek ar savu `-og.jpg` (nekas nemainās).

- [ ] 1. krītošais tests → 2. jākrīt → 3. īsteno (good-css prasme; veidnē nekādu inline JS) → 4. jāiziet + mutācija (atradumam padod veco og ceļu → krīt) → 5. PNG apskate ar acīm blakus `pretruna-13.png` (ekrānuzņēmums atskaitē) → 6. commit.

### Task 6: Pirmās trīs lapas (saturs — operatora vārti katrai)

Katrai lapai atsevišķi, šādā secībā: pilsonības lieta → Toca deklarācijas → dārza lieta. **Dārza lieta — operatora izvēle, var izlaist** (nav izsekota politiķa; operators 10-16: «varbūt nav tik aktuāli») — pirms izpētes jautā.

- [ ] **1. solis: melnraksts** `content/analizes/<slug>.md` ar `kind: atradums`, `draft: true`, `politicians: [...]` (tikai politiķi, pilnie slugi), `tags`, `image: <slug>.png`. Saturs tikai no izejmateriāliem (Lēmumi 5); katrs skaitlis pārrēķināts no avota; katrai saitei HTTP 200 (skaits atskaitē).
- [ ] **2. solis: privātpersonu pārbaude** (Lēmumi 4) — saraksts: katra nosauktā persona → publisks lēmums, kurā vārds jau ir, vai aprakstošs aizstājējs.
- [ ] **3. solis: shēma** — HTML pēc `src/graphics/templates/izpete-shema.html` (good-css) → `scripts/render_shema.py` → `output/images/analizes/<slug>.png`.
- [ ] **4. solis: vārti** — `scripts/lint_analysis.py` = 0; `@quality-reviewer` § H + § E pār lapu (saucējs); `@devils-advocate` pār virsrakstu un faktiem («vai virsraksts apgalvo vairāk nekā fakti?»).
- [ ] **5. solis: operatora atļauja** (`AskUserQuestion`: lapas kopsavilkums, attēls, § H tabula). Tikai pēc «jā» — noņem `draft: true`.
- [ ] **6. solis:** render `--only=analizes,dashboard,politiki,static` → `deploy.sh --dry-run --no-delete` → deploy → `verify_host.py --base https://atmina.lv` → `curl -I` lapai un OG kartītei `assets/og/atradumi/<slug>.png` (200; apskati — mūsu stilā kā citas OG kartītes). Commit.

---

## Pašpārbaude (izpildīta, rakstot plānu)

- Spec segums: forma (T1 vārti + T6), cilne un sākumlapa (T2), profili (T3), shēma (T4), vārti un privātpersonas (T5, T6), publicēšanas pauze (T6.5).
- Tipi: `kind`, `politicians`, `atradumi`, `pid_to_atradumi` — vienādi visos uzdevumos.
- Atklāts jautājums operatoram (nebloķē T1–T5): vai «Atradumi» likt arī galvenajā navigācijā blakus «Analīzes» (`templates/base.html.j2:90`). Noklusējums: NĒ — tikai cilne un sākumlapas josla, kamēr nav ≥3 publicētu lapu.
