# Contributing to atmina

Thanks for your interest. atmina is a Latvian political-transparency platform — civic infrastructure first, software second. Contributions are welcome at every level: data corrections, code fixes, source additions, documentation, translations.

> The project's primary working language is **Latvian**. English issue / PR descriptions are welcome and encouraged for non-Latvian contributors; maintainers will reply in either language.

## Quick start

```bash
git clone https://github.com/<org>/atmina
cd atmina
python -m venv .venv
.venv/Scripts/activate          # Windows
# source .venv/bin/activate      # Unix
pip install -r requirements.txt
python scripts/patch_twikit.py
bash scripts/check.sh           # ruff + pytest + render smoke
```

Detailed setup: [`wiki/operations/dev-setup.md`](wiki/operations/dev-setup.md).

## Ways to contribute

### Data corrections

If you spot a misattributed claim, an outdated position, a missing politician, or a factual error on [atmina.lv](https://atmina.lv):

1. Open a GitHub issue with the **source URL** of the original article / tweet / vote, the **politician slug** (the URL path on atmina.lv, e.g. `evika-silina`), and the specific error.
2. For politicians wishing to exercise right-of-reply on their own profile, see [`docs/data-policy.md`](docs/data-policy.md).

### Code contributions

Before opening a PR:

1. **Read** [`CLAUDE.md`](CLAUDE.md) — it contains data contracts and pipeline invariants that PRs must respect (Pydantic types, idempotency keys, append-only context notes, etc.).
2. **Branch** from `master`. Name branches by purpose (`fix/saeima-stage-link`, `feat/bluesky-adapter`).
3. **Run** `bash scripts/check.sh` locally — it must pass (ruff + pytest + `generate_public_site` smoke).
4. **Open PR** against `master`. Describe the *why* in the PR body; the *what* belongs in code.

PRs that fail `scripts/check.sh` will not be reviewed until green.

### New data sources

Adding a news source / public registry / parliamentary feed:

1. Propose via issue first. Include ToS / robots.txt status, rate-limit expectations, content licence.
2. Add the source to `sources.yaml` with `tier`, `fetcher_mode`, `legal_status`, `last_tos_review`.
3. Verify ingest works locally and produces correct politician matches.
4. Add at least one fixture test under `tests/fixtures/` and update [`wiki/operations/dev-setup.md`](wiki/operations/dev-setup.md) if setup steps changed.

### Translations

atmina UI text is currently Latvian-only. English / Russian readers are second-tier audiences. Full i18n lands with **M3** (see [README Roadmap](README.md#roadmap)). Until then, only documentation translations are welcome — open an issue first to claim a file.

## Style

- **Python** — `ruff` is the source of truth. Configuration in [`pyproject.toml`](pyproject.toml). Most modern style choices (Pydantic v2 generics, `X | None`) are accepted; some legacy patterns (`List[X]`, `Optional[X]`) coexist for now — don't auto-rewrite.
- **Commits** — conventional-commit style (`fix(profiles):`, `feat(saeima):`, `chore(repo):`, `docs:`). Latvian commit bodies are fine.
- **Comments** — write *why*, not *what*. Default to no comment.
- **Tests** — required for: ingest changes, schema migrations, render path changes, agent prompt changes.

## What we will not merge

- Sentiment-analysis features. We deliberately removed sentiment as unreliable.
- Politician-targeted editorializing in source code or wiki. Neutral, source-cited language only.
- Dependencies under licences incompatible with **AGPL-3.0** (e.g. SSPL, BUSL, Elastic 2.0, proprietary).
- Scraping of non-public registries or auth-walled content.
- Anything that adds advertising, tracking, or user-account functionality to atmina.lv.

## Code of Conduct

Participation in the project is governed by [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) (Contributor Covenant v2.1). Report violations to **info@atmina.lv**.

## Security

For vulnerabilities, **do not open a public issue**. See [`SECURITY.md`](SECURITY.md).

## Maintainer

atmina is maintained by a single developer with a Claude Code agent fleet. Response times vary; expect 1–7 days for issues and PRs. Patience welcome.

## License

By contributing, you agree that your contributions will be licensed under **AGPL-3.0-or-later** (the project's licence). See [`LICENSE`](LICENSE).
