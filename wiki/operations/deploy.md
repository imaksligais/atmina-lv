# Deploy uz Namecheap (atmina.lv)

Statiskā vietne (`output/atmina/`, ~37 MB) tiek publicēta uz Namecheap shared hosting caur `rsync` over SSH. Tikai diff tiek nosūtīts — pirmais deploy ~11 MB, turpmākie sekundēs.

## Komandas

```bash
# 1. Ģenerē statisko vietni
python -c "from src.render import generate_public_site; generate_public_site()"

# 2. Pārbaudes reiss (neko nesūta, parāda, kas mainītos)
bash scripts/deploy.sh --dry-run

# 3. Īstais deploy — STANDARTA režīms ir --no-delete
bash scripts/deploy.sh --no-delete
```

## `--no-delete` ir noklusētais deploy režīms (standing rule 2026-05-30)

Vienmēr deploy ar `--no-delete`, ja vien apzināti nevāc servera atkritumus. Iemesls:
lokālais build NESATUR visu, kas dzīvo serverī — `finanses.html` + `statistika.*` ir
**vienreizējas kurētas analīzes** (overlay no `curated/atmina/`, NEKAD neģenerē ar
`generate_public_site`), un dažu vēsturisko brief attēlu webp/jpg varianti eksistē
tikai serverī. `rsync --delete` ar nepilnu lokālo koku šīs lapas NOSLAUKA no live
vietnes (gandrīz notika 2026-05-30; noķerts dry-run).

Saistītā mācība: **nekad `rmtree output/atmina`** mērīšanai vai tīrīšanai — renderē
uz tmp dir. Ja kādreiz tiešām vajag `--delete` (servera reclaim), vispirms
`--dry-run` un pārliecinies, ka curated + visu attēlu varianti ir lokālajā kokā.

## Arhitektūra

- `scripts/deploy.sh` — rsync wrapper. Nolasa credentials no `.env.deploy` (gitignored).
- `.env.deploy.example` — template (checked in).
- `.ssh/config` alias `namecheap` — satur host, port, user, `IdentityFile`, un klasiskos KEX/hostkey algoritmus, jo Namecheap darbina vecāku OpenSSH nekā klienta OpenSSH 10+.
- `--delete` aktīvs tikai BEZ `--no-delete` karoga (sk. § augstāk — `--no-delete` ir standarta režīms), un arī tad **izslēdz `.well-known/` un `cgi-bin/`** — lai neiznīcinātu Let's Encrypt ACME challenge dir (SSL atjaunošana) un cPanel pārvaldīto CGI dir.

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

Pievienot bloku (jau izdarīts, skat. `~/.ssh/config`):

```
Host server403.web-hosting.com namecheap
    HostName server403.web-hosting.com
    User atmiohmm
    Port 21098
    IdentityFile ~/.ssh/id_ed25519
    KexAlgorithms +curve25519-sha256,curve25519-sha256@libssh.org,ecdh-sha2-nistp256,ecdh-sha2-nistp384,ecdh-sha2-nistp521,diffie-hellman-group14-sha256,diffie-hellman-group16-sha512,diffie-hellman-group18-sha512,diffie-hellman-group-exchange-sha256
    HostKeyAlgorithms +ssh-rsa,rsa-sha2-256,rsa-sha2-512
    PubkeyAcceptedAlgorithms +ssh-rsa,rsa-sha2-256,rsa-sha2-512
```

Pārbaude: `ssh namecheap "pwd"` → jāizvada `/home/atmiohmm` bez paroles prompt.

### 4. `.env.deploy` repo root

```
DEPLOY_HOST=server403.web-hosting.com
DEPLOY_USER=atmiohmm
DEPLOY_PORT=21098
DEPLOY_PATH=/home/atmiohmm/public_html
```

## Windows-specific: WSL rsync fallback

Git Bash uz Windows **nav rsync**. `scripts/deploy.sh` automātiski pāriet uz WSL (Hermes distro) rsync, ja lokālais nav atrasts. WSL tomēr ir **atsevišķs `~/.ssh/`** no Git Bash — tāpēc SSH atslēgas un config jāatspoguļo:

```bash
wsl -d Hermes -- bash -c '
mkdir -p ~/.ssh && chmod 700 ~/.ssh
cp "/mnt/c/Users/<user>/.ssh/id_ed25519"      ~/.ssh/
cp "/mnt/c/Users/<user>/.ssh/id_ed25519.pub"  ~/.ssh/
cp "/mnt/c/Users/<user>/.ssh/config"          ~/.ssh/
cp "/mnt/c/Users/<user>/.ssh/known_hosts"     ~/.ssh/ 2>/dev/null || true
chmod 600 ~/.ssh/id_ed25519 ~/.ssh/config
'
```

Pārbaude: `wsl -d Hermes -- ssh namecheap "pwd"`.

Ja `~/.ssh/config` tiek modificēts Windows pusē, jāatkārto cp uz WSL.

## Problēmu novēršana

| Simptoms | Iemesls | Labojums |
|---|---|---|
| `rsync: command not found` | Git Bash rsync trūkst | Skripts automātiski pāriet uz WSL; ja nedarbojas, pārbaudi `wsl -d Hermes -- command -v rsync` |
| `Connection closed by <ip>` + PQ KEX brīdinājums | OpenSSH 10 klients, OpenSSH 9 serveris | `~/.ssh/config` `KexAlgorithms` bloks (skat. augstāk) |
| Hanged pie "attempting to log in" | SSH atslēga nav autorizēta serverī | Re-import + Authorize cPanel "Manage SSH Keys" |
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
4. Ja profils dzēšams PILNĪBĀ (privātuma lūgums, 2026-06-13 precedents): backup DB pirms purge; vec0 vektoru tabulām vajag `sqlite_vec.load()`; `claim_vectors`→claim_id, `document_vectors`→chunk_id.
