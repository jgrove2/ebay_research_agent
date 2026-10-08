from langgraph.types import Send

from ebay_research_agent.state import IssuesState


def split_by_listing(state: IssuesState) -> list[Send] | str:
    listings = state.get("listings", {})
    sold_summaries = state.get("sold_summaries", {})
    commands = [
        Send(
            "evaluate_listing",
            {
                "product": product,
                "listing": listing,
                "sold_summaries": sold_summaries,
            },
        )
        for product, items in listings.items()
        for listing in items
    ]
    return commands or "END"
