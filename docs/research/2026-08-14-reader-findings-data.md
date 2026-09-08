# Lasītājam derīgi atradumi datos — 2026-08-14

> **IEKŠĒJS MELNRAKSTS — nepublicēt kā ir.** Galvenās sesijas QA labojumi: (1) frakciju atturēšanās likmes ir derīgas, bet tās nedrīkst pārvērst par vienu “koalīcija pret opozīciju” stāstu visam 2022–2026 periodam, jo koalīciju sastāvs mainās; (2) “gumijas zīmogs” nav datos pierādīts un ir izņemts no virsraksta; (3) KNAB atradums #8 ir pārvērtēts pret aktuālo API, likumu un reklāmas pārredzamības paziņojumiem — tas ir pilnībā atmaksāts mantisks labums, nevis €316 tūkst. naudas ziedojums.

_Metodika: read-only izpēte pret `data/atmina.db` (SQLite, `mode=ro`), veikta ar `E:\atmina\.venv\Scripts\python.exe`. Nekas nav rakstīts, neviens fails netika mainīts (izņemot šo atskaiti). Katrs atradums — ar precīzu vaicājumu, saucēju un avota rindām. Pretrunu atradumiem atvērtas un izlasītas abas avota rindas (claims + balsu rindas), ne tikai skaitītas._

_Konvencijas: "pozīcijas" = `claims.claim_type='position'`; "Saeimas balsojumi" = `saeima_votes`/`saeima_individual_votes`; laiki LV. Aktīvais politiķu kopums šeit = `relationship_type IN ('tracked','neutral')` → **172 personas** (167 tracked + 5 neutral); žurnālisti/organizācijas izslēgti, ja nav teikts citādi._

---

## Publicējami tagad (sarindoti pēc redakcionālās vērtības)

### 1. Frakciju atturēšanās stili krasi atšķiras

**Atradums.** 14. Saeimas būtisko balsojumu datos (2022–2026) frakciju paradumi krasi atšķiras: ZZS 17.1 %, JV 14.7 %, PRO 12.7 % — pret LPV 0.4 % un Stabilitātei! 0.0 % (53 624 balsis, neviena "Atturas"). Šo četru gadu agregātu nedrīkst nosaukt par stabilu “koalīcijas pret opozīciju” dalījumu, jo valdības un koalīciju sastāvs periodā mainās. ZZS biežāk atturas (17.1 %) nekā balso pret (14.4 %). Kopumā atturēšanās = 9.8 % no visām nodotajām balsīm (59 648 no 607 555), un 2 777 no 7 837 balsojumiem (35.4 %) satur vismaz vienu atturēšanos.

Lasītājam tas nozīmē: "atturējās" Saeimas protokolos bieži ir apzināts lēmums, nevis neitrālitāte — atbilstoši atmina darba konvencijai (atturēšanās liedz vairākumu tāpat kā balsojums pret).

**Konkrēts piemērs (pārbaudīts).** Balsojums **6778** (2026-06-04, "Par priekšlikumu Nr.34. Grozījumi Bāriņtiesu likumā (1031/Lp14), 2.lasījums"): 13:13:50:10, **Noraidīts**. No 50 atturēšanās 37 nāk no koalīcijas frakcijām (JV 21, ZZS 9, PRO 7); vienīgā frakcija, kas balsoja Par, bija NA (9). Bāriņtiesu reformas priekšlikums nomira, koalīcijai atturoties.

**Vaicājums (substantīvie balsojumi, `document_nr` nav tukšs):**
```sql
SELECT v.faction,
  ROUND(100.0*SUM(CASE WHEN v.vote='Atturas' THEN 1 ELSE 0 END)/COUNT(*),1) pct_atturas,
  ROUND(100.0*SUM(CASE WHEN v.vote='Pret' THEN 1 ELSE 0 END)/COUNT(*),1) pct_pret,
  COUNT(*) n
FROM saeima_individual_votes v
JOIN saeima_votes sv ON sv.id=v.vote_id
WHERE v.faction IS NOT NULL AND v.vote IN ('Par','Pret','Atturas','Nebalsoja')
  AND sv.document_nr IS NOT NULL AND sv.document_nr!=''
GROUP BY v.faction HAVING COUNT(*)>3000 ORDER BY pct_atturas DESC;
-- ZZS 17.1/14.4/101267 · JV 14.7/22.8/166184 · PRO 12.7/19.7/58845 ·
-- AS 4.9/14.2/80528 · NA 3.5/15.1/70104 · LPV 0.4/14.9/49723 ·
-- ST+ST! 0.0/26.5/53624
```
Per-balsojuma detaļa: `SELECT faction, vote, COUNT(*) FROM saeima_individual_votes WHERE vote_id=6778 GROUP BY faction, vote;`

**Saucējs:** visas 14. Saeimas substantīvās balsis pa frakcijām (ar `document_nr`); ST + ST! etiķetes apvienotas (vēsturiski divi apzīmējumi vienai frakcijai). Frakcija lasāma no balsu rindas, nevis no `party` (CLAUDE.md T6 korolārs).

**Riski/piezīmes:** (a) tas ir **agregāts fakts par frakciju uzvedību**, nevis apgalvojums par jebkura konkrēta balsojuma motiviem — atsevišķas atturēšanās var būt interešu konflikta normas vai procedūras sekas (sk. "Nepublicēt" §5); (b) nevis "koalīcija atturas pret visu" — JV 22.8 % gadījumu balso Pret; (c) `Nebalsoja` ieskaitīts saucējā, nevis atturēšanās skaitītājā.

---

### 2. Saeima noraida 5 no 6 priekšlikumiem, kamēr pārējos balsojumos pieņemšanas īpatsvars ir daudz lielāks

**Atradums.** No 2 459 priekšlikumu (amendment) balsojumiem (motifs "Par priekšlikumu%") pieņemti tikai **396 jeb 16.1 %**; lasījumu/pārējo balsojumu pieņemšanas rādītājs ir **80.5 %** (4 080 no 5 070). Vienprātīgi (0 pret, 0 atturas) ir tikai 3.3 % priekšlikumu balsojumu, bet 46.7 % pārējo. Tātad: priekšlikumi mirst teju vienmēr, un tieši tur notiek īstās sadursmes — vienprātības tur gandrīz nav.

**Konkrēts piemērs (pārbaudīts).** Tuvākais balsojums 2026. gadā: balsojums **5910** (2026-06-18, "Par priekšlikumu Nr.1. Par Enerģētiskās drošības un neatkarības veicināšanu…") — **37:37:1:6, Noraidīts**; ZZS frakcija sadalījās 7 Par / 3 Pret (un 2 Nebalsoja).

**Vaicājums:**
```sql
SELECT CASE
  WHEN motif LIKE 'Par priekšlikumu%' THEN 'amendment'
  WHEN motif LIKE '%nodošanu%' OR motif LIKE '%darba kārtībā%' OR motif LIKE '%steidzamīb%' THEN 'procedural'
  ELSE 'reading/other' END kind,
  COUNT(*), SUM(CASE WHEN result='Pieņemts' THEN 1 ELSE 0 END) passed,
  SUM(CASE WHEN total_pret=0 AND total_atturas=0 AND total_par>0 THEN 1 ELSE 0 END) unanimous
FROM saeima_votes GROUP BY kind;
-- amendment: 2459 / 396 pieņemti (16.1 %) / 81 vienprātīgi (3.3 %)
-- reading/other: 5070 / 4080 (80.5 %) / 2369 (46.7 %)
-- procedural: 308 / 125 / 26
```
**Saucējs:** visas 7 837 Saeimas balsis 2022–2026. Motifu klasifikācija pēc titania formulējuma; 2 459 ir "Par priekšlikumu%" apakškopa no tām.

**Riski/piezīmes:** priekšlikumu nāve pati par sevi nav nekas slikts — daudzi priekšlikumi ir tehniski vai atkārtoti; jāizvairās no "Saeima bloķē visu" naratīva. Skaitļi ir agregāti; konkrētais piemērs jāpārbauda pret balsu sarakstu pirms publicēšanas (šeit — izdarīts).

---

### 3. 43 no 172 aktīvajiem politiķiem — nulles ziņu mediju pārklājums; 18 sēdoši Saeimas deputāti bez vienas pozīcijas (arī X)

**Atradums.** Ziņu medijos (platforma `web`: LSM, Delfi, LETA, NRA, TVNet, LA, Diena, Jauns u.c.) **43 no 172** aktīvajiem politiķiem nav nevienas pozīcijas. Vēl dramatiskāk: **23 no 172** nav nevienas pozīcijas vispār — ne medijos, ne X — un no tiem **18 ir sēdoši Saeimas deputāti**: visa Stabilitātei! grupa (Drelinga, Ivanovs, Kļaviņa, Kovaļenko, Marčenko-Jodko, Sruoģis), ZZS (Daudze, Kozlovska, Vucāns), JV (Felss, Kalniņa, Zariņš), NA (Grasbergs), LPV (R. Šlesers, Stobova), AS (Lizbovskis). Turpretī Kulbergam ir 413 pozīcijas (180 ziņu medijos vien).

Asimetrijas ilustrācija: **Jānis Skrastiņš** (JV, Aizsardzības komisijas sekretārs) — 0 pozīciju, bet **1 230 atturēšanās** balsīs (17.8 % no viņa 6 927 balsīm) — "neredzamais atturētājs". Un **Guntars Vītols** (Finanšu ministra biroja ekonomists, nevis ministrs) ar 158 pozīcijām apsteidz lielāko daļu ministru — viņa pozīcijas pārbaudītas: tās ir viņa X konta (@guntarsv) ieraksti, atribūcija korekta.

**Vaicājumi:**
```sql
-- nulles pozīcijas vispār:
SELECT p.name, p.party, p.role FROM tracked_politicians p
LEFT JOIN claims c ON c.opponent_id=p.id AND c.claim_type='position'
WHERE p.relationship_type IN ('tracked','neutral')
GROUP BY p.id HAVING COUNT(c.id)=0;              -- 23 (18 sēdoši deputāti)
-- nulles ziņu mediju pozīcijas:
SELECT p.name, p.party, p.role FROM tracked_politicians p
LEFT JOIN claims c ON c.opponent_id=p.id AND c.claim_type='position'
LEFT JOIN documents d ON d.id=c.document_id AND d.platform='web'
WHERE p.relationship_type IN ('tracked','neutral')
GROUP BY p.id HAVING COUNT(d.id)=0;              -- 43 (24 deputāti/komisiju vadītāji)
-- Skrastiņš:
SELECT p.name, COUNT(*), SUM(CASE WHEN v.vote='Atturas' THEN 1 ELSE 0 END)
FROM saeima_individual_votes v JOIN tracked_politicians p ON p.id=v.politician_id
WHERE v.vote IN ('Par','Pret','Atturas','Nebalsoja') GROUP BY v.politician_id
HAVING COUNT(*)>3000 ORDER BY 3 DESC LIMIT 15;   -- Skrastiņš 6927 balsis / 1230 atturas
```

**Saucējs:** 172 (tracked+neutral). Piezīme par definīcijām: wiki indeksa "34/194 bez neviena media claim" lieto citu saucēju (194) un citu definīciju — skaitļi nav savstarpēji aizvietojami; publicējot jānorāda, ko mēra.

**Riski/piezīmes:** (a) pārklājums atspoguļo arī atmina avotu sarakstu, ne tikai realitāti — "nav datu" nav gluži "mediji viņus ignorē", lai gan sēdošu deputātu nulles pārklājums visos 11 medijos + X ir spēcīgs signāls; (b) daļa no 43 ir ārpus Saeimas (MMN kandidāti, EP deputāts Kols); (c) Vītola gadījumā precizēt, ka runa par X retoriku, ne mediju citēšanu.

---

### 4. Armaņeva: aizstāv brīvprātīgu 2. pensiju līmeņa izņemšanu — balsojumā bloķē pilsoņu kolektīvo iesniegumu ar to pašu prasību (tieša pretruna, pārbaudīta līdz balsij)

**Atradums.** Maija Armaņeva (LPV) 2026. gada 18. februārī X raksta: "Pat pilnībā izņemot 2. pensiju līmeni, cilvēks nepaliek bez vecuma pensijas" (#465), 2. martā paziņo, ka LPV iesniegusi likumprojektu par brīvprātīgu 2. pensiju līmeņa kapitāla izņemšanu (#466). 1. aprīlī Saeimā balsojumā **14** ("Par 11 391 Latvijas pilsoņa kolektīvā iesnieguma 'Nodrošināt iespēju brīvprātīgi izņemt 2. pensiju līmeņa uzkrāto kapitālu' turpmāko virzību (936/Lm14)") viņas balsis ir **Pret** — balsu rinda pārbaudīta: `Armaņeva / LPV / Pret`. Pret to pašu prasību, ko viņa pati aizstāvēja, vēl 11 391 pilsoņa paraksti.

**Avoti:** claims #465 (https://x.com/maija_armaneva/status/2024160264942207278), #466 (https://x.com/maija_armaneva/status/2028475136580444376), #502497 (https://titania.saeima.lv/LIVS14/SaeimaLIVS2_DK.nsf/0/8E329BC923CFED88C2258DCD000AFBC7?OpenDocument); pretrunu rinda: contradictions id=10 (`direct_contradiction`, confirmed=1, reviewed=1). Pārī ar pretrunu id=11 (otrais kolektīvais iesniegums, 10 946 paraksti, #502501).

**Vaicājums:** `SELECT * FROM claims WHERE id IN (465,466,502497,502501);` + balsu pārbaude pa `saeima_votes.url LIKE '%8E329BC9…%'` → vote_id=14 → `saeima_individual_votes`.

**Riski/piezīmes:** kolektīvā iesnieguma balsojums ir "turpmākā virzība" — procedūras balsojums; T14 noteikums prasa izlasīt balsojumu ķēdi. Šeit motīvs ir tieši iesnieguma turpmākā virzība, un LPV pašas iesniegtais likumprojekts ir tas pats saturs — pretruna ir tēmas līmenī, nevis tikai procedūras. Vēlams atsauce arī uz otru iesniegumu (#502501, 10 946 paraksti).

---

### 5. Kulbergs: no "iesaldēt Rail Baltica" līdz "jāfinansē kā militārās mobilitātes projekts" un no "amati bez konkursa — kauns" līdz likuma grozījumiem, kas ļauj iecelt bez konkursa

**Atradums.** Divas pārbaudītas apvērsuma pretrunas vienā politiskajā lokā (opozīcija → premjers):

- **Rail Baltica (#41, reversal, confirmed=1):** X ieraksts 2025-02-24: "#RailBaltica ir jāiesaldē. Ja 🇪🇺 EK ir jāatmaksā 100 mio €, tas ir lētāk, kā grūst RB iekšā vēl simtus mio €" (#532289) → NRA intervija 2026-06-09 (jau premjera amatā): "Šis projekts tagad ir ārkārtīgi svarīgs, īpaši, ja domājam par militāro mobilitāti…" (#527773).
- **Amati bez konkursa (#42, minor_shift→faktiski apvērsums, confirmed=1):** X 2026-03-21 izsmej Progresīvos, ka "klusi bez konkursa pagarina amatu" (#229) → X 2026-06-11: "Steidamas izmaiņas civildienesta likumā nodotas Saeimā, lai tiktu atcelta sen ieveista kļūda…" — iniciatīva atcelt normu, kas liedza Valsts kancelejas vadītāju iecelt pirms konkursa (#527887). (Citātā "Steidamas" ir politiķa paša kļūda — verbatim, nelabot.)

**Avoti:** #532289 (https://x.com/AndrisKulbergs/status/1894144849558860043), #527773 (https://nra.lv/baltija/igaunija/523076-…), #229 (https://x.com/AndrisKulbergs/status/2035328802012701023), #527887 (https://x.com/AndrisKulbergs/status/2065118053889679481); contradictions id=41, id=42.

**Riski/piezīmes:** konteksts mainās kopā ar amatu — opozīcijas kritika pret valdības praksi un premjera rīcība nav formāli identiskas situācijas; #42 mērķis atšķiras (kapitālsabiedrību padomes vs Valsts kanceleja). Precīzs formulējums: "opozīcijā nosodīja, premjera amatā pats iniciēja" — nevis "melojis". Rail Baltica gadījumā vērts pieminēt arī #37 (2026-05-25 "apzināta sabotāža" naratīvs, jauns.lv) kā starpposmu.

---

### 6. Šlesers: "nepretendēšu uz premjeru" (2021) → "esmu gatavs būt premjers" (2026); "man nav plānu kandidēt Saeimas vēlēšanās" (2025) → "balsot par premjeru Šleseru" (2026)

**Atradums.** Divas pārbaudītas apvērsuma pretrunas:

- **#39 (reversal, confirmed=1):** TVNET 2021-03-25: "Startējot vēlēšanās, Šlesers piedāvāšot pilnu Ministru kabineta sastāvu… pats nepretendētu uz premjera amatu" (#527756) → X 2026-05-11: "Aicinu Valsts prezidentu izteikt premjerei Siliņai neuzticību! … Esmu gatavs kļūt par jaunās valdības premjeru!" (#18125).
- **#45 (reversal, confirmed=1):** LSM 2025-06-07 (pašvaldību vēlēšanu vakars): "Man nav plānu kandidēt Saeimas vēlēšanās." (#548401) → X 2026-07-02: "3.oktobrī Saeimas Vēlēšanās Latvijas tautai būs izvēle balsot vai nu par esošo valdības premjeru Kulbergu, vai arī premjeru Šleseru…" (#532749).

**Avoti:** #527756 (https://www.tvnet.lv/7210228/slesers-apnemies-startet-nakamajas-saeimas-velesanas), #18125 (https://x.com/SlesersAinars/status/2053734795658596687), #548401 (https://www.lsm.lv/raksts/zinas/latvija/07.06.2025-…), #532749 (https://x.com/SlesersAinars/status/2072758982469705798); contradictions id=39, id=45.

**Riski/piezīmes:** politikā viedokļa maiņa laika gaitā ir normāla; vērtība ir laika loku pāru salikšanā un verbatim citātos. "Nepretendēšu uz premjeru" (2021) jālasa kopā ar 2021. gada kontekstu (tobrīd virzība uz satiksmes ministra amatu). Nekādu juridisku vai morālu spriedumu — fakti + citāti.

---

### 7. airBaltic — 2026. gada dominējošā politiskā tēma: viena aviokompānija pārspēj Rail Baltica un pensijas kopā

**Atradums.** Tēmā "airBaltic" ir **194 pozīcijas** — vairāk nekā "Rail Baltica" (104), "Pensijas" (72), "Klimats" (17) un "Sports" (17) kopā; salīdzinājumam visas "Veselības aprūpe" = 94. Aprīlī 2026 — krīzes mēnesī — 118 pozīcijas vienā mēnesī (no 2 2025. gada janvārī). Aktīvākie: Kulbergs 19, Vītols 18, Švinka 18, Šlesers 14, Siliņa 14.

**Vaicājums:**
```sql
SELECT topic, COUNT(*) FROM claims WHERE claim_type='position' GROUP BY topic ORDER BY 2 DESC;
SELECT substr(stated_at,1,7) m, COUNT(*) FROM claims
WHERE topic='airBaltic' AND claim_type='position' AND stated_at>='2025-01-01' GROUP BY m ORDER BY m;
```

**Riski/piezīmes:** tēmu skaits ir atmina kanonisko tēmu klasifikācijas produkts un ietver gan X, gan medijus; "dominē dienaskārtību" jāformulē kā korpusa fakts ("mūsu datos"), ne absolūta patiesība par valsti. Aprīļa smaile sakrīt ar airBaltic krīzi — vēlams atsaukties uz pretrunu #24/#28 kontekstu.

---

### 8. Biedrības apmaksāta LPV reklāma: +€340 654 mantisks labums, pēc tam pilnībā atmaksāts līdz nullei

**Pārbaudītais atradums.** Aktuālais KNAB avots 2026-05-07 uzrāda Biedrības “LATVIJA PIRMĀ” mantas vai pakalpojuma veida labumu LPV **€316 309,12** apmērā. Kopā ar vēl divām pozitīvām mantas/pakalpojuma rindām summa ir **€340 654,32**, bet 21 negatīva naudas rinda līdz 2026-07-18 to precīzi samazina līdz **€0,00**. Pēdējā atmaksa ir 72 dienas pēc pirmā ieraksta; likums paredz 75 dienu logu ziedojuma atdošanai pirms tas uzskatāms par pieņemtu.

JCDecaux pārredzamības paziņojums LPV norāda kā reklāmas sponsoru, bet biedrību kā maksātāju; SKONTO TEV biedrību norāda gan kā sponsoru, gan maksātāju. Drošais stāsts ir par lielu priekšvēlēšanu reklāmas labumu, kuru partija pilnībā neitralizēja ar atmaksām — nevis par €316 tūkst. naudas ziedojumu vai pierādītu pārkāpumu.

**Atmina kļūda.** 2026-07-24 DB momentuzņēmums trīs pozitīvās rindas kļūdaini glabā kā `Nauda`; aktuālais KNAB API tās klasificē kā `Manta vai pakalpojums`. Četri `public_id` ir mainīti. Pašreizējais `INSERT OR IGNORE` atjaunināšanas modelis nākamajā pilnajā importā var šīs četras rindas dublēt un radīt viltus **+€330 654,32** neto.

**Pilna izpēte:** `docs/research/2026-08-14-knab-latvija-pirma-row.md`.

**Riski/piezīmes:** neapgalvot nelikumību, KNAB piespiedu lēmumu vai precīzu KNAB rindu sasaisti ar konkrētiem reklāmas rēķiniem bez KNAB skaidrojuma.

---

### 9. Indriksone: "valdība nesagāzīsies" (3. marts) → "valdībai jāatkāpjas" (11. maijs) — 69 dienas

**Atradums.** NA līdere Ilze Indriksone LSM intervijā 2026-03-03: "valdība spēs 'nesagāzties' un nostrādāt līdz termiņa beigām, tomēr nespēs pieņemt lielus un būtiskus lēmumus" (#18183) → 69 dienas vēlāk, 2026-05-11, X: "Valdībai ir jāatkāpjas. Esmu gatava veidot nacionālās drošības valdību. Mēs aicināsim uz sarunu AS, ZZS un JV…" (#18104). Pārbaudīta abās avota rindās; pretruna id=32 (`reversal`, confirmed=1).

**Riski/piezīmes:** starp datumiem notika Sprūda demisijas krīze (10.05) — tas nav "melīgums", bet reakcija uz notikumu; vērtība ir laika loka precizitātē. Jāraksta ar kontekstu, ne bez tā.

---

### 10. X ir galvenā politiskā skatuve: 68 % no visām pozīcijām nāk no X, nevis medijiem

**Atradums.** No 5 653 pozīcijām **3 840 (67.9 %)** nāk no X ierakstiem (`platform='twitter'`), 1 706 (30.2 %) no ziņu mediju lapām (`web`). Skaļākie konti pēc savāktā apjoma: Lato Lapsa 3 050 dokumenti (žurnālists), Ēriks Stendzenieks (LPV, Rīgas domes deputāts) 689 dokumenti ar **297 tūkst.** kopējiem retvītiem, Andris Velps (ASL) 519 dokumenti ar 309 tūkst. retvītu; no ministriem visvairāk — Baiba Braže (1 776 dokumenti, 171 tūkst. retvītu).

**Vaicājums:**
```sql
SELECT d.platform, COUNT(*) FROM claims c JOIN documents d ON d.id=c.document_id
WHERE c.claim_type='position' GROUP BY d.platform ORDER BY 2 DESC;
SELECT p.name, COUNT(DISTINCT d.id) n, SUM(COALESCE(d.retweet_count,0)) rt
FROM documents d JOIN document_politicians dp ON dp.document_id=d.id AND dp.role='subject'
JOIN tracked_politicians p ON p.id=dp.politician_id
WHERE d.platform IN ('twitter','x_mention') GROUP BY dp.politician_id ORDER BY n DESC LIMIT 12;
```

**Riski/piezīmes:** (a) sadalījums daļēji atspoguļo savākšanas dizainu (X plūsmas tiek vāktas blīvi) — tas ir korpusa fakts, ne "patiesība par Latvijas mediju vidi"; (b) retvītu summas ir neapstrādāti skaitītāji, botu/pirktās amplifikācijas risks (sk. "Nepublicēt" §4); (c) Lapsa ir žurnālists — jāmarķē kā tāds.

---

## Nepublicēt vēl (kārdinoši, bet nedroši)

1. **Partiju programmu solījumi pret balsojumiem** ("partija solīja X, balsoja pret X"). Infrastruktūra ir ieviesta (2026-08-06), bet **neviena partiju pretruna nav saglabāta un nav izgājusi `@devils-advocate`** — dry-run radīja 18 914 tēmu pārus, pēc T14/Pret/Atturas ekrāniem 1 807; satura sapārošanas lēmums ir atvērts (BACKLOG § Partiju pretrunas). SQL pāris "solījums ↔ balsojums" bez tā rada viltus pozitīvos rūpnieciski (koalīcijas disciplīna, procedūru ķēdes). Šis ir viskārdinošākais stāsts datu kopā — un visnedrošākais tagad.

2. **KNAB "limitu pārkāpumi" kā nelikumīgi ziedojumi.** Trīs `critical` brīdinājumi (`knab_alerts`): 2× `limit_violation` (abi 2002. gads, pārsniegums €571.80) un 1× `donation_declaration_mismatch` ("Centra Partija" 2019, €2 973.95 pret deklarētiem €680). Tie ir atmina algoritmiski atvasinājumi, ne KNAB lēmumi; turklāt "SIA VEF un Ko" un "Ļubova Hartmane" rindās ir identiska summa €35 571.80 — datu dīvainība, kas jāizmeklē pirms jebkā. "Pārsniedz limitu" ≠ "nelikumīgi" bez KNAB izvērtējuma.

3. **VAD deklarāciju salīdzinājumi ("bagātākie/taupīgākie politiķi").** Pārklājums daļējs: deklarācijas ir 144 no 223 personām, gadi pa personām atšķiras (Mūrniecei 31 gads, citiem mazāk); īpašuma statusi (`īpašumā`/`valdījumā`/`lietošanā`) nozīmē dažādas lietas; kopējo vērtību nav. Rangs būtu artefakts. Atsevišķas pārbaudītas deklarāciju rindas var stāstīt (piem., Švinkas Audi Q6 e-tron "lietošanā"), bet tikai pret `raw_html` pārbaudītas un bez salīdzinājumiem.

4. **X engagement = ietekme.** "Stendzenieks ir visietekmīgākais" no retvītu summas ir secinājums, ne fakts — botu un pirktas amplifikācijas iespēja nav izslēgta. Var publicēt tikai "mūsu datos šiem kontiem ir lielākās retvītu kopsummas".

5. **Atsevišķas atturēšanās kā politikas pozīcija.** Agregāts frakciju līmenī (atradums #1) ir publicējams; "ZZS ar atturēšanos nobalsoja pret X" par konkrētu balsojumu nav — T14 noteikums (balsojumu ķēde, procedūras konteksts, interešu konflikta normas, whip). Vienmēr jāizlasa visa balsojumu ķēde pa `document_nr`.

6. **Precīzi 7 dienu pozīciju skaitļi.** Wiki indeksā "Kulbergs 44" pēdējās 7 dienās; mans vaicājums ar 2026-08-07 griezumu dod 42. Atšķirība = loga/metodikas definīcija, ne datu kļūda — bet publicēt precīzu skaitli bez metodikas ir nedroši.

7. **Šajā piegājienā neatvērtās pretrunu rindas** (#27–#30, #36–#38, #40, #44, #46). Tās ir `confirmed=1, reviewed=1` (pipeline validētas), bet es tās šeit nepārbaudīju avota līmenī; īpaši jūtīgas ir Siliņas #29/#30 (formulējuma jutīgas, ar atrunām) — pirms publicēšanas operatora izlases pārbaude pret avotu. (#40 Judins un #47 Dombrava ir `confirmed=0` — pēdējā ir eksplicīti noraidīta pirms publicēšanas; neizmantot.)

---

## Verifikācijas kopsavilkums

- **Pārbaudītas avota līmenī (atvērtas rindas, ne tikai skaitītas):** pretrunas #10/#11 (Armaņeva — arī balsu rinda vote 14: `Armaņeva/LPV/Pret`), #39 un #45 (Šlesers), #41 un #42 (Kulbergs), #34 (Šuvajevs), #32 (Indriksone) — citāti un URL atbilst apkopojumiem; balsojumu piemēri 6778 un 5910 — pa frakcijām un balsīm; Vītola un Pūpola pozīciju atribūcija — paraugi atbilst X kontiem; LPV €316 309.12 ziedojums — KNAB publiskā atsauce.
- **Saucēji:** 172 aktīvās personas (tracked+neutral); 7 837 Saeimas balsis; 5 653 pozīcijas; 2 459 priekšlikumu balsojumi; 607 555 nodotās balsis; KNAB ziedojumu rindas ar `date>=2025-01-01`.
- **Zināmie ierobežojumi:** pozīciju platformu sadalījums atspoguļo savākšanas dizainu; mediju "neredzamība" nav gluži mediju ignorēšana; ST frakcijai divi etiķešu varianti apvienoti; `Nebalsoja` ieskaitīta balsu saucējā.
