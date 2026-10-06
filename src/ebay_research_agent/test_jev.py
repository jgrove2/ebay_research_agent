from ebay_research_agent.jev import build_accept_questions, should_accept


def test_build_accept_questions_has_expected_keys() -> None:
    questions = build_accept_questions()
    assert set(questions) == {"fault_clarity", "legitimate", "profit_potential"}


def test_should_accept_all_pass() -> None:
    result = {
        "nouls": {"fault_clarity": {"noul": 0.9}, "legitimate": {"noul": 0.9}},
        "scores": {"profit_potential": {"score": 0.0}},
    }
    assert should_accept(result, 0.7, 0.7, 1.0) is True


def test_should_accept_rejects_below_threshold() -> None:
    result = {
        "nouls": {"fault_clarity": {"noul": 0.5}, "legitimate": {"noul": 0.9}},
        "scores": {"profit_potential": {"score": 0.0}},
    }
    assert should_accept(result, 0.7, 0.7, 1.0) is False


def test_should_accept_rejects_overpriced() -> None:
    result = {
        "nouls": {"fault_clarity": {"noul": 0.9}, "legitimate": {"noul": 0.9}},
        "scores": {"profit_potential": {"score": 2.0}},
    }
    assert should_accept(result, 0.7, 0.7, 1.0) is False
