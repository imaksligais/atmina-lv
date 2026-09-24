# Reader-Facing Story Ideas: atmina Methodology & Data

> **INTERNAL DRAFT — not publish-ready.** Parent QA independently checked the live templates and found a material correction to idea #4: public pages load Umami analytics (`templates/base.html.j2`, `assets/htaccess.template`). Therefore “no analytics / no third-party tracking” is false for the current site, despite the stale statement in `ARCHITECTURE.md`.

**Date:** 2026-08-14 · **Author role:** DeepSeek reader-experience researcher (subagent)
**Scope:** 8 concise explainer/story ideas for readers, each with hook, 3-beat narrative, exact evidence, and social-video suitability score. Every number below was re-verified today with read-only queries against `data/atmina.db` (SQLite `mode=ro`) via `.venv/Scripts/python.exe`; query provenance is noted per number. No data was mutated.

---

## 0. Verification summary (read-only, 2026-08-14)

All figures re-derived live; nothing taken on faith from wiki/CHANGELOG.

| Fact | Verified value | Query used |
|---|---|---|
| Tracked politicians (total / active) | 223 / 194 | `COUNT(*) tracked_politicians`, `WHERE relationship_type!='inactive'` |
| Parties (with ≥1 active politician) | 18 (19 rows in `parties`, one has no active member) | join vs `tracked_politicians` |
| Documents | 74 253 | `COUNT(*) documents` |
| Documents by platform | twitter 36 214 · x_mention 23 621 · web 12 613 · vestnesis 1 763 · other ~42 | `GROUP BY platform` |
| Position claims (all / active politicians) | 5 653 / 5 601 | `claims` + join |
| Position claims by year | 5 361 of 5 653 (94.8 %) dated 2026; depth to 2011 (sparse) | `GROUP BY substr(stated_at,1,4)` |
| Position claims with verbatim quote | 5 191 of 5 653 | `quote IS NOT NULL AND quote!=''` |
| `saeima_vote` claims | 641 944 | `GROUP BY claim_type` |
| Cast ballots (Par/Pret/Atturas/Nebalsoja) | 641 944 — **exactly equals** `saeima_vote` claim count | `vote IN (...)` |
| Ballot split | Par 430 180 · Pret 117 727 · Atturas 59 648 · Nebalsoja 34 389 (Atturas = 9.3 % of cast) | `GROUP BY vote` |
| Attendance rows (Reģistrējies/Nereģistrējies) | 52 470 (not counted as claims) | `GROUP BY vote` |
| Contradictions | 29 total, **27 confirmed**; severity split across all 29 = 3 direct_contradiction · 15 minor_shift · 11 reversal | `contradictions`, `COALESCE(confirmed,1)=1` |
| Canonical topics in claims | 33 distinct | `COUNT(DISTINCT topic)` |
| Media coverage | median **6 claims/politician**; **34 of 194 with zero** media claims; median 12 for those with ≥1; max 413 (Kulbergs) | per-politician LEFT JOIN |
| Top-5 all-time position counts | Kulbergs 413 · Braže 238 · Valainis 220 · Siliņa 202 · Pūpols 190 | per-politician LEFT JOIN |
| Last-7-days media claims (my window) | Kulbergs 42 · Hermanis 13 · Dombrava 13 · Valainis 11 · Vītols 9 | `created_at >= datetime('now','-7 days','localtime')` |
| Unreviewed web documents | **5 101 of 12 613** (40 %); reviewed web docs 7 512 | `platform='web' AND reviewed_at IS NULL` |
| Claims flagged `needs_review` | 9 | `review_status='needs_review'` |
| Politicians with vote claims | 139 of 223 | `COUNT(DISTINCT opponent_id)` |
| Duplicate bill-stage groups | 25 of 565 | `GROUP BY bill_id,stage_name,stage_date HAVING COUNT(*)>1` |
| Proposal votes whose summary carries a reading-outcome phrase | 1 567 (`motif LIKE 'Par priekšlikumu%'` + `summary LIKE '%lasījumā%'`) — broader superset of BACKLOG's 246-row known-bad class | `saeima_votes` |

**Could not be re-verified live (documented in repo instead):** the ~1-publishable-per-~2 700-raw-pairs contradiction yield (CLAUDE.md escalation rule 3), the 30 476 attendance-claims purge (CLAUDE.md Data Contract 4b, 2026-07-25), the 1 408 quotes not literally findable in source (BACKLOG § Citātu integritāte). Also: `from src.routine import print_routine` fails in this environment (`.venv` numpy is a cp311/cp312 binary mismatch) — the wiki index's "222 ziņu raksti" backlog figure is the routine's own daily-sweep definition, so the report cites the raw verified counts (5 101 unreviewed web docs) instead.

---

## 1. “Atturēšanās nav neitralitāte” (An abstention is not neutrality)

- **Format:** 9:16 short-form explainer + 1:1 “quiz” card (reuses storyboard's “Kurš to teica?” / quote-card patterns).
- **Hook:** Saeimas kārtība: priekšlikums krīt, ja “par” nav vairākuma klātesošo — un atturēšanās skaitās klātesošo vidū. 1 no 11 nobalsošanām ir “atturas”.
- **3-beat narrative:**
  1. Saeimas mehānika: vairākums no klātesošajiem; `Atturas` un `Pret` atņem vairākumu vienādi — priekšlikums krīt abos gadījumos.
  2. atmina noteikums: balsojumu rakstām kā ierakstīts (“atturējās”, nekad “balsoja pret”); bet “atturējās” nekad netiek lasīts kā neitralitāte vai prombūtne — tas ir būtisks akts.
  3. Robeža (T14): viena procedurāla atturēšanās vēl nav pozīcija — jālasa balsojumu ķēde (references gadījums 2025-04-10: Progresīvie atturējās darba kārtības jautājumā un minūti vēlāk balsoja PAR to pašu projektu).
- **Exact evidence:** 59 648 `Atturas` no 641 944 nobalsošanām = 9,3 % (verified); CLAUDE.md “Abstention blocks” ruling (2026-07-25); CLAUDE.md T14.
- **Social-video suitability: 9/10.** Single binary concept, one clean number, quiz/community format proven in the existing storyboard; works with no audio.
- **Overclaim flags:** Neformulēt “atturēšanās = balsojums pret” kā absolūtu — pareizais formulējums ir “līdzdarbojas vairākuma noliegšanā”. Nerādīt vienu atturēšanos kā politiķa nostāju (T14). Neapgalvot, ka atmina to “atklāja” — tā ir pieraksta konvencija, ne atradums.

---

## 2. “Vārdi pret balsojumiem: kā atmina salīdzina nesalīdzināmo” (Words vs. ballots)

- **Format:** 16:9 methodology card + long-form blog explainer (natural fit for the about-page “Runas vs. rīcība” section).
- **Hook:** Politiķis saka vienu, balsojums rāda otru. atmina tur abus blakus — un par pretrunu sauc tikai to, ko pieraksts atļauj.
- **3-beat narrative:**
  1. Divas paralēlas virsmas: pozīcijas (5 653 pierakstīti izteikumi ar avotu) un balsojumi (641 944 nobalsošanas, viena claims par katru biļetenu).
  2. Pretrunu medības ir apzināti konservatīvas: embedding līdzība to nevar izdarīt (T9) — vajag strukturālu SQL piegājienu ar obligātu frakcijas pārbaudi; devils-advocate filtrē; ~1 publicējams no ~2 700 jēl-pāriem; nekas nepublicējas bez apstiprinājuma.
  3. Godīgais griests: 27 apstiprinātas pretrunas pret 641 944 biļeteniem + 5 653 pozīcijām — pretrunas trūkums nav konsekvences pierādījums.
- **Exact evidence:** counts above (verified); CLAUDE.md T9/T10 + escalation rule 3; about.html.j2 “Runas vs. rīcība”.
- **Social-video suitability: 7/10.** Strong concept, needs a good “Teica / Balsoja” two-column visual (storyboard template exists); risks abstractness without a concrete named pair.
- **Overclaim flags:** 27 ir grīda, ne skaitīšana — “šīs ir visas pretrunas, kas pastāv” būtu nepatiess. “Nav pretrunas” ≠ “konsekvents”. atmina nevērtē — pieraksta; confidence ir ekstrakcijas skaidrība, ne apgalvojuma patiesība (par to saka pati about lapa).

---

## 3. “Bez avota nav ieraksta” (Provenance: no URL, no record)

- **Format:** 1:1 “avots ir” receipt card (storyboard has the exact template) + short explainer.
- **Hook:** atmina atsakās glabāt apgalvojumu, kuram nav citējama avota saites. “Bez avota nav ieraksta. Bez datuma nav atmiņas.”
- **3-beat narrative:**
  1. Vārti: claims bez `source_url` tiek nomesti validācijā (Data Contract #2) — nevis “pie datubāzes slāņa”, bet apzināti; idempotence uz (politiķis, URL, tēma) padara atkārtotas ielādes drošas.
  2. Citāts ir verbatim: politiķa paša drukas kļūda paliek (“Steidamas”, 2026-06-11) — labot citātu nozīmē citēt nepareizi; parafrāžu klase tiek vārtota, ekstraktoram ir 6 jautājumu kontrolsaraksts pirms katras atbildes.
  3. Robežas, ko sakām skaļi: 1 408 citāti avotā nav atrodami burtiski (dokumentēta klase, ne defektu saraksts); URL pārmantošana var atstāt claims bez dzīvā teksta (doc 72446); profila lapā citāts redzams tikai komentāru blokā.
- **Exact evidence:** 5 191 no 5 653 pozīciju claims nes verbatim citātu (verified); CLAUDE.md Data Contracts #2/#3, quote gate; BACKLOG § Citātu integritāte (c); storyboard “avots ir” card.
- **Social-video suitability: 8/10.** The receipt visual is instantly legible; good for WhatsApp/FB sharing; hook works as a one-liner.
- **Overclaim flags:** “Katrs apgalvojums ir verificēts” būtu pārspīlēts — ekstrakcija ir AI-asistēta un 1 408 citātu klase paliek neverificējama; neapgalvot pilnīgu citātu precizitāti. “Avots ir pārāks” — lapa pati to saka, nevis atmina.

---

## 4. REJECTED AFTER PARENT QA — “No tracking” is false on the current public site

- **Kas ir patiess:** publiskā izvade ir statisks HTML; nav lietotāju kontu un publiskā hostā nav atmina DB.
- **Kas ir nepatiess:** `templates/base.html.j2` ielādē `https://cloud.umami.is/script.js`, bet CSP atļauj `cloud.umami.is` un `gateway.umami.is`. Tātad pašreizējā vietne izmanto trešās puses analytics.
- **Secinājums:** šo ideju nepublicēt. Ja grib stāstu par arhitektūru, formulēt tikai “statiska vietne bez lietotāju kontiem un publiskas datubāzes”, ne “bez analytics” un ne “mēs tevi neizsekojam”. `ARCHITECTURE.md` šajā punktā ir novecojis.

---

## 5. “Ko atmina nesedz” (Selective coverage, said out loud)

- **Format:** 1:1 data-fact card + honest “limits” blog post; pairs with about-page disclaimer “Selektīvs pārklājums”.
- **Hook:** atmina seko 194 cilvēkiem un 33 tēmām — un saka to skaļi, tā vietā, lai izliktos par pilnīgu.
- **3-beat narrative:**
  1. Segums: 194 aktīvi politiķi, 18 partijas, 33 kanoniskas tēmas; mediāna 6 media-claims uz politiķi.
  2. Robi: 34 no 194 politiķiem bez neviena media claim; 5 101 no 12 613 web rakstiem joprojām nepārskatīti; sentimenta analīze noņemta kā neuzticama — vērtējumu nav.
  3. Godīguma garantijas: pārskatos “Pārējās tēmas” tabula — nekas nepazūd pēc konstrukcijas (T7); katrs skaitlis nāk ar saucēju.
- **Exact evidence:** all counts verified above; about.html.j2 Atrunas list; CLAUDE.md T7 (2026-07-24).
- **Social-video suitability: 7/10.** Honesty angle is refreshing and myth-busting; works as a list-card sequence; medium shareability.
- **Overclaim flags:** “Mēs sedzam Latvijas politiku” — nē, sedzam to, ko sedzam. 0-claims profils nav pierādījums, ka politiķis klusē: var būt nesegts medijs, matcher robs (diakritikas/uzvārdu kolīzijas), paywall vai aģentūras relīžu dublikātu filtrs.

---

## 6. “Kāpēc atmina nekauc: 27 pretrunas ir sistēmas darbs” (Contradiction yield is deliberately low)

- **Format:** 16:9 funnel visual + explainer; direct answer to the inevitable “tikai 27?” criticism.
- **Hook:** Simtiem tūkstošu biļetenu un tūkstošiem izteikumu — publicētas 27 pretrunas. Tas nav vājums; tas ir vārtu dizains.
- **3-beat narrative:**
  1. Piltuve: ~1 publicējams no ~2 700 jēl-pāriem; kandidāti → contradiction-hunter → devils-advocate → `confirmed=0` glabāšana; nekas nepublicējas automātiski.
  2. Kāpēc tik stingri: koalīcijas disciplīna un procedurālie balsojumi ražo viltus pretrunas industriālā apjomā (partiju-līmeņa plašā versija noraidīta tieši tāpēc: 18 914 tēmu-pāri → 1 807 pēc skrīniem); T14 prasa lasīt visu balsojumu ķēdi.
  3. Pareizais lasījums: arhīvs ir produkts, pretrunas ir bonuss; pretrunas trūkums nav konsekvences apliecinājums.
- **Exact evidence:** 29 total / 27 confirmed, severity split 3/15/11 (verified); CLAUDE.md rule 3; BACKLOG § Partiju pretrunas funnel; CHANGELOG 2026-08-06.
- **Social-video suitability: 8/10.** Trust-building “why we don't cry wolf” story; clean funnel visual; strong for community Q&A.
- **Overclaim flags:** Nesaistīt “27” ar “tās ir visas esošās pretrunas” — tikai tās, kas izdzīvoja konservatīvu piltuvi. Nesacīt “partiju līmenī liekulības nav” — plašā versija noraidīta trokšņa dēļ, ne pierādījumu trūkuma dēļ.

---

## 7. “Viens balsojums, viens ieraksts” (Vote claims = cast ballots, not attendance)

- **Format:** data-fact card with a big-number equality visual (641 944 = 641 944) + short explainer.
- **Hook:** atmina balsojumu skaitītājs neskaita sēdes — tas skaita biļetenus. Un katrs biļetens ir viens ieraksts.
- **3-beat narrative:**
  1. 2026-07-25 tīrīšana: 30 476 “ierašanās” claims izņemti; `saeima_vote` claim eksistē tikai par nobalsošanu (Par/Pret/Atturas/Nebalsoja) — reģistrēšanās paliek balsojumu pierakstā (52 470 rindas), ne claims.
  2. Pārbaude: nobalsošanas 641 944 == `saeima_vote` claims 641 944, precīzi (verified today).
  3. Kāpēc tas svarīgi: pirms 2026-04-11 pārklasifikācijas “pozīciju” skaits izskatījās 8× lielāks par īsto retorisko aktivitāti. Skaitļi nebija mazāki — tie bija pārklasificēti.
- **Exact evidence:** the equality (verified); CLAUDE.md Data Contract 4b; wiki/index.md note 2026-04-11.
- **Social-video suitability: 7/10.** Numbers-heavy but the equality visual is clean; good for a “kā mēs skaitām” explainer.
- **Overclaim flags:** “Visi Saeimas balsojumi” — nē: segums sākas 2022-11-01, 10 sēdes nekad nav auditētas, 2 ārkārtas sēdēs iespējami robi (BACKLOG § Saeima). Balsojumu ieraksti ir autoritatīvi, bet per-balsojuma frakcijas atribūcijai ir NULL robi (ST frakcija pazūd no avota 2026-04-16).

---

## 8. “Ko atmina apzināti nedara” (No sentiment, no verdicts, no auto-syntheses)

- **Format:** positioning/manifesto piece + launch-thread intro (pattern: `docs/tweet_bank/2026-04-19-intro-thread.md`).
- **Hook:** atmina nav vērtētājs. Nav “apstiprinājuma mērītāja”, nav sentimenta skalas, nav automātisku secinājumu — dažas lietas tika noņemtas, jo bija neuzticamas.
- **3-beat narrative:**
  1. Sentimenta analīze noņemta kā neuzticama; `sentiment=0.0` ir tikai shēmas saderība — nekad nerēķinām, nekad neglabājam.
  2. Sintēzes ir rakstītas ar roku (standing lēmums 2026-04-22); about lapa saka “Nepiedāvājam vērtējumu — secinājumi paliek lasītāja ziņā”.
  3. Kas to dara ticamu: publicēšanas pauze + cilvēka korektūra + operatora apstiprinājums katram izdevumam; meta-noteikums “stop beats write”.
- **Exact evidence:** CLAUDE.md (sentiment=0.0, standing decisions, publish pause); about.html.j2 Atrunas; CHANGELOG 2026-04-11.
- **Social-video suitability: 7/10.** Strong identity piece; best as text/thread with static cards rather than motion video.
- **Overclaim flags:** “Nulles redakcionāla sprieduma” nav — ekstrakcija pati ir spriedumu pilna (LLM aģenti, manuāla triāža, tēmu robežas). “Nav vērtējumu” ir apgalvojums par pasniegšanu, ne par pipeline iekšējiem lēmumiem. Nesacīt “bez AI” — tas ir AI-asistēts ar cilvēka vārtiem.

---

## 9. Cross-cutting overclaim / neutrality flags (apply to all ideas)

1. **“Arhīvs” ≠ “neitrāls”:** atmina sevi dēvē par atmiņu/arhīvu (storyboard: “Atmiņa nav partija. Atmiņa ir arhīvs.”). Tā ir pozicionēšana — bet pati ekstrakcija ir redakcionāla (kas tiek atzīts par pozīciju, tēmu robežas, ko izlaist). Jebkurš “mēs tikai pierakstām” formulējums jāprecizē: pierakstām saskaņā ar mūsu noteikumiem.
2. **Skaitļi ir dinamiska grīda, ne statisks fakts:** 5 101 nepārskatīti web dokumenti nozīmē, ka rīt pozīciju skaits būs lielāks. Visos materiālos pievienot “dati 2026-08-14” datumu.
3. **Pārklājuma asimetrija:** 34 politiķi bez media claims un Kulberga 413 claims nozīmē, ka “aktīvāko” saraksti ir pārklājuma artefakts tikpat daudz, cik aktivitātes mērs. Nekad neformulēt “šis politiķis klusē” — tikai “šim politiķim mūsu datos nav ierakstu”.
4. **Balsojumu autoritāte ≠ balsojumu interpretācija:** Saeimas ieraksti ir “nemainīga patiesība” (about lapa), bet 246 priekšlikumu balsojumu klase ar māsas-balsojuma kopsavilkumu (BACKLOG 2026-08-05, ~20k skarto claims; mans 2026-08-14 plašākais skrīns: 1 567 priekšlikumu balsojumi ar lasījuma-iznākuma frāzi) nozīmē, ka daļa stance teksta var nest cita balsojuma iznākumu. Pirms jebkura balsojumu-citāta materiāla — pārbaudīt pret `summary` un balsojumu ķēdi.
5. **“Pretrunas” vārds ir noslogots:** atmina pretrunu = ierakstīta, apstiprināta neatbilstība, nevis žurnālistikas “pieķeršana”. Visos materiālos lietot “atmina ierakstījusi”, ne “atmina atklājusi”.

## 10. Stale numbers found in existing public-facing assets (must fix before reuse)

- `docs/atmina-intro-video.html` scene 4 (“Mērogs”): **150 politiķi, 26 kanoniskās tēmas, 10k+ ieraksti** — versus verified 194 / 33 / 641 944+5 653. The video would publish stale figures today.
- `docs/social/visual-storyboard.html` “Datu fakts” card: **“11 atklātās pretrunas”** placeholder — verified confirmed count is 27 (29 total); card footer itself warns “atjaunot skaitli pirms publicēšanas”.
- `wiki/index.md` last-7-days top claims (Kulbergs 44, Hermanis 14, Kučinskis 9) vs my 2026-08-14 window (Kulbergs 42, Hermanis 13, Kučinskis 8) — window definition differs (routine's own vs `-7 days`); always restate the window when citing.
- `wiki/index.md` “33 likumi” and “222 nepārskatīts backlog” use project-specific definitions (laws = wiki law pages; backlog = daily-sweep queue); do not quote them as raw DB facts without the defining query.
