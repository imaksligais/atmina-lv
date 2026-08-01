# @saeima-tracker

> Kanoniskais prompts (izpildei): [.claude/agents/saeima-tracker.md](../../../.claude/agents/saeima-tracker.md) — šī lapa ir īss apraksts cilvēkiem.

Saeimas sēžu un balsojumu izsekotājs.

**Ko dara:** Skrāpē Saeimas darba kārtības un balsošanas rezultātus ar Playwright, parsē datus, saglabā DB ar automātisku politiķu sasaisti un claim ģenerēšanu.

**Kad izmanto:** Nedēļas rutīnā vai kad notikuši jauni Saeimas balsojumi.

**Tehniski:** Saeimas vietne (Lotus Notes/Domino) renderē ar JavaScript — OBLIGĀTI jāizmanto Playwright (`browser_navigate`, `browser_snapshot`), nevis WebFetch.

**Darbplūsma:**
1. Atvērt sēdes darba kārtību → snapshot
2. Izvilkt balsojumu URL no snapshot
3. Katram balsojumam — snapshot + parse + store
4. **Izlasīt likumprojekta tekstu/anotāciju** un uzrakstīt saturīgu summary (ne tikai nosaukumu!)
5. Ģenerēt claims katram izsekotajam deputātam — **obligāti ar `claim_type='saeima_vote'`**

**Svarīgi:**
- Ja ir grozījumi likumā, apskatīt arī `wiki/laws/` attiecīgo likuma lapu kontekstam.
- **claim_type=`'saeima_vote'`** — katrs balsojuma claim ir jātagē kā `saeima_vote` (nevis default `position`). `generate_claims_from_votes` to dara automātiski no 2026-04-11 (Phase B); ja raksti jaunu kodu, kas izsauc `store_claim()` balsojumam, obligāti nodod `claim_type='saeima_vote'`. Bez tā Phase C filtri neizdalīs balsojumus no Pozīcijām, un visas galvenes atkal būs kļūdainas.

**NEdrīkst (2026-04-17 mācības):**
- **Nemanuāli neievadīt topic kā string** — vienmēr caur `src.saeima._motif_to_topic()`. Hand-typed `'Ekonomika un finanses'` 16.apr piesārņoja 5630 claims.
- **Nepārrakstīt `deputy_name`** lai "salabotu" matching — pievienot formu `tracked_politicians.name_forms` vai labot canonical `name`. Saeimas raw vārds ir audit trail.
- **Summary nedublē motif title** — sāc ar būtību (ko likums dara, kurš iniciēja, kāpēc koalīcija dalījās), ne ar "Grozījumi X likumā (2. lasījums, steidzams)...".
- **Summary lauks NAV opcionāls bill-type balsojumiem** (2026-05-16 regress): Step 3.B nedrīkst izlaist. Pirms 30.04 100% balsojumiem bija saturīgs summary; pēc — 21 balsojumam tika atstāts NULL, kas radīja 1943 generic claim stances ("Balsoja PAR: <motif>" vietā "Atbalsta: <substance>"). Cēlonis: Step 3.5 strukturāli bija "papildu" solis starp Step 3 un Step 4 — restrukturēts par atomic blokā 3A→3B→3C (sk. CHANGELOG). Kods + prompt + verification gate darbojas trīs slāņos kā layered defense, bet pirmā līnija ir disciplīna: katram bill-type balsojumam summary tiek rakstīts pirms `process_vote_snapshot` izsaukuma.
- **URL** — gan absolūts, gan relatīvs ceļš pieņemams; `_resolve_vote_url()` to apstrādā. Nekonkatenē bāzes URL manuāli (tas radīja 3000+ rindu dubult-prefiksu bugu 16.apr).

---
> Pilns aģenta prompts: `.claude/agents/saeima-tracker.md`
