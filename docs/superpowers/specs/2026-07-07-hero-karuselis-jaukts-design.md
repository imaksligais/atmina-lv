# Spec: hero karuseļa jauktais saturs ("Uzmanības centrā" augšējā rotācija)

**Datums:** 2026-07-07 · **Statuss:** DONE + DEPLOYED 2026-07-07 (master `7353680`..`4bee25a`, pushots; deploy `--no-delete`, live-verificēts — 6 kartītes, grid-stack CSS un balsojuma josla apstiprinātas ar computed styles uz atmina.lv)
**Problēma:** hero karuselis (`hero_contradictions`, `templates/index.html.j2:28–69`) rotē tikai 5 jaunākās pretrunas. Pretrunu plūsma ir ~+1/7d → karuselis stāv uz vietas nedēļām, lai gan pozīcijas aug +182/7d.
**Risinājums:** karuselis rotē jauktu saturu — pretrunas + spilgtas svaigas pozīcijas + Saeimas balsojumi — sastāvu nosakot pēc svaiguma. Servera pusē uzbūvēts saraksts, rotācijas JS bez izmaiņām.
**Saistītais:** šī paša datuma kompozīta spec (`2026-07-07-uzmanibas-centra-rotacija-design.md`) — TĀ ir statiskā sekcija zemāk lapā un netiek aiztikta; karuselis ar to dala tikai dedup noteikumu (viens ekrāns nerāda vienu citātu divreiz).

## Verificētie dati (2026-07-07, dzīvā DB)

| Klase | Stāvoklis | Loma karuselī |
|---|---|---|
| Pretrunas confirmed=1, <14d | 1 | līdz 2; ja 0 — 1 jaunākā kā enkurs |
| Pozīcijas 7d, quote>40, salience≥0.7 | 58 | 2–3 spilgtākās |
| Saeimas balsojumi | jaunākais 2026-06-18 (vasaras pārtraukums) | 1–2 jaunākie BEZ svaiguma loga |

Balsojumu slazdi (verificēti): (a) jaunākā rinda ir procedurāla klātbūtnes reģistrācija ar 0/0/0 balsīm; (b) blakus rindas ar identisku `summary` (pantu/lasījumu balsojumi 92 un 89 Par).

## Sastāva noteikumi (`hero_feed`)

Kopā ≤6 kartītes, katra `{kind: "contradiction"|"position"|"vote", item: …}`:

1. **Pretrunas** — no orchestratora jau uzbūvētā `hero_cards` saraksta (excerpt loģika paliek): svaigās (`detected_at` <14d) līdz 2; ja svaigu nav — 1 jaunākā kā enkurs.
2. **Pozīcijas** — 2 spilgtākās pēc `salience` (3., ja cita klase savu kvotu neaizpilda un kopskaits paliek ≤6) (izšķirtne: jaunāka `stated_at`), logs 7d, `claim_type='position'`, `quote` NOT NULL un >40 zīmes, audience-izslēgšana (`journalist/organization/neutral/inactive`) — tas pats filtrs kā `_quote_of_day`. Viens citāts uz politiķi. **Dedup pret kompozītu:** izlaiž `source_url`, kas jau ir karstās tēmas citātos vai dienas citātā (padod izmantoto URL kopu no `assemble_focus` rezultāta).
3. **Balsojumi** — 1–2 jaunākie `saeima_votes` ar `result` NOT NULL un `total_par+total_pret+total_atturas > 0` (izslēdz procedurālas reģistrācijas), dedup pēc `summary` (ņem jaunāko no vienādiem). **BEZ svaiguma loga** — Saeimai ir brīvlaiki; datums kartītē vienmēr redzams.
4. **Secība:** sāk ar pretrunu; tālāk veidi mijas (blakus nestāv divas viena veida kartītes, cik atlikums ļauj).
5. Robežas LV laikā (`today_lv()`), ne `DATE('now')` (UTC slazds, 07-07 mācība).

Ja kāda klase tukša — karuselis dzīvo no pārējām; ja viss tukšs — sekcija paslēpjas kā līdz šim (`{% if hero_items %}`).

## Datu slānis

`src/render/focus.py` — jauna tīra funkcija `hero_feed(db, hero_cards, votes, focus, today=None) -> list[dict]` (nekādas DB rakstīšanas, kā pārējie focus helperi). Vienīgais jaunais SQL ir pozīciju vaicājums; balsojumus ņem no orchestratora jau nofetčotā `votes` saraksta (`_fetch_votes` rezultāts, DESC — satur `id`, `vote_date`, `summary`/`motif`, `total_par/pret/atturas`, `result`), tāpat kā pretrunas nāk no `hero_cards`. Pozīciju kartei atkārtoti izmanto `_person_card` + verbatim `quote` (CLAUDE.md vārtu izņēmums). Balsojuma saites mērķis = `balsojumi.html#vote-{id}` (tā pati idioma kā index `recent_votes` mini-tabulai; enkuri `balsojumi.html.j2:98` + hash-handleris :445, jaunākie balsojumi vienmēr ir SSR šardā). Mini-tabula "Pēdējie balsojumi" lapā paliek — karuselī ir 1–2 izceltie, tabulā 5 pilnie; tas nav dublēšanās tā paša satura izpratnē.

`src/render/dashboard.py`: `hero_items = hero_feed(db, hero_cards, focus)`; templotei padod `hero_items` (`hero_contradictions` mainīgo aizstāj).

## Šablons

Viens `hero-feature-card` rāmis, ķermenis pēc `kind`:

- **contradiction** — esošā kartīte bez izmaiņām (persona + split + "Skatīt pretrunu →").
- **position** — tā pati personas galva (avatars, vārds, partija · tēma); ķermenī citāts vienā pilna platuma rūtī, rūts etiķete = datums · avota domēns; badge "Pozīcija"; CTA "Skatīt profilu →" → `politiki/{slug}.html`. Citāts verbatim.
- **vote** — galvā "Saeimas balsojums" + datums (bez personas avatāra); virsraksts = `title`; ķermenī Par/Pret/Atturas josla (`focus-bloc-bar` stila; tikai šīs 3 vērtības — `Nebalsoja` NAV balss) ar skaitļiem un rezultātu ("Pieņemts"/"Noraidīts"); CTA "Skatīt balsojumu →".
- Punktu `aria-label` vispārināts pēc veida ("Pretruna/Pozīcija/Balsojums N").

Vizuālā valoda: esošais rāmis, avatari, badge un tipogrāfija nemainās (operatora dizaina-valodas atsauksme); jaunums tikai vidusdaļās. CSS — tikai jaunām vidusdaļām, esošajās idiomās.

## JS

Bez izmaiņām — rotācija strādā ar jebkādām `.hero-feature-card` (6 s intervāls, hover-pauze, punkti, reduced-motion tikai auto-gaitai).

## Testi un izvešana

- Hermētiski `hero_feed` testi (fixture DB): svaiguma kvota; enkura fallback, kad nav svaigu pretrunu; pozīciju dedup pret kompozīta URL; viens citāts uz politiķi; balsojumu 0-balsu un `summary`-dedup filtri; cap ≤6; mijas kārtība; visas klases tukšas → tukšs saraksts.
- `bash scripts/check.sh`; narrow renders `--only=dashboard`.
- **Augstuma stabilizācija:** pašreizējais `display:none`→`block` toggle (`assets/style.css:5711–5717`) liek skatuves augstumam lēkāt starp dažāda garuma kartīšu veidiem → metriku bloks zem karuseļa raustītos. Maiņa uz grid-stack: `.hero-feature-stage { display:grid }`, katra kartīte `grid-area:1/1; visibility:hidden`, `.is-active { visibility:visible }` — augstums vienmēr = garākā kartīte, fade animācija un JS paliek kā ir.
- Playwright 1440/375, gaišā UN tumšā tēma; focus-kompozīta baselines regen, ja mainās.
- `tests/test_render_chars.py` iesaldē index.html — pēc apzinātās maiņas `REGEN=1 pytest tests/test_render_chars.py` un baselines commit.
- Deploy `--no-delete` tikai pēc operatora apstiprinājuma (publish pause).

## Ārpus tvēruma

Spriedzes un partiju programmu solījumi karuselī (operatora izvēle 2026-07-07 — tikai pozīcijas + balsojumi); kompozīta sekcijas izmaiņas; JS pārbūve; jauns JSON feed.
