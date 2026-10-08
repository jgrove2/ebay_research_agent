from ebay_research_agent.sold_values import sold_records_for
from ebay_research_agent.state import IssuesState_v2


def get_product_info(state: IssuesState_v2) -> dict:
    product = state["product"]
    sold_listings = sold_records_for(product)

    return {
        "product_info": {
            product: {
                "issues": [],
                "blurb": "",
            }
        },
        "sold_product_data": {product: sold_listings},
    }
