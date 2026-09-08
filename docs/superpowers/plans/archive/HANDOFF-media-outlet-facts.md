# Media Outlet Transparency Facts — Handoff for Next Sessions

> **Audience:** Claude Code session picking up after the media-outlet facts population (master @ `bef2669`, 2026-06-01).
> **Status:** ✅ Shipped, verified, deployed to atmina.lv, and pushed to `origin/master`. The `/mediji` feature is fully populated. No blocking follow-ups — only optional polish + a pre-existing unrelated count bug (see Open Items).

---

## What this session did

Populated the previously-empty `facts: []` for all 10 outlets in `sources.yaml`'s `outlets:` block, then deployed + documented it. Each outlet now shows sourced transparency facts on its `/mediji/<slug>.html` page.

**Method:** ran the `@outlet-researcher`-style flow once per outlet (owner / funding_model / legal_form / editorial_leadership / founded), then an **adversarial verify pass** that fetched every `source_url` and confirmed it supports the value. Verifier corrections were applied before paste (dropped unsupported "owner financing" clauses on Delfi/LA/Jauns/Diena; swapped dead/bot-blocked source URLs; fixed misleading dates; trimmed NRA's funding_model to stay symmetric — transparency, not targeting).

### Commits (all on master, pushed)
- `ea738ab` — `feat(mediji): populate transparency facts for all 10 outlets` (sources.yaml, 51 facts)
- `3aad7bd` — `feat(mediji): Latvian labels for outlet transparency fields` (templates/medijs.html.j2)
- `cda9d28` — `feat(wiki): emit Mediji section in generated index` (src/wiki.py + wiki/index.md)
- `bef2669` — `docs(mediji): agent index + @outlet-researcher doc + CHANGELOG + source-framing`

---

## Current State (verified on master @ `bef2669`)

### `sources.yaml` — `outlets:` block
- **10 outlets, 51 facts total**, every fact carries `value` + `source_url` + `as_of: 2026-06-01`.
- Per outlet: 5 facts (`owner`, `funding_model`, `legal_form`, `editorial_leadership`, `founded`), **except `nra` which has 6** — two `owner` rows by design (registry ownership chain via firmas.lv + beneficial owner Anastasija Udalova via nra.lv's own announcement, each separately sourced).
- `src/outlets.py` silently drops any fact missing `value` or `source_url`, and only accepts those 5 English enum keys — so values stay English-keyed; do NOT translate the `field:` keys in YAML or they vanish.
- Verify the reader picks everything up:
  ```bash
  ./.venv/Scripts/python.exe -c "from src.outlets import load_outlets; print(sum(len(o['facts']) for o in load_outlets()))"   # -> 51
  ```

### Public site (live on atmina.lv)
- `/mediji.html` (index) + `/mediji/<slug>.html` × 10 — facts render as the **Caurskatāmība** table: each row = Latvian label, value, clickable `avots` link, `as_of` date. No more "vēl nav apkopoti" placeholder.
- Field labels are mapped to Latvian **in the template** (`templates/medijs.html.j2` → `fact_labels` dict): owner→Īpašnieks, funding_model→Finansējums, legal_form→Juridiskā forma, editorial_leadership→Redakcijas vadība, founded→Dibināts. If a new fact field is ever added, update this map too.

### Verification (green)
- `bash scripts/check.sh` — ruff clean, **1293 passed / 2 xfailed / 1 xpassed**, render smoke OK.
- `wiki_lint` — **0 broken links**; 2 orphans, both pre-existing person pages (`didzis-klucins`, `martins-krusts`), unrelated.

### Docs / wiki (updated this session)
- `wiki/operations/agenti/outlet-researcher.md` — new human-readable agent doc.
- `wiki/operations/agenti/agenti.md` — added `@outlet-researcher` + the previously-missing `@weekly-brief-writer`; count fixed to 11.
- `CLAUDE.md` (root) — agent registry updated.
- `wiki/CHANGELOG.md` — `2026-06-01 — Mediji` entry.
- `wiki/operations/source-framing.md` — cross-ref: internal `framing:` signal vs. public sourced facts.
- `src/wiki.py` — `_build_index` emits the `Mediji` Struktūra line (durable across `wiki_sync`).

---

## Key files
| File | Role |
|------|------|
| `sources.yaml` → `outlets:` | The registry + facts (config, no DB table). Edit here to change facts. |
| `src/outlets.py` | Reads outlets; drops unsourced facts; enforces the 5-field enum + host grouping. |
| `src/render/mediji.py` | Render-time coverage computation (single-pass, host-keyed) + page emit. |
| `templates/medijs.html.j2` / `mediji.html.j2` | Detail / index templates; Latvian `fact_labels` map lives in `medijs`. |
| `.claude/agents/outlet-researcher.md` | Canonical agent prompt (binding). |
| `docs/superpowers/specs/2026-06-01-media-outlet-profiles-design.md` | Design spec (ethos, scope, non-goals, phase 2). |
| `docs/superpowers/plans/2026-06-01-media-outlet-profiles.md` | Implementation plan. |

---

## Open Items / Follow-ups (none blocking)

1. **`16 → 15 partijas` index count bug (PRE-EXISTING, unrelated).** `wiki/index.md` says "16 partijas" but the DB has 15; flagged in the design spec's open items. It's a `len(party_rows)` counting issue in `src/wiki.py::_build_index` (likely an inactive/sentinel party row leaking in). Untouched this session — chase separately if wanted.

2. **Provenance caveats worth knowing** (all were verified, but flagged for future re-checks):
   - **Delfi `editorial_leadership`** source is an LSM article that returns HTTP 403 to automated fetchers but loads fine in browsers (public broadcaster, reliable). Swap to a non-403 source if a cleaner link is preferred.
   - **Delfi-RU `editorial_leadership`** (Anatolijs Golubovs) rests on a 2022 openDemocracy piece — most recent confirmation found; 2026 currency not independently re-verified.
   - **firmas.lv beneficial-owner names** (Udalova / Šmidre / Kots / LA's Monaco-resident owner) are masked on the public registry page but corroborated by independent reporting — the values name them with the registry as the source for the ownership chain.

3. **X handles incomplete.** Only `lsm` (ltvzinas), `leta` (letanewslv), `nra` (nralv) carry an `x_handle`. The researcher confirmed **`@vestnesislv`** exists for Latvijas Vēstnesis (not yet added). No official handle was confirmed for delfi / tvnet / diena / la / jauns / delfi-ru. Add `x_handle:` to the relevant `outlets:` entries if desired (identity field, not a `fact`).

4. **Re-verification cadence.** Facts are stamped `as_of: 2026-06-01`. Ownership/editor changes are rare but do happen (e.g. LSM editor-in-chief, board appointments) — re-run `@outlet-researcher` for a single outlet when something changes; git history is the change log.

5. **Phase 2 (deferred, from the design spec).** Would justify real DB tables: a published-rubric framing/emphasis layer (symmetric, only with a published rubric); individual-journalist profiles; an optional recurring media-brief agent. Open decisions still parked: is `rus.delfi.lv` a separate outlet or subsumed under Delfi (currently separate `delfi-ru`); is `vestnesis.lv` (official gazette) an `agency` outlet or excluded from coverage *comparisons* since it's official publishing, not journalism.

---

## How to refresh / add an outlet's facts (the loop)

1. Run `@outlet-researcher` (or the equivalent research+verify flow) with the outlet's name + website + X handle. It returns sourced facts; **omit any field it can't source** (no source_url → dropped at read time).
2. Review the proposed YAML; paste the `facts:` entries into that outlet's block in `sources.yaml` (single-quoted values are safest — they contain `"`).
3. `bash scripts/check.sh` (ruff + pytest + render smoke must be green).
4. Re-render: `./.venv/Scripts/python.exe -c "from src.render import generate_public_site; generate_public_site(only={'mediji'})"`.
5. Eyeball `output/atmina/mediji/<slug>.html`.
6. Deploy: `bash scripts/deploy.sh --dry-run` then `bash scripts/deploy.sh`.
7. Commit `sources.yaml` (scope commits to it — the working tree has unrelated untracked clutter; leave `wiki/log-ingest/2026-05.md`, which is a pre-existing uncommitted change, alone).

**Guardrails (non-negotiable — this is the credibility of the feature):** descriptive only, every fact sourced, the *same fields for every outlet* regardless of perceived lean, no `corrupt`/`bought`/`biased` labels, and the editorial `framing:` field (on `sources:` feed rows) stays **internal** — never surfaced on the page.
