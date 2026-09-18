# balsojumi.html virtualizācija — datu atdalīšana no rendera

**Statuss:** 1. solis darbā (2026-05-28).
**Konteksts:** `output/atmina/balsojumi.html` šobrīd ir **367 MB** (7.65M HTML rindas, 507 099 `<tr>`). Veidne `templates/balsojumi.html.j2` renderē matricu DIVREIZ: kā `<table>` SSR un kā `matrix_json` `<script>` embed (rinda 522). Pārlūks iesalst DOM parsē. Ilgtermiņā datu apjoms aug lineāri (1500 balsojumu/gads × ~100 deputātu = 150k jaunas šūnas/gads).

**Mērķis:** `balsojumi.html` plāns šell (50–100 KB SSR) + `data/balsojumi-matrica.json` (kompakts, ~300 KB pēc gzip) + JS virtualizēts matricas renderer. Time-to-interactive < 500 ms. Mērogojas līdz 10+ gadu vēsturei bez atkārtotas refaktorēšanas.

## Datu formāts

`output/atmina/data/balsojumi-matrica.json`:

```jsonc
{
  "meta": {
    "version": 1,
    "generated_at": "2026-05-28T10:00:00+03:00",
    "votes_total": 5703,
    "encoding": "P=Par,N=Pret,A=Atturas,X=Nebalsoja,.=absent"
  },
  "votes": [
    {
      "i": 0,             // index aligned with politicians[*].v string positions
      "vid": 12345,       // saeima_votes.id
      "d": "2022-11-03",  // vote_date
      "t": "10:15",       // vote_time
      "m": "Par MK ...",  // motif
      "s": "Summary...",  // summary (optional)
      "r": "Pieņemts",    // result
      "tp": "Imigrācija", // topic
      "url": "...",       // saeima.lv vote URL
      "doc_url": "...",   // bill document URL
      "doc_nr": "Lp-123", // bill document_nr
      "tot": [25, 0, 2],  // [par, pret, atturas]
      "uni": false,       // is_unanimous shortcut
      "f": [              // faction breakdown
        {"f": "JV", "p": 25, "n": 0, "a": 2, "x": 3}
      ]
    }
  ],
  "factions": [
    {"f": "JV", "c": "#3b82f6", "m": [2, 15, 156]}
  ],
  "politicians": {
    "2": {
      "n": "Evika Siliņa",
      "f": "JV",
      "s": "evika-silina",
      "v": "PPNAA.PPP...",         // 5703 chars, indexed by votes[i]
      "sum": [5000, 100, 50, 50],  // [par, pret, atturas, nebalso]
      "att": 96,                    // attendance_pct
      "dis": [                      // dissenting votes
        {"i": 234, "v": "Pret", "fm": "Par"}
        // i = vote index, v = own vote, fm = faction majority
      ]
    }
  }
}
```

**Vote string kodējums:**
- `P` = "Par"
- `N` = "Pret"
- `A` = "Atturas"
- `X` = "Nebalsoja" vai cita ne-standarta vērtība (rēķinās kā nebalso)
- `.` = `None` (nepiedalījās — nav ieraksta `saeima_individual_votes`)

`.` izvēlēts ASCII drošības + JSON lasāmības dēļ (em-dash daudzbaitains, `_` viegli sajaukt ar burtu, `0` semantiski apjucīgs).

**Lielums:** 5703 zīmes × ~100 deputāti = ~570 KB tikai vote stringos. `votes[]` metadati + politicians objekti pievieno ~250 KB. Kopā **~800 KB nesaspiests, ~250–400 KB pēc brotli**. Saglabājas mērogojams līdz ~20k balsojumiem (~2–3 MB br).

## Soļi

### 1. solis — Datu emiters (ŠOBRĪD)

- [x] Plāna fails (šis dokuments).
- [ ] `src/render/votes.py::_emit_matrix_json()` — paņem `_build_matrix_data()` izvadi, konvertē uz kompaktu formātu, ieraksta `output/atmina/data/balsojumi-matrica.json`.
- [ ] `render_votes()` izsauc `_emit_matrix_json()` pēc esošā veidnes renderēšanas (paralēli, nebrūk).
- [ ] `tests/test_render_votes_matrix_json.py` — unit testi kompaktajam kodējumam (roundtrip P/N/A/X/. → "Par"/"Pret"/...), schema validācija, faila esamība pēc `generate_public_site()` smoke.
- [ ] **SSR matrica veidnē paliek nemainīga** — šis ir bezriska refaktorings, kas pievieno datu artefaktu nemainot UI.
- [ ] Pārbaudīt pēc rebuild: `output/atmina/data/balsojumi-matrica.json` eksistē, valid JSON, satur visus tracked deputātus.
- [ ] `bash scripts/check.sh` paliek zaļš.

### 2. solis — Klients-puses renderer

- [ ] `templates/static/js/votes-matrix.js` — virtualizēts matricas renderer (kolonnu virtualizācija, ~30–60 redzamās kolonnas vienlaikus, event delegation).
- [ ] `templates/balsojumi.html.j2`:
  - Noņemt SSR matricas bloku (rindas 203–238).
  - Aizvietot ar `<div id="matrix-root" data-src="/data/balsojumi-matrica.json" class="matrix-skeleton"></div>`.
  - Noņemt `matrix_json` embed (rinda 522); JS `fetch()` ielādē no static path.
  - Filtru UI HTML paliek SSR — JS pārtver `change` eventus.
- [ ] `src/render/votes.py::render_votes()`:
  - Nemainīt `matrix_data` parametra plūsmu (template gates `{% if matrix_data %}`); padod tukšu `{}` lai SSR bloks neaktivējas, BET emit_matrix_json joprojām strādā.
- [ ] `tests/test_render_chars.py` baseline regen — balsojumi.html lielums kritīsies par >99%.
- [ ] Manuālais smoke `python serve.py` ar testu:
  - Lapa ielādējas < 1s.
  - Matrica parādās pēc fetch (< 200 ms).
  - Filtri (frakcija, sēde, strīdīgie, vote-type highlight) strādā.
  - showVoteDetail + showPoliticianDetail panel darbojas.
  - Scroll uz #vote-N hash navigāciju strādā.

### 3. solis — Veiktspējas nostiprina

- [ ] `tests/test_render_balsojumi_size.py` — assert `balsojumi.html` < 500 KB, `balsojumi-matrica.json` < 2 MB.
- [ ] `<link rel="preload" as="fetch" href="/data/balsojumi-matrica.json" crossorigin>` pievienots balsojumi.html `<head>`.
- [ ] `.htaccess` (LiteSpeed): brotli precompression `data/balsojumi-matrica.json.br` + `Cache-Control: public, max-age=3600`.
- [ ] Lighthouse smoke uz lokālo serve.py: TTI < 1s, CLS = 0.

## Atpakaļgaita

Ja 2. solis sastāv ar UI regresiju ražošanā:
- `git revert` veidnes commit → SSR matrica atjaunojas (datu emiters paliek, vienkārši nelietots).
- `_emit_matrix_json` ir idempotents un nesatur side-effects ārpus output dir.
- 1. solis ir izlaists no 2. soļa atkarīgi: emiteris drošs neatkarīgi no veidnes stāvokļa.

## Saistītās lapas (nākotnē, ne tagad)

Pēc 3. soļa pabeigšanas šablons piemērojams arī:
- `saites.html` (11 MB) — politiķu saišu grafs
- `x.html` (5 MB) — Twitter feed
- `zinas.html` (7.3 MB) — ziņu feed

Tāda paša formāta plāni rakstāmi katram atsevišķi. Reusable JS modulis `templates/static/js/virtualized-grid.js` izvilkstāms pēc 2-3 implementācijām.
