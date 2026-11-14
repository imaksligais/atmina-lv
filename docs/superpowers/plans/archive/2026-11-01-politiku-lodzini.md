# Politiķu saites ar lodziņu «Atradumos» — plāns (2026-11-01)

Avots: `docs/arhivs/handoffs/HANDOFF-2026-11-01-politiku-lodzini.md`. Dizains apstiprināts sesijā; pārskatīts (advisor + Codex gpt-6.1-sol).

## Mērķis
Atraduma rakstā politiķa vārds (pirmā pieminēšana) = saite uz `../politiki/<slug>.html`. Dators: hover atver lodziņu, klikšķis → profils. Telefons: pirmais pieskāriens atver lodziņu ar «Profils →». Bez JS = parasta saite. Vēlāk tas pats dienas pārskatiem (`src/render/blog.py`, tā pati veidne).

## Lēmumi
- Saiti saņem TIKAI frontmatter `politicians:` uzskaitītie (pilni slugi). Atbilst pilnais `tracked_politicians.name` burtiski, ar vārdu robežām (`(?<!\w)…(?!\w)`), pirmajā *derīgajā* teksta vietā — ne `<a>`, `h1–h6`, `code`, `pre` iekšā. Vēlāka vienkārša pieminēšana paliek derīga. Nekādas uzvārdu meklēšanas (T1). Locītas formas («Linda Liepiņas») netiek saistītas.
- Neatrasts vārds → stderr brīdinājums ar saucēju (`listed / resolved / linked; nav atrasts: […]`), NE izņēmums (dienas rutīna nedrīkst krist teksta dēļ).
- Lodziņš: foto (ja `assets/photos/<slug>.jpg` eksistē) vai iniciāļi; vārds; partija ar partijas krāsu (`party_color_map`); `role_label` (garš teksts aplaužas, netiek griezts); pozīcijas · pretrunas · balsojumi ar `lv_plural`; «Profils →»; «dati uz <render datums LV>».
- Balsojumu skaits = tas pats, kas profila čipā (`politicians.py:628`, viss vēsturiskais, bez klātbūtnes). Rinda izlaista, ja 0. «Apmeklējums» nav ieviests — vietnē tāda rādītāja nav.
- Kiršteins/Žuravļevs/Štāls rakstā ir tikai kā uzvārds X avota saitē → bez lodziņa (raksta teksts netiek mainīts).

## Uzdevumi
1. **Resolve kopīgots.** No `src/render/syntheses.py::_map_syntheses_to_politicians` izvelk `_resolve_politician_token(tok, politicians) -> dict | None` (tā pati semantika: precīzs slugs vai `-sufikss`, divdomīgs → None + stderr). Abi izsaucēji to lieto.
2. **Linkeris** `src/render/_common/politician_links.py`: tīra funkcija `link_politicians(html, people, href_prefix="../politiki/") -> (html, report)`. `people` = jau sagatavotas vārdnīcas. `HTMLParser(convert_charrefs=False)` TIKAI atrod pozīciju (tagu steks izslēgumiem; `getpos()` → absolūtais indekss); `<a class="pol-link" …>` tiek iešūts ORIĢINĀLAJĀ virknē, nekas netiek pārserializēts. Katra `data-*` vērtība caur `html.escape(v, quote=True)`.
3. **Dati.** Orķestratorā viens grupēts vaicājums balsojumu skaitam (`GROUP BY politician_id`, `NOT_ATTENDANCE_SQL`), `party_color_map`, foto esamība → `render_analyses(..., pol_summaries=…)`. Linkeris tiek izsaukts uz `analysis["content_html"]` PIRMS `_add_h2_anchors`; ielādētājs netiek mainīts (indeksa izraksti neskarti).
4. **Veidne** `templates/blog-post.html.j2`: viens `<div id="pol-pop" class="seat-pop pol-pop" popover role="dialog" aria-label="Politiķa kopsavilkums">` un skripts tikai tad, ja lapā ir saites (konteksta karogs).
5. **JS** jauns `assets/polpop.js` (blv1 sēdvietu lodziņa stāvokļa mašīna, ~389–491): hover tikai `pointerType==='mouse'` + `(hover:hover) and (pointer:fine)`, 200 ms aizvēršanas taimeris, `toggle` notīra stāvokli. Klikšķis: `if (e.detail===0 || e.ctrlKey || e.metaKey || e.shiftKey || e.button) return;` → pele navigē; pieskāriens/pildspalva + `showPopover` pieejams → `preventDefault` + atver. Lodziņu pilda ar DOM/`textContent`. blv1.js netiek refaktorēts.
6. **CSS** `assets/style.css` pie `.seat-pop`: `.pol-link` (punktēta apakšsvītra), `.pol-pop-*` (foto/iniciāļi, partijas punkts caur `--party` custom property). `:hover` tikai `@media (hover:hover) and (pointer:fine)`. Vispirms `good-css` skill.
7. **Saturs**: `content/analizes/lsm-2026-skaitlos.md` `politicians:` = ansis-pupols, edvins-snore, arturs-butans, linda-liepina, jurgis-klotins, atis-svinka, leila-rasima, andris-suvajevs, inese-libina-egnere, zanda-kalnina-lukasevica, maris-mezals, viktors-valainis.

## Tests (pirms koda, jāredz krītam)
Viens DB-brīvs tests `tests/test_politician_links.py`, kas izmanto `link_politicians` ar fiktīvu `people` uz parauga HTML: (a) pirmā pieminēšana → saite ar pareizu href + escapotiem `data-*` (pēdiņas, `&`); (b) otrā pieminēšana neskarta; (c) vārds esošā `<a>` neskarts, vēlāka vienkārša pieminēšana saistīta; (d) ģenitīvs neskarts; (e) `&lt;b&gt;` entītijas saglabājas burtiski; (f) neatrasts vārds report sarakstā. CSP aizsargā esošie `test_no_inline_js.py` / `test_csp_external_hosts.py`.

## Pārbaude
`--only=` render analizes; `CHECK_PYTEST_WORKERS=3 bash scripts/check.sh`; Playwright ekrānuzņēmumi: dators (hover) + telefons 390 px (tap), gaišā un tumšā tēma. Deploy — tikai ar operatora atļauju.
