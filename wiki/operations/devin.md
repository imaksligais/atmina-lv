# Devin CLI (SWE-2) kā apakšaģents

> **Statuss: lietošanā.** Pirmā koda izmaiņa, kas caur to nonāca repo:
> `-e` uzvārdu datīvs (2026-09-22, commit `15ec5079`). Modeļu mērījums:
> `docs/eval/claim-extractor-models-v2-2026-09-16.md` (SWE-2 max 11,5/12).

Binārais fails: `/e/Devin/bin/devin.cmd` (Windows) — pārbaudi ar `devin --version`.

## Komanda, kas strādā

```bash
cd /e/atmina
/e/Devin/bin/devin.cmd --prompt-file .scratch/brief.md -p --model swe-2-max \
  --respect-workspace-trust false --permission-mode <režīms> > .scratch/run.log 2>&1 &
```

## Slazdi, kas maksāja laiku (2026-09-22)

**1. `-p "$(cat brief.md)"` sakropļo promptu.** Dubultpēdiņās bash izpilda
atpakaļēdiņas kā komandas, un brīfs ar `` `kods` `` atnāk sadrumstalots —
aģents atbild «uzdevums nav ierakstīts, kas jādara?». Lieto **`--prompt-file`**.

**2. Tiesību režīms nosaka, vai aģents vispār var strādāt:**

| Režīms | Ko atļauj | Kad der |
|---|---|---|
| `auto` | tikai lasīšana | evalu skrējieni (modelis tikai lasa un atbild) |
| `accept-edits` | + failu labojumi | **nepietiek** — pytest palaist nevar |
| `smart` | + ātra modeļa spriests «drošs» | noraida pat `.scratch/` skripta rakstīšanu |
| `dangerous` | viss | koda uzdevumi, KUR sagatavots atgriezeniskums |

**3. Pirms `dangerous`:** (a) `git status` tīrs un **pushots** uz origin;
(b) DB momentuzņēmums — `src.backup(dst)` uz `data/atmina.db.pre-<iemesls>-<datums>.db`
(2,6 GB, 8 s; retention: `wiki/operations/db-snapshots.md`). Pēc darba salīdzini
rindu skaitus — tā ir vienīgā pārbaude, kas pierāda, ka aģents DB neaiztika.

## Brīfa uzbūve, kas nostrādāja

Problēma ar konkrētu pierādījumu (doc ID) · ko izdarīt · **obligātie mērījumi**
(ieguvums + risks, ar prasību dažus trāpījumus izlasīt ar aci) · aizliegtais
(DB tikai `mode=ro`, nekādu commitu/deploy, tikai nosaukti faili) · vārti, ko
pašam jāpalaiž · atskaite. Beigās: «**negatīvs rezultāts ar pierādījumu ir
derīgs rezultāts**» — citādi aģents spiež izmaiņu cauri.

Paraugs: `docs/eval/brief-paraugs-2026-09-22.md`.

## Divi skrējieni, divi dažādi rezultāti (2026-09-22)

| | Uzdevums A (`-em` formas) | Uzdevums B (`db.py` junction) |
|---|---|---|
| Rezultāts | izmaiņa ieviesta | **uzdevums atteikts ar pierādījumu** |
| Atskaites kvalitāte | ieguvums 9× par mazu, nepareizs drošības apgalvojums | precīza; pati ievilka dzīvos rakstus ar `curl` |
| Blakus | — | atrada **orķestratora kļūdu** (BACKLOG indeksa drifte) un salaboja |

B gadījumā aģents nedarīja to, kas bija uzdots («noņem rindas, ko teksts
nepamato»), bet pierādīja, kāpēc tas nav droši, un ieviesa vājāko, godīgo
variantu (karogs). Tas ir labākais iespējamais iznākums — un tas notika tāpēc,
ka brīfā bija ierakstīts «**negatīvs rezultāts ar pierādījumu ir derīgs
rezultāts**» un atsevišķa sadaļa «slazds, kura dēļ naivs labojums ir bīstams».
Bez tā aģents būtu spiedis dzēšanu cauri, lai uzdevums izskatītos izpildīts.

*Mācība brīfa rakstīšanai:* ja tu pats zini, ka uzdevumā ir slazds, **ieraksti to
brīfā ar pierādījumu** (doc ID, ko pārbaudīt). Aģents to pārbaudīs un var
atteikties — tas ir mērķis, ne neveiksme.

Paraugi: `docs/eval/brief-paraugs-2026-09-22.md` (A), `brief-paraugs-B-2026-09-22.md` (B).

## Aģenta atskaitei netic — pārmēri pats

Tas nav formalitāte. 2026-09-22 SWE-2 atskaite saturēja:

- **ieguvumu 9× par mazu** — ziņoja 6 dokumentus (tikai Šnore), īstenībā 54 pāri
  5 politiķiem (Krauze 39, Pūce 5, Zīle 3, Daudze 1);
- **nepareizu drošības apgalvojumu** — «nulle viltus kandidātu», kaut doc 64701
  «Indriķim **Zīlem**» ir cits cilvēks. Secinājums («izmaiņa ir droša») sakrita,
  jo veto to noķer, bet pamatojums bija izdomāts.

Minimums pēc katra koda uzdevuma: `git diff` izlasīt pilnībā · testi · attiecīgais
audita skripts · DB rindu skaiti pret momentuzņēmumu · **pašam pārmērīt ieguvumu
un risku uz korpusa**.

## Paralēli: četri aģenti atsevišķos worktree (2026-09-23)

Sākumlapas uzlabojumiem (CHANGELOG 2026-09-23 (4)) četri aģenti strādāja
vienlaikus, katrs savā `git worktree` (`E:\atmina-wt\ui-<x>`, zars
`ui-landing-<x>`). Tā viens aģents nevar pārrakstīt otra labojumu tajā pašā
failā. Kas strādāja:

- **Renders no worktree** ar galvenā koka DB un venv:
  `env -u PYTHONPATH /e/atmina/.venv/Scripts/python.exe -m src.render --only=dashboard --db E:/atmina/data/atmina.db --output output`.
  `env -u PYTHONPATH` ir obligāts, citādi `src` imports aiziet uz `E:\atmina`.
  Pārbaude brīfā: `python -c "import src;print(src.__file__)"`.
- **Zonas brīfā:** katram aģentam nosauktas rindas veidnē, ko tas drīkst mainīt.
  Rezultāts: sapludinot nebija neviena konflikta kodā.
- **Viens konflikts tomēr būs:** `tests/fixtures/render_baseline_dashboard.json`,
  jo katrs aģents pats palaida `REGEN=1`. Atrisini ar jebkuru pusi un pēc
  sapludināšanas palaid `REGEN=1 pytest tests/test_render_chars.py` vēlreiz.
- **Bāzes līnija pirms palaišanas:** tīrā worktree pilns pytest (2889 passed)
  ļauj katru aģenta «4 failed» atšķirt no vecām kļūdām. Aģentu atskaitēs
  `test_deploy_script.py` krita, jo `--only=dashboard` neveido `_headers`.
  Pēc `--only=static` tie gāja cauri, tātad krišana nebija saistīta ar kodu.
- **Brīfa vārtos ieraksti arī `ruff check src scripts tests`**, ne tikai pytest.
  Aģenta A kods pytest izturēja, bet `check.sh` pirmajā solī krita uz UP034
  (liekas iekavas). To salaboja orķestrators, taču vārtiem tas bija jānoķer.
- Aģents C pamanīja, ka 14 atlikušie mazie mērķi atrodas B zonā, un apzināti
  tos neaiztika. Robežas brīfā strādā, bet spraugu starp zonām aizver orķestrators.
