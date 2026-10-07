from collections.abc import Awaitable, Callable

from ebay_research_agent.sold_values import comps_for, summarize_sold_values
from ebay_research_agent.state import IssuesState

Node = Callable[[IssuesState], Awaitable[dict]]


def build_sold_summary_node() -> Node:
    async def sold_summary(state: IssuesState) -> dict:
        product = state["product"]
        records = comps_for(product)
        summary = summarize_sold_values(records)
        return {"product": product, "sold_summaries": {product: summary}}

    return sold_summary
