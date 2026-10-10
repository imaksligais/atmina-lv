# HANDOFF 2026-09-20 (vakars) — dienas rutīnas pabeigšana; izpildītājs: swe-2 orķestris ar swe-2 subaģentiem

> Publisks fails (nav izslēgumu sarakstā) — tikai operatīvās piezīmes, nekā identificējoša.
> Iepriekšējais: `docs/HANDOFF-2026-09-20.md` (dienas pirmā puse). Rutīnas stāvoklis vienmēr: `.venv/Scripts/python.exe -c "from src.routine import print_routine; print_routine()"`.
> Procedūra: `.claude/commands/dienas-rutina.md` (115 rindas — izlasi VISU pirms sākt). Ja tavs harness nav Claude Code: `wiki/operations/portability.md`.

## 0. Tu esi cits modelis — ko tas nozīmē (izlasi pirmo)

- **Standing rule (CLAUDE.md § Standing Decisions): ekstrakciju un visus latviešu tekstus raksta Opus.** swe-2 subaģenti ir atkāpe no šī noteikuma. To pieņēmis operators (2026-09-20 ~22:50, sarunā: „šodienas rutīnu došu citam aģentam”). Atkāpes paraugs ir **2026-08-10 uzraudzītais izņēmums** (CHANGELOG 2026-08-10 (1)): cits modelis izpildīja ekstrakciju, bet orķestris pārbaudīja KATRU rezultātu, un tieši QA noķēra to, ko lints neredz — **izdomātus virsrakstus, darbības vārda stipruma paaugstināšanu („pieļauj” → „prasa”), retvītu ar verbatim citātu kā paša pozīciju.** Tas ir tavs pienākums šovakar: orķestris lasa katru subaģenta claim, ne tikai skaitļus.
- **Latviešu valodas vārti** (CLAUDE.md § Output Conventions): katrs jauns LV teksts (stance, reasoning, piezīme, pārskata rindkopa) — locījumi, garumzīmes, darbības vārdu formas, bez kalkiem („Dienas pārskats”, ne „brief”). Ja neesi drošs par formu — pārfrāzē. `claims.quote` ir VERBATIM, arī ar autora kļūdām.
- **Diakritiku dreifs (T4):** ja `src/quality.py` validators nostrādā tavā galvenajā kontekstā — apstājies, sāc svaigu sesiju. Subaģenti ar tīru kontekstu no tā izvairās — tāpēc ekstrakcija iet subaģentos, ne orķestrī.
- **Publicēšana paliek pie operatora.** Pārskats, attēls, deploy, sociālie — katrs ar atsevišķu vārdisku „jā”. Tas, ka rutīna nodota tev, NAV atļauja publicēt.
- **Stop beats write.** Divi noteikumi konfliktē un nevari izšķirt → apstājies un ziņo.

## 1. Stāvoklis 22:40 LV (komandas, kas to deva, zem tabulas)

| solis | stāvoklis |
|---|---|
| 1 Ielāde | rīta ķēde 5/5 — **613 dokumenti, no tiem 600 ap 00:xx** (nakts skrējiens), pēc tam tikai 13 (16–20 h). **Vakara ingests NAV noticis.** |
| 2 Pozīciju analīze | 40/45; 40 pozīcijas šodien. Trūkst 5 subjekti / 11 dokumenti: Latvijas armija (NBS) 6, Andris Šuvajevs 2, Valsts kontrole 1, Latvijas Darba devēju konfederācija 1, Andris Kulbergs 1 |
| 3 Pretrunu pārbaude | 40 pozīcijas pārbaudītas, 0 atradumu, medību pēda ierakstīta `logs` — **jāatkārto jaunajām pozīcijām pēc 2. soļa** |
| 4 Devils-advocate | nav ko pārskatīt |
| 5 Spriedzes | 0 šodien; 22 politiķiem jaunas pozīcijas → `saites_proposals.py --days 1` vēl nav palaists |
| 6 Konteksta piezīmes | 0 šodien |
| 7 Dienas pārskats | nav par 2026-09-20; pēdējais — 2026-09-19 (note 619, rakstīts 01:19) |
| 8 Attēls | — |
| 9 Wiki sync | 22:35 |
| 10 Renders | 22:35 (deploy versija `284a647a`, sk. § 3) |
| Saeima | šodien svētdiena, sēdes nav. 17.09. sēdes turpinājums gaidāms **ceturtdien 24.09.** — ielādēt PIRMS tās dienas pārskata |
| Nedēļas pārskats | pēdējais 09-07…09-13. Nedēļa 09-14…09-20 beidzas šodien; `weekly-routine.md` saka „piektdien vai pirmdien” → **ne šovakar**, pirmdien |

Komandas: `print_routine()`; `SELECT substr(scraped_at,12,2),COUNT(*) FROM documents WHERE scraped_at LIKE '2026-09-20%' GROUP BY 1`; nesaanalizētie — `documents.reviewed_at IS NULL` × `document_politicians.role='subject'` × `scraped_at LIKE '2026-09-20%'`; `SELECT COUNT(*) FROM claims WHERE claim_type='position' AND date(created_at)='2026-09-20'` → 40.

## 2. Ko darīt šovakar, secībā

1. **Vakara ingests vispirms** (operatora noteikums: dienas pārskats TIKAI pēc otrā ingesta). `scripts/morning_ingest.py` ilgst ~15 min — palaid fonā, ne priekšplānā ar noklusēto timeout (citādi kluss daļējs skrējiens). Pēc tam `print_routine()` — 1. soļa skaitlis jāpieaug; ja 0 jaunu, tas ir signāls pārbaudīt avotus (T12), ne „tukša diena”.
2. **2. solis — ekstrakcija subaģentos** pēc `.claude/agents/claim-extractor.md` (kanoniskais prompts, ~48 KB — subaģents to izlasa pilnībā). Sadalījums pēc rindas garuma (`dienas-rutina.md` 2. punkts): NBS ar 6 dokumentiem — savs subaģents; četri mazie (Šuvajevs 2, VK 1, LDDK 1, Kulbergs 1) — var vienā, **bet katrs claim nes SAVA subjekta `opponent_id`** (krusteniskā piedēvēšana ir kopīgā aģenta kļūdas veids). Pēc vakara ingesta rinda būs garāka — pārrēķini sadalījumu no `print_routine()`.
   - Katram subaģentam: `save_analysis()` atgriež `failures` — orķestris LASA sarakstu; katrs `missing_source_url` / `silent_dedup` ir reāls zaudējums (T2, T3). `empty_doc_ids` obligāts, kad dokuments nedod claim (T5) — citādi tas rindā paliek mūžīgi.
   - Pārbaude pēc katra: `stored == intended`; `SELECT COUNT(*) … WHERE reviewed_at IS NULL` sarūk par apstrādāto skaitu.
   - **Orķestra QA katram claim** (2026-08-10 saraksts): (a) virsraksts/stance nav izdomāts — atrodams avota tekstā; (b) darbības vārda stiprums nav paaugstināts; (c) retvīts/citāts ar cita vārdiem nav kā paša pozīcija; (d) `NEEDS_REVIEW:` prefikss, kur atsauce netieša (eskalācija #2); (e) LV gramatika stance/reasoning laukos.
3. **3. solis** jaunajām pozīcijām: `search_similar_claims(..., claim_type_filter=['position'])` (T10), `store_contradiction()` ar `confirmed=0`; **arī pie 0 atradumiem ieraksti medību pēdu** `logs` tabulā (komanda `dienas-rutina.md` 3. punktā — citādi statuss ziņo `missing`). Zero ir normāls iznākums (~1 publicējama uz ~2700 pāriem) — neražo atradumus.
4. **5. solis** `scripts/saites_proposals.py --days 1` → katru priekšlikumu pret avota dokumentu → `scripts/saites_accept.py <id> --topic "<kanoniskā>" --description "<viena rinda, latviski, bez #NN>" [--type spriedze|uzbrukums|atbalsts]` vai `--reject`. **Aprakstam viena rinda bez jaunrindām** — tas nonāk markdown tabulas šūnā (CLAUDE.md inv #8, carrier asymmetry).
5. **6. solis** konteksta piezīmes: append-only, vispirms `SELECT … FROM context_notes WHERE note_type='context'` par tēmu; B forma ≤120 vārdi, 4+ nosaukti aktieri; piezīme nonāk pārskatā verbatim.
6. **7. solis** pārskats pēc `.claude/agents/brief-writer.md` + `wiki/operations/agenti/brief-shared-rules.md`. Skelets no `generate_daily_brief()`; `### Pārējās tēmas` tabula nedrīkst pazust (T7). Lead = tikai TAJĀ dienā jaunais (operatora korekcija 09-xx: verificē svaigumu). Ministru piedēvēšana pret `tracked_politicians.role` + svaigu avotu, ne pret vecu piezīmi. Rindkopa nedrīkst sākties ar „N. ” (markdown `<ol>` slazds). **Jauns kopš šodienas (§ 3):** sākumlapas kartīte rāda pārskata `## Galvenais` PIRMO punktu kā kopsavilkumu (≤300 zīmes) — raksti to kā patstāvīgu teikumu, kas saprotams bez pārējā.
7. **Operatora vārti pirms deploy** (visi UN): pārskats nodots proofread; `@graphics-designer` ekvivalents → attēls → operatora „jā” → `brief_images.approved=1`; `scripts/approve_publish.py 2026-09-20`; `check_output.py --publish-gate-only` 0 bloķētas; `bash scripts/deploy.sh --dry-run --no-delete` → parādi izvadi → **atsevišķs „deploy”** → `bash scripts/deploy.sh --no-delete` (pilns koks, T15 — melnraksts, kas ir `output/atmina/blog/`, aizbrauc līdzi). Pēc deploy: `curl` 200 pārskatam, `og:image`, sākumlapā jaunā kartīte ar 2026-09-20.
8. **Sociālie** (`/social-thread` procedūra `.claude/commands/social-thread.md`) — atsevišķs melnraksts, atsevišķa atļauja; tvīts nesākas ar `@`; «Diena skaitļos» bez „0 pretrunu”.

## 3. Kas šodien mainījās vietnē (lai nebrīnies)

- **Sākumlapa (deploy `d9417046`, `7d9f5e37`, `284a647a`):** zem meklētāja josla „Jaunākais” — jaunākais pārskats + jaunākā analīze ar kopsavilkumiem; karuselis vairs nerāda vecu pretrunu, ja 14 dienās nav svaigas; „Jaunākie pārskati” rāda nākamos trīs, „Vairāk analīžu” nākamās divas. Spec `docs/superpowers/specs/2026-09-20-landing-jaunakais-design.md`; testi `tests/test_dashboard_latest.py`. Renderis `index.html` hash ir `tests/fixtures/render_baseline_dashboard.json` — pēc pārskata renderā tas mainīsies likumīgi (`REGEN=1 pytest tests/test_render_chars.py`, tad commit).
- **Partiju tests publicēts** `analizes/partiju-tests.html` (CHANGELOG 2026-09-20 (17), (19)). `grep -rl partiju-tests output/atmina | wc -l` > 0 ir norma tagad. q10/ASL pārkodēta uz klusē pēc operatora atradnes — rubrikas zars bija kļūdains; D1b audita brīfs `docs/plans/2026-09-20-partiju-tests-v2-briefi.md` § D1b (ne šīs rutīnas darbs).
- **VAD analīze** `analizes/vad-2026.html`: politiķu vārdi ir profila saites; `vad-izmeklesana-2026`: uzkrājumu summēšanas kļūda labota (Burkāns 137 510 €).
- **Pārskats 2026-09-19** labots DB („skaņts” → „saskaņots”, note 619, `data/rollback_brief_619_saskanots_2026-09-20.sql`).
- Partiju testa gaišais attēls pārģenerēts (deploy `189ac9d5`, 22:55).
- Darba koks tīrs pie `94daeca2`; `wiki/dailies/` ir gitignore (tā kopija labota lokāli).

## 4. Delegēšana swe-2 subaģentiem — kas iet ārā, kas paliek orķestrī

| iet subaģentam (tīrs konteksts, savs scratchpad `scratchpad/<solis>-<kods>/`, nekādu git) | paliek orķestrī |
|---|---|
| ekstrakcijas paketes (2. solis) pēc `claim-extractor.md` — raksta caur `save_analysis()`, atgriež `failures` + `stored/intended` | sadalījums paketēs, `failures` lasīšana, QA saraksts (§ 2.2), `reviewed_at` skaitītājs |
| `@devils-advocate` katrai jaunai pretrunai (ja būs) | `confirmed` paliek 0; nekad auto-apstiprināt |
| pārskata melnraksts pēc `brief-writer.md` (viens subaģents, saņem skeletu + dienas claims + piezīmes) | LV gramatikas + stila lasījums rindu pa rindai, T7 tabulas klātbūtne, lead svaigums, ministru piedēvēšana, `<ol>` slazds; nodošana operatoram |
| `@quality-reviewer` pēc `quality-reviewer.md` uz renderēto pārskata lapu (cietie vārti) | bloķē → labo → atkārto; nekad neapiet |
| attēla ģenerēšana pēc `graphics-designer.md` | operatora „jā” attēlam; `approved=1` tikai pēc tā |

Katram subaģentam brīfā: ceļš uz kanonisko promptu (`.claude/agents/<x>.md` — izlasīt pilnībā), `.venv/Scripts/python.exe` (nekad bare `python` — cita venv, daļējs raksts), DB rakstīšana tikai caur `store_*`/`save_analysis` (raw INSERT apiet vārtus), atgriezt saucējus (dokumenti lasīti / claims mēģināti / saglabāti / `failures`). Paralēliem aģentiem — unikāli failu nosaukumi; ja kāds raksta `data/rollback_*.sql`, katram sava (kopīgs ceļš 2026-08-03 iznīcināja četru aģentu drošības tīklu).

## 5. Ko nedarīt

- Nerakstīt pārskatu pirms vakara ingesta. Nepublicēt bez trim atsevišķiem „jā” (pārskats, attēls, deploy).
- Nelabot `claims.review_status` ar roku (trigeri); nerakstīt `now_lv()` UTC kolonnās (`political_tensions.created_at`, `analyses.created_at`).
- Nerakstīt nedēļas pārskatu šovakar. Neingestēt Saeimu (sēdes nav). Nesākt Partiju testa D1b/D2 — cits darbs, cits brīfs.
- Neaiztikt `content/partiju-tests/`, `curated/`, `assets/style.css`, `templates/index.html.j2` — šodien tikko publicēti, izmaiņas tur nav rutīnas darbs.
- Nemainīt `tests/fixtures/render_baseline_*.json` ar roku — tikai `REGEN=1 pytest tests/test_render_chars.py`.

## 6. Pārbaudes, ko orķestris izpilda pirms ziņo „gatavs”

```
.venv/Scripts/python.exe -c "from src.routine import print_routine; print_routine()"   # 10/10 vai skaidrs, kas nav un kāpēc
bash scripts/check.sh                                                                     # ruff + pytest (~2780) + smoke
.venv/Scripts/python.exe scripts/check_output.py --publish-gate-only                      # 0 bloķētas
bash scripts/deploy.sh --dry-run --no-delete                                              # tikai pēc operatora „deploy”
```

Ziņojumā operatoram: katrs skaitlis ar komandu, `failures` kopsumma, QA atradumi (cik claim laboti/atmesti un kāpēc), kas gaida atļauju. CHANGELOG ieraksts ≤5 rindas tikai, ja pieņemts lēmums vai mainīts invariants — dienas hronika ir `git log`.
