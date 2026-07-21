---
name: social-thread
description: Uzraksti X/Twitter pavedienu (un pēc pieprasījuma FB postu) par dienas pārskatu — rindkopu tvīti katrs savā kopējamā blokā, DB-verificēti @tagi, unikāli sepia attēli katram tvītam, saite tikai pēdējā tvītā. Encodes copy-block + no-leading-tag + handle-verification guardrails.
argument-hint: "[YYYY-MM-DD] (pārskata datums; noklusējums — jaunākais daily_brief)"
---

# Social thread — atmina.lv dienas pārskata pavediens

Kad operators prasa "twitter thread par X pārskatu", izpildi VISU šo procedūru. Noteikumi kodē agrākus incidentus, ne gaumi.

## 0. Priekšnosacījumi

- Pārskatam jābūt DB (`context_notes`, `note_type='daily_brief'`, topic `dienas pārskats {DATE}`) un publicētam (`https://atmina.lv/blog/{DATE}.html` → 200). Ja nav — vispirms dienas rutīna, ne pavediens.
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

## 4. Attēli

- Katram satura tvītam (1–5) unikāls attēls: sepia, 16:9, **text-free** (bez virsrakstiem/skaitļiem attēlā — operatora standarta prasība), **full-bleed bez papīra malām** (operatora prasība 2026-07-08): promptā "full-bleed, edge-to-edge, NO border/frame/paper margins"; ja malas tomēr ģenerējas — proporcionāls PIL crop ~3 % katrā pusē (16:9 saglabājas), nevis pārģenerēšanas loterija.
- Prompti → `docs/tweet_bank/{DATE}-thread-prompts.json` (`{"1-slug": "prompts...", ...}`), ģenerēšana:
  ```bash
  .venv/Scripts/python -m src.graphics.cli thread --date {DATE} --prompts docs/tweet_bank/{DATE}-thread-prompts.json
  ```
  → `output/images/threads/{DATE}-thread-{suffix}.png`.
- OBLIGĀTI vizuāli pārbaudi katru PNG (Read) — halucinēts teksts / kropļotas garumzīmes → pārģenerē konkrēto.

## 5. Melnraksts + nodošana

- Melnraksts → `docs/tweet_bank/{DATE}-dienas-parskats-social.md` (paraugs: 2026-07-03 fails): galvene (statuss, stils, tagi, attēli), tvīti, `## Handles (no DB)`, `## Avotu piezīmes (claim id / domēns)` + izlaisto saraksts.
- Operatoram: attēlus sūti ar SendUserFile (`display: "attach"`, lai telefonā lejupielādējas) + pavedienu tekstā pa blokam. NEPOSTĒ pats — publicēšana vienmēr operatora rokās.

## FB posts (ja prasa "arī facebook postu")

- → `docs/social/{DATE}-dienas-parskats-facebook.md` (paraugs: 2026-07-03 fails). Viens konsolidēts posts, **bez @-tagiem** (FB lapu nosaukumi ≠ X handle, DB tos neglabā; vārds + partija iekavās), ~1900 zīmes, skaidrojošs tonis.
- Obligātās rindas beigās: `Diena skaitļos: …` (no pārskata Koalīcija vs Opozīcija tabulas, summai jāsakrīt) un `Atmiņa nepieraksta vērtējumu, bet secību: datums, pozīcija, avots.` + saite.
- Piezīmju sadaļā: skaitļu atšifrējums, spriedzes, izlaistais, OG-kartītes norāde.
