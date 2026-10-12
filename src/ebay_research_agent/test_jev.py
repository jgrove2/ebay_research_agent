from ebay_research_agent.jev import has_profit, number_of_consoles, should_accept
from ebay_research_agent.nodes.evaluate_listing import (
    build_accept_questions,
    included_flags,
    listing_total_cost,
    noul_value,
    sold_average_for,
)


def test_build_accept_questions_has_expected_keys() -> None:
    questions = build_accept_questions(["RVL-001"])
    assert set(questions) == {
        "correct_product",
        "water_damage",
        "includes_controllers",
        "includes_games",
        "includes_cords",
        "model_number",
        "number_of_consoles",
    }


def test_build_accept_questions_model_number_criteria() -> None:
    questions = build_accept_questions(["RVL-001", "RVL-101"])
    assert set(questions["model_number"].criteria) == {"RVL-001", "RVL-101", "unknown"}


def test_build_accept_questions_number_of_consoles_criteria() -> None:
    questions = build_accept_questions([])
    assert set(questions["number_of_consoles"].criteria) == {
        *[str(n) for n in range(1, 10)],
        "10+",
    }


def _result(nouls: dict, model_number: str = "RVL-001") -> dict:
    return {
        "nouls": nouls,
        "choices": {"model_number": {"choice": model_number}},
    }


def test_should_accept_all_pass() -> None:
    result = _result(
        {"correct_product": {"noul": 0.9}, "water_damage": {"noul": 0.1}}
    )
    assert should_accept(result, 25.0, 50.0, 0.7, 0.7, 0.10) is True


def test_should_accept_rejects_wrong_product() -> None:
    result = _result(
        {"correct_product": {"noul": 0.2}, "water_damage": {"noul": 0.1}}
    )
    assert should_accept(result, 25.0, 50.0, 0.7, 0.7, 0.10) is False


def test_should_accept_rejects_water_damage() -> None:
    result = _result(
        {"correct_product": {"noul": 0.9}, "water_damage": {"noul": 0.8}}
    )
    assert should_accept(result, 25.0, 50.0, 0.7, 0.7, 0.10) is False


def test_should_accept_rejects_no_profit() -> None:
    result = _result(
        {"correct_product": {"noul": 0.9}, "water_damage": {"noul": 0.1}}
    )
    assert should_accept(result, 49.0, 50.0, 0.7, 0.7, 0.10) is False


def test_has_profit_requires_ten_percent_margin() -> None:
    assert has_profit(45.0, 50.0, 0.10) is True
    assert has_profit(45.1, 50.0, 0.10) is False
    assert has_profit(None, 50.0, 0.10) is False
    assert has_profit(45.0, None, 0.10) is False
    assert has_profit(45.0, 0.0, 0.10) is False


def test_number_of_consoles_parses_choice() -> None:
    def result(choice: object) -> dict:
        return {"choices": {"number_of_consoles": {"choice": choice}}}

    assert number_of_consoles(result("3")) == 3
    assert number_of_consoles(result("10+")) == 10
    assert number_of_consoles(result("1")) == 1
    assert number_of_consoles(result(None)) == 1
    assert number_of_consoles({"choices": {}}) == 1
    assert number_of_consoles({}) == 1


def test_listing_total_cost_parses_fields() -> None:
    assert listing_total_cost({"total_cost": "25.00"}) == 25.0
    assert listing_total_cost({"totalPrice": "$25.00"}) == 25.0
    assert listing_total_cost({"price": 20.0, "shipping_cost": 5.0}) == 25.0
    assert listing_total_cost({"price": "20.00", "shipping": 5}) == 25.0
    assert listing_total_cost({"price": 20.0}) == 20.0
    assert listing_total_cost({}) is None


def test_sold_average_for_uses_version_and_falls_back() -> None:
    summary = {
        "average": 45.0,
        "by_version": {"RVL-001": {"average": 40.0}},
    }
    assert sold_average_for(summary, "RVL-001") == 40.0
    assert sold_average_for(summary, "RVL-101") == 45.0
    assert sold_average_for(summary, "unknown") == 45.0
    assert sold_average_for({}, "RVL-001") is None


def test_noul_value_reads_nested_noul() -> None:
    result = {"nouls": {"includes_games": {"noul": 0.9}}}
    assert noul_value(result, "includes_games") == 0.9


def test_noul_value_falls_back_to_zero() -> None:
    assert noul_value({}, "includes_games") == 0.0
    assert noul_value({"nouls": {}}, "includes_games") == 0.0
    assert noul_value({"nouls": {"includes_games": {}}}, "includes_games") == 0.0
    assert noul_value({"nouls": {"includes_games": {"noul": None}}}, "includes_games") == 0.0


def test_included_flags_uses_threshold() -> None:
    result = {
        "nouls": {
            "includes_controllers": {"noul": 0.8},
            "includes_games": {"noul": 0.2},
            "includes_cords": {"noul": 0.5},
        }
    }
    assert included_flags(result, 0.5) == {
        "controllers": True,
        "games": False,
        "cords": True,
    }
    assert included_flags(result, 0.7) == {
        "controllers": True,
        "games": False,
        "cords": False,
    }


def test_included_flags_all_false_when_missing() -> None:
    assert included_flags({}, 0.5) == {
        "controllers": False,
        "games": False,
        "cords": False,
    }
