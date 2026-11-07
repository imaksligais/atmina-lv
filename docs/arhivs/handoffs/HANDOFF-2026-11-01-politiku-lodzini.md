# Handoff 2026-11-01 — politiķu saites ar lodziņu «Atradumos»

**Uzdevums (operatora pieprasījums 11-01):** rakstos politiķu vārdi kļūst par saitēm uz profilu; datorā uzbraucot (hover), telefonā ar pirmo pieskārienu atveras lodziņš ar profila kopsavilkumu. Sākt ar «Atradumiem» — pirmais `content/analizes/lsm-2026-skaitlos.md`; dienas pārskati vēlāk ar to pašu mehānismu.

**Sākt ar plānu** (`superpowers:brainstorming` → `writing-plans`, advisor pie katriem vārtiem), tad viens Opus palīgs kodam, orķestrators pārbauda diff un renderēto lapu.

## Lēmumi (vienojāmies sesijā)
- **Kuri vārdi:** tikai tie, kas uzskaitīti frontmatter `politicians:` (lauks jau eksistē, šobrīd tukšs). Saite tikai **pirmajai** pieminēšanai rakstā. NEKĀDA automātiska vārdu meklēšana tekstā (T1 — «Kols» → «Kolumbija»).
- **Lodziņa saturs:** foto vai iniciāļi, vārds, partija (partijas krāsā), amats, pozīciju un pretrunu skaits, balsojumu apmeklējums, «Profils →». Rinda «dati uz <datums>».
- **Bez JS** vārds paliek parasta saite uz `politiki/<slug>.html`.
- **Paraugs:** Saeimas sēdvietu lodziņš — `assets/blv1.js` (~393–491, native `popover`, `showPopover({source})`), šablons `templates/balsojumi.html.j2`. Atkārtoti izmantot, nevis rakstīt no jauna.

## Ierobežojumi
- Stingrā CSP: JS tikai `assets/*.js` (`tests/test_no_inline_js.py`). Dati lodziņam — `data-*` atribūti vai ārējs JSON, ne inline skripts.
- `good-css` skill pirms CSS; mobile + desktop ekrānuzņēmumi; `:hover` tikai `@media (hover:hover) and (pointer:fine)`.
- T6: `tracked_politicians.party`/`role` var būt novecojuši (pēc 3.10. vēlēšanām) — pirms ieviešanas pārbaudīt LSM rakstā minētos; koalīcijai tikai `parties.coalition_status`.
- Attēlu atvasinājumu slazds (`backlog/vietne-ui.md` [FIX]): pēc PNG maiņas dzēst `<slug>-*.webp`/`-og.jpg` abās mapēs.
- Deploy tikai ar operatora atļauju; `approve_publish.py` jau ir LSM rakstam.

## Konteksts no šīs sesijas
LSM atradums publicēts (commits `500f3c1b`, vāks B `2f370f7a`), audita mape publiskajā spogulī (`docs/audits/2026-11-01-lsm/`), sākumlapas «Jaunākais» kārto vienādu datumu pēc `publish_approvals.approved_at`. Tvīti: `docs/tweet_bank/2026-11-01-lsm-2026-skaitlos-social.md` (nav likti).
