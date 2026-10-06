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


def test_ebay_defaults() -> None:
    settings = Settings(_env_file=None)
    assert settings.ebay_env == "sandbox"
    assert settings.ebay_marketplace_id == "EBAY_US"
    assert settings.ebay_zip_code == ""
    assert settings.ebay_country == "US"
    assert settings.ebay_app_id_sandbox == ""
    assert settings.ebay_cert_id_production == ""


def test_ebay_credentials_sandbox() -> None:
    settings = Settings(
        _env_file=None,
        ebay_env="sandbox",
        ebay_app_id_sandbox="sandbox-app",
        ebay_cert_id_sandbox="sandbox-cert",
        ebay_dev_id_sandbox="sandbox-dev",
        ebay_app_id_production="prod-app",
        ebay_cert_id_production="prod-cert",
        ebay_dev_id_production="prod-dev",
    )
    assert settings.ebay_credentials() == ("sandbox-app", "sandbox-cert", "sandbox-dev")


def test_ebay_credentials_production() -> None:
    settings = Settings(
        _env_file=None,
        ebay_env="production",
        ebay_app_id_sandbox="sandbox-app",
        ebay_cert_id_sandbox="sandbox-cert",
        ebay_dev_id_sandbox="sandbox-dev",
        ebay_app_id_production="prod-app",
        ebay_cert_id_production="prod-cert",
        ebay_dev_id_production="prod-dev",
    )
    assert settings.ebay_credentials() == ("prod-app", "prod-cert", "prod-dev")
