from ebay_research_agent.state import IssuesState_v2


def get_product_info(state: IssuesState_v2) -> dict:
    product = state["product"]
    return {
        "product_info": {
            product: {
                "issues": [],
                "blurb": "",
            }
        }
    }
