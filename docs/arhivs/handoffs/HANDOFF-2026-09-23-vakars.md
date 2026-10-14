# Handoff 2026-09-23 (dienas sesija) — sākumlapas uzlabojumi, 22.09 sociālie posti, backfill 1. partija

**Stāvoklis:** viss komitēts un pushots uz privāto `origin/master`. Publiskais spogulis **nav** sinhronizēts (`docs/funding/repo-sync.md`). Dzīvē ir sākumlapa ar wrangler versiju `322196ab`. Backfill 1. partijas jaunās pozīcijas un citāti ir DB, bet **vēl nav renderēti un nav deployoti**.

## Izdarīts

- **Sākumlapa** (CHANGELOG 2026-09-23 (4)):
  - dedup: viens saturs vienā vietā;
  - «Uzmanības centrā» izkārtojums;
  - Līderu josla;
  - telefona pieskāriena mērķi, galvene un diagrammas.

  4 Devin SWE-2 max aģenti strādāja paralēlos worktree (recepte: `wiki/operations/devin.md` § Paralēli). `check.sh` 2921 passed. Deploy notika pēc **pilna** rendera, lai visas lapas saņemtu jauno `style.css?v=`. Dzīvi pārbaudīts.
- **Sociālie posti par 22.09 pārskatu** (X, FB, Reddit r/atminaLV) — **publicēti** (operators). Statuss atzīmēts `docs/tweet_bank/2026-09-23-dienas-parskats-social.md` un `docs/social/2026-09-23-*`.
- **Truncated backfill 1. partija:** visi truncated doki ar claims.
  - 101 pārlādēts (vidēji 47 → 383 vārdi).
  - 10 `@claim-extractor` aģenti: +34 claims (#717940–#717973, 8 `needs_review`).
  - 47 citāti aizstāti ar burtisku politiķa teikumu.
  - Pilnā atskaite, skaitļi un atradumi: `docs/audits/2026-09-23-backfill-batch1/README.md`.
  - Rollbacki:
    - `data/rollback_truncated_backfill_batch1_2026-09-23.sql`;
    - `data/rollback_claim_quotes_batch1_2026-09-23.sql`.

## Nākamajai sesijai

1. **Vakara rutīna 23.09** (`/dienas-rutina`). Neizskatīti doki ar `scraped_at` kopš 22.09: 579 (mērīts sesijas beigās). Daļa no tiem ir RSS ievada pārejas doki (iepriekšējais handoff). Renders un deploy aiznesīs arī backfill 1. partijas pozīcijas un citātus. **Viens politiķis = viens aģents** (`backlog/agenti-pipeline.md` § Paralēlos ekstrakcijas aģentus dala PA POLITIĶIEM). Šajā sesijā noteikums tika pārkāpts (Kulbergs 8+8). Dublikāts neradās, bet tikai laika nejaušības dēļ.
2. **Backfill atlikums: 2 455 truncated doki bez claims.** Pārlāde katru doku ieliek ekstrakcijas rindā, tātad tas ir aģentu darbs, ne tikai fetch. Kārtība:
   - partijās pa ~200 doku;
   - katrai partijai operatora «jā» + aģentu skaita novērtējums (Fan-out opt-in);
   - brīfa paraugs: `docs/audits/2026-09-23-backfill-batch1/brief.md`;
   - ID atlases vaicājums un skaitļi: README § Atlikums.
3. **Operatora lēmumi** (atskaitīts sarunā, nav izlemts):
   - **`needs_review` inflācija.** Kopš v3 prompta (CHANGELOG 2026-09-22 (4)) katrs atstāsts bez citāta = conf 0.6 = karodziņš (CLAUDE.md eskalācija 2). 22.09 karodziņš bija 37 % pozīciju; 14.–20.09 tas bija 0–10 %. Atvērtā rinda tagad ir 47, nevienam nav >14 d. Ieteikums, ko operators vēl nav apstiprinājis: aģents, kas katru karodziņu pārbauda pret avotu un raksta `Izvērtēts`. Alternatīva ir noteikuma maiņa (operatora lēmums).
   - **Backfill 1. partijas atradumi vecajos claims:**
     - 5 nepareizi nolasīti stance;
     - 5 biroja balss claims;
     - 8 dublikāti;
     - klase: conf>0.6 bez citāta;
     - neglabātas nostājas tēmu sadursmes dēļ;
     - junction robi.

     Saraksts: README; ieraksts `backlog/dati-db.md` § 2026-09-23 backfill izmēģinājums.
   - **Operators apstiprināja plānu 2026-09-23 sesijas beigās («ok»).** Plāns attiecas uz 1. partijas atradumiem vecajos claims. Izpilde notiks jaunajā sesijā. Pirms jebkura raksta sesija operatoram parāda dzēšamo un pārrakstāmo rindu sarakstu. Katram labojumam ir pāra `data/rollback_*.sql`. Ja mainās `stance`, rinda jāpārembedo ar `scripts/reembed_claims.py`.

     | Kategorija | Skaits | Rīcība |
     |---|---|---|
     | Stance nolasīts nepareizi (#527890, #532366, #18366, #18324, #521029) | 5 | Pārrakstīt stance pēc avota. |
     | Dublikāti (README § Dublikāti) | 8 pāri | Paturēt pirmo/pirmavotu, otro dzēst. |
     | Biroja/padomnieka balss (#521116, #531904, #532350, #521026, #20722) | 5 | Dzēst pēc 2026-08-25 noteikuma. Ja tā pati nostāja ir politiķa paša avotā, tas paliek. |
     | `confidence>0.6` bez tieša citāta | ~11 šeit, visticamāk daudz vairāk DB | **NElabot šoreiz.** Tā ir visas DB klase: pazeminot ticamību, katrs claim dabū NEEDS_REVIEW un rinda uzbriest. Vajag atsevišķu operatora lēmumu. |
     | Neglabātas nostājas tēmu sadursmes dēļ (Kulbergs 46167, Tavars 56037, Rinkēvičs 56685 u.c.) | ~6 | Katru izvērtēt: glabāt citā pamatotā tēmā vai apvienot ar esošo. |

     Dzēšot claim, avota dokuments paliek profila X/ziņu virsmā (CLAUDE.md § Deleting a claim). Atskaitē pasaki, kuru virsmu tīrīji.
4. **DB momentuzņēmumi dzēšanai pēc apstiprinājuma** (katrs ~2,7 GB):
   - `pre-ui-landing-20260923`;
   - `pre-backfill-trial48-20260923`;
   - `pre-backfill-batch1-20260923`;
   - `pre-swe2-agent-20260922`.
5. Sīkumi:
   - `analizes.html` telefonā 360 px ritinās horizontāli par 15 px (vecs defekts, `backlog/vietne-ui.md`);
   - publiskā spoguļa sync.
