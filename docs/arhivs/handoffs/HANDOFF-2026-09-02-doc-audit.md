# Handoff — dokumentācijas audits (2026-09-02)

> **Statuss 2026-09-07:** vēsturisks. STOP rindas par politiķu lapu renderu ATCELTAS 2026-09-05 (CHANGELOG 2026-09-05 (4), Ceriņa lēmums); pārējie atradumi izlemti verdiktu kārtā 2026-09-06 un izpildīti 2026-09-07.

## Mērķis

Nolasīt `CLAUDE.md`, `wiki/`, aktuālos handoff un backlog failus; fonā palaist ikdienas ingest; ar Terra apakšaģentiem analizēt visu dokumentāciju; secinājumus un nākamos soļus saglabāt tā, lai darbu var turpināt jaunā sesijā.

## Drošības robežas

- Nekas netiek publicēts vai deployots.
- Esošie neizsekotie `data/` faili pieder operatoram un netiek mainīti.
- `wiki/synthesis/` ir ar roku rakstīts saturs; audits to drīkst lasīt, bet ne automātiski pārrakstīt.
- Šis ir audits, nevis automātiska visu atrasto problēmu labošana.

## Progress

- [x] Nolasīts repozitorija saknes failu saraksts un git statuss.
- [x] Atrasts un sākts lasīt `CLAUDE.md`, `wiki/index.md`, `wiki/operations/operacijas.md`, `BACKLOG.md` un `docs/HANDOFF-2026-08-28.md` (fails dzēsts 2026-09-05 — dzīvās rindas § „Live items” zemāk).
- [x] Identificēts kanoniskais ikdienas ingest entrypoint: `scripts/morning_ingest.py`.
- [x] Palaists fona ingest noturīgā termināļa sesijā; vēl jāpārbauda gala rezultāts.
- [x] Dokumentācija sadalīta trim Terra aģentiem; pilnie inventāri top viņu rezultātu failos.
- [x] Saņemti un diskā saglabāti visi trīs pabeigtie Terra auditi.
- [x] Aģenti būtiskos secinājumus pārbaudīja pret kodu, lokālo output un dokumentu inventāru; DB mutācijas netika veiktas.
- [x] Sagatavots prioritizēts turpinājuma saraksts zemāk un detalizētajos auditos.

## Fona ingest

- Statuss: PABEIGTS; visi 5/5 soļi OK, exit code `0`.
- RSS rezultāts: 11/11 avoti OK, 0 kļūmju, 114 dokumenti; ilgums 1003.5 s.
- `fetch_all_twitter` OK 557.9 s; `fetch_all_mentions` OK 72.1 s; Vestnesis OK 95.8 s (33 saglabāti, 0 izlaisti, 0 kļūmju); backstop linking OK 1.4 s.
- Gala marķieris: `KOPSAVILKUMS: 5/5 soļi OK` / `ALL DONE`; exit code `0`.
- Palaišanas komanda: `$env:UV_CACHE_DIR='E:\atmina\.scratch\uv-cache'; $env:UV_PYTHON_INSTALL_DIR='E:\atmina\.scratch\uv-python'; uv run --python 3.12 python scripts\morning_ingest.py`.
- Iemesls `uv` TAJĀ sesijā: `Test-Path` uz `.venv/Scripts/python` (bez `.exe`) atgrieza `False`, un tas tika nolasīts kā salauzts launcher.
- **Atspēkots 2026-09-05:** `.venv/Scripts/python.exe --version` → **Python 3.12.10**, un `import src.db, src.analyze, src.briefs, src.routine` iziet. `.venv` STRĀDĀ; `uv` apvedceļš nav vajadzīgs un turpmāk nav jālieto — kanoniskais izsaukums paliek `.venv/Scripts/python.exe` (`wiki/operations/commands.md:14`).

## Aģentu sadalījums

- `ops_docs_audit` (Terra): `CLAUDE.md`, `wiki/operations/**`, saknes tehniskie dokumenti, `.claude` instrukcijas → `docs/audits/terra-ops-docs-2026-09-02.md`.
- `backlog_handoff_audit` (Terra): `BACKLOG.md`, `backlog/**`, `docs/**` un visi handoff/plāni → `docs/audits/terra-backlog-handoff-2026-09-02.md`.
- `wiki_content_audit` (Terra): viss `wiki/**`, ieskaitot ģenerēto un manuālo saturu → `docs/audits/terra-wiki-content-2026-09-02.md`.

## Starprezultāti

### ~~STOP pirms jebkāda deploy~~ — ATCELTS 2026-09-05 (operatora lēmums: #704196 paliek un drīkst būt publiska; lapa jau bija live kopš 09-04 deploy)

- `#704196` (Aivis Ceriņš) jau atrodas lokālajā `output/atmina/politiki/aivis-cerins.html` trīs virsmās, lai gan backlog nosaka politiķu lapas nerenderēt līdz operatora verdiktam. Nav pierādījuma, ka tas ir deployots, bet nākamais deploy ir jāaptur līdz eksplicītam lēmumam.

### P0 operāciju dokumentācija

- Runbooki konfliktē par paralēlo ekstrakciju: dažviet iesaka dalīt viena politiķa dokumentus, bet aktuālais drošības noteikums prasa dalīt pa politiķiem.
- `claim-extractor.md` vienā vietā kļūdaini apgalvo, ka `save_analysis(claims=[])` vien pats atzīmē dokumentu kā reviewed; kods prasa `empty_doc_ids` jau izlasītiem, patiesi tukšiem dokumentiem.

### P1 darba rinda

- Toro/Gobzema `name_forms` piesārņojums: 64 no 88 junction rindām ir kļūdainas.
- `doc 95002` ir fantoma `subject` saite bez personas vārda tekstā.
- `pmo.ee` avota etiķete joprojām tiek atvasināta no URL, ne normalizētā `source_domain`.
- Wiki indeksa saucēji nesakrīt (`167` pret `196`; pozīciju starpība `52`) un jāizskaidro vai jāsalabo ģeneratorā.
- Ir 418 `ingest_url.py` web dokumenti bez chunkiem; tie nav semantiskajā meklēšanā.

### Dokumentācijas novecojums

- VAD Phase 1.5 handoff norāda uz dzēstu zaru/worktree, lai gan darbs ir merge/deploy vēsturē.
- Vecs `claim_type` plāns joprojām saka “Not started”, lai gan funkcionalitāte ir kodā.
- Video ceļš vairākos dokumentos saukts par operacionālu, bet `CLAUDE.md` korekti norāda: stop-gate testēts, produkcijas happy path nav lietots.
- `CLAUDE.md` T9 saka, ka vote claims ir vektorizēti, bet kopš 2026-08-21 jaunie `saeima_vote` vektorus nesaņem; vēsturiskie var palikt.

### Detalizētie nodevumi

- `docs/audits/terra-ops-docs-2026-09-02.md`
- `docs/audits/terra-backlog-handoff-2026-09-02.md`
- `docs/audits/terra-wiki-content-2026-09-02.md`

### Ieteiktā turpinājuma secība

1. Saņemt operatora verdiktu par #704196 un līdz tam neveikt deploy/politiķu renderu.
2. Salabot abus P0 operāciju instrukciju konfliktus un pievienot regression pārbaudes.
3. Labot matcher piesārņojumu un `doc 95002` tikai ar projekta rollback/approval guardrail.
4. Salabot avota etiķeti, wiki saucējus un dokumentu chunking robu.
5. Ar vienu docs-only izmaiņu vilni sakārtot novecojušos handoff/plānus, vote-vector/video statusa tekstus un nederīgos Python/deploy ceļus.

## Atsākšana jaunā sesijā

1. Izlasi `CLAUDE.md`, `wiki/index.md` un šo failu.
2. Pārbaudi `git status --short`; nepārraksti operatora neizsekotos `data/` failus.
3. Apskati aģentu rezultātu failus, kas norādīti sadaļā “Aģentu sadalījums”.
4. Turpini no pirmās neatzīmētās Progress rindas.

## Live items no `docs/HANDOFF-2026-08-28.md` (fails dzēsts 2026-09-05)

08-28 handoff pārējais saturs bija tās dienas stāvokļa momentuzņēmums un ir novecojis. Divas rindas bija joprojām dzīvas, tāpēc tās pārceltas šurp, nevis izmestas:

1. **#704196 (Aivis Ceriņš) — STOP pirms politiķu lapu rendera.** Rinda paliek DB ar `needs_review`; pārskatos un sociālajos melnrakstos tās nav. Bet `output/atmina/politiki/aivis-cerins.html` to nes, un `--only=politiki` vai pilns renders publicētu GAN pozīciju, GAN neapstrādāto tvītu X apakšcilnē, kurai apslāpēšanas karoga nav (CLAUDE.md § *Deleting a claim does NOT remove its source document*). **Nerenderē politiķu lapas, kamēr nav operatora verdikta.** Tas pats fiksēts augstāk § „STOP pirms jebkāda deploy".
2. **`check.sh` izsaukuma forma apēd izejas kodu.** `bash scripts/check.sh > log 2>&1; echo "EXIT=$?"; grep …` — `$?` paņem `grep` kodu, harness ziņo „exit 0", kamēr `check_output` ir kritis. Vienīgais, kas to noķēra, ir 2026-08-27 pievienotais `trap … EXIT` banneris: krītot pēdējā izvada rinda ir `==> CHECK FAILED (exit N)`, zaļumā — `==> all checks passed`. **Lasi pēdējo rindu, ne izejas kodu.** Cauruli (`| tail`) skripts salabot nevar; to labo izsaukuma forma.
