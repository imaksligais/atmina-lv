# Cloudflare Task 9 — vecā hostinga likvidēšana (BACKLOG 67)

**STATUSS: IZPILDĪTS 2026-10-19** — CHANGELOG 2026-10-19 (2), BACKLOG 67: hostings anulēts, 14 DNS ieraksti izdzēsti (`6a60d922`).
Arhivēts 2026-10-21.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** repo vairs nezina par veco web hostingu: `_headers` ir vienīgais galveņu avots, `.htaccess` netiek ģenerēts, runbooki un vārti runā tikai par Cloudflare; operators anulē hostingu un izdzēš tā DNS ierakstus.

**Architecture:** Divi posmi. (1) Koda posms — tagad, neatkarīgs no operatora: Cloudflare `.htaccess` nelasa, tāpēc tā izņemšana dzīvo vietni nemaina. (2) Operatora posms — hostinga anulēšana + DNS tīrīšana CF panelī; pēc tā mazs dokumentu komits ar to, kas izpildi pierādīja.

**Tech Stack:** Python 3 (`.venv`), pytest, `scripts/check.sh`, Cloudflare panelis, `nslookup`.

**Spec:** `docs/superpowers/plans/2026-09-15-cloudflare-migracija.md` § Task 9 (Files bloks ir novecojis — šis plāns to aizstāj; atšķirības zemāk).

## Global Constraints

- Šis fails ir PUBLISKS (spogulis). Konkrētas IP adreses, konta/plāna nosaukumi, lietotājvārdi — TIKAI `private/dns-atmina-2026-09-15.txt` un `private/dns-fix-2026-09-16.txt`.
- CSP `script-src` NEKAD nesatur `'unsafe-inline'`.
- Pasta ieraksti (A `mail`/`webmail`/`autoconfig`/`autodiscover`, MX, SPF, DKIM, DMARC, SRV `_autodiscover._tcp`) netiek aiztikti.
- Helperi neizpilda `git stash` / `checkout --` / `restore` / `reset`.
- `check.sh` palaiž tikai tad, kad DB neviens neraksta (HANDOFF 2026-10-19: sacensība ar ekstrakciju).

## Atšķirības no 09-15 plāna (mērīts 2026-10-19)

- `tests/test_csp_external_hosts.py` jau lasa `assets/_headers` — maina tikai docstring.
- `CLAUDE.md` „No inline JavaScript" jau saka `assets/_headers`; deploy rinda jau saka „FULL local tree". Paliek tikai teikums „The old host stays in reserve until 2026-10-16 (BACKLOG 67)".
- `deep-check.md:37` un BACKLOG § Ne-darīt kompresijas rinda jau ir labotas.
- SPF jau tīrs kopš 2026-09-16 (`nslookup -type=TXT atmina.lv 1.1.1.1` → bez `+a` un `ip4:`). BACKLOG 67 teksts par SPF ir novecojis.
- Jauns kopš plāna: `assets/.assetsignore`, `scripts/audit_remote_tree.sh` (tikai vecajam hostam), `tests/test_no_deploy_credentials.py` (lasa `DEPLOY_*` — pēc to izņemšanas klusi skipotu mūžīgi).
- Live DNS 2026-10-19: 6 A ieraksti uz veco web IP + 4 SRV (`_caldav*`/`_carddav*`) + to 4 TXT `path=/` = **14 dzēšami**.

## Review Focus

1. Nākamais pilnais deploy publicē `/.htaccess`, ja vecais fails paliek `output/atmina/` UN tas izkrīt no `.assetsignore` → fails jāizdzēš no koka, un ignorēšanas rinda paliek (aizsardzība, maksā 0).
2. Izņemot htaccess salīdzinājuma testu, pazūd vienīgā pārbaude, ka `/*` nes HSTS/nosniff/X-Frame/Referrer/CSP → aizstāj ar nosaukumu testu (denominators 5) un pierādi ar mutāciju.
3. Noplūdes vārts `test_no_deploy_credentials.py` kļūst par vārtu, kas nevar nokrist → pārmērķē uz `CLOUDFLARE_API_TOKEN`/`CLOUDFLARE_ACCOUNT_ID`, pierādi ar mutāciju.
4. Saites uz dzēsto `deploy-namecheap-arhivs.md` → `deploy.md:163` jāpārraksta; citas dzīvas saites nav (grep 2026-10-19: tikai arhīvs/CHANGELOG/žurnāls).
5. Komentāri „see htaccess" `.br/.gz` kodā (`positions.py`, `votes_matrix.py`, `search_index.py`, `links.py`, `_common/assets.py`, `test_render_votes_matrix_json.py`, `test_saites_sidecar.py`) — APZINĀTI paliek: tas ir atsevišķais BACKLOG uzdevums (`.json.br/.gz` izņemšana); CHANGELOG to pasaka.

---

### Task 1: Koda posms — `htaccess.template` ārā, vārti uz `_headers` / Cloudflare

**Files:**
- Delete: `assets/htaccess.template`, `scripts/audit_remote_tree.sh`, `wiki/operations/deploy-namecheap-arhivs.md`; netrekots `output/atmina/.htaccess` (`rm`).
- Modify: `src/render/_orchestrator.py` (:131 komentārs, `_copy_host_config` pāri + docstring, :565 komentārs); `assets/.assetsignore` (izņem `assets/htaccess.template`; `.htaccess` paliek ar komentāru); `assets/_headers` :2-3 komentārs; `.env.deploy.example` (izņem Namecheap bloku, Cloudflare paliek).
- Test: `tests/test_headers_file.py`, `tests/test_host_config_copy.py`, `tests/test_no_deploy_credentials.py`; docstringi `tests/test_csp_external_hosts.py:5,10`, `tests/test_no_inline_js.py:16`.
- Docs: `CLAUDE.md:21` (teikums par rezervi); `ARCHITECTURE.md:13-14`; `docs/data-policy.md:144`; `templates/about.html.j2:387` (Jinja komentārs); `.claude/commands/dienas-rutina.md:131`; `wiki/operations/ui-conventions.md:17`; `wiki/operations/deploy.md` (:67, :71, :138-146 nākotnes teikums, :157-163 sadaļa → 2-3 rindas vēsture: `git show c0e9d15d:wiki/operations/deploy-namecheap-arhivs.md`); `wiki/operations/cloudflare-security.md` (:32, :106-110 → „gaida operatoru, sk. šo plānu"); `docs/funding/repo-sync.md:45,51` (`DEPLOY_*` → Cloudflare atslēgas); `BACKLOG.md:94,148-149`; `wiki/CHANGELOG.md` (≤5 rindas); 09-15 plāna Task 9 → atsauce uz šo plānu.

**Interfaces:**
- Produces: `src.render._orchestrator._copy_host_config(atmina_dir: Path) -> list[str]` — pāri `_headers`, `_redirects`, `.assetsignore` (secība nemainās).

- [ ] **Step 1: Sarkans.** `rm assets/htaccess.template`; `.venv/Scripts/python.exe -m pytest tests/test_headers_file.py tests/test_host_config_copy.py tests/test_csp_external_hosts.py -v`. Gaidāms: krīt `test_every_htaccess_security_header_is_carried_over` un `test_real_assets_dir_yields_both_files` (pārējie host_config testi lieto tmp_path). Ja krīt kas cits — apstājies, pieraksti.

- [ ] **Step 2: Galveņu tests.** `tests/test_headers_file.py`: izņem `_HTACCESS`, `_htaccess_headers`, carry-over testu; docstring → „`assets/_headers` ir vienīgais galveņu avots (kopš 2026-10-19)". Pievieno:

```python
_REQUIRED_SECURITY_HEADERS = (
    "Strict-Transport-Security",
    "X-Content-Type-Options",
    "X-Frame-Options",
    "Referrer-Policy",
    "Content-Security-Policy",
)


def test_root_rule_carries_every_security_header():
    """Līdz 2026-10-19 šo sargāja salīdzinājums ar htaccess.template; tagad nosaukumi ir šeit."""
    root = _parse_headers_file(_HEADERS.read_text(encoding="utf-8"))["/*"]
    missing = [h for h in _REQUIRED_SECURITY_HEADERS if not root.get(h)]
    assert not missing, f"/* trūkst {missing} (pārbaudīti {len(_REQUIRED_SECURITY_HEADERS)})"
```

Mutācija: izdzēs `X-Frame-Options` rindu no `assets/_headers` → tests krīt; atliec rindu ar roku.

- [ ] **Step 3: Kopēšanas tests + kods.** `_copy_host_config` pāri:

```python
    pairs = (
        ("_headers", "_headers"),
        ("_redirects", "_redirects"),
        (".assetsignore", ".assetsignore"),
    )
```

Docstring bez `.htaccess` rindas; LF komentārs bez LiteSpeed. `tests/test_host_config_copy.py`: pirmais tests → `test_copies_headers` (tmp assets ar `_headers` + svešu `htaccess.template`; gaida `["_headers"]` un ka `.htaccess` NErodas); trešais → gaida `[".assetsignore", "_headers", "_redirects"]` un `.htaccess` un `assets/_headers` joprojām `.assetsignore` sarakstā. `.assetsignore`: izņem `assets/htaccess.template`, virs `.htaccess` komentārs „vecs artefakts; ja kokā paliek, neaugšupielādē".

- [ ] **Step 4: Noplūdes vārts.** `tests/test_no_deploy_credentials.py`: `SECRET_KEYS = ("CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID")`, `PLACEHOLDERS = {"cf-token-here", "cf-account-id-here"}`; docstring papildina ar teikumu „Kopš 2026-10-19 (vecais hostings anulēts) sargā Cloudflare atslēgas; `DEPLOY_*` vēsturi sk. CHANGELOG 2026-08-01". Porta komentāru izņem. Mutācija: īsto `CLOUDFLARE_ACCOUNT_ID` vērtību īslaicīgi ieliek kādā izsekotā failā → tests krīt (ziņojums bez vērtības); izņem ar roku. Ja `.env.deploy` CF vērtības ir tukšas → tests skipo; tad to pasaki, ne „zaļš".

- [ ] **Step 5: Atlikušie faili** no Files bloka (`.env.deploy.example`, `_headers` komentārs, docstringi, docs, `git rm` trīs failiem). `rm output/atmina/.htaccess`.

- [ ] **Step 6: Zaļš.** Kad DB neviens neraksta: `bash scripts/check.sh`. Tad `.venv/Scripts/python.exe -m src.render --only=static` → `ls -a output/atmina/ | grep -E '^(\.htaccess|_headers|_redirects|\.assetsignore)$'` → trīs, bez `.htaccess`. `git grep -n htaccess.template` → tikai vēsture (CHANGELOG*, `docs/arhivs`, `docs/audits`, 09-15 plāns/spec) + šis plāns.

- [ ] **Step 7: Komits** (`git commit -F <fails>`): „Cloudflare Task 9 (koda daļa): htaccess.template izņemts, _headers vienīgais galveņu avots; DNS + hostings gaida operatoru".

---

### Task 2: Operatora posms (secībā)

Vērtības (IP, plāni, konti) — `private/dns-atmina-2026-09-15.txt`.

- [x] **O1. Rezerves kopija — nevajag** (operators 2026-10-19: vecā hostinga saturs nav vajadzīgs; viss ir repo un Cloudflare).
- [x] **O2. Pārliecinies, ka anulē pareizo.** Tas ir vecais web plāns, NE plāns, kurā dzīvo pasts (pasts ir citā plānā; `private/dns-atmina-2026-09-15.txt` § ATBILDE). Domēns reģistrēts pie .lv reģistratora, ne pie hostinga — anulēšana to neskar.
- [x] **O3. Anulē veco web hostingu** hostinga panelī (aktīvi, ne „ļauj beigties"); izslēdz automātisko atjaunošanu.
- [x] **O4. Cloudflare → atmina.lv → DNS → Records — izdzēs 14:** A `cpanel`, `whm`, `webdisk`, `cpcalendars`, `cpcontacts`, `ftp`; SRV `_caldav._tcp`, `_caldavs._tcp`, `_carddav._tcp`, `_carddavs._tcp`; TXT `path=/` uz tiem pašiem četriem vārdiem. **NEaiztiec:** A `mail`, `webmail`, `autoconfig`, `autodiscover`, MX, TXT `@` (SPF), `_dmarc`, `default._domainkey`, SRV `_autodiscover._tcp`.
- [x] **O5. Pārbaude** (2026-10-19: 14/14 nav, pasta ieraksti paliek, `verify_host.py` 9/9; pasta tests abos virzienos OK) (es varu palaist): 14 vārdi pret `1.1.1.1` → nav atbildes (14/14); 4 pasta vārdi joprojām atbild; pasta tests abos virzienos (vēstule uz ārēju adresi un atpakaļ).
- [x] **O6. Lokāli** (`.env.deploy` izdarīts 2026-10-19; SSH — operators): `.env.deploy` → izdzēs `DEPLOY_HOST/USER/PORT/PATH/SSH_KEY` rindas; vecā hosta SSH atslēga un `~/.ssh/config` `Host namecheap` bloks → dzēš.
- [x] **O7. Pasaki man** — tad 2. komits: `cloudflare-security.md` §4 datums, BACKLOG 67 → IZPILDĪTS ar pierādījumu (nslookup 14/14, `verify_host.py` 9/9), CHANGELOG viena rinda.

DMARC `p=quarantine` ir atsevišķs atvērts darbs — neiekļauj šeit.
