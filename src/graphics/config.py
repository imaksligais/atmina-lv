"""Graphics package configuration: Gemini API key loading + budget constants."""
import json
from pathlib import Path

COST_PER_IMAGE_USD = 0.039
MONTHLY_BUDGET_USD = 5.00

KEY_PATH = Path(__file__).parent.parent.parent / "data" / "gemini_key.json"


def load_gemini_key() -> dict:
    if not KEY_PATH.exists():
        raise FileNotFoundError(
            f"gemini_key.json not found at {KEY_PATH}. "
            'Create it with {"api_key": "...", "model": "..."}.'
        )
    data = json.loads(KEY_PATH.read_text(encoding="utf-8"))
    if not data.get("api_key", "").strip():
        raise ValueError("gemini_key.json has empty api_key")
    if not data.get("model", "").strip():
        raise ValueError("gemini_key.json has empty model")
    return {"api_key": data["api_key"], "model": data["model"]}


class BudgetExceededError(RuntimeError):
    """Raised when monthly image-generation budget is exceeded."""


def budget_check(db) -> None:
    from src.graphics.storage import monthly_cost_usd
    spent = monthly_cost_usd(db)
    if spent >= MONTHLY_BUDGET_USD:
        raise BudgetExceededError(
            f"Monthly budget {MONTHLY_BUDGET_USD:.2f} USD exceeded (spent: {spent:.2f})."
        )
