# Saeimas pusloks — ieviešanas plāns (2026-10-08)

**Spec:** `docs/superpowers/specs/2026-10-08-saeimas-pusloks-design.md` (lasīt pilnībā). **Izpilde:** viens Opus palīgs (1.–4. uzdevums), orķestrators pārskata diff, pārbauda vizuāli, renderē pilno koku, deploy (5.–6.). Operators apstiprinājis arī deploy (2026-10-08).

## Global Constraints

- Tikai `.venv/Scripts/python.exe`, vide `PYTHONUTF8=1`. Testi nekad neaiztiek produkcijas DB (`tests/conftest.py` § 4–5); YAML ceļus testos pārsien uz `tests/fixtures/` kopijām tāpat kā `tests/test_render_chars.py:198-205`.
- Palīgs NEDRĪKST: `git stash`, `git checkout --`, `git restore`, `git reset`, commit, deploy.
- Sastāvs = `data/cvk_sv2026_ievēlētie.yaml` (100). Vietas un saraksta nosaukumi = `data/cvk_sv2026_rezultati.yaml` + `parties.color`/`short_name` (sk. `src/render/parties.py::_build_election_context`). Ielādētāju nedublēt — kopīgo pārnest uz `src/render/_common/`, ja to lieto `personas.py` un jaunais modulis.
- Sasaiste ar `tracked_politicians` — TIKAI precīzs pilnais `name` (T1: nekādu apakšvirkņu). Šodien: 98/100; bez profila Gita Plaude, Leontijs Morozs.
- Lēcas: «Saraksts»; «Balsoja 14. Saeimā» = `politician_id` ∈ `saeima_individual_votes` (41/100); «Pozīcijas 90 dienās» = `claims.claim_type='position'`, `stated_at` vai `created_at` LV laikā pret `now_lv()` (izvēlēties to, ko lieto profila lapa, un nosaukt komentārā); «Pretrunas» = `contradictions.confirmed=1`, politiķis kā jebkurš puse. Koalīcijas loģiku NEaiztikt.
- Render KRĪT, ja sastāvā ≠ 100 vai `list_nr` nav rezultātu failā. Izdrukā `saeima: sēdvietas=100 izsekoti=N bez_profila=M`.
- Bez inline JS un inline `style=""` ar JS (CSP). JS tikai `assets/slv1.js`, CSS — `assets/style.css` (sekcija ar komentāru `/* Saeima pusloks */`). Krāsas kā tokeni gaišajam un tumšajam režīmam (sk. esošos `:root`/`[data-theme=dark]` blokus; tumšais `--accent` = #90A4AE). Tipogrāfiju un kaimiņu kastu valodu NEmainīt — lieto esošās klases (sk. `partijas.html` vēlēšanu bloku, `personas.html` kartītes).
- Visas jaunās LV virknes — gramatika + stilistika (locījumi, garumzīmes, bez kalkiem).

## 1. uzdevums — e2e tests pirmais

`tests/test_render_saeima.py`: renderē `saeima.html` no fixture DB + fixture YAML (100 rindu fixture sastāvs var būt ģenerēts testā no rezultātu fixture). Pārbauda: (a) 100 sēdvietas SVG; (b) izsekotajam ir saite `politiki/<slug>.html`, neizsekotajam nav; (c) neizsekotajam pozīciju lēcā vērtība «nav datu», ne 0; (d) sastāvs ar 99 → izņēmums. Redzēt to krītam.

## 2. uzdevums — `src/render/saeima.py` + `templates/saeima.html.j2`

- Domēns `saeima` `_orchestrator.py` `KNOWN_DOMAINS` + izsaukums + `root_pages` (sitemap, ~rinda 634).
- Lapas struktūra (mobile-first):
  1. Virsraksts «15. Saeima», apakšvirsraksts vienā teikumā cilvēciski: kas te redzams un ko darīt («Pieskaries deputātam, lai redzētu, ko viņš saka un kā balsoja»). Zīme «Provizoriski — CVK aprēķins, 04.10.» (sk. `partijas.html` provizoriskā zīme).
  2. Lēcu pārslēdzējs — segmentēta poga (4), mobilajā lipīga (`position: sticky`). Bez JS — redzama tikai noklusētā lēca, pogas paslēptas (`.js` klase uz `<html>` jau eksistē? pārbaudi `theme-init.js`; ja nē — pogas renderē ar `hidden` un JS tās atklāj).
  3. SVG pusloks Python pusē: 100 sēdvietas rindās (parlamenta pusloka algoritms), pa sarakstiem no kreisās pēc vietu skaita dilstoši. Katra sēdvieta `<a href="#dep-<slug>" class="seat" data-list=… data-voted14=… data-pos=… data-ctr=… aria-label="Vārds Uzvārds, AS">` ar redzamo apli + caurspīdīgu lielāku trāpījuma apli. Centrā zem loka liels skaitlis «100 deputāti» un aktīvās lēcas kopsavilkums.
  4. Leģenda — mainās ar lēcu: krāsas + teksts + saucējs un periods («dati par 98 no 100», «pēdējās 90 dienās»).
  5. Saraksts zem: `<details>` katram sarakstam (virsrakstā krāsas punkts, nosaukums, vietu skaits); desktop visi atvērti, mobilajā tikai pirmais (JS uzstāda pēc platuma; bez JS — visi atvērti). Katrs deputāts — rinda `id="dep-<slug>"` ar vārdu, apgabalu, aktīvās lēcas vērtību tekstā, un izvēršama kartīte (`<details>` rindā): jaunākā pozīcija (stance, datums, avota saite), pretrunu skaits ar saiti uz profila pretrunām, «Balsoja 14. Saeimā: jā/nē», «Pilnais profils →». Neizsekotajam: «Profils vēl nav izveidots.»
- `print` kopsavilkuma rinda; render krīt pie nepilna sastāva.

## 3. uzdevums — `assets/slv1.js`

Lēcas pārslēgšana (klase uz saknes elementa → CSS krāsas ar `transition: fill`; `prefers-reduced-motion` izslēdz), leģendas un kopsavilkuma teksta maiņa (teksti iepriekš renderēti `data-*` vai slēptos elementos, ne JS virknēs), URL `#lens=` atcerēšanās. Sēdvietas klikšķis: desktop (≥768px) — popover blakus puslokam ar kartītes saturu (klonēts no saraksta rindas); mobilajā — apakšējā lapa (bottom sheet). Esc aizver, fokuss atgriežas uz sēdvietu, klikšķis ārpusē aizver. Hover/fokuss uz sēdvietas izceļ atbilstošo saraksta rindu un otrādi. Bez JS: enkurs aizved uz rindu sarakstā un atver tās `<details>` (`:target` CSS izcelšana).

## 4. uzdevums — izvēlne

`templates/base.html.j2`: augšējā joslā «Tēmas» vietā «Saeima» (`saeima.html`, `active_page == "saeima"`); «Tēmas» pārceļas uz «Vairāk» izvēlni (pirmā), un `'temas'` pievienots «Vairāk» pogas `active_page in [...]` sarakstam. Palaist `tests/test_render_chars.py` — ja bāzlīnijās mainās tikai izvēlne + jaunā lapa, REGEN; citādi STOP un ziņot.

## 5. uzdevums — pārbaude (orķestrators)

`bash scripts/check.sh` (pie «os error 1455» `CHECK_PYTEST_WORKERS=3`). Playwright: `saeima.html` 375px un 1280px, gaišs un tumšs, ar atvērtu kartīti; skatīties pašam. Pilns render fonā; T15 preflight — nav nepublicētu pārskatu melnrakstu.

## 6. uzdevums — dokumentācija, commit, push, deploy (orķestrators)

CHANGELOG (≤5 rindas), ideja → statusa rinda ar saiti uz spec, `wiki/operations/commands.md` `--only=saeima`, spec izvēlnes rinda. Commit caur `-F`, push, `bash scripts/deploy.sh`, live `saeima.html` + `assets/slv1.js` → 200.
