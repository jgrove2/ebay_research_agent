import json
from collections.abc import Awaitable, Callable

from typesafe_sdk import Noul

from ebay_research_agent.config import get_settings
from ebay_research_agent.jev import JevClient, should_accept
from ebay_research_agent.state import IssuesState

Node = Callable[[IssuesState], Awaitable[dict]]


def build_accept_questions() -> dict:
    return {
        "correct_product": Noul(
            instructions=(
                "Is this listing a console unit matching the product named in the "
                "state — not a game, accessory, controller, or a different console?"
            )
        ),
        "worth_price": Noul(
            instructions=(
                "Using the sold-value summary in the state, is the listing's total "
                "price (item + shipping) roughly half or less of the typical sold "
                "value, meaning there is room to profit after repairing or parting "
                "it out?"
            )
        ),
        "water_damage": Noul(
            instructions=(
                "Does the listing indicate water damage (liquid exposure, "
                "corrosion, waterlogged, or water damage)?"
            )
        ),
    }


def build_evaluate_listing_node(jev: JevClient) -> Node:
    async def evaluate_listing(state: IssuesState) -> dict:
        product = state["product"]
        listing = state["listing"]
        jev_state = {
            "product": product,
            "listing": listing,
            "sold_value_summary": state.get("sold_summaries", {}).get(product),
        }
        result = await jev.evaluate(jev_state, build_accept_questions())
        settings = get_settings()
        correct_product = result["nouls"]["correct_product"]["noul"]
        worth_price = result["nouls"]["worth_price"]["noul"]
        water_damage = result["nouls"]["water_damage"]["noul"]
        accepted = should_accept(
            result,
            settings.accept_correct_product_threshold,
            settings.accept_worth_price_threshold,
            settings.reject_water_damage_threshold,
        )
        print(
            json.dumps(
                {
                    "product": product,
                    "listing": listing,
                    "verdict": "ACCEPT" if accepted else "REJECT",
                    "correct_product": correct_product,
                    "worth_price": worth_price,
                    "water_damage": water_damage,
                    "thresholds": {
                        "correct_product": settings.accept_correct_product_threshold,
                        "worth_price": settings.accept_worth_price_threshold,
                        "water_damage": settings.reject_water_damage_threshold,
                    },
                },
                indent=2,
            )
        )
        if not accepted:
            return {}
        return {
            "evaluations": [
                {"product": product, "listing": listing, "decision": result}
            ]
        }

    return evaluate_listing
