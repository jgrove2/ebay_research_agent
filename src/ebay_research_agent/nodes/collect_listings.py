from langgraph.types import Send

from ebay_research_agent.state import IssuesState


def join_listings(state: IssuesState) -> dict:
    return {}


def fan_out_listings(state: IssuesState) -> list[Send] | str:
    cleaned = state["cleaned"]
    if not cleaned:
        return "aggregator"
    sold_summaries = state.get("sold_summaries", {})
    return [
        Send(
            "evaluate_listing",
            {
                "product": item["product"],
                "listing": item,
                "sold_summaries": sold_summaries,
            },
        )
        for item in cleaned
    ]
