# Partiju tests — sākuma instrukcija izpildošajam aģentam (Muse) · 2026-09-20

Tu pabeidz projektu „Partiju tests” atmina repo (`E:\atmina`). Operators 2026-09-20 ir devis „jā” visam, kas šeit uzskaitīts. Lasi failus tieši šādā secībā — neko nedari pirms 1.–5. izlasīšanas.

## Lasi PIRMS jebkuras darbības (secība obligāta)

1. `CLAUDE.md` (repo sakne) — projekta operatīvā rokasgrāmata. Īpaši: § Standing Decisions (publiskā anonimitāte, publicēšanas pauze), § Working Conventions (klusais panākums = defekts; katrs vārts ar saucēju), § Commands (**vienmēr `.venv/Scripts/python.exe`, nekad `python`**; ceļi pēdiņās — mājas mapē ir atstarpe), § Escalation Rules 7–8.
2. `wiki/operations/portability.md` — ja neesi Claude Code: kā lasīt skills/agent-promptus kā procedūras; LV valodas vārts (pirmais skrējiens = dry-run).
3. `docs/plans/2026-09-17-partiju-tests-handoff.md` — kur stāvam, § 5 nepārjautājamie lēmumi, § 6 noteikumi izpildītājam.
4. `docs/plans/2026-09-20-partiju-tests-briefi.md` — **tavs darba uzdevums**: B1 → B2 → B3. B1 priekšnosacījums („jā” trim URL) ir izpildīts.
5. `docs/plans/2026-09-14-partiju-tests-v1-godigums.md` — pamatojums, šūnu shēma, vārti (§ 3.3–3.5, § 4). Lasi pilnībā pirms kodēšanas soļa B1.3.
6. Pirms B2: `wiki/operations/quality-bars.md` (render + deploy rinda) un `.claude/agents/quality-reviewer.md`.
7. Pirms B3: `wiki/operations/deploy.md` un CLAUDE.md T15.

Citu wiki lapu (arī `wiki/index.md`, ko CLAUDE.md prasa sesijas sākumā) šim uzdevumam NAV jālasa — tās ir dienas rutīnai. Ja kāds solis tomēr prasa lapu, kas šeit nav nosaukta, atver tikai to.

## Pirmā komanda, ko izpildi (pārbaude, ka sākumpunkts sakrīt)

```
.venv/Scripts/python.exe scripts/partiju_tests_validate.py --quiz-gate
.venv/Scripts/python.exe scripts/partiju_tests_audit.py
.venv/Scripts/python.exe -m pytest tests/test_partiju_tests.py tests/test_partiju_tests_audit.py tests/test_analyses_draft.py -q
```

Gaidāms: 168 šūnas (cvk 72 / pilna_programma 3 / izteikums 5 / klusē 88), vienīgā validatora kļūda `quiz: true skaits 0 < 8`, audits 2/12, 39 passed. Ja skaitļi atšķiras — APSTĀJIES un ziņo, nevis turpini.

## Ko drīkst un ko nedrīkst

- DB rakstīt drīkst TIKAI ar `scripts/ingest_url.py` un TIKAI trim URL no B1 tabulas. Viss cits — `mode=ro`.
- `content/partiju-tests/kodejums.json` raksti tikai pēc tam, kad priekšlikumi ir tabulā `kodejums_l2_priekslikumi.md` un tu pats esi pārbaudījis katru citātu ar `instr(content, citāts)`. Par/pret bez verbatim citāta nav.
- Neko nepublicē: B3 katrs solis (draft noņemšana, `--publish`, deploy) prasa atsevišķu operatora „publicē”. Viena atļauja ≠ nākamā.
- Quiz (U5–U7) neraksti — operatora lēmums „matrica tagad, quiz vēlāk” paliek, ja vien `--quiz-gate` pēc B1 nerāda ≥ 8 jautājumus.
- Pēc katra soļa: `grep -rl partiju-tests output/atmina | wc -l` = 0, kamēr nav B3.
- Katrs skaitlis ziņojumā ar komandu, kas to deva. Commit ziņas bez operatora identitātes, ar `Co-Authored-By` pēc CLAUDE.md. Commit pēc B1 un pēc B2 — atsevišķi.
- LV gramatika + stilistika katram jaunam tekstam pirms commit; ja par formu neesi drošs — pārfrāzē.

## Beigās

Ziņojums operatoram: B1 skaitļi (jaunie dokumenti + ID, jaunās šūnas, vārts pirms/pēc), B2 quality-reviewer verdikts, kas tieši gaida operatora apstiprinājumu (attēls, „publicē”). Atjaunini handoff § 1 un `BACKLOG.md` WIP rindu; CHANGELOG ≤ 5 rindas uz commit.
