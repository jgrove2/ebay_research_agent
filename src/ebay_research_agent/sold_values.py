import sqlite3
from collections import defaultdict
from pathlib import Path
from statistics import mean, median

from ebay_research_agent.config import get_settings

DEFAULT_SOLD_VALUES_PATH = Path(__file__).parent / "data" / "sold_values.db"

_COLUMNS = ("product", "version", "shortDescription", "totalPrice", "numberOfProducts")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sold_values (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    product          TEXT NOT NULL,
    version          TEXT NOT NULL,
    shortDescription TEXT NOT NULL DEFAULT '',
    totalPrice       REAL NOT NULL,
    numberOfProducts INTEGER NOT NULL DEFAULT 1
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


def sold_records_for(product: str) -> list[dict]:
    settings = get_settings()
    path = _resolve_path(settings.sold_values_path)
    columns = _COLUMNS[1:]
    with _connect(path) as connection:
        rows = connection.execute(
            "SELECT version, shortDescription, totalPrice, numberOfProducts "
            "FROM sold_values WHERE product = ? ORDER BY id",
            (product,),
        ).fetchall()
    return [dict(zip(columns, row)) for row in rows]


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


def _raw_price(record: dict) -> float | None:
    return record.get("totalPrice")


def summarize_raw_sold_values(records: list[dict]) -> dict:
    by_version: dict[str, list[float]] = defaultdict(list)
    by_number: dict[str, list[float]] = defaultdict(list)
    by_version_number: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )

    for record in records:
        raw_price = _raw_price(record)
        if raw_price is None:
            continue
        version = record["version"]
        number = str(record.get("numberOfProducts") or 1)
        by_version[version].append(raw_price)
        by_number[number].append(raw_price)
        by_version_number[version][number].append(raw_price)

    return {
        **_price_stats([r["totalPrice"] for r in records if r.get("totalPrice") is not None]),
        "listingCount": len(records),
        "by_version": {
            code: _price_stats(values) for code, values in sorted(by_version.items())
        },
        "by_number_of_products": {
            number: _price_stats(values) for number, values in sorted(by_number.items())
        },
        "by_version_number_of_products": {
            code: {
                number: _price_stats(values)
                for number, values in sorted(numbers.items())
            }
            for code, numbers in sorted(by_version_number.items())
        },
    }
