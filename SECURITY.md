# Security policy

## Supported versions

atmina is currently a single-trunk project. Only the `master` branch is supported. There are no semver releases yet — production deployment is rolling from `master`.

## Reporting a vulnerability

Please report security issues **privately** before opening a public issue.

- **E-mail:** info@atmina.lv
- **Subject prefix:** `[atmina-security]`
- **Expected response:** within 72 hours for acknowledgement; coordinated-disclosure window negotiated case by case (default 90 days from acknowledgement).

If the issue affects deployed atmina.lv specifically (rather than the codebase), include the URL path, browser, timestamp, and a description of what you observed.

## What counts as a security issue

| In scope | Out of scope |
|---|---|
| Credential / secret leakage in the repository or git history | Scraped content disputes (use the right-of-reply process — see [`docs/data-policy.md`](docs/data-policy.md)) |
| Vulnerabilities in `src/` code: SQL injection, path traversal, SSRF, deserialization | Bugs in dependencies (report upstream) |
| Pipeline integrity flaws: ways to inject false claims, contradictions, or vote records | Output formatting / typography issues |
| Exposure of private data via the static site or REST API (planned) | Aesthetic issues with atmina.lv |
| Authentication or authorization bypasses in `serve.py` operator dashboard | Theoretical attacks on third-party services we scrape |

## Disclosure preferences

- Coordinated disclosure preferred over full disclosure.
- Credit in `CHANGELOG.md` / commit message if requested.
- No bug-bounty programme exists; reports are accepted in good faith.

## Cryptographic context

- Credentials live in the OS keyring (via `python-keyring`), not in the repository.
- `data/x_cookies.json` and `data/gemini_key.json` are gitignored and never tracked.
- HTTPS is enforced for all outbound API calls (`httpx` defaults).
- No user-account / login system on atmina.lv — public read-only static HTML.

## Past advisories

None as of 2026-05.
