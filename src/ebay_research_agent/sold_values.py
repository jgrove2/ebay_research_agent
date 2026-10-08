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

_OLD_COLUMNS = ("console", "console_code", "description", "total_price")


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
            "SELECT product, version, shortDescription, totalPrice, numberOfProducts "
            "FROM sold_values ORDER BY id"
        ).fetchall()
    return [dict(zip(_COLUMNS, row)) for row in rows]


def comps_for(product: str) -> list[dict]:
    return [record for record in load_sold_values() if record["product"] == product]


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


def _unit_price(record: dict) -> float | None:
    total = record.get("totalPrice")
    if total is None:
        return None
    try:
        count = int(record.get("numberOfProducts") or 1)
    except (TypeError, ValueError):
        count = 1
    if count <= 0:
        return total
    return total / count


def summarize_sold_values(records: list[dict]) -> dict:
    unit_prices = [
        unit_price for record in records if (unit_price := _unit_price(record)) is not None
    ]

    by_version: dict[str, list[float]] = defaultdict(list)
    for record in records:
        unit_price = _unit_price(record)
        if unit_price is not None:
            by_version[record["version"]].append(unit_price)

    descriptions: list[str] = []
    seen: set[str] = set()
    for record in records:
        text = (record.get("shortDescription") or "").strip()
        if text and text not in seen:
            seen.add(text)
            descriptions.append(text)

    total_products = sum(int(r.get("numberOfProducts") or 1) for r in records)

    return {
        **_price_stats(unit_prices),
        "listingCount": len(records),
        "totalProducts": total_products,
        "by_version": {
            code: _price_stats(values) for code, values in sorted(by_version.items())
        },
        "descriptions": descriptions,
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


def migrate_sold_values(path: Path) -> bool:
    connection = sqlite3.connect(path)
    try:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(sold_values)")
        }
        if "product" in columns:
            return False
        if not set(_OLD_COLUMNS).issubset(columns):
            raise ValueError(f"Unexpected sold_values schema: {sorted(columns)}")

        connection.execute(
            "CREATE TABLE sold_values_new ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "product TEXT NOT NULL,"
            "version TEXT NOT NULL,"
            "shortDescription TEXT NOT NULL DEFAULT '',"
            "totalPrice REAL NOT NULL,"
            "numberOfProducts INTEGER NOT NULL DEFAULT 1)"
        )
        connection.execute(
            "INSERT INTO sold_values_new "
            "(id, product, version, shortDescription, totalPrice, numberOfProducts) "
            "SELECT id, console, console_code, description, total_price, 1 "
            "FROM sold_values ORDER BY id"
        )
        connection.execute("DROP TABLE sold_values")
        connection.execute("ALTER TABLE sold_values_new RENAME TO sold_values")
        connection.execute(
            "DELETE FROM sqlite_sequence WHERE name IN ('sold_values', 'sold_values_new')"
        )
        connection.commit()
        return True
    finally:
        connection.close()
