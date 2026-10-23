# Handoff 2026-09-25 (dienas sesija) — CLAUDE.md, backlog triāža, vārti, kas nevar nokrist

**Stāvoklis:** viss komitēts un pushots (`master` = `origin/master`, `6e38b686` + šī handoff commits). `check.sh` zaļš uz sapludinātā koda: 3069 passed. Neiekomitēti paliek tikai operatora 09-25 sociālie melnraksti (`docs/social/2026-09-25-*`, `docs/tweet_bank/2026-09-25-*`) — gaida publicēšanas atļauju.

## Kas izdarīts

1. **CLAUDE.md saīsināts** 53 130 → 44 265 B (`25009e99`, `ef55aa0c`): vēsture uz git (`git show f83b799c:CLAUDE.md`), dublikāti uz vienu vietu; numuri nemainīti. CHANGELOG 2026-09-25 (4).
2. **T4 pārmērīts** (`9927ca25`): Opus 5.5, 40 doki vienā kontekstā → 0/80 garumzīmju atteikumu; «~8 politiķi sesijā» robeža izņemta. Metode: `docs/audits/2026-09-25-t4-dreifs/`. CHANGELOG (5).
3. **Backlog triāža** (`387f2960`): 86 → 57 ieraksti; katram verdiktam pierādījums `docs/audits/2026-09-25-backlog-triaza/`.
4. **Vārti, kas nevar nokrist** — plāns `docs/plans/2026-09-25-varti-kas-nevar-nokrist.md`, sapludināts `6e38b686`. CHANGELOG (6):
   - pretrunu/pozīciju dienas skaiti (pārskats, nedēļa, kājene, rutīnas soļi 3–5) pa rutīnas dienu; `current_routine_day()`;
   - kājenes pāreja `FOOTER_ROUTINE_DAY_FROM = "2026-09-25"` — publicētās kājenes nemainās (171 datums, 0 atšķirību);
   - `@quality-reviewer`/`@brief-writer` prompti pa rutīnas dienu; statiskais vārts `tests/test_prompt_routine_day.py` (30 prompti);
   - Saeimas summary vārti `bill_votes_missing_summary()` pēc `vote_date`, arī `/Lp15`; `/saeima-ingest` saskaņots;
   - manifests: turpinājuma sēdes `continued_on` (arī ķēdes `29 / 5 / 12`), audits tās atlasa pēc datuma — **09-24 handoff 2. punkts (A / B etiķetes) ir slēgts**;
   - backlog indeksa tests salīdzina pilnu virsrakstu.
5. Runbooki atjaunināti: `commands.md` (manifests ar `--snapshot`, turpinājumi), `agenti/saeima-tracker.md`, `agenti/quality-reviewer.md`, `daily-routine.md` (pretrunas pirms pārskata).

## Šovakar (09-25 rutīna) — ko ievērot

- Šī ir **pirmā rutīna ar rutīnas dienas skaitiem**. Pēc pārskata pārbaudi, ka kājenes pretrunu skaits sakrīt ar pārskata `## Pretrunas` tabulu.
- **Pretrunu solis pirms pārskata** — pēc pārskata atrasta pretruna dienas pārskatā vairs nenonāk (tikai nedēļas).
- `print_routine()` pēc pusnakts joprojām noklusē uz kalendāra dienu — padod datumu ar roku (apzināti nemainīts).

## Gaida operatoru

1. **09-03 trūkstošie 4 balsojumi (plāna Task E)** — tīkls + DB rakstīšana: svaigs kalendāra momentuzņēmums → manifests ar eksplicītu `--snapshot` (jāredz `886631a9-…` ar `continued_on: ["2026-09-03"]`) → `audit_saeima_agenda_parity.py --year 2026 --dates 2026-09-03` (gaidāms: 4 trūkst) → `/saeima-ingest 2026-09-03` (gaidāms: 39, 15:12:57) → audits 0. Detaļas: `backlog/saeima.md`.
2. **09-24 kārtējās sēdes pilnīguma audits** (no 09-24 handoff 1. punkta) — šajā sesijā NAV darīts.
3. **F5 `migrations/` ietvars** — ieteikums NĒ, `BACKLOG.md` § Atliktais «gaida operatora apstiprinājumu».
4. **@AtminaLV retvītu ceļš** (9 doki, 39 junction rindas) — vai RT no projekta konta skaitās avots (`backlog/matcher.md`).
5. **Zīles doc 93439** (KVC vadītājs ≠ R. Zīle) — junction dzēšana + paterns «KVC vadītāj» (`backlog/matcher.md`).
6. Sociālie melnraksti 09-25 — publicēšanas atļauja.

## Termiņš

- **15. Saeima: `Lp14`/`Lm14`/`P14` iekodēts** 33 failos (`src/saeima/bills.py`, `parsing.py`, `votes.py` `_BILL_LIKE_MOTIF`, `render/_common/filters.py`) — pēc jaunās Saeimas sanākšanas (novembris) likumprojekti klusi pārstās parsēties un saistīties. Labot pirms 15. Saeimas pirmās sēdes (`backlog/saeima.md`). Paraugs: `bill_votes_missing_summary` (`GLOB '*/L[pm][0-9]*)*'`).

## Atlikti sīkumi (nav steidzami)

- Nedēļas loga kortežs būvēts divreiz, divi pretrunu skaita palīgi dala SQL (`src/briefs.py`).
- Promptu vārts neķer `strftime('%Y-%m-%d', col) = ?` / `substr(col,1,10) = ?` formas (šobrīd 0 tādu).
- Pārgadu turpinājums (dec. → jan.) audita 3. vārtos iziet ar 2 un neprecīzu padomu (pārregenerēt, nevis `--year <bāzes gads>`) — droši, bet maldinoši.
- `src/render/blog.py` kājenes komentāra pirmais teikums apraksta pāreju pa pārskata datumu, kods — pa rindu (otrais bloks pareizs).
