import json
from collections.abc import Awaitable, Callable

from typesafe_sdk import Choice, Noul

from ebay_research_agent.config import get_settings
from ebay_research_agent.jev import JevClient, should_accept
from ebay_research_agent.state import IssuesState

Node = Callable[[IssuesState], Awaitable[dict]]


def build_accept_questions(model_numbers: list[str]) -> dict:
    return {
        "correct_product": Noul(
            instructions=(
                "Is this listing a console unit matching the product named in the "
                "state — not a game, accessory, controller, or a different console?"
            )
        ),
        "water_damage": Noul(
            instructions=(
                "Does the listing indicate water damage (liquid exposure, "
                "corrosion, waterlogged, or water damage)?"
            )
        ),
        "included_in_listing": Choice(
            instructions="What is included in the listing?",
            criteria={
                "console_only": "Just the console, no cords or controllers",
                "console_cords": "Console with cords, no controllers",
                "console_controllers": "Console with controllers, no cords",
                "console_cords_controllers": "Console with cords and controllers",
            },
        ),
        "model_number": Choice(
            instructions=(
                "Which model number does this listing match? If none of the known "
                "model numbers match, select unknown."
            ),
            criteria={**{model: None for model in model_numbers}, "unknown": None},
        ),
        "number_of_consoles": Choice(
            instructions="How many consoles are included in the listing?",
            criteria={
                **{str(number): None for number in range(1, 10)},
                "10+": None,
            },
        ),
    }


def listing_total_cost(listing: dict) -> float | None:
    for key in ("total_cost", "totalPrice"):
        raw = listing.get(key)
        parsed = _parse_money(raw)
        if parsed is not None:
            return parsed

    price = _parse_money(listing.get("price"))
    shipping = _parse_money(listing.get("shipping_cost"))
    if shipping is None:
        shipping = _parse_money(listing.get("shipping"))
    if price is not None and shipping is not None:
        return round(price + shipping, 2)
    return price


def _parse_money(raw: object) -> float | None:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        cleaned = raw.replace("$", "").replace(",", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def sold_average_for(sold_value_summary: dict, model: str) -> float | None:
    if not sold_value_summary:
        return None
    by_version = sold_value_summary.get("by_version", {})
    if model != "unknown" and model in by_version:
        return by_version[model].get("average")
    return sold_value_summary.get("average")


def build_evaluate_listing_node(jev: JevClient) -> Node:
    async def evaluate_listing(state: IssuesState) -> dict:
        product = state["product"]
        listing = state["listing"]
        sold_value_summary = state.get("sold_summaries", {}).get(product) or {}
        model_numbers = list(sold_value_summary.get("by_version", {}).keys())
        jev_state = {
            "product": product,
            "listing": listing,
            "sold_value_summary": sold_value_summary,
        }
        result = await jev.evaluate(jev_state, build_accept_questions(model_numbers))
        settings = get_settings()
        correct_product = result["nouls"]["correct_product"]["noul"]
        water_damage = result["nouls"]["water_damage"]["noul"]
        model_number = result["choices"]["model_number"]["choice"]
        total_cost = listing_total_cost(listing)
        sold_average = sold_average_for(sold_value_summary, model_number)
        accepted = should_accept(
            result,
            total_cost,
            sold_average,
            settings.accept_correct_product_threshold,
            settings.reject_water_damage_threshold,
            settings.accept_profit_margin,
        )
        print(
            json.dumps(
                {
                    "product": product,
                    "listing": listing,
                    "verdict": "ACCEPT" if accepted else "REJECT",
                    "correct_product": correct_product,
                    "water_damage": water_damage,
                    "model_number": model_number,
                    "total_cost": total_cost,
                    "sold_average": sold_average,
                    "profit_margin": settings.accept_profit_margin,
                    "thresholds": {
                        "correct_product": settings.accept_correct_product_threshold,
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
