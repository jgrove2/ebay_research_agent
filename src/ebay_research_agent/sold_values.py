import json
from functools import lru_cache
from pathlib import Path

from ebay_research_agent.config import get_settings

DEFAULT_SOLD_VALUES_PATH = Path(__file__).parent / "data" / "sold_values.json"


def _resolve_path(path: str) -> Path:
    resolved = Path(path)
    if resolved.is_absolute():
        return resolved
    if resolved.exists():
        return resolved
    return DEFAULT_SOLD_VALUES_PATH


@lru_cache
def load_sold_values() -> list[dict]:
    settings = get_settings()
    path = _resolve_path(settings.sold_values_path)
    with path.open() as handle:
        return json.load(handle)


def comps_for(product: str) -> list[dict]:
    return [record for record in load_sold_values() if record.get("product") == product]
