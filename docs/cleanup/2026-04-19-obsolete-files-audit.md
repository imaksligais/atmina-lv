# Obsolete / Unused Files Audit — 2026-04-19

Audit scope: `~/atmina`. Analyzed by Claude (Explore agent) on operator request. **Nothing was deleted** — this is a candidate list for human review.

Already cleaned before this audit: 48 loose dev screenshots in project root + `probe_social.json` scratch file.

---

## 1. Scripts — one-off experiments (LOW risk)

Safe to delete. No routine references these. Many are already covered by `.gitignore`.

- `scripts/backfill_brief_images.py` — one-shot migration, graphics now run on ingest
- `scripts/backfill_diacritics_from_source.py` — one-shot data fix
- `scripts/sitemap_backfill.py` — one-shot
- `scripts/fix_image_26_recolor.py` — specific image fix, not tracked in git
- `scripts/scan_diacritics.py` — one-off diagnostic
- `scripts/normalize_broken_topics.py` — one-off repair
- `scripts/check_photos.py` — one-off check
- `scripts/smoke_test.py` — Phase 0 smoke test, never maintained
- `scripts/test_image_prompt.py` — scratch test

**Brand asset generation** (already gitignored per `.gitignore:50-55`, kept for reference):
- `scripts/generate_banners_atmina_brand*.py` (v1–v5, 5 files)
- `scripts/generate_logos_atmina_brand.py`
- `scripts/generate_x_logos*.py` (+ `_dark_ripples`, `_atmina_diacritic`)
- `scripts/generate_x_banners*.py` (+ `_dark`)
- `scripts/crop_banners_to_3x1.py`

**Superseded intro-thread renderers** (replaced by `render_intro_thread_pdf.py`):
- `scripts/render_intro_thread.py` (56 lines, v1 hero only)
- `scripts/render_intro_thread_45.py` (kept — still used for T4+T5 re-renders)

## 2. Top-level loose files

- **`atmina-handoff.zip`** (565 KB, 2026-04-18) — snapshot for handoff. `MEDIUM` — verify handoff complete.
- **`atmina-handoff/`** (folder with `lapsa_*.py`/`.txt`) — looks like live work session. `HIGH` — confirm with operator.
- **`design-handoff/`** (`brief.md` + `sample-data.md`) — static design reference. `LOW` — archive once design work done.
- **`data/db.sqlite3`** (untracked, 0 bytes) — stale empty DB. `LOW`.
- **`data/atmina.db.backup-2026-04-08`**, `atmina_backup_20260409_120904.db`, `atmina.phase2-backup.db`, `atmina.pre-dedup-backup.db` — 4 pre-April-11 DB backups, ~84 MB each. `LOW` — keep the two most recent (Apr 16–17), drop the others.
- **`politracker.db`** (304 KB, 2026-04-18) — untracked, no references in source. `MEDIUM` — verify with operator.
- **`scratch/jv_analyze.py`** + `jv_results.json` — by-name scratch. `LOW`.
- **`scripts/social_agent_smoke.md`** — manual checklist superseded by `wiki/operations/social-agent.md` setup section. `LOW`.

## 3. Plans + docs

- `docs/plans/2026-04-06-atmina-implementation.md` (46 KB) — project inception plan. `LOW` — archive rather than delete.
- `docs/plans/2026-04-07-knab-scraper.md` (55 KB) — feature landed. `LOW` — archive.
- `docs/plans/2026-04-07-lilly-framework.md` — historical. `LOW`.
- `docs/plans/2026-04-11-claim-type-split.md` — migration landed, now documented in CLAUDE.md rule #12. `LOW` — archive.

Suggestion: move all four to `docs/plans/archive/`.

## 4. Source modules

All `src/*.py` modules have at least one importer. **No orphans found.** `src/preflight.py` has only one importer (`src/ingest.py`) but is a legitimate helper.

## 5. Tests

All test files map to existing modules. One verification note: `tests/test_post_launch_fixes.py` imports `get_pending_politicians` from `src.analyze` — confirmed still present (489/489 tests pass).

## 6. Wiki

- `wiki/dailies/` — 4 dailies (Apr 10, 14, 17, 18). No retention policy. Small set; no action yet.
- `wiki/log-ingest.md` — actively synced (daily). Keep.

---

## Suggested cleanup commands

```bash
# DB backups — keep only most recent 2
rm data/atmina.db.backup-2026-04-08 data/atmina.pre-dedup-backup.db \
   data/atmina.phase2-backup.db data/atmina_backup_20260409_120904.db

# One-off scripts (review each first)
rm scripts/backfill_brief_images.py scripts/backfill_diacritics_from_source.py \
   scripts/sitemap_backfill.py scripts/fix_image_26_recolor.py \
   scripts/scan_diacritics.py scripts/normalize_broken_topics.py \
   scripts/check_photos.py scripts/smoke_test.py scripts/test_image_prompt.py

# Brand experiment scripts (already gitignored — just clearing working tree)
rm scripts/generate_banners_atmina_brand*.py scripts/generate_logos_atmina_brand.py \
   scripts/generate_x_logos*.py scripts/generate_x_banners*.py \
   scripts/crop_banners_to_3x1.py

# Superseded renderer
rm scripts/render_intro_thread.py  # v1 hero-only; superseded by render_intro_thread_pdf.py

# Archive finished plans
mkdir -p docs/plans/archive
mv docs/plans/2026-04-06-*.md docs/plans/2026-04-07-*.md \
   docs/plans/2026-04-11-*.md docs/plans/archive/

# Scratch + empty artifacts
rm data/db.sqlite3  # 0 bytes
rm -r scratch/  # by-name scratch

# Social agent smoke doc — superseded by wiki runbook
rm scripts/social_agent_smoke.md
```

## Needs operator confirmation

- `atmina-handoff.zip` + `atmina-handoff/` — is handoff complete?
- `politracker.db` — what is this?
- `design-handoff/` — is design work done?
