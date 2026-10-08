import sqlite3
from collections import defaultdict
from pathlib import Path
from statistics import mean, median

from ebay_research_agent.config import get_settings

DEFAULT_SOLD_VALUES_PATH = Path(__file__).parent / "data" / "sold_values.db"

_COLUMNS = ("console", "console_code", "description", "total_price")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sold_values (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    console      TEXT NOT NULL,
    console_code TEXT NOT NULL,
    description  TEXT NOT NULL DEFAULT '',
    total_price  REAL NOT NULL
);
"""


def _resolve_path(path: str) -> Path:
    resolved = Path(path)
    if resolved.is_absolute():
        return resolved
    if resolved.exists():
        return resolved
    return DEFAULT_SOLD_VALUES_PATH


def _connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute(_SCHEMA)
    connection.commit()
    return connection


def load_sold_values() -> list[dict]:
    settings = get_settings()
    path = _resolve_path(settings.sold_values_path)
    with _connect(path) as connection:
        rows = connection.execute(
            "SELECT console, console_code, description, total_price "
            "FROM sold_values ORDER BY id"
        ).fetchall()
    return [dict(zip(_COLUMNS, row)) for row in rows]


def comps_for(product: str) -> list[dict]:
    return [record for record in load_sold_values() if record["console"] == product]


def sold_records_for(product: str) -> list[dict]:
    settings = get_settings()
    path = _resolve_path(settings.sold_values_path)
    with _connect(path) as connection:
        rows = connection.execute(
            "SELECT console_code, description, total_price "
            "FROM sold_values WHERE console = ? ORDER BY id",
            (product,),
        ).fetchall()
    return [dict(zip(("console_code", "description", "total_price"), row)) for row in rows]


def _price_stats(prices: list[float]) -> dict:
    if not prices:
        return {"count": 0, "average": None, "median": None, "min": None, "max": None}
    return {
        "count": len(prices),
        "average": round(mean(prices), 2),
        "median": round(median(prices), 2),
        "min": round(min(prices), 2),
        "max": round(max(prices), 2),
    }


def summarize_sold_values(records: list[dict]) -> dict:
    prices = [r["total_price"] for r in records if r["total_price"] is not None]

    by_model: dict[str, list[float]] = defaultdict(list)
    for record in records:
        if record["total_price"] is not None:
            by_model[record["console_code"]].append(record["total_price"])

    descriptions: list[str] = []
    seen: set[str] = set()
    for record in records:
        text = (record.get("description") or "").strip()
        if text and text not in seen:
            seen.add(text)
            descriptions.append(text)

    return {
        **_price_stats(prices),
        "by_model": {
            code: _price_stats(values) for code, values in sorted(by_model.items())
        },
        "descriptions": descriptions,
    }
