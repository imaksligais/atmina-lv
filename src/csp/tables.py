"""Configuration for 10 CSP statistical tables."""

TABLES: dict[str, dict] = {
    "NVA011m": {
        "path": "EMP/NBBA/NVA/NVA011m",
        "label": "Reģistrētais bezdarba līmenis",
        "domain": "social",
        "freq": "M",
        "unit": "%",
        "history_years": 25,
        "query": [
            {"code": "ContentsCode", "selection": {"filter": "item", "values": ["NVA011m"]}},
        ],
        "value_indicator": "EliminatedValue",
        # CSP restructured this table in 2024 — current only has 2024+.
        # Archive holds 2008-2023 under a different path/content code.
        "archive": {
            "path": "EMP/NBBA/A_NBBA/NVA010m",
            "query": [
                {"code": "ContentsCode", "selection": {"filter": "item", "values": ["NVA010m"]}},
            ],
        },
        "topics": ["Darbs un nodarbinātība"],
        "keywords": ["bezdarbs", "darbs", "nodarbinātība", "bezdarbnieki", "darba tirgus"],
        "trend_direction": "lower_is_better",
        "format_value": lambda v: f"{v:.1f}%",
        "format_short": lambda v: f"{v:.1f}%",
    },
    "PCI021m": {
        "path": "VEK/PC/PCI/PCI021m",
        "label": "Patēriņa cenu indekss (inflācija)",
        "domain": "prices",
        "freq": "M",
        "unit": "%",
        "history_years": 25,
        "query": [
            {"code": "ContentsCode", "selection": {"filter": "item", "values": ["PCI021m6"]}},
        ],
        "value_indicator": "EliminatedValue",
        "topics": ["Degviela un enerģētika", "Budžets un finanses"],
        "keywords": ["inflācija", "cenas", "dārdzība", "patēriņš", "pārtikas cenas"],
        "trend_direction": "lower_is_better",
        "format_value": lambda v: f"{v:+.1f}%",
        "format_short": lambda v: f"{v:+.1f}%",
    },
    "DSV010m": {
        "path": "EMP/DS/DSV/DSV010m",
        "label": "Vidējā bruto alga",
        "domain": "economy",
        "freq": "M",
        "unit": "EUR",
        "history_years": 25,
        "query": [
            {"code": "GRS_NET", "selection": {"filter": "item", "values": ["GRS"]}},
            {"code": "ContentsCode", "selection": {"filter": "item", "values": ["DSV010m"]}},
        ],
        "value_indicator": "EliminatedValue",
        "topics": ["Darbs un nodarbinātība"],
        "keywords": ["alga", "algas", "atalgojums", "samaksa", "darba alga"],
        "trend_direction": "higher_is_better",
        "format_value": lambda v: f"€{v:,.0f}",
        "format_short": lambda v: f"€{v:,.0f}",
    },
    "IRS010m": {
        "path": "POP/IR/IRS/IRS010m",
        "label": "Iedzīvotāju skaits",
        "domain": "state",
        "freq": "M",
        "unit": "tūkst.",
        "history_years": 20,
        "query": [
            {"code": "ContentsCode", "selection": {"filter": "item", "values": ["IRS010m"]}},
        ],
        "value_indicator": "EliminatedValue",
        "topics": ["Demogrāfija"],
        "keywords": ["iedzīvotāji", "demogrāfija", "populācija", "iedzīvotāju skaits"],
        "trend_direction": "higher_is_better",
        "format_value": lambda v: f"{v/1_000:.2f}M",
        "format_short": lambda v: f"{v/1_000:.2f}M",
    },
    "NNI030": {
        "path": "POP/NN/NNI/NNI030",
        "label": "Džini koeficients",
        "domain": "social",
        "freq": "A",
        "unit": "%",
        "history_years": 25,
        "query": [
            {"code": "ContentsCode", "selection": {"filter": "item", "values": ["NNI030"]}},
        ],
        "value_indicator": "EliminatedValue",
        "topics": ["Sociālā politika"],
        "keywords": ["nevienlīdzība", "džini", "nabadzība", "ienākumu nevienlīdzība"],
        "trend_direction": "lower_is_better",
        "format_value": lambda v: f"{v:.1f}%",
        "format_short": lambda v: f"{v:.1f}%",
    },
    "IKP010": {
        "path": "VEK/IK/IKP/IKP010",
        "label": "IKP kopā un uz vienu iedzīvotāju",
        "domain": "economy",
        "freq": "A",
        "unit": "tūkst. EUR",
        "history_years": 30,
        "query": [
            {"code": "PRICES", "selection": {"filter": "item", "values": ["CP"]}},
            {"code": "ContentsCode", "selection": {"filter": "item", "values": ["IKP010"]}},
        ],
        "value_indicator": "EliminatedValue",
        "topics": ["Budžets un finanses"],
        "keywords": ["IKP", "ekonomika", "iekšzemes kopprodukts", "ekonomiskā izaugsme"],
        "trend_direction": "higher_is_better",
        "format_value": lambda v: f"€{v/1_000_000:.1f}B",
        "format_short": lambda v: f"€{v/1_000_000:.1f}B",
    },
    "ISP010c": {
        "path": "VEK/IS/ISP/ISP010c",
        "label": "IKP ceturksnī",
        "domain": "economy",
        "freq": "Q",
        "unit": "tūkst. EUR",
        "history_years": 30,
        "query": [
            {"code": "PRICES", "selection": {"filter": "item", "values": ["CP"]}},
            {"code": "SESON", "selection": {"filter": "item", "values": ["NSA"]}},
            {"code": "ContentsCode", "selection": {"filter": "item", "values": ["ISP010c"]}},
        ],
        "value_indicator": "EliminatedValue",
        "topics": ["Budžets un finanses"],
        "keywords": ["IKP", "ceturksnis", "ekonomiskā izaugsme"],
        "trend_direction": "higher_is_better",
        "format_value": lambda v: f"€{v/1_000_000:.1f}B",
        "format_short": lambda v: f"€{v/1_000_000:.1f}B",
    },
    "VFV050": {
        "path": "VEK/VF/VFV/VFV050",
        "label": "Valsts parāds",
        "domain": "state",
        "freq": "A",
        "unit": "mln EUR",
        "history_years": 30,
        "query": [
            {"code": "INDICATOR", "selection": {"filter": "item", "values": ["TOTAL"]}},
            {"code": "SECTOR", "selection": {"filter": "item", "values": ["S13"]}},
            {"code": "ContentsCode", "selection": {"filter": "item", "values": ["VFV050"]}},
        ],
        "value_indicator": "EliminatedValue",
        "topics": ["Budžets un finanses"],
        "keywords": ["parāds", "valsts parāds", "budžets", "deficīts", "aizņēmumi"],
        "trend_direction": "neutral",
        "format_value": lambda v: f"€{v:,.0f}M",
        "format_short": lambda v: f"€{v/1_000:.1f}B",
    },
    "KRE020m": {
        "path": "VEK/KR/KRE/KRE020m",
        "label": "Uzņēmēju konfidence",
        "domain": "economy",
        "freq": "M",
        "unit": "bilance %",
        "history_years": 20,
        "query": [
            {"code": "VAL", "selection": {"filter": "item", "values": ["NSA"]}},
            {"code": "INDICATOR", "selection": {"filter": "item", "values": ["CI_IND"]}},
            {"code": "ContentsCode", "selection": {"filter": "item", "values": ["KRE020m"]}},
        ],
        "value_indicator": "EliminatedValue",
        "topics": ["Uzņēmējdarbība"],
        "keywords": ["uzņēmēji", "konfidence", "bizness", "uzņēmējdarbība", "ekonomiskais sentiments"],
        "trend_direction": "higher_is_better",
        "format_value": lambda v: f"{v:+.1f}",
        "format_short": lambda v: f"{v:+.1f}",
    },
    "IBE010": {
        "path": "POP/IB/IBE/IBE010",
        "label": "Starptautiskā ilgtermiņa migrācija",
        "domain": "social",
        "freq": "A",
        "unit": "skaits",
        "history_years": 25,
        "query": [
            {"code": "INDICATOR", "selection": {"filter": "item", "values": ["MIGR_NET"]}},
            {"code": "COUNTRY_GROUP", "selection": {"filter": "item", "values": ["TOTAL"]}},
            {"code": "ContentsCode", "selection": {"filter": "item", "values": ["IBE010"]}},
        ],
        "value_indicator": "EliminatedValue",
        "topics": ["Demogrāfija"],
        "keywords": ["migrācija", "emigrācija", "imigrācija", "izceļošana"],
        "trend_direction": "higher_is_better",
        "format_value": lambda v: f"{v:+,.0f}",
        "format_short": lambda v: f"{v:+,.0f}",
    },
}

# Periods per year by frequency — used to convert history_years to API "top N"
FREQ_PERIODS_PER_YEAR = {"M": 12, "Q": 4, "A": 1}

# Domain color scheme
DOMAIN_COLORS = {
    "economy": {"primary": "#3b82f6", "bg": "rgba(59,130,246,0.1)"},
    "social": {"primary": "#a855f7", "bg": "rgba(168,85,247,0.1)"},
    "prices": {"primary": "#f59e0b", "bg": "rgba(245,158,11,0.1)"},
    "state": {"primary": "#10b981", "bg": "rgba(16,185,129,0.1)"},
}

# Display order on dashboard
DASHBOARD_ORDER = [
    "NVA011m",   # Bezdarbs
    "PCI021m",   # Inflācija
    "DSV010m",   # Algas
    "IRS010m",   # Iedzīvotāji
    "IKP010",    # IKP gada
    "VFV050",    # Valsts parāds
    "NNI030",    # Džini
    "KRE020m",   # Konfidence
    "IBE010",    # Migrācija
    "ISP010c",   # IKP ceturksnis
]
