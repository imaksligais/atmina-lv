"""Noplūdes vārti: `.env.deploy` vērtības nedrīkst parādīties nevienā izsekotā failā.

Konteksts (2026-08-01): `wiki/operations/deploy.md` no 2026-04-17 nesa ĪSTO
`DEPLOY_HOST` / `DEPLOY_USER` / `DEPLOY_PATH` — hostu, cPanel lietotājvārdu un
mājas ceļu — un `wiki/operations` ir `docs/funding/repo-sync.md` NEGRIEZT
sarakstā, tāpēc tas aizgāja KATRĀ publiskajā sync un bija lasāms publiskajā
spogulī. Pirms-sync grepu kontrolsaraksts šo klasi neaptvēra, tāpēc tas gāja
cauri tīrs, kamēr akreditācijas dati stāvēja failā, ko tas nekad neskatījās.
(Pats kontrolsaraksts dzīvo `docs/funding/repo-sync.md` — apzināti izslēgts no
publiskā koka, jo tā punkti nosauc tieši tos vārdus, kurus meklē.)

Kāpēc tas svarīgi: hosts + lietotājvārds + ports ir puse no SSH pieteikšanās uz
zināma-derīga konta (nav ko uzminēt) un pilna cPanel konta identitāte — plus tas
piesaista anonīmi publicēto atmina.lv vienam nosauktam hostinga kontam, pretēji
CLAUDE.md § Standing Decisions anonimitātes lēmumam. `SECURITY.md` pats sauc
"Credential / secret leakage in the repository" par pirmo IN-SCOPE punktu.

Tests ir apzināti tievs un lēts, lai to varētu turēt `scripts/check.sh` ceļā:
lasa `.env.deploy` (gitignorēts, tāpēc CI to neredz → skip) un pārbauda, ka
neviena tā vērtība neparādās `git ls-files` kokā.

Ja tests krīt: aizvieto vērtību ar vietturi (`.env.deploy.example` formas —
`server123.web-hosting.com`, `cpanelusername`) TAJĀ failā. Nekad neatslēdz šo
testu, lai "ātri nosūtītu" — noplūdusī vērtība publiskajā spogulī prasa gan
sanitizāciju, gan atslēgu rotāciju.
"""

import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
ENV_DEPLOY = REPO / ".env.deploy"

# Ports (21098) ir Namecheap koplietotā hostinga standarts un jau stāv
# izsekotajā `.env.deploy.example`, tāpēc tas NAV noslēpums un netiek pārbaudīts.
SECRET_KEYS = ("DEPLOY_HOST", "DEPLOY_USER", "DEPLOY_PATH")

# `.env.deploy.example` vietturi: ja kāda vērtība sakrīt ar tiem, tā nav
# noslēpums, bet nepiepildīts template — izlaižam, lai tests nekristu tukšā.
PLACEHOLDERS = {
    "server123.web-hosting.com",
    "cpanelusername",
    "/home/cpanelusername/public_html",
}

# Faili, kuriem vērtība ir leģitīma pēc definīcijas.
ALLOWED = {".env.deploy.example"}


def _load_secrets() -> dict[str, str]:
    """`.env.deploy` KEY=value → dict, tikai SECRET_KEYS un tikai īstās vērtības."""
    secrets: dict[str, str] = {}
    for raw in ENV_DEPLOY.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip("\"'")
        if key in SECRET_KEYS and value and value not in PLACEHOLDERS:
            secrets[key] = value
    return secrets


def _tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True
    )
    return [p for p in out.stdout.splitlines() if p and p not in ALLOWED]


@pytest.mark.skipif(not ENV_DEPLOY.exists(), reason=".env.deploy nav (CI / svaigs klons)")
def test_env_deploy_values_absent_from_tracked_files():
    """Neviena `.env.deploy` vērtība nedrīkst būt nevienā izsekotā failā.

    Kļūdas ziņojums nosauc failu un atslēgu, BET NE vērtību — citādi noslēpums
    nonāktu CI logā, kas ir tieši tas, no kā mēs izvairāmies.
    """
    secrets = _load_secrets()
    if not secrets:
        pytest.skip(".env.deploy satur tikai vietturus")

    hits: list[str] = []
    for rel in _tracked_files():
        path = REPO / rel
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except (OSError, UnicodeDecodeError):
            continue  # binārie / nelasāmie — vērtība tur nav teksta formā
        for key, value in secrets.items():
            for lineno, line in enumerate(text.splitlines(), 1):
                if value in line:
                    hits.append(f"{rel}:{lineno} satur {key} vērtību")

    assert not hits, (
        "Deploy akreditācijas dati izsekotos (= publiskojamos) failos:\n  "
        + "\n  ".join(hits)
        + "\n\nAizvieto ar vietturi (sk. .env.deploy.example). Ja tas jau ir "
        "aizgājis publiskajā spogulī — sanitizē, pārsyncē UN rotē atslēgu."
    )


@pytest.mark.skipif(not ENV_DEPLOY.exists(), reason=".env.deploy nav (CI / svaigs klons)")
def test_deploy_runbook_uses_placeholders():
    """`wiki/operations/deploy.md` ir NEGRIEZT sarakstā → tikai vietturi.

    Atsevišķs tests no augšējā ar nolūku: šis ir konkrētais fails, kur noplūde
    notika, un tas paliek zaļš arī tad, ja kāds pārkārto vispārīgo pārbaudi.
    """
    runbook = REPO / "wiki" / "operations" / "deploy.md"
    text = runbook.read_text(encoding="utf-8")
    leaked = [key for key, value in _load_secrets().items() if value in text]
    assert not leaked, (
        f"wiki/operations/deploy.md satur īstās vērtības: {', '.join(leaked)}. "
        "Šis fails ir publisks katrā sync (docs/funding/repo-sync.md NEGRIEZT saraksts)."
    )
