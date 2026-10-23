# claim-extractor — sloti un runātāji

Lasi, ja slots nav parasts politiķis (`relationship_type` ∈ `journalist` / `organization` / `neutral`, vai `feed_type='relay'`) vai ja tekstā runā kāds cits politiķa vietā. Kodols: `.claude/agents/claim-extractor.md`.

Vispārīgais tests: **iestādes slots atbild uz «vai iestāde to saka?», personas slots — uz «vai šī persona to saka?».** Viens dokuments var būt tukšs vienam slotam un derīgs otram.

## Slotu tipi

| `relationship_type` | `feed_type` | Piemēri | Ko sagaidīt |
|---|---|---|---|
| `journalist` | `relay` | visi 7 žurnālistu ieraksti (Lapsa, Madžiņš, Ozols, Kasems, K. Kļaviņš, Tetarenko-Supe, Iļjinska) | Atklāšanas kanāls, ne pozīciju avots: slota pasei noklusējums `empty_doc_ids`. Text-scan piesaista politiķus, ko viņi citē |
| `organization` | `relay` | LETA, TV3 Ziņas, IR žurnāls, Saeimas ziņas | ~95–99 % tukši: ziņu virsraksti un RT |
| `organization` | `first_party` | NBS, LVM, LDDK | Tikai nostāja, ko pauž pati iestāde (reti) |
| `neutral` | dažādi | Rajevskis, G. Vītols, Slaidiņš | Kā parasts politiķis — lēmums par katru dokumentu |

- Tabulai netici — pārbaudi: `SELECT tp.relationship_type, sa.feed_type, COUNT(*) FROM social_accounts sa JOIN tracked_politicians tp ON tp.id=sa.opponent_id GROUP BY 1,2`.
- `journalist` = `relay` kopš 2026-08-21 (CLAUDE.md inv #11). Šaurs izņēmums: dokuments IR paša žurnālista parakstīts viedokļraksts — tad lemj kā parasti. Sveša cilvēka vārdi, kas izplatīti caur žurnālista kontu, pieder tam cilvēkam, ne žurnālistam.
- Stratēģi, analītiķi un žurnālisti-kandidāti ar first_party ir `neutral`, ne `journalist`. Ja sastop `journalist|first_party`, tas ir jauns operatora lēmums — izlasi `wiki/operations/seeding.md` § Žurnālisti un nepieņem ne vienā, ne otrā virzienā.
- Relay konts pats nekad nav runātājs, arī ja junction ir `role='subject'`.
- Uzvārda sadursme relay dokumentā (sporta ziņa par vārdabrāli) → `empty_doc_ids` un piezīme reasoning; `negative_patterns` nelabo (operatora lēmums).
- Relay doki zem 12 dokumentu robežas var palikt rindā ilgi — tā ir zināma uzvedība, ne kļūda.

## Iestāde pret amatpersonu

- **Amatpersona runā iestādes vārdā** (departamenta vadītājs par sava departamenta darbu) = iestādes balss, ekstraktē.
- **Virsnieks vai darbinieks kā neatkarīgs eksperts** (militārais komentētājs raidījumā) iestādes slotā = `empty_doc_ids`. Ja ekspertam ir SAVS slots, tur tā pati runa IR pozīcija.
- **Iestādes vērtējums, iebildums vai ieteikums** (arī ierāmējumā «būtiski, ka kārtība kļuvusi vienkāršāka») = pozīcija.
- **Operatīvs paziņojums** (kas, kur, cik izdarīts; mācību norise, dalībnieki, vieta) bez vērtējuma = `empty_doc_ids`. Ja tajā pašā dokumentā ir arī vērtējums vai apņemšanās — ekstraktē to.
- Pārbaudi, vai runātājs vispār ir šī iestāde (cita iestāde tajā pašā reportāžā ir sveša balss).
- **Datu izteikums analītiķa slotā** («norāda, ka [skaitlis / salīdzinājums]») IR pozīcija — tas, kurus skaitļus persona izvēlas publiskot, ir nostāja. `NEEDS_REVIEW` tikai tāpēc, ka nav rīcības priekšlikuma, neliec.

## Biroja balss nav amatpersonas balss

Ja izteikumu pauž parlamentārais sekretārs, padomnieks, preses sekretārs vai preses dienests — gan savā vārdā, gan nododot amatpersonas viedokli («Kulbergs uzskata…, atzina padomniece») —, tā **nav** amatpersonas pozīcija: `empty_doc_ids` ar iemeslu. Izņēmums: ja tā pati nostāja ±5 dienu logā ir amatpersonas pašas vārdos (tvīts, tiešs citāts), glabā TO avotu.

**Žurnālista pārstāsts ir cita lieta.** Ja politiķis runāja publiski (TV, intervija, Saeima) un žurnālists to pārstāsta, tā ir parasta ekstrakcija. Jautājums: vai amatpersona pati kaut kur runāja?

`speaker_id` šeit nav risinājums: commentary ceļš ir slēgts kopš 2026-04-25.

## Komentētāji (commentary ceļš slēgts 2026-04-25)

Bijušie komentētāji ir `inactive` + `relay`. Ja izsekots politiķis ir `subject` komentētāja tvītā, tā ir trešās personas kritika, ne viņa pozīcija: `empty_doc_ids`. Jaunas `claim_type='commentary'` rindas neveido.

## Citi runātāja gadījumi

- **RT, kurā cits konts citē pašu politiķi** (`RT @ltvzinas: Vārds Uzvārds: «…»`): saturs var būt īsts, bet dokuments nav viņa paša publikācija. `empty` vai glabā ar `NEEDS_REVIEW:` — nekad kā tīru first-party pozīciju.
- **Daudzrunātāju raksts:** ekstraktē tikai sava politiķa bloku. Paneļdiskusijā «kāpēc mums nē?» var būt auditorijas motīva piesaukums, ne paša nostāja — pārbaudi, vai tas pats runātājs vēlāk neiebilst.
- **Svinīgs pasākums:** apsveikums bez jauna instrumenta = rituāls (`empty`), arī prezidentam un premjeram — pozīciju nosaka izteikums, ne runātāja rangs. Runa svinīgā sēdē ar saturisku normatīvu apgalvojumu = pozīcija ar zemāku confidence. Tests: izņem svētku ierāmējumu — vai paliek apgalvojums, ar ko var nepiekrist?
- **Simulācijas spēle / lomu spēle** («X stunda», izdomāta pilsēta, «ko jūs darītu, ja…» ar izdomātiem faktiem) = `empty_doc_ids` («simulācijas spēle»). Arī vispārīgs princips, kas izskan spēlē, paliek spēles kontekstā. Glabā tikai tad, ja tā pati nostāja ±5 d ir izteikta ārpus spēles, un tad TO avotu.
- **Satīra:** satīriķa pastāvīgais paņēmiens (piem., Stendzenieka «viņš piebilda») ir paša satīriķa autorība. Izdomāts «citāts» īstam politiķim satīras kontā nav tā politiķa pozīcija.
- **Politiķi tikai piemin vai par viņu runā citi** (divi citi politiķi debatē par viņu) → `empty_doc_ids`. Runātāju nosaki pats, ne pēc `subject` saites.
