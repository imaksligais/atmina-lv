# Atmiņas optimizācijas plāna izvērtējums un atbilde otram aģentam

Jā — otrā aģenta atbilde ir laba, un es lielā mērā piekrītu korekcijai. Mans sākotnējais brīfs bija apzināti “drošs” un strukturāli robusts, bet otrs aģents pareizi pārkalibrē to uz **reālo Atmiņas darba kontekstu**: mazs projekts, maz patērētāju, lokāls process, aģentu prompti kā galvenais API patērētājs, nevis publiska Python bibliotēka.

Mana precizētā pozīcija: **pieņemt otrā aģenta plānu kā praktiskāku bāzi**, bet ar dažiem drošības papildinājumiem, lai refaktorings nekļūst pārāk “optimistisks”.

---

## Mans vērtējums par otrā aģenta atbildi

Viņš pareizi nošķir divas lietas:

1. **Teorētiski pareizu arhitektūru** vidēja izmēra komandprojektam.
2. **Atmiņai piemērotu arhitektūru**, kur galvenais mērķis ir droši uzturēt pipeline, DB invariantu loģiku un aģentu darba plūsmu.

Tas ir būtiski. Atmiņai nevajag pārvērsties par frameworku. Vajag panākt, lai lielie faili vairs nebremzē domāšanu un izmaiņas, bet bez liekiem slāņiem.

Es mainītu savu sākotnējo prioritāti šādi:

```text
1. Matcher izvilkšana
2. schema.sql izvilkšana no db.py
3. predeploy/check skripts + pyproject.toml
4. generate.py vienkāršāka šķelšana uz src/render/
5. saeima.py šķelšana pirms nākamā lielā Saeima darba
6. migrācijas tikai uz priekšu
7. performance/storage/dependency grupas tikai tad, kad ir konkrēta sāpe
```

---

## Kur es pilnībā piekrītu otram aģentam

### 1. “Stable API” nav visa `src.db`, bet aģentiem redzamās funkcijas

Šis ir labs labojums manam sākotnējam brīfam.

Ja nav ārēju lietotāju, PyPI pakas vai cita projekta, kas importē Atmiņu, tad nav vērts aizsargāt katru veco moduļa ceļu ar facade slāņiem.

Reāli jāiesaldē:

```text
store_claim
save_analysis
retrieve_context
search_similar_claims
link_politicians_to_documents
match_politicians
generate_public_site
print_routine
```

Un vēl tās funkcijas, kuras tieši minētas `.claude/agents/*.md`, `scripts/`, `src/social_agent/`, `src/video_ingest/`, `src/csp/`, `src/graphics/`.

Bet es pievienotu vienu drošības noteikumu: pirms jebkuras pārvietošanas palaist:

```bash
rg "store_claim|save_analysis|retrieve_context|search_similar_claims|link_politicians_to_documents|match_politicians|generate_public_site|print_routine" .
```

Tad publiskais API ir nevis sajūta, bet inventarizēts saraksts.

---

### 2. Matcher izvilkšana kā pirmais solis ir pareiza

Šeit otrs aģents mani pārliecināja.

`match_politicians`, `_load_politician_forms`, `_disambiguate_shared_surname`, `link_politicians_to_documents` ir laba pirmā refaktoringa zona, jo:

- tā ir bieži mainīta loģika;
- tā ir relatīvi izolēta;
- tai var uzrakstīt raksturojošus testus;
- tā trenē refaktoringa procesu pirms lielākiem failiem;
- tā tieši sargā datu kvalitāti.

Vienīgais, ko es precizētu: testiem nevajadzētu paļauties tikai uz dzīvo DB, kas laika gaitā mainās. Labāks variants:

```text
tests/fixtures/matcher_docs.json
tests/test_matcher.py
```

Tur ielikt 10–15 reālus, bet iesaldētus piemērus. Var būt arī viens optional integration tests pret aktuālo DB, bet pamat-testiem jābūt deterministiskiem.

---

### 3. `schema.sql` kā pirmais `db.py` solis ir labāks nekā pilna `storage/` pakete

Piekrītu.

Mans sākotnējais `src/storage/{connection,time,schema,migrations,documents,claims,vectors,logs}.py` ir pareizs, ja projekts aug komandā vai ja DB loģika kļūst nevadāma. Bet šobrīd tas varētu radīt pārāk daudz failu ar pārāk maz satura.

Labāks pirmais solis:

```text
src/db.py
src/schema.sql
```

`init_db()` lasa `schema.sql`, izpilda baseline DDL un pēc tam palaiž nākotnes migrācijas.

Drošības papildinājums: pēc izvilkšanas jānotestē divi scenāriji:

```text
1. tukša DB → init_db() → visas tabulas/indeksi izveidojas;
2. esoša DB → init_db() → nekas netiek sabojāts vai negaidīti pārrakstīts.
```

---

### 4. Migrācijas tikai uz priekšu ir pietiekamas

Piekrītu.

Vēsturisko shēmu pārvēršana par `0001`, `0002`, `0003` migrācijām būtu skaista, bet šajā kontekstā mazvērtīga. Ja esošā DB jau ir “baseline”, tad praktiskākais variants ir:

```text
0000 = pašreizējā schema.sql baseline
0001 = nākamā reālā DDL izmaiņa
0002 = nākamā pēc tās
```

Ar `schema_migrations` tabulu.

Rollback vēsture pirms baseline nav vajadzīga, ja jau eksistē manuālie backupi.

---

## Kur es piekrītu, bet ar atrunām

### 1. “Nav vajadzīgi facade slāņi” — jā, bet ar pārejas shim svarīgākajām vietām

Es nepieprasītu facade slāni visur, bet atstātu pārejas shim failiem, kuri var būt minēti promptos, skriptos vai dokumentācijā.

Piemēram:

```python
# src/ingest.py
from src.matcher import match_politicians, link_politicians_to_documents
```

Un:

```python
# src/generate.py
from src.render import generate_public_site
```

Tie var būt 20 rindu faili, nevis nopietns facade slānis.

Tas dod drošību bez arhitektūras smaguma.

---

### 2. Lokāls pre-commit hook ir labs, bet vajag arī `scripts/check.sh`

Es piekrītu, ka GitHub Actions šobrīd nav obligāts. Bet lokāls hook nav pietiekami redzams vai pārnesams.

Es ieteiktu pievienot:

```bash
scripts/check.sh
```

kas dara:

```bash
python -m ruff check src scripts tests
python -m pytest tests -q
python -c "from src.generate import generate_public_site; generate_public_site()"
```

Tad pre-commit hook var vienkārši saukt šo skriptu. Ja vēlāk gribat CI, GitHub Actions arī sauc to pašu skriptu. Nav jāmaina process.

---

### 3. `generate.py` šķelšana uz `src/render/<page>.py` ir pietiekama, bet jāievēro robežas

Es piekrītu otram aģentam: trīs slāņi `queries / viewmodels / render` šobrīd ir par smagu.

Bet, lai vienkāršais modelis nekļūtu par nākamo monolītu, es ieliktu šādu konvenciju:

```text
src/render/
  __init__.py
  _common.py
  dashboard.py
  politicians.py
  politician.py
  parties.py
  party.py
  positions.py
  contradictions.py
  statistics.py
  search.py
```

Katrā lapas failā:

```python
def render_politicians_page(conn, output_dir):
    data = _fetch_politicians(conn)
    context = _build_context(data)
    return _render_template("politicians.html", context, output_dir)
```

Un privātās funkcijas blakus:

```python
def _fetch_politicians(conn): ...
def _build_context(rows): ...
```

`_common.py` drīkst saturēt:

```text
Jinja env
drošības filtrus
URL helperus
safe_json
sanitize_html
kopīgās konstantes
kopīgās render/write funkcijas
```

Bet `_common.py` nedrīkst kļūt par miskasti ar konkrētu lapu SQL.

Ja viena lapa pārsniedz, teiksim, 600–800 LOC vai trīs lapas sāk kopēt vienu un to pašu SQL, tikai tad jāievieš `src/render/_queries.py` vai `src/readmodels/`.

---

## Atbilde uz pirmo aģenta jautājumu

> Vai vienkāršais `src/render/<page>.py` šablons, nevis `queries/viewmodels/render` trīs slāņi, ir pietiekams Atmiņas mērogam?

Jā, ir pietiekams, un šajā kontekstā tas ir labāks sākuma variants.

Trīs slāņu modelis būtu noderīgs, ja:

- būtu vairāki UI formāti;
- būtu daudz atkārtoti lietojamu read-modelu;
- būtu atsevišķi cilvēki, kas strādā pie SQL un pie renderēšanas;
- lapu datu sagatavošana būtu ļoti sarežģīta un koplietota.

Atmiņā šobrīd svarīgāk ir, lai viena lapa ir saprotama vienā failā. Tāpēc `src/render/<page>.py` ir pareizais kompromiss.

Mans ieteiktais noteikums:

```text
Sāc ar vienu failu uz lapu.
Tur blakus turi fetch + context + render loģiku.
Ekstrahē queries/viewmodels tikai tad, kad parādās atkārtošanās vai fails kļūst pārāk liels.
```

Tas ir labāks nekā pāragri izveidot arhitektūru, kuru pēc tam katra maza izmaiņa spiesta apkalpot.

---

## Atbilde uz otro aģenta jautājumu

> Vai `saeima.py` šķelšanas pievienošana plānam ir prioritāte virs pilnas `storage` paketes sadales?

Jā. `saeima.py` šķelšana ir prioritāte virs pilnas `storage` paketes sadales.

Iemesli:

1. **Saeima ir domēna modulis**, nevis tehnisks helperis. Tur sajaucas shēma, parsing, balsis, likumprojekti un claim ģenerēšana. Tā ir reāla domēna sarežģītība.

2. **Tur nāk jauns darbs.** Ja Phase 1.5/2/3 papildinās Saeima funkcionalitāti, labāk vispirms radīt pareizo vietu jaunajam kodam, nevis vēl vairāk audzēt monolītu.

3. **Pilna storage pakete šobrīd ir vairāk estētisks nekā praktisks ieguvums.** `db.py` var sākt uzlabot ar `schema.sql`, nevis uzreiz sadalīt astoņos moduļos.

4. **Saeima sadalījuma robežas ir dabiskas.** Šis nav mākslīgs slāņojums; tās ir dažādas atbildības.

Es ieteiktu:

```text
src/saeima/
  __init__.py       # publiskie eksporti, lai import src.saeima joprojām strādā
  schema.py         # Saeima tabulu DDL/helperi, ja vēl vajag kodā
  parsing.py        # dokumentu/balsojumu parsing
  votes.py          # vote import, lookup, normalization
  bills.py          # bill-related logic
  claims.py         # Saeima vote → claim derivation
```

Tehniska piezīme: nevar vienlaikus būt `src/saeima.py` un `src/saeima/` pakete. Refaktorā `src/saeima.py` jāaizstāj ar direktoriju `src/saeima/`, un `src/saeima/__init__.py` jāpārpublicē vecās galvenās funkcijas.

---

## Ko es ieteiktu pateikt otram aģentam

Vari viņam dot šādu atbildi:

```text
Piekrītu tavai korekcijai. Mans precizētais skatījums:

1. `src/render/<page>.py` modelis ir pietiekams Atmiņas mērogam un šobrīd labāks par queries/viewmodels/render trīs slāņiem. Fetch + context + render vienā lapas modulī ir praktiski pareizi, jo šajā projektā SQL un renderēšanas izmaiņas parasti notiek kopā. Tomēr vajag stingru `_common.py` robežu: tur tikai Jinja env, drošības filtri, URL/helper funkcijas un konstantes; nekādu lapas-specifisku SQL. Ja konkrēts page fails izaug pārāk liels vai sākas atkārtošanās starp lapām, tad ekstrahējam read-model/query slāni vēlāk.

2. `saeima.py` šķelšana noteikti ir prioritāte virs pilnas `src/storage/` paketes sadales. `db.py` šobrīd pietiek optimizēt ar `schema.sql` un nākotnes migrāciju formātu. Savukārt Saeima modulī ir īsta domēna sarežģītība un gaidāms jauns Phase 1.5/2/3 darbs, tāpēc labāk sadalīt pirms tur pievieno vēl kodu. Ieteiktais sadalījums: `src/saeima/{schema, parsing, votes, bills, claims}.py`, ar `__init__.py` kā re-export shim, lai vecie importi paliek dzīvi.

3. Vienīgā atruna: characterization testiem jābūt deterministiskiem. Matcher testus labāk balstīt uz iesaldētiem fixtures no reāliem dokumentiem, ne tikai uz dzīvo DB. Un pirms pārdēvēšanas jāpārbauda `.claude/agents/*.md`, `scripts/`, `src/social_agent/`, `src/video_ingest/`, `src/csp/`, `src/graphics/`, lai neizjauktu aģentiem redzamos tool nosaukumus.

Tātad: sākam ar matcher extraction + tests, tad schema.sql + scripts/check.sh/predeploy, pēc tam generate.py uz `src/render/`, un pirms nākamā lielā Saeima darba pārvēršam `saeima.py` par `src/saeima/` paketi.
```

---

## Mans galīgais ieteikums

Es virzītos pēc otrā aģenta plāna, bet ar šiem trim papildinājumiem:

1. **Pirms refaktoringa inventarizēt aģentu API ar `rg`**, nevis paļauties uz atmiņu.
2. **Characterization testus balstīt uz fixtures**, nevis tikai uz mainīgu dzīvo DB.
3. **Pievienot `scripts/check.sh`**, ko sauc gan pre-commit, gan predeploy.

Tas saglabā otrā aģenta galveno priekšrocību — praktiskumu — bet iedod pietiekamu drošības tīklu, lai refaktorings nekļūst bīstams.
