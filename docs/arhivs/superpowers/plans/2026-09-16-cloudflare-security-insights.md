# Cloudflare Security Insights 2026-09-16 — plāns

Avots: Cloudflare paneļa Security Insights eksports (2026-09-16 03:28 UTC), 15 ieraksti. Šis plāns ir arī deleģēšanas brīfs diviem Opus aģentiem (A — kods, B — dokumenti). Konkrētas IP adreses un pasta hostinga nosaukumi šeit NAV — tie dzīvo `private/` (gitignorēts).

## Verdikts pa ierakstiem

| # | Ieraksts | Smagums | Verdikts | Kur |
|---|---|---|---|---|
| 1 | Security.txt nav | Low | **DARĀM repo** — `/.well-known/security.txt` (RFC 9116) no `static` rendera; Contact = publiskā `info@atmina.lv` (jau `kontakti.html`) | Aģents A |
| 2 | Bot Fight Mode izslēgts | Moderate | **Ieteikums: NEIESLĒGT** (operatora lēmums). Vietne ir statiska uz Workers, nav origin servera, ko sargāt; BFM izaicina Python klientus → `scripts/verify_host.py` 7 pārbaudes un dashboard dzīvās pārbaudes var krist; Free plānā BFM nevar apiet ar WAF kārtulu. Dokumentē izmēģinājuma procedūru (ieslēdz → `verify_host` → ja krīt, izslēdz). | Aģents B → runbook + § Ne-darīt |
| 3 | SPF kļūda | Low | **Operators panelī.** Dzīvais ieraksts: `+a` (tagad rezolvē uz Cloudflare proxy IP — bezjēdzīgi), 3 `ip4:` (visi jau iekļauti `include:spf.web-hosting.com` apakštīklos), 9 DNS lookups no 10. Ieteiktais: `v=spf1 mx include:spf.web-hosting.com ~all` (8 lookups). Konkrētais vecais/jaunais + rollback → `private/`. | Aģents B |
| 4 | DMARC kļūda | Low | **Operators panelī.** Dzīvais `v=DMARC1; p=none;` bez `rua`. 1. solis: pievieno `rua=` (Cloudflare DMARC Management dod bezmaksas adresi) + `fo=1`, paliek `p=none` 2–4 nedēļas; 2. solis: `p=quarantine`. DKIM `default._domainkey` eksistē → izlīdzināšana iespējama. | Aģents B |
| 5–10 | Neproksēti A: `cpanel`, `whm`, `webdisk`, `cpcalendars`, `cpcontacts`, `ftp` | Moderate | **NEPROKSĒT, dzēst Task 9 ietvaros (pēc 2026-10-16, BACKLOG 67).** Rāda uz veco web hostingu (rezervē); 0 vaicājumu; proxy nav iespējams (ftp/cPanel porti). Risks „origin IP atklāts" neattiecas — vietnes origin ir Cloudflare Workers, ne šis IP. | Aģents B → BACKLOG 67 papildinājums |
| 11–14 | Neproksēti A: `mail`, `webmail`, `autoconfig`, `autodiscover` | Moderate | **NEPROKSĒT nekad** — pasta hosts; proxy nes tikai HTTP, SMTP/IMAP salūztu. Panelī: Security Insights → ieraksts → *Archive/Dismiss*. | Aģents B → § Ne-darīt |
| 15 | AI Labyrinth | Low | **Ieteikums: NEIESLĒGT.** Caurspīdības vietne grib būt lasāma un citējama; funkcija injicē AI-ģenerētas saites lapās (satura paritāte `verify_host`/`check_output` pret repo koku zūd). | Aģents B → § Ne-darīt |

**Ierobežojums:** deploy tokenam ir tikai `Workers Scripts:Edit` — nekas no 2–15 nav darāms no repo; visi ir operatora paneļa soļi. Cloudflare Security.txt ieraksts, iespējams, paliks „Active" arī pēc repo faila, jo skeneris skatās paneļa slēdzi (Security → Settings → Security.txt); NElietot paneļa slēdzi paralēli repo failam (divi avoti).

## Aģents A — kods (faili: `src/render/_orchestrator.py`, `assets/_redirects`, `scripts/verify_host.py`, `tests/`)

1. `_orchestrator.py` static solī (blakus robots.txt): raksti `output/atmina/.well-known/security.txt`, LF, UTF-8, ar tīru palīgfunkciju `security_txt(now: datetime) -> str`:
   ```
   Contact: mailto:info@atmina.lv
   Expires: <now + 180 dienas, RFC 3339, UTC, sekundes 00>
   Preferred-Languages: lv, en
   Canonical: https://atmina.lv/.well-known/security.txt
   Policy: https://atmina.lv/kontakti.html
   ```
2. `assets/_redirects`: `/security.txt /.well-known/security.txt 301` (avots nebeidzas ar `.html` — `tests/test_redirects_file.py` netraucē; pārbaudi).
3. `scripts/verify_host.py`: 8. pārbaude `security_txt` — GET `/.well-known/security.txt` = 200, satur `Contact: mailto:`, `Expires:` nākotnē; denominators n=1 (viens fails, viens URL — norādi to `detail`).
4. Testi (TDD, sarkans → zaļš): `tests/test_security_txt.py` — lauki, `Expires` parsējas un ir ≤ 365 dienas uz priekšu, LF, beidzas ar `\n`; orchestrator raksta failu tmp katalogā (izsauc tieši rakstīšanas palīgu, ne pilno renderu); `verify_host` 8. pārbaude ar fake fetch (pass + fail gadījums).
5. `bash scripts/check.sh` zaļš; `--only=static` renders → `ls output/atmina/.well-known/`.
6. NE deploy, NE git commit. Atskaitē: kas izpildīts, kas NAV pārbaudīts (vai wrangler augšupielādē `.well-known/` punktu-katalogu — pierāda tikai nākamais operatora deploy + `verify_host` 8/8).

## Aģents B — dokumenti (faili: `wiki/operations/cloudflare-security.md` (jauns), `wiki/operations/deploy.md`, `wiki/operations/operacijas.md`, `BACKLOG.md`, `wiki/CHANGELOG.md`, `private/dns-fix-2026-09-16.txt` (jauns))

1. Jauns runbook `wiki/operations/cloudflare-security.md`: tabula augstāk + paneļa soļi (SPF rediģēšana, DMARC Management, insight arhivēšana, BFM izmēģinājums) + „ko nekad" saraksts. Bez IP, bez pasta hostinga nosaukuma, bez operatora vārdiem (publiskais spogulis).
2. `private/dns-fix-2026-09-16.txt`: vecais SPF/DMARC verbatim (rollback), jaunais ieteiktais, pārbaudes komanda (`nslookup -type=TXT atmina.lv 1.1.1.1`).
3. `BACKLOG.md` 67: papildini ar insight numuriem 5–10 un SPF `+a` piezīmi; § Ne-darīt: BFM (ar izmēģinājuma atrunu), AI Labyrinth, pasta ierakstu proksēšana. Ievēro `tests/test_backlog_index_sync.py` (indeksa rindas = tēmu failu virsraksti; § Ne-darīt nav indeksā).
4. `deploy.md` § Cloudflare + `operacijas.md` tabula: saite uz jauno runbook.
5. `wiki/CHANGELOG.md`: `## 2026-09-16 (3)` ≤ ~3 KB — Security Insights triāža, security.txt (Aģents A), DNS ieteikumi, godīguma rinda: nekas no paneļa vēl nav mainīts, security.txt vēl nav deployots.
6. NE git commit. LV gramatikas vārti.
