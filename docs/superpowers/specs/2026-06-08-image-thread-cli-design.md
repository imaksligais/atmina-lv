# Image / thread CLI — design (2026-06-08)

## Problem

Daily image generation is reproduced as throwaway scripts, not invoked as a tool:

- **Brief posters** (`generate_brief_image_*.py`, ~9 files): already use the canonical
  `src/graphics/` pipeline, but each is a ~70-line clone with `NOTE_ID` + a custom
  metaphor `VM` hardcoded.
- **Thread/tweet sepia** (`_thread_images_*.py`, `gen_*`, ~6 files): bypass the canonical
  pipeline entirely — hardcoded `STYLE` + prompt dict, direct `generate_image()`, manual
  file writes. **Sepia formula has diverged into 3 variants** across days (verified:
  06-04/06-05 "19th-century engraving…"; 06-06 "Aged archival… slate-blue"; gen_kulberga
  a third). No audit, no budget guard.

Result: ~15 untracked one-off scripts, drifting style, in ruff scope.

## Goal

One committed, tested CLI replacing both patterns. Encode the canonical sepia once.
The `@graphics-designer` agent keeps deciding metaphors/prompts (the creative part); the
CLI removes boilerplate.

## Architecture (reuse existing `src/graphics/`)

1. **`src/graphics/prompt.py`** — add `SEPIA_STYLE` constant (single source for tweet/thread
   sepia, beside `STYLE_VARIANTS`). Canonical text = the most complete 06-06 variant:
   > "Aged archival editorial illustration, muted sepia tones with subtle slate-blue accents,
   > fine cross-hatching and engraving texture, printed on textured aged paper, no text, no
   > lettering, no numbers, no words, no captions, no logos."
2. **`src/graphics/thread.py`** (new, lightweight — no DB):
   - `thread_filename(date, suffix) -> str` → `"{date}-thread-{suffix}.png"`
   - `compose_thread_prompt(base) -> str` → `base + " " + SEPIA_STYLE`
   - `generate_thread(date, prompts: dict, out_dir, generate_fn=generate_image) -> list[Path]`
     — for each `{suffix: base_prompt}` generate + write PNG. `generate_fn` injectable so
     tests never hit the API.
3. **`src/graphics/cli.py`** (new) — `python -m src.graphics.cli` with two subcommands:
   - `brief --note-id N [--metaphor M] [--mood …] [--accent …] [--db PATH]` — faithful
     parameterization of the existing brief pipeline (build_prompt + storage audit + budget +
     approval gate `approved=0`). `--metaphor` overrides; else `visual_map.get_visual(topic)`
     (house style: metaphor_hint overrides generic). Prints `RESULT_JSON:` like the scripts.
   - `thread --date D --prompts thread.json [--out output/images/threads]` — read JSON
     `{suffix: prompt}`, call `generate_thread`. UTF-8 stdout.

## Data flow

- `thread.json`: `{"1-lead": "A newly assembled cabinet…", "2-valdiba": "…"}` →
  `output/images/threads/{date}-thread-{suffix}.png`.
- `brief`: unchanged DB flow (context_notes.visual_brief_json → build_prompt → brief_images
  row approved=0 → human review → render → deploy).

## Testing (TDD)

- `prompt`: `SEPIA_STYLE` exists + non-empty + contains the no-text rule; `STYLE_VARIANTS`
  keys unchanged (no regression to brief poster).
- `thread`: `thread_filename` format; `compose_thread_prompt` appends `SEPIA_STYLE`;
  `generate_thread` with a fake `generate_fn` writes N files with correct names and prompts
  that include `SEPIA_STYLE` — no API/cost.
- `cli`: arg parser routes `brief`/`thread` to the right handler (parse-only, no generation).

## Migration

- Move **image-only** throwaway scripts → `scripts/_scratch/` (gitignored):
  `generate_brief_image_*`, `_thread_images_*`, `generate_thread_images_*`, `regen_brief_*`,
  `gen_thread_*`, `gen_tweet_images_*`, `gen_kulberga_tweet_image`, `_gen_synth_imigracija`.
  Add `scripts/_scratch/` to `.gitignore` + `pyproject.toml` ruff `exclude`.
  Leave non-image untracked files (`build_pppa_reply.py`, `render_one_politician.py`, `_bf_*`,
  `_p2_*`) untouched — separate concern.
- `.claude/agents/graphics-designer.md` → call the CLI, not paste code.
- `wiki/operations/commands.md` → document the CLI.

## Scope (YAGNI)

`brief` + `thread` only. No separate single-tweet command (a 1-entry thread JSON covers it).

## Non-goals / unchanged

@graphics-designer authors metaphors/prompts; image model, approval gate, deploy flow
unchanged; brief poster ≠ tweet sepia distinction preserved; brief `build_prompt` semantics
untouched (no new inline constraints).
