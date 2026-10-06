from ebay_research_agent.sold_values import comps_for, load_sold_values


def test_load_sold_values_returns_records() -> None:
    records = load_sold_values()
    assert isinstance(records, list)
    assert all("product" in record for record in records)


def test_comps_for_filters_by_product() -> None:
    records = comps_for("wii")
    assert records
    assert all(record["product"] == "wii" for record in records)
    assert {record["class"] for record in records} == {
        "console_working",
        "console_parts",
    }


def test_comps_for_unknown_product_empty() -> None:
    assert comps_for("nonexistent") == []
