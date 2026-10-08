import asyncio
import json
import sqlite3

import pytest
from langchain_core.messages import ToolMessage

from ebay_research_agent.config import get_settings
from ebay_research_agent.nodes import (
    build_evaluate_listing_node,
    get_product_info,
    split_by_listing,
)
from ebay_research_agent.nodes.get_ebay_listing import (
    EBAY_SYSTEM_PROMPT,
    EBAY_TOOL_NAME,
    build_ebay_prompt,
    build_get_ebay_listings_node,
    extract_items,
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


def test_split_by_listing_fans_out_one_evaluate_per_listing() -> None:
    commands = split_by_listing(
        {
            "listings": {
                "wii": [{"title": "Broken Wii", "url": "u1"}],
                "switch": [
                    {"title": "Dead Switch", "url": "u2"},
                    {"title": "Cracked Switch", "url": "u3"},
                ],
            },
            "sold_summaries": {"wii": {"average": 45.0}, "switch": {"average": 150.0}},
        }
    )
    assert [command.node for command in commands] == [
        "evaluate_listing",
        "evaluate_listing",
        "evaluate_listing",
    ]
    assert commands[0].arg["product"] == "wii"
    assert commands[0].arg["listing"]["url"] == "u1"
    assert commands[1].arg["product"] == "switch"
    assert commands[1].arg["listing"]["url"] == "u2"
    assert commands[2].arg["listing"]["url"] == "u3"
    assert commands[0].arg["sold_summaries"]["wii"]["average"] == 45.0


def test_split_by_listing_empty_routes_to_end() -> None:
    assert split_by_listing({"listings": {}}) == "END"


def test_build_evaluate_listing_node_returns_evaluation_when_accepted() -> None:
    class FakeJev:
        async def evaluate(self, state, questions):
            return {
                "choices": {"model_number": {"choice": "RVL-001"}},
                "nouls": {
                    "correct_product": {"noul": 0.9},
                    "water_damage": {"noul": 0.1},
                },
                "scores": {},
            }

    node = build_evaluate_listing_node(FakeJev())
    result = asyncio.run(
        node(
            {
                "product": "wii",
                "listing": {
                    "title": "Broken Wii",
                    "url": "u1",
                    "total_cost": "20.00",
                },
                "sold_summaries": {
                    "wii": {
                        "average": 45.0,
                        "by_version": {"RVL-001": {"average": 45.0}},
                    }
                },
            }
        )
    )
    assert len(result["evaluations"]) == 1
    assert result["evaluations"][0]["product"] == "wii"
    assert result["evaluations"][0]["listing"]["url"] == "u1"


def test_build_evaluate_listing_node_returns_empty_when_rejected() -> None:
    class FakeJev:
        async def evaluate(self, state, questions):
            return {
                "choices": {"model_number": {"choice": "RVL-001"}},
                "nouls": {
                    "correct_product": {"noul": 0.9},
                    "water_damage": {"noul": 0.8},
                },
                "scores": {},
            }

    node = build_evaluate_listing_node(FakeJev())
    result = asyncio.run(
        node(
            {
                "product": "wii",
                "listing": {
                    "title": "Broken Wii",
                    "url": "u1",
                    "total_cost": "20.00",
                },
                "sold_summaries": {
                    "wii": {
                        "average": 45.0,
                        "by_version": {"RVL-001": {"average": 45.0}},
                    }
                },
            }
        )
    )
    assert result == {}


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
