import asyncio
import sys

from ebay_research_agent.config import get_settings
from ebay_research_agent.ebay import EbayClient, base_url_for_env, build_ebay_tool
from ebay_research_agent.graph import build_graph
from ebay_research_agent.mcp import load_search_tools


async def run(products: list[str]) -> None:
    settings = get_settings()
    app_id, cert_id, _dev_id = settings.ebay_credentials()
    if not app_id or not cert_id:
        print(
            "eBay credentials are not set. Add EBAY_APP_ID_* and EBAY_CERT_ID_* "
            "to .env or your environment."
        )
        return

    search_tools = await load_search_tools()
    client = EbayClient(
        base_url=base_url_for_env(settings.ebay_env),
        app_id=app_id,
        cert_id=cert_id,
        marketplace_id=settings.ebay_marketplace_id,
        zip_code=settings.ebay_zip_code,
        country=settings.ebay_country,
    )
    try:
        ebay_tool = build_ebay_tool(client)
        graph = build_graph(search_tools, [ebay_tool])
        await graph.ainvoke({"products": products})
    finally:
        await client.close()


def print_diagram() -> None:
    if not get_settings().deepseek_api_key:
        print("DEEPSEEK_API_KEY is not set. Add it to .env or your environment.")
        return
    print(build_graph([], []).get_graph().draw_ascii())


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
