# Saites lapa un wiki grafs — dizains

**Datums:** 2026-10-18 · **Plāns:** `docs/superpowers/plans/archive/2026-10-18-saites-redizains.md`
**Izpētes avoti:** izpēte 2026-10-18 (Claude + GPT-6-Astra neatkarīgs priekšlikums + advisor; vietējās piezīmes `.scratch/saites-izpete/`, nav repo). Katram skaitlim zemāk ir vaicājums vai fails, kas to deva.

## Problēma (ar pierādījumiem)

1. **Matu kamols.** `saites.html` uzreiz zīmē 216 mezglus un 506 saites (D3 force). Mobilajā leģenda (`position:absolute` īsā panelī, `templates/saites.html.j2` `#graph-legend`) pārklāj grafu. *Avots:* `#saites-data` JSON no `output/atmina/saites.html`; ekrānuzņēmumi 390 px un 1400 px.
2. **Viens mezgls dominē.** Andris Kulbergs ir 178 no 986 saišu galapunktiem (145 kā mērķis); nākamais Šlesers 42. *Vaicājums:* `political_tensions` galapunktu `Counter` pa `source_pid`/`target_pid`.
3. **Mirusi poga.** «Balsojumi» filtram 0 saišu: `vote_alignment_data()` dod 9 034 pārus, neviens neatbilst sliekšņiem (`links.py` — citas partijas <25 %, savas partijas <50 %). «Kopīgās tēmas» pogai nav skaita (20 saites). 4. tips «Nostāju konflikts» (`TENSION_TYPE_LV`) nav grafa pogās.
4. **Dublikāts.** Tabula zem grafa (486 rindas) atkārto `spriedzes.html`, kas jau ir kartīšu reģistrs ar tiem pašiem 3 filtriem un labs mobilajā.
5. **Svars.** `saites.html` 1,2 MB (inline JSON) + `data/saites-data.json` 4,3 MB + `saites-votes.json` 11,7 MB (lazy).
6. **Spriedzes partiju filtrs skatās tikai uz autoru.** `templates/spriedzes.html.j2:71` `data-party="{{ t.source_party }}"` → izvēloties «AS», neredz spriedzes, kur AS ir adresāts. Spriedzes lapa nelasa URL parametrus (`assets/spv1.js`, 31 rinda) → filtrētu skatu nevar nosūtīt.
7. **Skaitļi bez skaidrojuma.** DB 493 rindas, lapā 486 (1 `target_pid IS NULL` + dalībnieki ar `relationship_type IN ('inactive','commentator')`, `src/render/tensions.py::_fetch_tensions`), grafā 506 (= 486 + 20 kopīgās tēmas). Tas ir publiskais līgums, ne defekts — bet lasītājam tas jāpasaka.

## Kas jau ir (atkārtoti izmantot, nebūvēt no jauna)

- **Politiķa profila «Saites» cilne** (`templates/politician.html.j2:774+`, `src/render/politicians_tabs.py::_saites_neighbors_with_coords`): servera SVG mini-grafs līdz 8 kaimiņiem, 0 JS, klikšķis → `#saites-{pid}` kartīte ar kontekstu (spec `2026-05-02-saites-tab-click-focus-design.md`). **Tas jau ir «ego-tīkls».** Jaunā Saites lapa uz to ved, nevis zīmē savu.
- `sav1.js` jau prot URL stāvokli, iezīmēšanu, kaimiņus — pilnais grafs paliek, tikai ne kā noklusējums.
- `atminaMultiSelect` (`assets/msv1.js`) — filtru komponents abām lapām.

## Lēmumi

1. **Noklusējuma skats vienāds abos ekrānos:** ievads ar saucējiem (N saiknes · M politiķi · periods · kas skaitās saikne) → politiķa meklētājs (ved uz profila Saites cilni) → partiju saraksts (`<details>` katrai partijai; atverot — tās pāri «A → B · n» ar saiti uz profila kartīti `politiki/{a}.html#saites-{b_pid}`). 0 JS šim slānim.
2. **Pilnais tīkls** — poga «Rādīt visu tīklu»; D3 + `sav1.js` + grafa JSON ielādējas tikai pēc klikšķa. Leģenda zem grafa, ne virs.
3. **Tabula no Saites lapas pazūd**, tās vietā saite «Visas N saiknes sarakstā →» uz `spriedzes.html`. *Operatora apstiprinājums vajadzīgs sesijas sākumā* (ārēji redzama izmaiņa).
4. **Spriedzes lapa** iegūst URL parametrus `type`, `party`, `person` (tie paši nosaukumi kā `sav1.js::syncUrl`), un partijas filtrs atbilst jebkuram galapunktam.
5. **Pogas tikai ar saturu:** grafa tipu pogu renderē tikai, ja tipam ir >0 saišu; katrai pogai skaits.
6. **Partiju matrica (autors × adresāts)** — NAV MVP. Atgriezties pie tās tikai pēc MVP apskates un pēc Kulberga parauga (matrica pastiprina vienu kolonnu).
7. **Pele: šobrīd neizmantot.** Tā zīmē Mermaid shēmas (nevar 216 mezglu tīklu); ego-tīkls jau ir servera SVG; Obsidian Mermaid renderē pats. Mūsu būvē nav Node. Pārskatīt tikai, ja analīžu rakstiem vajag shēmas no teksta.
8. **Neitralitāte:** nekādu «kurš uzbrūk visvairāk» rangu; partiju sarakstu kārto alfabētiski, pārus — pēc jaunākā ieraksta, ne pēc skaita; katram skaitlim blakus saucējs.

## Wiki (Obsidian) — lēmumi

Fakti (`wiki/`, 628 `.md`, 1 133 wikilinki): 255 lapām (dailies 194, weeklies 25, synthesis 11) nav saišu, un `graph.json` `showOrphans:false` tās slēpj; `operations/` + 3 CHANGELOG (arhīvs 702 KB) tajā pašā grafā; `topics/*` `top_politicians` ir teksts, ne saites; 25 datumi gan `dailies/`, gan `weeklies/`; `graph.json` krāsu dublikāts (`index.md` un AS = 16498468); 0 Mermaid, 0 Canvas, nav kopienas spraudņu.

1. `graph.json`: meklēšanas filtrs izslēdz `operations/`, `log-ingest/`, `CHANGELOG*`, `log-ingest.md`, `project-brief.md`; krāsu dublikāts salabots.
2. `topics/*` frontmatter `top_politicians` → wikilinki uz esošām personu lapām (ģeneratorā; inactive → teksts).
3. `politiki.base` jauns skats «Maz pārklāti» (esošie lauki).
4. NEdarīt: wikilinki sintēzēs (aizliegti — `tests/test_synthesis_no_wikilinks.py`, tās renderējas publiski); vārdu meklēšana pārskatu tekstā saišu radīšanai (T1); Mermaid/Canvas visam tīklam; kopienas spraudņi.
5. Dailies/weeklies saites tikai, ja DB ir strukturēta dalībnieku saite uz pārskatu — plāna B4 pārbauda; ja nav, ieraksts backlogā, ne kods.
