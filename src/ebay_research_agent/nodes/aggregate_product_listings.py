from ebay_research_agent.state import IssuesState


def aggregate_product_listings(state: IssuesState) -> dict:
    return {"combined": state.get("accepted_listings", {})}
