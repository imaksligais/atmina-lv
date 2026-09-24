# D1 — akla pārkodēšana: protokols kodētājam (K1 / K2 / K3)

Konteksts un noteikumi: `docs/plans/2026-09-20-partiju-tests-v2-briefi.md` § 3 un § D1. Šis fails ir viss, kas tev jāzina; **nelasi** `content/partiju-tests/kodejums.json`, `kodejums_draft.md`, `kodejums_l2_priekslikumi.md`, `l3/`, `partiju-tests.draft.html`, `docs/plans/*partiju-tests*` (izņemot v2 brīfu § 3) — tavs lasījums jābūt neatkarīgs. Ja kaut ko no tā esi atvēris, pasaki ziņojumā.

## Uzdevums

12 apgalvojumi (`content/partiju-tests/jautajumi.yaml`: `apgalvojums` + `piekrit_nozime`) × 14 saraksti (`saraksti.yaml`: `short_name`) = 168 šūnas. Katrai šūnai `par` / `pret` / `klusē` TIKAI no partijas programmas teksta datubāzē.

## Vide

- Windows, bash; `.venv/Scripts/python.exe` no repo saknes; ceļi pēdiņās.
- DB tikai lasīšanai: `sqlite3.connect('file:data/atmina.db?mode=ro', uri=True)`. Nekā nerakstīt DB, git, citos failos.
- Pagaidu skripti tikai `scratchpad/d1-<K>/`.

## Dokumenti (nolasi abus pilnībā katrai partijai)

| SN | CVK doc | pilnā programma doc |
|---|---|---|
| SV-AJ | 65207 | 112125 (22 907 z., `recall` variants — noklusējums deva 0) |
| MMN | 63386 | 112117 |
| SC | 62702 | nav — programma nav publicēta |
| ZZS | 64220 | 112118 |
| NA | 62701 | 62113 |
| GS | 63385 | 112120 |
| AS | 63383 | 112121 |
| LPV | 62698 | 112122 |
| JV | 62696 | 107753 |
| JKP | 63384 | 107754 |
| LA | 64221 | 112114 |
| ASL | 62700 | 112123 |
| ST | 62699 | 112126 (6 040 z., `recall` variants — noklusējums deva 0) |
| PRO | 62697 | 112124 |

`SELECT content FROM documents WHERE id=?`. CVK dokuments satur arī kandidātu sarakstu — programma ir tā daļa (~4000 zīmju).

## Kodēšanas likumi

1. `par`/`pret` tikai tad, ja teikums adresē apgalvojumu tieši pēc `piekrit_nozime`. **Hedžings nav nostāja** („līdzsvarota, saprātīga politika” = klusē). Secinājums no pieņēmuma (kaut kas *presuponē* nostāju) = klusē. Robeža ir vienādi stingra abām pusēm.
2. Citāts verbatim (arī ar autora kļūdām), ≤ 300 zīmes, un pārbaudīts: `SELECT instr(content, ?) FROM documents WHERE id=?` > 0. Bez pārbaudīta citāta nostājas NAV.
3. Ja abi dokumenti dod nostāju — ņem CVK (`avots: cvk`); pilno programmu (`avots: pilna_programma`) tikai tur, kur CVK klusē. Ja CVK un pilnā programma ir pretrunā — `klusē` + piezīme ar abiem citātiem.
4. `klusē` piezīme: viens latviešu teikums — ko programma tēmā saka (vai ka nemin) un kāpēc tas nostāju nedod. Bez vērtējošiem vārdiem.
5. CVK šūnai `claim_id`: `SELECT id FROM claims WHERE claim_type='program_promise' AND party_id=(SELECT id FROM parties WHERE short_name=?) AND document_id=?` — izvēlies to, kura `quote` pārklājas ar tavu citātu; ja nav — `"claim_id": null` un piezīme „claim nav; citāts dokumentā ir”.
6. Līderu izteikumus, ziņas, X — NEmeklē. Tikai programmas teksts.
7. Latviešu valoda savos vārdos ar gramatikas un stila pārbaudi.

## Izvade — divi faili, nekas cits

`content/partiju-tests/d1/<K>.json` — tāda pati forma kā oficiālajam kodējumam:

```json
{"q01": {"SV-AJ": {"nostaja": "par", "avots": "cvk", "claim_id": 123, "citats": "…", "url": "<cvk_url no saraksti.yaml>"},
         "MMN":   {"nostaja": "klusē", "piezime": "CVK: … ; pilnā programma: …"},
         "LA":    {"nostaja": "pret", "avots": "pilna_programma", "document_id": 112114, "citats": "…", "url": "<pilna_programma_url>"}},
 "q02": {…}}
```

Visas 12 × 14 šūnas obligātas — saskaņas skripts (`scripts/partiju_tests_saskana.py`) krīt pie pirmās trūkstošās.

`content/partiju-tests/d1/<K>.md` — saucējs: dokumenti izlasīti N (CVK 14, pilnās M), šūnas 168, sadalījums par/pret/klusē, `instr`-pārbaudīti citāti N no N, un līdz 10 šūnas, kur tev pašam bija grūti izšķirties (ar vienu teikumu kāpēc).
