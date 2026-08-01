# Deploy uz Namecheap (atmina.lv)

Statiskā vietne (`output/atmina/`) tiek publicēta uz Namecheap shared hosting caur `rsync` over SSH. Tikai diff tiek nosūtīts, tāpēc ikdienas deploy ir sekundes. Koka izmērs aug ar katru pārskatu un attēlu variantu — 2026-08-09 mērījums: **166 MB, 1948 faili** (`du -sh output/atmina`). Skaitli pārmēri, nevis tici šai rindai; agrāk šeit stāvēja „~37 MB", kas bija novecojis 4,5×.

## Komandas

```bash
# 1. Ģenerē statisko vietni — STANDARTA režīms ir šaurais renders
.venv/Scripts/python.exe -m src.render --only=dashboard,blog,static # skope pēc tā, kas mainījies (`static` vienmēr līdzi — about skaitļi + sitemap)
# pilnais renders (visa vietne, ~3 min) — tikai release/baseline vai pēc bāzes veidnes/assetu maiņas:
# .venv/Scripts/python.exe -c "from src.render import generate_public_site; generate_public_site()"

# 2. Pārbaudes reiss (neko nesūta, parāda, kas mainītos)
bash scripts/deploy.sh --dry-run --no-delete

# 3. Īstais deploy
bash scripts/deploy.sh --no-delete
```

## Additīvais režīms ir NOKLUSĒJUMS pašā kodā (kopš 2026-08-01)

**`--no-delete` vairs nav jāatceras — tas ir no-op.** `scripts/deploy.sh` uzstāda
`DELETE_FLAG=""` pēc noklusējuma, un `--delete` ieslēdzas TIKAI ar eksplicītu
`--delete` karogu. Līdz 2026-08-01 bija otrādi: noklusējums bija destruktīvs, un
katram dokumentētajam izsaucējam vajadzēja atcerēties `--no-delete` — dashboard
deploy poga to nedarīja, tāpēc tās nospiešana būtu noslaucījusi kurētos kokus.
Drošais režīms tagad ir noklusējums, un destrukcija ir opt-in.

Karogu runbooki joprojām raksta klāt, un tā arī jāpaliek: tas ir redzams nodoms
lasītājam un maksā neko. Bet **neuzskati tā izlaišanu par kļūdu** — kods ir
noteicošais, un šī rindkopa līdz 2026-08-09 apgalvoja pretējo.

Iemesls, kāpēc additīvais režīms vispār ir pareizais:
lokālais build NESATUR visu, kas dzīvo serverī — `finanses.html` + `statistika.*` ir
**vienreizējas kurētas analīzes** (overlay no `curated/atmina/`, NEKAD neģenerē ar
`generate_public_site`), un dažu vēsturisko brief attēlu webp/jpg varianti eksistē
tikai serverī. `rsync --delete` ar nepilnu lokālo koku šīs lapas NOSLAUKA no live
vietnes (gandrīz notika 2026-05-30; noķerts dry-run).

Saistītā mācība: **nekad `rmtree output/atmina`** mērīšanai vai tīrīšanai — renderē
uz tmp dir. Ja kādreiz tiešām vajag `--delete` (servera reclaim), vispirms
`--dry-run` un pārliecinies, ka curated + visu attēlu varianti ir lokālajā kokā.

## Preflight vārti pirms rsync (abi obligāti, automātiski)

`deploy.sh` pirms sūtīšanas izpilda divas pārbaudes ar `.venv` python; katra
kļūme = `exit 1`, deploy nenotiek. Apzināta apiešana abām: `--no-output-check`
(tas skar ABAS — tas ir viens karogs diviem vārtiem, neviens atsevišķs).

1. **`scripts/check_output.py`** (kopš 2026-08-01) — uzbūvētā koka atsauces
   (`src=`/`href=`/og:image) izšķiras pret failu + `sitemap.xml` abos virzienos.
   Additīvajam deploy salauzts ref paliek live uz mūžu, tāpēc pārbaude ir pirms
   sūtīšanas, ne pēc. Izņēmumi: `scripts/output_check_allowlist.txt` (ar iemeslu).
2. **`scripts/check_output.py --publish-gate-only`** (kopš 2026-08-09, T15) —
   neviens deploy nedrīkst aiznest `blog/<datums>.html`, kuras brief nav izgājis
   publicēšanas vārtus. `check.sh` pilnais renders liek dienas MELNRAKSTU kokā,
   un additīvais deploy to publicētu (2026-08-09 tā nonāca live 08-09 pārskats).
   v1 heiristika: briefam jābūt `brief_images.approved=1`; orfāna lapa bez DB
   brief = bloķē; DB nepieejama = hard fail. Apzināti NAV `check.sh` daļa — tam
   jāpaliek zaļam, kamēr melnraksts kokā eksistē. Vēsturiskais #222 ir
   allowlistā. Atlikums: eksplicīts publish karogs (BACKLOG § Dati/DB).

Ieteikums: ja publish-gate bloķē deploy pirms vakara rutīnas pabeigšanas — tas
ir vārta mērķis, ne kļūme; pabeidz vārtus (attēla apstiprinājums) vai izmērs
melnraksta lapu no koka pirms deploy.

## Arhitektūra

- `scripts/deploy.sh` — rsync wrapper. Nolasa credentials no `.env.deploy` (gitignored).
- `.env.deploy.example` — template (checked in).
- `.ssh/config` alias `namecheap` — satur host, port, user, `IdentityFile`, un klasiskos KEX/hostkey algoritmus, jo Namecheap darbina vecāku OpenSSH nekā klienta OpenSSH 10+.
- `--delete` aktīvs **tikai ar eksplicītu `--delete` karogu** (sk. § augstāk), un arī tad **izslēdz `.well-known/` un `cgi-bin/`** — lai neiznīcinātu Let's Encrypt ACME challenge dir (SSL atjaunošana) un cPanel pārvaldīto CGI dir.
- **Mērķēta attālināta dzēšana bez `--delete`.** Kad jāizņem konkrēti faili (2026-08-09: 188 noraidītu brief attēlu varianti), pareizais ceļš ir SSH + `rm` pēc nosaukumu saraksta, nevis `rsync --delete` — pēc šaura render lokālais koks ir nepilns, un `--delete` noslaucītu visu, ko tas renders neemitēja. Divi vārti pirms dzēšanas: (1) pozitīvā kontrole — palaid to pašu pārbaudi pret nosaukumiem, kuriem serverī JĀBŪT, un pārliecinies, ka tie tiek atrasti; (2) `grep` pār uzbūvēto koku, ka neviena lapa uz dzēšamajiem failiem nesaista. Pirmais vārts nav formalitāte: 08-09 pirmā inventarizācija rādīja „0 serverī" tikai tāpēc, ka saraksta failam bija CRLF rindu beigas, un bez kontroles secinājums būtu bijis „nav ko tīrīt".

## Pirmreizējā iestatīšana

### 1. Atļaut SSH piekļuvi Namecheap cPanel

SSH jau iekļauts Stellar Plus un augstākos plānos. Stellar basic — nav pieejams.

### 2. Augšupielādēt publisko atslēgu cPanel (nevajag paroli)

Namecheap ir "password-less" — auto-login no Namecheap dashboard nedod tev cPanel paroli. Tā vietā:

1. Namecheap Dashboard → Hosting List → **Manage** → **Go to cPanel**
2. cPanel → Security → **SSH Access** → **Manage SSH Keys**
3. **Import Key** (nevis "Generate a New Key"):
   - Key Name: `atmina-laptop` (vai pēc izvēles)
   - Paste the Public Key: `~/.ssh/id_ed25519.pub` saturs
   - Paste the Private Key: **atstāt tukšu**
   - Key Passphrase: **atstāt tukšu**
4. Atgriezties uz Manage SSH Keys → **Authorize** jauno atslēgu

### 3. `~/.ssh/config` uz klienta

Pievienot bloku (jau izdarīts, skat. `~/.ssh/config`). **Vietturi zemāk ir apzināti** — īstais
hosts un cPanel lietotājvārds dzīvo TIKAI `.env.deploy` (gitignorēts) un lokālajā `~/.ssh/config`;
šis fails iet publiskajā spogulī, tāpēc konkrētas vērtības te nedrīkst nonākt (sk. § Kāpēc vietturi):

```
Host server123.web-hosting.com namecheap
    HostName server123.web-hosting.com
    User cpanelusername
    Port 21098
    IdentityFile ~/.ssh/id_ed25519
    KexAlgorithms +curve25519-sha256,curve25519-sha256@libssh.org,ecdh-sha2-nistp256,ecdh-sha2-nistp384,ecdh-sha2-nistp521,diffie-hellman-group14-sha256,diffie-hellman-group16-sha512,diffie-hellman-group18-sha512,diffie-hellman-group-exchange-sha256
    HostKeyAlgorithms +ssh-rsa,rsa-sha2-256,rsa-sha2-512
    PubkeyAcceptedAlgorithms +ssh-rsa,rsa-sha2-256,rsa-sha2-512
```

Pārbaude: `ssh namecheap "pwd"` → jāizvada tavs cPanel mājas ceļš (`/home/<cpanel-user>`) bez paroles prompt.

### 4. `.env.deploy` repo root

Forma (identiska `.env.deploy.example`; īstās vērtības ņem no cPanel un raksti TIKAI `.env.deploy`):

```
DEPLOY_HOST=server123.web-hosting.com
DEPLOY_USER=cpanelusername
DEPLOY_PORT=21098
DEPLOY_PATH=/home/cpanelusername/public_html
```

### Atslēgas rotācija (2026-08-01)

Deploy atslēga rotēta pēc tam, kad atklājās, ka hosts + lietotājvārds bija publiski (sk. § zemāk). Recepte, ja kādreiz jāatkārto:

1. **Ģenerē LOKĀLI**, nekad cPanel „Generate a New Key" — tas uztaisītu privāto atslēgu uz servera: `ssh-keygen -t ed25519 -f ~/.ssh/atmina-deploy -N "" -C "atmina-deploy-<datums>"`, tad `chmod 600`.
2. cPanel → SSH Access → **Import Key**: vārds + PUBLISKĀ atslēga; privātās atslēgas un paroles lauki paliek **tukši**. Tad Manage → **Authorize**.
3. `.env.deploy`: `DEPLOY_SSH_KEY=<8.3 īsais ceļš>/.ssh/atmina-deploy`. **Īsais ceļš ir obligāts** (`cygpath -d`) — `rsync -e` vērtību sadala pa atstarpēm, un šīs mašīnas mājas mapē ir atstarpe.
4. `~/.ssh/config` → `IdentityFile ~/.ssh/atmina-deploy` (interaktīvajam `ssh namecheap`).
5. Pārbaudi **abus** ceļus: `ssh namecheap "pwd"` un `bash scripts/deploy.sh --dry-run --no-delete`. Tikai tad dzēs veco atslēgu cPanel-ā.
6. Veco privāto atslēgu pārsauc par `retired-<datums>-*`, nevis dzēs uzreiz.

> **SLAZDS, kas deva viltus rezultātu (2026-08-01).** Rotācijas pārbaude ar `ssh -i ~/.ssh/<vecā> -o IdentitiesOnly=yes namecheap` **nostrādāja veiksmīgi un lika domāt, ka vecā atslēga joprojām der.** Tā nederēja. `IdentitiesOnly=yes` ierobežo līdz identitātēm, kas norādītas **konfigurācijā VAI komandrindā** — un `~/.ssh/config` Host blokā jau bija `IdentityFile` uz JAUNO atslēgu, tāpēc katrs mēģinājums klusi autentificējās ar to. Blakus pierādījums, ka tests ir nepareizs: ar to pašu metodi „nostrādāja" arī pilnīgi nesaistīta cita projekta atslēga.
>
> Pareizi ir viens no diviem: (a) `ssh -F /dev/null` ar visiem parametriem komandrindā, vai (b) nolasi servera patiesību — `ssh namecheap "ssh-keygen -lf ~/.ssh/authorized_keys"`, kam jārāda tieši viena atslēga ar jaunās pirkstu nospiedumu. (b) ir ātrāks un neapstrīdams.

### Kāpēc vietturi, ne īstās vērtības

`wiki/operations` ir NEGRIEZT sarakstā (`docs/funding/repo-sync.md`), tāpēc šis fails ir publisks
katrā sync. Hosts + cPanel lietotājvārds + ports ir puse no SSH pieteikšanās un pilna hostinga
konta identitāte — un tas piesaista anonīmi publicēto atmina.lv vienam nosauktam kontam.
2026-04-17…2026-08-01 tie te stāvēja īsti un bija publiski lasāmi; sanitizēts 2026-08-01.
Vārti, kas to tur: `tests/test_no_deploy_credentials.py` (krīt `check.sh` laikā, ja `.env.deploy`
vērtība parādās kādā izsekotā failā) + pirms-sync greps `repo-sync.md` kontrolsarakstā.

## Windows-specific: rsync

Git Bash uz Windows **nav rsync**, un uz šīs mašīnas tā nav nekur — ne PATH-ā, ne `C:\Program Files\Git\usr\bin\`. `scripts/deploy.sh` tāpēc izvēlas izpildītāju šādā secībā:

1. **Vietējais `rsync`**, ja tas ir PATH-ā — nekādas WSL, nekādas ceļu translācijas, nekāda atsevišķa `~/.ssh/`. Šis ir vēlamais ceļš.
2. **WSL rsync** — vispirms noklusējuma distro, tad jebkurš distro, kuram rsync ir. Agrāk te bija cietkodēts `wsl -d Hermes`; tas piesēja publicēšanu vienam nosauktam distro, kas šim repo nepieder — atinstalē to, un deploy nomirst ar neskaidru kļūdu tieši publicēšanas brīdī. Tagad tas tiek meklēts.
3. Ja neviens no tiem — skaidra kļūda ar norādi uzstādīt rsync.

### Vietējais rsync (uzstādīts 2026-07-25 — WSL vairs nav vajadzīga)

Šai mašīnai 1. solis tagad izpildās: `rsync` 3.4.4 no MSYS2, un WSL ceļš vairs netiek aiztikts. Uzstādīšana bija:

```bash
winget install --id MSYS2.MSYS2 -e
C:\msys64\usr\bin\bash.exe -lc "pacman -S --noconfirm rsync"
# C:\msys64\usr\bin pievienots lietotāja PATH BEIGĀS
```

**Beigās, ne sākumā** — tas ir būtiski. Tā `rsync` atrodas, bet MSYS2 pārējie rīki neaizēno Git for Windows savus. Pārbaudīts: `ssh`, `grep`, `sed`, `awk`, `find`, `sort` joprojām atrisinās uz `/usr/bin/*`, `git` uz `/mingw64/bin/git`, un tikai `rsync` uz `/c/msys64/usr/bin/rsync`.

Atsevišķā WSL `~/.ssh/` atspoguļošana (zemāk) vairs nav vajadzīga.

Uz citas mašīnas: tas pats, vai `cwRsync` bināri, ieliekot `rsync.exe` un tā DLL PATH-ā.

### rsync un ssh jānāk no VIENA runtime (2026-07-26)

Sākotnēji šeit bija rakstīts, ka vietējais rsync vienkārši lieto Git Bash `ssh`. **Tas ir nepareizi**, un kļūda parādās tikai tad, kad stdio nav terminālis — t.i. automatizētā vai caur rīku pārtvertā palaidienā. Interaktīvā logā tas iet, tāpēc 07-25 uzstādīšana izskatījās veiksmīga.

rsync **pats spawno ssh**, tāpēc abiem jābūt no viena runtime. Pārbaudītas visas trīs kombinācijas:

| rsync | ssh | Rezultāts |
|---|---|---|
| MSYS2 `/c/msys64/usr/bin/rsync` | Git Bash `/usr/bin/ssh` | `dup() in/out/err failed`, savienojums krīt uzreiz |
| MSYS2 | Win32 `C:\Windows\System32\OpenSSH\ssh.exe` | savienojas un autentificējas, bet `safe_read failed / connection reset` — protokola straume lūst |
| MSYS2 | MSYS2 `/c/msys64/usr/bin/ssh` | **strādā** |

Tāpēc uzstādīts arī MSYS2 openssh, un `deploy.sh` izvēlas ssh, kas atrodas **blakus** atrastajam rsync, ja tas atšķiras no PATH ssh:

```bash
C:\msys64\usr\bin\bash.exe -lc "pacman -S --noconfirm openssh"
```

**Divi slazdi, kas nāk līdzi** (abi apstrādāti `deploy.sh`, komentāri pie koda):

1. **`~` neizšķiras uz `$HOME`.** MSYS2 ssh lasa savu `/etc/passwd` un meklē `/home/<user>/.ssh`, nevis mantoto `HOME=/c/Users/<user>`. Rezultāts ir maldinošs `Permission denied (publickey)`, lai gan atslēga eksistē. Skripts tāpēc padod `-i`, `UserKnownHostsFile` un `IdentitiesOnly=yes`. Atslēgas ceļu var pārrakstīt ar `DEPLOY_SSH_KEY` `.env.deploy` failā; noklusējums ir `~/.ssh/id_ed25519`.
2. **`rsync -e` sadala vērtību pa atstarpēm.** Mājas ceļš ar atstarpi (`C:\Users\<vārds uzvārds>\…`) salauztu komandu. Ceļš tiek pārvērsts 8.3 īsajā formā ar `cygpath -d`, kurā atstarpju nav. Ja atstarpe tomēr paliek, skripts apstājas ar skaidru kļūdu, nevis ar neizskaidrojamu autentifikācijas atteikumu.

WSL zars šo nesaņem — tur ssh dzīvo distro iekšienē, un Windows ceļus tam dot nedrīkst.

**Kas NEDER aizvietošanai:** `scp -r` un `sftp` (nav inkrementāli — katrs deploy augšupielādētu visu koku no jauna). `rclone` ar sftp aizmuguri der semantiski (`copy` pēc noklusējuma nedzēš, kas sakrīt ar mūsu `--no-delete` likumu), bet prasa `deploy.sh` pārrakstīšanu un citu izmaiņu noteikšanu — jēga tikai tad, ja rsync uzstādīšana kāda iemesla dēļ nav iespējama.

### WSL ceļa SSH atspoguļošana

Vajadzīga TIKAI tad, ja paliec pie 2. soļa. WSL ir **atsevišķs `~/.ssh/`** no Git Bash, tāpēc atslēgas un config jāatspoguļo (`<distro>` = tas, ko deploy.sh atrada):

```bash
wsl -d <distro> -- bash -c '
mkdir -p ~/.ssh && chmod 700 ~/.ssh
cp "/mnt/c/Users/<user>/.ssh/id_ed25519"      ~/.ssh/
cp "/mnt/c/Users/<user>/.ssh/id_ed25519.pub"  ~/.ssh/
cp "/mnt/c/Users/<user>/.ssh/config"          ~/.ssh/
cp "/mnt/c/Users/<user>/.ssh/known_hosts"     ~/.ssh/ 2>/dev/null || true
chmod 600 ~/.ssh/id_ed25519 ~/.ssh/config
'
```

Pārbaude: `wsl -d <distro> -- ssh namecheap "pwd"`.

Ja `~/.ssh/config` tiek modificēts Windows pusē, jāatkārto cp uz WSL.

## Problēmu novēršana

| Simptoms | Iemesls | Labojums |
|---|---|---|
| `rsync: command not found` | Git Bash rsync trūkst | Skripts pāriet uz WSL un pats atrod distro ar rsync; ja neatrod, uzstādi vietējo rsync (skat. augstāk) — tas ir noturīgākais labojums |
| `Connection closed by <ip>` + PQ KEX brīdinājums | OpenSSH 10 klients, OpenSSH 9 serveris | `~/.ssh/config` `KexAlgorithms` bloks (skat. augstāk) |
| Hanged pie "attempting to log in" | SSH atslēga nav autorizēta serverī | Re-import + Authorize cPanel "Manage SSH Keys" |
| `dup() in/out/err failed` + `connection unexpectedly closed (0 bytes)` | rsync un ssh no dažādiem runtime (MSYS2 rsync dzen Git Bash ssh); parādās TIKAI bez termināļa | Uzstādi MSYS2 openssh; `deploy.sh` pats paņem blakus esošo ssh (skat. augstāk) |
| `safe_read failed to read 4 bytes: Connection reset` | MSYS2 rsync ar Win32 OpenSSH — autentifikācija iet, protokols lūst | Tas pats: lieto ssh no rsync runtime, nevis `System32\OpenSSH` |
| `Permission denied (publickey)`, lai gan atslēga eksistē | MSYS2 ssh izšķir `~` uz `/home/<user>`, ne uz `$HOME` | `deploy.sh` padod `-i` + `IdentitiesOnly`; ja atslēga citur — `DEPLOY_SSH_KEY` `.env.deploy` |
| `The source and destination cannot both be remote` | Git Bash path-mangling | Skripts eksportē `MSYS_NO_PATHCONV=1` — pārbaudi, vai tas ir fallback ceļā |
| Deploy nodzēš `.well-known/` | `--delete` bez exclude | Pārbaudi, vai `--exclude='.well-known/'` ir `scripts/deploy.sh` |

## Verifikācija pēc deploy

```bash
# Failu skaits un izmērs serverī
ssh namecheap "find ~/public_html -name '*.html' | wc -l && du -sh ~/public_html/"

# Pārbaudīt, vai .well-known un cgi-bin saglabājušies
ssh namecheap "ls -la ~/public_html/ | grep -E '(well-known|cgi-bin)'"
```

## Politiķa deaktivācijas checklist (`relationship_type='inactive'`)

`--no-delete` standing mode nozīmē, ka deaktivēta politiķa lapa **pati nepazūd** ne no `output/`, ne no servera (2026-06-13 Kļaviņa/Freidenfelda mācība):

1. `generate_public_site()` pārstāj lapu ģenerēt, bet **NEdzēš** stale `politiki/{slug}.html` — dzēs manuāli `output/atmina/politiki/` UN serverī: `ssh namecheap "rm ~/public_html/politiki/<slug>.html"`.
2. `inactive` filtrē: x.py, positions.py, dashboard, personas, parties, links (nodes), profila ģenerāciju. Pārbaudi `political_tensions` — ja deaktivētajam ir tensions rindas, dzēs tās vai pārliecinies, ka render filtrs tās izlaiž (dangling-link risks spriedzes.html / saites grafā).
3. Editorial sintēzes (manuāls teksts) var pieminēt vārdā — operatora editorial lēmums, ne automātika.
4. **`wiki/persons/<slug>.md` paliek un kļūst par orphan** — `wiki_sync()` deaktivēto no `persons/personas.md` izņem, bet pašu lapu nedzēš, tāpēc `wiki_lint` to mūžīgi rāda kā `orphan_page` un `index.md` statusā stāv „Lint: N orphans". Tas ir GAIDĪTS, ne defekts (2026-07-25: 1 orphan = Freidenfelds, id=190). Ja orphans krājas, dzēs lapu manuāli; pirms tam apsver, vai tās pozīcijas vēl vajag vēsturei.
5. Ja profils dzēšams PILNĪBĀ (privātuma lūgums, 2026-06-13 precedents): backup DB pirms purge; vec0 vektoru tabulām vajag `sqlite_vec.load()`; `claim_vectors`→claim_id, `document_vectors`→chunk_id.
