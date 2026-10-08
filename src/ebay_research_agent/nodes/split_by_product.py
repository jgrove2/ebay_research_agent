from langgraph.types import Send

from ebay_research_agent.state import IssuesState


def split_by_product(state: IssuesState) -> list[Send]:
    return [
        Send("get_product_info", {"product": product})
        for product in state["products"]
    ]
