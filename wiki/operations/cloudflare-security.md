# Cloudflare drošība — Security Insights triāža un paneļa soļi

Kopš 2026-09-16 `atmina.lv` dzīvo uz Cloudflare Workers Static Assets, un
paneļa sadaļa **Security → Insights** pati ģenerē ieteikumu sarakstu. Šis fails
ir tā saraksta triāža: kas ir izpildīts, kas ir apzināti noraidīts un kāda ir
procedūra tam, ko drīkst darīt tikai operators panelī.

**Avots:** Security Insights eksports 2026-09-16 03:28 UTC, **15 ieraksti**.
Sadalījums pēc rīcības: **1** darbs repo, **2** DNS labojumi panelī, **12**
arhivējami bez darbības (10 neproksētie apakšvārdi + Bot Fight Mode + AI
Labyrinth).

**Pamata ierobežojums.** Deploy tokenam ir TIKAI `Account · Workers Scripts ·
Edit` ([deploy.md § Cloudflare](deploy.md)) — tas neredz ne zonu, ne DNS, ne
drošības slēdžus. Tātad no repo nav izdarāms neviens no zemāk aprakstītajiem
paneļa soļiem; katrs ir operatora rokas darbs. Tā ir apzināta izvēle, ne robs:
plašāks token uz diska būtu drošības kāpums atpakaļ (sk. CHANGELOG 2026-09-16 (2)).

**Konkrētās vērtības šeit nav.** Dzīvie DNS ieraksti (IP adreses, pasta hostinga
vārdi), to rollback un pārbaudes komandas dzīvo `private/dns-fix-2026-09-16.txt`
(gitignorēts). Šis fails aiziet publiskajā spogulī, tāpēc tur paliek tikai
lēmumi un procedūras.

## Verdikti pa ierakstiem

| # | Ieraksts | Smagums | Verdikts |
|---|---|---|---|
| 1 | `security.txt` nav | Low | **Izpildīts un dzīvs** (deploy 2026-09-16, `verify_host` 8/8 caur CF malu) → § 1 |
| 2 | Bot Fight Mode izslēgts | Moderate | **Neieslēgt.** Izmēģinājuma procedūra, ja tomēr grib pārbaudīt → § 5 |
| 3 | SPF kļūda | Low | **Operators panelī** → § 2 |
| 4 | DMARC kļūda | Low | **Operators panelī, divos soļos** → § 3 |
| 5–10 | Neproksēti A ieraksti: `cpanel`, `whm`, `webdisk`, `cpcalendars`, `cpcontacts`, `ftp` | Moderate | **Neproksēt; dzēst kopā ar veco hostingu** (izdzēsti 2026-10-19, BACKLOG 67) → § 4 |
| 11–14 | Neproksēti A ieraksti: `mail`, `webmail`, `autoconfig`, `autodiscover` | Moderate | **Neproksēt nekad** — pasta ieraksti → § 4 |
| 15 | AI Labyrinth izslēgts | Low | **Neieslēgt** → § 6 |

## 1. `security.txt` — vienīgais darbs repo

`/.well-known/security.txt` (RFC 9116) tiek ģenerēts `static` renderā blakus
`robots.txt`; `/security.txt` → `/.well-known/security.txt` 301 dzīvo
`assets/_redirects`; `scripts/verify_host.py` 8. pārbaude (`security_txt`)
prasa 200, `Contact: mailto:` un `Expires` nākotnē.

**Statuss: DZĪVS kopš 2026-09-16** (deploy versija `2264c656`; wrangler augšupielādēja
`/.well-known/security.txt` — punktu-katalogs iet līdzi, pieņēmums pierādīts).
`verify_host` **8/8** caur Cloudflare malu; `/security.txt` → 301 pārbaudīts dzīvi.
Slazds: šajā mašīnā lokālais resolvers vēl kešo VECO hostu, un nepinēts `verify_host`
krīt ar `security_txt: status 404` no LiteSpeed — pinē `atmina.lv` uz CF IP
(getaddrinfo monkeypatch) vai `ipconfig /flushdns` pirms lasi rezultātu.

**NElieto paneļa slēdzi paralēli repo failam.** Cloudflare ieraksts, iespējams,
paliks „Active" arī pēc deploy, jo skeneris skatās paneļa slēdzi (Security →
Settings → Security.txt), ne faila esamību. Divi avoti vienam failam ir dārgāka
kļūda nekā viens neaizvērts ieteikums — ieteikumu arhivē, slēdzi neieslēdz.

## 2. SPF — viens paneļa labojums

**Kas ir nepareizi dzīvajā ierakstā** (mērīts 2026-09-16 ar `nslookup` pret
publisko resolveri):

- **`+a` kopš 4. fāzes ir bezjēdzīgs.** Tas atļauj sūtīt no domēna A ieraksta
  adresēm, un tās tagad ir Cloudflare proxy adreses — no turienes pastu nesūta
  neviens. Mehānisms maksā vienu DNS lookup un nedod neko.
- **Trīs `ip4:` adreses ir liekas.** Visas trīs ietilpst apakštīklos, ko jau
  uzskaita pasta hostinga `include:` ķēde (tā satur 6 ieligzdotus `include`).
- **Kopā 9 DNS lookups no 10 atļautajiem.** Viens kļūdains ieraksts vairāk, un
  visa SPF pārbaude atgriež `permerror`, t.i. nogāžas klusi.

**Ieteiktais ieraksts:** `v=spf1 mx include:<pasta hostinga SPF include> ~all`
— 8 lookups, tā pati atļauto sūtītāju kopa. Burtiskais vecais un jaunais
ieraksts: `private/dns-fix-2026-09-16.txt`.

**Soļi panelī:** DNS → Records → TXT `@` ar `v=spf1 …` → Edit → aizvieto
saturu → Save. Pēc tam pārbaude ar `nslookup` (komanda privātajā failā) un
**operatora pasta tests abos virzienos** — SPF kļūda neredzas vietnē, tā redzas
tikai pēc tam, kad vēstules sāk nonākt mēstulēs.

**Atpakaļceļš:** ielīmē veco rindu no `private/dns-fix-2026-09-16.txt`. TTL ir
īss, tāpēc atgriešanās ir minūtes, ne stundas.

## 3. DMARC — trīs soļi ar pauzēm pa vidu

**Stāvoklis: 2. solis izpildīts 2026-10-20** — dzīvs `v=DMARC1; p=quarantine;
rua=mailto:info@atmina.lv; fo=1` (pamatojums § 7, 4. rinda). Atskaites nāk uz
`info@` kā Google `.zip` pielikumi; tos izsaiņo uz `private/dmarc/<datums>/`.
DKIM selektors `default._domainkey` dod izlīdzināšanu (alignment).

**1. solis (izpildīts 2026-09-16).** DNS → TXT `_dmarc` → `v=DMARC1; p=none;
rua=mailto:<adrese no Cloudflare DMARC Management>; fo=1`. Adresi dod pats
Cloudflare: Email → DMARC Management → Enable; tas ir bez maksas un atskaites
parādās panelī. `p=none` paliek — šis solis neko nebloķē, tikai sāk skaitīt.

**2. solis (izpildīts 2026-10-20; tikai ja atskaites ir tīras).** `p=none` →
`p=quarantine`. „Tīras" nozīmē: visi leģitīmie sūtītāji atskaitēs iziet SPF vai
DKIM izlīdzināšanu. Ja kāds neiziet, vispirms salabo sūtītāju, ne politiku.

**3. solis (ne agrāk kā 2026-11-03, tikai ar tīrām atskaitēm kopš 2. soļa).**
`p=quarantine` → `p=reject`. Tā pati pārbaude: pašu pasta hosts visās rindās
iziet SPF vai DKIM; trešo pušu pārsūtījumi ar `arc=pass` nav mūsu sūtītāji.

**Kāpēc ne uzreiz stingrāk:** bez atskaišu loga nav zināms, cik sūtītāju
domēnam ir. Politika, kas ieviesta akli, nogriež savu pastu, un to pamana tikai
adresāts, kas nesaņēma vēstuli.

## 4. Neproksētie A ieraksti (5–14) — divas dažādas klases

**Kopīgais iemesls, kāpēc Cloudflare brīdinājums šeit neattiecas.** Skeneris
pieņem, ka neproksēts A ieraksts atklāj vietnes origin serveri. atmina.lv origin
ir Cloudflare Workers — šie vārdi rāda uz citām mašīnām, ne uz vietni, tāpēc
„origin IP atklāts" nav risks, ko šeit varētu realizēt.

- **5–10 (`cpanel`, `whm`, `webdisk`, `cpcalendars`, `cpcontacts`, `ftp`)** —
  vecā web hostinga paneļa artefakti. 0 vaicājumu; proxy tehniski nav iespējams
  (šie porti nav HTTP). **Izdzēsti 2026-10-19** kopā ar veco hostingu
  (Task 9, BACKLOG 67; `nslookup` 1.1.1.1: 14/14 nav, ieskaitot `_caldav*`/`_carddav*`).
- **11–14 (`mail`, `webmail`, `autoconfig`, `autodiscover`)** — pasta hosta
  ieraksti. **Neproksēt NEKAD:** Cloudflare proxy nes tikai HTTP(S), tāpēc
  SMTP/IMAP caur to vienkārši salūztu, un `autoconfig`/`autodiscover` pārstātu
  atbildēt pasta programmām. Šie ieraksti paliek `DNS only` uz visiem laikiem.

**Ieteikuma aizvēršana panelī:** Security → Insights → ieraksts → *Archive*
(vai *Dismiss*). Tas aizver ieteikumu, nemainot DNS.

## 5. Bot Fight Mode — neieslēgt; ja tomēr, tad pēc šīs procedūras

**Verdikts: NEIESLĒGT.** Trīs iemesli, katrs neatkarīgs:

1. **Nav origin servera, ko sargāt.** Vietne ir statiska uz Workers; BFM galvenā
   vērtība ir origin slodzes nogriešana.
2. **Tas var nogalināt mūsu pašu pārbaudes.** `scripts/verify_host.py` iet ar
   `httpx` (Python lietotāja aģents) — tieši tā klase, ko BFM izaicina. Tas ir
   vienīgais dzīvais pierādījums, ka deploy tiešām aizgāja; ja tas krīt, deploy
   paliek bez pierādījuma (`CLAUDE.md` § „gate that cannot fail").
3. **Free plānā nav vidusceļa.** BFM nevar apiet ar WAF skip kārtulu, tāpēc
   izvēle ir binārā: vai nu visiem, vai nevienam.

**Izmēģinājuma procedūra (ja operators tomēr grib mērījumu):**

1. Security → Bots → Bot Fight Mode → **On**.
2. Uzreiz: `.venv/Scripts/python.exe scripts/verify_host.py --base https://atmina.lv`.
3. Lasi denominatorus, ne tikai PASS/FAIL. 403, 503 vai izaicinājuma lapa
   jebkurā pārbaudē = BFM nogrieza mūsu pašu rīku.
4. Ja kaut viena krīt → **izslēdz atpakaļ tajā pašā sesijā** un pieraksti
   rezultātu šeit (cik pārbaudes, cik krita). Nepamet ieslēgtu „uz nakti".

## 6. AI Labyrinth — neieslēgt

Funkcija rāpuļiem servē AI ģenerētas lapas un injicē tajās saites.
Divi iemesli, kāpēc tas nesader ar šo projektu:

- **Caurspīdības vietne grib būt lasāma un citējama.** Automātiskais lasītājs
  šeit nav uzbrucējs.
- **Tas salauž satura paritāti.** `scripts/verify_host.py` un
  `scripts/check_output.py` balstās uz to, ka dzīvā lapa atbilst uzbūvētajam
  kokam. Injicēts saturs šo pieņēmumu atceļ — un tas ir tas pats pieņēmums,
  uz kura stāv visi deploy vārti.

## Ko nekad (kopsavilkums)

- **Nekad neproksē pasta ierakstus** (`mail`, `webmail`, `autoconfig`,
  `autodiscover`) — proxy nes tikai HTTP, pasts apstātos.
- **Nekad neieslēdz Bot Fight Mode bez § 5 procedūras** un bez gatavības
  izslēgt to atpakaļ tajā pašā sesijā.
- **Nekad neieslēdz AI Labyrinth.**
- **Nekad nelieto paneļa Security.txt slēdzi**, kamēr fails nāk no repo.
- **Nekad neieraksti `p=quarantine`/`p=reject`, pirms `rua` atskaites nav
  nostrādājušas 2–4 nedēļas.**
- **Nekad nepaplašini deploy token tiesības**, lai kādu no šiem soļiem izdarītu
  no repo. Paneļa solis ir lētāks par token uz diska, kas redz DNS.
- **Nekad neieraksti konkrētas IP adreses vai pasta hostinga vārdus** šajā vai
  citā `wiki/`, `BACKLOG.md`, `docs/` failā — tie iet uz `private/`.

## Statuss 2026-09-16 (pēc izpildes ~11:45 LV)

Izpildīts ar API, nevis panelī — no pilnā konta tokena uz 1 dienu izkalts
zonas tokens (DNS Write + Zone Security Center Insights + DMARC Reports),
pēc darba **atsaukts** (`DELETE /accounts/…/tokens/{id}` → success). Pastāvīgais
deploy tokens nemainīts (joprojām tikai `Workers Scripts:Edit`).

- **SPF (#3): IZPILDĪTS** — `v=spf1 mx include:<…> ~all` dzīvs (pārbaudīts pret 1.1.1.1).
- **DMARC (#4): 1. SOLIS IZPILDĪTS** (2. solis — 2026-10-20, § 3) — `p=none; rua=mailto:info@atmina.lv; fo=1`.
  DMARC Management API publiski neeksistē (5 ceļi = 404), tāpēc `rua` pagaidām
  iet uz publisko kontaktu pastkasti; pārslēgšana uz Cloudflare adresi ir viens
  paneļa klikšķis (Email → DMARC Management → Enable, tad `rua=` nomaiņa). 2. solis
  (`p=quarantine`) ne agrāk kā **2026-09-30**, tikai ar tīrām atskaitēm.
- **#1 security.txt: dzīvs**, ieteikums arhivēts (paneļa slēdzis NAV ieslēgts).
- **#2, #5–14, #15: arhivēti** (12 `dismiss=true`, visi `success`).
- **Palikuši aktīvi: 2 no 15** — `spf` un `dmarc`; tie dzēšas paši pēc Cloudflare
  nākamā skenējuma (ieraksti mainīti tikko). Ja pēc 48 h joprojām aktīvi — lasi
  skenera pamatojumu, ne pieņem.
  **Pārbaudīts 2026-09-16 vakarā:** eksports 17:57 LV vēl rāda abus, bet tā
  `scan_performed_on` ir 03:27 UTC — PIRMS labojumiem; dzīvie ieraksti (1.1.1.1)
  ir pareizi. Nav jauna darba, tikai gaidīšana uz nākamo skenējumu.
- **Operatora pasta tests abos virzienos pēc SPF maiņas — IZPILDĪTS 2026-09-16:**
  Gmail galvenes `SPF: PASS`, `DKIM: PASS`, `DMARC: PASS` (3/3); atbilde no Gmail
  pienāca. Pirmā testa vēstule iekrita Gmail spamā ar visiem trim PASS — tas ir
  reputācijas lēmums (jauns domēns, īss «tests» teksts), ne autentifikācija;
  ārstē «Not spam» + normāla sarakste, ne DNS.
- **Mērījumu saucējs:** 15 no 15 izlemti; 13 no 15 izpildīti/arhivēti; 2 gaida skeneri.

## 7. Ārējais drošības tests 2026-10-20 — triāža

Ārējs melnās kastes tests (~40 pieprasījumu, autorizēts ar pagaidu failu
`/.well-known/security-test.txt`, kas pēc testa izdzēsts no koka). Atskaite
glabājas ārpus repo. Verdiktus pārbaudīja otrs modelis (Codex) un advisor.
**7 atradumi: 1 operatora paneļa solis, 1 gaida atskaites, 5 bez darbības.**

| # | Atradums | Verdikts |
|---|---|---|
| 1 | „WAF neaktīvs" (4 testa virknes → 200) | **Bez darbības.** Free plānā ir tikai automātiski ieslēgtais Free Managed Ruleset (dažas augsta riska CVE); pilnais Managed/OWASP ruleset ir Pro+. Statiskā vietnē nav kur injicēt. Paneļa slēdža nav, un tā nav kļūda. |
| 2 | Pasta apakšvārdi atklāj hosta IP | **Bez darbības** — § 4: web origin nav, pasta ieraksti paliek `DNS only`. |
| 3 | HSTS bez `includeSubDomains`/`preload`; `www` 301 bez HSTS | **`includeSubDomains`/`preload` neieviest:** `webmail.` uz 443 rāda sertifikātu ar citu vārdu (`SEC_E_WRONG_PRINCIPAL`, mērīts 2026-10-20) — ar HSTS tā kļūtu par neapejamu kļūdu. `www` 301 nāk no zonas Redirect Rule, `_headers` to nesasniedz; paneļa HSTS slēdzis radītu otru galvenes avotu → robs pieņemts. |
| 4 | DMARC `p=none` | **IZPILDĪTS 2026-10-20** — § 3, 2. solis: `p=quarantine` (operators panelī; dzīvs pret 1.1.1.1 un 8.8.8.8). Pamats: 3 Google atskaites (10-07, 10-18, 10-19) — pašu pasta hosts 8/8 SPF+DKIM pass; 1 neizgāja = trešās puses pārsūtīšana ar `arc=pass`, ne mūsu sūtītājs. Atpakaļceļš: tā pati rinda ar `p=none`. `p=reject` — ne agrāk kā pēc vēl 2–4 nedēļām tīru atskaišu. |
| 5 | Minimālā TLS versija nepārbaudīta | **IZPILDĪTS 2026-10-20** (operators panelī; `openssl s_client` pēc maiņas: 1.0/1.1 atteikti ar `protocol version` alert, 1.2/1.3 strādā — 8/8 pārbaudes uz `atmina.lv` + `www`). Bija: SSL/TLS → Edge Certificates → Minimum TLS Version = **1.2**. Mērīts 2026-10-20 ar `openssl s_client`: TLS 1.0 un 1.1 rokasspiediens izdodas (Cloudflare noklusējums ir 1.0). Pārbaude pēc maiņas — tas pats `openssl s_client -tls1` / `-tls1_1` jāatsaka; Windows `curl` (Schannel) šim neder, jo vecās versijas OS līmenī nepiedāvā. |
| 6 | Nav botu aizsardzības | **Bez darbības** — § 5. Atskaite pati sev pretrunā: `/wp-login.php` šeit „200", pozitīvajos „404"; dzīvi 404. |
| 7 | CT uzskaite nepilna (crt.sh 502) | **Bez darbības** — testa ierobežojums, ne vietnes defekts. |

Pielāgotas WAF kārtulas Free plānā nav vajadzīgas: metodes, kas nav GET/HEAD,
jau atbild 405. Kārtulu pievieno tikai pret izmērītu ļaunprātīgu trafiku.
