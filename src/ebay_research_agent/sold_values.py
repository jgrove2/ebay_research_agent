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


def _per_console_price(record: dict) -> float | None:
    raw_price = record.get("totalPrice")
    if raw_price is None:
        return None
    number = record.get("numberOfProducts") or 1
    try:
        number = int(number)
    except (TypeError, ValueError):
        number = 1
    return raw_price / max(number, 1)


def summarize_raw_sold_values(records: list[dict]) -> dict:
    by_version: dict[str, list[float]] = defaultdict(list)
    by_version_number: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )

    for record in records:
        per_console = _per_console_price(record)
        if per_console is None:
            continue
        version = record["version"]
        number = str(record.get("numberOfProducts") or 1)
        by_version[version].append(per_console)
        by_version_number[version][number].append(per_console)

    return {
        **_price_stats(
            [
                _per_console_price(r)
                for r in records
                if _per_console_price(r) is not None
            ]
        ),
        "listingCount": len(records),
        "by_version": {
            code: _price_stats(values) for code, values in sorted(by_version.items())
        },
        "by_version_number_of_products": {
            code: {
                number: _price_stats(values)
                for number, values in sorted(numbers.items())
            }
            for code, numbers in sorted(by_version_number.items())
        },
    }
