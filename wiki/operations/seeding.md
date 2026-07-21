# Politiķu / entītiju seedēšana

Jaunu `tracked_politicians` ierakstu pievienošana — institucionālās balsis un partijas-piederības lamatas.

## Institucionālā balss — `relationship_type='organization'`

Slots interešu grupām, arodbiedrībām, darba devēju asociācijām, profesionālām struktūrām, kas publicē politiskas pozīcijas, bet nav politiķi vai žurnālisti (pirmā: LDDK #193, 2026-04-30, commit `dad3928`). NEder `journalist` (nav komentārs), `neutral` (nav objektīvs — institucionālas intereses) vai `tracked` (piesārņotu koalīcija/opozīcija skaitus).

**Onboarding:**

1. `tracked_politicians` rinda: `relationship_type='organization'`, `party=NULL`, `name` = oficiālais LV nosaukums, `role` = apraksts (piem. "Darba devēju interešu organizācija"), `x_handle` = handle bez `@`.
2. `name_forms` = gan abreviatūra, gan pilnais nosaukums + varianti (piem. LDDK: `["LDDK", "Latvijas Darba Devēju Konfederācija", "Darba devēju konfederācija"]`). **Seedējot diakritiku saturošus nosaukumus — iekļauj gan diacritic, gan ASCII variantus** (matcher nenostrippo diakritikas). NB: `scripts/audit_matcher_name_forms.py` ķer tikai trūkstošos ASCII variantus, NE nepareizu celmu — vēsturiskais piemērs: Šnore (#7) formās bija palatalizētais `Šņore` vietā `Šnore` (fiksēts 2026-05-16, `ba66f6f`); celmu pareizību verificē ar acīm.
3. `social_accounts`: `feed_type='first_party'`, `active=1`, `platform='twitter'`.
4. **Nav koda izmaiņas** — slot-B refaktorings (commit `031820f`, 2026-04-30) pievienoja `'organization'` visiem 9 audience-exclusion sites (`briefs.py`, `social.py`, `render/{blog,x,positions}.py`, `social_agent/candidates.py`).

**Uzvedība platformā:** izslēgts no koalīcija/opozīcija blokiem; iet "Neitrāli" rindā; "Komentētājs" etiķete (party=NULL); fetch priority 3 (kā žurnālistam).

**Multi-voice:** institūcijas runā caur vairākām personām (LDDK: prezidents, ģenerāldirektors, institucionālā balss). Visas claims = organizācijas pozīcijas; ja līderi vēlāk pievienoti atsevišķi, viņu claims kļūst par kandidātiem retroaktīvai `speaker_id` sasaistei.

Tas pats paterns bez koda izmaiņas: LBAS, LTRK, LPS, LBA u.c.

## Partijas piederība — kopējo sarakstu lamatas

Ziņās bieži parādās apvienots saraksts (piem. "LPV/Kopā Latvijai") — tā ir **kopēja vēlēšanu saraksta** forma, NE partijas piederība.

- **Kopā Latvijai** = Bartaševiča 2023-04 dibinātā partija (pēc Saskaņas izformēšanas); Tutins ir līdzdibinātājs. 14. Saeimas vēlēšanās kandidēja LPV/Kopā Latvijai kopējā sarakstā Rēzeknē. **NEVIS** Latvija Pirmajā Vietā (Liepiņas vadītā).
- `parties` tabulā "Kopā Latvijai" nav reģistrēts → `get_coalition_map` atgriež `"other"` → UI rāda "Bez Saeimas frakcijas" (līdz 2026-07-22 "Ārpus Saeimas"; sk. CHANGELOG).

**Likums:** pievienojot Latgales / ex-Saskaņas politiķi, vienmēr **verificē partijas piederību** (Wikipedia LV / puaro.lv / ir.lv) PIRMS `party` lauka iestatīšanas. Ja politiķis publiski sevi sauc par X, lieto to neraugoties uz kopējā saraksta formulējumu ziņās. (2026-04-26 Tutins sākotnēji kļūdaini iesēdināts kā "Latvija Pirmajā Vietā", balstoties uz PDF "LPV/Kopā Latvijai" formulējumu.)
