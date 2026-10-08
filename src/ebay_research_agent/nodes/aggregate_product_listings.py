from ebay_research_agent.state import IssuesState_v2


def aggregate_product_listings(state: IssuesState_v2) -> dict:
    combined = {
        product: {
            "product_info": state.get("product_info", {}).get(product),
            "sold_summary": state.get("sold_summaries", {}).get(product),
            "listings": state.get("listings", {}).get(product, []),
            "evaluations": state.get("evaluations_by_product", {}).get(product, []),
        }
        for product in state["products"]
    }
    return {"combined": combined}
