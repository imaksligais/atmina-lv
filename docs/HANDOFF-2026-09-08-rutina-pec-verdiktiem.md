# Nodošana: nākamā rutīna pēc verdiktu izpildes (2026-09-07)

> **IZPILDĪTS 2026-09-06 vakarā** (commit `fedf1e05`, CHANGELOG «2026-09-06 (rutīna)»). Rezultāti pa rindām — § Izpilde zemāk. Šis fails vairs nav to-do.

**Stāvoklis:** 2026-09-06 verdikti izpildīti (CHANGELOG 2026-09-07 (1)–(11), pēdējais commit `2f3fa0bc`). Kokā stāv **nedeployotas** izmaiņas — šī rutīna ir pirmā, kur jaunie ceļi darbojas dzīvē. Rutīnu vada `/dienas-rutina` kā parasti; zemāk tikai tas, kas šoreiz ir citādi.

## Obligāti šoreiz

- **8. solis = PILNS renders, ne `--only`.** Nedeployots: avota etiķete no `source_domain` (pmo.ee → tvnet.lv), Nozīmīguma vārdi (09-06), profila tēmu filtrs (09-07), profilu sintēžu sīktēli, divi jauni profili (Pujāts pid 246, Freifalts pid 247), 4 atsauktas pozīcijas (#689743, #689646, #703870, #704024 — `output/` tās vēl nes; deploy PIRMS rendera aiznestu dzēsto uz live).
- Pirms deploy: `grep -rl "pmo.ee" output/atmina/temas/ | wc -l` = 0; `grep -l "689743\|703870" output/atmina/politiki/*.html` = nekas.

## Pārbaudes ar mērījumu (pieraksti CHANGELOG, arī ja zaļš)

| Solis | Ko skatīties | Gaidāms |
|---|---|---|
| Ingest kopsavilkums | rinda «N no M web dokiem ar nogrieztu ievadu» | rinda ir; N=0 bez diena.lv dokiem ir aizdomīgs |
| Pēc ingest | `SELECT COUNT(*) FROM document_politicians WHERE politician_id=195 AND role='subject' AND document_id IN (SELECT id FROM documents WHERE DATE(scraped_at)=DATE('now','localtime'))` | 0 (relay slots `subject` vārts, CHANGELOG (7)) |
| Pēc ingest | junction rindas pid 246, 247 dienas dokiem; Freifalta doki nav pid 234 slotā | ≥0, bet Toro slots bez Freifalta |
| Rutīnas statuss | «📜 VĒSTNEŠA AKTI» rinda ar saucēju «N no M» | rinda ir; tukša = Vēstnesis ienāca pēc rutīnas (backlog ieraksts) |
| Rutīnas statuss | confidence drift brīdinājums tikai ar «n A → B», klusē n<5 | |
| Ekstrakcija | pid 209 Štekerhofs pirmo reizi rindā (doc 90283; tajā arī Kulberga un Rokpeļņa pozīcijas — per-dokumenta `reviewed_at` slazds) | pieraksti, kuru politiķi zīmogs sedz |
| Ekstrakcija | jaunām NEEDS_REVIEW rindām `review_status_at IS NOT NULL` | trigeris strādā (šodien visām NULL) |
| Attēls | `image_audit` +1 rinda `kind='brief'` ar cenu pēc `generate_image()` | mēneša summa aug tieši par to |
| Pēc deploy live | profila filtrs tumšajā tēmā, «Vēl N tēmas» mobilajā, `?tema=Pensijas` uz sakļautu tēmu | skatīts tikai gaišajā desktop |
| Pēc rutīnas (neobligāti) | `/audit-integrity` | 13. pārbaude rādīs 150 `saeima_vote` stale — zināms, backlog; 6. pārbaudi nelasīt kā bāzlīniju |

Ja kas krīt — tas ir vērtīgāks par zaļu: CHANGELOG rinda ar vaicājumu, backlog ieraksts ar trigeri + rīcību.

## Gaida operatoru (ne rutīnas darbs)

~~`BACKLOG.md` § Atliktais pēc 2026-09-06 verdiktiem: Zīles `negative_patterns`, 17 ASCII name_forms, vēsturiskā `subject` demotēšana (3 027 rindas), pirmais `python -m src.csp --apply`, citātu triāžas sesija, video.~~ **Izlemts 2026-09-06 vakarā:** Zīle, demotēšana, `csp --apply` un 6 dienas `needs_review` rindas izpildītas; name_forms noraidīts; paliek citātu triāža un video (CHANGELOG «2026-09-06 (2)»).

## Zināmie slazdi (nemainīti)

`morning_ingest.py --help` klusi beidz ķēdi; variantu vārta PNG glob; ingest ~15 min > Bash timeout → fonā.

## Izpilde 2026-09-06 (rezultāti pa rindām)

| Solis | Iznākums | Statuss |
|---|---|---|
| Ingest kopsavilkums | «Nogriezts ievads: 0 no 63 web dokiem»; diena.lv 4 doki, 0 nogrieztu | zaļš |
| pid 195 `subject` | Handoff vaicājums (pēc `scraped_at`) deva **3**, ne 0 — visas 3 rindas rakstītas 09-04/09-05 pirms labojuma; web doki pārrakstīti (URL-first UPDATE reseto `scraped_at`), šodienas ceļš pievienoja `mentioned`. Pēc `document_politicians.created_at`: **0 no 99** šodien rakstītām `subject` rindām ir LETA, 0 biroja balss RT. **Vaicājumu lasa pēc `created_at`.** Blakus: PK `(document_id, politician_id, role)` pieļauj `subject`+`mentioned` vienam pārim — 3 376 pāri korpusā, E1 demotēšana tos aizvērtu | zaļš (vaicājums labots) |
| pid 246/247 junction | Šodien 0 jaunu rindu (kopā 246: 9 subject / 15 mentioned; 247: 2 / 7); Freifalta doki Toro (234) slotā — 0 | zaļš |
| «📜 VĒSTNEŠA AKTI» | «0 no 0» — svētdiena, Vēstnesis `stored=0` | zaļš |
| Confidence drift | Klusē (n<5) | zaļš |
| Štekerhofs 90283 | `get_pending_politicians(days=1)` doku **nedeva** (rinda ir dienas logā, doks 08-19) — dispatchēts ar roku. Zīmogs sedz visus trīs: 209 → #709106 NEEDS_REVIEW (balsojuma fakts bez izteikuma); 126 Rokpelnis — dublikāts pret #690470; 10 Kulbergs — jau #703970 | zaļš, ar backlog ierakstu |
| `review_status_at` | 6 no 6 jaunajām `needs_review` rindām NOT NULL | zaļš |
| `image_audit` | #317 `kind='brief'` 0,039 USD; mēnesis 0,624 → 0,663 | zaļš |
| Live profila filtrs | 390 px + `data-theme=dark`: sakļauts 13 čipi + «Vēl 20 tēmas», klikšķis atver 32; `?tema=Pensijas` atver grupu un iezīmē čipu; 0 konsoles kļūdu | zaļš |
| Pre-deploy `pmo.ee` grep | **21**, ne 0 — tas ir `href`, ne etiķete; redzamā `>pmo.ee<` = 0, `tvnet.lv ↗` = 2 live | zaļš (grep bija par rupju) |
| Atsauktās 4 pozīcijas | `output/` 0, live profilos 0 | zaļš |
| `check.sh` | KRITA: `test_politiki_detail_pages_byte_identical` — 2f3fa0bc nepārģenerēja `render_baseline_politicians.json`; REGEN, 24/24 | labots |
| `@quality-reviewer` | BLOCKED: spriedze #267 «tajā pašā dienā» nepatiess; labots 3 vietās ar `data/rollback_tensions_267_268_brief_546_2026-09-06.sql` | labots |
| Variantu vārts | Skripts glabāja PNG glob deploy kokā (renders kopē tikai variantus) → 0; `/dienas-rutina` labots (PNG no `output/images/briefs`) | labots |
