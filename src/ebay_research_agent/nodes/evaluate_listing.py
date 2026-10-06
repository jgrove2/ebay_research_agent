from collections.abc import Awaitable, Callable

from ebay_research_agent.config import get_settings
from ebay_research_agent.jev import JevClient, build_accept_questions, should_accept
from ebay_research_agent.sold_values import comps_for
from ebay_research_agent.state import IssuesState

Node = Callable[[IssuesState], Awaitable[dict]]


def build_evaluate_listing_node(jev: JevClient) -> Node:
    async def evaluate_listing(state: IssuesState) -> dict:
        product = state["product"]
        listing = state["listing"]
        jev_state = {
            "product": product,
            "listing": listing,
            "sold_value_comps": comps_for(product),
        }
        result = await jev.evaluate(jev_state, build_accept_questions())
        settings = get_settings()
        if not should_accept(
            result,
            settings.accept_fault_clarity_threshold,
            settings.accept_legitimate_threshold,
            settings.accept_profit_potential_threshold,
        ):
            return {}
        return {
            "evaluations": [
                {"product": product, "listing": listing, "decision": result}
            ]
        }

    return evaluate_listing
