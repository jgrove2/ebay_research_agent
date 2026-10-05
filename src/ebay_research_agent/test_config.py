from repair_agent.config import Settings


def test_defaults() -> None:
    settings = Settings(_env_file=None)
    assert settings.deepseek_model == "deepseek-chat"
    assert settings.deepseek_base_url == "https://api.deepseek.com"
    assert settings.temperature == 0.0
    assert settings.max_tokens == 4096


def test_env_override(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-reasoner")
    settings = Settings(_env_file=None)
    assert settings.deepseek_api_key == "test-key"
    assert settings.deepseek_model == "deepseek-reasoner"
