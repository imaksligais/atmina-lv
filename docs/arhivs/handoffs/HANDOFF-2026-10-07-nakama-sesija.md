# HANDOFF 2026-10-07 — nākamās sesijas darba kārtība (advisor ieteikums)

> **2026-10-08: atlikumi izdarīti → `docs/HANDOFF-2026-10-08-atlikumi.md`** (punkti 2, 4–6; atvērts tikai operatora lēmumi).

Secību nosaka termiņi, nevis darba apjoms.

1. ~~**Nākamā sesija: 10-07 dienas rutīna**~~ — IZDARĪTS 2026-10-07 vakarā (pārskats publicēts, CHANGELOG (10)). (`/dienas-rutina`). Tavara un Kulberga Stambulas konvencijas pozīcijas (claims 730724–730728) iekļūst pārskatā tikai tad, ja rutīna noskrien.
2. **Līdz 3.11 (15. Saeimas pirmā sēde): kolektīvo iesniegumu polaritāte ielādē.** 2026-10-07 izlaboti 12 balsojumi, bet ģenerators joprojām raksta iesnieguma PRASĪBU, ne balsojamo objektu (`backlog/saeima.md` [FIX] «Kolektīvo iesniegumu balsojumi…»). Darbs:
   - `@saeima-tracker` Step 3.B un `/saeima-ingest` nolasa darbības vārdu pēc «nolemj:» (recepte: `.scratch/petitions/read_drafts.py`).
   - Tests ar «noraidīt» fiksturi, kas redzēts krītam.
   - T21 CLAUDE.md — tikai ar operatora «jā».
3. **Saeimas pusloks** — `docs/plans/2026-10-07-saeimas-pusloks-ideja.md`. Sāc ar `superpowers:brainstorming`, vispirms atbildi uz tā 3 jautājumiem.
4. ~~Mehāniski atlikumi: 382 balsojumi bez summary~~ — IZDARĪTS 2026-10-07 (CHANGELOG (8)). Jauns: īpašvārdu mazā burta defekts (2006 balsojumi / 175 684 claims) → `backlog/saeima.md` [FIX], operatora lēmums.
5. **Mazi operatora lēmumi:**
   - FP7 lomas maiņa (#37/#41): vai «minor_shift»? Ierakstīt `contradiction-hunter.md`.
   - ~~Tavara 730724/730725~~ — atstāti 0,65 bez marķiera; ~~9 kandidāti~~ — #52/#54 publicēti, 7 noraidīti (CHANGELOG (10)).
   - Autora uzvārda grep publiskajā klonā (operatora solis).
6. **Profilu dizains — IZDARĪTS un publicēts 2026-10-07** (CHANGELOG (9), commiti 8a38af4c…a5383426). Nākamais: EP deputātu bio no europarl.europa.eu (operators 10-07: nākamajā sesijā) + 3 profilu UI atlikumi — viss `backlog/vietne-ui.md`. Kļaviņa foto CF kešs: ja vēl rāda Jodu, Purge Custom URL panelī (API tokenam purge tiesību nav).

**Pārbaudīts 2026-10-07:** `wiki/dailies` + `wiki/weeklies` nesatur nevienu no 12 apgrieztajiem iesniegumu balsojumiem. 05-25 pārskats citē 973/Lm14, un tā lēmumprojekts ir «nodot», tātad lasījums pareizs.

**Neatvērt:** priekšlikumu balsojumu konvencija (T20), #17/#29/#30/#38 (operators izlēma 10-07).

**~~Priekšlikums~~ IZDARĪTS 2026-10-08 (≤10 aģenti kārtā, CHANGELOG 2026-10-08 (2)):** 19 paralēli ekstrakcijas aģenti, katrs ielādējot embedding modeli, deva atmiņas trūkumu (2× `transaction_rolled_back`, pilnais renders apturēts). Apsvērt `dienas-rutina` 1. kārtā ierobežot ~10 aģentus vai pakas aģentus pārcelt uz 2. kārtu. Prasmi nemainīju.

**2026-10-08 (naktī):** 10-07 NEEDS_REVIEW triāža pabeigta (17 → 0), viltus junction 127450, claim 20597 un wiki saite labotas, deploy 8ca03f97. Atvērts no 10-07: `negative_patterns` «Imant» Krastiņai (operators), Baško pāris (30, 126284), utm dublikātu doc rindas, aģentu paralēlisma priekšlikums.

**2026-10-08 (2):** Baško pāris, utm dedup kods, ≤10 aģenti kārtā — izdarīts. «Imant» paterni piemēroti (CHANGELOG 2026-10-08 (4)); indekss documents(source_url) (3). No šī saraksta nekas nav atvērts.
