# Cloudflare (Workers Static Assets) migrācijas izpildes plāns

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** atmina.lv statiskā vietne tiek publicēta Cloudflare Workers Static Assets, DNS zona dzīvo Cloudflare, publicēšanas vārti un publiskie URL nemainās.

**Architecture:** Renderis paliek; `output/atmina/` (pilns koks) augšupielādē `npx wrangler deploy` pēc `wrangler.json` (`html_handling: none`, `not_found_handling: 404-page`). `.htaccess` loģika pāriet uz `assets/_headers`; `scripts/deploy.sh` maina tikai transporta zaru, abi preflight vārti paliek priekšā. Četras fāzes, katra ar operatora apstiprinājumu; vecais hostings paliek rezervē 30 dienas.

**Tech Stack:** bash (`scripts/deploy.sh`), Python 3 (`.venv`), pytest, Node 25 + `npx wrangler` (piesprausta versija), Cloudflare bezmaksas plāns.

Spec: `docs/superpowers/specs/2026-09-15-cloudflare-pages-migracija-design.md`.

## Global Constraints

- Vienmēr `.venv/Scripts/python.exe`, nekad bare `python` (CLAUDE.md § Commands).
- Katrs ceļš pēdiņās — mājas direktorijā ir atstarpe.
- Nekā operatoru identificējoša (konta ID, tokeni, hosts, lietotājvārdi) nevienā izsekotā failā; `tests/test_no_deploy_credentials.py` to sargā un jāpaliek zaļam.
- CSP `script-src` NEKAD nesatur `'unsafe-inline'`; CSP vērtība `_headers` failā burtiski = `htaccess.template` vērtība, kamēr abi eksistē.
- Publiskie URL nes `.html` un pēc pārcelšanas atbild 200 bez redirect.
- `deploy.sh` preflight (`check_output.py` + `--publish-gate-only`) notiek PIRMS jebkuras augšupielādes; `--no-delete`, `--delete`, `--dry-run`, `--no-output-check` paliek pieņemti (dashboard `src/dashboard/views/deploy.py` sauc `--no-delete`).
- Katrs deploy = pilns `output/atmina/` koks. Nekad `rmtree output/atmina`.
- Limiti: 20 000 faili/versija, 25 MiB/fails, `_headers` ≤100 rindas.
- Pirms katras fāzes (1–4) — operatora „jā". Fāze 4 tikai pēc fāzes 3 pārbaužu tabulas ar denominatoriem.
- Katrs uzdevums beidzas ar `bash scripts/check.sh` zaļu (ruff + pytest + render smoke) un komitu.

---

## 1. fāze — DNS uz Cloudflare (operatora rokas darbs, bez koda)

### Task 1: DNS zonas eksports, imports, vārdserveru maiņa

**Files:**
- Create (privāts, NEizsekots): `private/dns-atmina-2026-09-XX.txt` — `.gitignore` saknes allow-lists to ignorē automātiski; pārbaudi ar `git check-ignore -v private/dns-atmina-2026-09-XX.txt` (jāizdrukā `.gitignore:23:/*`).

**Interfaces:**
- Produces: Cloudflare zona `atmina.lv` aktīva; e-pasts strādā; `www` uzvedība pierakstīta eksporta failā (vajadzīgs Task 8).

- [ ] **Step 1: Eksportē pašreizējo zonu.** Reģistratora panelī → Advanced DNS → katru rindu (Type, Host, Value, TTL, Priority) pārraksti `private/dns-atmina-2026-09-XX.txt`. Papildus no termināļa, lai eksportam būtu neatkarīgs otrs avots:

```powershell
nslookup -type=A atmina.lv 8.8.8.8
nslookup -type=AAAA atmina.lv 8.8.8.8
nslookup -type=CNAME www.atmina.lv 8.8.8.8
nslookup -type=MX atmina.lv 8.8.8.8
nslookup -type=TXT atmina.lv 8.8.8.8
nslookup -type=TXT _dmarc.atmina.lv 8.8.8.8
nslookup -type=TXT default._domainkey.atmina.lv 8.8.8.8
nslookup -type=CNAME mail.atmina.lv 8.8.8.8
nslookup -type=CNAME autodiscover.atmina.lv 8.8.8.8
```

Pieraksti failā arī: „`www` → apex redirect: JĀ/NĒ; kura puse ir kanoniskā". Denominators: N ierakstu panelī, M no `nslookup` — katram paneļa ierakstam jābūt redzamam DNS (ja nē, tas jau ir miris ieraksts; atzīmē).

- [ ] **Step 2: Cloudflare konts + zona.** dash.cloudflare.com → Add a domain → `atmina.lv` → Free plan → Cloudflare skenē un importē ierakstus.

- [ ] **Step 3: Salīdzini importu ar eksportu rindu pa rindai.** Katram eksporta ierakstam jābūt importā ar identisku vērtību. Trūkstošos pievieno ar roku. Proxy statusa noteikums:
  - MX mērķi, `mail`, `autodiscover`, `autoconfig`, `webmail`, `cpanel`, `ftp`, jebkurš `_`-prefikss un TXT → **DNS only** (pelēks mākonis).
  - `@` (A) un `www` → arī **DNS only** šajā fāzē (sertifikātu joprojām izsniedz vecais hostings; pārslēgšana uz proxy notiek tikai Task 8).

- [ ] **Step 4: Nomaini vārdserverus reģistratorā** uz diviem, ko Cloudflare rāda zonas pārskatā. Cloudflare atsūta e-pastu „zone is active" (līdz 24 h, parasti < 1 h).

- [ ] **Step 5: Pārbaude pēc aktivizēšanas** (denominators: 9 vaicājumi, visiem jāatbilst Step 1 vērtībām):

```powershell
nslookup -type=NS atmina.lv 8.8.8.8      # jārāda *.ns.cloudflare.com
nslookup -type=MX atmina.lv 8.8.8.8      # identisks Step 1
nslookup -type=TXT atmina.lv 8.8.8.8     # SPF identisks Step 1
nslookup -type=TXT _dmarc.atmina.lv 8.8.8.8
nslookup -type=A atmina.lv 8.8.8.8       # vecā hostinga IP (nav Cloudflare IP, jo pelēks)
```

Pēc tam: vietne atveras pārlūkā ar derīgu sertifikātu; nosūti e-pastu NO `@atmina.lv` uz ārēju kasti un atpakaļ — abiem jāpienāk. Ja kaut kas nesakrīt → atgriez vārdserverus reģistratorā uz noklusējumu (zona Cloudflare paliek) un labo.

- [ ] **Step 6: Pieraksti CHANGELOG** `wiki/CHANGELOG.md` augšā ierakstu „2026-09-XX — DNS zona → Cloudflare (1. fāze)": kas darīts, denominatori no Step 1 un Step 5, bez konta datiem. Komits: `git add wiki/CHANGELOG.md && git commit -m "DNS zona uz Cloudflare (migrācijas 1. fāze): N ieraksti pārnesti, pasts pārbaudīts abos virzienos"`.

---

## 2. fāze — servera koka audits

### Task 2: „Kas ir tikai serverī" saraksts un lēmums katram failam

**Files:**
- Create: `scripts/audit_remote_tree.sh`
- Scratch (neizsekots): `private/remote-tree-2026-09-XX.txt`, `private/local-tree-2026-09-XX.txt`

**Interfaces:**
- Consumes: `.env.deploy` (`DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_PORT`, `DEPLOY_PATH`, pēc izvēles `DEPLOY_SSH_KEY`).
- Produces: `private/remote-only-2026-09-XX.txt` — faili, kas ir serverī un nav lokāli; lēmums katram CHANGELOG ierakstā.

- [ ] **Step 1: Uzraksti skriptu**

```bash
#!/usr/bin/env bash
# Salīdzina servera koku ar lokālo output/atmina/ — kas ir TIKAI serverī.
# Lasīšanas režīms: neko nemaina ne serverī, ne lokāli.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env.deploy; set +a
: "${DEPLOY_HOST:?}" "${DEPLOY_USER:?}" "${DEPLOY_PATH:?}"
DEPLOY_PORT="${DEPLOY_PORT:-21098}"
OUT="${1:-private}"
mkdir -p "$OUT"
STAMP="$(date +%F)"
SSH_OPTS=(-p "$DEPLOY_PORT" -o StrictHostKeyChecking=accept-new)
[[ -n "${DEPLOY_SSH_KEY:-}" ]] && SSH_OPTS+=(-o IdentitiesOnly=yes -i "$DEPLOY_SSH_KEY")

ssh "${SSH_OPTS[@]}" "${DEPLOY_USER}@${DEPLOY_HOST}" \
  "cd '${DEPLOY_PATH}' && find . -type f ! -path './.well-known/*' ! -path './cgi-bin/*' | sort" \
  > "$OUT/remote-tree-$STAMP.txt"
( cd output/atmina && find . -type f | sort ) > "$OUT/local-tree-$STAMP.txt"
comm -23 "$OUT/remote-tree-$STAMP.txt" "$OUT/local-tree-$STAMP.txt" > "$OUT/remote-only-$STAMP.txt"
comm -13 "$OUT/remote-tree-$STAMP.txt" "$OUT/local-tree-$STAMP.txt" > "$OUT/local-only-$STAMP.txt"

echo "serverī:        $(wc -l < "$OUT/remote-tree-$STAMP.txt")"
echo "lokāli:         $(wc -l < "$OUT/local-tree-$STAMP.txt")"
echo "tikai serverī:  $(wc -l < "$OUT/remote-only-$STAMP.txt")  -> $OUT/remote-only-$STAMP.txt"
echo "tikai lokāli:   $(wc -l < "$OUT/local-only-$STAMP.txt")  -> $OUT/local-only-$STAMP.txt"
```

- [ ] **Step 2: Palaid** `bash scripts/audit_remote_tree.sh` (Git Bash; `find`, `comm`, `ssh` tur ir). Gaidāms: četras rindas ar skaitļiem; „serverī" ≈ 2 200. Ja „tikai serverī" = 0 UN „serverī" < 1 000 — skripts, visticamāk, lasa nepareizu ceļu (denominators), pārbaudi `DEPLOY_PATH`.

- [ ] **Step 3: Lēmums katram tikai-serverī failam.** Atver `private/remote-only-*.txt`. Kategorijas:
  - `images/briefs/*.webp|jpg|png` — nokopē lokāli uz `output/images/briefs/` (renderis tos pārkopē uz `output/atmina/images/briefs/`): `scp -P "$DEPLOY_PORT" "user@host:$DEPLOY_PATH/images/briefs/<fails>" "output/images/briefs/"`.
  - `.htaccess`, `.well-known/*`, `cgi-bin/*`, `error_log`, `*.php` — servera artefakti, atmet.
  - viss cits — nosauc failu, izlem, pieraksti.
  Pēc kopēšanas palaid Step 2 vēlreiz: „tikai serverī" drīkst saturēt tikai apzināti atmestos.

- [ ] **Step 4: `bash scripts/check.sh`** — zaļš (skripts ir bash, ruff to neskata; smoke renders nepieskaras).

- [ ] **Step 5: CHANGELOG + komits.** Ieraksts „2026-09-XX — servera koka audits (2. fāze)": N serverī / M lokāli / K tikai serverī, saraksts ar lēmumu katram (bez hosta/ceļa datiem).

```bash
git add scripts/audit_remote_tree.sh wiki/CHANGELOG.md
git commit -m "Servera koka audits pirms Cloudflare (2. fāze): K tikai-serverī faili, lēmums katram; scripts/audit_remote_tree.sh"
```

---

## 3. fāze — Workers projekts paralēli vecajam hostingam

### Task 3: `assets/_headers` ar testu, kas to lasa pret `htaccess.template`

**Files:**
- Create: `assets/_headers`
- Test: `tests/test_headers_file.py`

**Interfaces:**
- Produces: `assets/_headers` Cloudflare formātā (`/patern` rinda, tad `  Nosaukums: vērtība` rindas). Task 4 to kopē uz `output/atmina/_headers`.

- [ ] **Step 1: Uzraksti testu**

```python
"""`assets/_headers` (Cloudflare) sargi: lasa to, ko rakstītājs raksta.

Kamēr `assets/htaccess.template` eksistē (vecais hostings rezervē), abiem
failiem jānes IDENTISKA CSP un tie paši drošības galveņu nosaukumi.
`script-src` nekad nesatur 'unsafe-inline' (CLAUDE.md § No inline JavaScript).
"""
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_HEADERS = _ROOT / "assets" / "_headers"
_HTACCESS = _ROOT / "assets" / "htaccess.template"


def _parse_headers_file(text: str) -> dict[str, dict[str, str]]:
    """{ceļa_paterns: {nosaukums: vērtība}} — Cloudflare `_headers` formāts."""
    rules: dict[str, dict[str, str]] = {}
    current = None
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if not raw.startswith((" ", "\t")):
            current = raw.strip()
            rules[current] = {}
            continue
        assert current is not None, f"galvene bez ceļa: {raw!r}"
        name, _, value = raw.strip().partition(":")
        rules[current][name.strip()] = value.strip()
    return rules


def _htaccess_headers() -> dict[str, str]:
    text = _HTACCESS.read_text(encoding="utf-8")
    found = dict(re.findall(r'Header always set (\S+) "([^"]*)"', text))
    assert len(found) >= 5, f"htaccess.template denominators sabrucis: {found}"
    return found


def test_headers_file_exists_and_has_root_rule():
    rules = _parse_headers_file(_HEADERS.read_text(encoding="utf-8"))
    assert "/*" in rules, f"nav /* kārtulas; ir: {list(rules)}"
    assert len(_HEADERS.read_text(encoding="utf-8").splitlines()) <= 100


def test_every_htaccess_security_header_is_carried_over():
    root = _parse_headers_file(_HEADERS.read_text(encoding="utf-8"))["/*"]
    for name, value in _htaccess_headers().items():
        assert name in root, f"{name} trūkst _headers /* kārtulā"
        assert root[name] == value, f"{name} atšķiras:\n  htaccess: {value}\n  _headers: {root[name]}"


def test_script_src_has_no_unsafe_inline():
    root = _parse_headers_file(_HEADERS.read_text(encoding="utf-8"))["/*"]
    csp = root["Content-Security-Policy"]
    script_src = next(p for p in csp.split(";") if p.strip().startswith("script-src"))
    assert "'unsafe-inline'" not in script_src


def test_cache_rules_cover_json_and_assets():
    rules = _parse_headers_file(_HEADERS.read_text(encoding="utf-8"))
    assert "/*.json" in rules and "max-age=300" in rules["/*.json"]["Cache-Control"]
    assert "/assets/*" in rules and "max-age=86400" in rules["/assets/*"]["Cache-Control"]
    assert "/images/*" in rules and "max-age=604800" in rules["/images/*"]["Cache-Control"]
```

- [ ] **Step 2: Palaid, sagaidi FAIL** — `.venv/Scripts/python.exe -m pytest tests/test_headers_file.py -v` → `FileNotFoundError: assets/_headers`.

- [ ] **Step 3: Uzraksti `assets/_headers`.** CSP rinda jāpārkopē BURTISKI no `htaccess.template` (`Header always set Content-Security-Policy "..."` iekšpuse):

```
# atmina.lv — Cloudflare Workers Static Assets galvenes.
# Avots līdz vecā hostinga izslēgšanai: assets/htaccess.template (CSP vērtībai
# jābūt identiskai — tests/test_headers_file.py). Pēc tam šis ir vienīgais avots.
# script-src bez 'unsafe-inline' — apzināts drošības lēmums (CLAUDE.md).

/*
  Strict-Transport-Security: max-age=31536000
  X-Content-Type-Options: nosniff
  X-Frame-Options: SAMEORIGIN
  Referrer-Policy: strict-origin-when-cross-origin
  Content-Security-Policy: default-src 'self'; script-src 'self' https://cloud.umami.is; style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self' data:; connect-src 'self' https://gateway.umami.is https://cloud.umami.is; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'self'

# JSON dati — īss kešs, lai dienas rutīnas atjauninājumi iet cauri
/*.json
  Cache-Control: public, max-age=300
/data/*
  Cache-Control: public, max-age=300

# Statiskie aseti — ?v= versionēti
/assets/*
  Cache-Control: public, max-age=86400

/images/*
  Cache-Control: public, max-age=604800
```

- [ ] **Step 4: Palaid, sagaidi PASS** (4 testi). Ja `test_every_htaccess_security_header_is_carried_over` krīt uz CSP — pārkopē vērtību vēlreiz, nelabo ar roku.

- [ ] **Step 5: `bash scripts/check.sh` zaļš; komits**

```bash
git add assets/_headers tests/test_headers_file.py
git commit -m "assets/_headers Cloudflare formātā — CSP identiska htaccess.template, tests lasa abus (3. fāze)"
```

### Task 4: Renderis kopē `_headers` (un `_redirects`) līdzās `.htaccess`

**Files:**
- Modify: `src/render/_orchestrator.py:478-485` (14a solis)
- Test: `tests/test_host_config_copy.py`

**Interfaces:**
- Produces: `src.render._orchestrator._copy_host_config(atmina_dir: Path) -> list[str]` — atgriež nokopēto failu nosaukumus.

- [ ] **Step 1: Tests**

```python
"""Renderis kopē hostinga konfigurācijas failus no assets/ uz koka sakni.

Kamēr vecais hostings ir rezervē: .htaccess (no htaccess.template) UN _headers.
_redirects — tikai ja assets/_redirects eksistē.
"""
from pathlib import Path

import src.render._orchestrator as orch


def test_copies_htaccess_and_headers(tmp_path, monkeypatch):
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "htaccess.template").write_text("RewriteEngine On\n", encoding="utf-8")
    (assets / "_headers").write_text("/*\n  X-Test: 1\n", encoding="utf-8")
    monkeypatch.setattr(orch, "ASSETS_DIR", assets)
    out = tmp_path / "atmina"
    out.mkdir()

    copied = orch._copy_host_config(out)

    assert sorted(copied) == [".htaccess", "_headers"]
    assert (out / ".htaccess").read_text(encoding="utf-8") == "RewriteEngine On\n"
    assert (out / "_headers").read_text(encoding="utf-8") == "/*\n  X-Test: 1\n"
    assert not (out / "_redirects").exists()


def test_copies_redirects_when_present(tmp_path, monkeypatch):
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "_redirects").write_text("/vecais /jaunais.html 301\n", encoding="utf-8")
    monkeypatch.setattr(orch, "ASSETS_DIR", assets)
    out = tmp_path / "atmina"
    out.mkdir()

    assert orch._copy_host_config(out) == ["_redirects"]
    assert (out / "_redirects").exists()


def test_real_assets_dir_yields_both_files(tmp_path):
    out = tmp_path / "atmina"
    out.mkdir()
    copied = orch._copy_host_config(out)
    assert ".htaccess" in copied and "_headers" in copied, copied
```

- [ ] **Step 2: FAIL** — `.venv/Scripts/python.exe -m pytest tests/test_host_config_copy.py -v` → `AttributeError: _copy_host_config`.

- [ ] **Step 3: Implementācija.** `src/render/_orchestrator.py`: pievieno moduļa līmeņa funkciju (blakus `_copy_curated` importam, virs `generate_public_site`):

```python
def _copy_host_config(atmina_dir: Path) -> list[str]:
    """Hostinga konfigurācija no assets/ uz koka sakni. output/ ir gitignorēts,
    tāpēc avots ir izsekotie faili assets/.

    .htaccess  — vecais LiteSpeed hostings (rezervē līdz migrācijas 4. fāzes
                 beigām; tad htaccess.template + šī rinda izņemama).
    _headers   — Cloudflare Workers Static Assets galvenes (CSP u.c.).
    _redirects — tikai ja assets/_redirects eksistē (šobrīd nav).
    """
    pairs = (
        ("htaccess.template", ".htaccess"),
        ("_headers", "_headers"),
        ("_redirects", "_redirects"),
    )
    copied: list[str] = []
    for src_name, dest_name in pairs:
        src = ASSETS_DIR / src_name
        if src.exists():
            (atmina_dir / dest_name).write_text(
                src.read_text(encoding="utf-8"), encoding="utf-8"
            )
            copied.append(dest_name)
    return copied
```

un 14a soli aizstāj ar:

```python
        # 14a. Hostinga konfigurācija (.htaccess + _headers [+ _redirects]).
        logger.info("Host config copied: %s", _copy_host_config(atmina_dir))
```

- [ ] **Step 4: PASS** (3 testi). Pēc tam `.venv/Scripts/python.exe -m src.render --only=static` un `ls -la output/atmina/_headers output/atmina/.htaccess` — abi eksistē.

- [ ] **Step 5: check.sh + komits**

```bash
git add src/render/_orchestrator.py tests/test_host_config_copy.py
git commit -m "Renderis kopē assets/_headers (+_redirects) līdzās .htaccess — _copy_host_config (3. fāze)"
```

### Task 5: `wrangler.json` + `.gitignore` + versijas piespraude

**Files:**
- Create: `wrangler.json`
- Modify: `.gitignore` (saknes allow-lists, pēc `!/.env.deploy.example`)
- Modify: `.env.deploy.example`
- Test: `tests/test_wrangler_config.py`

**Interfaces:**
- Produces: `wrangler.json` ar `name: "atmina"`, `assets.directory: "./output/atmina"`, `html_handling: "none"`, `not_found_handling: "404-page"`. Task 6 to lasa netieši (`wrangler deploy` bez argumentiem).

- [ ] **Step 1: Tests**

```python
"""wrangler.json invarianti — publiskie URL nes .html un NEDRĪKST saņemt redirect."""
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_CFG = _ROOT / "wrangler.json"


def _cfg() -> dict:
    return json.loads(_CFG.read_text(encoding="utf-8"))


def test_wrangler_config_is_tracked():
    import subprocess
    out = subprocess.run(["git", "ls-files", "wrangler.json"], capture_output=True, text=True, cwd=_ROOT)
    assert out.stdout.strip() == "wrangler.json", "wrangler.json nav git kokā — .gitignore allow-list"


def test_assets_block_keeps_html_urls_as_is():
    a = _cfg()["assets"]
    assert a["directory"] == "./output/atmina"
    assert a["html_handling"] == "none"
    assert a["not_found_handling"] == "404-page"


def test_no_account_identifiers_in_config():
    text = _CFG.read_text(encoding="utf-8")
    assert "account_id" not in text
    assert "api_token" not in text.lower()
```

- [ ] **Step 2: FAIL** — `FileNotFoundError: wrangler.json`.

- [ ] **Step 3: Faili.**

`wrangler.json`:

```json
{
  "$schema": "node_modules/wrangler/config-schema.json",
  "name": "atmina",
  "compatibility_date": "2026-09-01",
  "assets": {
    "directory": "./output/atmina",
    "html_handling": "none",
    "not_found_handling": "404-page"
  }
}
```

`.gitignore` — pēc rindas `!/.env.deploy.example` pievieno:

```
!/wrangler.json
```

`.env.deploy.example` — pievieno beigās:

```
# Cloudflare (Workers Static Assets) — migrācija 2026-09. Token ar TIKAI
# "Workers Scripts:Edit" tiesībām (dash.cloudflare.com → My Profile → API Tokens).
# Account ID: dash.cloudflare.com → Workers & Pages → labajā malā.
CLOUDFLARE_API_TOKEN=cf-token-here
CLOUDFLARE_ACCOUNT_ID=cf-account-id-here
```

- [ ] **Step 4: Versijas piespraude.** `npm view wrangler version` → pieraksti (piem. `4.x.y`). To izmanto Task 6 kā `WRANGLER_CMD` noklusējumu un Task 7 `deploy.md`.

- [ ] **Step 5: PASS**; `bash scripts/check.sh` zaļš (tests `test_no_deploy_credentials` skenē `.env.deploy` vērtības — īstais token/ID `.env.deploy` failā vēl nav, tāpēc skip vai zaļš).

- [ ] **Step 6: Komits**

```bash
git add wrangler.json .gitignore .env.deploy.example tests/test_wrangler_config.py
git commit -m "wrangler.json (html_handling none, 404-page) + .gitignore allow + .env.deploy.example CF atslēgas (3. fāze)"
```

### Task 6: `scripts/deploy.sh` — rsync zars → `wrangler deploy`, preflight nemainīts

**Files:**
- Modify: `scripts/deploy.sh` (rindas ~14–22 env ielāde; ~40–76 karogi; 114–223 rsync/ssh bloks → aizstāj)
- Test: `tests/test_deploy_script.py`

**Interfaces:**
- Consumes: `.env.deploy` ar `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`.
- Produces: `deploy.sh` ar env pārrakstīm `DEPLOY_ENV_FILE` (noklusējums `.env.deploy`) un `WRANGLER_CMD` (noklusējums `npx wrangler@<piespraustā>`), karogi `--dry-run`, `--no-output-check`, `--no-delete`/`--delete` (no-op ar paziņojumu).

- [ ] **Step 1: Tests** (bash izpilde caur subprocess; stub wrangler; preflight izlaists ar `--no-output-check`, jo tas ir pārbaudīts `tests/test_check_output.py`):

```python
"""deploy.sh transporta zars: wrangler, nevis rsync; preflight paliek priekšā."""
import os
import subprocess
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "deploy.sh"


def _run(tmp_path: Path, *flags: str, env_text: str | None = None) -> subprocess.CompletedProcess:
    env_file = tmp_path / "env"
    env_file.write_text(
        env_text if env_text is not None
        else "CLOUDFLARE_API_TOKEN=t\nCLOUDFLARE_ACCOUNT_ID=a\n",
        encoding="utf-8",
    )
    env = dict(os.environ)
    env["DEPLOY_ENV_FILE"] = str(env_file)
    env["WRANGLER_CMD"] = "echo WRANGLER-STUB"
    return subprocess.run(
        ["bash", str(_SCRIPT), "--no-output-check", *flags],
        capture_output=True, text=True, cwd=_ROOT, env=env, check=False,
    )


@pytest.mark.skipif(not (_ROOT / "output" / "atmina").is_dir(), reason="nav output/atmina")
def test_deploy_calls_wrangler_deploy(tmp_path):
    r = _run(tmp_path)
    assert r.returncode == 0, r.stderr
    assert "WRANGLER-STUB deploy" in r.stdout


@pytest.mark.skipif(not (_ROOT / "output" / "atmina").is_dir(), reason="nav output/atmina")
def test_dry_run_never_calls_wrangler(tmp_path):
    r = _run(tmp_path, "--dry-run")
    assert r.returncode == 0, r.stderr
    assert "WRANGLER-STUB" not in r.stdout
    assert "faili kokā:" in r.stdout


@pytest.mark.skipif(not (_ROOT / "output" / "atmina").is_dir(), reason="nav output/atmina")
def test_legacy_delete_flags_are_accepted_noops(tmp_path):
    r = _run(tmp_path, "--no-delete", "--dry-run")
    assert r.returncode == 0, r.stderr
    assert "no-op" in r.stdout + r.stderr


def test_missing_token_stops_before_anything(tmp_path):
    r = _run(tmp_path, env_text="CLOUDFLARE_ACCOUNT_ID=a\n")
    assert r.returncode != 0
    assert "CLOUDFLARE_API_TOKEN" in r.stderr
    assert "WRANGLER-STUB" not in r.stdout


def test_no_rsync_left_in_script():
    text = _SCRIPT.read_text(encoding="utf-8")
    assert "rsync" not in text.split("# --- transports", 1)[-1]
```

- [ ] **Step 2: FAIL** — `.venv/Scripts/python.exe -m pytest tests/test_deploy_script.py -v` (pirmie trīs krīt uz `DEPLOY_HOST missing`, pēdējais uz `rsync`).

- [ ] **Step 3: Pārraksti `scripts/deploy.sh`.** Saglabā: karogu cilpu (ar pielāgotiem tekstiem), preflight bloku (rindas ~78–112) NEMAINĪTU. Aizstāj env ielādi un visu no `echo ">> Deploying ..."` līdz beigām:

Galva (aizstāj rindas 4–22):

```bash
# Deploy output/atmina/ uz Cloudflare Workers Static Assets (wrangler deploy).
# Konfigurācija: wrangler.json (html_handling none — publiskie URL nes .html).
# Akreditācija: .env.deploy (gitignored) — CLOUDFLARE_API_TOKEN + CLOUDFLARE_ACCOUNT_ID.
# Līdz 2026-09 šis skripts rsync-oja uz koplietoto hostingu; vēsture git logā.

cd "$(dirname "$0")/.."

DEPLOY_ENV_FILE="${DEPLOY_ENV_FILE:-.env.deploy}"
if [[ ! -f "$DEPLOY_ENV_FILE" ]]; then
  echo "ERROR: $DEPLOY_ENV_FILE not found. Copy .env.deploy.example and fill in." >&2
  exit 1
fi
set -a
# shellcheck disable=SC1090
source "$DEPLOY_ENV_FILE"
set +a

: "${CLOUDFLARE_API_TOKEN:?missing in $DEPLOY_ENV_FILE}"
: "${CLOUDFLARE_ACCOUNT_ID:?missing in $DEPLOY_ENV_FILE}"
export CLOUDFLARE_API_TOKEN CLOUDFLARE_ACCOUNT_ID
WRANGLER_CMD="${WRANGLER_CMD:-npx wrangler@4.x.y}"   # piesprausta versija — sk. wiki/operations/deploy.md
```

Karogu cilpā: `--no-delete` un `--delete` zaros aizstāj esošo saturu ar

```bash
    --no-delete|--delete)
      # Cloudflare deploy vienmēr ir PILNS koks — additīvā/destruktīvā režīma vairs
      # nav. Karogi paliek pieņemti, jo katrs runbooks un dashboard tos padod.
      echo ">> $arg — no-op kopš Cloudflare migrācijas (deploy vienmēr ir pilns koks)"
      ;;
```

Transporta bloks (aizstāj visu no `echo ">> Deploying $SRC -> ..."` līdz `echo ">> Done."`):

```bash
# --- transports: Cloudflare Workers Static Assets -------------------------
FILE_COUNT="$(find "$SRC" -type f | wc -l | tr -d ' ')"
BIG="$(find "$SRC" -type f -size +25M | head -5)"
echo ">> faili kokā: ${FILE_COUNT} (limits 20 000 / versija)"
if (( FILE_COUNT > 15000 )); then
  echo ">> WARNING: ${FILE_COUNT} faili — tuvojas 20 000 limitam" >&2
fi
if [[ -n "$BIG" ]]; then
  echo "ERROR: faili virs 25 MiB (Cloudflare limits):" >&2
  echo "$BIG" >&2
  exit 1
fi
if [[ ! -f "${SRC}_headers" ]]; then
  echo "ERROR: ${SRC}_headers trūkst — renderē 'static' domēnu (assets/_headers → koks)." >&2
  exit 1
fi

if [[ -n "$DRY_RUN" ]]; then
  echo ">> DRY RUN beidzas šeit — wrangler netiek saukts."
  exit 0
fi

echo ">> $WRANGLER_CMD deploy (wrangler.json → ${SRC})"
# shellcheck disable=SC2086
$WRANGLER_CMD deploy
echo ">> Done."
```

Izņem arī `DEPLOY_HOST/USER/PATH/PORT` `:?` pārbaudes un `SRC_PATH`, `SSH_BIN`, `SSH_EXTRA`, WSL zaru. `SRC="output/atmina/"` paliek.

- [ ] **Step 4: PASS** (5 testi). `bash scripts/deploy.sh --dry-run --no-delete` ar īsto `.env.deploy` (ar aizpildītām CF atslēgām) → preflight abi vārti + `faili kokā: NNNN` + `DRY RUN beidzas šeit`.

- [ ] **Step 5: `bash scripts/check.sh` zaļš.** Pārbaudi `tests/test_no_deploy_credentials.py` — īstais token un konta ID `.env.deploy` failā nedrīkst parādīties izsekotos failos (tie tur nav; tests to pierāda).

- [ ] **Step 6: Komits**

```bash
git add scripts/deploy.sh tests/test_deploy_script.py
git commit -m "deploy.sh: rsync → wrangler deploy; preflight vārti nemainīti, --no-delete/--delete no-op, failu skaita + 25 MiB vārts (3. fāze)"
```

### Task 7: Pārbaudes skripts + pirmais deploy uz `workers.dev`

**Files:**
- Create: `scripts/verify_host.py`
- Test: `tests/test_verify_host.py`
- Modify: `wiki/operations/deploy.md` (jauna sadaļa augšā), `wiki/CHANGELOG.md`

**Interfaces:**
- Produces: `scripts/verify_host.py --base https://<host> [--sample 20] [--sitemap output/atmina/sitemap.xml]` — drukā tabulu ar denominatoriem, exit 1 ja kāda pārbaude krīt. Task 8 to palaiž uz `https://atmina.lv`.
- Iekšēji: `run_checks(base: str, sitemap_urls: list[str], fetch: Callable[[str], Response]) -> list[Check]`, kur `Response = namedtuple("Response", "status headers body")`, `Check = namedtuple("Check", "name passed examined detail")`.

- [ ] **Step 1: Tests**

```python
"""verify_host.py — katra pārbaude ziņo, cik ko apskatīja (denominators)."""
import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("verify_host", _ROOT / "scripts" / "verify_host.py")
vh = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vh)

CSP = "default-src 'self'; script-src 'self' https://cloud.umami.is"


def _fake_site(redirect_html: bool = False):
    def fetch(url: str) -> vh.Response:
        path = url.split("//", 1)[1].split("/", 1)[1] if "/" in url.split("//", 1)[1] else ""
        h = {"content-security-policy": CSP, "strict-transport-security": "max-age=31536000"}
        if path.endswith(".html"):
            if redirect_html:
                return vh.Response(308, {"location": "/" + path[:-5]}, b"")
            return vh.Response(200, h, b"<html>ok</html>")
        if path.endswith(".json"):
            return vh.Response(200, {**h, "content-encoding": "br"}, b"{}")
        if path == "404.html" or path == "nav-tada-lapa-xyz":
            return vh.Response(404 if path != "404.html" else 200, h, b"<html>Lapa nav atrasta</html>")
        if path in ("robots.txt", "sitemap.xml", "finanses.html", "statistika.html"):
            return vh.Response(200, h, b"x")
        if path.startswith("images/briefs/"):
            return vh.Response(200, h, b"png")
        return vh.Response(404, h, b"")
    return fetch


SITEMAP = [f"https://atmina.lv/politiki/p{i}.html" for i in range(30)]


def test_all_checks_pass_on_good_host():
    checks = vh.run_checks("https://x.example", SITEMAP, _fake_site(), sample=20,
                           hero_paths=["images/briefs/a.png", "images/briefs/b.png"])
    assert all(c.passed for c in checks), [c for c in checks if not c.passed]
    by = {c.name: c for c in checks}
    assert by["sitemap_html_200_no_redirect"].examined == 20
    assert by["hero_images"].examined == 2


def test_html_redirect_is_a_failure():
    checks = vh.run_checks("https://x.example", SITEMAP, _fake_site(redirect_html=True), sample=5,
                           hero_paths=[])
    by = {c.name: c for c in checks}
    assert not by["sitemap_html_200_no_redirect"].passed
    assert "308" in by["sitemap_html_200_no_redirect"].detail


def test_zero_denominator_is_a_failure():
    checks = vh.run_checks("https://x.example", [], _fake_site(), sample=20, hero_paths=[])
    by = {c.name: c for c in checks}
    assert not by["sitemap_html_200_no_redirect"].passed
    assert by["sitemap_html_200_no_redirect"].examined == 0
```

- [ ] **Step 2: FAIL** — `FileNotFoundError: scripts/verify_host.py`.

- [ ] **Step 3: Skripts**

```python
"""Dzīvā hosta pārbaude pēc deploy — katra rinda ar denominatoru.

  .venv/Scripts/python.exe scripts/verify_host.py --base https://atmina.<konts>.workers.dev
  .venv/Scripts/python.exe scripts/verify_host.py --base https://atmina.lv

Pārbaudes (spec 3. fāze): drošības galvenes uz 3 lapām; sitemap paraugs → 200
bez redirect (html_handling none vārts); nezināms URL → 404 ar 404.html saturu;
robots/sitemap; sidecar JSON saspiests; kurētais saturs; hero attēlu paraugs.
Exit 1, ja kāda krīt VAI kādas denominators ir 0.
"""
from __future__ import annotations

import argparse
import random
import re
import sys
from collections import namedtuple
from pathlib import Path
from typing import Callable

import httpx

Response = namedtuple("Response", "status headers body")
Check = namedtuple("Check", "name passed examined detail")

_REQUIRED_HEADERS = (
    "content-security-policy",
    "strict-transport-security",
    "x-content-type-options",
    "x-frame-options",
    "referrer-policy",
)
_JSON_SIDECARS = ("pozicijas-data.json", "data/balsojumi-matrica.json")


def http_fetch(url: str) -> Response:
    r = httpx.get(url, follow_redirects=False, timeout=20,
                  headers={"accept-encoding": "br, gzip"})
    return Response(r.status_code, {k.lower(): v for k, v in r.headers.items()}, r.content)


def sitemap_urls(path: Path) -> list[str]:
    return re.findall(r"<loc>([^<]+)</loc>", path.read_text(encoding="utf-8"))


def _path_of(url: str) -> str:
    return url.split("//", 1)[1].split("/", 1)[1] if "/" in url.split("//", 1)[1] else ""


def run_checks(base: str, sitemap: list[str], fetch: Callable[[str], Response],
               sample: int = 20, hero_paths: list[str] | None = None,
               rng: random.Random | None = None) -> list[Check]:
    rng = rng or random.Random(0)
    base = base.rstrip("/")
    out: list[Check] = []

    # 1. drošības galvenes uz 3 lapām
    pages = ["index.html", "personas.html", "blog.html"]
    missing = []
    for p in pages:
        r = fetch(f"{base}/{p}")
        for h in _REQUIRED_HEADERS:
            if h not in r.headers:
                missing.append(f"{p}:{h}")
        if "'unsafe-inline'" in r.headers.get("content-security-policy", "").split("style-src")[0]:
            missing.append(f"{p}:script-src unsafe-inline")
    out.append(Check("security_headers", not missing, len(pages), ", ".join(missing) or "ok"))

    # 2. sitemap paraugs: .html → 200, bez 30x
    html = [u for u in sitemap if u.endswith(".html")]
    picked = rng.sample(html, min(sample, len(html))) if html else []
    bad = []
    for u in picked:
        r = fetch(f"{base}/{_path_of(u)}")
        if r.status != 200:
            bad.append(f"{_path_of(u)} → {r.status}")
    out.append(Check("sitemap_html_200_no_redirect", bool(picked) and not bad,
                     len(picked), "; ".join(bad[:5]) or "ok"))

    # 3. 404 ar 404.html saturu
    r404 = fetch(f"{base}/nav-tada-lapa-xyz")
    page404 = fetch(f"{base}/404.html")
    ok404 = r404.status == 404 and page404.status == 200 and r404.body == page404.body
    out.append(Check("custom_404", ok404, 2, f"status {r404.status}, body match {r404.body == page404.body}"))

    # 4. robots + sitemap
    rs = [fetch(f"{base}/robots.txt").status, fetch(f"{base}/sitemap.xml").status]
    out.append(Check("robots_sitemap", rs == [200, 200], 2, str(rs)))

    # 5. sidecar JSON saspiests
    enc = []
    for j in _JSON_SIDECARS:
        r = fetch(f"{base}/{j}")
        enc.append(f"{j}:{r.status}/{r.headers.get('content-encoding', '-')}")
    ok_json = all(":200/" in e and e.split("/")[-1] in ("br", "gzip") for e in enc)
    out.append(Check("json_compressed", ok_json, len(_JSON_SIDECARS), ", ".join(enc)))

    # 6. kurētais saturs
    cur = ["finanses.html", "statistika.html"]
    st = [fetch(f"{base}/{c}").status for c in cur]
    out.append(Check("curated_present", st == [200, 200], len(cur), str(st)))

    # 7. hero attēli
    heroes = hero_paths or []
    hs = [(h, fetch(f"{base}/{h}").status) for h in heroes]
    badh = [f"{h}→{s}" for h, s in hs if s != 200]
    out.append(Check("hero_images", bool(hs) and not badh, len(hs), "; ".join(badh[:5]) or "ok"))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True)
    ap.add_argument("--sample", type=int, default=20)
    ap.add_argument("--sitemap", default="output/atmina/sitemap.xml")
    ap.add_argument("--heroes", type=int, default=10, help="cik pārskatu hero attēlu paraugā")
    a = ap.parse_args(argv)

    briefs = sorted(Path("output/atmina/images/briefs").glob("*.png"))
    hero_paths = [f"images/briefs/{p.name}" for p in briefs[-a.heroes:]]
    checks = run_checks(a.base, sitemap_urls(Path(a.sitemap)), http_fetch,
                        sample=a.sample, hero_paths=hero_paths)
    width = max(len(c.name) for c in checks)
    for c in checks:
        print(f"{'PASS' if c.passed else 'FAIL'}  {c.name:<{width}}  n={c.examined:<3}  {c.detail}")
    failed = [c for c in checks if not c.passed]
    print(f"{len(checks) - len(failed)}/{len(checks)} pārbaudes zaļas")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
```

Sidecar vārdi pārbaudīti 2026-09-15: `output/atmina/pozicijas-data.json`, `output/atmina/data/balsojumi-matrica.json`; kurētie: `finanses.html`, `statistika.html`.

- [ ] **Step 4: PASS** (3 testi); `ruff check scripts/verify_host.py` tīrs.

- [ ] **Step 5: Cloudflare token + pirmais deploy (operators).** dash.cloudflare.com → API Tokens → Create → Custom: `Account · Workers Scripts · Edit`, tikai šis konts. Account ID no Workers & Pages lapas. Ieraksti abus `.env.deploy`. Tad:

```bash
bash scripts/deploy.sh --dry-run --no-delete     # preflight + skaits, bez sūtīšanas
bash scripts/deploy.sh --no-delete               # pirmais īstais — wrangler izdrukā https://atmina.<konts>.workers.dev
```

Ja `wrangler` prasa interaktīvu login — token nav eksportēts; pārbaudi `DEPLOY_ENV_FILE` ceļu.

- [ ] **Step 6: Pārbaude uz workers.dev** — `.venv/Scripts/python.exe scripts/verify_host.py --base https://atmina.<konts>.workers.dev`. Gaidāms `7/7 pārbaudes zaļas`, katra ar `n=`. Papildus ar roku: atver lapu pārlūkā, DevTools → Network → Umami `gateway.umami.is` pieprasījums 2xx (CSP neblokē). Ja `sitemap_html_200_no_redirect` krīt ar 30x — `wrangler.json` `html_handling` nav `none`.

- [ ] **Step 7: Dokumentācija.** `wiki/operations/deploy.md` augšā jauna sadaļa „## Cloudflare (kopš 2026-09-XX)": komandas (`--dry-run`, deploy, `verify_host.py`), `wrangler` piespraustā versija, token tiesības, ka `--no-delete` ir no-op, ka deploy vienmēr pilns koks; veco Namecheap sadaļu virsraksts → „## Vecais hostings (rezervē līdz 2026-10-XX)". `wiki/CHANGELOG.md` ieraksts „3. fāze": `verify_host.py` tabula ar n=.

- [ ] **Step 8: check.sh + komits**

```bash
git add scripts/verify_host.py tests/test_verify_host.py wiki/operations/deploy.md wiki/CHANGELOG.md
git commit -m "verify_host.py (7 pārbaudes ar denominatoru) + pirmais deploy uz workers.dev; deploy.md Cloudflare sadaļa (3. fāze)"
```

---

## 4. fāze — pārslēgšana un rezerve

### Task 8: Custom domain, `www` redirect, pārbaude uz atmina.lv

**Files:**
- Modify: `wrangler.json` (pievieno `routes`)
- Modify: `tests/test_wrangler_config.py` (pievieno testu)
- Modify: `wiki/CHANGELOG.md`

**Interfaces:**
- Consumes: Task 1 pieraksts par `www` uzvedību; Task 7 `verify_host.py`.

- [ ] **Step 1: Tests** — pievieno `tests/test_wrangler_config.py` beigās:

```python
def test_routes_bind_apex_and_www_as_custom_domains():
    routes = _cfg()["routes"]
    patterns = {r["pattern"] for r in routes}
    assert patterns == {"atmina.lv", "www.atmina.lv"}
    assert all(r.get("custom_domain") is True for r in routes)
```

- [ ] **Step 2: FAIL** (`KeyError: 'routes'`).

- [ ] **Step 3: `wrangler.json`** — pievieno pēc `"compatibility_date"`:

```json
  "routes": [
    { "pattern": "atmina.lv", "custom_domain": true },
    { "pattern": "www.atmina.lv", "custom_domain": true }
  ],
```

Cloudflare pati aizstās esošos `@`/`www` A/CNAME ierakstus ar Workers ierakstiem (dash brīdina, ja ieraksts konfliktē — tad dzēs veco A ierakstu Cloudflare DNS panelī pirms deploy; vecā hostinga IP jau ir pierakstīts Task 1 eksportā atpakaļceļam).

- [ ] **Step 4: PASS**; `bash scripts/deploy.sh --no-delete` — wrangler piesaista domēnus, izsniedz sertifikātu (minūtes).

- [ ] **Step 5: `www` redirect** — Cloudflare dash → zona → Rules → Redirect Rules → „www → apex" (vai otrādi, kā Task 1 fiksēts): `(http.host eq "www.atmina.lv")` → `concat("https://atmina.lv", http.request.uri.path)`, 301. Pārbaude: `curl -sI https://www.atmina.lv/personas.html | head -3` → `301` + `location: https://atmina.lv/personas.html`.

- [ ] **Step 6: Pārbaude uz atmina.lv** — `.venv/Scripts/python.exe scripts/verify_host.py --base https://atmina.lv` → `7/7`; `nslookup -type=MX atmina.lv 8.8.8.8` joprojām = Task 1; e-pasts nosūtīts/saņemts vēlreiz (custom domain skar tikai `@`/`www`, bet pierādi, nevis pieņem).

- [ ] **Step 7: CHANGELOG + komits** — ieraksts „4. fāze: atmina.lv uz Cloudflare", `verify_host.py` tabula, atpakaļceļš (Cloudflare DNS: dzēst Workers ierakstu, atjaunot A uz veco IP), rezerves termiņš = šodiena + 30 dienas.

```bash
git add wrangler.json tests/test_wrangler_config.py wiki/CHANGELOG.md
git commit -m "atmina.lv + www uz Cloudflare Workers custom domains; verify_host 7/7; vecais hostings rezervē 30 dienas (4. fāze)"
```

### Task 9: Tīrīšana pēc 30 dienām (tikai ja rezerve nav bijusi vajadzīga)

**Files:**
- Delete: `assets/htaccess.template`
- Modify: `src/render/_orchestrator.py` (`_copy_host_config` pāri — izņem `htaccess.template` rindu + docstring teikumu), `tests/test_host_config_copy.py` (`.htaccess` gaidas → tikai `_headers`), `tests/test_headers_file.py` (`test_every_htaccess_security_header_is_carried_over` un `_htaccess_headers` → izņem; `_HTACCESS` → izņem), `tests/test_csp_external_hosts.py:22,38-41` (`_HTACCESS` → `_ROOT / "assets" / "_headers"`; `_parse_allowlist` regex → `r'Content-Security-Policy:\s*(.+)'`), `tests/test_no_inline_js.py:16` un `.claude/commands/dienas-rutina.md:113` (teksts `assets/htaccess.template` → `assets/_headers`), `CLAUDE.md` § Output Conventions „No inline JavaScript" rinda (`assets/htaccess.template` → `assets/_headers`; rindu ar `--no-delete` § Standing Decisions „Deploy is additive" → „Deploy ir pilns koks (Cloudflare kopš 2026-09-XX); `--no-delete` ir no-op"), `wiki/operations/deploy.md` (vecā hostinga sadaļa → arhīvs, `.br/.gz` rindas), `BACKLOG.md` § Ne-darīt rinda „NE Cloudflare-for-compression" → papildina „(hostings uz Cloudflare kopš 2026-09-XX ir cits lēmums; kompresijas ieraksts paliek)", `.claude/commands/deep-check.md:36` un `dienas-rutina.md:112` deploy rindas (`--no-delete` paskaidrojums → „no-op").

- [ ] **Step 1: Sarkans** — izdzēs `assets/htaccess.template`, palaid `.venv/Scripts/python.exe -m pytest tests/test_headers_file.py tests/test_host_config_copy.py tests/test_csp_external_hosts.py -v` → krīt tieši tie testi, kas nosaukti augstāk (denominators: ≥3 sarkani). Ja krīt kas cits — atkarība, ko šis plāns nezināja; apstājies un pieraksti.

- [ ] **Step 2: Labo testus un kodu** kā uzskaitīts Files blokā. `_copy_host_config` pēc labojuma:

```python
    pairs = (
        ("_headers", "_headers"),
        ("_redirects", "_redirects"),
    )
```

`tests/test_csp_external_hosts.py::_parse_allowlist`:

```python
    text = (_ROOT / "assets" / "_headers").read_text(encoding="utf-8")
    m = re.search(r"Content-Security-Policy:\s*(.+)", text)
    assert m, "CSP galvene nav atrasta assets/_headers"
```

- [ ] **Step 3: Zaļš** — `bash scripts/check.sh`; `.venv/Scripts/python.exe -m src.render --only=static` → `output/atmina/.htaccess` vairs NErodas (vecais fails kokā jāizdzēš ar roku: `rm output/atmina/.htaccess`).

- [ ] **Step 4: Dokumenti** — CLAUDE.md, BACKLOG, deploy.md, runbooki kā Files blokā; CHANGELOG ieraksts „Migrācija noslēgta: vecais hostings atslēgts, htaccess.template izņemts". Vecā hostinga konta anulēšana — operatora solis ārpus repo; `.env.deploy` `DEPLOY_HOST/USER/PATH/PORT/SSH_KEY` rindas izņem (tests `test_no_deploy_credentials` skenē tikai esošās vērtības).

- [ ] **Step 5: Komits**

```bash
git add -A assets src/render/_orchestrator.py tests .claude/commands CLAUDE.md BACKLOG.md wiki
git commit -m "Cloudflare migrācija noslēgta: htaccess.template izņemts, _headers vienīgais galveņu avots, runbooki + CLAUDE.md deploy rindas"
```

Pēc tam atsevišķs, jau BACKLOG-ā pierakstīts uzdevums: `.json.br/.gz` ģenerēšanas izņemšana (`src/render/positions.py`, `votes_matrix.py`, `search_index.py`, `links.py`, `_common.py` + `tests/test_render_votes_matrix_json.py:436`, `tests/test_saites_sidecar.py`).
