# Saeimas balsojumu tēmas — dizains

**Datums:** 2026-10-21 · **Plāns:** `docs/superpowers/plans/2026-10-21-saeimas-balsojumu-temas.md`
**Izpētes avoti:** Claude sesija 2026-10-21 + GPT-6-Astra neatkarīga recenzija + advisor. Katram skaitlim zemāk ir vaicājums, kas to deva (dzīvā DB, tikai lasīšana, 2026-10-21).

## Problēma (ar pierādījumiem)

Balsojuma tēmu šodien izvēlas pirmais atslēgvārds balsojuma virsrakstā (`src/saeima/claims.py::_motif_to_topic` → `_MOTIF_TOPIC_MAP` → `src/topic_map.py::normalize_topic` → `_SAEIMA_KEYWORD_MAP` → noklusējums «Valsts pārvalde»). Tēma glabājas `saeima_votes.topic` (8 407 rindas) un tiek kopēta uz `claims.topic` visiem `saeima_vote` ierakstiem (685 769 rindas; neatbilstību starp abām tabulām šodien ir 0, savienojums `claims.source_url = saeima_votes.url`).

1. **«Valsts pārvalde» ir atkritumu kaste.** Tajā ir 2 627 balsojumi; bez klātbūtnes reģistrācijas — 2 056. Tur nonāk, piemēram, Tiesībsarga likums, Notariāta likums, pilsonības piešķiršana un partiju finansēšana. *Vaicājums:* `SELECT count(*) FROM saeima_votes WHERE topic='Valsts pārvalde' AND motif NOT LIKE 'Deputātu klātbūtnes%'`.
2. **Komisiju nosaukumi nosaka tēmu.** 18 no 142 «Vide» balsojumiem ir deputātu ievēlēšana vai atsaukšana «Tautsaimniecības, agrārās, vides un reģionālās politikas komisijā».
3. **Vārda sākums ≠ vārds.** «dabas» atrod «dabasgāze»: Skultes sašķidrinātās dabasgāzes termināļa likums ir «Vide», nevis «Degviela un enerģētika».
4. **Saglabātā tēma jau atšķiras no tā, ko kods dod šodien.** 239 no 8 407 balsojumiem `_motif_to_topic(motif) != topic` (2026-10-14 komisijas teikuma izgriešana nekad netika piemērota vecajām rindām).
5. **Latenta dublikātu kļūda.** `generate_claims_from_votes()` tēmu nelasa no DB, bet pārrēķina no virsraksta (`src/saeima/votes.py:815`), kamēr `store_vote()` jau saglabātam balsojumam atgriež veco id (`:501–508`) un ieraksti tiek ģenerēti vienalga (`:965–967`). Ja tēma mainās, `store_claim()` idempotences atslēga `(opponent_id, source_url, topic)` vairs nesakrīt → atkārtota ielāde ievieto **otru** ierakstu katram politiķim (T2). Šodien dublikātu nav (`max` ierakstu uz `(source_url, opponent_id)` = 1), bet jebkura pārklasifikācija bez šī labojuma tos radītu.
6. **Kāpēc tas ir svarīgi ne tikai filtriem.** `src/party_contradictions.py:139` atlasa balsojumus partijas solījumam pēc `c.topic = ?`; nepareiza tēma = pazaudēts īsts atradums. Tēmu lieto arī `src/render/votes.py`, `votes_matrix.py` (filtri), `src/render/laws.py:149–158` (no `saeima_bills.topic`).

## Dati, uz kuriem balstāmies

- `document_nr`: 7 592 no 8 407 balsojumiem; 2 583 dažādi. Formāti: `NNN/Lp14` likumprojekti (1 491), `NNN/Lm14` Saeimas lēmumi (951 — personāls, tiesneši, rezolūcijas), `NNN/P14` pieprasījumi (118). Bez numura: galvenokārt klātbūtnes reģistrācija un sēdes procedūra.
- Vidēji 2,9 balsojumi uz dokumentu, maksimums 253.
- `saeima_votes.summary` ir visām 8 407 rindām, bet garās ķēdēs tas bieži atkārto likumprojekta kopsavilkumu (`1130/Lp14`: 195 balsojumi, 3 dažādi kopsavilkumi).
- `saeima_bills`: 555 rindas, 206 ar tēmu; `bill_id` ir tikai 1 581 balsojumam. 27 balsojumiem `document_nr` atšķiras no piesaistītā likumprojekta numura (piem. `1179` pret `1179/Lp14`).
- 11 dokumentu ķēdēs ir vairākas tēmas, un ne visas ir kļūdas: `1286/Lp14` (Ceļu satiksmes likums) balsojums 197 par apmācības valodu pareizi ir «Valodu politika».
- `saeima_agenda_items` ir tukša; `agenda_item_id` visiem NULL — komisijas vai darba kārtības punkta signāla nav.

## Lēmumi

1. **0. fāze ir koda labojums, ne datu migrācija.** `generate_claims_from_votes()` lasa tēmu no `saeima_votes.topic` (vai lēmumu tabulas), nekad nepārrēķina. Ar testu, kas pierāda: atkārtota ielāde pēc tēmas maiņas neievieto otru ierakstu. Neviena datu partija nesākas pirms šī labojuma.
2. **Tēmu izlemj dokumentam; balsojums to manto.** Atsevišķam balsojumam drīkst būt izņēmums (`override`), ja tā saturs skaidri ir cita tēma (1286/Lp14 #197). Vai izņēmumiem vajag atsevišķu kolonnu, izlemj zelta kopas mērījums: ja vote≠document ir dažos procentos, izņēmumi iet pārbaudes sarakstā, nevis shēmā. Sekundāras tēmas NAV; ierakstus nedublē.
3. **34. tēma «Saeimas darbs» — šaura.** Tikai parlamenta iekšējā kārtība: sēdes sākšana un slēgšana, darba kārtības izmaiņas, deputātu pārcelšana komisijās, Saeimas amatpersonu ievēlēšana. Tiesnešu apstiprināšana, rezolūcijas un pieprasījumi paliek savās politikas tēmās. Procedūras balsojums par likumprojektu (steidzamība, nodošana komisijai) pieder likuma tēmai; to, ka tas nav politikas nostāja (T14), joprojām nosaka motīvs balsojuma līmenī (`is_urgency_declaration`, `_vote_salience`, veto `party_contradictions.py:139–145`). Dokumenta lēmums ir tikai tēma — atsevišķa procedūras karoga nav. Klātbūtnes reģistrācija ierakstus nerada (4b), bet balsojuma rindai tēma «Saeimas darbs».
4. **Viens patiesības avots.** Jauna tabula `saeima_document_topics` — rindas tikai pievieno (vēsture paliek), aktuālā = jaunākā neatsauktā. Kolonnas: `document_nr` (normalizēts), `document_nr_raw`, `topic`, `method` (`keyword`/`jev`/`claude`/`human`), `model` (atrisinātais, ne `jev-latest`), `confidence`, `input_hash`, `rubric_version`, `review_status`, `decided_at`. `saeima_bills.topic` atvasina no tās pašas tabulas — otras klasifikācijas nav. Tēmu uz `saeima_votes`/`claims` raksta tikai viena funkcija `src/saeima/topics.py::apply_document_topic()`.
5. **Klasifikatoru izvēlas mērījums, ne priekšroka.** Salīdzina uz vienas zelta kopas ar vienādu ievadi:
   - A — pašreizējie atslēgvārdi (bāzlīnija; atsevišķi arī saglabātās tēmas, jo tās atšķiras 239 rindās);
   - B — Jev (TypeSafe `choice` jautājums ar 34 opcijām un aprakstiem; API atļauj 1–255. `src/jev_filter.py` prot tikai Noul — vajag `choice` adapteri ar `probabilities` un atrisināto modeli);
   - C — Claude Opus apakšaģents (`model: 'opus'`), partijās pa ~50 dokumentiem.
   Ievade visiem: dokumenta virsraksts + distinct `summary` + `saeima_bills.title/summary`, ja ir. Zelta kopas etiķetes, pašreizējās tēmas un strīdu lēmumi klasifikatoru promptos NEnonāk.
6. **Ielādē lieto uzvarētāju.** Jauns dokuments → klasifikators → ja pārliecība zem kalibrētā sliekšņa vai serviss nav pieejams, `review_status='pending'` un tēma no atslēgvārdiem ar žurnāla ierakstu (kluss kritums nav atļauts). Slieksni kalibrē uz pārbaudes daļas, katram klasifikatoram savu.

## Zelta kopa (0. partija)

- ~250 dokumentu: visi reto tēmu dokumenti, pārsvars pašreizējai «Valsts pārvalde» un «Vide», visi trīs prefiksi, 20 garās ķēdes (≥10 balsojumi) ar etiķeti balsojuma līmenī (mēra vote≠document), atsevišķa josla balsojumiem bez numura.
- Sadalījums izstrādes / pārbaudes kopā pēc bāzes likuma, lai viena likuma grozījumi nenonāk abās.
- Etiķetes liek Claude no avota teksta pēc rakstiskas rubrikas (`rubric_version`); otrs neatkarīgs marķētājs (cits modelis) uz 60 dokumentu apakškopas; nesakritības izšķir pret avotu. **T16:** katru rubrikas zaru (katru tēmu un «Saeimas darbs» robežu) pārbauda pret avota tekstu, nevis pret marķētāju sakritību.
- Atskaite: atbalsta skaits katrai tēmai, precizitāte dokumentu un balsojumu svarā, macro-F1, sajaukšanas matrica, atteikumu īpatsvars pie sliekšņa. Saucēji obligāti.
- Rezultāts un etiķetes: `data/saeima_topic_gold/` (CSV + rubrika), komitēts.

## Partijas un atsākšana

- **Partija** = iesaldēts `document_nr` saraksts (~300), sakārtots pēc ietekmes (vispirms «Valsts pārvalde», tad «Vide», tad pārējās). Tabula `vote_topic_batches`: `batch_id`, dalībnieki, `status` (`planned`/`classified`/`applied`/`rolled_back`), `applied_at`, atjaunošanas faila vārds.
- **Katra partija** vienā transakcijā: snapshot `(claim_id/vote_id, old_topic)` atsevišķā tabulā → sadursmju vaicājums uz `(opponent_id, source_url, topic)` → UPDATE ar aizsargu `WHERE topic = old_topic` → pirms/pēc sadalījums pa tēmām, izmainīto rindu skaits pret gaidīto, balsojuma/ieraksta tēmu paritāte. `data/rollback_vote_topics_<batch>.sql` atjauno no snapshot tabulas un tiek komitēts PIRMS apply (eskalācija 8). Balsojumu ierakstiem vektorus nepārrēķina.
- Atkārtota palaišana izlaiž `applied` partijas; partija, kas apstājās pusē, atritinās ar transakciju.
- Viena sesija = viena vai vairākas pilnas partijas; stāvoklis dzīvo DB, ne sesijas atmiņā.
- **Atkāpe no ierastā rollback veida:** partijas rollback fails NAV pašpietiekams — tas atjauno no `vote_topic_snapshot` (686k rindu SQL fails būtu nepareizā forma). Tāpēc snapshot rindas nekad nedzēš, un fails to pasaka galvenē.
- `saeima_bills.topic` sinhronizē katras partijas beigās, lai likumu un balsojumu lapas neatšķiras pārejas laikā.

## Ko pārbauda pēc katras partijas

- `party_contradictions.py` kandidātu skaits pirms/pēc (mainās — tas ir mērķis, bet skaitlim jābūt atskaitē).
- Balsojumu lapas filtru saraksts (`votes.py`, `votes_matrix.py`) — šaurs render `--only`.
- Likumu wiki lapas: ja tēma tajās parādās, bāzlīnijas REGEN ir plānots solis (`test_likumi_detail_pages_byte_identical`); wiki_sync failus ar roku nelabo.

## Ārpus šī darba

- Tēmu ikonas (atsevišķs BACKLOG ieraksts).
- `position` ierakstu tēmas — tās liek `@claim-extractor`, cits mehānisms.
- Vecā `_MOTIF_TOPIC_MAP` dzēšana — paliek kā rezerve, līdz uzvarētājs nostrādājis ielādē ≥2 nedēļas.

## Atvērtie operatora jautājumi

- Nav (34. tēma apstiprināta 2026-10-21). Testi, kas jāpielāgo: `tests/test_audit_topic_canonical.py:132` (`== 33`), `tests/test_topic_map.py`, `tests/test_csp_readpath.py`; teksts «33 canonical» CLAUDE.md un `src/render/{positions,topics,syntheses}.py`, `src/graphics/visual_map.py`.
