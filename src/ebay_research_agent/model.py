from langchain_deepseek import ChatDeepSeek

from repair_agent.config import get_settings


def get_model() -> ChatDeepSeek:
    settings = get_settings()
    return ChatDeepSeek(
        model=settings.deepseek_model,
        api_key=settings.deepseek_api_key,
        api_base=settings.deepseek_base_url,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
    )
