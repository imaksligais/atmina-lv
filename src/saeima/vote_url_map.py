"""Vecās `Voting?ReadForm&parentID=` balsojumu saites → pastāvīgās `/0/<UNID>?OpenDocument`.

Titania `parentID=` lapa vēlāk ir tukša. DB saites nomainītas 2026-11-04
(`data/rollback_vote_permanent_urls_2026-11-04.sql`), bet publicēto pārskatu
tekstu nemainām: tas ir apstiprināts ar hešu (T15). Tāpēc renderā saiti nomaina
pēc kartējuma. Nezināma saite paliek, kā ir.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

_MAP_PATH = Path(__file__).with_name("parentid_url_map.json")
_PARENT_ID_URL_RE = re.compile(
    r"https://titania\.saeima\.lv/LIVS\d+/SaeimaLIVS2_DK\.nsf/Voting\?ReadForm(?:&|&amp;)parentID=[0-9a-fA-F-]{16,36}"
)


@lru_cache(maxsize=1)
def _load_map() -> dict[str, str]:
    return json.loads(_MAP_PATH.read_text(encoding="utf-8"))


def permanent_vote_url(url: str) -> str | None:
    """Pastāvīgā saite vecajai `parentID=` saitei; `None`, ja nav viennozīmīgas.

    Pārskatā 584 ID ir nogriezti, tāpēc der arī viens vienīgs prefiksa trāpījums.
    """
    url = url.replace("&amp;", "&")
    mapping = _load_map()
    if url in mapping:
        return mapping[url]
    hits = [new for old, new in mapping.items() if old.startswith(url)]
    return hits[0] if len(hits) == 1 else None


def rewrite_parentid_vote_urls(text: str) -> str:
    """Nomaina tekstā visas zināmās `parentID=` saites; pārējo atstāj."""
    return _PARENT_ID_URL_RE.sub(lambda m: permanent_vote_url(m.group(0)) or m.group(0), text)
