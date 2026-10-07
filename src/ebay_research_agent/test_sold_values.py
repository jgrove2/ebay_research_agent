import sqlite3

import pytest

from ebay_research_agent.config import get_settings
from ebay_research_agent.sold_values import (
    comps_for,
    load_sold_values,
    summarize_sold_values,
)


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


def test_summarize_sold_values_stats() -> None:
    records = [
        {"console": "wii", "console_code": "RVL-001", "description": "console only", "total_price": 40.0},
        {"console": "wii", "console_code": "RVL-001", "description": "console only", "total_price": 60.0},
        {"console": "wii", "console_code": "RVL-101", "description": "console + cables", "total_price": 50.0},
    ]
    summary = summarize_sold_values(records)
    assert summary["count"] == 3
    assert summary["average"] == 50.0
    assert summary["median"] == 50.0
    assert summary["min"] == 40.0
    assert summary["max"] == 60.0
    assert summary["by_model"]["RVL-001"]["count"] == 2
    assert summary["by_model"]["RVL-001"]["average"] == 50.0
    assert summary["by_model"]["RVL-101"]["count"] == 1
    assert summary["descriptions"] == ["console only", "console + cables"]


def test_summarize_sold_values_empty() -> None:
    summary = summarize_sold_values([])
    assert summary == {
        "count": 0,
        "average": None,
        "median": None,
        "min": None,
        "max": None,
        "by_model": {},
        "descriptions": [],
    }
