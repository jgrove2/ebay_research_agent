import asyncio
import sys

from ebay_research_agent.config import get_settings
from ebay_research_agent.graph import build_graph
from ebay_research_agent.mcp import load_search_tools


async def run(products: list[str]) -> None:
    tools = await load_search_tools()
    graph = build_graph(tools)
    await graph.ainvoke({"products": products})


def print_diagram() -> None:
    if not get_settings().deepseek_api_key:
        print("DEEPSEEK_API_KEY is not set. Add it to .env or your environment.")
        return
    print(build_graph([]).get_graph().draw_ascii())


def main() -> None:
    if "--diagram" in sys.argv:
        print_diagram()
        return
    settings = get_settings()
    if not settings.deepseek_api_key:
        print("DEEPSEEK_API_KEY is not set. Add it to .env or your environment.")
        return
    asyncio.run(run(settings.products))


if __name__ == "__main__":
    main()
