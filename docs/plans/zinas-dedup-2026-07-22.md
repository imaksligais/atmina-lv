# Ziņas dedup — viena kartīte per raksts

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** zinas.html rāda VIENU kartīti katram rakstam ar visu pieminēto politiķu tagiem — nevis atsevišķu kartīti katram (raksts, politiķis) pārim.

**Architecture:** `_fetch_news` (src/render/news.py) grupē rindas pa dokumentiem (`persons` saraksts kartītē), pāravotu republikācijas (viens kanoniskais virsraksts) apvieno ar personu+tēmu ūniju. Šablons renderē tagu sarakstu; filtru JS pāriet uz `data-persons`/`data-parties` sarakstiem, `party_members_json` vairs nevajag. Mērogs: šodien 6650 kartītes → ~3164 unikāli raksti (1261 rakstam >1 kartīte, rekords 32).

**Tech Stack:** Python (sqlite3, Jinja2), vanilla JS šablonā, pytest + characterization baselines (`tests/test_render_chars.py`).

**Konteksta fakti izpildītājam:**
- Renderēšanas ieeja: `src/render/news.py` (`_fetch_news` + `render_news`), šablons `templates/zinas.html.j2`, izsauc `src/render/_orchestrator.py:549`.
- Baseline: `tests/fixtures/render_baseline_misc.json` satur zinas.html SHA-256 no fixture DB — šī izmaiņa to APZINĀTI maina; regen ar `REGEN=1 pytest tests/test_render_chars.py`, gate ir operatora diff review (skat. Task 5).
- Mirušais kods, ko šī pārbūve novāc līdzi: `excerpt` (aprēķina, šablons nerādā), `d.summary`/`d.word_count` SELECT (nelasa; `word_count` paliek WHERE), `commentators` konteksta mainīgais un `data-commentator` atribūts (ne šablons, ne CSS, ne JS tos nelieto — pārbaudīts ar grep), N+1 topics vaicājums (viens vaicājums per dokuments).
- `documents.summary` pēc šīs izmaiņas render vairs NELASA nekur (pārbaudīts: `src/render/` grep atrod tikai citu tabulu summary kolonnas) → jāatjauno novecojušais komentārs `src/db.py:133-136`.
- UI teksti latviski; jaunie stringi šablonā iet caur LV gramatikas gate (CLAUDE.md).

**Apzināti lēmumi (nepārspriest izpildē):**
1. Republikāciju merge atslēga = kanoniskais virsraksts (strip+lower) VIEN — iepriekš bija (virsraksts, persona). Teorētisks over-merge risks diviem dažādiem rakstiem ar identisku virsrakstu — pieņemts, atbilst sākotnējam nolūkam (LETA/Diena/NRA republikācijas).
2. Kartītē redzami ne vairāk kā 5 personu tagi + "+N vēl" (32 tagi ir tikpat tizli kā 32 kartītes); filtrēšanu tas neietekmē — tā lasa `data-persons`, ne tagus.
3. Metrika "Kopā" kļūst par unikālo rakstu skaitu (~3164, bija 6650) — godīgāks skaitlis, redzams kritums lapā ir GAIDĪTS.
4. Separators `data-persons`/`data-parties` = `|` (vārdos nav `|`; tēmas paliek ar komatu kā līdz šim).
5. `only_inactive` dokumenti (visi linki inactive): paliek tikai ja dokumentam ir claims, bez tagiem — saglabā esošo uzvedību.

---

## Task 1: Testi jaunajai `_fetch_news` uzvedībai

**Files:**
- Create: `tests/test_render_news.py`

- [ ] **Step 1: Uzraksti testus (sarkani)**

```python
"""_fetch_news grouping tests — viena kartīte per raksts (zinas dedup 2026-07-22)."""

from src.db import get_db, init_db
from src.render.news import _fetch_news


def _make_db(tmp_path):
    db_path = str(tmp_path / "atmina.db")
    init_db(db_path)
    db = get_db(db_path)
    db.executescript(
        """
        INSERT INTO tracked_politicians (id, name, party, relationship_type) VALUES
            (1, 'Andris Kulbergs', 'Apvienotais saraksts', 'tracked'),
            (2, 'Dace Melbārde', 'Nacionālā apvienība', 'tracked'),
            (3, 'Jānis Komentētājs', NULL, 'journalist'),
            (4, 'Vecais Neaktīvais', NULL, 'inactive');
        INSERT INTO documents (id, content, content_hash, source_url, source_domain,
                               platform, published_at, title, word_count, language) VALUES
            (10, 'saturs A', 'hA', 'https://nra.lv/a', 'nra.lv', 'web',
             '2026-07-20', 'Valsts kontrole atsaka dalību', 100, 'lv'),
            (11, 'saturs A2', 'hA2', 'https://diena.lv/a', 'diena.lv', 'web',
             '2026-07-19', 'Valsts kontrole atsaka dalību', 100, 'lv'),
            (12, 'saturs B', 'hB', 'https://lsm.lv/b', 'lsm.lv', 'web',
             '2026-07-18', 'Cits raksts', 100, 'lv'),
            (13, 'saturs C', 'hC', 'https://lsm.lv/c', 'lsm.lv', 'web',
             '2026-07-17', 'Neaktīvā raksts', 100, 'lv');
        INSERT INTO document_politicians (document_id, politician_id, role) VALUES
            (10, 1, 'subject'), (10, 2, 'mentioned'), (10, 3, 'mentioned'),
            (11, 2, 'subject'),
            (12, 2, 'subject'), (12, 4, 'mentioned'),
            (13, 4, 'subject');
        """
    )
    db.commit()
    return db


def test_one_card_per_document(tmp_path):
    """Doc 10 (3 linki) → VIENA kartīte ar abiem politiķiem + komentētāju."""
    db = _make_db(tmp_path)
    news = _fetch_news(db)
    cards_a = [n for n in news if n["source_url"] == "https://nra.lv/a"]
    assert len(cards_a) == 1
    names = [p["name"] for p in cards_a[0]["persons"]]
    assert names == ["Andris Kulbergs", "Dace Melbārde", "Jānis Komentētājs"]
    # politiķi alfabētiski pirms komentētājiem; komentētājam karodziņš
    assert cards_a[0]["persons"][2]["is_commentator"] is True
    assert cards_a[0]["persons_str"] == "Andris Kulbergs|Dace Melbārde|Jānis Komentētājs"
    assert cards_a[0]["parties_str"] == "Apvienotais saraksts|Nacionālā apvienība"
    db.close()


def test_republished_title_merges_persons(tmp_path):
    """Doc 11 (tas pats virsraksts citā avotā) pazūd; personas apvienojas jaunākajā."""
    db = _make_db(tmp_path)
    news = _fetch_news(db)
    urls = [n["source_url"] for n in news]
    assert "https://diena.lv/a" not in urls          # republikācija sakļauta
    assert urls[0] == "https://nra.lv/a"             # jaunākais paliek pirmais
    # Melbārde bija abos — nedublējas
    names = [p["name"] for p in news[0]["persons"]]
    assert names.count("Dace Melbārde") == 1
    db.close()


def test_inactive_link_never_tags_and_inactive_only_needs_claims(tmp_path):
    """Inactive links nedod tagu; tikai-inactive doc bez claims izkrīt, ar claims paliek."""
    db = _make_db(tmp_path)
    news = _fetch_news(db)
    urls = [n["source_url"] for n in news]
    card_b = next(n for n in news if n["source_url"] == "https://lsm.lv/b")
    assert [p["name"] for p in card_b["persons"]] == ["Dace Melbārde"]  # id=4 bez taga
    assert "https://lsm.lv/c" not in urls  # tikai-inactive, bez claims → ārā
    db.execute(
        "INSERT INTO claims (opponent_id, document_id, topic, stance, confidence, "
        "reasoning, salience, source_url, claim_type) VALUES "
        "(4, 13, 'Izglītība', 'Pozīcija ar garumzīmēm ā ē ī.', 0.8, "
        "'Pamatojums ar garumzīmēm ā ē ī.', 0.5, 'https://lsm.lv/c', 'position')"
    )
    db.commit()
    news2 = _fetch_news(db)
    card_c = next(n for n in news2 if n["source_url"] == "https://lsm.lv/c")
    assert card_c["persons"] == []                    # paliek, bet bez tagiem
    assert card_c["topics_list"] == ["Izglītība"]
    db.close()
```

- [ ] **Step 2: Pārliecinies, ka testi krīt**

Run: `python -m pytest tests/test_render_news.py -q`
Expected: 3 failed — vecā `_fetch_news` atgriež rindu per (doc, persona) bez `persons` atslēgas (`KeyError: 'persons'` / len assert kļūdas).

- [ ] **Step 3: Commit (tikai testi)**

```bash
git add tests/test_render_news.py
git commit -m "test(zinas): grouped _fetch_news expectations — viena kartīte per raksts"
```

---

## Task 2: Pārbūvē `_fetch_news` + `render_news`

**Files:**
- Modify: `src/render/news.py` (pilna `_fetch_news` aizstāšana, rindas 26–108; `render_news` konteksts, rindas 122–161; noņem `import json`)

- [ ] **Step 1: Aizstāj `_fetch_news` ar grupējošo versiju**

Pilnais jaunais `_fetch_news` (aizstāj veco 26.–108. rindā; `import json` 15. rindā dzēst — pēc Task 2 to vairs nelieto):

```python
def _fetch_news(db: sqlite3.Connection) -> list[dict[str, Any]]:
    """Fetch web articles for the Ziņas page — ONE entry per article.

    Rindas nāk pa (dokuments, politiķis) pārim; salokām vienā dictā ar
    ``persons`` sarakstu. Pāravotu republikācijas (viens kanoniskais
    virsraksts, strip+lower) apvieno personu + tēmu ūnijā jaunākajā
    eksemplārā. Dokumenti, kam VISI linki ir inactive, paliek tikai tad,
    ja tiem ir claims (un renderējas bez personu tagiem).
    """
    rows = db.execute("""
        SELECT d.id, d.source_url, d.source_domain, d.published_at, d.scraped_at,
               d.title, tp.name AS politician_name, tp.party, tp.relationship_type
        FROM documents d
        JOIN document_politicians dp ON dp.document_id = d.id
        JOIN tracked_politicians tp ON dp.politician_id = tp.id
        WHERE d.platform = 'web' AND d.word_count > 30
              AND d.source_domain != 'rus.delfi.lv'
              AND (tp.party IS NOT NULL
                   OR tp.relationship_type IN ('inactive', 'journalist', 'influencer', 'neutral', 'commentator'))
        ORDER BY COALESCE(d.published_at, d.scraped_at) DESC, d.id, tp.name
    """).fetchall()

    # Divi kopvaicājumi bijušo per-dokumenta vaicājumu vietā (N+1 fix).
    topics_by_doc: dict[int, list[str]] = {}
    for doc_id, topic in db.execute(
        "SELECT DISTINCT document_id, topic FROM claims "
        "WHERE document_id IS NOT NULL AND topic IS NOT NULL "
        "ORDER BY document_id, topic"
    ).fetchall():
        topics_by_doc.setdefault(doc_id, []).append(topic)
    docs_with_claims = {
        r[0] for r in db.execute(
            "SELECT DISTINCT document_id FROM claims WHERE document_id IS NOT NULL"
        ).fetchall()
    }

    docs: dict[int, dict[str, Any]] = {}
    order: list[int] = []
    for r in rows:
        d = dict(r)
        doc = docs.get(d["id"])
        if doc is None:
            # Headline: DB title; pēdējais fallback — URL slug (rets gadījums,
            # kas izbēdzis gan forward-fix, gan backfill).
            headline = (d.get("title") or "").strip()
            if not headline:
                headline = d["source_url"].split("/")[-1].replace("-", " ").replace(".htm", "")[:100]
            doc = {
                "id": d["id"],
                "source_url": d["source_url"],
                "source_domain": d["source_domain"],
                "published_at": d["published_at"],
                "scraped_at": d["scraped_at"],
                "headline": headline,
                "date": (d["published_at"] or "")[:10],
                "persons": [],
                "topics_list": topics_by_doc.get(d["id"], []),
                "only_inactive": True,
            }
            docs[d["id"]] = doc
            order.append(d["id"])
        rel = d.get("relationship_type")
        if rel == "inactive":
            continue  # dokuments var palikt (claims gate zemāk), bet bez taga
        doc["only_inactive"] = False
        if all(p["name"] != d["politician_name"] for p in doc["persons"]):
            doc["persons"].append({
                "name": d["politician_name"],
                "slug": _slugify(d["politician_name"]),
                "party": d["party"],
                "is_commentator": rel in ("journalist", "influencer", "neutral", "commentator"),
            })

    # Republikāciju merge: viens kanoniskais virsraksts = viena kartīte;
    # personas + tēmas ūnijā paliek jaunākajā (pirmajā, jo ORDER BY DESC).
    seen_titles: dict[str, dict[str, Any]] = {}
    deduped: list[dict[str, Any]] = []
    for doc_id in order:
        doc = docs[doc_id]
        if doc["only_inactive"] and doc["id"] not in docs_with_claims:
            continue
        canonical = doc["headline"].strip().lower()
        if not canonical:
            continue
        kept = seen_titles.get(canonical)
        if kept is None:
            seen_titles[canonical] = doc
            deduped.append(doc)
        else:
            have = {p["name"] for p in kept["persons"]}
            kept["persons"].extend(p for p in doc["persons"] if p["name"] not in have)
            kept["topics_list"] = sorted(set(kept["topics_list"]) | set(doc["topics_list"]))

    for doc in deduped:
        doc["persons"].sort(key=lambda p: (p["is_commentator"], p["name"]))
        doc["persons_str"] = "|".join(p["name"] for p in doc["persons"])
        doc["parties_str"] = "|".join(sorted({
            p["party"] for p in doc["persons"] if p["party"] and not p["is_commentator"]
        }))
        doc["topics_str"] = ",".join(doc["topics_list"])
        doc["has_commentator"] = any(p["is_commentator"] for p in doc["persons"])
    return deduped
```

- [ ] **Step 2: Aizstāj `render_news` ķermeni (122.–161. rinda)**

```python
    news = _fetch_news(db)
    news_sources = sorted(set(n["source_domain"] for n in news if n.get("source_domain")))
    news_topics = sorted(set(t for n in news for t in n["topics_list"]))
    real_parties = sorted(set(
        p["party"] for n in news for p in n["persons"]
        if p["party"] and not p["is_commentator"]
    ))
    all_persons = sorted(set(p["name"] for n in news for p in n["persons"]))
    week_cutoff = (date.today() - timedelta(days=7)).isoformat()
    last_week = sum(
        1 for n in news
        if ((n.get("published_at") or n.get("scraped_at") or "") >= week_cutoff)
    )
    zinas_metrics = {
        "total": len(news),
        "last_week": last_week,
        "sources": len(news_sources),
    }
    _render_page(env, "zinas.html.j2", atmina_dir / "zinas.html", {
        "news": news,
        "sources": news_sources,
        "topics": news_topics,
        "mentioned_parties": real_parties,
        "mentioned_persons": all_persons,
        "metrics": zinas_metrics,
    })
```

(Izkrīt: `commentators`, `party_members_json` — abus šablons pēc Task 3 vairs nelieto; `commentators` nelietoja jau tagad.)

- [ ] **Step 3: Testi zaļi**

Run: `python -m pytest tests/test_render_news.py -q`
Expected: 3 passed

- [ ] **Step 4: Commit**

```bash
git add src/render/news.py
git commit -m "feat(zinas): _fetch_news grupē pa rakstiem — persons saraksts, republikāciju ūnija, N+1 fix"
```

---

## Task 3: Šablons + filtru JS

**Files:**
- Modify: `templates/zinas.html.j2` (kartītes bloks, rindas 102–130; JS, rindas 137–257)

- [ ] **Step 1: Kartītes bloks — tagu saraksts un jaunie data atribūti**

Aizstāj `{% for n in news %}` bloku (102.–130. rinda):

```html
    {% for n in news %}
    <div class="news-card" data-source="{{ n.source_domain }}" data-persons="{{ n.persons_str }}" data-parties="{{ n.parties_str }}" data-topics="{{ n.topics_str }}">
      <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:1rem;">
        <div style="flex:1; min-width:0;">
          <a href="{{ n.source_url | safe_url }}" target="_blank" rel="noopener" class="news-title" style="font-weight:600; font-size:0.95rem; line-height:1.4; display:block; margin-bottom:0.3rem;">{{ n.headline }}<span class="ext-arrow" aria-hidden="true">↗</span></a>
          <div style="font-size:0.82rem; color:var(--text-muted); display:flex; flex-wrap:wrap; gap:0.5rem; align-items:center;">
            <span>{{ n.date }}</span>
            <span style="opacity:0.4;">·</span>
            <a href="{{ n.source_url | safe_url }}" target="_blank" rel="noopener" class="news-source-link" title="Atvērt avotā">{{ n.source_domain }} ↗</a>
          </div>
        </div>
        <div style="flex-shrink:0; max-width:45%; display:flex; flex-direction:column; align-items:flex-end; gap:0.3rem;">
          {% for p in n.persons[:5] %}
          <a href="politiki/{{ p.slug }}.html" class="party-tag" style="font-size:0.78rem;{% if p.is_commentator %} opacity:0.7;{% endif %}"{% if p.is_commentator %} title="Komentētājs"{% endif %}>{{ p.name }}</a>
          {% endfor %}
          {% if n.persons|length > 5 %}
          <span class="party-tag" style="font-size:0.72rem; opacity:0.7;">+{{ n.persons|length - 5 }} vēl</span>
          {% endif %}
          {% if n.has_commentator %}
          <span class="party-tag" style="font-size:0.72rem; opacity:0.7;">Komentētājs</span>
          {% endif %}
        </div>
      </div>
      {% if n.topics_list %}
      <div style="margin-top:0.4rem; display:flex; flex-wrap:wrap; gap:0.3rem;">
        {% for t in n.topics_list %}
        <span class="topic-tag" style="font-size:0.72rem;">{{ t }}</span>
        {% endfor %}
      </div>
      {% endif %}
    </div>
    {% endfor %}
```

- [ ] **Step 2: JS — saraksta filtri, `partyMembers` ārā**

Dzēs rindu `const partyMembers = {{ party_members_json | safe_json }};` (139).
`applyFilters` iekšienē aizstāj `matchPerson`/`matchParty` blokus (167.–179. rinda):

```js
      let matchPerson = selectedPersons.size === 0;
      if (!matchPerson) {
        const persons = (card.dataset.persons || '').split('|');
        for (const p of selectedPersons) {
          if (persons.includes(p)) { matchPerson = true; break; }
        }
      }

      let matchParty = selectedParties.size === 0;
      if (!matchParty) {
        const parties = (card.dataset.parties || '').split('|');
        for (const p of selectedParties) {
          if (parties.includes(p)) { matchParty = true; break; }
        }
      }
```

`?persona=` priekšizvēles bloks (236.–250. rinda) paliek negrozīts — tas raksta `selectedPersons` un sauc `applyFilters()`, kas tagad lieto jauno ceļu.

- [ ] **Step 3: Vizuālā pārbaude lokāli**

```bash
python -m src.render --only=zinas
```

(Kanoniskais šaurais renderis — domēns `zinas`, skat. `src/render/_orchestrator.py` KNOWN_DOMAINS.) Atver `output/atmina/zinas.html` pārlūkā: virsraksts vairs neatkārtojas pēc kārtas; kartītei ar vairākiem politiķiem ir vairāki tagi; personas/partijas filtrs strādā; `zinas.html?persona=Andris%20Kulbergs` priekšizvēlas.

- [ ] **Step 4: Commit**

```bash
git add templates/zinas.html.j2
git commit -m "feat(zinas): kartītē vairāku politiķu tagi (max 5 + '+N vēl'); filtri uz data-persons/data-parties"
```

---

## Task 4: Baseline regen + pilnā verifikācija

**Files:**
- Modify: `tests/fixtures/render_baseline_misc.json` (tikai zinas.html hash)

- [ ] **Step 1: Regen**

```bash
REGEN=1 python -m pytest tests/test_render_chars.py -q
python -m pytest tests/test_render_chars.py -q
```

Expected: 1. izsaukumā skipped (regen), 2. izsaukumā visi passed.

- [ ] **Step 2: Diff gate — STOP, ja mainījies vairāk par zinas**

```bash
git diff --stat tests/fixtures/
```

Expected: TIKAI `render_baseline_misc.json` ar 1 mainītu rindu (zinas.html hash). Ja mainījies vēl kāds baseline fails vai cits hash tajā pašā failā — STOP: izmaiņa noplūdusi citās lapās; atrast cēloni pirms commit (operatora diff review ir gate, nevis akls regen — CHANGELOG-arhivs § F3d).

- [ ] **Step 3: Pilnais checks**

Run: `bash scripts/check.sh`
Expected: ruff clean, pytest visi passed, generate_public_site smoke OK.

- [ ] **Step 4: Commit**

```bash
git add tests/fixtures/render_baseline_misc.json
git commit -m "test(zinas): baseline regen — viena kartīte per raksts"
```

---

## Task 5: Novecojušā `src/db.py` komentāra fikss

**Files:**
- Modify: `src/db.py:133-136`

- [ ] **Step 1: Atjauno komentāru**

Vecais (133.–136. rinda):

```python
    # summary + is_paywall were also added to the live DB ahead of schema.sql.
    # summary is read unconditionally by render_news (src/render/news.py); a
    # fresh init_db DB without it crashes the Ziņas page. is_paywall is written
    # by video_ingest. Both must be mirrored here so fresh/test DBs match prod.
```

Jaunais:

```python
    # summary + is_paywall were also added to the live DB ahead of schema.sql.
    # summary is written by ingest paths (no render reader since the 2026-07
    # zinas dedup); is_paywall is written by video_ingest. Both stay mirrored
    # here so fresh/test DBs match prod column-for-column.
```

- [ ] **Step 2: Verifikācija + commit**

Run: `python -m pytest tests/test_render_news.py tests/test_render_chars.py -q` → visi passed / regen-skip nav.

```bash
git add src/db.py
git commit -m "docs(db): summary kolonnas komentārs — render_news to vairs nelasa"
```

---

## Ārpus tvēruma (apzināti — nav bloat)

Atsevišķi BACKLOG kandidāti, NE šī plāna daļa: lapas sadalīšana pa periodiem (10,8 MB → dedup to samazina ~2×, bet neatrisina), virsrakstu meklēšana, klikšķināmi tēmu tagi, tēmu pārklājuma godīgums (~67 % kartīšu bez tēmām), `content-visibility: auto`.
