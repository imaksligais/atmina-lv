# Nedēļas stāsti — jaunais nedēļas pārskats (dizains)

Datums: 2026-11-01. Statuss: operators apstiprināja 1. un 2. daļu sarunā; šis fails gaida pārskatīšanu.

## Mērķis

Nedēļas pārskats apstājās pēc 2026-10-11, jo svētdienā vajadzēja uzrakstīt gan dienas, gan nedēļas pārskatu, un tas aizņēma pārāk daudz laika un aprēķinu. Atsākot tam jābūt tiešām lasāmam un interesantam: daži stāsti par to, kas nedēļā mainījās, nevis tēmu saraksts ar pozīciju skaitiem.

Panākumu kritēriji:

- Pārskatā ir 3–5 stāsti, kopā ~700–1 000 vārdu (vecais ~1 800).
- Katrs stāsts balstās vismaz divos avotos vai pozīcijās, ko aģents izlasīja pilnībā.
- Pārskats iziet `lint_lv_style`, saglabāšanas pārbaudi un `@quality-reviewer` § H.
- Aģenta darbs maksā mazāk nekā vecais. Pirmajā palaidienā izmērām tokenus un salīdzinām ar 2026-10-11 pārskatu.

## Kas paliek kā bija

- Rakstīšana un publicēšana **pirmdienas rītā** par iepriekšējo nedēļu (pirmdiena–svētdiena). Svētdien tikai dienas pārskats.
- `note_type='weekly_brief'`, `store_context_note`, adrese `nedela-<YYYY-MM-DD>`, `approve_publish.py`, `@quality-reviewer` pirms deploy, `weekly_vote_breakdown()` kā vienīgais frakciju skaitļu avots.
- Featured image caur `## Vizuālais brief` bloku.
- Vecie nedēļas pārskati netiek pārrakstīti. Jaunā forma attiecas tikai uz jauniem.

## 1. Struktūra lapā

```
# Nedēļas stāsti, <sākums> – <beigas>

## <Kas ko izdarīja, teikuma reģistrā>
60–220 vārdi. Sāk ar faktu un dienu («Otrdien Saeima…»).
0–2 citāti ar personu un saiti pie apgalvojuma.
Ja kaut kas mainījās salīdzinājumā ar agrāk, nosauc abus punktus ar datumiem.
Beidzas ar pēdējo konkrēto faktu: nākamais solis, datums, balsojums vai atbilde.

## … (3–5 stāsti, svarīgākais pirmais)

## Īsumā
0–5 teikumi, katrs ar saiti. Ja nav ko teikt, sadaļas nav.

## Ko gaidīt
Tikai datēti notikumi ar nedēļas dienu un datumu. Ja tādu nav, sadaļas nav.

## Nedēļa skaitļos
<!-- WEEKLY_STATS: … -->   (deterministisks, kā līdz šim)

## Kas kustējās
![Kas kustējās](…movers.svg)   (deterministisks, kā līdz šim)

## Vizuālais brief
(Tēma / Galvenā tēze / Skaitlis / Metaforas hint — featured image ievaddati)
```

Izzūd: «Nedēļas stāsts» prozas ievads, «Nedēļas galvenās tēmas» ar pozīciju skaitiem, «Koalīcija vs Opozīcija» tabula, atsevišķa «Pretrunas» sadaļa (publicēta pretruna kļūst par stāstu, ja tā ir svarīga).

Virsraksti bez numuriem: rindkopa, kas sākas ar «1. », kļūst par `<ol>` (zināms slazds). Virsraksts nosauc, kas ko izdarīja, nevis ir efekta frāze.

## 2. Stāstu kandidāti (kods)

Jauna funkcija `weekly_story_candidates(db, week_start) -> list[dict]` failā `src/briefs.py`. Katrs kandidāts: `kind`, viena rinda fakta, `claim_ids` / `vote_ids` / `contradiction_ids`, `topic`, `days` (kurās dienās). NEEDS_REVIEW pozīcijas izslēgtas vienmēr.

| `kind` | Signāls | Slieksnis / avots |
|---|---|---|
| `contradiction` | publicēta pretruna | `confirmed=1`, `detected_at` nedēļā, `withdrawn_at IS NULL` |
| `vote_split` | frakcija nebalsoja vienoti, vai koalīcijas partija pret savu bloku | no tiem pašiem datiem kā `weekly_vote_breakdown`; `⚠ NESAKRĪT` balsojumus izlaiž; ķēde pēc `document_nr` (T14); koalīcija pēc `coalition_at()` |
| `topic_surge` | tēmas pozīcijas pret iepriekšējo 4 nedēļu vidējo | ≥8 pozīcijas un ≥×2 |
| `tension_pair` | kas kam uzbruka vairāk nekā vienreiz | `political_tensions.created_at` ir UTC → `DATE(col,'localtime')` (T17) |
| `followup` | pagājušās nedēļas «Ko gaidīt» punkts | esošā `_previous_forward_look()` |
| `daily_lead` | dienas pārskatu «Galvenais» treknie punkti | atzīme, ja tā pati tēma vadīja ≥2 dienas; diena pēc `brief_subject_date()` |
| `new_voice` | politiķis ar 0 pozīcijām iepriekšējās 30 dienās | `relationship_type` nav `inactive` |

Mērījums 2026-10-26…11-01 (pirms ieviešanas): 3 publicētas pretrunas; «Korupcija un KNAB» 19 pret vidēji 3,2; Liepnieks→Kulbergs 3 spriedzes; 60 balsojumi; 5 jaunas balsis. Signāli datos ir.

`generate_weekly_brief()` raksta kandidātus skeletā kā HTML komentāru `<!-- STORY_CANDIDATES … -->` (renderētājs to nerāda) un jaunās sadaļas kā vietturus.

## 3. Aģents (`@weekly-brief-writer`)

Prompts tiek pārrakstīts jaunajai formai. Aģents lasa kandidātu sarakstu, nevis visu nedēļu.

Izvēle:

- 3–5 stāsti. Prioritāte: publicēta pretruna vai frakciju šķelšanās → tēma, kas vadīja vairākas dienas → tēmas lēciens → spriedzes.
- Ne vairāk kā 2 stāsti no vienas tēmas.
- Katram stāstam ≥2 avoti vai pozīcijas, izlasītas pilnībā. Viens tvīts nav stāsts.
- Neizvēlēts kandidāts drīkst kļūt par vienu «Īsumā» teikumu.
- Atskaitē: «izskatīti N kandidāti, izvēlēti K», katram noraidītajam viens iemesls.

Valoda — viens saraksts § «Aizliegtie rāmji» (`weekly-brief-writer.md`), ar pierādījumiem no 25 vecajiem pārskatiem (48 191 vārds, bez citātiem un kastītēm):

| Rāmis | Trāpījumi / pārskatos | Kur |
|---|---|---|
| «iezīmē / iezīmējas» kā analītisks pildvārds | 46 / 13 | prompts + **lint** |
| «pavediens» >2× | 41 / 14 | prompts (jau bija) |
| treknraksts prozā | 350 / 25 | prompts: nedēļas pārskatā nekur; dienas pārskats patur savu bold pirmo teikumu |
| «nav X, bet Y» mūsu tekstā | 7 / 5 | prompts + QR (lintam par daudz viltus trāpījumu: puse ir politiķu vārdi) |
| «būtisks», «izšķirošs», «nozīmīgs» kā svarīguma uzpūšana | 15/11, 5/3, 2/2 | prompts: nesaki, ka svarīgi — saki, kas mainījās |
| «smaguma centrs», «divās līnijās», «caurviju» | 5/4, 3/3, 2/2 | prompts (jau bija) |
| «Jautājums ir», «nedēļa parādīja», «tādējādi» | 2, 1, 1 | prompts, viena rinda |

Strukturālie noteikumi (prompts + QR § H, spriedums, ne regex): stāsta pēdējais teikums nav punkta atkārtojums; pirmais teikums neatkārto virsrakstu; nav «kāpēc tas svarīgi» soļa; nav trīs paralēlu piemēru, kur pietiek ar diviem.

Saskaņojumi ar mājas noteikumiem:

- Domuzīme: atļauta sarakstos, virsrakstos un datumu diapazonos (to prasa `brief-shared-rules.md` saraksta forma); prozā labāk punkts vai komats. Lintā nekad.
- Atrunas: «ko viņš raksturo kā», «viņaprāt», «esot» ir obligāta atribūcija (CLAUDE.md § Harsh content), nevis vilcināšanās. Griež tikai MŪSU nedrošību virs avotota fakta («iespējams, varētu liecināt»).
- «uzsver» kā runas darbības vārds ir normāla ziņu valoda un nav aizliegts.
- Netiek pievienoti angliskā modeļa rāmji bez trāpījumiem mūsu tekstos («pavērsiens», «plašāka tendence», «liecina par», «Kopumā», «Būtībā», «uzsver nozīmi» — visi 0/25).

## 4. Koda izmaiņas

1. `src/briefs.py`: `weekly_story_candidates()`; `generate_weekly_brief()` jaunais skelets (H1 «Nedēļas stāsti», kandidātu komentārs, `## Īsumā`, `## Ko gaidīt`, esošie `WEEKLY_STATS` un movers bloki, `## Vizuālais brief`).
2. `src/tools.py` `_validate_brief_structure` weekly zars: pieņem jauno formu (H1, ≥3 `## ` stāstu virsraksti pirms `## Īsumā`/`## Ko gaidīt`/`## Nedēļa skaitļos`, garums ≥2 500 zīmes). Vecā forma joprojām derīga, lai vecu pārskatu UPSERT nesalūzt.
3. `src/render/blog.py` `_brief_preview`: weekly priekšskats ņem pirmā stāsta pirmo rindkopu, ja «## Nedēļas stāsts» nav.
4. `src/lv_style.py`: 7. likums `analytic-filler-iezime` (prozā, izlaižot «…» citātus un context-box); `RULES_TOTAL = 7`.
5. `.claude/agents/weekly-brief-writer.md`: pārrakstīts § SAGLABĀ/PAPILDINI/Valoda jaunajai formai.
6. `.claude/agents/quality-reviewer.md` § H: strukturālie noteikumi no 3. daļas weekly pārskatam.
7. `wiki/operations/weekly-routine.md`: pirmdienas rīts; jaunā struktūra īsi; atsauce uz šo dizainu.

## 5. Testi

- **E2E (viens):** testa DB ar iestādītu frakciju šķelšanos un tēmas lēcienu → `generate_weekly_brief()` skeletā abi ir kandidātos; aizpildīts paraugs iziet `store_context_note(note_type='weekly_brief')` un renderējas ar priekšskatu un WEEKLY_STATS kartītēm.
- **Unit:** `topic_surge` slieksnis (7 vs 8 pozīcijas, ×1,9 vs ×2, tēma bez vēstures).
- **Lint:** 7. likums nokrīt uz īsta vecā teikuma («Stendzenieks (LPV) iezīmē selektīvu darbaspēka imigrāciju») un nenokrīt, ja tas pats vārds ir citātā. Pierāda ar mutāciju (likums izslēgts → tests krīt).
- Esošie `tests/test_*weekly*` un `test_no_inline_js.py` paliek zaļi.

## 6. Ārpus tvēruma

- Vecu pārskatu pārrakstīšana.
- Nedēļas pārskata automātiska publicēšana (publicēšanas pauze paliek).
- `/deep-check` nedēļas pretrunu medību maiņa.

## 7. Pirmais palaidiens

Pirmais jaunās formas pārskats: nedēļa, kas sākas pēc ieviešanas. Ja ieviešana pabeigta līdz pirmdienai, var mēģināt 2026-10-26…11-01 kā pilotu ar operatora atļauju pirms publicēšanas. Pilotā mēra aģenta tokenus pret 2026-10-11 pārskatu.
