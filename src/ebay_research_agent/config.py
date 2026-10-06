from functools import lru_cache
from typing import Annotated

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

    @field_validator("products", mode="before")
    @classmethod
    def _parse_products(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
