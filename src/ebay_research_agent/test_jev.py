from ebay_research_agent.jev import build_accept_questions, should_accept


def test_build_accept_questions_has_expected_keys() -> None:
    questions = build_accept_questions()
    assert set(questions) == {"correct_product", "worth_price", "water_damage"}


def test_should_accept_all_pass() -> None:
    result = {
        "nouls": {
            "correct_product": {"noul": 0.9},
            "worth_price": {"noul": 0.9},
            "water_damage": {"noul": 0.1},
        },
    }
    assert should_accept(result, 0.7, 0.7, 0.7) is True


def test_should_accept_rejects_wrong_product() -> None:
    result = {
        "nouls": {
            "correct_product": {"noul": 0.2},
            "worth_price": {"noul": 0.9},
            "water_damage": {"noul": 0.1},
        },
    }
    assert should_accept(result, 0.7, 0.7, 0.7) is False


def test_should_accept_rejects_not_worth_price() -> None:
    result = {
        "nouls": {
            "correct_product": {"noul": 0.9},
            "worth_price": {"noul": 0.3},
            "water_damage": {"noul": 0.1},
        },
    }
    assert should_accept(result, 0.7, 0.7, 0.7) is False


def test_should_accept_rejects_water_damage() -> None:
    result = {
        "nouls": {
            "correct_product": {"noul": 0.9},
            "worth_price": {"noul": 0.9},
            "water_damage": {"noul": 0.8},
        },
    }
    assert should_accept(result, 0.7, 0.7, 0.7) is False
