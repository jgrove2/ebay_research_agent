import sqlite3

import pytest

from ebay_research_agent.config import get_settings
from ebay_research_agent.sold_values import comps_for, load_sold_values


@pytest.fixture
def seeded_db(tmp_path, monkeypatch):
    db_path = tmp_path / "sold_values.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE sold_values ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "console TEXT NOT NULL,"
        "console_code TEXT NOT NULL,"
        "description TEXT NOT NULL DEFAULT '',"
        "total_price REAL NOT NULL)"
    )
    conn.executemany(
        "INSERT INTO sold_values (console, console_code, description, total_price) "
        "VALUES (?, ?, ?, ?)",
        [
            ("wii", "RVL-001", "console only", 40.0),
            ("wii", "RVL-101", "console + cables", 50.0),
            ("switch", "HAC-001", "console + dock", 150.0),
        ],
    )
    conn.commit()
    conn.close()
    monkeypatch.setenv("SOLD_VALUES_PATH", str(db_path))
    get_settings.cache_clear()
    return db_path


def test_load_sold_values_returns_records(seeded_db) -> None:
    records = load_sold_values()
    assert isinstance(records, list)
    assert all("console" in record for record in records)
    assert all("total_price" in record for record in records)


def test_comps_for_filters_by_console(seeded_db) -> None:
    records = comps_for("wii")
    assert records
    assert all(record["console"] == "wii" for record in records)
    assert {record["console_code"] for record in records} == {"RVL-001", "RVL-101"}


def test_comps_for_unknown_console_empty(seeded_db) -> None:
    assert comps_for("nonexistent") == []
