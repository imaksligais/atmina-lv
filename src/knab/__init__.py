"""KNAB politiskā finansējuma pakotne (ziedojumi, deklarācijas, anomālijas).

Moduļi:

- ``src.knab.parse``   — konstantes + tīrie parseri (bez tīkla, bez DB)
- ``src.knab.ingest``  — JSON API klients, dedup kāpnes, glabāšana
- ``src.knab.queries`` — lasīšanas puses vaicājumi (tikai SELECT)
- ``src.knab.analyze`` — savstarpējās pārbaudes un anomāliju atklāšana

Šis ``__init__`` ir pakotnes virsma: visi publiskie nosaukumi, kas agrāk
dzīvoja plakanajos ``src/knab.py`` un ``src/knab_analyze.py`` moduļos, ir
re-eksportēti šeit, tāpēc ``from src.knab import fetch_all`` un
``import src.knab`` strādā tāpat kā pirms 2026-09-05 sadalīšanas.

UZMANĪBU testiem: ``monkeypatch.setattr`` jāliek uz KONKRĒTĀ moduļa
(``src.knab.ingest``), nevis uz šī pakotnes objekta — re-eksportēts vārds ir
kopija, un ielādes funkcijas savus palīgus meklē sava moduļa globālajos.
"""

from src.knab.analyze import (
    detect_donation_declaration_mismatch,
    detect_family_clusters,
    detect_limit_violations,
    detect_multi_party_donors,
    link_donors_to_politicians,
    run_all_checks,
)
from src.knab.ingest import (
    fetch_all,
    fetch_all_declarations,
    fetch_all_donations,
    fetch_declaration_details,
)
from src.knab.parse import (
    API_BASE,
    DECLARATIONS_URL,
    DONATIONS_URL,
    FIELD_MAP,
    KNAB_BASE,
    LEGACY_CUTOFF_DATE,
    LVL_TO_EUR_RATE,
    RATE_LIMIT_SECONDS,
    TRACKED_PARTIES,
    parse_declaration_detail,
    parse_declarations_page,
    parse_donations_page,
)
from src.knab.queries import get_alerts, get_party_summary, get_top_donors

__all__ = [
    # parse — konstantes
    "API_BASE",
    "DECLARATIONS_URL",
    "DONATIONS_URL",
    "FIELD_MAP",
    "KNAB_BASE",
    "LEGACY_CUTOFF_DATE",
    "LVL_TO_EUR_RATE",
    "RATE_LIMIT_SECONDS",
    "TRACKED_PARTIES",
    # parse — legacy HTML parseri
    "parse_declaration_detail",
    "parse_declarations_page",
    "parse_donations_page",
    # ingest
    "fetch_all",
    "fetch_all_declarations",
    "fetch_all_donations",
    "fetch_declaration_details",
    # queries
    "get_alerts",
    "get_party_summary",
    "get_top_donors",
    # analyze
    "detect_donation_declaration_mismatch",
    "detect_family_clusters",
    "detect_limit_violations",
    "detect_multi_party_donors",
    "link_donors_to_politicians",
    "run_all_checks",
]
