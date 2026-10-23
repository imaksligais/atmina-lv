"""Targeted re-render of balsojumi.html only.

Bypasses full generate_public_site() (5-7 min) for one-off balsojumi
tweaks. Renders only the balsojumi page + matrix JSON artifact;
likumprojekti.html renderē `--only=bills`.

Šis skripts likumprojekti.html NEATSVAIDZINA — pēc jauniem balsojumiem
lieto `--only=balsojumi,bills`.
"""
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from src.db import get_db
from src.render._common import (
    DEFAULT_DB_PATH, DEFAULT_OUTPUT_DIR, TEMPLATES_DIR,
    _autolink_bills_filter, _party_short_name, _render_page,
    _resolve_assets_version, _safe_json_filter, _safe_url_filter,
)
from src.render._common.dates import lv_date
from src.render.bills import _fetch_bills
from src.render.votes import _fetch_votes, render_votes

atmina_dir = Path(DEFAULT_OUTPUT_DIR) / "atmina"
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)
env.filters["lv_date"] = lv_date  # vienīgais formatētājs (src/render/_common/dates.py)
env.filters["safe_json"] = _safe_json_filter
env.filters["safe_url"] = _safe_url_filter
env.filters["autolink_bills"] = _autolink_bills_filter
env.globals["_party_short_name"] = _party_short_name
env.globals["assets_version"] = _resolve_assets_version()

db = get_db(DEFAULT_DB_PATH)
votes = _fetch_votes(db)
bills = _fetch_bills(db)
bill_slugs = {b["slug"] for b in bills}
env.globals["bill_slugs"] = bill_slugs

render_votes(env, db, atmina_dir, votes)

# Copy updated bmv1.js/blv1.js since assets are not copied by render_votes.
import shutil
assets_src = Path(TEMPLATES_DIR).parent / "assets"
for fn in ("bmv1.js", "blv1.js", "style.css"):
    src = assets_src / fn
    if src.exists():
        shutil.copy2(src, atmina_dir / "assets" / fn)

print("Done — balsojumi.html + matrix JSON + bmv1.js/blv1.js refreshed")
db.close()
