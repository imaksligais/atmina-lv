# Backlog izpilde 2026-10-18 — plāns

**STATUSS: IZPILDĪTS 2026-10-19** — zars `backlog-izpilde-2026-10-18` apvienots ar master un izdzēsts (`docs/arhivs/handoffs/HANDOFF-2026-10-19.md`).
Arhivēts 2026-10-21.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Mērķis:** izdarīt tos `BACKLOG.md` + `backlog/*.md` ierakstus, kurus var izdarīt bez jauna operatora lēmuma; pārējiem — viens jautājums katram ar noklusējumu.

**Pieeja:** 2026-10-18 triāža pār visiem 8 tēmu failiem (682 rindas). Četri grozi: **A** — koda darbs bez lēmuma (šis plāns); **B** — apstiprināts, bet ar ārēju vai publisku soli (plāns beidzas pie «jautā pirms deploy»); **C** — operatora lēmumi (tikai jautājumi); **D** — neaiztikt (`[DEFERRED]`, § Ne-darīt). Secība — pēc šaurākā ierobežojuma: termiņš → nosaukta rinda + tests → vairāku failu darbs.

**Tech:** Python 3 + SQLite (`data/atmina.db`), pytest (`bash scripts/check.sh`), Jinja2 render.

**Spec:** `BACKLOG.md` + `backlog/*.md` ieraksti, kas nosaukti katrā uzdevumā (virsraksts VERBATIM).

## Globālie ierobežojumi (katram uzdevumam)

- Vienmēr `.venv/Scripts/python.exe`, nekad kails `python`.
- **Palīgi NEKAD nedara** `git stash`, `git checkout --`, `git restore`, `git reset` (kopīgs darba koks). Commito tikai savus failus ar `git add <ceļš>`; ziņa caur failu `git commit -F <fails>`.
- Palīgu modelis: **Opus** (`model: opus`); viens palīgs = viens uzdevums; recenzents pēc katra uzdevuma.
- **0. solis katram uzdevumam — reproducē defektu dzīvajā kokā/DB** (ieraksts var būt novecojis). Ja nereproducējas — STOP, ziņo, uzdevumu neizpildi.
- Tests pirms koda; tests jāredz KRĪTAM bez labojuma (mutācija = atsauc labojumu). Testi nekad neaiztiek dzīvo DB (`tests/conftest.py` § 4–5).
- Datu mutācija ar roku → pāra `data/rollback_<tvērums>_2026-10-XX.sql` commitēts PIRMS piemērošanas (eskalācija 8). Šajā plānā A grozā datu mutāciju NAV.
- Nekas netiek izvietots (`deploy.sh`) šī plāna ietvaros bez operatora atļaujas.
- Latviešu teksts (komentāri, CHANGELOG, backlog) — gramatikas un stila vārti; nekādu operatoru identificējošu ziņu (fails ir publiskajā spogulī).
- Pabeidzot ierakstu: izgriez to no tēmu faila UN indeksa vienlaikus (`tests/test_backlog_index_sync.py`); CHANGELOG ≤5 rindas tikai, ja mainās noteikums.

## Ko šis plāns apzināti NEdara (§ Ne-darīt sadursmes)

- NEpieslēdz embedēšanu `scripts/ingest_url.py` (bloķē arī `avoti.md` truncated (b) pārchunkošanu).
- NEliek stance-hash idempotences atslēgā; NEievieš `analyses` UPSERT.
- LSM slug dreifam NEbūvē koda dedup atslēgu — tikai triāža (C grozs).
- `saeima_vote` stance teksta (T20) neaiztiek.

## Review Focus

1. Balsu skaits profilā pēc `scope.py` konsolidācijas mainās par `Nebalsoja` rindām — sagaidāms: šodienas skaitļi baitu identiski (fikstūras renders pirms/pēc), `Nebalsoja` semantika nemainās līdz operatora lēmumam.
2. `_vote_salience` ar motīvu, kurā ir gan «nodošanu … komisijai», gan «2.lasījums» — sagaidāms: lasījums uzvar (0,8), jo lasījuma zars tiek pārbaudīts pirms nodošanas zara.
3. Rutīnas dienas robeža 00:00–05:00 LV — claim, kas glabāts 02:00, pieder IEPRIEKŠĒJAI rutīnas dienai diakritikas pārbaudē.
4. `coverage.py` pie 23:30 LV (= cita UTC diena vasarā/ziemā) — pretruna, kas atrasta šodien, nav «veca».
5. `db.store_contradiction` ar nederīgu `severity` — jākrīt pirms INSERT ar skaidru kļūdu, ne klusi jāieraksta.

---

## Task 0: Backlog higiēna — izgriezt slēgtos ierakstus

**Faili:** `BACKLOG.md` (indekss), `backlog/{saeima,agenti-pipeline,matcher,dati-db,avoti,vad,vietne-ui,repo-higiena}.md`

Izgriežamie (13): saeima — `_motif_to_topic()` [SLĒGTS 10-14], Steidzamības balsojumi [SLĒGTS 10-14]; agenti-pipeline — NEEDS_REVIEW robeža [SLĒGTS], Pretrunu pārbaudes pārklājums [IZPILDĪTS 10-15], **Kaili claim ID** (pārbaudīts 10-18: `scripts/check_output.py:192` `BARE_ID_IS_FAILURE = True`, `grep -c "claim #" output/atmina/blog/2026-08-10.html` → 0); matcher — NBS pid=204, Seržants, @AtminaLV ceturtais ceļš [SLĒGTS], Dzēstas junction rindas [IZPILDĪTS]; dati-db — Deep-check stale-pol, Rosļikovs, 09-23 backfill [SLĒGTS]; avoti — Baško, RT no diviem kontiem, video-extractor:24 [SLĒGTS], leta.lv `published_at` [IZPILDĪTS]; vad — VAD resweep [SLĒGTS]; vietne-ui — divi [DONE]; repo-higiena — Vārtu saucēju atlikums [IZPILDĪTS].

- [ ] **1.** Katram ierakstam pārbaudi, ka pēda eksistē: `git log --oneline --grep=<atslēgvārds>` vai CHANGELOG / `docs/verdikti-2026-10-14.md` rinda. Ja pēdas nav — ierakstu NEgriez, ziņo.
- [ ] **2.** Ja ierakstā ir «Paliek:» ar atvērtu daļu (piem. RT dokumentā `social.py:307-313` `documents_skipped`; vietne-ui «Atradumi» nākamie stāsti; VAD «Paliek (process)»), atvērto daļu pārcel uz atbilstošu atvērto ierakstu vai jaunu `[FIX]`, tad griez.
- [ ] **3.** `.venv/Scripts/python.exe -m pytest tests/test_backlog_index_sync.py -q` → PASS.
- [ ] **4.** Commit: `Backlog: izgriezti 10-14…10-18 slēgtie ieraksti (pēdas pārbaudītas)`.

## Task 1: Balsu skaitīšanas noteikums vienā vietā (termiņš — pirms 15. Saeimas pārslēgšanas)

**Ieraksts:** `backlog/saeima.md` «[OPEN] Balsu skaitīšanas noteikums 5 formulās + profila tipa dalījums».

**Faili:** Modify `src/scope.py` (jauns `NOT_ATTENDANCE_SQL`), `src/render/politicians_tabs.py:51`, `src/render/politicians.py:61,283`, `src/render/saeima.py:~160`, `src/render/rankings.py:~205`, `src/render/bio.py:46`, `src/render/politicians.py:111-123` (`_fetch_politicians`). Test: `tests/test_vote_count_single_rule.py`.

**Interfaces:** Produces `src.scope.NOT_ATTENDANCE_SQL: str` (alias `siv`) un `src.scope.CAST_BALLOTS: tuple[str, ...]`.

- [ ] **0.** Reproducē: `grep -n "Reģistrējies\|Nereģistrējies\|Nebalsoja" src/render/*.py` — uzskaiti katru formulu un kuru vērtību kopu tā skaita. Pieraksti (atskaitē), kuras divas nesakrīt par `Nebalsoja`.
- [ ] **1. Tests (e2e caur renderu):** uz fikstūras DB ar vienu politiķi, kam ir pa vienai `Par`, `Pret`, `Atturas`, `Nebalsoja`, `Reģistrējies` rindai, renderē profilu, Saeimas lapu, reitingu un bio; nolasi «bals.» skaitli katrā virsmā un pārbaudi, ka visi sakrīt ar `src.scope` noteikumu. Krīt šodien (bio/rankings atšķiras par `Nebalsoja`).
- [ ] **2.** Pārnes `NOT_ATTENDANCE_SQL` uz `src/scope.py`. Importē to **tikai tās kopijas, kas jau šodien ir semantiski identiskas** `politicians_tabs.py:51` (`Nebalsoja` skaitās). `rankings.py` (apzināti izslēdz `Nebalsoja`, sk. docstring `:189` un komentāru `politicians.py:281`) NEaiztiec — testā tā virsma `xfail(strict=True, reason="Nebalsoja — divas apzinātas konvencijas, C1")`. Publicētie skaitļi nemainās.
- [ ] **3.** `_fetch_politicians` profila tipam lieto `current_term_vote_counts()` (kā `personas.py:134`, `search_index.py:111`).
- [ ] **4.** Fikstūras renders pirms/pēc: `diff -rq` → 0 atšķirību (šodien abi skaitļi sakrīt).
- [ ] **5.** `bash scripts/check.sh` → zaļš. Commit.

## Task 2: `_vote_salience` lasījumu zari

**Ieraksts:** `backlog/saeima.md` «[FIX] `_vote_salience` lasījumu zari neķer nevienu reālu motīvu».

**Mērījums 2026-10-18 (read-only):** vecie zari («galīgajā/trešajā/otrajā lasījumā») → **0** motīvu; `[123].lasījum` → **5 814**; «nodošanu … komisij» → 66 (neķer), «nodošana komisij» → 575 (ķer); «steidzam» BEZ `N.lasījum` → **37** (tāpēc atsevišķais `steidzam → 0,9` zars paliek).

**Faili:** Modify `src/saeima/claims.py:365-382`. Test: `tests/test_vote_salience.py`.

- [ ] **1. Tests:**

```python
import pytest
from src.saeima.claims import _vote_salience

@pytest.mark.parametrize("motif,expected", [
    ("Grozījumi Imigrācijas likumā (1030/Lp14), 3.lasījums", 0.9),
    ("Grozījumi Imigrācijas likumā (1030/Lp14), 2.lasījums", 0.8),
    ("Grozījumi Imigrācijas likumā (1030/Lp14), 2.lasījums, steidzams", 0.9),
    ("Par nodošanu Izglītības, kultūras un zinātnes komisijai. Par grozījumiem…", 0.5),
    ("Likumprojekta nodošana komisijām", 0.5),
    ("Par likumprojekta atzīšanu par steidzamu", 0.4),
    ("Par priekšlikumu Nr. 8", 0.7),
])
def test_vote_salience_real_motif_formats(motif, expected):
    assert _vote_salience(motif) == expected
```

Pirms koda pārbaudi pret DB, ka katra parauga forma reāli eksistē (`SELECT motif FROM saeima_votes WHERE motif GLOB '*3.lasījum*' LIMIT 3` utt.); ja forma atšķiras — labo paraugu, ne kodu.

- [ ] **2.** Palaid — 3.lasījums/2.lasījums/«nodošanu» krīt.
- [ ] **3. Kods:**

```python
_READING_RE = re.compile(r"\b([123])\.\s*lasījum")

def _vote_salience(motif: str) -> float:
    motif_lower = motif.lower()
    if is_urgency_declaration(motif):
        return 0.4  # verdikti 2026-10-14 § C2
    m = _READING_RE.search(motif_lower)
    if m:
        if "steidzam" in motif_lower or m.group(1) == "3":
            return 0.9  # galīgais lasījums (steidzamam — 2.)
        if m.group(1) == "2":
            return 0.8
    if _REFERRAL_CLAUSE_RE.search(motif_lower) or "nodošana komisij" in motif_lower:
        return 0.5
    if "steidzam" in motif_lower:
        return 0.9  # steidzama likumprojekta lasījums bez N.lasījums formas (37 motīvi)
    return 0.7
```

Lasījums tiek pārbaudīts PIRMS nodošanas (klauzula netiek nogriezta — tikai secība). Pārbaudi, ka `1.lasījums` bez nodošanas paliek 0,7, un pievieno testam vienu no 37 «steidzam» motīviem bez lasījuma → 0,9.

- [ ] **4.** Tests PASS; mutācija (atgriez veco zaru) → krīt.
- [ ] **5. Vēsturiskās rindas NEmigrē** (noklusējums; C jautājums Nr. 3). Atskaitē saucējs: cik `saeima_vote` claims saņemtu citu salience.
- [ ] **6.** Commit.

## Task 3: Divu pulksteņu atlikumi

**Ieraksts:** `backlog/repo-higiena.md` «[FIX] Divu pulksteņu atlikumi» (rinda pārvietojusies uz `routine.py:584`).

**Faili:** `src/routine.py:575-590` (`_check_diacritic_health`), `src/coverage.py:105-114`. Test: `tests/test_two_clocks_residue.py`.

- [ ] **0.** `_check_diacritic_health(target_date)` vienīgais izsaucējs ir `src/routine.py:468` (`print_routine` rutīnas diena) — pārbaudi, ka `target_date` tur ir rutīnas diena (`current_routine_day()`), ne kalendāra datums; ja kalendāra — labo arī izsaucēju.
- [ ] **1. Tests (a):** pagaidu DB ar claim `created_at='2026-10-19 02:00:00'` (LV) un sliktu diakritiku; `_check_diacritic_health('2026-10-18')` to ATRAST (rutīnas diena 18. = [18. 05:00, 19. 05:00)); `('2026-10-19')` — NE. Šodien krīt.
- [ ] **2. Kods (a):** `start, end = routine_day_window(target_date)`; `WHERE created_at >= ? AND created_at < ?`.
- [ ] **3. Tests (b):** pretruna ar `detected_at = <LV tagad mīnus N dienas plus 1 stunda>` NAV veca pie `stale_days=N`; ar fiksētu pulksteni (monkeypatch `src.coverage.now_lv_dt` — `src/db.py:113` eksistē, atgriež `datetime`), kur LV un UTC datumi atšķiras (00:30 LV). Šodien krīt.
- [ ] **4. Kods (b):** `from src.db import now_lv_dt`; `cutoff = (now_lv_dt() - timedelta(days=stale_days)).strftime("%Y-%m-%d")`, padod kā `?` — nevis `date('now', ?)`. NEraksti `'localtime'` LV kolonnai.
- [ ] **5.** Abi testi PASS; mutācija → krīt. `pytest tests/test_utc_column_is_never_read_bare*` PASS. Commit.

## Task 4: `store_contradiction` validācija `db` slānī + `party_id`

**Ieraksts:** `backlog/agenti-pipeline.md` «[OPEN] `store_contradiction` validācija tikai `tools` slānī; partiju pretrunu solis nevar izpildīties».

**Faili:** `src/db.py:1320-1345`, `src/tools.py:557-595`, `src/models.py` (`Contradiction` + lauks `party_id: int | None = None`, pašlaik nav), `scripts/partiju_pretrunas.py:37`. Test: `tests/test_store_contradiction_db_layer.py`.

**Interfaces:** `src.db.store_contradiction(..., party_id: int | None = None, confirmed: int = 0)` — validē ar `src.models.Contradiction` + `normalize_topic` iekšā; `src.tools.store_contradiction` kļūst par plānu apvalku (JSON), dubultas validācijas nav.

- [ ] **0.** Reproducē: `.venv/Scripts/python.exe scripts/partiju_pretrunas.py --help` un sausais ceļš → `TypeError` par `party_id`/`confirmed`. `SELECT COUNT(*) FROM contradictions WHERE party_id IS NOT NULL` → 0 (10-18).
- [ ] **1. Tests:** (i) `db.store_contradiction(severity='nepareizs', …)` → `ValueError`/`ValidationError`, rindu skaits nemainās; (ii) `db.store_contradiction(..., party_id=<fikstūras partija>)` ieraksta `party_id`; (iii) e2e: `scripts/partiju_pretrunas.py` uz pagaidu DB palaižas bez `TypeError`.
- [ ] **2.** Pārbaudi `contradictions` shēmā `confirmed` noklusējumu un vai kolonna `party_id` jau ir (`src/schema.sql`); ja `confirmed` jau ir ar noklusējumu 0, parametru pievieno tikai, ja skripts to tiešām padod.
- [ ] **3.** Kods; visi `store_contradiction` izsaucēji (`grep -rn "store_contradiction(" src scripts .claude`) turpina strādāt.
- [ ] **4.** `bash scripts/check.sh` zaļš. Commit. Partiju pretrunu soļa reāls palaidiens — NĒ (tas ir C jautājums Nr. 6).

## Task 5: Saeimas ielādes sīkums (a) — iesniedzēju lauka troksnis

**Ieraksts:** `backlog/saeima.md` «[FIX] Saeimas ielādes sīkumi …» punkts (a).

**Faili:** `src/saeima/parsing.py:48-56`. Test: esošais `tests/test_saeima_parsing*.py` (pirms jauna testa nosauc, vai kāds jau sedz `parse_agenda_snapshot` iesniedzējus).

- [ ] **0.** Atrodi 3 reālas trokšņa instances (`" [ref=…`, `DKP izskatīšanas gaita`, `(Referents: …)`) `data/saeima_snapshots/` vai DB laukā; pieraksti.
- [ ] **1.** Parametrizēts tests ar šīm trim virknēm → tīrs iesniedzēja vārds. Krīt.
- [ ] **2.** Minimāla tīrīšana parserī. PASS. Vēsturisko lauku NEpārraksta. Commit.
- Punkts (c) (transakcija `store_vote` + `generate_claims_from_votes`) **NAV šeit** — skar inv. #4b/#12, atsevišķs plāns (B grozs).

## Task 6: Atgūšanas apsekojums neatgriež jau ekstraktētus pārus — `find_inversions` (f)

**Ieraksts:** `backlog/agenti-pipeline.md` «[OPEN] `find_inversions` …» punkts (f).

**Faili:** `scripts/recovery_survey.py` (vaicājums). Test: esošais `tests/test_recovery_survey*.py` papildinājums.

- [ ] **0.** Reproducē: saskaiti pārus, kur `claims` (tas pats `opponent_id` + `source_url`) jau eksistē, bet pāris parādās apsekojumā (D4: 4/303).
- [ ] **1.** Tests: fikstūrā pāris ar esošu claim no tā paša URL un `extracted_at IS NULL` → apsekojums to NEatgriež. Krīt.
- [ ] **2.** `NOT EXISTS (SELECT 1 FROM claims c WHERE c.opponent_id = dp.politician_id AND c.source_url = d.source_url)` vaicājumā. PASS. Commit. (Vienreizējs zīmogs ar rollback — NĒ; vaicājuma filtrs pietiek.)

## Task 7: Testu mutāciju robi (5 zari)

**Ieraksts:** `backlog/repo-higiena.md` «[OPEN] Testu mutāciju izlases robi — 5 neaizsegti zari».

- [ ] Katram no 5 zariem (UTC kolonna bez datuma funkcijas `t.created_at >= ?`; `link_audit_row` otrā pārbaude; `backfill_truncated_docs` glabātās rindas pārbaude; pavediena stila pārbaude; `_fetch_topics` neaktīvo izslēgšana): **vispirms nosauc esošo testu**, kas tuvākais; papildini to ar vienu gadījumu; pierādi ar mutāciju (noņem zaru → tests krīt). Nav jaunu testu failu, ja esošs der.
- [ ] CI skipu jautājums (`TestTensionDayBoundaryTimezone`) — tikai pieraksts, kad nākamais sync palaiž `-rs`.
- [ ] Commit pa vienam zaram.

## Task 8: OG kartīte «Vārdi pret darbiem» — balsojums, ne likumprojekta apraksts

**Ieraksts:** `backlog/vietne-ui.md` «[OPEN] OG kartīte …» (zema prioritāte).

**Faili:** `templates/og-card.html.j2`, `_og_card_context` (atrodi ar `grep -rn "_og_card_context" src`). UI darbā — `good-css` skill; ekrānuzņēmums pirms/pēc.

- [ ] Tests: renderē OG kartīti fikstūras pretrunai ar `saeima_vote` pusi (dzīvajā vietnē piemērs — #56; fikstūras ceļu atrodi `tests/conftest.py`) → teksts satur «Balsoja «Par»» + skaitļus `(47:8:18)` formā no `saeima_votes`, nesatur likumprojekta `summary`. Krīt.
- [ ] Kods; ekrānuzņēmums; commit. Izvietošana — tikai ar operatora atļauju.

## Task 9: (pēc izvēles, zema prioritāte) `multi_select` makro

**Ieraksts:** `backlog/vietne-ui.md` «[OPEN] Multi-select marķējuma makro». Trigeris ir «nākamā filtra lapa» — **izpildi tikai, ja operators saka «jā» tagad.** Metode: makro `_macros.html.j2`, 18 veidnes; fikstūras renders pirms/pēc `diff -rq` = 0.

---

## B grozs — plānojams, beidzas pie «jautā pirms deploy»

- **B1. Cloudflare Task 9 koda daļa** (BACKLOG § Atliktais 67; operators 10-16: rezerve nebija vajadzīga). Sekot `docs/superpowers/plans/2026-09-15-cloudflare-migracija.md` § Task 9 (rinda 897) Files blokam: `assets/htaccess.template` + `_copy_host_config` ārā, testi, runbooki, CLAUDE.md rindas. Hostinga anulēšana un DNS tīrīšana CF panelī — **operatora soļi**. Pirms deploy — atļauja; pēc — `verify_host.py --base https://atmina.lv` 8/8.
- **B2. `src/scope.py` paplašināšana (~90 vietas)** — ieraksts pats prasa «plāns pirms diff»: atsevišķs plāns `docs/superpowers/plans/2026-10-XX-scope-paplasinasana.md`, pēc 1. uzdevuma (tas pats fails). Divu pozīciju predikātu nozīme — operatora lēmums (#689559, #704196).
- **B3. Paywall stop-gate uz teksta/garuma pazīmes** (`agenti-pipeline.md` Stance-fidelity (c)) — analogs truncated-stub vārtiem; vispirms izmērīt FP uz 30 d korpusa (T18).
- **B4. Truncated (c): `og:description` kā ievads backfill ceļā** — koda daļa + vēsturisko doku pārlāde ar rollback; skar `reviewed_at` atiestatīšanu → atsevišķs plāns.
- **B5. Saeimas ielāde (c): claim ģenerēšana vienā transakcijā ar `store_vote`** — atsevišķs plāns (inv. #4b, #12).

## C grozs — operatora lēmumi (viens jautājums katram; noklusējums iekavās)

1. **`Nebalsoja` bals. skaitā** — pastāv divas apzinātas konvencijas (profils/bio skaita, reitingi ne; metrikas filtrē tikai Par/Pret/Atturas). Apvienot vai paturēt abas? (Paturēt abas, kā ir.)
2. **Datu triāžas ar rollback — atļauji man izpildīt kā «operatoram»?** LSM 40 pāri; `subject` demotēšana (120049, 120019, 120708/120684/120676, 124194/124250, 129930, 125359, 120749); stale junction (1) 50 rindas; 10-07 atlikumi (LETA 195 pāris). (Nē — paliek tev.)
3. **`_vote_salience` vēsturiskās rindas** — migrēt? (Nē, tikai jaunās.)
4. **Stance-checker pastāvīgs rutīnas solis** pēc 10-15 izmēģinājuma? (Gaida tavu «jā».)
5. **Vēstneša laiks** — palaist Vēstneša soli ar roku pirms analīzes vai pieņemt «akts nākamajā dienā»? (Pieņemt un ierakstīt `dienas-rutina.md`.)
6. **Partiju pretrunu solis** pēc 4. uzdevuma — palaist izmēģinājumu? (Nē, līdz atsevišķam lēmumam.)
7. **Spriedzes notikuma datums** — filtrs pēc avota `published_at` vai jauna kolonna? (Filtrs.)
8. **Jev keša atslēga** — eksplicīts modelis izsaukumā vai atbildējušais modelis atslēgā? (Eksplicīts modelis.)
9. **@contradiction-hunter medību pēdas (9 punkti)** — kurus uz `/deep-check`? (Neviens, kamēr nav valdības.)
10. **Redakcionālais noteikums par bijušā PRO deputāta uzvārdu** — ratificēt promptā? (Ratificēt.)
11. **`claim-extractor.md`: parakstīts ministrijas ziņojums = pozīcija?** (§ Atliktais 66; noklusējums (a) tukšs.)
12. Pārējie `[OPERATOR]` ieraksti (15. Saeima, Gorkšs, Jurēvics, matcher paterni, Zīle/Puče, Lūsis, LIELO burtu 130, Vēstneša Lietuvas VK) — gaida ārēju trigeri vai tavu pārlasi; neko nedaru.

## D grozs — neaiztiek

Visi `[DEFERRED]` (parent_vote_id, komisiju balsojumi, visual_brief_json, diena RSS sānjosla, video ingest, Aizsardzības industrija, vektoru bāreņi, amatu pārskatīšana, tēmu direktorija, VAD `_norm_kind`); visa § Ne-darīt; vizuālā identitāte (operators: «vēlāk»).

## Izpilde

- 0.–8. uzdevums: **9 Opus palīgi** (viens uzdevumam) + recenzents katram; 1. uzdevums pirmais (termiņš), 0. var iet paralēli (tikai backlog faili). 2., 3., 4., 6. pieskaras dažādiem failiem — drīkst paralēli; 1. un B2 — nē (`scope.py`).
- Orķestrators pirms «gatavs»: lasa katru diff, palaiž `bash scripts/check.sh`, citē izvadi.
