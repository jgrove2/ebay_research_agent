from functools import lru_cache
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class McpServerConfig(BaseModel):
    command: str
    args: list[str] = Field(default_factory=list)
    transport: str = "stdio"


def _default_mcp_servers() -> dict[str, McpServerConfig]:
    return {
        "duckduckgo": McpServerConfig(
            command="npx",
            args=["-y", "duckduckgo-mcp-server"],
            transport="stdio",
        ),
    }


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"
    deepseek_base_url: str = "https://api.deepseek.com"
    temperature: float = 0.0
    max_tokens: int = 4096

    products: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["wii", "switch"]
    )
    mcp_servers: dict[str, McpServerConfig] = Field(
        default_factory=_default_mcp_servers
    )

    ebay_env: Literal["sandbox", "production"] = "sandbox"
    ebay_marketplace_id: str = "EBAY_US"
    ebay_zip_code: str = ""
    ebay_country: str = "US"
    ebay_app_id_sandbox: str = ""
    ebay_dev_id_sandbox: str = ""
    ebay_cert_id_sandbox: str = ""
    ebay_app_id_production: str = ""
    ebay_dev_id_production: str = ""
    ebay_cert_id_production: str = ""

    @field_validator("products", mode="before")
    @classmethod
    def _parse_products(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    def ebay_credentials(self) -> tuple[str, str, str]:
        if self.ebay_env == "production":
            return (
                self.ebay_app_id_production,
                self.ebay_cert_id_production,
                self.ebay_dev_id_production,
            )
        return (
            self.ebay_app_id_sandbox,
            self.ebay_cert_id_sandbox,
            self.ebay_dev_id_sandbox,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
