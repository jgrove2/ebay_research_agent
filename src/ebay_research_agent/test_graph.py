from ebay_research_agent.graph import fan_out, format_output, issues_prompt


def test_fan_out_sends_one_worker_per_product() -> None:
    commands = fan_out({"products": ["wii", "switch"]})
    assert [(command.node, command.arg) for command in commands] == [
        ("issues_worker", {"product": "wii"}),
        ("issues_worker", {"product": "switch"}),
    ]


def test_issues_prompt_mentions_product() -> None:
    assert "wii" in issues_prompt("wii")


def test_format_output_includes_every_product() -> None:
    researched = [
        {"product": "wii", "issues": ["disc drive fails"], "blurb": "look for dead drives"},
        {"product": "switch", "issues": ["joy-con drift"], "blurb": "look for drift"},
    ]
    listings = [
        {
            "product": "wii",
            "items": [{"title": "Broken Wii", "price": "25.00", "currency": "USD", "url": "u1"}],
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
