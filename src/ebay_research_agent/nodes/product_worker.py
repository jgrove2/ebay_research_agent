import json
from collections.abc import Awaitable, Callable

from langchain_core.messages import HumanMessage, ToolMessage

from ebay_research_agent.prompts import (
    EBAY_TOOL_NAME,
    issues_prompt,
    judgement_prompt,
)
from ebay_research_agent.state import IssuesState

Node = Callable[[IssuesState], Awaitable[dict]]


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


def build_product_worker_node(
    worker_agent,
    ebay_agent,
    extractor,
    judge,
) -> Node:
    async def product_worker(state: IssuesState) -> dict:
        product = state["product"]

        result = await worker_agent.ainvoke(
            {"messages": [HumanMessage(content=issues_prompt(product))]}
        )
        research = result["messages"][-1].content
        structured = await extractor.ainvoke(
            [
                HumanMessage(
                    content=(
                        f"Console: {product}\n\n"
                        f"Research notes:\n{research}\n\n"
                        f"Return the common issues and the for-parts blurb."
                    )
                )
            ]
        )
        issues = structured.issues
        blurb = structured.blurb

        ebay_prompt = (
            f"Console: {product}\n\n"
            f"Common issues:\n"
            + "\n".join(f"- {issue}" for issue in issues)
            + f"\n\nFor-parts blurb:\n{blurb}\n\n"
            f"Find 'for parts or not working' listings for this console within a "
            f"profitable price range (accounting for shipping), and report each "
            f"listing's title, price, shipping cost, total cost, and URL."
        )
        ebay_result = await ebay_agent.ainvoke(
            {"messages": [HumanMessage(content=ebay_prompt)]}
        )
        items = extract_items(ebay_result["messages"])

        cleaned: list[dict] = []
        if items:
            batch = await judge.ainvoke(
                [HumanMessage(content=judgement_prompt(product, items))]
            )
            cleaned = [item.model_dump() for item in batch.listings]

        return {
            "results": [{"product": product, "issues": issues, "blurb": blurb}],
            "listings": [{"product": product, "items": items}],
            "cleaned": cleaned,
        }

    return product_worker
