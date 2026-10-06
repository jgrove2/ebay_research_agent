from ebay_research_agent.graph import fan_out
from ebay_research_agent.nodes import fan_out_listings, format_output, group_by_product
from ebay_research_agent.prompts import issues_prompt


def test_fan_out_sends_one_worker_per_product() -> None:
    commands = fan_out({"products": ["wii", "switch"]})
    assert [(command.node, command.arg) for command in commands] == [
        ("product_worker", {"product": "wii"}),
        ("product_worker", {"product": "switch"}),
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
