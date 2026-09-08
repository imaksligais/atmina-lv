"""``_common`` slug / partiju / kategoriju palīgi.

Izgriezts no vienfaila ``src/render/_common.py`` 2026-09-05 (plāna 5.8).
``src.topic_map`` un ``src.outlets`` importi paliek funkciju iekšienē
(kā bija) — moduļa līmenī tikai lapu-moduļi ārpus ``src.render.*``.
"""

from __future__ import annotations

import sqlite3
import sys
from typing import Any, Optional

from src.coalition import lookup_party_short_name
from src.lv_text import slugify

# ── Slug / party / format helpers ───────────────────────────────────


# Vēsturiskais privātais nosaukums — 20 `src/render/*` patērētāji un testi
# importē `_slugify` no šejienes. Vienīgā definīcija:
# `src/lv_text.py` (identiska ar bijušo `src/wiki.py:35` kopiju).
_slugify = slugify


def _topic_page_href(topic: Optional[str], prefix: str = "../") -> str:
    """Href uz tēmas lapu — TIKAI kanoniskajām grupām; brīvas formas
    claims.topic lapas temas/<slug>.html neeksistē (src/render/topics.py
    renderē tikai 33 grupas), tāpēc tām atgriež tēmu direktoriju.
    2026-08-22: index/politiki/pretrunas lapas lika 404 saites uz
    temas/robezsargu-riciba-... u.c."""
    from src.topic_map import get_all_group_names
    if topic and topic in get_all_group_names():
        return f"{prefix}temas/{_slugify(topic)}.html"
    return f"{prefix}temas.html"


def _party_page_slug(short_name: str) -> str:
    """Filename-safe slug for a party detail page (``partijas/<slug>.html``).

    Historically this was just ``short_name.lower()``, which breaks when a
    short_name contains a filesystem/path-separator character — e.g. a
    'SV/AJ'-style class label would point the render at a nested/invalid
    path. Rule: lowercase, then map every character that is unsafe in a
    filename (``/ \\ : * ? " < > |`` and whitespace) to ``-``. All
    currently-tracked short_names contain only ``[A-Za-z0-9-]`` so their
    URLs are unchanged (locked by
    ``tests/test_party_page_slug.py::test_existing_party_urls_unchanged``).

    This is the ONE canonical party-page slug — every link to a party page
    (render modules, templates, sitemap) must route through it.
    """
    _UNSAFE = set('/\\:*?"<>|')
    slug = "".join(
        "-" if (ch in _UNSAFE or ch.isspace()) else ch
        for ch in short_name.lower()
    )
    return slug


def _party_short_name(party: str, db=None) -> str:
    """Map party full name to its official short name (NA, JV, etc.).

    Resolution goes through ``src.coalition.lookup_party_short_name()``, whose
    truth source is ``parties.short_name`` (CLAUDE.md T6 second corollary).
    Until 2026-09-05 this held its own 11-entry map that disagreed with the
    brief's (``Stabilitātei!`` → ``ST`` here vs ``S!`` there) and knew nothing
    of the other eight parties in the table. Falls back to
    first-letters-of-words when the label resolves nowhere.
    """
    short = lookup_party_short_name(party, db)
    if short:
        return short
    letters = [w[0].upper() for w in party.split() if w]
    return "".join(letters[:3])


def _persona_category(
    votes_count: int,
    relationship_type: str | None,
    party: str | None,
    role: str | None,
) -> str:
    """Classify a tracked politician into a UI category for the Personas page.

    Rules (first match wins):
      1. votes_count > 0 → Deputāti (active MP regardless of role)
      2. relationship_type = organization → Iestādes un mediji (NBS, LVM,
         LDDK, ziņu raidījumi/aģentūras — pre-2026-06-09 these leaked into
         Amatpersonas (role set) or Citi (bare), and media feeds typed
         'journalist' sat among human journalists)
      3. relationship_type ∈ {journalist, influencer, neutral} → mapped label
      4. party set → Amatpersonas (ministers, party officials)
      5. role set (no party) → Amatpersonas (civil servants, board members)
      6. otherwise → Citi

    Kandidāti category was removed 2026-04-25 evening — even with broadened
    `coalition_status='not_in_saeima'` rule the bucket showed mostly MMN
    members (9 of 12), which gave a misleading impression. Non-Saeima party
    members now flow into Amatpersonas like other party-affiliated
    non-deputies. Re-introduce when there is a credible cross-party
    candidate dataset (e.g. CVK kandidātu saraksts ingest).
    """
    if votes_count > 0:
        return "Deputāti"
    if relationship_type == "organization":
        return "Iestādes un mediji"
    role_map = {"journalist": "Žurnālisti", "influencer": "Ietekmētāji", "neutral": "Analītiķi"}
    if relationship_type in role_map:
        return role_map[relationship_type]
    if party:
        return "Amatpersonas"
    if role:
        return "Amatpersonas"
    return "Citi"


def _outlet_feed_map(
    db: sqlite3.Connection,
    outlets: list[dict[str, Any]] | None = None,
) -> dict[int, dict[str, Any]]:
    """opponent_id -> {short_name, name, slug, hosts} outletam, kuram pieder
    profila X konts (sources.yaml ``x_feeds`` x social_accounts.handle join).

    ``hosts`` ir outleta domēnu saraksts (sources.yaml ``hosts``) — to izmanto
    politicians.py own_pubs vaicājums, lai atlasītu medija paša publikācijas
    pēc source_domain. Aditīvs atslēga; agrākie lasītāji (short_name/name/slug)
    nemainās.

    Handle salīdzinājums case-insensitive; join iet caur social_accounts.handle
    (autoritatīvais), NE tracked_politicians.x_handle (legacy, klusi diverģē —
    sk. CLAUDE.md schema invariants). Dublēts handle divos outletos -> pirmais
    uzvar + stderr brīdinājums. outlets=None ielādē no sources.yaml.
    """
    if outlets is None:
        from src.outlets import load_outlets
        outlets = load_outlets()
    handle_to_outlet: dict[str, dict[str, Any]] = {}
    for o in outlets:
        for h in o.get("x_feeds") or []:
            hl = h.lower()
            if hl in handle_to_outlet and handle_to_outlet[hl]["short_name"] != o["short_name"]:
                print(f"[mediji] @{h} divos outletos — paliek "
                      f"{handle_to_outlet[hl]['short_name']}", file=sys.stderr)
                continue
            handle_to_outlet.setdefault(hl, o)
    if not handle_to_outlet:
        return {}
    m: dict[int, dict[str, Any]] = {}
    # Reālā DB glabā platform='twitter' (vēsturiskais nosaukums); 'x' pieņemts
    # testu/nākotnes rindām. Tikai 'x' šeit nozīmētu klusu 0-rindu join.
    for pid, handle in db.execute(
            "SELECT opponent_id, handle FROM social_accounts "
            "WHERE platform IN ('twitter', 'x')"):
        o = handle_to_outlet.get((handle or "").lower())
        if o is not None:
            m.setdefault(pid, {"short_name": o["short_name"],
                               "name": o["name"], "slug": o["slug"],
                               "hosts": list(o.get("hosts") or [])})
    return m


def _split_org_category(category: str, pid: int, media_feed_ids: set[int]) -> str:
    """'Iestādes un mediji' -> 'Mediji' (outleta feeds) vai 'Iestādes' (pārējie).
    Citas kategorijas iziet cauri nemainītas. Sk. spec 2026-06-10."""
    if category != "Iestādes un mediji":
        return category
    return "Mediji" if pid in media_feed_ids else "Iestādes"


def _bill_slug(document_nr: str) -> str:
    """'1315/Lp14' -> '1315-lp14'.

    Used by `_fetch_bills` / `_fetch_bill_detail` (F3e bills.py target)
    and `_fetch_politician_detail` (F3b politicians.py — links a
    politician's involved bills back to their bill detail page).
    Promoted to `_common` so neither sub-page module imports from the
    other (F4 leaf rule).
    """
    return document_nr.lower().replace("/", "-")

