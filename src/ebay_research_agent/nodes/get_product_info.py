from ebay_research_agent.sold_values import (
    sold_records_for,
    summarize_raw_sold_values,
)
from ebay_research_agent.state import IssuesState


def get_product_info(state: IssuesState) -> dict:
    product = state["product"]
    sold_listings = sold_records_for(product)

    return {
        "product": product,
        "product_info": {
            product: {
                "issues": [],
                "blurb": "",
            }
        },
        "sold_product_data": {product: sold_listings},
        "sold_summaries": {product: summarize_raw_sold_values(sold_listings)},
    }
