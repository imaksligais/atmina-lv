---
name: social-thread
description: Uzraksti X/Twitter pavedienu par dienas vai nedēļas pārskatu (pēc pieprasījuma arī Facebook/Reddit postu) — rindkopu tvīti katrs savā kopējamā blokā, DB-verificēti @tagi, unikāli sepia attēli, saite tikai pēdējā tvītā.
argument-hint: "[YYYY-MM-DD vai nedēļa] (pārskata datums; noklusējums — jaunākais daily_brief)"
---

# Social thread — dienas vai nedēļas pārskata pavediens

> **Pirms nodošanas izlasi [`wiki/operations/quality-bars.md`](../../wiki/operations/quality-bars.md) § «Sociālais pavediens», arī «Ierāmējuma vārti».**

Kad operators prasa pavedienu par pārskatu, izpildi VISU šo procedūru. Noteikumi kodē agrākus incidentus, ne gaumi.

## 0. Priekšnosacījumi

- Pārskats ir `context_notes` (`daily_brief` vai `weekly_brief`) un publicēts: `https://atmina.lv/blog/{brief_publish_key(note_type, subject_date)}.html` → 200 (`src.briefs`); citādi vispirms rutīna.
- Atlasi pēc `note_type`, NE pēc ar roku rakstītas topic virknes (vēsturiski līdzās pastāv četras formas); dienu nosaki ar `brief_subject_date()`, rakstīšanai `daily_brief_topic()` (CHANGELOG § Telegram topic diverģence).
- Noslēguma plakāts = tas, uz ko rāda lapas `og:image` (`curl -s URL | grep -o 'og:image" content="[^"]*'`; var būt vairāki hash varianti) → 200.
- **Pirmdienās** nedēļas pārskata svētdiena = svētdienas dienas pārskats. Nedēļas pavediens ņem pārklājošās tēmas; dienas pavedienā tikai pārējais, postē otro — un tikai, ja operators to grib (2026-10-12: postēja tikai nedēļas).

## 1. Saturs no pārskata

Seko pārskata «Galvenais»: **1. tvīts = perioda vadošā tēma** (tikai tas, kas TAJĀ dienā/nedēļā jauns, ne stāvoši fakti), tālāk pa tēmu blokam tvītā, ~5 satura tvīti + noslēgums. Katram apgalvojumam claim ID melnraksta «Avotu piezīmēs».

## 2. Tagi (HARD)

- @tago TIKAI ar rokturi DB: `SELECT handle FROM social_accounts WHERE opponent_id=? AND platform='twitter'` (ne 'x'; `tracked_politicians.x_handle` ir legacy). Ja rokturis neatklāj personu (`@Chapis`), raksti vārdu blakus: «Kristaps Krištopans (@Chapis, LPV)».
- Bez DB roktura → vārds bez @, melnrakstā «Bez DB handle: …».
- **Tvīts NEDRĪKST sākties ar @tagu** (X to uztver kā reply → krīt redzamība).

## 3. Teksta forma (HARD)

- **Katrs tvīts savā ``` blokā** ar numuru (1/6 …); viens kopīgs bloks neder (2026-07-03 recidīvs). Bloka priekšā `**N/6** · attēls: fails.png`.
- Rindkopas, ne aizzīmes; ≤3 īsas rindkopas tvītā. Projekta konts: @atminaLV (`@atmina_lv` neeksistē; 2026-07-22).
- Saite un domēnu nosaukumi (`saeima.lv`, `atmina.lv` — X tos pārvērš saitēs) TIKAI noslēgumā (2026-10-06); citur avotu nosauc vārdos. Noslēgumā pārskata saite + plakāts kā MEDIJS — OG-kartīti X nerāda droši (2026-07-20, 07-21).
- 1. tvītā nav kailas skaitļu rindas (2026-06-08); saite — kails URL, ne markdown; datumi «D. mēnesī», ne ISO.
- LV gramatikas + stilistikas vārti pirms nodošanas.
- **Nedēļas dienu aprēķini** (`date(Y,M,D).weekday()`) vai neraksti; «vakar/šodien» nav droši — pārskata datums ir rutīnas diena (2026-07-25).
- **Skaitļa vārti (2026-10-06, divas kļūdas vienā tvītā).** Katram skaitlim melnrakstā: (a) ko tieši tas skaita, (b) par kādu periodu un vai persona visu periodu bija amatā («visilgāk runājis» deputāts, kas Saeimā bija 2,5 no 4 gadiem), (c) vai tas salīdzināms ar blakus esošo (146 = jautājumi + pieprasījumi blakus «no 144 pieprasījumiem»). Ja (b) vai (c) lasītājam nav acīmredzams — precizē vai izvēlies citu skaitli.

## 4. Attēli

- Katram satura tvītam unikāls attēls: sepia, 16:9, **bez teksta**, **full-bleed** (2026-07-08): promptā «full-bleed, edge-to-edge, NO border/frame/paper margins»; ja malas tomēr ir — PIL crop ~3 % katrā pusē, ne pārģenerēšana.
- **Vide LATVISKA** (2026-08-21). Saeima: kompakts gaiša ozolkoka sēžu pusloks koncentriskos lokos, zaļi krēsli, mikrofoni un klēpjdatori (ekrāni tukši), koka paneļi, publikas balkons, paaugstināts prezidijs ar tribīni, Latvijas karogs kreisajā malā, ES karogs pie prezidija, moderni uzvalki. Citur — Rīgas siluets, Latvijas ainava, ne ģenēriska Rietumeiropa vai debesskrāpji.
- Prompti → `docs/tweet_bank/{PUB_DATE}-thread-prompts.json` (`{"1-slug": "…"}`), ģenerē:
  `.venv/Scripts/python.exe -m src.graphics.cli thread --date {PUB_DATE} --prompts FILE [--backend codex]` → `output/images/threads/{PUB_DATE}-thread-{key}.png`. Gemini 429 → `--backend codex`.
- **Divi komplekti vienā dienā** (nedēļas + dienas): atsevišķi faili `{PUB_DATE}-nedelas-thread-prompts.json` / `-dienas-…` UN atšķirīgas atslēgas `n1-…` / `d1-…` — izvade iet pēc atslēgas, viens komplekts citādi pārraksta otru.
- Vizuāli pārbaudi katru PNG; halucinēts teksts, kropļotas garumzīmes, sveša vide vai zila nokrāsa → pārģenerē konkrēto.

## 5. Melnraksts + nodošana

- **`{PUB_DATE}` = publicēšanas diena** (kad taisi pavedienu), ne pārskata subjekta diena; pārskata URL un plakāts paliek pēc subjekta datuma. Pirms rakstīšanas `ls docs/tweet_bank/{PUB_DATE}-* docs/social/{PUB_DATE}-* output/images/threads/{PUB_DATE}-*`; esošs komplekts NAV tavējais — nepārraksti (2026-08-17).
- Melnraksts → `docs/tweet_bank/{PUB_DATE}-{dienas|nedelas}-parskats-social.md`: galvene (statuss, stils, tagi, attēli), tvīti, `## Handles (no DB)`, `## Avotu piezīmes` + izlaistais.
- Operatoram: attēlus iegulsti atbildē ar Markdown un absolūtu ceļu (arī plakātu), virs katra tvīta bloka. NEPOSTĒ pats — publicē tikai operators.

## FB posts (ja prasa)

- → `docs/social/{PUB_DATE}-{dienas|nedelas}-parskats-facebook.md`. Viens posts, **bez @-tagiem** (vārds + partija iekavās), ~1900–3000 zīmes, skaidrojošs tonis.
- Beigās: `Diena skaitļos: …` / `Nedēļa skaitļos: …` no pārskata Koalīcija vs Opozīcija tabulas (summa sakrīt), tad `Atmiņa nepieraksta vērtējumu, bet secību: datums, pozīcija, avots.` + saite.
- Piezīmēs: skaitļu atšifrējums, izlaistais, plakāta fails.

## Reddit (ja prasa)

- → `docs/social/{PUB_DATE}-{dienas|nedelas}-parskats-reddit-atminalv.md`. Primāri **r/atminaLV**; r/latvia tikai reizēm atsevišķiem atradumiem, ne pārskatiem (2026-08-14).
- Teksta posts bez attēliem, lietotāju tagiem un aicinājuma sekot; beigās saite un aicinājums norādīt kļūdas komentāros. Pēc pieprasījuma angliska versija šaurākai tēmai.
