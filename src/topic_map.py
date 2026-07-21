"""
Topic normalization for PoliTracker claims.

Maps ~158 granular topic strings into 32 canonical groups for the position matrix.
DB stores normalized group names; stance text preserves the original detail.
"""

# Canonical group name → list of raw topic strings that belong to it.
# Every raw topic in claims.topic should appear in exactly one group.
TOPIC_GROUPS: dict[str, list[str]] = {
    "Aizsardzība un drošība": [
        "drošība",
        "aizsardzība",
        "aizsardzības ministrija",
        "aizsardzības industrija",
        "aizsardzības finansējums",
        "pretgaisa aizsardzība",
        "civilā aizsardzība",
        "NATO",
        "NATO un reģionālā drošība",
        "Baltijas drošība",
        "ES drošības politika",
        "ES drošība un Ungārija",
        "ES aizsardziibas industrija",
        "drošība un imigrācija",
        "ekonomikas aizsardziba",
        "gaisa telpas drošība",
    ],
    "Ukraina un Krievija": [
        "Ukrainas atbalsts",
        "Ukrainas pamieris",
        "Krievijas ietekme",
        "Krievijas agresija Ukrainā",
        "sankcijas pret Krieviju",
        "ES sankciju politika",
        "ES kultūras sankcijas pret Krieviju",
        "ES kultūras sankcijas",
        "kara noziegumi",
        "komunisma upuri",
        "vēsturiskā atmiņa",
    ],
    "Droni": [
        "dronu incidents",
        "dronu incidenti",
        "dronu aizsardzība",
        "drona krīze",
        "iedzīvotāju apziņošana",
        # 2026-06-10 robežas precizēšana (Droni ↔ Aizsardzība un drošība):
        # tiešie pārtveršanas/pretdronu temati vienmēr → Droni.
        "dronu notriekšana",
        "drona notriekšana",
        "dronu pārtveršana",
        "pretdronu aizsardzība",
        "pretdronu sadarbība",
        "pretdronu spējas",
        "pretdronu sistēmas",
        "FPV droni",
        "dronu operatori",
        "dronu siena",
        "dronu ražošana",
    ],
    "airBaltic": [
        "airBaltic finansējums",
        "AirBaltic",
        "airBaltic valsts finansējums",
        "airBaltic stratēģija",
        "airBaltic aizdevums",
        "airBaltic aizdevuma robežas",
        "airBaltic ZZS bloķēšana",
        "airBaltic Saeimas balsojums",
        "AirBaltic un Rail Baltica",
        "aviācija",
    ],
    "Rail Baltica": [
        "Rail Baltica",
        # Alias: "Rail Baltic" (missing trailing 'a') — an extractor typo
        # 2026-06-01. The diacritic-strip fallback can't coerce it (it differs
        # by a letter, not a diacritic), so map it explicitly.
        "Rail Baltic",
    ],
    "Imigrācija": [
        "imigrācija",
        "Immigracija",
        "migrācija",
        "darbaspēka imigrācija",
        "ES migrācijas pakts",
        "uzturēšanās atļaujas",
    ],
    "Degviela un enerģētika": [
        "degvielas akcīze",
        "degvielas cenas",
        "degvielas tirgus",
        "degvielas solidaritātes maksājums",
        "enerģētika",
        "enerģētika un ģeopolitika",
        "energoneatkarība",
        "energoneatkariiba",
        "lauksaimniecības akcīze",
        "CBAM un lauksaimniecība",
    ],
    "Vēlēšanas": [
        "vēlēšanu drošība",
        "vēlēšanu reforma",
        "vēlēšanu prognozes",
        "vēlēšanas",
        "IT iepirkumi un vēlēšanu drošība",
        "tautas vēlēts prezidents",
    ],
    "Valsts pārvalde": [
        "valsts pārvalde",
        "valsts parvaldes reforma",
        "pārvaldība",
        "valdība",
        "valdibas kvalitate",
        "ministriju darbs",
        "publiskais sektors",
    ],
    "Budžets un finanses": [
        "budžets",
        "valsts budžets",
        "nulles budžets",
        "ES budžets",
        "valsts parāds",
        "PVN samazināšana pārtikai",
        "nodokļu politika",
        "finanšu sektora uzraudzība",
        "nebanku uzraudzība",
        "pārtikas cenas",
        "platformu ekonomika",
        "ekonomika un eksports",
        # Alias: earlier writers (pre-2026-04-16) used these non-canonical
        # labels. Keep them here so normalize_topic() coerces them back.
        "Ekonomika un finanses",
        "Ekonomika",
        # Dismantled 2026-04-17: "Inovācijas" was a drift-bucket for AI/tech
        # mentions. 11 claims redistributed manually; remaining drift → here
        # (most coherent innovation claims were economic policy anyway).
        "inovācijas",
        "Inovācijas",
    ],
    "Mežsaimniecība": [
        "mežsaimniecība",
        "mezsaimnieciba",
        "Meža likums",
        "Meža likuma grozījumi",
        "kokrūpnieku lieta",
        "kokrūpniecība",
    ],
    "Lauksaimniecība": [
        "lauksaimniecība",
        "lauksaimnieciba",
        "zemkopība",
        "lauku attīstība",
        "Lauksaimniecības un lauku attīstības likums",
        "pārtikas ražošana",
        "zemnieku saimniecības",
    ],
    "Sabiedriskie mediji": [
        "sabiedriskie mediji",
        "sabiedrisko mediju reforma",
        "sabiedrisko mediju objektivitāte",
        "krievu valoda medijos",
    ],
    "Koalīcija un partijas": [
        "koalīcija",
        "koalīcijas kritika",
        "partijas disciplīna",
        "Progresīvo kritika",
        "Nacionālās Apvienības kritika",
        "JV kritika",
        "KNAB kritika",
        "PTAC kritika",
        "Latvijas partiju politika",
        "politiskais autentiskums",
        "politiskās pieredzes nozīme",
        "politiska filozofija",
        "uzticības balsojums",
        "MMN vadība",
        "MMN organizācija",
        "MMN ideoloģija",
        "MMN",
    ],
    "Valodu politika": [
        "valodu politika",
    ],
    "Pašvaldības": [
        "pašvaldības",
        "Rīgas infrastruktūra",
        "pierobežas attīstība",
        "reģionālā attīstība",
        "sporta infrastruktūra",
        "infrastruktura",
        "policijas infrastruktūra",
    ],
    # Added 2026-04-25 — urban planning, traffic-calming, neighborhood mobility.
    # Distinct from Pašvaldības (general municipal governance) and Transports
    # (intercity / public transit). Catalysed by Grīziņkalna modal-filter
    # debate and Kotello (PRO, Rīgas domes Satiksmes komitejas vadītāja)
    # tracking from 2026-04-25.
    "Pilsētvide": [
        "pilsētvide",
        "pilsētplānošana",
        "Rīgas pilsētvide",
        "apkaimju attīstība",
        "pilsētas attīstība",
        "gājēju ielas",
        "gājēju drošība",
        "modālie filtri",
        "modālā filtra projekts",
        "tranzītsatiksme apkaimēs",
        "veloceļi",
        "veloinfrastruktūra",
        "mikromobilitāte",
        "autostāvvietas",
    ],
    "Transports": [
        "transports",
        "ceļu satiksmes drošība",
        "ceļu satiksme",
    ],
    "Izglītība": [
        "izglītība",
        "izglītības brīvība",
        "senioru izglītība",
    ],
    "ES politika": [
        "ES tirdzniecība",
        "ES ekonomikas politika",
        "ES reģionālā politika",
        "ārpolitika / ES",
        "Moldovas ES integrācija",
        "Baltijas salīdzinājums",
    ],
    "Ārpolitika": [
        "ārlietas",
        "transatlantiskā sadarbība",
        "transatlantiskā ekonomiskā sadarbība",
        "starptautiskā sadarbība",
        "Latvijas-Polijas sadarbība",
        "ASV aarlietas",
        "Šlesera-Orbāna sadarbība",
        # Merged 2026-04-17: "Irāna" (12 claims) folded back in — Iran is a
        # transient geopolitical event, not a sustained Latvian political lane.
        "ārpolitika — Irāna",
        "arlieta — Iranas karss",
        "Irāna — drošības draudi",
        "Hormuza šaurums",
        "Irāna",
    ],
    "Tieslietas": [
        "Satversmes tiesas loma",
        "tiesnešu pensijas",
        "Stambulas konvencija",
        "bernu tiesibu aizsardziba",
        "sabiedriska kartiba",
        "pretterorisma un AML politika",
    ],
    # Added 2026-04-25 — corruption investigations, KNAB, conflicts of interest,
    # asset declarations. Split out of Tieslietas (judicial system) because
    # corruption claims have a distinct rhetorical register and recurring
    # speakers (commentators, opposition critique).
    "Korupcija un KNAB": [
        "korupcija",
        "sistēmiska korupcija",
        "KNAB",
        "KNAB izmeklēšana",
        "korupcijas izmeklēšana",
        "interešu konflikts",
        "interešu konflikti",
        "amatpersonu deklarācijas",
        "amatpersonu darbības",
    ],
    "Sociālā politika": [
        "ģimenes politika",
        "demogrāfija",
        "dubultpilsonība",
        "pilsonība",
    ],
    # Added 2026-04-25 — healthcare delivery (medics, hospitals, ER, drug
    # pricing). Split from Sociālā politika because recurring topic with
    # own structural dynamics (mediķu trūkums, RAKUS finansējums).
    "Veselības aprūpe": [
        "veselības aprūpe",
        "veselības sistēma",
        "mediķu trūkums",
        "ārstniecības iestādes",
        "RAKUS",
        "neatliekamā palīdzība",
        "rehabilitācija",
        "garīgā veselība",
        "medikamentu cenas",
        "ambulances",
    ],
    "Pensijas": [
        "pensijas",
        "pensiju reforma",
        "pensiju sistēma",
        "2. pensiju līmenis",
        "otrais pensiju līmenis",
        "pensiju 2. līmenis",
        "2PL",
        "pedagogu pensijas",
        "vecuma pensija",
        "pensionāri",
        # Alias: drift label from 2026-04-16 (1 claim) — coerce back.
        "Pensiju reforma",
    ],
    "Vide": [
        "vide",
        "zaļā politika",
        "dzīvnieku tiesību aktīvisms",
    ],
    # Added 2026-04-25 — climate-specific policy (CO2, ETS, climate neutrality
    # 2050, EV adoption framing as climate). Split from Vide (waste/nature)
    # and Degviela un enerģētika (fuel-tax/energy-mix) because climate has
    # its own narrative axis and EU regulatory dimension.
    "Klimats": [
        "klimats",
        "klimatneitralitāte",
        "klimata politika",
        "CO2 nodoklis",
        "ETS",
        "emisiju tirgus",
        "oglekļa neitrālā ekonomika",
        "klimata mērķi",
    ],
    # Added 2026-04-25 — state IT, digital governance, e-services, election IT
    # delivery, cybersecurity. Was distributed across Valsts pārvalde
    # (VRAA krīze), Vēlēšanas (vēlēšanu IT), and Sabiedriskie mediji
    # (digitālā plaisa). Surfaced as own bucket after VARAM/RIX 24.04.
    # incident + EIS iepirkumu publiskošana.
    "Digitālā politika": [
        "digitālā politika",
        "valsts IT",
        "EIS iepirkumi",
        "VRAA",
        "kiberdrošība",
        "e-pārvalde",
        "valsts digitālā transformācija",
        "valsts informācijas sistēmas",
    ],
    "Valsts kapitālsabiedrības": [
        "valsts kapitālsabiedrības",
    ],
    "Kultūra": [
        "kultūra",
        "kultūras politika",
        "kultūras ministrija",
        "JRT",
        "teātris",
        "opera",
        "muzeji",
    ],
    # 2026-07-04 — 32. kanoniskā tēma. Sporta likums + sporta politika
    # atkārtoti spiedās Kultūrā/Izglītībā ar NEEDS_REVIEW (06-18 ×2,
    # 07-02/04 programmas, 07-04 triāžas eskalācijas ×2) — operatora lēmums
    # izdalīt atsevišķi. NB: "sporta infrastruktūra" paliek Pašvaldībās
    # (apzināti — infrastruktūras objekti ir pašvaldību kompetence).
    "Sports": [
        "sports",
        "sporta politika",
        "Sporta likums",
        "sporta likums",
        "tautas sports",
        "augstu sasniegumu sports",
        "bērnu un jauniešu sports",
        "sporta finansēšana",
    ],
}

# Latvian diacritics stripping for fuzzy matching
_STRIP_DIACRITICS = str.maketrans("āčēģīķļņōŗšūž", "acegiklnorsuz")

# Reverse lookup: raw topic → group name (built once at import time)
_TOPIC_TO_GROUP: dict[str, str] = {}
for _group, _topics in TOPIC_GROUPS.items():
    for _topic in _topics:
        if _topic in _TOPIC_TO_GROUP:
            raise ValueError(
                f"Duplicate topic mapping: '{_topic}' is in both "
                f"'{_TOPIC_TO_GROUP[_topic]}' and '{_group}'"
            )
        _TOPIC_TO_GROUP[_topic] = _group


_SAEIMA_KEYWORD_MAP: list[tuple[list[str], str]] = [
    # IMPORTANT: pensij* MUST come before nodokļ/budžet/sociāl/ārstniecīb —
    # pension bills routinely mention taxes, budget, and health; keyword
    # precedence is first-match, so Pensijas must win.
    (["pensij", "2. pensiju", "2pl", "pedagogu pensij"], "Pensijas"),
    # 2026-04-25 — climate keywords now route to Klimats (was Vide). General
    # vide/atkritumi remain in Vide.
    (["klimat", "co2", "ets", "klimatneitral", "oglekļa neitr"], "Klimats"),
    (["atkritum", "vide", "dabas"], "Vide"),
    # 2026-04-25 — KNAB / corruption keywords precede tieslietas (judicial
    # procedure) because corruption has a distinct narrative axis.
    (["knab", "korupcij", "interešu konflikt", "amatpersonu dekl"], "Korupcija un KNAB"),
    # 2026-04-25 — urban-planning / traffic-calming keywords precede generic
    # transports/satiksm — modal filters, neighborhood mobility, gājēju ielas
    # are urban policy, not intercity transport.
    (["modāl", "tranzītsatiks", "veloceļ", "veloinfra", "mikromobilitāt",
      "pilsētvid", "pilsētplāno", "apkaim", "gājēju ielas", "gājēju droš",
      "autostāvviet"], "Pilsētvide"),
    (["būvniecīb", "nekustam", "dzīvokl"], "Pašvaldības"),
    (["konsulār", "diplomāt", "ārlietu"], "Ārpolitika"),
    (["lauksaimniecīb", "lauku attīstīb", "zemkopīb"], "Lauksaimniecība"),
    (["kapsēt", "apbedī"], "Pašvaldības"),
    (["tiesnes", "tiesu", "prokuror", "prokurat"], "Tieslietas"),
    # 2026-04-25 — medicine keywords now route to Veselības aprūpe (was
    # Sociālā politika). Sociālā politika retains family/demographics/
    # citizenship; healthcare delivery now has its own bucket.
    (["ārstniecīb", "veselīb", "farmācij", "medicīn", "rakus", "ambulanc",
      "neatliekam", "mediķ", "ārst"], "Veselības aprūpe"),
    (["izglītīb", "augstskol", "zinātņ"], "Izglītība"),
    (["budžet", "nodokļ", "finanš"], "Budžets un finanses"),
    (["aizsardzīb", "militār", "nacionāl", "bruņot"], "Aizsardzība un drošība"),
    # 2026-04-25 — digital governance keywords precede generic enerģētik to
    # catch VRAA/EIS/digitālā politika before they fall through.
    (["vraa", "eis iepirkum", "digitālā politik", "kiberdroš",
      "e-pārvald", "valsts informācijas"], "Digitālā politika"),
    (["enerģētik", "elektr", "degviel"], "Degviela un enerģētika"),
    (["transport", "ceļu", "dzelzceļ", "satiksm"], "Transports"),
    (["imigrāc", "patvērum", "migrāc"], "Imigrācija"),
    (["mež", "kokmateri"], "Mežsaimniecība"),
    (["vēlēšan"], "Vēlēšanas"),
    (["valod"], "Valodu politika"),
    # 2026-07-04 — Sports. Apzināti daudzvārdu atslēgas, NE kails "sport":
    # tas ir substring vārdos "transporta" un "eksporta" un aizvestu svešus
    # likumprojektus uz Sports.
    (["sporta likum", "tautas sport", "sporta politik",
      "augstu sasniegumu sport", "sporta federāc"], "Sports"),
    (["sabiedrisk", "medij"], "Sabiedriskie mediji"),
]


def normalize_topic(raw_topic: str) -> str:
    """Return the canonical group name for a raw topic string.

    If the topic is already a group name, returns it as-is.
    If the topic is not mapped, tries keyword-based matching for
    Saeima legislative items (bill titles, procedure motions).
    If still not matched, returns it unchanged (passthrough).
    """
    # Direct match in reverse lookup
    if raw_topic in _TOPIC_TO_GROUP:
        return _TOPIC_TO_GROUP[raw_topic]
    # Already a group name
    if raw_topic in TOPIC_GROUPS:
        return raw_topic
    # Try matching without diacritics (LLM agents sometimes omit them under
    # context drift — see 2026-04-16 incident). Two-tier check:
    #   1) Whole group name: catches when agent emits "Aizsardziba un drosiba"
    #      instead of "Aizsardzība un drošība".
    #   2) Raw subtopic: catches when agent emits a stripped version of a
    #      subtopic, e.g. "Koalicija" → matches subtopic "koalīcija" in the
    #      "Koalīcija un partijas" group.
    raw_lower = raw_topic.lower()
    raw_stripped = raw_lower.translate(_STRIP_DIACRITICS)
    for group_name in TOPIC_GROUPS:
        if group_name.lower().translate(_STRIP_DIACRITICS) == raw_stripped:
            return group_name
    for raw_subtopic, group in _TOPIC_TO_GROUP.items():
        if raw_subtopic.lower().translate(_STRIP_DIACRITICS) == raw_stripped:
            return group
    # Keyword-based matching for Saeima bill titles and legislative items
    lower = raw_topic.lower()
    for keywords, group in _SAEIMA_KEYWORD_MAP:
        if any(kw in lower for kw in keywords):
            return group
    # Saeima procedural motions that don't map to a policy topic
    if any(proc in lower for proc in [
        "caurlūkošan", "lasījum", "iesniegšanas termiņ",
        "priekšlikum", "balsošan", "balsojum",
    ]):
        return "Valsts pārvalde"
    # Unknown topic — passthrough
    return raw_topic


def get_group_topics(group_name: str) -> list[str]:
    """Return all raw sub-topics belonging to a group."""
    return TOPIC_GROUPS.get(group_name, [])


def get_all_group_names() -> list[str]:
    """Return all canonical group names, sorted alphabetically."""
    return sorted(TOPIC_GROUPS.keys())
