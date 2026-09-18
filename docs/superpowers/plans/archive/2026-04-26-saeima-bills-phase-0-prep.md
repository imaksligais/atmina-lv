# Saeima Bills — Phase 0 Prep Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Aizvākt 5 dizaina flaws no `docs/superpowers/specs/2026-04-22-saeima-bills-design.md`, kas atklāti pēc real-data audita 2026-04-26, lai Phase 1 implementācija balstās uz ticamu datu pamatu un pilnu stage vocabulary, neaiztverot Phase 3 (debates) hooks.

**Architecture:** Doc-heavy work (5 no 6 task-iem ir spec edit) + viens read-only audit script kā guardrail. Visas izmaiņas master spec ir tieši uz `docs/superpowers/specs/2026-04-22-saeima-bills-design.md` ar versijas annotation footnote ("Phase 0 prep applied 2026-04-26"). Audit skripts iet `scripts/audit_saeima_vote_results.py` un kļūst par routine sanity check.

**Tech Stack:** Python 3.11 + pytest (audit script), Markdown spec edits, SQLite read-only queries.

**Konteksts (audit findings 2026-04-26):**
- 139 saeima_votes rindas (spec assumed 113), 105 ar `document_nr` (75%), span 2026-03→2026-04
- Stage classifiable: 67% (lasījumi + priekšlikumi), **33% nezināms** — pie spec § 5.4 30% sliekšņa
- 46 "nezināms" motifs sadalās: 5×P14 paziņojumi, 10×tiesnešu iecelšana/atbrīvošana, 3×procesuāli termiņi/komisijas, 7×Lm14 cits, **21 patiesi nezināmi**
- **0 result mismatches** present-majority recompute pret stored — esošie dati tīri (78d87fb fix bija fallback path, ne main path); audit guardrail joprojām vērts pret nākotnes drift
- `f059ea7` (2026-04-25) jau noņēma `documents.platform='saeima'` — strukturāla sanācija, kas atbalsta saeima_bills kā atsevišķu entītiju

**Spec sekcijas, kas tiek modificētas:**
- § 2 (Scope) — bill_type whitelist + Phase 3 hook
- § 3.1 (Schema) — `saeima_bill_stages.stage_kind` kolonna
- § 3.3 (Stage vocabulary) — paplašināts saraksts
- § 5.4 (Acceptance) — atjaunināts "nezināms" sliekšņa racionāls
- § 6.2 (Detail page) — wiki/laws bidirectional render contract

---

## File Structure

| Fails | Atbildība | Status |
|---|---|---|
| `docs/superpowers/specs/2026-04-22-saeima-bills-design.md` | Master Phase 1 spec — visas dizaina izmaiņas tiek aplikus inline | Modify |
| `scripts/audit_saeima_vote_results.py` | Read-only audit: present-majority recompute vs stored result, exit 1 ja mismatches | Create |
| `tests/test_audit_saeima_vote_results.py` | Unit tests audit funkcijai | Create |
| `wiki/CHANGELOG.md` | Phase 0 prep ieraksts ar atklājumu skaitļiem | Modify |
| `wiki/operations/operacijas.md` | Pievienot audit skriptu pie weekly/sanity rutīnas | Modify |

---

## Task 1: Audit script ar TDD — vote-result sanity guardrail

**Mērķis:** Read-only skripts, kas pārvalida, ka katra `saeima_votes.result` saskan ar present-majority formula, kas piemērota `(total_par, total_pret, total_atturas)` skaitiem. Šobrīd 0 mismatches uz dzīvās DB; skripts kalpo kā regression guardrail pret nākotnes parser drift.

**Files:**
- Create: `scripts/audit_saeima_vote_results.py`
- Test: `tests/test_audit_saeima_vote_results.py`

- [ ] **Step 1: Write the failing test (helperis `compute_expected_result`)**

```python
# tests/test_audit_saeima_vote_results.py
import pytest
from scripts.audit_saeima_vote_results import compute_expected_result


def test_majority_par_above_present_half():
    # 60 par, 30 pret, 5 atturas → present=95, par > 47 → pieņemts
    assert compute_expected_result(60, 30, 5) == "pieņemts"


def test_majority_par_equal_present_half_is_noraidits():
    # 50 par, 30 pret, 20 atturas → present=100, par == 50 (not strictly greater) → noraidīts
    assert compute_expected_result(50, 30, 20) == "noraidīts"


def test_majority_par_below_present_half():
    # 30 par, 60 pret, 5 atturas → present=95, par < 48 → noraidīts
    assert compute_expected_result(30, 60, 5) == "noraidīts"


def test_zero_present_returns_nezinams():
    # All abstain or absent → no quorum participated
    assert compute_expected_result(0, 0, 0) == "nezināms"


def test_only_atturas_counts_as_present_so_par_zero_loses():
    # 0 par, 0 pret, 50 atturas → present=50, par=0 → noraidīts (atturas counts as present)
    assert compute_expected_result(0, 0, 50) == "noraidīts"
```

- [ ] **Step 2: Run test, confirm it fails**

Run: `.venv/Scripts/activate && pytest tests/test_audit_saeima_vote_results.py -v`
Expected: FAIL with `ModuleNotFoundError` vai `ImportError: compute_expected_result`.

- [ ] **Step 3: Write minimal `scripts/audit_saeima_vote_results.py`**

```python
"""Audit saeima_votes.result against present-majority recomputation.

Background: commit 78d87fb fixed a fallback path that used wrong absolute 51-of-100
threshold instead of "klātesošo vairākums" (par > present // 2). The main parsing
path was always correct, but this script guardrails against future regressions
or manually inserted rows.

Usage:
    python scripts/audit_saeima_vote_results.py            # exit 0 ok, 1 if mismatches
    python scripts/audit_saeima_vote_results.py --verbose  # print each mismatch
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from typing import Optional

from src.db import DB_PATH


def compute_expected_result(par: int, pret: int, atturas: int) -> str:
    """Apply Saeimas present-majority rule.

    Present = par + pret + atturas (those who registered a vote on the floor).
    Pieņemts iff par > present // 2; equality is NOT a majority.
    Special case: if no one voted, return 'nezināms' rather than fabricating
    a result.
    """
    present = par + pret + atturas
    if present == 0:
        return "nezināms"
    if par > present // 2:
        return "pieņemts"
    return "noraidīts"


def _normalize(s: Optional[str]) -> str:
    return (s or "").strip().lower()


def audit(verbose: bool = False) -> int:
    """Return mismatch count. Print verbose details on demand."""
    db = sqlite3.connect(DB_PATH)
    rows = db.execute(
        "SELECT id, total_par, total_pret, total_atturas, result, motif "
        "FROM saeima_votes"
    ).fetchall()
    mismatches = 0
    for vid, par, pret, atturas, stored, motif in rows:
        expected = compute_expected_result(par, pret, atturas)
        if _normalize(stored) != _normalize(expected):
            mismatches += 1
            if verbose:
                print(
                    f"vote_id={vid} par={par} pret={pret} atturas={atturas} "
                    f"stored={stored!r} expected={expected!r} motif={motif[:80]!r}"
                )
    print(f"audited={len(rows)} mismatches={mismatches}")
    return mismatches


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    return 0 if audit(verbose=args.verbose) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run unit tests, confirm they pass**

Run: `.venv/Scripts/activate && pytest tests/test_audit_saeima_vote_results.py -v`
Expected: 5 passed.

- [ ] **Step 5: Run audit on dzīvās DB, confirm clean**

Run: `.venv/Scripts/activate && PYTHONIOENCODING=utf-8 python scripts/audit_saeima_vote_results.py`
Expected: `audited=139 mismatches=0` un exit code 0.

- [ ] **Step 6: Commit**

```bash
git add scripts/audit_saeima_vote_results.py tests/test_audit_saeima_vote_results.py
git commit -m "feat(saeima): vote-result audit guardrail — present-majority recompute"
```

---

## Task 2: Stage vocabulary expansion — spec § 3.3 + § 5.4

**Mērķis:** Reducēt stage_name='nezināms' no 33% uz <8% ievietojot 4 jaunas kanoniskas vērtības, kas apraksta reālos motif buckets, kurus Saeima jau lieto. Skaitliskais mērķis: 25 no 46 unknown → klasificēti, 21 paliek `nezināms` (patiesi neklasificējami bez agenda parser logic).

**Files:**
- Modify: `docs/superpowers/specs/2026-04-22-saeima-bills-design.md` (sekcijas § 3.3 un § 5.4)

- [ ] **Step 1: Read existing § 3.3 stage vocabulary table**

Run: `Read tool on docs/superpowers/specs/2026-04-22-saeima-bills-design.md` (lines 113-130)
Expected: pašreizējās 10 stage_name vērtības identificētas (`iesniegts`, `1.lasījums`, `2.lasījums`, `2.lasījums priekšlikums`, `3.lasījums`, `3.lasījums priekšlikums`, `atgriezts komisijā`, `atsaukts`, `Lm14 balsojums`, `nezināms`).

- [ ] **Step 2: Replace § 3.3 stage vocabulary tabula ar paplašinātu versiju**

Edit `docs/superpowers/specs/2026-04-22-saeima-bills-design.md`, atrod tabulu zem `### 3.3 Stage vocabulary (slēgts saraksts)` un aizstāj ar:

```markdown
| stage_name | Kad | stage_result | bill_type ierobežojums |
|---|---|---|---|
| `iesniegts` | Kad bill pirmoreiz parādās agendā | NULL | jebkurš |
| `1.lasījums` | 1. lasījuma konceptuālais balsojums | `pieņemts` / `noraidīts` | Lp14 |
| `2.lasījums` | 2. lasījuma gala balsojums (pēc visiem priekšlikumiem) | `pieņemts` / `noraidīts` | Lp14 |
| `2.lasījums priekšlikums` | Viens priekšlikuma balsojums 2. lasījumā. `amendment_nr` aizpildīts. | `pieņemts` / `noraidīts` | Lp14 |
| `3.lasījums` | Galīgais balsojums | `pieņemts` / `noraidīts` | Lp14 |
| `3.lasījums priekšlikums` | Priekšlikums 3. lasījumā. `amendment_nr` aizpildīts. | `pieņemts` / `noraidīts` | Lp14 |
| `atgriezts komisijā` | Balsojums par atgriešanu atpakaļ | `pieņemts` ja atgriezts | Lp14 |
| `atsaukts` | Iesniedzējs atsauc | NULL | jebkurš |
| `tiesneša_amats` | Lm14 balsojums par tiesneša iecelšanu, atbrīvošanu vai apstiprināšanu | `pieņemts` / `noraidīts` | Lm14 |
| `procesuāls` | Lm14 termiņa pagarinājums, līdzatbildīgās komisijas noteikšana, deputāta atsaukšana no komisijas | `pieņemts` / `noraidīts` | Lm14 |
| `Lm14 cits` | Citi Lm14 balsojumi (Air Baltic aizdevums, izmeklēšanas komisijas izveide, eksportētāju saraksts utml.) | `pieņemts` / `noraidīts` | Lm14 |
| `paziņojuma_balsojums` | P14 paziņojuma (rezolūcijas) galīgais balsojums | `pieņemts` / `noraidīts` | P14 |
| `nezināms` | Backfill fallback motif, ko regex nevar klasificēt; atstājams līdz manuālai pārklasifikācijai | inherit no `saeima_votes.result` | jebkurš |

Vocabulary tiek kontrolēts caur `src.saeima._VALID_STAGE_NAMES` konstante + `_canonicalize_stage_name()` helper; `append_bill_stage()` noraidīs citas vērtības ar `ValueError`.

**Klasifikācijas regex (`_reading_from_motif`)**, ievērojot prioritāti:
1. `\d\.\s?lasījum` ar reading number → `{N}.lasījums` (priekšlikuma sufiksu pievieno, ja motif satur "priekšlikum")
2. `iecelšanu par.*tiesnesi` vai `apstiprināšanu par.*tiesnesi` vai `atbrīvošanu no tiesneša` → `tiesneša_amats`
3. `termiņa pagarināšanu` vai `komisijas noteikšanu` vai `atsaukšanu no.*komisijas` → `procesuāls`
4. `/P14` document_nr → `paziņojuma_balsojums`
5. `/Lm14` document_nr (citi) → `Lm14 cits`
6. Pārējie → `nezināms` (informatīvs warn loga ievadīt)
```

- [ ] **Step 3: Update § 5.4 acceptance kritērijs par "unknown stages" sliekšņi**

Atrod § 5.4 (līnija ~352) un aizstāj `unknown_stages` rindu ar:

```markdown
- `unknown_stages` ziņojums tiek ielogots; ja pārsniedz **10%** (paplašinātais vocabulary aptver 80%+ esošo motifs), failo atsevišķu issue par agenda re-parse vai jauna stage_name pievienošana. Iepriekšējais 30% slieksnis attiecās uz minimālo 9-stage vocabulary; pēc § 3.3 paplašinājuma realitāte ir <8% (audit 2026-04-26).
```

- [ ] **Step 4: Verify with diff review**

Run: `git diff docs/superpowers/specs/2026-04-22-saeima-bills-design.md`
Expected: tikai § 3.3 tabula + § 5.4 viena rinda mainītas; nav citu sekciju izmaiņu.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/specs/2026-04-22-saeima-bills-design.md
git commit -m "docs(spec): expand stage vocabulary — Lm14/P14/procesuāls buckets

Phase 0 prep — addresses 33% nezināms backfill rate found in 2026-04-26 audit.
4 new stage_name values + classification regex priority order documented."
```

---

## Task 3: bill_type whitelist + P14 ieviešana — spec § 2 + § 3.1

**Mērķis:** Specā šobrīd atļauti tikai `Lp14` un `Lm14`; reālie dati jau saturu **5 P14 paziņojumus** (rezolūcijas par dronu uzbrukumiem, IT vēlēšanu sistēmu, cukura diabēta pacientiem, robežšķērsošanas finansējumu, politisko spiedienu). P14 jāpievieno whitelist'am, lai tie netiek silently atmesti.

**Files:**
- Modify: `docs/superpowers/specs/2026-04-22-saeima-bills-design.md` (sekcijas § 2, § 3.1, § 10)

- [ ] **Step 1: Update § 3.1 saeima_bills.bill_type komentārs**

Atrod līniju `bill_type TEXT NOT NULL,                -- "Lp14" (likumprojekts) | "Lm14" (lēmuma projekts)` un aizstāj ar:

```sql
    bill_type TEXT NOT NULL,                -- "Lp14" (likumprojekts) | "Lm14" (lēmuma projekts) | "P14" (paziņojums/rezolūcija)
```

- [ ] **Step 2: Update § 2 Scope tabula**

Atrod § 2 sekciju `### Darām Phase 1 (MVP, droši ship-able)` un pievieno bullet pirms `Retro-backfill`:

```markdown
- **bill_type whitelist:** `{'Lp14', 'Lm14', 'P14'}`. Validēts pret `_VALID_BILL_TYPES` konstanti `src/saeima.py`. Nezināmi prefiksi (piem. nākotnes `/Lp15`) → log + skip ar warn, neraksta DB.
```

- [ ] **Step 3: Update § 10 Riski tabulu**

Atrod rindu `| `document_nr` nav klasificēts kā Lp14 vai Lm14 (nākotnes Saeima) | ... |` un aizstāj ar:

```markdown
| `document_nr` nav klasificēts kā Lp14, Lm14 vai P14 (nākotnes Saeima vai jauni dokumentu tipi) | `bill_type` validē pret `_VALID_BILL_TYPES = {'Lp14', 'Lm14', 'P14'}` whitelistu; nezināms → log + skip ar warn. Nepārdali datus. |
```

- [ ] **Step 4: Atjaunina § 12 atklāto jautājumu sarakstu**

Atrod § 12 1. punktu un aizstāj:

```markdown
1. Vai `bill_type` whitelist jāpaplašina ar nākotnes Saeimu variantiem (`/Lp15`, `/Lm15`, `/P15` kad 15. Saeima sāks)? Phase 1 ignorē — tikai 14. Konstantes nosaukums `_VALID_BILL_TYPES` neatkarīgs no Saeimas numura, tikai vērtības saraksts.
```

- [ ] **Step 5: Verify diff**

Run: `git diff docs/superpowers/specs/2026-04-22-saeima-bills-design.md`
Expected: 4 lokalizēti edits sekcijās 2, 3.1, 10, 12.

- [ ] **Step 6: Commit**

```bash
git add docs/superpowers/specs/2026-04-22-saeima-bills-design.md
git commit -m "docs(spec): add P14 (paziņojums) to bill_type whitelist

Phase 0 prep — 5 P14 rows already in saeima_votes (drone strikes,
election IT, etc.); spec previously implied silent drop. Whitelist
now {Lp14, Lm14, P14}."
```

---

## Task 4: wiki/laws ↔ saeima_bills bidirectional render contract — spec § 6.2

**Mērķis:** Esošās 33 cilvēka rakstītās `wiki/laws/*.md` lapas (ar manuālu mērķi, normām, politiski jutīgām sadaļām) ir aktīvs, kuru Phase 1 detail page izmanto tikai kā vienvirziena tekstu ("Šis likumprojekts groza: X"). Šis tasks definē divvirziena render: `wiki/laws/<slug>.md` saņem auto-ģenerētu "Aktuālie likumprojekti" sekciju, un `/likumprojekti/{nr}.html` link vēl uz wiki rendered versiju.

**Files:**
- Modify: `docs/superpowers/specs/2026-04-22-saeima-bills-design.md` (sekcija § 6.2 + § 6.5)

- [ ] **Step 1: Read § 6.2 detail page struktūru**

Run: `Read tool on docs/superpowers/specs/2026-04-22-saeima-bills-design.md` (lines 396-446)
Expected: identificēt "Saistītais bāzes likums" bloku zem detail page wireframe.

- [ ] **Step 2: Replace "Saistītais bāzes likums" bloka definīciju**

Atrod § 6.2 līnija `[Saistītais bāzes likums]  ← ja base_law_slug ne null` un aizstāj sekciju:

```markdown
[Saistītais bāzes likums]  ← ja base_law_slug ne null
Šis likumprojekts groza: **Valsts aizsardzības finansēšanas likums**
[Atvērt likuma lapu →] linko uz `/likumi/valsts-aizsardzibas-finansesanas-likums.html`
(rendered no `wiki/laws/valsts-aizsardzibas-finansesanas-likums.md` ar Jinja2)

**base_law_slug atlases noteikumi (`_resolve_base_law_slug`):**
1. Ja motif satur eksaktu likuma nosaukumu no `wiki/laws/likumi.md` indeksa (case-insensitive substring match), atgriež slug.
2. Ja motif satur "Grozījumi {X}" un X normalizācijā atbilst slug → atgriež slug.
3. Citādi NULL (lielākoties tas notiek jauniem likumiem, kas vēl nav wiki).
```

- [ ] **Step 3: Pievieno jaunu § 6.2.1 apakšsekciju**

Aiz "Saistītais bāzes likums" bloka, pirms § 6.3 cross-linking, ievieto jaunu apakšsadaļu:

```markdown
### 6.2.1 wiki/laws lapas auto-enrichment

Esošās `wiki/laws/<slug>.md` lapas tiek paplašinātas ar auto-ģenerētu sekciju **starp markeriem** (analogi `<!-- SYNC-AUTO START -->` / `<!-- SYNC-AUTO END -->` patternam, ko jau izmanto person profiles):

```markdown
<!-- BILLS-SYNC-AUTO START -->
## Aktuālie likumprojekti šajā likumā

| Bill nr | Nosaukums | Stadija | Datums |
|---|---|---|---|
| [1315/Lp14](/likumprojekti/1315-lp14.html) | Grozījumi par 5% IKP | 3.lasījums (pieņemts) | 2026-04-23 |
| [1098/Lp14](/likumprojekti/1098-lp14.html) | Iepirkumu vienkāršošana | 2.lasījums (pieņemts) | 2026-03-12 |
<!-- BILLS-SYNC-AUTO END -->
```

**Generators:**
- `src/wiki_sync.py` (jauna funkcija `_render_law_bills_block(slug)`) izmeklē `saeima_bills WHERE base_law_slug = ?` un atjaunina markerus.
- Tiek izsaukts no esošā wiki sync flow, palaists pēc `@saeima-tracker` agent darba un pirms publiskās ģenerācijas.
- Idempotents: ja nav saistīto bills, sekcija ir tukša ("Šajā likumā šobrīd nav aktīvu likumprojektu Saeimā.").

**Publiskā render no wiki:**
- `src/generate.py::_generate_law_pages()` (jauna funkcija) iet pār `wiki/laws/*.md`, atjaunina BILLS-SYNC-AUTO marķierus *runtime*, un renderē `/likumi/<slug>.html` ar `templates/likums.html.j2`.
- Detail page `[Atvērt likuma lapu →]` link rāda uz šo URL.
```

- [ ] **Step 4: Update § 6.5 Statiskā ģenerācija ar jaunu funkciju saraksta papildinājumu**

Atrod § 6.5 sākumu `Jaunas funkcijas:` un pievieno divas jaunas rindas:

```markdown
- `_generate_law_pages()` — iterē pār `wiki/laws/*.md`, atjaunina `BILLS-SYNC-AUTO` markierus, renderē `/likumi/<slug>.html`. Izsaukts pirms `_generate_bill_pages()`, lai bill detail page back-link rezolvē.
- `_resolve_base_law_slug(motif)` (`src/saeima.py`) — match logic, kas aprakstīts § 6.2.
```

Un pievieno § 6.5 Modificēti sarakstam:
```markdown
- `templates/likums.html.j2` — jauns; rāda wiki/laws lapu + auto-iekļautās bills (Markdown → HTML konversija ar mistune vai esošu wiki render helper).
```

- [ ] **Step 5: Verify diff (read whole spec)**

Run: `Read docs/superpowers/specs/2026-04-22-saeima-bills-design.md` (visu)
Expected: § 6.2, § 6.2.1 (jauns), § 6.5 izmaiņas konsistentas; nav atliku no oriģināla "Saistītais bāzes likums" bloka.

- [ ] **Step 6: Commit**

```bash
git add docs/superpowers/specs/2026-04-22-saeima-bills-design.md
git commit -m "docs(spec): wiki/laws bidirectional render contract

Phase 0 prep — 33 manual law pages get auto BILLS-SYNC-AUTO block,
detail page back-links to /likumi/<slug>.html. Resolves orphan-asset
risk where wiki/laws/ semi-isolated from new saeima_bills entity."
```

---

## Task 5: Phase 3 (debates) hook reservation — spec § 2 + § 3.1

**Mērķis:** Lietotāja faktiskā motivācija ir debates → bill saiste. Phase 3 paliek atsevišķs darbs, BET Phase 1 schema nedrīkst aizvērt durvis. Šis task pievieno `saeima_bill_stages.stage_kind` kolonnu (TEXT, defaults `'vote'`), kas nākotnē atļaus `'debate'` rindas tajā pašā timeline tabulā bez migrācijas. Alternatīvi varētu atstāt tikai `stage_name='debate'`, bet kind kolonna ļauj atšķirt votes no debate utterances bez stage_name parsēšanas.

**Files:**
- Modify: `docs/superpowers/specs/2026-04-22-saeima-bills-design.md` (sekcijas § 2, § 3.1)

- [ ] **Step 1: Pievieno `stage_kind` kolonnu § 3.1 saeima_bill_stages CREATE**

Atrod tabulu `CREATE TABLE IF NOT EXISTS saeima_bill_stages` un pievieno pirms `created_at`:

```sql
    stage_kind TEXT NOT NULL DEFAULT 'vote',  -- 'vote' (Phase 1) | 'debate' (Phase 3) | 'commission' (Phase 3+)
```

Un pievieno indeksu zem esošajiem:

```sql
CREATE INDEX IF NOT EXISTS idx_bill_stages_kind ON saeima_bill_stages(stage_kind);
```

- [ ] **Step 2: Atjaunina § 3.3 stage vocabulary tabulas ievadu**

Aiz tabulas (kas tika papildināta Task 2) pievieno paragrāfu:

```markdown
**Phase 3 hook:** `stage_kind` kolonna (`'vote' | 'debate' | 'commission'`) atļauj nākotnē Phase 3 ievietot debate utterances kā timeline rindas bez schema migrācijas. Phase 1 visi raksta `stage_kind='vote'` (default); `_VALID_STAGE_NAMES` validē tikai `kind='vote'` rindas. Phase 3 spec definēs atsevišķu `_VALID_DEBATE_STAGE_NAMES` un, iespējams, atsevišķu insert helperi `append_bill_debate()`.
```

- [ ] **Step 3: Update § 2 "Ārpus scope" rindu par debates**

Atrod § 2 līniju `- **Debates** — nav šī darba daļa. Flagojams kā Phase 3 kandidāts; on-the-record rhetorika, kas tieši saistīta ar bill.` un aizstāj:

```markdown
- **Debates / stenogrammas** — nav Phase 1 vai 2 daļa. Phase 3 specs definēs stenogrammu skrāpēšanu un per-utterance ekstrakciju. Phase 1 schema *jau* rezervē hook: `saeima_bill_stages.stage_kind='debate'` ļauj Phase 3 pievienot debate ierakstus tajā pašā timeline tabulā bez migrācijas. Phase 1 nedrīkst pievienot Lp14 nosaukumu vai motif-based debate detection, kamēr nav Phase 3 spec.
```

- [ ] **Step 4: Pievieno § 12 atklāto jautājumu sarakstā**

Pievieno jaunu punktu:

```markdown
5. Vai Phase 3 lietos `saeima_bill_stages` ar `stage_kind='debate'` vai atsevišķu `saeima_debate_utterances` tabulu? Phase 1 hook abi pieļauj — atsevišķa tabula labāka, ja per-utterance ir vairāki politiķi (panel debate); apvienota tabula labāka, ja katra utterance ir 1 politiķis. Lēmums Phase 3 specā.
```

- [ ] **Step 5: Verify diff**

Run: `git diff docs/superpowers/specs/2026-04-22-saeima-bills-design.md`
Expected: § 2, § 3.1, § 3.3, § 12 izmaiņas; nav citu sekciju izmaiņu.

- [ ] **Step 6: Commit**

```bash
git add docs/superpowers/specs/2026-04-22-saeima-bills-design.md
git commit -m "docs(spec): reserve Phase 3 debates hook in stage table

Phase 0 prep — saeima_bill_stages.stage_kind column (default 'vote')
lets Phase 3 add debate utterances without schema migration. No
Phase 1 behavior change."
```

---

## Task 6: CHANGELOG entry + operacijas.md sanity check integration

**Mērķis:** Dokumentēt Phase 0 prep tirgu un pievienot audit skripta palaišanu pie weekly rutīnas.

**Files:**
- Modify: `wiki/CHANGELOG.md`
- Modify: `wiki/operations/operacijas.md`

- [ ] **Step 1: Pievieno CHANGELOG ierakstu**

Atveri `wiki/CHANGELOG.md`, atrod augšējo ierakstu un *iepriekš* tā pievieno:

```markdown
## 2026-04-26 — Saeima bills Phase 0 prep applied

Pirms Phase 1 implementācijas (`docs/superpowers/specs/2026-04-22-saeima-bills-design.md`) atklāti 5 dizaina flaws audit'ā uz dzīvās DB:

- **Stage classification 33% nezināms** uz 139 esošajiem `saeima_votes` — pie spec § 5.4 30% sliekšņa. Atrisināts ar 4 jaunām stage_name vērtībām (`tiesneša_amats`, `procesuāls`, `Lm14 cits`, `paziņojuma_balsojums`); paredzamais nezināms <8%.
- **P14 (paziņojumi) nav whitelist** — 5 reālas P14 rindas (dronu uzbrukumi, IT vēlēšanas, robežšķērsošana) būtu silently atmestas. Pievienoti `_VALID_BILL_TYPES`.
- **wiki/laws/* izolācija** — 33 manuālas likumu lapas neintegrētas ar bill detail page. Pievienots BILLS-SYNC-AUTO marķieri pattern + `/likumi/<slug>.html` render.
- **Phase 3 debates hook** — `saeima_bill_stages.stage_kind` kolonna (default `'vote'`) ļauj nākotnē Phase 3 pievienot stenogrammu utterances bez migrācijas.
- **Vote-result audit guardrail** — `scripts/audit_saeima_vote_results.py` validē present-majority formula pret stored result. Šobrīd 0 mismatches; turpmāk daļa weekly sanity check.

Spec'a izmaiņas commits: skat. `git log --oneline --since=2026-04-26 -- docs/superpowers/specs/2026-04-22-saeima-bills-design.md`.

**Phase 1 statuss:** schema un agent prompt darba paka ship-ready uz spec v2 (pēc Phase 0).
```

- [ ] **Step 2: Pievieno audit skripta palaišanu pie operacijas.md**

Atveri `wiki/operations/operacijas.md`, atrod weekly/sanity rutīnas sekciju (`grep "weekly"` vai `grep "sanity"`) un pievieno bullet:

```markdown
- **Saeima vote-result audit** — palaid `python scripts/audit_saeima_vote_results.py` (exit 0 = clean). Ja exit 1, palaid ar `--verbose` lai redzētu konkrētus vote_id un izmeklē, vai `78d87fb` style fallback bug ir atgriezies vai jauns parser drift.
```

- [ ] **Step 3: Verify final state**

Run: `git status`
Expected: `wiki/CHANGELOG.md` un `wiki/operations/operacijas.md` modified, nekas cits.

Run: `git log --oneline -6`
Expected: 5 commits no Tasks 1-5 + Task 6 vēl nav committed.

- [ ] **Step 4: Commit**

```bash
git add wiki/CHANGELOG.md wiki/operations/operacijas.md
git commit -m "docs(changelog,ops): document Phase 0 prep + add vote-result audit to weekly

Closes Phase 0 prep work for saeima bills tracker. Phase 1 spec
ready for implementation per docs/superpowers/specs/2026-04-22-saeima-bills-design.md."
```

---

## Self-Review

**Spec coverage check:**

| Flaw (no manuālā audit ziņojuma) | Plāna task |
|---|---|
| 1. Vote-result correctness post-78d87fb | Task 1 — audit guardrail |
| 2. 33% nezināms stages | Task 2 — vocabulary expansion |
| 3. P14 whitelist trūkums | Task 3 — bill_type expansion |
| 4. wiki/laws izolācija | Task 4 — bidirectional render |
| 5. Phase 3 hook | Task 5 — stage_kind kolonna |

Visi 5 flaws ir adresēti. Task 6 ir close-out (CHANGELOG + ops integration).

**Placeholder scan:** Visi code blocks satur konkrētu kodu vai SQL, visi commits satur konkrētus message text, visi paths ir absolūti. Nav "TBD" vai "fill in details".

**Type consistency:**
- `compute_expected_result(par, pret, atturas)` — viens signature, izmantots Task 1 testos un implementācijā.
- `_VALID_STAGE_NAMES` — pieminēts § 3.3 (Task 2) un § 3.3 Phase 3 hook (Task 5); abi atsaucas uz to pašu konstanti.
- `_VALID_BILL_TYPES` — pieminēts Task 3 § 2 un § 10; konsistents.
- `stage_kind` — Task 5 kolonna; nav konflikts ar `stage_name`.
- `_resolve_base_law_slug` — Task 4 pieminēts; jāimplementē Phase 1 (nav šī plāna scope, bet specā minēts).

**Plāna apjoms:** 6 tasks, ~1.5h darbs (1× 30min code + 5× 10-15min doc edits). Sekvencionāli: Task 1 var paralēli ar 2-5; Task 6 prasa 1-5 pabeigtus.

---

**Plan complete and saved to `docs/superpowers/plans/2026-04-26-saeima-bills-phase-0-prep.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — Es dispatchoju jaunu subagent par katru task, review starp tasks, ātra iterācija. Piemērots šim plānam, jo Tasks 2-5 ir paralēli neatkarīgi (visi atsevišķi spec sekciju edits).

**2. Inline Execution** — Pildām šajā sesijā ar executing-plans, batch ar checkpoints. Piemērots, ja gribi tiešu redzamību spec evolūcijai.

**Kuru pieeju izvēlies?**
