# Vecais deploy — Namecheap + rsync (TIKAI rezerve un vēsture)

> **Nav ikdienas ceļš.** Kopš 2026-09-16 deploy = Cloudflare Workers
> ([deploy.md](deploy.md)). Šī lapa glabā rsync/SSH/cPanel zināšanas, kamēr vecais
> hostings ir rezervē (līdz 2026-10-16, BACKLOG 67 / Task 9). Pēc Task 9 lapu var
> dzēst; tās saturs paliek git vēsturē.

## Ārkārtas atkāpšanās uz veco hostu

1. Vecais skripts: `git show c4b5289d^:scripts/deploy.sh > scripts/deploy_rsync.sh`
   (neizsekots pagaidu fails — skripts dara `cd "$(dirname "$0")/.."`, tāpēc tam
   jāstāv `scripts/`). Preflight vārti tajā ir tie paši.
2. `.env.deploy` vajag vecos laukus (forma = `.env.deploy.example`; īstās vērtības
   TIKAI `.env.deploy`): `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_PORT=21098`,
   `DEPLOY_PATH=/home/<cpanel-user>/public_html`, pēc vajadzības `DEPLOY_SSH_KEY`.
3. `bash scripts/deploy_rsync.sh --dry-run`, tad bez `--dry-run`. Vecā skripta
   noklusējums ir additīvs (nedzēš serverī); `--delete` izslēdz `.well-known/` un
   `cgi-bin/` (Let's Encrypt ACME + cPanel CGI).
4. DNS jāpārslēdz atpakaļ uz veco hostu Cloudflare panelī — repo tokenam zonas
   tiesību nav.

**Mērķēta dzēšana serverī** (bez `--delete`): `ssh namecheap "rm ~/public_html/<ceļš>"`
pēc nosaukumu saraksta. Divi vārti pirms tam: (1) pozitīvā kontrole — tā pati
pārbaude pret failiem, kuriem serverī JĀBŪT (2026-08-09 „0 serverī" bija CRLF
rindu beigu dēļ saraksta failā); (2) `grep` pār uzbūvēto koku, ka neviena lapa uz
dzēšamajiem failiem nesaista.

## SSH iestatīšana (cPanel)

- SSH ir Stellar Plus un augstākos plānos. Namecheap ir „password-less" — atslēgu
  importē: cPanel → Security → SSH Access → Manage SSH Keys → **Import Key**
  (publiskā atslēga; privātās atslēgas un paroles lauki TUKŠI) → **Authorize**.
- `~/.ssh/config` (vietturi apzināti — īstās vērtības tikai lokāli):

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

  Klasiskie KEX/hostkey algoritmi vajadzīgi, jo serverī ir vecāks OpenSSH nekā
  klientā (OpenSSH 10+). Pārbaude: `ssh namecheap "pwd"` → `/home/<cpanel-user>`
  bez paroles.

**Atslēgas rotācija (2026-08-01).** Ģenerē LOKĀLI (`ssh-keygen -t ed25519 -f
~/.ssh/atmina-deploy -N ""`), nekad cPanel „Generate a New Key". Import + Authorize;
`.env.deploy` → `DEPLOY_SSH_KEY=<8.3 īsais ceļš>` (`cygpath -d` — `rsync -e` dala
pa atstarpēm, un mājas mapē ir atstarpe); `~/.ssh/config` → jaunais `IdentityFile`.
Pārbaudi abus ceļus, tikai tad dzēs veco atslēgu cPanel-ā.

> **Slazds:** `ssh -i <vecā> -o IdentitiesOnly=yes namecheap` „nostrādā" arī ar
> nederīgu atslēgu, jo config bloka `IdentityFile` (jaunā) arī skaitās. Pareizi:
> `ssh -F /dev/null` ar visiem parametriem komandrindā vai servera patiesība —
> `ssh namecheap "ssh-keygen -lf ~/.ssh/authorized_keys"`.

**Kāpēc vietturi.** `wiki/operations` iet publiskajā spogulī; hosts + cPanel
lietotājvārds piesaistītu anonīmo atmina.lv nosauktam kontam (2026-04-17…08-01 tie
te stāvēja īsti). Vārti: `tests/test_no_deploy_credentials.py` + pirms-sync greps.

## rsync uz Windows

- Git Bash rsync nav. Šajā mašīnā: MSYS2 `rsync` + MSYS2 `openssh`
  (`pacman -S --noconfirm rsync openssh`), `C:\msys64\usr\bin` lietotāja PATH
  **beigās** (lai neaizēno Git for Windows rīkus). Rezerves ceļš — WSL rsync (vecais
  skripts pats atrod distro); tad atslēgas un config jākopē uz WSL `~/.ssh/`.
- **rsync un ssh jābūt no VIENA runtime** (rsync pats spawno ssh); kļūda redzama
  tikai bez termināļa. Vecais skripts ņem ssh blakus atrastajam rsync.
- MSYS2 ssh izšķir `~` uz `/home/<user>`, nevis `$HOME` — skripts padod `-i` +
  `IdentitiesOnly=yes` (`DEPLOY_SSH_KEY`).
- Neder aizvietot: `scp -r` / `sftp` (nav inkrementāli).

## Problēmu novēršana

| Simptoms | Iemesls | Labojums |
|---|---|---|
| `rsync: command not found` | Git Bash bez rsync | MSYS2 rsync (augstāk) vai WSL |
| `Connection closed by <ip>` + PQ KEX brīdinājums | OpenSSH 10 klients, vecs serveris | `KexAlgorithms` bloks |
| Karājas pie „attempting to log in" | Atslēga nav autorizēta | Import + Authorize cPanel-ā |
| `dup() in/out/err failed` | MSYS2 rsync + Git Bash ssh | MSYS2 openssh |
| `safe_read failed … Connection reset` | MSYS2 rsync + Win32 OpenSSH | ssh no rsync runtime |
| `Permission denied (publickey)`, atslēga ir | MSYS2 `~` ≠ `$HOME` | `DEPLOY_SSH_KEY` `.env.deploy` |
| `The source and destination cannot both be remote` | Git Bash ceļu pārveide | `MSYS_NO_PATHCONV=1` |
| Pazūd `.well-known/` | `--delete` bez exclude | `--exclude='.well-known/'` |

## Pārbaude serverī

```bash
ssh namecheap "find ~/public_html -name '*.html' | wc -l && du -sh ~/public_html/"
ssh namecheap "ls -la ~/public_html/ | grep -E '(well-known|cgi-bin)'"
```
