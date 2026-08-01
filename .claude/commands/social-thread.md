---
name: social-thread
description: Uzraksti X/Twitter pavedienu (un pēc pieprasījuma FB postu) par dienas pārskatu — rindkopu tvīti katrs savā kopējamā blokā, DB-verificēti @tagi, unikāli sepia attēli katram tvītam, saite tikai pēdējā tvītā. Encodes copy-block + no-leading-tag + handle-verification guardrails.
argument-hint: "[YYYY-MM-DD] (pārskata datums; noklusējums — jaunākais daily_brief)"
---

# Social thread — atmina.lv dienas pārskata pavediens

> **Pass/fail kritēriji sociālajam pavedienam — [`wiki/operations/quality-bars.md`](../../wiki/operations/quality-bars.md). Izlasi PIRMS glabāšanas/publicēšanas, ne pēc.** CLAUDE.md § Quality Bars sauc šo failu par kanonisko nesēju; līdz 2026-08-09 uz to saistīja 1 no 17 nesējiem.

Kad operators prasa "twitter thread par X pārskatu", izpildi VISU šo procedūru. Noteikumi kodē agrākus incidentus, ne gaumi.

## 0. Priekšnosacījumi

- Pārskatam jābūt DB (`context_notes`, `note_type='daily_brief'`) un publicētam (`https://atmina.lv/blog/{DATE}.html` → 200). Ja nav — vispirms dienas rutīna, ne pavediens.
- **NEMEKLĒ pārskatu ar ar roku rakstītu topic virkni.** Šeit agrāk stāvēja `dienas pārskats {DATE}` — tā ir **veca forma**, un `daily_brief` rindās vēsturiski līdzās pastāv **četras**: `dienas analīze` (kanoniskā, 68 rindas), `dienas pārskats` (47), `dienas parskats` bez diakritikas (1) un `daily` (1). Vaicājums ar `LIKE 'dienas analīze%'` tāpēc redz 68 no 117 pārskatiem un klusi izlaiž 49 — bez kļūdas, jo nepareiza topic virkne vienkārši atgriež mazāk. Lieto `src.briefs.daily_brief_topic()` rakstīšanai un `src.briefs.brief_subject_date()` dienas noteikšanai (topic → H1 → `created_at` mantotajām rindām); tieši šī nesakritība reiz padarīja Telegram kopsavilkumu vienmēr tukšu (CHANGELOG § Telegram topic diverģence).
- Dienas plakāta varianti live (`…{DATE}-dienas-parskats-*-og.jpg` → 200) — 6. tvīta OG-kartītei.

## 1. Saturs no pārskata

Pavediena struktūra seko pārskata "Galvenais" sadaļai: **1. tvīts = dienas vadošā tēma** (tikai tas, kas TAJĀ dienā jauns — ne stāvoši fakti), tālāk pa tēmu blokam tvītā, **~5 satura tvīti + noslēgums**. Katram apgalvojumam jābūt segtam ar claim ID — pieraksti tos melnraksta "Avotu piezīmes" sadaļā.

## 2. Tagi (HARD)

- @tago TIKAI politiķus ar rokturi DB: `SELECT sa.handle FROM social_accounts sa WHERE sa.opponent_id=? AND sa.platform='twitter'` (NB: **platform='twitter'**, ne 'x'; `tracked_politicians.x_handle` ir legacy — nelieto).
- Bez DB roktura → vārds bez @, melnrakstā sadaļa "Bez DB handle: … (verificēt pirms posta)".
- **Tvīts NEDRĪKST sākties ar @tagu** (X to uztver kā reply → krīt redzamība) — tags teikuma vidū/beigās.

## 3. Teksta forma (HARD)

- **Katrs tvīts savā atsevišķā ``` blokā** ar numuru (1/6, 2/6 …) — VIENS kopīgs bloks visam pavedienam neder (viena kopēšanas poga; 2026-07-03 recidīvs). Bloka priekšā rinda `**N/6** · attēls: fails.png`.
- Rindkopas, ne aizzīmes; @atminaLV (pareizais rokturis — `@atmina_lv` neeksistē; twikit-verificēts 2026-07-22) ir verified — 280 zīmju limits nav saistošs, bet turi tvītu ≤3 īsām rindkopām.
- Saite TIKAI noslēguma tvītā (`https://atmina.lv/blog/{DATE}.html`); noslēguma tvītam PIEVIENO dienas plakāta `…-og.jpg` kā mediju — NEpaļaujies uz OG-kartīti: X to divas reizes pēc kārtas (07-20 un 07-21 pavedieni) nerādīja pat ar 100% tīru mūsu pusi (visi OG/twitter tagi korekti, og.jpg 200 Twitterbot UA). Operatoram melnrakstā sūti arī og.jpg failu.
- LV gramatikas + stilistikas vārti pirms nodošanas (locījumi, garumzīmes, bez kalkiem).
- **Nedēļas dienu NEKAD neraksti no galvas** — rēķini to (`date(Y,M,D).weekday()`) vai neraksti vispār. 2026-07-25: pavediena 1. tvītā 24. jūlijs nosaukts par ceturtdienu, kaut tā bija piektdiena; operators to pamanīja PĒC publicēšanas. Datums pārskatā ir rutīnas diena, tāpēc "vakar/šodien" formas arī nav drošas — droši ir tikai "24. jūlijā" vai pārbaudīta dienas nosaukuma forma.

## 4. Attēli

- Katram satura tvītam (1–5) unikāls attēls: sepia, 16:9, **text-free** (bez virsrakstiem/skaitļiem attēlā — operatora standarta prasība), **full-bleed bez papīra malām** (operatora prasība 2026-07-08): promptā "full-bleed, edge-to-edge, NO border/frame/paper margins"; ja malas tomēr ģenerējas — proporcionāls PIL crop ~3 % katrā pusē (16:9 saglabājas), nevis pārģenerēšanas loterija.
- **Vide attēlos ir LATVISKA (operatora prasība 2026-08-21).** Ģenerators pēc noklusējuma zīmē svešas telpas (gotisks Vestminsteras-tipa parlaments, anglosakšu tiesu zāles) — promptā apraksti reālo Latvijas vidi. Saeimas zālei: kompakts gaiša ozolkoka sēžu PUSLOKS koncentriskos lokos, zaļi polsterēti krēsli, mikrofoni + klēpjdatori (ekrāni tukši!) uz galdiem, koka paneļu sienas, publikas balkons aizmugurē, paaugstināts prezidijs ar tribīni, Latvijas karogs kreisajā malā + ES karogs pie prezidija; deputāti modernos uzvalkos, ne 19. gs. frakās. Tas pats princips citām vietām: Rīgas siluets, Latvijas lauku ainava — ne ģenēriska Rietumeiropa.
- Prompti → `docs/tweet_bank/{DATE}-thread-prompts.json` (`{"1-slug": "prompts...", ...}`), ģenerēšana:
  ```bash
  .venv/Scripts/python -m src.graphics.cli thread --date {DATE} --prompts docs/tweet_bank/{DATE}-thread-prompts.json
  ```
  → `output/images/threads/{DATE}-thread-{suffix}.png`.
- OBLIGĀTI vizuāli pārbaudi katru PNG (Read) — halucinēts teksts / kropļotas garumzīmes → pārģenerē konkrēto.

## 5. Melnraksts + nodošana

- **`{DATE}` visos melnrakstu, promptu un attēlu vārdos ir PUBLICĒŠANAS diena — diena, kad taisi pavedienu —, nevis pārskata subjekta diena.** Dienas pārskatam tās parasti sakrīt, tāpēc slazds guļ nedēļas pārskatā: nedēļai 08-03…08-09 komplekts ir `2026-08-10-*`, jo tas taps 10. augustā. Ja nosauc pēc nedēļas sākuma, faila vārds trāpa iepriekšējā komplektā un `Write` to **klusi pārraksta** (2026-08-17: pārrakstīti divi 08-10 faili, atgūti no `HEAD`). Pirms rakstīšanas pārbaudi `ls docs/tweet_bank/{DATE}-* docs/social/{DATE}-*`; ja kaut kas jau ir, tas NAV tavējais.
- Melnraksts → `docs/tweet_bank/{DATE}-dienas-parskats-social.md` (paraugs: 2026-07-03 fails): galvene (statuss, stils, tagi, attēli), tvīti, `## Handles (no DB)`, `## Avotu piezīmes (claim id / domēns)` + izlaisto saraksts. Nedēļas pavedienam tā pati shēma ar `nedelas-parskats` vietā `dienas-parskats`.
- Operatoram: attēlus sūti ar SendUserFile (`display: "attach"`, lai telefonā lejupielādējas) + pavedienu tekstā pa blokam. NEPOSTĒ pats — publicēšana vienmēr operatora rokās.

## FB posts (ja prasa "arī facebook postu")

- → `docs/social/{DATE}-dienas-parskats-facebook.md` (paraugs: 2026-07-03 fails). Viens konsolidēts posts, **bez @-tagiem** (FB lapu nosaukumi ≠ X handle, DB tos neglabā; vārds + partija iekavās), ~1900 zīmes, skaidrojošs tonis.
- Obligātās rindas beigās: `Diena skaitļos: …` (no pārskata Koalīcija vs Opozīcija tabulas, summai jāsakrīt) un `Atmiņa nepieraksta vērtējumu, bet secību: datums, pozīcija, avots.` + saite.
- Piezīmju sadaļā: skaitļu atšifrējums, spriedzes, izlaistais, OG-kartītes norāde.

## Reddit posti (ja prasa "reddit postu")

- → `docs/social/{DATE}-dienas-parskats-reddit.md`. **Primārais mērķis: r/atminaLV** (projekta community kopš 2026-08; pašreklāmas ierobežojumu nav). r/latvia lieto TIKAI ik pa laikam atsevišķiem atradumiem (piem., apstiprināta pretruna), ne ikdienas pārskatiem — operatora norāde 2026-08-14.
- Teksta posts bez attēliem (OG-kartīti Reddit ģenerē pats no saites), bez Reddit lietotāju tagiem, bez aicinājumiem sekot; saite un aicinājums norādīt kļūdas komentāros beigās. Pēc pieprasījuma otrs, angliskais variants šaurākai tēmai (r/BalticStates tips).
