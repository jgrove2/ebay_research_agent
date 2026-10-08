from ebay_research_agent.state import IssuesState


def aggregate_listings(state: IssuesState) -> dict:
    grouped: dict[str, list[dict]] = {}
    for evaluation in state.get("evaluations", []):
        grouped.setdefault(evaluation["product"], []).append(evaluation)
    return {"evaluations_by_product": grouped}
