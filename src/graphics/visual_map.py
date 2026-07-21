"""
Visual metaphor mapping for the 32 canonical political topics.

Maps each topic to an abstract visual metaphor, mood descriptor, and accent color.
These are used to guide nanobanana image generation prompts.

Metaphors are abstract/symbolic (no people, flags, party logos, photorealism).
Moods describe the emotional tenor. Accent colors are simple descriptive names.

Keys in VISUAL_MAP must stay in sync with src.topic_map.get_all_group_names().
This is enforced by test_visual_map.test_visual_map_covers_all_canonical_topics.
"""

# Fallback visual for unknown topics
_DEFAULT = {
    "metaphor": "abstract geometric pattern with shifting planes",
    "mood": "neutral, analytical",
    "accent": "slate gray",
}

# Canonical mapping: topic name → visual properties
VISUAL_MAP: dict[str, dict[str, str]] = {
    "Aizsardzība un drošība": {
        "metaphor": "shield with concentric ripples, fortress outline",
        "mood": "vigilant, protective",
        "accent": "deep navy",
    },
    "Budžets un finanses": {
        "metaphor": "ascending bar chart with anomalous dip, ledger grid",
        "mood": "analytical, scrutiny",
        "accent": "forest green",
    },
    "Degviela un enerģētika": {
        "metaphor": "branching power lines, molecular bonds radiating outward",
        "mood": "dynamic, flowing",
        "accent": "amber",
    },
    "Droni": {
        "metaphor": "quadcopter silhouette, geometric drone trajectory grid",
        "mood": "technological, aerial",
        "accent": "charcoal",
    },
    "ES politika": {
        "metaphor": "interlocking hexagons, network node constellation",
        "mood": "collaborative, interconnected",
        "accent": "cornflower blue",
    },
    "Imigrācija": {
        "metaphor": "abstract flow lines converging, compass rose paths",
        "mood": "movement, convergence",
        "accent": "rust orange",
    },
    "Izglītība": {
        "metaphor": "ascending spiral, light bulb silhouette with radiating rays",
        "mood": "illumination, growth",
        "accent": "golden yellow",
    },
    "Koalīcija un partijas": {
        "metaphor": "overlapping circles (Venn), interlocking puzzle pieces",
        "mood": "strategic alignment, tension",
        "accent": "deep red",
    },
    "Kultūra": {
        "metaphor": "abstract brushstroke curves, mask and musical note silhouettes",
        "mood": "creative, reflective",
        "accent": "plum purple",
    },
    "Sports": {
        "metaphor": "stylized running track curves, laurel wreath silhouette",
        "mood": "energetic, striving",
        "accent": "medal bronze",
    },
    "Lauksaimniecība": {
        "metaphor": "stylized grain stalks, concentric field pattern",
        "mood": "rooted, cyclical",
        "accent": "ochre",
    },
    "Mežsaimniecība": {
        "metaphor": "coniferous tree outline, growth rings and timber grain",
        "mood": "resilience, sustainability",
        "accent": "forest green",
    },
    "Pašvaldības": {
        "metaphor": "building silhouettes in grid, city block intersection",
        "mood": "local, structural",
        "accent": "brick red",
    },
    "Pensijas": {
        "metaphor": "descending/ascending curve, hourglass with weighted base",
        "mood": "time-bound, security",
        "accent": "teal",
    },
    "Rail Baltica": {
        "metaphor": "parallel railroad tracks, railway crossing symbol",
        "mood": "connection, infrastructure",
        "accent": "steel gray",
    },
    "Sabiedriskie mediji": {
        "metaphor": "broadcast waves radiating, interconnected nodes forming a tree",
        "mood": "amplification, reach",
        "accent": "sky blue",
    },
    "Sociālā politika": {
        "metaphor": "interconnected silhouettes, concentric circles of care",
        "mood": "inclusive, supportive",
        "accent": "soft pink",
    },
    "Tieslietas": {
        "metaphor": "scales in balance, gavel outline, legal text blocks",
        "mood": "justice, deliberation",
        "accent": "midnight blue",
    },
    "Transports": {
        "metaphor": "road converging lines, abstract lane markings with roundabout",
        "mood": "motion, convergence",
        "accent": "dark teal",
    },
    "Ukraina un Krievija": {
        "metaphor": "two abstract landmasses with barrier line, fault line pattern",
        "mood": "tension, conflict",
        "accent": "crimson",
    },
    "Valodu politika": {
        "metaphor": "interlocking letterforms, speech bubble silhouettes",
        "mood": "linguistic, symbolic",
        "accent": "violet",
    },
    "Valsts kapitālsabiedrības": {
        "metaphor": "institutional building silhouette, stock ticker segments",
        "mood": "authority, ownership",
        "accent": "bronze",
    },
    "Valsts pārvalde": {
        "metaphor": "government building columns, hierarchical org-chart outline",
        "mood": "formal, hierarchical",
        "accent": "dark slate",
    },
    "Vide": {
        "metaphor": "leaf vein network, Earth with environmental overlay",
        "mood": "organic, regenerative",
        "accent": "emerald green",
    },
    "Vēlēšanas": {
        "metaphor": "ballot box with radiating decision nodes, pie chart segments",
        "mood": "democratic, choice",
        "accent": "voting blue",
    },
    "airBaltic": {
        "metaphor": "aircraft silhouette, abstract tail fin and flight trajectory arc",
        "mood": "aeronautical, ascent",
        "accent": "aviation white",
    },
    "Ārpolitika": {
        "metaphor": "globe with arrow flows, diplomatic bridge outline",
        "mood": "international, diplomatic",
        "accent": "sage green",
    },
    # 2026-04-25 — 5 new canonical topics added with topic_map expansion
    "Klimats": {
        "metaphor": "stylized cloud formation with temperature gradient bars, melting iceberg silhouette",
        "mood": "urgent, atmospheric",
        "accent": "sky blue",
    },
    "Veselības aprūpe": {
        "metaphor": "stylized caduceus, heartbeat line crossing a stethoscope outline",
        "mood": "caring, clinical",
        "accent": "medical teal",
    },
    "Pilsētvide": {
        "metaphor": "abstract cityscape grid with parks, intersecting street layout from above",
        "mood": "structured, communal",
        "accent": "slate gray",
    },
    "Korupcija un KNAB": {
        "metaphor": "magnifying glass over a contract, balance scale tilting toward shadow",
        "mood": "investigative, weighty",
        "accent": "deep purple",
    },
    "Digitālā politika": {
        "metaphor": "circuit-board path with binary fragments, abstract data flow nodes",
        "mood": "technological, networked",
        "accent": "cyan",
    },
}


def get_visual(topic: str) -> dict[str, str]:
    """
    Retrieve the visual properties for a given political topic.

    Args:
        topic: A canonical topic name (from src.topic_map.get_all_group_names()).

    Returns:
        A dict with keys: metaphor, mood, accent.
        If the topic is not found, returns _DEFAULT.
    """
    return VISUAL_MAP.get(topic, _DEFAULT)
