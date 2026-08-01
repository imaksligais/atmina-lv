# Dienas rutīna

> **Kanoniskā procedūra ir `/dienas-rutina` prasme** (`.claude/commands/dienas-rutina.md`), nevis šis fails. Šeit dzīvo atsauces detaļas, ko prasme neietver: kodu piemēri, argumentu semantika, triāžas saraksti, ad-hoc plūsmas. Kad abi runā par vienu soli un nesakrīt — **prasme uzvar**, un šis fails jālabo.
>
> Kāpēc tas rakstīts: 2026-08-01 audits atrada, ka šis fails bija aizdreifējis četrās vietās (auto-apstiprinātas pretrunas, mantots pārskata temats, trūkstoši publicēšanas vārti, pilnais renders), un tas ir pirmā saite `operacijas.md` Rutīnas tabulā — tātad sesija nonāca šeit pirms prasmes. Kopijas dreifē; šī rindkopa nosaka, kura ir noteicošā.

Kad lietotājs saka "izpildi dienas rutīnu", izpildi VISUS soļus secībā.

> **Laika noteikums (standing decision):** ielāde notiek visu dienu; claim ekstrakcija + dienas pārskats TIKAI pēcpusdienā (~15:00+ LV, nekad no rīta). Rīta "0/N analizēti" ir gaidītais stāvoklis, nevis kļūda.

## Solis 0: Interlock pārbaude (30 sekundes)

Pirms sākt rutīnu, atbildi uz trim jautājumiem:
1. **Ko es sagaidu atrast šodien?** (Ja atbilde ir "to pašu ko vakar" — esi uzmanīgs)
2. **Kas mani pārsteigtu?** (Ja nekas nepārsteidz jau nedēļu — iespējams esi interlock)
3. **Vai es izvairos no kādas personas/tēmas analīzes?** (Ja jā — sāc ar to)

Šis nav aģenta solis — to izdara cilvēks. Aģents nevar pārbaudīt operatora metaprogrammu.

## Solis 1: Ielāde (ingest)

**Kanoniskais ceļš — `scripts/morning_ingest.py`, visi pieci soļi ar vienu komandu** (RSS + X laika līnijas + pieminējumi + Vēstnesis + politiķu junction backstop, ar laika telemetriju). Claim ekstrakcija ir izlaista pēc dizaina (tā notiek pēcpusdienā — sk. Laika noteikumu faila sākumā).

```bash
.venv/Scripts/python.exe scripts/morning_ingest.py
```

**Izejas kods ir jēdzīgs (kopš 2026-08-01):** `0` = visi pieci soļi OK, `1` = vismaz viens kritis. Skripts beigās drukā `KOPSAVILKUMS: N/5 soļi OK` un nosauc kritušos vārdā; `ALL DONE` parādās tikai pie tīra skrējiena. Ja šo palaiž automatizēti, **pārbaudi izejas kodu** — līdz 2026-08-01 tas vienmēr bija 0, tāpēc pilna ingesta kļūme izskatījās pēc labas dienas, un neievāktais tajā dienā ekstrakcijas rindā vairs neatgriežas (`get_pending_politicians(days=1)`).

**Avārijas / atkļūdošanas variants — trīs atsevišķi izsaukumi.** Lieto tikai tad, ja skripts pats ir jāapiet (piemēram, viena soļa izolētai atkļūdošanai). **Brīdinājums: apstāšanās pēc otrā izsaukuma neatstāj nekādas pēdas** — `logs` tabulā nav ne veiksmes, ne kļūmes ieraksta, un dienas beigās tas izskatās kā "pieminējumu tajā dienā nebija" (noticis 2026-07-22, 07-28 un 07-31, pēdējā reizē trīs reizes pēc kārtas). Ja lieto šo ceļu, izpildi visus trīs izsaukumus un pēc tam pārbaudi ingest žurnālu.

```python
from src.ingest import ingest_all; ingest_all()
from src.social import fetch_all_twitter; fetch_all_twitter()
from src.social import fetch_all_mentions; fetch_all_mentions()  # PĒC twitter — rate limits
```

5. solis `link_politicians_to_documents(days=2)` ir idempotents — skenē tikai dokumentus, kuriem nav neviena `document_politicians` rindiņa. Aizpilda relay-konta tweet'us (LTV Ziņas, kuru `social.py` relay zars atstāj `politician_links=[]`) un citus untracked-author dokumentus, kuriem ingest neuzstādīja junction. 2-dienu logs dod buferi, ja rutīna izlaista. Funkcija arī piedāvā `rescan_all=True` re-skenēšanai pēc jaunu politiķu pievienošanas — to manuāli, ne caur morning_ingest.

Manuāls atsevišķi: Latvijas Vēstnesis JL — pilnā kanoniskā plūsma (komanda, karogi, idempotence, junction detaļas): [[operacijas#Latvijas Vēstnesis (manuāla plūsma)|operacijas.md]]. Šeit to neatkārtojam, lai abas kopijas nedreifē.

Ingest auto-matches politicians via `match_politician()` (name_forms). Shared surnames return None if ambiguous. Sources with `keyword_filter: true` (e.g. TVNet) only store political content.

Pēc ingest automātiski tiek papildināts ingest žurnāls — mēneša rotācijas mape `wiki/log-ingest/<YYYY-MM>.md`. Pārbaudi ar:
```python
from src.ingest_log import read_ingest_log
print("\n".join(read_ingest_log(last_n=10)))
```

> **Avotu framing** — skatīt [[source-framing]] detalizētu aprakstu par katra avota perspektīvu.

## Solis 2: Pozīciju analīze

```python
from src.analyze import get_pending_politicians, get_politician_documents, get_existing_claims, save_analysis
pending = get_pending_politicians(days=1)  # [{id, name, party, doc_count, last_analyzed}, ...]
```

For each politician with unanalyzed docs:

```python
docs = get_politician_documents(pid, days=1)
claims = get_existing_claims(pid, days=90)  # for contradiction detection
result = save_analysis(
    pid=3, analysis_date="2026-04-06", sentiment=0.0,  # ALWAYS 0.0
    topics=["Vēlēšanas"], quotes=["quote"], brief="Analysis...", confidence=0.9,
    claims=[{
        "document_id": 2534, "topic": "Vēlēšanas",
        "stance": "Atbalsta manuālu balsu skaitīšanu",
        "quote": "optional", "confidence": 0.85, "reasoning": "Why distinct",
        "salience": 0.85, "source_url": "https://...", "stated_at": "2026-04-06",
    }],
    empty_doc_ids=[2535, 2536],  # docs looked at but no extractable position
)  # Returns: {status, analysis_id, claim_ids, contradiction_ids, failures}
```

**Svarīgi par `empty_doc_ids`:** katram dokumentam, ko analizēji bet neizvilki claims (ceremoniāls, dublikāts, trešās puses citāts), padod tā ID šajā sarakstā. Bez tā docs paliek `reviewed_at IS NULL` un atkal atgriežas backlog.

**`claim_type`:** `save_analysis` pieņem neobligātu `claim_type` katrā claim dict. Noklusējums `'position'` — `@claim-extractor` to nekad nepārraksta. `'saeima_vote'` rezervēts `@saeima-tracker` un tiek uzlikts automātiski no `generate_claims_from_votes()`. Ja tev liekas, ka jāuzstāda manuāli, kaut kas cits ir nepareizi — pajautā. Detaļas un vēsture: [[CHANGELOG]].

**Circuit breaker:** ja vienam politiķim ir vairāk par **12** dokumentiem dienā (limitu samazinājām no 33 uz 2026-04-22 pēc batch-drift diagnostikas, sk. [[CHANGELOG]]), analizē tikai pirmās 12 (augstākais salience). Par >5 docs ieteicams dispečēt paralēlus sub-aģentus **pa vienam dokumentam** — katrs sub-aģents iegūst tīru kontekstu, kas atbilst diagnostikas ceļam, kurā izolētais prompt pareizi apstrādā indirect references 100%. Ja backlog lielāks, palaid rutīnu vairākas reizes.

**Indirect-reference gate (2026-04-22):** `save_analysis` auto-prepend `NEEDS_REVIEW:` marķieri reasoning laukam, ja tas satur frāzes kā `nav paša pozīcij`, `pašam nav ekstraktēj`, `bare retweet`, `pure retweet`, `does not speak`, `tikai pieminē`. Claim tiek saglabāts operatora triāžai (nevis nomests — false-positive uz likumīgiem "netiešs citāts caur LETA" gadījumiem). Piedalies self-check pirms save_analysis: pārlasi savu reasoning un, ja tā pati atzīst indirectness, atgriez `empty`.

**Session limit & drift check:** ~8 politiķi vienā sesijā maksimums. Ja redzi `"diacritic validation failed"` kļūdas — tas ir context drift: **NEKAVĒJOTIES STOP** un sāc jaunu sesiju (drift ir autoregresīvs). Validācija (`src/quality.py`) noraida stripped tekstu jau save/store līmenī — nekad neiegūst DB. Kāpēc šī robeža un kā validācija strādā — [[CHANGELOG]].

> **Confidence & salience** — skatīt [[rubrics]] detalizētas skalas.

**Partijas-maiņas signāls (pēc ekstrakcijas, pirms pārskata):** ja dienas pozīcijās ir izstāšanās/pārejas valoda (topic `Koalīcija un partijas`: `izstājas`, `pamet partiju`, `pievienojas`, `izslēgts no`) vai `@claim-extractor` atskaitē ir "party-change signāls" rinda — pārbaudi `tracked_politicians.party` pret jauno faktu. Lauks no ziņām nesinhronizējas automātiski (T6; Vergina 2026-06-29: pārskats vienlaikus ziņoja izstāšanos no JV un rādīja viņu kā JV). Labojums vienmēr manuāls: `UPDATE` + pāra `data/rollback_*.sql` tajā pašā commitā.

## Solis 3: Pretrunu pārbaude (OBLIGĀTA, MANUĀLA)

`save_analysis()` pretrunas NEDETEKTĒ automātiski — ≥0.6 zars `src/analyze.py` ir apzināts no-op hook. Katram jaunam claim PAŠAM jāizsauc `search_similar_claims()` ar virziena `claim_type_filter` (CLAUDE.md invariants #7) un jāizvērtē rezultāti:

```python
from src.tools import store_contradiction
store_contradiction(opponent_id=5, old_claim_id=10, new_claim_id=55,
    topic="pārvaldība", summary="Said X before, now says Y",
    severity="minor_shift", salience=0.6)  # minor_shift | reversal | direct_contradiction
```

## Solis 4: @devils-advocate pārskats (OBLIGĀTS)

Pēc claim extraction, palaid `@devils-advocate` lai pārskatītu VISAS jaunās pretrunas (detected_at = šodien). Katrai pretrunai piešķir robustness score:

- **Strong** — tieša pretruna ar skaidru citātu, augsts salience
- **Medium** — ticama pretruna, konteksts mazliet neskaidrs
- **Weak** — iespējama pretruna, bet konteksts vai laiks var izskaidrot
- **False** — nav īsta pretruna, jānoņem vai jāpazemina

Weak/False pretrunas pazemināt salience (`UPDATE contradictions SET salience=0.1 WHERE id=?`). Pārskatītās atzīmēt kā pārskatītas — **bet NE kā apstiprinātas**:

```python
from src.db import get_db
db = get_db()
db.execute("UPDATE contradictions SET reviewed=1 WHERE id=?", (contra_id,))
db.commit()
```

**`confirmed` paliek 0.** `reviewed=1` nozīmē „@devils-advocate to ir izskatījis"; `confirmed=1` nozīmē „atmina to publiski apgalvo" — tie ir divi dažādi lēmumi, un otro pieņem operators, ne aģents. CLAUDE.md eskalācijas noteikums 3: „store survivors `confirmed=0`. Never auto-confirm." Līdz 2026-08-01 šeit stāvēja `reviewed=1, confirmed=1` vienā rindā, kas nozīmēja, ka rutīna publicēja katru izdzīvojušo pretrunu bez cilvēka lēmuma.

**Šis solis ir obligāts** — `@quality-reviewer` bloķēs rutīnu ja ir jaunas pretrunas ar `reviewed=0`.

## Solis 5: Spriedžu reģistrēšana (OBLIGĀTS)

Pārbaudi starppartiju dinamiku. Ja politiķi uzbrūk viens otram vai ir savstarpējas spriedzes:

```python
from src.db import store_tension
store_tension(source_pid, target_pid, topic, description,
    tension_type="uzbrukums",
    source_url="https://...",   # MUST be a real documents.source_url
    target_url="https://...")   # optional, same validation
# Types: spriedze (tension), uzbrukums (attack), atbalsts (support)
```

**CRITICAL — source_url/target_url must be real:** `store_tension` validē, ka abas URL eksistē `documents.source_url` tabulā, un noraida halucinētus URL ar `ValueError`. NEKAD nerakstīt URL no galvas. Pārbaudi pirms zvana:

```python
# For the source document you're reading, grab its URL from docs query:
doc = db.execute(
    "SELECT id, source_url FROM documents WHERE source_url LIKE ? ORDER BY scraped_at DESC LIMIT 1",
    (f'%{handle}%',)
).fetchone()
source_url = doc["source_url"]
```

Redzams Pārskati → Spriedzes tabā un Saites grafā.

## Solis 6: Konteksta piezīmes

Konteksta piezīmes rakstīt neitrāli — faktiski, bez partejiskas perspektīvas. Add NEW context notes (never update old). Topic names uppercase. Source = actual URL.

```python
from src.tools import store_context_note
store_context_note(topic="Imigrācija", note_type="context",
    content="Trend description...", source="https://actual-url.com")
# note_type: context | polling | event | tip | correction | daily_brief | weekly_brief
```

## Solis 7: Dienas pārskats

```python
from src.briefs import daily_brief_topic
store_context_note(topic=daily_brief_topic("2026-04-06"), note_type="daily_brief",
    content="...", source="atmina analīze 2026-04-06")
```

**Nekad neraksti tematu ar roku.** Kanoniskā forma ir `dienas analīze YYYY-MM-DD`, un to būvē `daily_brief_topic()` (`src/briefs.py:48`). Rakstīts no galvas, tas aizdreifē uz `dienas pārskats {date}` — formu, ko neviens lasītājs nemeklē, tāpēc meklējums klusi neatgriež neko un kļūda neizmet izņēmumu. Tā jau vienreiz iztukšoja Telegram pārskata punktus (BACKLOG 2026-07-16, salabots 2026-07-25), un DB šobrīd glabā 47 pārskatus zem nepareizās formas pret 68 zem pareizās.

> **Formāts** — pilnais SAGLABĀ/PAPILDINI likumu apraksts dzīvo @brief-writer aģenta failā (`.claude/agents/brief-writer.md`).

**Atpakaļdatēta pozīcija pieder VIENAI dienai, un vēlāks pārskats to apslāpē.** `_BRIEF_DAY_CLAIM_SQL` (`src/briefs.py:94`) ieskaita claim dienā, ja `stated_at` ir tā diena VAI tas ievākts tajā dienā, nav vecāks par 7 dienām **un tā `stated_at` dienai nav uzrakstīts VĒLĀKS pārskats**. Sekas, kas nav acīmredzamas un ko nedrīkst pārsteigt:

- claim, kas saglabāts nākamajā dienā par vakardienas izteikumu, dabiski nonāk **šodienas** pārskatā — tā tam jābūt;
- ja kāds pārģenerē un UPDATE-o VAKARDIENAS pārskatu, tā `created_at` kļūst jaunāks par claim, `NOT EXISTS` vārti nostrādā, un claim **pazūd no šodienas pārskata**.

Dublēšanās nav nevienā variantā, bet izvēle ir **binārā** — viena vai otra diena, ne abas. Tāpēc publicēta pārskata atjaunošana nav bezmaksas darbība: tā klusi izņem pozīciju no nākamās dienas. Etalons: 2026-08-02 operatora lēmums NEATJAUNOT pārskatu #398 pēc claim #615821 saglabāšanas — daļēji tieši šā mehānisma dēļ, daļēji tāpēc, ka retroaktīvi ielikt publicētā pārskatā tikai vienu pusi divpusējai apmaiņai nozīmētu publicēt vienpusēju versiju.

One per day (overwrites same-day). All sections mandatory. Use actual DB data.

## Solis 8: Featured image ģenerēšana

Ja `## Vizuālais brief` bloks ir aizpildīts dienas pārskata markdown, palaid `@graphics-designer`:

```python
from src.db import get_db
from src.briefs import daily_brief_topic
db = get_db()
note_id = db.execute(
    "SELECT id FROM context_notes WHERE topic = ? AND note_type='daily_brief' ORDER BY id DESC LIMIT 1",
    (daily_brief_topic(date),),
).fetchone()['id']
# Then dispatch @graphics-designer with note_id
```

`@graphics-designer` lasa `visual_brief_json` no DB (auto-extrahēts no markdown bloka pēc `parse_visual_brief()`), izvēlas metaforu no `visual_map`, ģenerē 16:9 PNG ar nanobanana, saglabā ar `approved=0`. Cilvēks-operators apstiprina ar `approve_image(db, image_id)` vai noraida ar `reject_image(db, image_id, reason)`.

**Telegram preview:** ja gribi nosūtīt rezultātu cilvēkam pārbaudei, pievieno PNG kā attachment Telegram ziņai.

**Vizuālā bloka strip:** `## Vizuālais brief` markdown bloks tiek automātiski izņemts no public lapas renderēšanas (`strip_visual_brief_block()` `src/briefs.py`) — tas paliek tikai DB scaffolding @graphics-designer vajadzībām.

## Solis 9: Wiki sync

```python
from src.wiki import wiki_sync; wiki_sync()
```

Auto-generates/updates person + topic pages in `wiki/`. Safe to run multiple times (idempotent).

### 9.5. Wiki lint

Pēc wiki_sync automātiski palaists wiki lint — rezultāts ir `wiki_sync()` atgrieztajā vērtībā ar atslēgu `lint` (failā nekas netiek rakstīts). Ja ir issues:
- **orphan_page**: vai politiķis ir inactive? Ja jā, ignorē. Ja nē, pievieno index.
- **broken_link**: palaid `wiki_sync()` vēlreiz vai noņem saiti no index.
- **stale_frontmatter**: palaid `wiki_sync()` vēlreiz.
- **isolated_topic**: pārbaudi vai tēma ir aktīva. Ja jā, pievieno person lapām.

### 9.6. Query writeback

Analīzes laikā (2.-6. soļi), ja atklāj netriviālu ieskatu par politiķi vai tēmu:
```python
from src.tools import writeback_insight
writeback_insight(politician_name="Evika Siliņa", insight="...", source="daily analysis 2026-04-08")
```
Neraksti triviālas lietas. Raksti tikai to, ko nevar noņemt no DB ar SQL query — kontekstu, modeļus, novērojumus.

**Person/topic lapas** tiek auto-ģenerētas no DB ar `wiki_sync()`. Manuālās piezīmes izdzīvo sync cauri tikai `## Writeback` sadaļā — to pārvalda `writeback_insight()` (piemērs augšā). Tiešas profila modifikācijas tiks pārrakstītas nākamajā sync.

**Cross-cutting synthesis lapas** (starppartiju dinamika, viena politiķa laika līnija, tēmas evolūcija) tiek rakstītas kā raw markdown faili `wiki/synthesis/<slug>.md`. Nav API wrapper-a — `wiki_sync()` tos glob-ē tikai indeksam (`src/wiki.py:832`):

```python
from pathlib import Path
Path("wiki/synthesis/slesers-nato.md").write_text(
    "# Šlesera NATO evolūcija\n\n...", encoding="utf-8"
)
```

## Solis 9.7: Drift pārbaude (`bash scripts/check.sh`)

Pirms publikācijas palaid drošības tīklu:

```bash
bash scripts/check.sh
```

Tas izpilda ruff + pytest + `generate_public_site()` smoke. Divas tipiskas drift situācijas, ko ķer:

1. **Char baseline drift** (`tests/test_render_chars.py`) — pēc dienas ingest pulses dashboard counts un index hashes mainās. Ja sarkans, regen + commit:
   ```bash
   REGEN=1 .venv/Scripts/python.exe -m pytest tests/test_render_chars.py
   git add tests/fixtures/render_baseline_*.json && git commit -m "test: REGEN char baselines post-<datums>-ingest"
   ```

2. **Schema baseline drift** (`tests/test_schema.py`) — ja pievienots ALTER TABLE caur `src/db.py`, baseline jāatjauno:
   ```bash
   REGEN=1 .venv/Scripts/python.exe -m pytest tests/test_schema.py
   git add docs/refactor/schema-dump-pre-f2.sql && git commit -m "test: refresh schema dump for <ALTER details>"
   ```

Ja `check.sh` paliek sarkans pat pēc REGEN — apstājies, neturpini uz Soli 10. Reālas regresijas (broken render, salauzts importas) jārisina pirms publish.

## Pirms 10. soļa: @quality-reviewer (OBLIGĀTS)

Pirms statiskās vietnes ģenerēšanas palaid `@quality-reviewer`. Tas ir manuāls vārtsargs starp 9. un 10. soli — nav atsevišķi izsekots `print_routine()` izvadē, bet ir obligāts. Tas pārbauda:

- **source_url** — visiem jaunajiem claims ir source_url
- **Duplikāti** — nav identiskas pozīcijas no viena politiķa tajā pašā dienā
- **NEEDS_REVIEW claims** — visi ar `confidence < 0.6` ir atzīmēti vai pamatoti
- **Desperation indikatori** — nav pārāk daudz low-salience claims (vidējais < 0.3 → brīdinājums)
- **Devils-advocate statuss** — nav jaunu pretrunu ar `reviewed=0` (blokē ja ir)
- **Neutralitāte** — dienas pārskats nav partejisks

Ja `@quality-reviewer` = **PASS** → turpini uz publicēšanas vārtiem. Ja **FAIL** → labo problēmas un atkārto no attiecīgā soļa.

## Publicēšanas vārti (CIETIE — pirms 10. soļa)

`@quality-reviewer` PASS **nav** atļauja publicēt. Tas pārbauda datu integritāti; publicēšanas lēmumu pieņem operators. Pirms deploy:

1. **Manuāli pārlasi** pilnu pārskata tekstu — darbības vārdu formas, vienskaitlis/daudzskaitlis, nogriezti teikumi, lielie burti. `lint_lv_style` ar 0 problēmām NAV pietiekami.
2. **Apstiprini attēlu** — featured image ir ģenerēts, apstiprināts (`approve_image`), un varianti eksistē.
3. **Prasi operatoram atļauju** (AskUserQuestion) un sagaidi atbildi.

Standing decision (CLAUDE.md § Publish pause): nekas ārpus vērsts neaiziet automātiski, un **viena publikācijas atļauja nav atļauja nākamajai**.

## Solis 10: Statiskās vietnes ģenerēšana (tikai pēc PASS)

Dienas rutīnai kanoniskais ceļš ir ŠAURAIS renders + additīvais deploy (sk. `/dienas-rutina` prasmi un [[commands]] § Narrow render):

```bash
.venv/Scripts/python.exe -m src.render --only=dashboard,blog,static   # tipiskā dienas kopa (`static` = about skaitļi + sitemap)
bash scripts/deploy.sh --no-delete
```

Pilnais `generate_public_site()` (visa vietne, ~3 min) — tikai release/baseline gadījumiem vai kad mainīta bāzes veidne/asseti.

**NB:** `finanses.html` ir manuāli kurēta lapa (avots: `OppTracker/Deklare2/finanses_content.html`) — `generate_public_site()` to neaiztiek.

## Ad hoc: Lietotājs dalās ar tvītu

Kad lietotājs iedod atsevišķu tvīta URL ārpus rutīnas (piem. ielīmē linku chatā), darba plūsma ir:

1. `insert_document(content=..., source_url=..., platform='twitter', ...)` — ieraksta tvītu ar visām metadatām.
2. Ja autors ir tracked politiķis (pārbauda caur `social_accounts.handle`), seko parastai `save_analysis` plūsmai — `get_politician_documents(pid)` atgriezīs jauno doc.
3. Ja autors ir relay (LTV u.c.) vai nav tracked, `link_politicians_to_documents(days=7)` piešķir `subject` lomu citētajam politiķim no teksta skenēšanas; tad seko standarta analīze šim politiķim. `rescan_all=True` re-skenē jau pielinkētos docs meklējot papildu mentions (piem. pēc jaunu politiķu pievienošanas).
4. Šaurs renders skartajām jomām: `.venv/Scripts/python.exe -m src.render --only=politiki,dashboard,static`. Pilnais `generate_public_site()` šeit nav vajadzīgs.

## Refresh (atkārtota palaišana tajā pašā dienā)

Var palaist cik bieži gribi:

1. `ingest_all()` + `fetch_all_twitter()` + `fetch_all_mentions()` — dedup nodrošina ka neatkārtojas
2. `get_pending_politicians(days=1)` — rādīs TIKAI politiķus ar docs jaunākiem par pēdējo analīzi
3. Analizēt tikai saturīgos jaunos docs (ne RT, ne apsveikumus). Nesaturīgos atzīmēt ar `save_analysis(claims=[], empty_doc_ids=[id1, id2, ...])` — `empty_doc_ids` parametrs ir obligāts, lai docs tiktu atzīmēti reviewed. Bez tā `save_analysis(claims=[])` neatzīmē neko un docs atkārtoti atgriežas backlog
4. Spriedzes/pretrunas — pievienot tikai ja atrod jaunas
5. Jaunās pretrunas pārskatīt ar `@devils-advocate` (solis 4)
6. Dienas pārskatu **UPDATE** (ne jaunu) — `UPDATE context_notes SET content=? WHERE id=? AND note_type='daily_brief'`
7. `@quality-reviewer` → publicēšanas vārti (operatora atļauja) → šaurs renders + `bash scripts/deploy.sh --no-delete`
