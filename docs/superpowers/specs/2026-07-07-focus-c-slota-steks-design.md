# Spec: Uzmanības centra C slota steks (spriedzes + dienas citāts)

**Datums:** 2026-07-07 · **Statuss:** DONE 2026-07-07 (master `2a1c497`..`5859231`; check.sh zaļš, Playwright 1440/375 abas tēmas — B 817px / C 674px līdzsvarā; DEPLOYED + live-verificēts 07-07: 3 dueļi + citāts, atdalītāji, kicker "⚡ Spriedzes"/"Dienas citāts" uz atmina.lv)
**Problēma:** kompozīta C slots rāda tieši vienu vienumu (parasti īso spriedzes dueli), kamēr B slotā ir garā pretrunas kartīte → labajā kolonnā liels tukšums. Dzīvajā DB ir 8 spriedzes <14d — 7 no tām landing nekur neparādās.
**Risinājums:** `slot_c` vietā `slot_c_items` saraksts: līdz 3 svaigas spriedzes stekā + dienas citāts kā pēdējais. Kolonna piepildās, saturs vienmēr svaigs.
**Saistītie:** kompozīta spec `2026-07-07-uzmanibas-centra-rotacija-design.md` (B slots un karstā tēma nemainās); hero karuseļa spec `2026-07-07-hero-karuselis-jaukts-design.md` (dedup integrācija caur `_focus_used_urls`).

## Verificētie dati (2026-07-07 vakars, dzīvā DB)

Spriedzes <14d: **8** (<30d: 22). Dienas citāts vienmēr pieejams (113 kvalificēti citāti nedēļā pēc rīta spec datiem).

## Sastāva noteikumi (`assemble_focus` jaunā forma)

Atgriež `{"hot": ..., "slot_b": ..., "slot_c_items": [...]}`:

- **`slot_b`** — nemainīgs: viens vienums, fallback ķēde svaigā pretruna (<14d) → spriedze → dienas citāts.
- **`slot_c_items`** — saraksts, secība: **līdz 3 svaigas spriedzes** (<14d, DESC pēc `created_at`; izslēdzot to, kas jau `slot_b`, ja B ir spriedze) `{"kind": "tension", "item": t}`, tad **dienas citāts** `{"kind": "quote", "item": q}` kā pēdējais, ja (a) tas nav jau `slot_b` un (b) tā `source_url` nav karstās tēmas citātos (esošais dedup noteikums saglabājas). Tukšs saraksts = kolonna kolapsē; esošais CSS `.focus-grid > .focus-slot:only-of-type { grid-column: 1/-1 }` tad izpleš B pilnā platumā.
- **`_fresh_tension`** helpers vispārinās uz `_fresh_tensions(tensions, limit, exclude=None)` (saraksta versija); B slota izvēle to lieto ar `limit=1`.

**Integrācijas punkts (obligāts):** `_focus_used_urls` (`focus.py`, hero karuseļa dedup) šobrīd lasa `slot_b`/`slot_c` — jāatjaunina, lai citātu URL ņem arī no `slot_c_items` saraksta. Pretējā gadījumā hero pozīcija var dublēt C slota citātu.

## Šablons (`templates/index.html.j2` C slota zars)

C slota `focus-slot` kaste (esošā `{% for slot in [...] %}` konstrukcija sadalās: B renderējas kā līdz šim; C kļūst par savu blodu ar ciklu pār `slot_c_items`):

- Kicker **"⚡ Spriedzes"** vienreiz virs steka (ja sarakstā ir vismaz viena spriedze).
- Katra spriedze = esošā `focus-duel` kartīte, bet: `type_lv` marķējums pāriet uz rindas meta-rindu (`{{ t.date }} · {{ t.type_lv }}{% if t.topic %} · {{ t.topic }}{% endif %}`); "Visas spriedzes →" saite VIENREIZ steka apakšā, ne katrā rindā.
- Steka atdalītājs: jauns CSS noteikums `.focus-duel + .focus-duel { border-top: 1px solid var(--border-soft); padding-top: 12px; margin-top: 12px; }` (esošajā idiomā).
- Citāts (ja ir) — kicker "Dienas citāts" + esošais `focus_quote_card` makro, zem spriedzēm.

B slota markup nemainās. Mobilajā (<900px) grid jau ir viena kolonna — steks turpina strādāt.

## Testi

- `assemble_focus` esošie 4 testi pielāgojas `slot_c_items` formai.
- Jauni: 3 spriedžu cap; B-spriedzes izslēgšana no C; citāts vienmēr pēdējais; citāta dedup pret karsto tēmu izslēdz to arī no C; viss tukšs → `slot_c_items == []`.
- `_focus_used_urls`: citāts `slot_c_items` sarakstā nonāk URL kopā (hero dedup).
- Renders + `check.sh` + baseline REGEN + Playwright 1440/375 abas tēmas.

## Ārpus tvēruma

B slots, karstā tēma, hero karuselis (paliek kā ir); spriedžu datu modelis; `spriedzes.html` lapa.
