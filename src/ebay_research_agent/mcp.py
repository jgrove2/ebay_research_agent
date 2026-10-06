from langchain_mcp_adapters.client import MultiServerMCPClient

from ebay_research_agent.config import get_settings


async def load_search_tools() -> list:
    settings = get_settings()
    connections = {
        name: config.model_dump() for name, config in settings.mcp_servers.items()
    }
    client = MultiServerMCPClient(connections)
    return await client.get_tools()
