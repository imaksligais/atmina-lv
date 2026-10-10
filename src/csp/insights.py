"""Algorithmic trend insights — no LLM, pure logic."""
import re


def generate_insight(values: list[tuple[str, float]], direction: str = "neutral") -> str:  # noqa: ARG001 - direction API accepted but not yet implemented; callers pass it
    """Generate a one-line Latvian insight from time-series data.

    Args:
        values: List of (period, value) tuples sorted chronologically
        direction: "higher_is_better", "lower_is_better", or "neutral"

    Returns:
        One-line insight string in Latvian, or "" if insufficient data
    """
    if len(values) < 2:
        return ""

    parts = []

    # Current value and recent change
    latest_period, latest_val = values[-1]
    prev_period, prev_val = values[-2]

    # Streak: how many consecutive periods in same direction
    streak_dir = None  # "up" or "down"
    streak_len = 0
    for i in range(len(values) - 1, 0, -1):
        curr = values[i][1]
        prev = values[i - 1][1]
        if curr > prev:
            d = "up"
        elif curr < prev:
            d = "down"
        else:
            break
        if streak_dir is None:
            streak_dir = d
        if d == streak_dir:
            streak_len += 1
        else:
            break

    if streak_len >= 3:
        verb = "aug" if streak_dir == "up" else "sarūk"
        freq = _freq_label(values[0][0])
        parts.append(f"{verb} {streak_len} {freq} pēc kārtas")

    # Historical context: is this the min or max?
    all_vals = [v for _, v in values]
    if latest_val == min(all_vals) and len(values) >= 5:
        first_year = _extract_year(values[0][0])
        parts.append(f"zemākais kopš {first_year}")
    elif latest_val == max(all_vals) and len(values) >= 5:
        first_year = _extract_year(values[0][0])
        parts.append(f"augstākais kopš {first_year}")

    # Year-over-year if monthly/quarterly data with enough history
    yoy = _yoy_change(values)
    if yoy is not None and not parts:  # Only if no streak/historical insight
        sign = "+" if yoy > 0 else ""
        parts.append(f"{sign}{yoy:.1f}% g/g")

    if not parts:
        # Fallback: simple direction
        if latest_val > prev_val:
            parts.append("pieaug")
        elif latest_val < prev_val:
            parts.append("sarūk")
        else:
            parts.append("nemainās")

    return ". ".join(parts[:2])  # Max 2 insights


def _freq_label(period: str) -> str:
    """Return 'mēn.' or 'cet.' or 'g.' based on period format."""
    if "M" in period:
        return "mēn."
    elif "Q" in period:
        return "cet."
    return "g."


def _extract_year(period: str) -> str:
    """Extract year from period like '2025M01' or '2025Q1' or '2025'."""
    return period[:4]


def _yoy_change(values: list[tuple[str, float]]) -> float | None:
    """Compute year-over-year % change for the latest period."""
    latest_period, latest_val = values[-1]

    if "M" in latest_period:
        # Find same month last year
        match = re.match(r"(\d{4})M(\d{2})", latest_period)
        if not match:
            return None
        target = f"{int(match.group(1)) - 1}M{match.group(2)}"
    elif "Q" in latest_period:
        match = re.match(r"(\d{4})Q(\d)", latest_period)
        if not match:
            return None
        target = f"{int(match.group(1)) - 1}Q{match.group(2)}"
    else:
        target = str(int(latest_period) - 1)

    for period, val in values:
        if period == target and val != 0:
            return ((latest_val - val) / abs(val)) * 100

    return None
