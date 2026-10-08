import asyncio
import json
import sqlite3

import pytest
from langchain_core.messages import ToolMessage

from ebay_research_agent.config import get_settings
from ebay_research_agent.graph import fan_out
from ebay_research_agent.nodes import (
    fan_out_listings,
    format_output,
    get_product_info,
    group_by_product,
)
from ebay_research_agent.nodes.get_ebay_listing import (
    EBAY_SYSTEM_PROMPT,
    EBAY_TOOL_NAME,
    build_ebay_prompt,
    build_get_ebay_listings_node,
    extract_items,
)
from ebay_research_agent.prompts import issues_prompt


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


def test_fan_out_sends_one_worker_per_product() -> None:
    commands = fan_out({"products": ["wii", "switch"]})
    assert [(command.node, command.arg) for command in commands] == [
        ("sold_summary", {"product": "wii"}),
        ("sold_summary", {"product": "switch"}),
    ]


def test_fan_out_listings_sends_one_evaluate_per_listing() -> None:
    commands = fan_out_listings(
        {
            "cleaned": [
                {
                    "product": "wii",
                    "issue": "no power",
                    "totalPrice": "$20",
                    "url": "u1",
                },
                {"product": "wii", "issue": "disc", "totalPrice": "$30", "url": "u2"},
            ]
        }
    )
    assert [command.node for command in commands] == [
        "evaluate_listing",
        "evaluate_listing",
    ]
    assert commands[0].arg["product"] == "wii"
    assert commands[0].arg["listing"]["issue"] == "no power"
    assert commands[1].arg["listing"]["issue"] == "disc"


def test_fan_out_listings_empty_routes_to_aggregator() -> None:
    assert fan_out_listings({"cleaned": []}) == "aggregator"


def test_get_product_info_mocks_and_loads_sold_data(seeded_db) -> None:
    result = get_product_info({"product": "wii"})
    assert result["product_info"]["wii"] == {"issues": [], "blurb": ""}
    records = result["sold_product_data"]["wii"]
    assert records
    assert all("product" not in record for record in records)
    assert {record["version"] for record in records} == {"RVL-001", "RVL-101"}
    summary = result["sold_summaries"]["wii"]
    assert summary["average"] == 45.0
    assert summary["by_version"]["RVL-001"]["average"] == 40.0
    assert summary["by_version"]["RVL-101"]["average"] == 50.0


def test_issues_prompt_mentions_product() -> None:
    assert "wii" in issues_prompt("wii")


def test_format_output_includes_every_product() -> None:
    researched = [
        {
            "product": "wii",
            "issues": ["disc drive fails"],
            "blurb": "look for dead drives",
        },
        {"product": "switch", "issues": ["joy-con drift"], "blurb": "look for drift"},
    ]
    listings = [
        {
            "product": "wii",
            "items": [
                {
                    "title": "Broken Wii",
                    "price": "25.00",
                    "currency": "USD",
                    "url": "u1",
                }
            ],
        }
    ]
    text = format_output(researched, listings)
    assert "wii" in text
    assert "switch" in text
    assert "disc drive fails" in text
    assert "joy-con drift" in text
    assert "look for dead drives" in text
    assert "look for drift" in text
    assert "Broken Wii" in text
    assert "u1" in text
    assert "(no listings found)" in text


def test_group_by_product_groups_entries() -> None:
    entries = [
        {"product": "wii", "issue": "no power"},
        {"product": "switch", "issue": "drift"},
        {"product": "wii", "issue": "disc"},
    ]
    assert group_by_product(entries) == {
        "wii": [
            {"product": "wii", "issue": "no power"},
            {"product": "wii", "issue": "disc"},
        ],
        "switch": [{"product": "switch", "issue": "drift"}],
    }


def test_build_ebay_prompt_mentions_product_issues_and_blurb() -> None:
    prompt = build_ebay_prompt("wii", ["no power", "disc drive"], "look for dead drives")
    assert "wii" in prompt
    assert "no power" in prompt
    assert "disc drive" in prompt
    assert "look for dead drives" in prompt


def test_extract_items_parses_only_ebay_tool_messages() -> None:
    messages = [
        ToolMessage(
            content=json.dumps([{"title": "Broken Wii", "price": "20.00"}]),
            name=EBAY_TOOL_NAME,
            tool_call_id="1",
        ),
        ToolMessage(content="not json", name=EBAY_TOOL_NAME, tool_call_id="2"),
        ToolMessage(content='{"not": "a list"}', name=EBAY_TOOL_NAME, tool_call_id="3"),
        ToolMessage(
            content=json.dumps([{"title": "other"}]),
            name="other_tool",
            tool_call_id="4",
        ),
    ]
    assert extract_items(messages) == [{"title": "Broken Wii", "price": "20.00"}]


def test_get_ebay_listings_node_returns_listings_by_product(monkeypatch) -> None:
    captured: dict = {}

    class FakeAgent:
        async def ainvoke(self, state):
            captured["content"] = state["messages"][-1].content
            return {
                "messages": [
                    ToolMessage(
                        content=json.dumps([{"title": "Broken Wii", "url": "u1"}]),
                        name=EBAY_TOOL_NAME,
                        tool_call_id="1",
                    )
                ]
            }

    def fake_create_react_agent(model, tools, prompt=None):
        captured["system"] = prompt
        return FakeAgent()

    monkeypatch.setattr(
        "ebay_research_agent.nodes.get_ebay_listing.create_react_agent",
        fake_create_react_agent,
    )

    node = build_get_ebay_listings_node([])
    result = asyncio.run(
        node(
            {
                "product": "wii",
                "product_info": {"wii": {"issues": ["no power"], "blurb": "blurb"}},
            }
        )
    )

    assert result["product"] == "wii"
    assert result["listings"] == {"wii": [{"title": "Broken Wii", "url": "u1"}]}
    assert "wii" in captured["content"]
    assert "no power" in captured["content"]
    assert captured["system"] == EBAY_SYSTEM_PROMPT
