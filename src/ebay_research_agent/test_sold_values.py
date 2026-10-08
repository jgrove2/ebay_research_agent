import sqlite3

import pytest

from ebay_research_agent.config import get_settings
from ebay_research_agent.sold_values import (
    sold_records_for,
    summarize_raw_sold_values,
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


def test_summarize_raw_sold_values_stats() -> None:
    records = [
        {"version": "RVL-001", "totalPrice": 40.0, "numberOfProducts": 1},
        {"version": "RVL-001", "totalPrice": 120.0, "numberOfProducts": 2},
        {"version": "RVL-101", "totalPrice": 50.0, "numberOfProducts": 1},
    ]
    summary = summarize_raw_sold_values(records)
    assert summary["average"] == 70.0
    assert summary["listingCount"] == 3
    assert summary["by_version"]["RVL-001"]["average"] == 80.0
    assert summary["by_version"]["RVL-101"]["average"] == 50.0
    assert summary["by_number_of_products"]["1"]["average"] == 45.0
    assert summary["by_number_of_products"]["2"]["average"] == 120.0
    assert summary["by_version_number_of_products"]["RVL-001"]["1"]["average"] == 40.0
    assert summary["by_version_number_of_products"]["RVL-001"]["2"]["average"] == 120.0
    assert summary["by_version_number_of_products"]["RVL-101"]["1"]["average"] == 50.0


def test_summarize_raw_sold_values_empty() -> None:
    summary = summarize_raw_sold_values([])
    assert summary == {
        "count": 0,
        "average": None,
        "median": None,
        "min": None,
        "max": None,
        "listingCount": 0,
        "by_version": {},
        "by_number_of_products": {},
        "by_version_number_of_products": {},
    }
