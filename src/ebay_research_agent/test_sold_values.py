import sqlite3

import pytest

from ebay_research_agent.config import get_settings
from ebay_research_agent.sold_values import (
    comps_for,
    load_sold_values,
    sold_records_for,
    summarize_sold_values,
)


@pytest.fixture
def seeded_db(tmp_path, monkeypatch):
    db_path = tmp_path / "sold_values.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE sold_values ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "product TEXT NOT NULL,"
        "version TEXT NOT NULL,"
        "shortDescription TEXT NOT NULL DEFAULT '',"
        "totalPrice REAL NOT NULL,"
        "numberOfProducts INTEGER NOT NULL DEFAULT 1)"
    )
    conn.executemany(
        "INSERT INTO sold_values "
        "(product, version, shortDescription, totalPrice, numberOfProducts) "
        "VALUES (?, ?, ?, ?, ?)",
        [
            ("wii", "RVL-001", "console only", 40.0, 1),
            ("wii", "RVL-101", "console + cables", 50.0, 1),
            ("switch", "HAC-001", "console + dock", 150.0, 1),
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
    assert all("product" in record for record in records)
    assert all("totalPrice" in record for record in records)


def test_comps_for_filters_by_product(seeded_db) -> None:
    records = comps_for("wii")
    assert records
    assert all(record["product"] == "wii" for record in records)
    assert {record["version"] for record in records} == {"RVL-001", "RVL-101"}


def test_comps_for_unknown_console_empty(seeded_db) -> None:
    assert comps_for("nonexistent") == []


def test_sold_records_for_filters_and_drops_product(seeded_db) -> None:
    records = sold_records_for("wii")
    assert records
    assert all("product" not in record for record in records)
    assert all(
        set(record) == {"version", "shortDescription", "totalPrice", "numberOfProducts"}
        for record in records
    )
    assert {record["version"] for record in records} == {"RVL-001", "RVL-101"}


def test_sold_records_for_unknown_console_empty(seeded_db) -> None:
    assert sold_records_for("nonexistent") == []


def test_summarize_sold_values_stats() -> None:
    records = [
        {"product": "wii", "version": "RVL-001", "shortDescription": "console only", "totalPrice": 40.0, "numberOfProducts": 1},
        {"product": "wii", "version": "RVL-001", "shortDescription": "console only", "totalPrice": 120.0, "numberOfProducts": 2},
        {"product": "wii", "version": "RVL-101", "shortDescription": "console + cables", "totalPrice": 50.0, "numberOfProducts": 1},
    ]
    summary = summarize_sold_values(records)
    assert summary["count"] == 3
    assert summary["average"] == 50.0
    assert summary["median"] == 50.0
    assert summary["min"] == 40.0
    assert summary["max"] == 60.0
    assert summary["listingCount"] == 3
    assert summary["totalProducts"] == 4
    assert summary["by_version"]["RVL-001"]["count"] == 2
    assert summary["by_version"]["RVL-001"]["average"] == 50.0
    assert summary["by_version"]["RVL-101"]["count"] == 1
    assert summary["descriptions"] == ["console only", "console + cables"]


def test_summarize_sold_values_empty() -> None:
    summary = summarize_sold_values([])
    assert summary == {
        "count": 0,
        "average": None,
        "median": None,
        "min": None,
        "max": None,
        "listingCount": 0,
        "totalProducts": 0,
        "by_version": {},
        "descriptions": [],
    }
