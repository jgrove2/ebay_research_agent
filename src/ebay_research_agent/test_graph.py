from ebay_research_agent.graph import fan_out, format_results, research_prompt


def test_fan_out_sends_one_worker_per_product() -> None:
    commands = fan_out({"products": ["wii", "switch"]})
    assert [(command.node, command.arg) for command in commands] == [
        ("research_worker", {"product": "wii"}),
        ("research_worker", {"product": "switch"}),
    ]


def test_research_prompt_mentions_product() -> None:
    assert "wii" in research_prompt("wii")


def test_format_results_includes_every_product() -> None:
    text = format_results(
        [
            {"product": "wii", "answer": "nope"},
            {"product": "switch", "answer": "nada"},
        ]
    )
    assert "wii" in text
    assert "switch" in text
    assert "nope" in text
    assert "nada" in text
