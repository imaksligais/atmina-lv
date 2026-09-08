# Security Audit Report — atmina

_Audit date: 2026-04-14 | Method: STRIDE + OWASP Top 10 | Scope: full src/, templates/, data/_
_Remediation: 2026-04-14 | SEC-01 through SEC-05 FIXED_

## Executive Summary

**Overall posture: STRONG. All critical and high findings remediated.**

The codebase has excellent fundamentals — parameterized SQL everywhere, Jinja2 autoescape enabled, keyring-based credential management, safe YAML loading, no eval/exec. The XSS and supply chain findings identified during audit have been fixed.

| Severity | Count | Status | Category |
|----------|-------|--------|----------|
| CRITICAL | 1 | FIXED | XSS: `wiki_profile \| safe` — now bleach-sanitized |
| HIGH | 8 | FIXED | XSS: `\| safe` on JSON — replaced with `\| safe_json` filter |
| HIGH | 1 | FIXED | Dependency pinning — all 16 packages pinned with `==` |
| MEDIUM | 1 | FIXED | URL href injection — `\| safe_url` filter on 17 template locations |
| MEDIUM | 1 | N/A | File permissions — Windows NTFS ACLs already restrict to owner+admin |
| MEDIUM | 1 | OPEN | twikit PR #411 KEY_BYTE patch — needs manual verification |
| LOW | 4 | OPEN | Error message disclosure, unused credentials, minor issues |

---

## CRITICAL Findings

### SEC-01: XSS via `wiki_profile | safe` in politician.html.j2

**File:** `templates/politician.html.j2:78`
```jinja2
{{ wiki_profile | safe }}
```

**Attack vector:** Wiki markdown files are converted to HTML via Python's `markdown` library and rendered with `|safe`, bypassing Jinja2 autoescaping entirely. If a wiki file contains `<script>alert('XSS')</script>`, it executes in the browser.

**Data flow:** `wiki/persons/*.md` -> `markdown.markdown()` -> `|safe` -> browser

**Risk:** While wiki files are currently operator-controlled, this is a stored XSS vector. Any future automation that writes to wiki (e.g., `wiki_writeback.py`) could inject scripts.

**Remediation:** Sanitize HTML output with `bleach.clean()` before passing to template:
```python
import bleach
ALLOWED_TAGS = ['p', 'h1', 'h2', 'h3', 'h4', 'ul', 'ol', 'li', 'a', 'strong', 'em', 'code', 'pre', 'blockquote', 'table', 'thead', 'tbody', 'tr', 'th', 'td']
wiki_html = bleach.clean(markdown.markdown(wiki_md), tags=ALLOWED_TAGS, attributes={'a': ['href']})
```

---

## HIGH Findings

### SEC-02: XSS via `| safe` on inline JSON data (8 instances)

Multiple templates embed database-sourced JSON directly in `<script>` blocks with `|safe`:

| Template | Line | Variable |
|----------|------|----------|
| `index.html.j2` | 125 | `trends_data \| tojson \| safe` |
| `balsojumi.html.j2` | 344 | `matrix_json \| safe` |
| `statistika.html.j2` | 132 | `trends_data \| tojson \| safe` |
| `statistika.html.j2` | 243-244 | `chart_json \| safe`, `events_json \| safe` |
| `statistika-detail.html.j2` | 133-136 | `graph_data`, `tensions_json`, `claims_json`, `contras_json` |
| `partija.html.j2` | 134 | `party_members_json \| safe` |
| `blog-post.html.j2` | 151 | `cards_json \| safe` |

**Attack vector:** Scraped content (politician names, stances, quotes) flows from web/Twitter into the DB, then into JSON, then into `<script>` blocks. A crafted article title like `</script><script>alert(1)//` could break out of the JSON context.

**Risk:** `json.dumps()` escapes quotes but not `</script>`. Jinja2's `tojson` filter similarly doesn't escape HTML-significant sequences inside `<script>` tags.

**Remediation:** Move JSON data to `<script type="application/json">` elements and parse with `JSON.parse()`:
```html
<script type="application/json" id="trends-data">{{ trends_data | tojson }}</script>
<script>
  var trendsData = JSON.parse(document.getElementById('trends-data').textContent);
</script>
```
This is safe because `<script type="application/json">` content is never executed.

### SEC-03: Unpinned dependencies (supply chain risk)

**File:** `requirements.txt`

All 16 packages are unpinned (no `==` version constraints). A compromised PyPI upload or breaking change would silently propagate.

**Remediation:**
```bash
pip freeze > requirements.lock
# Then pin in requirements.txt with == versions
```

---

## MEDIUM Findings

### SEC-04: JavaScript protocol injection via `href` attributes

~20 template locations render `source_url` from the database in `href` attributes:
```jinja2
<a href="{{ v.source_url }}" target="_blank">
```

Jinja2 autoescaping prevents HTML injection but does NOT prevent `javascript:` protocol URLs. If the DB contains `javascript:alert(1)` as a source_url, it becomes clickable XSS.

**Remediation:** Add URL validation in Python before template rendering:
```python
def safe_url(url):
    if url and url.lower().startswith(('http://', 'https://')):
        return url
    return '#'
```

### SEC-05: World-readable cookie and database files

```
-rw-r--r-- data/x_cookies/1.json   (X/Twitter auth tokens)
-rw-r--r-- data/atmina.db          (scraped content + PII)
-rw-r--r-- data/atmina.db.backup-* (5 backup files)
```

On a multi-user system, any user can read Twitter auth tokens and scraped political data.

**Remediation:**
```bash
chmod 600 data/x_cookies/*.json data/*.db data/*.db.*
```

### SEC-06: twikit PR #411 KEY_BYTE patch not applied

The CLAUDE.md documents two required patches for twikit. The KeyError fix is present but the PR #411 KEY_BYTE fix was not found in the installed version.

**Remediation:** Verify and reapply the patch after any twikit reinstall.

---

## LOW Findings

### SEC-07: Unused credential keys in keyring

`dashboard_password` and `session_secret` are defined in `KNOWN_KEYS` but never used in the codebase. Dead credential references expand the perceived attack surface.

### SEC-08: Error messages may leak social media handles

`src/x_scraper.py` and `src/social.py` log full exception messages that may include Twitter handles. Low risk since handles are public.

### SEC-09: crawl4ai downloads and executes Chromium

`crawl4ai` downloads browser binaries on first use. The scraping is source-whitelisted but the browser binary download itself is a trust-on-first-use risk.

### SEC-10: No CSP headers on static site

The generated static site has no Content-Security-Policy headers. Since it's static HTML served by a web server, CSP should be configured at the server level to prevent inline script execution.

---

## What's GOOD (no findings)

| Area | Status | Notes |
|------|--------|-------|
| SQL injection | PASS | 100% parameterized queries, `?` placeholders throughout |
| Command injection | PASS | No subprocess, os.system, eval, exec usage |
| YAML deserialization | PASS | All `yaml.safe_load()`, never `yaml.load()` |
| SSRF | PASS | URL validation + domain whitelisting in ingest.py |
| Path traversal | PASS | pathlib used throughout, no user-controlled paths |
| Template injection (SSTI) | PASS | Template names hardcoded, autoescape enabled |
| Credential management | PASS | keyring-based, no hardcoded secrets |
| .gitignore coverage | PASS | All sensitive files excluded |
| Static site isolation | PASS | No DB/cookies in output/ |

---

## Remediation Status

| Finding | Status | What was done |
|---------|--------|---------------|
| SEC-01: Wiki HTML XSS | FIXED | Added `bleach.clean()` with allowlisted tags in `_load_wiki_profile()` and `_load_blog_post()` |
| SEC-02: Inline JSON XSS | FIXED | Created `safe_json` Jinja2 filter (escapes `</` to `<\/`), replaced `\|safe` in 11 template locations |
| SEC-03: Dependency pinning | FIXED | All 16 direct deps pinned with `==` in `requirements.txt`, full lockfile in `requirements.lock` |
| SEC-04: URL protocol injection | FIXED | Created `safe_url` Jinja2 filter (validates http/https/mailto), applied to 17 `href` attributes across 8 templates |
| SEC-05: File permissions | N/A | Windows NTFS ACLs already restrict to owner+admin; Git Bash `-rw-r--r--` was emulation artifact |
| SEC-06: twikit KEY_BYTE patch | OPEN | Needs manual verification on next twikit reinstall |
| SEC-07-10: Low severity | OPEN | Minor issues — unused credential keys, error message handles, crawl4ai binary trust, no CSP headers |

### Files changed in remediation

- `src/generate.py` — added `bleach` import, `_sanitize_html()`, `_safe_json_filter()`, `_safe_url_filter()`, registered on both Jinja2 Environments
- `requirements.txt` — pinned all 16 direct dependencies with `==`, added `bleach==6.2.0`
- `requirements.lock` — generated full dependency tree (146 packages)
- 11 templates — `|safe` → `|safe_json` for inline JSON
- 8 templates — added `|safe_url` to database-sourced `href` attributes

### Remaining recommendations

| Priority | Finding | Effort |
|----------|---------|--------|
| 1 | SEC-06: Verify twikit KEY_BYTE patch | 15 min |
| 2 | SEC-10: Add CSP headers at web server level | 15 min |
| 3 | SEC-07: Remove unused `dashboard_password`/`session_secret` from KNOWN_KEYS | 5 min |
