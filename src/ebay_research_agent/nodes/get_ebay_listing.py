import json
from collections.abc import Awaitable, Callable

from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.prebuilt import create_react_agent

from ebay_research_agent.models import get_model
from ebay_research_agent.state import IssuesState

Node = Callable[[IssuesState], Awaitable[dict]]

EBAY_SYSTEM_PROMPT = (
    "You search eBay for 'for parts or not working' game console listings that "
    "could be profitable to buy, repair, or part out. Given a console, its "
    "common issues, and a blurb describing what to look for, decide a price "
    "range where the listing is cheap enough to make a profit. Use the "
    "search_ebay_for_parts tool to find listings within that range. Judge "
    "profitability by the total cost (item price plus shipping), not just the "
    "item price. Then report each listing with its title, price, shipping cost, "
    "total cost, and URL. If the search returns no results, say so."
)

EBAY_TOOL_NAME = "search_ebay_for_parts"


def build_ebay_prompt(product: str, issues: list[str], blurb: str) -> str:
    return (
        f"Console: {product}\n\n"
        f"Common issues:\n"
        + "\n".join(f"- {issue}" for issue in issues)
        + f"\n\nFor-parts blurb:\n{blurb}\n\n"
        f"Find 'for parts or not working' listings for this console within a "
        f"profitable price range (accounting for shipping), and report each "
        f"listing's title, price, shipping cost, total cost, and URL."
    )


def extract_items(messages: list) -> list[dict]:
    items: list[dict] = []
    for message in messages:
        if isinstance(message, ToolMessage) and message.name == EBAY_TOOL_NAME:
            try:
                parsed = json.loads(message.content)
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(parsed, list):
                items.extend(parsed)
    return items


def build_get_ebay_listings_node(ebay_tools: list) -> Node:
    ebay_agent = create_react_agent(get_model(), ebay_tools, prompt=EBAY_SYSTEM_PROMPT)

    async def get_ebay_listings(state: IssuesState) -> dict:
        product = state["product"]
        info = state.get("product_info", {}).get(product, {})
        issues = info.get("issues", [])
        blurb = info.get("blurb", "")

        result = await ebay_agent.ainvoke(
            {"messages": [HumanMessage(content=build_ebay_prompt(product, issues, blurb))]}
        )
        items = extract_items(result["messages"])

        return {
            "product": product,
            "listings": {product: items},
        }

    return get_ebay_listings
