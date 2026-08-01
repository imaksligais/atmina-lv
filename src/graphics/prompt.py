"""
Nanobanana image-generation prompt composer.

Constructs full, detailed prompts for nanobanana image generation by combining:
- A selected style variant (editorial, scandi, constructivist)
- Topic-specific visual metaphors and moods (from visual_map)
- Headline text with explicit diacritic preservation instruction
- Optional key figure/stat line
- Negative constraints (no people, flags, logos, etc.)

After Phase 1 image matrix review, DEFAULT_STYLE will be frozen to a single variant.
"""

# Three style variants for Phase 1 testing
STYLE_VARIANTS: dict[str, str] = {
    "editorial": (
        "Editorial poster style. Textured cream/beige paper background with aged document feel. "
        "Monochrome black condensed serif display typography (Economist/political-poster style). "
        "One accent color per composition. Rule-of-thirds composition with generous negative space. "
        "16:9 aspect ratio. Mood: restrained, analytical, serious."
    ),
    "scandi": (
        "Nordic minimalist editorial aesthetic. Off-white / bone-colored background. "
        "Thin geometric line work with subtle asymmetry and ample negative space. "
        "Inter- or Söhne-style sans-serif typography. One muted accent color. "
        "16:9 aspect ratio. Mood: calm, measured, Scandinavian civic seriousness."
    ),
    "constructivist": (
        "Modernized constructivist / Bauhaus political poster. Two contrasting colors per composition "
        "(e.g. deep navy + ochre, or charcoal + deep red). Bold geometric blocks with diagonal composition, "
        "slab-serif or display sans-serif typography. High contrast, strong visual hierarchy. "
        "16:9 aspect ratio. Mood: declarative, purposeful, visually commanding."
    ),
    "weekly": (
        "Editorial weekly-digest poster. Textured cream/beige paper background. "
        "Monochrome black condensed serif display typography. A thin ink-navy "
        "frame border runs just inside the edges, with a small ink-navy corner "
        "wordmark block (no text inside it). Ink-navy is the single accent color. "
        "Rule-of-thirds composition, generous negative space. 16:9 aspect ratio. "
        "Mood: reflective, summarizing, analytical."
    ),
}

# Default style for prompt generation (frozen after Phase 1 testing)
DEFAULT_STYLE: str = "editorial"

# Canonical sepia style for @atmina_lv TWEET / THREAD illustrations — a single
# source of truth so the per-day thread scripts stop drifting into divergent
# sepia formulas. Distinct from STYLE_VARIANTS (those are the brief poster, WITH
# a rendered headline); tweet/thread images are always text-free, metaphor-only.
# House-style rationale + the manual thread recipe this serves live in
# wiki/operations/social-agent.md § "Manuālais dienas-pārskata pavediens".
SEPIA_STYLE: str = (
    "Aged archival editorial illustration, muted sepia tones with subtle "
    "slate-blue accents, fine cross-hatching and engraving texture, printed on "
    "textured aged paper, 16:9 composition, no text, no lettering, no numbers, "
    "no words, no captions, no logos."
)

# Kopš 2026-08-19 (operatora lēmums) sepia ir arī brief attēla izvēle:
# `cli brief --style sepia` VIENMĒR jāpāro ar --no-text — stils pats aizliedz
# tekstu, tāpēc headline/stat renderēšana tajā ir pretrunīga.
STYLE_VARIANTS["sepia"] = SEPIA_STYLE

# Negative constraints: what NOT to include in the image
NEGATIVE_CONSTRAINTS: str = (
    "Do NOT include: people, faces, hands, party logos, photorealistic elements, "
    "cartoon style, decorative borders, watermarks, national flags, political party "
    "symbols, or any recognizable real-world individuals. "
    "STRICT TEXT RULE: render ONLY the provided headline text (and the provided stat "
    "if one is given). Do NOT invent, add, or render ANY other text — no subtitles, "
    "no captions, no labels on graphic elements, no percentages, no figures, no "
    "dates, no party abbreviations. If no stat is provided, no numerical value "
    "should appear anywhere in the image."
)


# Text-free variant of NEGATIVE_CONSTRAINTS for `build_prompt(no_text=True)`.
# Kept as a SEPARATE constant rather than a parameterization of
# NEGATIVE_CONSTRAINTS because that name is imported verbatim by
# scripts/regen_172_v2.py and scripts/twitter_pack_designer.py — changing its
# contents would silently alter those posters too.
TEXT_FREE_CONSTRAINTS: str = (
    "Do NOT include: people, faces, hands, party logos, photorealistic elements, "
    "cartoon style, decorative borders, watermarks, national flags, political party "
    "symbols, or any recognizable real-world individuals. "
    "STRICT TEXT RULE: this image must contain NO text whatsoever — no headline, no "
    "title, no subtitle, no caption, no labels on graphic elements, no letters, no "
    "words, no numbers, no percentages, no dates, no party abbreviations, no "
    "signatures, no watermark lettering. The composition must carry its meaning "
    "through imagery alone. Ignore any typography instruction in the style "
    "description above — this composition has no typographic element."
)


def build_prompt(
    visual_brief: dict,
    visual_map_entry: dict,
    style_key: str = DEFAULT_STYLE,
    no_text: bool = False,
) -> str:
    """
    Compose a full nanobanana image-generation prompt.

    Args:
        visual_brief: Dict with keys:
            - topic: str (canonical political topic name)
            - headline: str (the claim/assertion to display)
            - stat: str | None (optional key figure to emphasize)
            - metaphor_hint: str (optional hint to guide metaphor selection)
        visual_map_entry: Dict returned by visual_map.get_visual() with keys:
            - metaphor: str (abstract visual metaphor, may include "OR" alternatives)
            - mood: str (emotional tenor)
            - accent: str (accent color name)
        style_key: str (style variant key: "editorial", "scandi", or "constructivist")
        no_text: bool — when True, render a text-free poster: the headline and
            stat blocks are omitted entirely and TEXT_FREE_CONSTRAINTS replaces
            NEGATIVE_CONSTRAINTS. `visual_brief["headline"]` is still required
            (it is the editorial anchor the metaphor must express), it is simply
            not handed to the model as text to draw.

    Returns:
        A complete prompt string for nanobanana image generation.

    Raises:
        KeyError: If style_key not in STYLE_VARIANTS.
    """
    # Validate style_key (natural KeyError if not found)
    style_description = STYLE_VARIANTS[style_key]

    # Extract visual properties
    metaphor = visual_map_entry["metaphor"]
    mood = visual_map_entry["mood"]
    accent = visual_map_entry["accent"]
    # Weekly style is monochrome ink-navy by design — override the per-topic
    # accent so the model does not get two conflicting accent colors (the
    # per-topic "deep red" fights the "ink-navy single accent" style text and
    # produced red-dominant weekly images).
    if style_key == "weekly":
        accent = "ink navy (deep blue)"
    topic = visual_brief["topic"]
    headline = visual_brief["headline"]
    stat = visual_brief.get("stat")

    # Build the prompt by concatenating sections
    prompt_sections = [
        # 1. Style variant description
        style_description,
        "",  # blank line
        # 2. Topic and visual guidance
        f"Topic: {topic}",
        f"Visual Metaphor: {metaphor}",
        f"Emotional Mood: {mood}",
        f"Accent Color: {accent}",
        "",  # blank line
    ]

    # 3. Headline block with diacritic preservation instruction.
    # Skipped for no_text posters — handing the model a headline while also
    # forbidding text produces the exact conflict that makes it render the
    # words anyway.
    if not no_text:
        prompt_sections.append(
            f'Headline text (render exactly as shown, preserve Latvian diacritics): "{headline}"'
        )
        prompt_sections.append("")  # blank line

        # 4. Optional stat line — skip for None, empty, or "-" sentinel.
        # brief-writer emits "-" when no meaningful unit-bearing number is available.
        if stat and stat != "-":
            prompt_sections.append(f"Key figure to display prominently: {stat}")
            prompt_sections.append("")  # blank line

    # 5. Negative constraints
    prompt_sections.append(TEXT_FREE_CONSTRAINTS if no_text else NEGATIVE_CONSTRAINTS)

    return "\n".join(prompt_sections)
