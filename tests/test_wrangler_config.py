"""wrangler.json invarianti — publiskie URL nes .html un NEDRĪKST saņemt redirect."""
import json
import subprocess
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_CFG = _ROOT / "wrangler.json"


def _cfg() -> dict:
    return json.loads(_CFG.read_text(encoding="utf-8"))


def test_wrangler_config_is_tracked():
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


def test_custom_domains_are_dashboard_managed_not_in_config():
    """atmina.lv + www ir piesaistīti Cloudflare panelī (Workers & Pages → atmina →
    Domains), NEVIS `routes` blokā. Iemesls (2026-09-16): `custom_domain` sinhronizācija
    prasa zonas tiesības (Workers Routes / DNS Edit), bet deploy token apzināti ir
    tikai `Workers Scripts:Edit` — ar `routes` konfigā katrs deploy krīt ar auth 10000.
    workers.dev adrese izslēgta — nav dubultsatura."""
    cfg = _cfg()
    assert "routes" not in cfg, "routes → deploy token nevar sinhronizēt domēnus (sk. docstring)"
    assert cfg["workers_dev"] is False
