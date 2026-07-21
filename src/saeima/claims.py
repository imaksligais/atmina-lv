"""Saeimas balsojumu motif → topic + salience kartēšana.

F4.3 izvilkts no src/saeima.py monolīta. Pure functions: regex-based topic
classification + salience aprēķins no motif teksta. Nedz DB writes, nedz
imports no `votes.py` — domāts kā leaf-modulis, ko `votes.py` (un nākotnē
citi) drīkst importēt bez cikla.

Pre-2026-04-17 buga apgabals — sk. komentāru pie `_MOTIF_TOPIC_MAP`: agrāk
naive `keyword.lower() in motif` substring match-ošana 2026-04-16 sesijā
mis-kategorizēja 8/39 votus. Word-boundary fix (per `_stem` un `_word`)
ir te.

Šajā modulī NEdzīvo `generate_claims_from_votes` (kā plāns sākumā paredzēja)
— tā glabājas `votes.py`, jo runtime atkarības pret `VoteResult` un pārējo
vote-pipeline-u plūsmu būtu izveidojušas votes ↔ claims ciklu. claims.py
paliek tīrs topic mapper.
"""

from __future__ import annotations

import re

# Map common legislative keywords to PoliTracker topic groups.
#
# Matching semantics: patterns are anchored at a word boundary on the LEFT
# (`\b`) — stems by default, so `"pārvald"` matches "pārvaldes", "pārvaldība",
# "pārvaldi". Entries wrapped with `_word(...)` are anchored on BOTH ends,
# which is needed for tokens whose suffix would match Latvian inflections
# elsewhere (`"ES"` must not catch words ending in "-es ").
#
# First match wins — put specific phrases BEFORE broader stems so the
# generic `"aizsardzīb"` fallback doesn't eat more precise rules like
# `"tiesību aizsardzīb"` (law enforcement) or `"vides aizsardzīb"` (env).
#
# Prior bug (pre-2026-04-17): the map used naive `keyword.lower() in motif`
# substring matching, so `"ES "` matched any Latvian genitive ending in
# "-es " (aprites, dzīles, apstrādes, ...) and `"aizsardzīb"` over-covered
# justice-related phrases. 8/39 votes in the 2026-04-16 session were
# mis-tagged; switching to word-boundary matching + specific rules fixes
# the regression and prevents future drift.


def _stem(kw: str) -> re.Pattern:
    """Compile `kw` as a stem pattern — anchored at word start only.

    Accepts Latvian inflections after the stem. Used for most topic
    keywords (`"pārvald"` ≈ "pārvaldes"/"pārvaldība"/"pārvaldi").
    """
    return re.compile(r'\b' + re.escape(kw), re.IGNORECASE)


def _word(kw: str) -> re.Pattern:
    """Compile `kw` as a full-word pattern — anchored at both ends.

    Required for ambiguous short tokens. `"ES"` must be exactly the
    abbreviation, not the trailing letters of a Latvian genitive.
    """
    return re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE)


_MOTIF_TOPIC_MAP: list[tuple[re.Pattern, str]] = [
    # --- Child rights (before 'tiesību aizsardzīb' — child-protection law is
    #     a social policy framework, not law-enforcement / justice). ---
    (_stem("Bērnu tiesīb"), "Sociālā politika"),

    # --- Culture / Kultūra (specific institutions; must win before
    #     normalize_topic's "nacionāl" keyword routes cultural bills to
    #     Aizsardzība). ---
    (_stem("koncertzāl"), "Kultūra"),
    (_stem("filharmoni"), "Kultūra"),
    (_stem("bibliotēk"), "Kultūra"),
    (_stem("muzej"), "Kultūra"),
    (_stem("teātr"), "Kultūra"),
    # 2026-06-12 coverage revīzija: autortiesības/sakrālais mantojums/Brīvības
    # piemineklis = kultūra, NOT Valsts pārvalde — guard before normalize routing.
    (_stem("autortiesīb"), "Kultūra"),
    (_stem("sakrālā mantojum"), "Kultūra"),
    (_stem("brīvības pieminekļ"), "Kultūra"),
    (_stem("kultūr"), "Kultūra"),
    (_word("JRT"), "Kultūra"),

    # --- Justice / Tieslietas (specific phrases before generic `aizsardzīb`) ---
    (_stem("tiesību aizsardzīb"), "Tieslietas"),                # law enforcement
    (_stem("personu aizsardzīb"), "Tieslietas"),                 # person protection law
    (_stem("sabiedrības interesēs iesaistīt"), "Tieslietas"),    # whistleblower protection
    (_stem("biometrij"), "Tieslietas"),
    (_stem("datu aizsardzīb"), "Tieslietas"),
    (_stem("personas datu"), "Tieslietas"),
    (_stem("fizisko personu"), "Tieslietas"),
    # 2026-06-12 coverage revīzija: tieslietu fāzes likumi, kas citādi krīt
    # uz generic `pārvald` ("Ieslodzījuma vietu pārvaldes likums") vai
    # `aizsardzīb` — guard pirms abiem fallback-iem.
    (_stem("ieslodzījuma viet"), "Tieslietas"),
    (_stem("noziedzīgi iegūt"), "Tieslietas"),
    (_stem("legalizācij"), "Tieslietas"),
    (_stem("konfiskācij"), "Tieslietas"),
    (_stem("aizturēto person"), "Tieslietas"),

    # --- Municipalities / Pašvaldības (specific land/territory stems; MUST
    #     precede the Budžets `nodokl`/`nodokļ` rules AND generic `pārvald`).
    #     2026-06-12 coverage revīzija: nekustamā īpašuma nodoklis = pašvaldību
    #     ieņēmumi, NOT Budžets — guard before any generic tax stem. ---
    (_stem("nekustamā īpašuma nodokl"), "Pašvaldības"),
    (_stem("administratīvo teritor"), "Pašvaldības"),
    (_stem("teritorijas attīst"), "Pašvaldības"),
    (_stem("zemes privatizācij"), "Pašvaldības"),
    (_stem("zemes reform"), "Pašvaldības"),
    (_stem("dzīvokļa jautāj"), "Pašvaldības"),
    (_stem("speciālās ekonomiskās zonas"), "Pašvaldības"),

    # --- State enterprises (specific; MUST precede generic `pārvald` —
    #     "kapitāla daļu un kapitālsabiedrību pārvaldības likums" matches
    #     `pārvald`). 2026-06-12 coverage revīzija. ---
    (_stem("kapitāla daļu un kapitālsabiedr"), "Valsts kapitālsabiedrības"),

    # --- Public health / social (specific; MUST precede `pārvald` —
    #     "Covid-19 ... izplatības seku pārvarēšanas likums" matches `pārvald`
    #     — un `aizsardzīb`/`sociāl` fallback). 2026-06-12 coverage revīzija. ---
    (_stem("covid-19"), "Veselības aprūpe"),
    (_stem("maternitāt"), "Sociālā politika"),

    # --- Environment / Vide (specific phrases before aizsardzīb/drošīb) ---
    (_stem("vides aizsardzīb"), "Vide"),                         # env protection law
    (_stem("ietekmes uz vidi"), "Vide"),                         # IVN
    (_stem("sugu un biotop"), "Vide"),
    (_stem("zemes dzīl"), "Vide"),
    (_stem("derīg"), "Vide"),                                    # derīgo izrakteņu
    (_stem("ūdens apsaimnieko"), "Vide"),
    (_stem("ķīmisk"), "Vide"),

    # --- Agriculture / Lauksaimniecība (specific before generic `aizsardzīb` —
    #     animal-welfare law is agri policy, not defence; 2026-06-11 regression
    #     mis-tagged 24 votes / 2103 claims as "Aizsardzība un drošība") ---
    (_stem("dzīvnieku aizsardzīb"), "Lauksaimniecība"),
    (_stem("dzīvnieku labturīb"), "Lauksaimniecība"),

    # --- Public health (before drošīb) ---
    (_stem("epidemioloģ"), "Sociālā politika"),

    # --- Defence-adjacent phrases that ARE defence (before transport/env) ---
    (_stem("radiācijas drošīb"), "Aizsardzība un drošība"),
    (_stem("kodoldrošīb"), "Aizsardzība un drošība"),
    (_stem("valsts drošīb"), "Aizsardzība un drošība"),
    (_stem("robežsardz"), "Aizsardzība un drošība"),
    (_stem("šaujamieroč"), "Aizsardzība un drošība"),
    (_stem("ieroču aprit"), "Aizsardzība un drošība"),
    # 2026-06-12 coverage revīzija: zemessardze/valsts robežas/ugunsdrošība/
    # stratēģiskas nozīmes preces = aizsardzība — guard pirms generic fallback.
    (_stem("zemessardz"), "Aizsardzība un drošība"),
    (_stem("valsts robežas likum"), "Aizsardzība un drošība"),
    (_stem("ugunsdroš"), "Aizsardzība un drošība"),
    (_stem("stratēģiskas nozīmes preč"), "Aizsardzība un drošība"),

    # --- Transport (specific before drošīb) ---
    (_stem("satiksmes drošīb"), "Transports"),                   # road safety

    # --- Energy (specific; MUST precede generic `aizsardzīb`/`pārvald`.
    #     "Energoresursu"/"Energoapgādes" lack the `enerģēt` 'ēt' root, so the
    #     existing `enerģēt` stem misses them). 2026-06-12 coverage revīzija. ---
    (_stem("energoresurs"), "Degviela un enerģētika"),
    (_stem("energoapgād"), "Degviela un enerģētika"),

    # --- Social policy (Bērnu tiesīb moved to top — see ordering header) ---
    (_stem("patērētāju aizsardzīb"), "Sociālā politika"),
    (_stem("sociāl apdrošināšan"), "Sociālā politika"),
    (_stem("pensij"), "Sociālā politika"),

    # --- Elections ---
    (_stem("vēlēšan"), "Vēlēšanas"),

    # --- Budget / finance ---
    (_stem("Latvijas Bank"), "Budžets un finanses"),
    (_stem("budžet"), "Budžets un finanses"),
    # 2026-06-12 coverage revīzija: ienākuma/akcīzes nodokļi, kredītiestādes,
    # VID, Uzņēmumu reģistrs = Budžets. `nekustamā īpašuma nodokl` jau noķerts
    # augstāk (Pašvaldības), tāpēc šie nodokļu stem-i ir droši.
    (_stem("ienākuma nodokl"), "Budžets un finanses"),
    (_stem("akcīz"), "Budžets un finanses"),
    (_stem("kredītiestāž"), "Budžets un finanses"),
    (_stem("valsts ieņēmumu dienest"), "Budžets un finanses"),
    (_stem("uzņēmumu reģistr"), "Budžets un finanses"),
    (_stem("nodokļ"), "Budžets un finanses"),
    # `_word("nodokli")` noķer akuzatīva formu, ko `nodokļ` (ar mīksto ļ) izlaiž.
    (_word("nodokli"), "Budžets un finanses"),
    (_stem("finanš"), "Budžets un finanses"),

    # --- Defence / security (fallbacks) ---
    (_stem("aizsardzīb"), "Aizsardzība un drošība"),
    (_stem("drošīb"), "Aizsardzība un drošība"),
    (_word("NATO"), "Aizsardzība un drošība"),

    # --- Ukraine / Russia ---
    (_stem("Ukrain"), "Ukraina un Krievija"),
    (_stem("Krievij"), "Ukraina un Krievija"),
    (_stem("sankcij"), "Ukraina un Krievija"),

    # --- Education ---
    (_stem("profesionāl izglītīb"), "Izglītība"),
    (_stem("izglītīb"), "Izglītība"),
    (_stem("augstskol"), "Izglītība"),

    # --- Energy ---
    (_stem("enerģēt"), "Degviela un enerģētika"),
    (_stem("degviel"), "Degviela un enerģētika"),
    (_stem("elektr"), "Degviela un enerģētika"),
    (_stem("nafta"), "Degviela un enerģētika"),
    (_stem("naftas"), "Degviela un enerģētika"),

    # --- Immigration ---
    (_stem("imigrāc"), "Imigrācija"),
    (_stem("patvērum"), "Imigrācija"),

    # --- Municipalities ---
    (_stem("pašvaldīb"), "Pašvaldības"),

    # --- Drones ---
    (_stem("dron"), "Droni"),

    # --- airBaltic / Rail Baltica ---
    (_stem("airBaltic"), "airBaltic"),
    (_stem("Air Baltic"), "airBaltic"),
    (_stem("Rail Baltica"), "Rail Baltica"),

    # --- Forestry ---
    (_stem("mež"), "Mežsaimniecība"),

    # --- Media ---
    (_stem("medij"), "Sabiedriskie mediji"),

    # --- Language ---
    (_stem("valod"), "Valodu politika"),

    # --- Transport ---
    (_stem("transport"), "Transports"),
    (_stem("ceļ"), "Transports"),
    (_stem("satiksm"), "Transports"),

    # --- Justice (generic stems) ---
    (_stem("tieslietu"), "Tieslietas"),
    (_stem("krimināl"), "Tieslietas"),
    (_stem("korupcij"), "Tieslietas"),
    (_stem("sod"), "Tieslietas"),
    (_stem("maksātnespēj"), "Tieslietas"),

    # --- State administration ---
    (_stem("arhīv"), "Valsts pārvalde"),
    (_stem("Ministru kabinet"), "Valsts pārvalde"),
    (_stem("pārvald"), "Valsts pārvalde"),

    # --- Social policy (fallback) ---
    (_stem("sociāl"), "Sociālā politika"),

    # --- Environment (fallback) ---
    (_stem("vide"), "Vide"),

    # --- Coalitions ---
    (_stem("koalīcij"), "Koalīcija un partijas"),

    # --- EU ---
    (_stem("Eirop"), "ES politika"),
    (_word("ES"), "ES politika"),           # exact word — not a genitive suffix

    # --- Foreign policy ---
    (_stem("ārpolitik"), "Ārpolitika"),

    # --- Iran ---
    (_stem("Irān"), "Irāna"),

    # --- State enterprises ---
    (_stem("kapitālsabiedr"), "Valsts kapitālsabiedrības"),

    # --- Innovation ---
    (_stem("inovācij"), "Inovācijas"),
]


def _motif_to_topic(motif: str) -> str:
    """Map a vote motif to the closest PoliTracker topic group.

    Uses word-boundary regex matching (compiled at module import).
    First match wins; see `_MOTIF_TOPIC_MAP` ordering comment for why
    specific rules must precede generic stems.
    """
    for pattern, topic in _MOTIF_TOPIC_MAP:
        if pattern.search(motif):
            return topic
    # Default: try normalize_topic from topic_map. It returns the input
    # unchanged when nothing matches (passthrough), which would leak the
    # full motif text into the topic column. Validate the result against
    # the canonical TOPIC_GROUPS set and fall back to "Valsts pārvalde"
    # if normalize_topic didn't actually recognize anything.
    try:
        from src.topic_map import normalize_topic, TOPIC_GROUPS
        normalized = normalize_topic(motif)
        if normalized in TOPIC_GROUPS:
            return normalized
    except Exception:
        pass
    return "Valsts pārvalde"  # Safe default for legislative votes


def _vote_salience(motif: str) -> float:
    """Estimate salience of a vote based on the motif.

    Saeima votes on laws are generally 0.7-0.9 salience (major policy).
    Committee referrals are lower (0.5-0.6).
    """
    motif_lower = motif.lower()
    if "nodošana komisijām" in motif_lower or "nodošana komisij" in motif_lower:
        return 0.5  # First reading / committee referral
    if "galīgajā lasījumā" in motif_lower or "trešajā lasījumā" in motif_lower:
        return 0.9  # Final reading
    if "otrajā lasījumā" in motif_lower:
        return 0.8  # Second reading
    if "steidzam" in motif_lower:
        return 0.9  # Urgent procedure
    return 0.7  # Default for legislative votes
