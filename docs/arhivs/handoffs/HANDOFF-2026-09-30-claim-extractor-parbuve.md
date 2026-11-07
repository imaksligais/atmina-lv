# Handoff 2026-09-30: claim-extractor pārbūve + atlikušā korpusa stance pārbaude
> **Dienas rutīnas turpinājums (otrā ielāde + pārskats): `docs/arhivs/handoffs/HANDOFF-2026-09-30-dienas-rutina.md`.**

> **NĀKAMĀ SESIJA — SĀC ŠEIT (stāvoklis 2026-09-30 vakarā).** Secība:
> 1. **HOLD: visi 8 IZPILDĪTI 2026-09-30 vakarā.** 7 — `data/rollback_stance_noquote_hold_2026-09-30.sql`; #6991 + publicētā pretruna #27 — jauns mehānisms `withdraw_contradiction()` (`confirmed=-1`, noindex labojuma lapa `pretrunas/27.html`, 10.05. pārskata saite rezolvējas), `data/rollback_withdraw_contradiction_27_2026-09-30.sql`, CHANGELOG 2026-09-30 (2). Vecais `output/atmina/assets/og/pretruna-27.png` paliek kokā kā neizmantots fails (nekaitīgs).
> 2. **IZPILDĪTS 2026-09-30 ~15:40:** deploy `97d46969`, `verify_host` 9/9, live #27 = «Pretruna atsaukta» + noindex, Siliņas lapā #6991 vairs nav. Operatora secība (09-30): (a) `/audit-integrity` → skripts — viens Opus palīgs darbā pēc plāna `docs/plans/2026-09-30-audit-integrity-skripts.md`; (b) vakara rutīna = pirmais v4 mērījums (`missing_support`/`support_not_in_source`, stored==intended); (c) v4 pirmajā rutīnā tīrs (22 aģenti, `support` atteikumi 0 — `docs/arhivs/handoffs/HANDOFF-2026-09-30-dienas-rutina.md`) → `later` tvītu kārta GATAVA palaišanai ar operatora «jā»: ievade `docs/audits/2026-09-30-stance-izlase/later_tviti/a01..a65.json` (3 758 pozīcijas, twitter+x_mention, `created_at` < v4; nekomitēti — `.git/info/exclude`), 65 vērtētāji + ~17 verifikatori ≈ 82 Opus, brīfi `BRIFI.md`, pēc tam `build_chunks.py verify later_tviti` → `_fix_stance_verdicts_2026_09_30.py later_tviti …` (dry-run → `--apply`) → `reembed_claims.py`. Agrākā aplēse: (twitter+x_mention ~3 900, ~68 vērtētāji + ~15 verifikatori ≈ 83 Opus; izlasē tvīti 11/54 A+B, web 1/20 — web atlikts, NE notīrīts). Iepriekšējais teksts: **Deploy** «bez citāta» kārtai (169 stance + 22 atsaukumi, DB kopš 09-30 vakara, NAV vietnē) + HOLD izpildei: pilns renders (lokāli jau izdarīts 09-30 vakarā; pirms deploy atkārto, ja DB mainījusies), `check.sh`, T15, `deploy.sh`, `verify_host` — tikai ar operatora «jā».
> 3. **Slānis `later`** (5 315 pozīcijas, ~110–120 Opus) — recepte sadaļā «bez citāta izpildīts»; palīgu skaitu pasaki pirms palaišanas.
> 4. **Promptu optimizācija** — `backlog/agenti-pipeline.md` § Aģentu promptu optimizācija (secība pieņemta: audit-integrity → skripts, tad quality-reviewer ar eval).
> Pirmajā rutīnā ar claim-extractor v4 skaties `failures`: `missing_support` / `support_not_in_source`.

**Operatora lēmums 2026-09-30:** pārbūve sāksies jaunā sesijā («ļoti garš, noteikti jāizdomā kaut kas»). Pēc tam jāiziet cauri visām atlikušajām pozīcijām. Šodienas stāvoklis ir aprakstīts `docs/arhivs/handoffs/HANDOFF-2026-09-30-citatu-triaza.md`.

## Kāpēc

Stance pret avotu nomērīts 1 696 pozīcijās: izlase 300 + aprīļa pilnā pārbaude 1 096 (`docs/audits/2026-09-30-stance-izlase/README.md`). Aprīlī A+B bija 47 %, bet arī jaunākajās (kopš maija) 16 %. Tātad pašreizējais ekstraktors kļūdas rada joprojām.

Tipiskās kļūdas:
- nomests piesardzības vārds («izskatās», «varētu»);
- jautājums vai ironija pārvērsta apgalvojumā;
- fakts paņemts no blakus dokumenta vai pavediena;
- mainīts laiks («sāks» → «sākušas»);
- apgriezts cēlonis un sekas;
- cita cilvēka vārdi vai pārpublicējums uzdoti par politiķa pozīciju.

Šie noteikumi `.claude/agents/claim-extractor.md` jau ir (Breadth self-check 2026-08-03, jautājumi Critical Rules § 9). Tie **nedarbojas lēmuma brīdī**. Tāpēc tikai saīsināt nepietiek.

## Mērījums (09-30)

- **Apjoms:** 597 rindas, 8 404 vārdi, ~63 KB (~16k tokenu).
- **Kur ir apjoms:** puse ir trīs sadaļās:
  - Step 3c žurnālistu/organizāciju slots, 11,8 KB (attiecas uz mazākumu dokumentu);
  - Critical Rules, 10,5 KB (katram noteikumam sava incidenta vēsture);
  - Step 4 `save_analysis` mehānika, 9,3 KB.
- **Vēsture promptā:** 49 claim ID atsauces un 46 «added/pievienots/precedent» marķieri. Prompts ir kļuvis par izmaiņu žurnālu.

## Pārbūves priekšlikums (advisor + orķestrators, 09-30)

1. **Kodols ≤ ~150 rindas.**
   - Loma.
   - «Kas ir pozīcija» — tā pati definīcija, kas `docs/audits/2026-09-30-stance-izlase/RUBRIKA.md` (6 klašu noteikumi). Ekstraktors un vērtētājs tad lieto vienu definīciju.
   - 7 jautājumu kontrolsaraksts.
   - Izvades forma.
   - NEEDS_REVIEW noteikums un LV vārti.
2. **Atsauces faili, ko lasa tikai vajadzības gadījumā.**
   - Žurnālistu/organizāciju slots («ja runātājs nav izsekotais politiķis, vispirms izlasi X»).
   - Tēmas no `src/topic_map.py` (nedublēt 33 nosaukumus).
   - `save_analysis` mehānika: uz `wiki/operations/agenti/` vai palīgfunkcija, kas validē JSON.
   - Incidentu arhīvs, kā `CHANGELOG-arhivs.md` CLAUDE.md gadījumā.
3. **Koda vārti, ne teksts.**
   - Katrai pozīcijai obligāts burtisks `support` fragments no avota. Rīku slānis pirms `save_analysis` pārbauda `support in doc_text`.
   - Tieši tā strādāja 09-30 verifikatori, un tas deva 582 ticamus formulējumus.
   - Slazds: nezināma atslēga claim dict tiek klusi izmesta. Tāpēc pārbaudei jābūt `src/tools.py`/`analyze.py` slānī, un tai vajag testu, kas redzēts krītam (mutācija).
4. **Viens dokuments = viens lēmums.** `src/extraction_plan.py` pako līdz 8 viena politiķa dokiem vienā aģentā, un fakti pārlec no doka uz doku (#710906, #553898, #6961, #6770, #7051). Tas ir izmaksu kompromiss, tāpēc lēmums ir operatora. Minimums: noteikums «stance drīkst citēt tikai ŠĪ dokumenta tekstu».

## Metode: eval pirms ieviešanas

- **Zelta kopa:** ~40 doki no šodienas verificētajām rindām, stratificēti pa kļūdu tipiem (sk. augstāk) + daži D_OK kā kontrole.
  - Avots: `aprilis/vout*.json` + `verify_out{1,2}.json` (verdikts un pareizais stance).
  - `doc_text` ņem no DB pēc `source_url`. Atsaukto claims `document_id` ir `data/rollback_stance_*_2026-09-30.sql`.
  - Ievades `vin*.json` nav komitēti; tie var būt lokāli, ja darba koks nav tīrīts.
- **Salīdzinājums:** vecais prompts pret jauno, bez rakstīšanas DB (tikai JSON izvade, aģentiem aizliegts `save_analysis`). Vērtē ar `RUBRIKA.md` (A+B īpatsvars). Ievieš tikai tad, ja jaunais ir labāks.
- Jau bija 2026-08-12 A/B eksperiments uz 11 precedentiem (kontrolsaraksta variants uzvarēja). Pārbaudi, vai tā rīku var izmantot atkārtoti (`CHANGELOG-arhivs.md`).
- **Enkuri:**
  - CLAUDE.md citē «claim-extractor.md Critical Rules § 8»;
  - `wiki/operations/quality-bars.md` norāda uz šo failu;
  - `tests/test_prompt_routine_day.py` skenē `.claude/`;
  - sinhronizē `wiki/operations/agenti/claim-extractor.md`.

  Saglabā šos enkurus vai tajā pašā commitā atjauno atsauces. Pirms beigām palaid `check.sh`.
- Pārbūve ir kanoniska nesēja pārveide. Vispirms vienas lapas plāns, tad operatora «jā», tad izpilde. Pirms dienas rutīnas ievieš tikai pārbaudītu versiju.

## PĒC pārbūves: jāiziet cauri visām atlikušajām pozīcijām

Operators 09-30: «jāiziet vēl cauri visiem atlikušajiem». Stāvoklis 09-30 (skaits no `build_chunks.py grade`):

| Slānis | Nepārbaudīti | A+B izlasē | Aplēse |
|---|---|---|---|
| later (ar citātu, ≥ 2026-05-01) | 5 315 | 16 % | ~850 |
| noquote (bez citāta) | 746 | 12 % | ~90 |
| april | 0 (+#164 — `document_id` uz neesošu dokumentu, atsevišķi) | | |
| + visas pozīcijas, kas izveidotas pēc 2026-09-30, līdz jaunais prompts ir ieviests | | | |

**Kāpēc pēc pārbūves:** citādi vecais prompts turpina radīt jaunas kļūdas, kamēr vecās tiek labotas.

**Rīki (gatavi):**
- `docs/audits/2026-09-30-stance-izlase/build_chunks.py`: `grade <slānis> <mape>` → `a*.json` pa 58; `verify <mape>` → `vin*.json` pa 55. Jau pārbaudītos ID izslēdz automātiski.
- `RUBRIKA.md`: kopējā vērtētāju/verifikatoru rubrika. Brīfu teksti ir šīs dienas transkriptā; būtība ir «izlasi rubriku, vērtē katru rindu, raksti tikai savu failu».
- `scripts/_fix_stance_verdicts_2026_09_30.py <scope> vin:vout …`: dry-run, tad `--apply`. Rollback `data/rollback_stance_<scope>_2026-09-30.sql` + `.ids`. Pēc tam `scripts/reembed_claims.py --ids-from …_stance.ids`.

**Apjoms (vajag operatora «jā» ar skaitu):**
- later: ~92 vērtētāji + ~18 verifikatori;
- noquote: ~13 + ~2;
- kopā ~125 Opus palīgi.

Vienlaikus var darboties 20 palīgi. Katram palīgam `model: opus`, aizliegtas git mutācijas, un tas raksta tikai savu failu. Varbūt vispirms lētāks priekšfiltrs (piemēram, tikai tvītu slānis vai augsta riska tēmas), bet par to lemj operators.

**Katrai kārtai:**
- orķestrators pats izlasa izlasi no gala tekstiem;
- `validate_lv_diacritics` visiem;
- `stored == intended`;
- HOLD saraksts operatoram;
- vakara renderā `politiki`;
- deploy tikai ar «jā».

## Atvērtie operatora jautājumi (no 09-30)

- **4 HOLD:** #6650, #7040, #7391, #7420 (README § Piemērots).
- **15 U** (stubs/saite bez teksta).
- **Dublikātu pāri vienā avotā (T2):** #6657/#7040, #6677/#6678, #43/#6902, #425/#6844, #11172/#11211, #7469/#7507, #7301/#11039, #6683/#6734/#6802, #428/#411.
- **~40 `quote`, kas nav politiķa vārdi:** atzīmēti `vout*.json` lv_notes.
- **Tēma pēc pārrakstīšanas neatbilst:** #6659, #11043. Tēma ir idempotences atslēgā — pirms maiņas vajag sadursmes vaicājumu.
- **Melbārdes `role`** (T6).
- **Datu posti bez viedokļa** (#254, #7397, #310, #21): vai tā ir pozīcija?
- **Ne-politiķa citāti no citātu triāžas:** 11 OPERATOR «citāts no cita dokumenta» rindas + 41 KEEP ar izlaidumu.

## IZPILDĪTS 2026-09-30 pēcpusdienā

- Pārbūve ieviesta, commit `4bee90d4`: kodols 96 rindas, atsauces faili `.claude/references/claim-extractor/`, `support` vārti `src/support.py` → `save_analysis`. Eval un kalibrēšana: `docs/eval/claim-extractor-prompt-v4-2026-09-30.md`.
- Deploy: pilns renders ar `politiki` (199 profili), versija `36dfb8c1`, `verify_host` 9/9. ~700 stance labojumi kopš 09-30 ir vietnē. **Vakara rutīnā `politiki` vairs nav obligāts** (parastais tvērums).
- Pirmā rutīna ar jauno promptu: skaties, vai `failures` parādās `missing_support` / `support_not_in_source`, un vai saglabāto skaits == iecerētais. Ja aģenti bieži atkārto saglabāšanu, tas ir signāls, ka `support` noteikums promptā ir neskaidrs.
- Atlikušo 6 061 pozīciju pārbaude NAV sākta — operatora lēmums.

## 2026-09-30 vakars — slānis «bez citāta» izpildīts (pirmā daļa no atlikušajiem)

- 746 pozīcijas: 22 atsauktas, 169 stance laboti + re-embed, 8 HOLD. Detaļas + HOLD saraksts: `docs/audits/2026-09-30-stance-izlase/README.md` (pēdējā sadaļa). Rollback `data/rollback_stance_noquote_2026-09-30.sql`. 17 Opus palīgi (13 + 4).
- **NAV deployots.** Vakara rutīnas renderam jāietver `politiki` (vai pilns renders); deploy — ar operatora «jā».
- **Atlicis: slānis `later` (5 315, ar citātu, ≥ 2026-05-01).** Recepte tā pati: `build_chunks.py grade later <mape>` (~92 vērtētāji pa 58), `verify` (~18–25 verifikatori; A+B var būt augstāks par izlases 16 % — «bez citāta» slānī bija 20 % pret izlases 12 %), `_fix_stance_verdicts_2026_09_30.py later …` (dry-run → `--apply`), `reembed_claims.py`. Vērtētāju/verifikatoru brīfi: `docs/audits/2026-09-30-stance-izlase/BRIFI.md`.

### «Bez citāta» HOLD (8) — OPERATORA LĒMUMS 2026-09-30: visi ieteikumi pieņemti, izpildīt nākamajā sesijā

**Izpildes plāns (viens labojumu skripts + rollback, pirms tam dry-run):**
- atsaukt: #6991, #22992, #20621, #6739, #704274 (pretrunu atsauces pārbaudīt — #6991 ir pretrunā #27);
- pretruna #27 → `confirmed=0` (nedzēst), jo tās vecā puse #6991 tiek atsaukta; pirms tam pārbaudi, vai #27 minēta publicētos pārskatos/sintēzēs (grep `output/` un `wiki/synthesis/`) — ja ir, tas ir atsevišķs operatora jautājums;
- pārrakstīt + re-embed: #22993, #521029 (verifikatora formulējumi zemāk 2. punktā / `noquote/vout0*.json` lv_notes), #703920 (verifikatora formulējums ar «Ironiski apgalvo … izskatās …»);
- LV vārti visiem jaunajiem tekstiem; saglabāts == iecerēts; vakara renderā `politiki` + `pretrunas`; deploy tikai ar operatora «jā».

Ieteikumi (pieņemti):

1. **#6991 Siliņa + publicētā pretruna #27 (`confirmed=1`).** Claim ir Saeimas balsojuma apraksts; Siliņa tekstā nerunā. Pretrunas #27 kopsavilkums to pats atzīst («tiešs Siliņas aizstāvības citāts nav fiksēts»). Citas Siliņas aprīļa pozīcijas par Sprūda aizstāvību DB nav (vaicājums: viņas `position` ar «Sprūd» → pirmā ir 05-07). *Ieteikums:* atsaukt #6991 un #27 noņemt no publicētajām (`confirmed=0`, nevis dzēst), ar rollback. Ja operators uzskata, ka premjera koalīcijas balsojums ir viņas rīcība, — #6991 pārrakstīt «Viņas vadītā koalīcija …» un #27 atstāt.
2. **#22992, #22993, #521029 Kulbergs — koalīcijas līgums un valdības deklarācija.** Vienreizējs klases lēmums. *Ieteikums:* valdības deklarācija = premjera paša dokumentēts akts (rubrikas 1. klase) → #22993 un #521029 paturēt ar verifikatora formulējumu («Paredz savas valdības deklarācijā …»); partiju koalīcijas līgums ≠ viņa personīga pozīcija → #22992 atsaukt. Lēmumu ierakstīt `RUBRIKA.md` 1. klasē.
3. **#20621 Kulbergs — REPOINT uz doc 42024 nav iespējams bez sadursmes:** tajā dokumentā jau ir #20824 (`Valsts pārvalde`) un #20822 (`Koalīcija un partijas`) — T2 atslēga. *Ieteikums:* atsaukt #20621 (tajā LETA dokumentā amatu dalīšana viņam nav piedēvēta); Kulberga «līdzvērtīgas atbildības» teikumu pievienot #20822 stance, ja vajag.
4. **#703920 Pūpols (sarkasms par Anitu Braunu).** Pašreizējā stance apgriež mērķi — viņš žēlo žurnālistus, nevis kritizē. *Ieteikums:* pieņemt verifikatora formulējumu ar «Ironiski apgalvo … izskatās …» (atrunas saglabātas), jo pašreizējā ir faktiski nepareiza.
5. **#6739 Abu Meri (paywall, 2024. gada atsauce).** Redzamajā tekstā viņš nerunā; «gaida iniciatīvu no speciālistiem» ir citu politiķu vārdi. *Ieteikums:* atsaukt (retrospektīva atsauce ≠ pozīcija šim dokumentam).
6. **#704274 Latvijas Banka.** Stance ir žurnālista teikums. *Ieteikums:* atsaukt; Fadejevas intervija ir eksperta viedoklis, ne iestādes pozīcija (`sloti.md` § Iestāde pret amatpersonu).
