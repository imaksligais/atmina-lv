# Handoff 2026-11-01 — rutīna, tad politiķu lodziņi dienas pārskatos

**Secība (operatora lēmums 11-01):** 1) šīs dienas rutīna + dienas pārskats (`/dienas-rutina`, publicēšana ar atļauju); 2) pēc tam politiķu lodziņi dienas pārskatos.

## Jau izdarīts
Atradumos lodziņi live (commit `65715b99`, deploy `ec708fbb`): `link_politicians()` `src/render/_common/politician_links.py`, `assets/polpop.js`, `.pol-*` `assets/style.css`, lodziņš `templates/blog-post.html.j2` (ieslēdz `pol_asof`), dati `_politician_summaries()` `src/render/_orchestrator.py`. Lēmumi — `wiki/CHANGELOG.md` 2026-11-01 (5), plāns `docs/superpowers/plans/2026-11-01-politiku-lodzini.md`.

## Pārskatiem (ierosināts, operators vēl nav apstiprinājis)
- Saraksts = politiķi ar `claim_type='position'` pozīcijām vai pretrunām attiecīgajā RUTĪNAS dienā (`routine_day_window`); pārskatiem frontmatter nav, šobrīd tajos 0 profila saišu.
- Tikai dienas pārskati (`blog-post.html.j2`); nedēļas (`_weekly_body.html.j2`) — vēlāk.
- Pārrenderējot saites parādās arī vecajos publicētajos pārskatos (teksts nemainās) — deploy tikai ar atļauju.
- Darba gaita kā Atradumiem: īss dizains → operatora «jā» → plāns → viens Opus palīgs → diff + ekrānuzņēmumi pašam.

## Rutīna 11-01 — PABEIGTA (deploy `23d5b071`)
36+2 pozīcijas, 0 pretrunu (36/36, 15/15), 4 spriedzes, 3 piezīmes, pārskats #776 publicēts. Rollbacki: `f18a2d45`, `c0aa19fc`, `2901b5e3`.

**Atvērts operatoram:**
- 5 NEEDS_REVIEW: 752800 Štāls, 752811 Velps (uz tā paša tvīta balstās publicētā spriedze #581), 752816 Žuravļevs, 752819 Baško, 752823 Kols (iespējams 747403 atkārtojums; nedzēsts — T19).
- 15. Saeima 11-03: `role` neturpinošajiem deputātiem, `parties.coalition_status` pēc valdības apstiprināšanas, `seed_coalition_periods.py` (BACKLOG.md [OPERATOR] rindas).
- Bezpartejisko pieraksts nav vienots: 7 rindas `party='Bezpartejisks'`, pārējās NULL (piem., Ābrama) — konvencijas lēmums.
- 12 nekomitēti `docs/social/`, `docs/tweet_bank/` faili (10-30…11-01) — komitēt vai dzēst (publiskais spogulis).
- Nedēļas pārskats: pēdējais 10-05…10-11 — apzināta pauze vai atsākt?
- `scripts/backup_db.py` ap 11-03 (iknedēļas).

**Pārbaudīts, NAV defekts:** doks 148096→Kols (`mentioned`) — Kols to pašu Valtonenas tvītu retvītoja (bare-RT dedup, `src/db.py:526`); balsojums 8541 — 75 rindas = Saeimas kopsummas 8+41+22+4.

**Jauns defekts:** B2 veto garumzīmes → `backlog/matcher.md` (2026-11-01).

## Nedēļas pārskats «Nedēļas stāsti» — IEVIESTS 11-02, pilots saglabāts
Spec/plāns `docs/superpowers/{specs,plans}/2026-11-01-nedelas-stasti*.md`; kods `560478ce…29c068ee`, `check.sh` zaļš. «atkārtojas» slieksnis 3 dienas (joprojām 23/35 — tēmas par plašām; promptā piezīme).
**Pilots #777** (`nedēļas analīze 2026-10-26 līdz 2026-11-01`, NEPUBLICĒTS): 5 stāsti, 928 vārdi (pret 1 452 #699), lint 7/7, ~225 tūkst. tokenu (10-11 bāzes nav). Izmest = `DELETE FROM context_notes WHERE id=777` (ar rollback failu). Publicēšanai: operatora korektūra, QR § H, featured image, `approve_publish.py nedela-2026-10-26`, atļauja.
**Datu defekts:** pozīcijām 747688 (Līdaka) un 747689 (Judins) identisks stance no viena dokumenta 144520 — viena piedēvēta nepareizi; pārskatā nav citētas. Jāizšķir pēc avota.
`followup` šonedēļ tukšs pēc konstrukcijas (10-19…10-25 nedēļas pārskata nav).
**11-02 PUBLICĒTS:** #777 = `/blog/nedela-2026-10-26.html`, attēls #428 (`stories`, 427/429/430 noraidīti), deploy versija `0bec2aec`, verify_host 9/9. Nedēļas attēla noklusējums tagad `stories` bez teksta. Nākamais nedēļas pārskats: pirmdien 11-09 par 11-02…11-08.
