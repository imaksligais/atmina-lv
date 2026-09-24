# @claim-extractor

> Kanoniskais prompts (izpildei): [.claude/agents/claim-extractor.md](../../../.claude/agents/claim-extractor.md) — šī lapa ir īss apraksts cilvēkiem.

Neitrāla politisko pozīciju ekstrakcija no dokumentiem.

**Ko dara:** Lasa dokumentus (ziņas, tvītus, balsojumus) un izvelk konkrētas politiskās pozīcijas. "Es nevaru noteikt" ir derīgs rezultāts.

**Kad izmanto:** Dienas rutīnas solī pēc dokumentu ielādes (ingest).

**Ievade:** `get_politician_documents(pid)` + `get_existing_claims(pid)` pretrunu pārbaudei.

**Izvade:** `save_analysis()` ar claims sarakstu → DB `claims` tabula.

**Noteikumi:**
- sentiment vienmēr 0.0
- Tēmas no `src/topic_map.py` (33 kanoniskās grupas; `Sports` kopš 2026-07-04, `NVO un pilsoniskā sabiedrība` kopš 2026-08-06)
- Claims bez source_url tiek klusi izlaisti
- Pārbaudīt esošos claims lai neduplicējas
- Max 12 docs uz politiķi **vienā sweep** (circuit breaker dienas rutīnai — samazināts no 33 uz 2026-04-22 pēc batch-drift diagnostikas, kas parādīja, ka lielākā batch režīmā aģents saglabā pozīcijas dokumentiem, kurus izolēti atzīmē pareizi kā `empty`). Ja vairāk par 12 — pirmie 12 tagad, atlikušie **otrajā sweep** ar svaigu sub-aģentu (tīrs konteksts). 12 ir kvalitātes limits, nevis STOP; dokumentus izmest nedrīkst. Kanoniskais formulējums: `.claude/agents/claim-extractor.md` § Circuit breaker rules.
- **Neizlasītus dokumentus NEDRĪKST atzīmēt ar `empty_doc_ids`** — tas uzliek `reviewed_at`, un dokuments pazūd no rindas uz visiem laikiem bez pēdas, ka to neviens nav atvēris (T5 + T11). Trīs failu pretruna par šo salāgota 2026-08-02; līdz tam `rubrics.md` prasīja pretējo.
- **claim_type = `'position'`** (noklusējums) — ekstraktors strādā ar mediju/X dokumentiem, tātad pirmās personas retoriku. Nemainīt uz `'saeima_vote'`; tas ir rezervēts tikai `@saeima-tracker` izveidotajiem balsojumu ierakstiem. Ja `save_analysis(claims=[...])` dict satur `claim_type` atslēgu, tā tiek ievērota; parasti to var izlaist (default `'position'` ir pareizais).
- **claim_type = `'commentary'` + `speaker_id`** (2026-04-23, **DEPRECATED 2026-04-25**) — komentētāju demote 2026-04-25 noņēma šo ceļu. 7 vēsturiskie commentators (Heinrih5, Kurmitis_, Klucis, Tuksumsz, Svirskis, Lūsis, PStrautins) tagad `relationship_type='inactive'` + `social_accounts.feed_type='relay'`. To tvīti turpina ielādēties caur relay path; tracked politiķi, kas pieminēti viņu saturā, link kā `mentioned` vai `subject` caur text scan, un raw mentions nokļūst politiķa profila X subtabā (jauna 2026-04-25). **Atsevišķa commentary claim NETIEK ģenerēta**. Ja matcher pārprata commentator-autoru tvītu kā tracked politiķa subject, mark kā `empty_doc_ids` — tā ir trešās personas kritika, ne pirmpersonas pozīcija. Vēsturiskās commentary claims paliek DB kā audit trail. Sk. [CHANGELOG 2026-04-25 Commentator demotion](../../CHANGELOG.md#2026-04-25--commentator-demotion--profila-x-subtaba) un `.claude/agents/claim-extractor.md` Step 3b.

**Schema trap (2026-04-11 incidents):** tweetiem `documents.title` VIENMĒR ir NULL un nav `text` kolonnas — tweet saturs dzīvo `content` kolonnā. Prior sub-agent sessijā nepareiza schema lasīšana noveda pie 15 tweetu kļūdaini atzīmēšanas kā "empty" (un 4 reālu pozīciju zaudēšanas līdz re-run). Kad lemj vai tweet ir tukšs, lasi `content`, ne `title`.

**Indirect-reference gate (2026-04-22, `save_analysis`):** Ja `reasoning` satur frāzes kā `nav paša pozīcij / pašam nav ekstraktēj / bare retweet / pure retweet / does not speak / tikai pieminē`, `save_analysis` automātiski prepend `NEEDS_REVIEW:` marķieri reasoning laukam (nevis nomet claim — legitimate "netiešs citāts caur LETA" netiktu mestas). `@quality-reviewer` izgāž visus NEEDS_REVIEW claims operatoram triāžai. Diagnostikas pilns apraksts: `data/autoresearch/DIAGNOSTIC_SUMMARY.md` (lokāls fails — `data/autoresearch/` ir gitignorēta, tāpēc publiskajā spogulī tā nav; agrāk šeit bija wikilinks ar samainītu mērķi un aliasu, kas neatrisinājās nekur).

**Per-doc dispatch preferred:** For > ~5 pending docs per politician, dispatch parallel single-doc `@claim-extractor` sub-agents instead of one sub-agent doing all docs. Each sub-agent gets a clean context; matches the diagnostic path that correctly handles indirect cases 100%.

**Journalist & organization slot pattern (2026-05-04):** daži `tracked_politicians` ieraksti nav politiķi, bet institūciju/žurnālistu plūsmas. Identificē pēc `relationship_type` + `social_accounts.feed_type`:

| `relationship_type` | `feed_type` | Piemēri | Sagaidāms |
|---|---|---|---|
| `journalist` | `relay` | **visi 7 žurnālistu ieraksti**: Lato Lapsa, Gatis Madžiņš, Otto Ozols, Marats Kasems, Krišjānis Kļaviņš, Anastasija Tetarenko-Supe, Katrīna Iļjinska | Atklāšanas kanāls, NEVIS pozīciju avots — slota paša pasei default `empty_doc_ids`; text-scan piesaista citētos politiķus. `journalist` joprojām = TIKAI cilvēki (kopš 2026-06-09/10) |
| `organization` | `relay` | LETA, TV3 Ziņas, IR žurnāls, Saeimas ziņas | ~95–99% empty — saturs sasniedz subjektus caur text-scan, ne caur šo slot |
| `organization` | `first_party` | NBS, LVM, LDDK | Oficiāli institūcijas paziņojumi — ekstraktē TIKAI pašas organizācijas paustu nostāju (reti) |
| `neutral` | dažādi | Filips Rajevskis, Guntars Vītols | Per-doc lēmums; tracked figures, ne org accounts |

> Mediju plūsmu konti (LETA, LTV*, KNL, NRA, TV3 Ziņas, IR žurnāls, Krustpunktā) 2026-06-09/10 pārcelti `journalist`→`organization` (migrācijas + rollback `data/fix_media_feeds_organization_*.sql`) — sk. [CHANGELOG](../../CHANGELOG.md).
>
> **`journalist` = `relay` pēc noklusējuma kopš 2026-08-21** (operatora lēmums, CLAUDE.md invariants #11). Žurnālistu plūsmas paliek atklāšanas kanāli — text-scan piesaista viņu citētos politiķus —, bet pašas vairs neģenerē `position` claims. **`journalist|first_party` tagad ir 0 rindu.** NEvispārini uz „žurnālisti nekad nerunā": apzinātie first_party izņēmumi ir politiskie stratēģi/analītiķi un žurnālisti-kandidāti, un tie nes `neutral`, ne `journalist` (4. rinda; [seeding.md](../seeding.md) § Žurnālisti). Ja tomēr sastop `journalist|first_party` rindu — tas ir svaigs operatora lēmums, izlasi seeding piezīmi, nepieņem ne vienā, ne otrā virzienā.
>
> Pārbaudi, nevis tici tabulai: `SELECT tp.relationship_type, sa.feed_type, COUNT(*) FROM social_accounts sa JOIN tracked_politicians tp ON tp.id=sa.opponent_id GROUP BY 1,2`.

`relay` slot eksistē, lai dokumenti ieiet korpusā un `link_politicians_to_documents` atrod minētos politiķus kā `subject`/`mentioned`. Pats relay konts nekad nav runātājs — pat ja `document_politicians.role='subject'` (legacy junction shape). Default `empty_doc_ids` relay slot's analīzes pasai.

Tas pats attiecas uz `journalist` — visas 7 plūsmas ir `relay` kopš 2026-08-21. Šaurais izņēmums: kad dokuments IR paša žurnālista parakstīts viedokļraksts un viņš ir sava teksta subjekts, lemj standard skip-list un self-check kā parasti. Sveša cilvēka invektīvas pārpublicēšana caur žurnālista handle kā ŽURNĀLISTA `position` ir tieši tas, ko 08-21 lēmums apturēja — ja vārdi pieder citētajai personai, tie pieder viņas slotam caur text-scan.

**Edge case:** Salience-cap-12 atstāj sub-cap relay docs permanent pending stāvoklī (LETA's 7-doc backlog 2026-05-04). Atzīts uzvedības raksturs, ne bug — līdz circuit-breaker izņēmuma vai operator manual sweep.

---
> Pilns aģenta prompts: `.claude/agents/claim-extractor.md`
