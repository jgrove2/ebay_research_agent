import sqlite3
from pathlib import Path

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
