import json
from collections.abc import Awaitable, Callable

from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.prebuilt import create_react_agent

from ebay_research_agent.models import get_model
from ebay_research_agent.state import IssuesState

Node = Callable[[IssuesState], Awaitable[dict]]

EBAY_SYSTEM_PROMPT = (
    "You search eBay for 'for parts or not working' game console listings. "
    "Call search_ebay_for_parts once with a good query for the console. "
    "The tool stores all results itself; reply with a brief summary of the "
    "count and the best-looking deals. If there are no results, say so."
)

EBAY_TOOL_NAME = "search_ebay_for_parts"


def build_ebay_prompt(product: str) -> str:
    return (
        f"Console: {product}\n\n"
        f"Find 'for parts or not working' listings for this console within a "
        f"profitable price range (accounting for shipping), and report each "
        f"listing's title, price, shipping cost, total cost, and URL."
    )


def extract_items(messages: list) -> list[dict]:
    items: list[dict] = []
    seen: set[str] = set()
    for message in messages:
        if isinstance(message, ToolMessage) and message.name == EBAY_TOOL_NAME:
            artifact = message.artifact
            if not isinstance(artifact, list):
                continue
            for item in artifact:
                item_id = item.get("item_id")
                if item_id and item_id in seen:
                    continue
                if item_id:
                    seen.add(item_id)
                items.append(item)
    return items

def build_get_ebay_listings_node(ebay_tools: list) -> Node:
    ebay_agent = create_react_agent(get_model(), ebay_tools, prompt=EBAY_SYSTEM_PROMPT)

    async def get_ebay_listings(state: IssuesState) -> dict:
        product = state["product"]

        result = await ebay_agent.ainvoke(
            {"messages": [HumanMessage(content=build_ebay_prompt(product))]}
        )
        items = extract_items(result["messages"])

        return {
            "product": product,
            "listings": {product: items},
        }

    return get_ebay_listings
