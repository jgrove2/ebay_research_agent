from ebay_research_agent.config import Settings


def test_defaults() -> None:
    settings = Settings(_env_file=None)
    assert settings.deepseek_model == "deepseek-chat"
    assert settings.deepseek_base_url == "https://api.deepseek.com"
    assert settings.temperature == 0.0
    assert settings.max_tokens == 4096
    assert settings.products == ["wii", "switch"]


def test_env_override(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-reasoner")
    settings = Settings(_env_file=None)
    assert settings.deepseek_api_key == "test-key"
    assert settings.deepseek_model == "deepseek-reasoner"


def test_products_env_override(monkeypatch) -> None:
    monkeypatch.setenv("PRODUCTS", "gamecube, n64")
    settings = Settings(_env_file=None)
    assert settings.products == ["gamecube", "n64"]


def test_mcp_servers_default() -> None:
    settings = Settings(_env_file=None)
    duckduckgo = settings.mcp_servers["duckduckgo"]
    assert duckduckgo.command == "npx"
    assert duckduckgo.transport == "stdio"
    assert "-y" in duckduckgo.args
