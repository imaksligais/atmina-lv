# HANDOFF 2026-09-15 — Cloudflare migrācija, sākam 1. fāzi

## Stāvoklis

- Dizains apstiprināts un komitēts: `docs/superpowers/specs/2026-09-15-cloudflare-pages-migracija-design.md`
  (Workers Static Assets, ne Pages — visi publiskie URL nes `.html`, `html_handling: none`).
- Izpildes plāns komitēts: `docs/superpowers/plans/2026-09-15-cloudflare-migracija.md`
  (9 uzdevumi, 4 fāzes; kods sākas tikai 3. fāzē).
- Nekas vēl nav izpildīts. `git status` tīrs pēc `2b9c5cea`.

## Kur apstājāmies

Task 1 (DNS eksports), 0. solis: noskaidrot, kur DNS zona tagad dzīvo.
Domēns ir reģistrēts pie .lv reģistratora, hostings ir Namecheap cPanel —
tāpēc ieraksti, visticamāk, ir **cPanel → Zone Editor**, bet vārdserverus
mainīs **reģistratora** panelī, ne Namecheap.

Nākamā komanda (operators, terminālī):

```
nslookup -type=NS atmina.lv 8.8.8.8
```

- `*.namecheaphosting.com` / `*.web-hosting.com` → eksportē no cPanel Zone Editor.
- reģistratora vārdserveri → eksportē no reģistratora DNS paneļa.

Tālāk pēc plāna Task 1 Step 1–6: eksports uz `private/dns-atmina-2026-09-XX.txt`
(neizsekots), `www` uzvedības pieraksts, `nslookup` kopija, Cloudflare zona,
salīdzināšana rindu pa rindai (pasta ieraksti pelēks mākonis), vārdserveru
maiņa reģistratorā, pārbaude + e-pasta tests abos virzienos, CHANGELOG.

## Atjaunināts 2026-09-15 vakarā (pēc dienas rutīnas)

- **E-pasts JAU pārcelts** (operators, ārpus repo) — pieņēmums „e-pasts paliek pie līdzšinējā cPanel" vairs neder.
  Sekas Task 1: eksportē DNS zonu **tādu, kāda tā ir TAGAD** (jaunie MX/SPF/DKIM/DMARC mērķi), un
  `nslookup -type=MX atmina.lv 8.8.8.8` PIRMS eksporta ir atskaites punkts — tieši šīs vērtības
  jāpārnes uz Cloudflare ar pelēko mākoni. Pārbaudi arī, vai `mail`/`autodiscover`/`webmail`
  ieraksti vēl vajadzīgi vai norāda uz veco hostu (tad tie ir dzēšami pēc pasta testa, ne pirms).
- Vakara rutīna 09-15 pabeigta un deployota (CHANGELOG „2026-09-15 (2)"); nākamā sesija var sākt
  ar 1. fāzi bez rutīnas priekšdarbiem. Pēdējais deploy uz veco hostu ir šis — 3./4. fāzē
  `deploy.sh` mērķis mainās pēc plāna.
- Nākamā komanda nemainās: `nslookup -type=NS atmina.lv 8.8.8.8`, tad Task 1.

## Atgādinājumi

- E-pasts ir ārpus Cloudflare (jau pārcelts, sk. augstāk) — MX/SPF/DKIM/DMARC pārnešana
  ar pelēko mākoni joprojām ir 1. fāzes kritiskā daļa.
- Katra fāze prasa operatora „jā" pirms izpildes.
- `BACKLOG.md` § Ne-darīt „NE Cloudflare-for-compression" — papildina 4. fāzes beigās, nedzēš.

## NOSLĒGTS 2026-09-16 ~01:30 — visas 4 fāzes izpildītas

`atmina.lv` + `www` dzīvo uz Cloudflare Workers Static Assets. Pilns pieraksts: `wiki/CHANGELOG.md`
2026-09-15 (3), (4) un 2026-09-16 (1), (2); runbook `wiki/operations/deploy.md` § Cloudflare.

Kas atšķiras no plāna (izlasi, pirms uzticies plānam):
- **Domēni ir piesaistīti PANELĪ, ne `wrangler.json` `routes`** — deploy token ir tikai
  `Workers Scripts:Edit`, zonas sinhronizācija krīt ar auth 10000; `tests/test_wrangler_config.py`
  tagad sargā, ka `routes` NAV. `workers_dev: false`.
- **`assets/_redirects`** (`/ /index.html 200`) — bez tā sakne ir 404; **`assets/.assetsignore`** —
  citādi `/.htaccess` u.c. ir publiski.
- Task 1: nic.lv reģistrā bija viens NS ieraksts; ~20 `*.<otrs domēns>.atmina.lv` cPanel artefakti
  apzināti nepārnesti; pasts dzīvo uz otra Namecheap (Stellar+) plāna — veco hostingu drīkst slēgt.

Atvērts: (1) `verify_host.py --base https://atmina.lv` caur CF nākamajā deploy (09-16 lokālais
resolvers kešoja veco A; `curl --resolve` 20/20 zaļš); (2) operatora pasta tests PĒC pārslēgšanas;
(3) **Task 9 pēc 2026-10-16** — BACKLOG 67.
