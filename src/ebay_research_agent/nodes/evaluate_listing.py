import json
from collections.abc import Awaitable, Callable

from typesafe_sdk import Choice, Noul

from ebay_research_agent.config import get_settings
from ebay_research_agent.jev import JevClient, number_of_consoles, should_accept
from ebay_research_agent.state import IssuesState

Node = Callable[[IssuesState], Awaitable[dict]]


def build_accept_questions(model_numbers: list[str]) -> dict:
    return {
        "correct_product": Noul(
            instructions=(
                "Is this listing a console matching the product in the state — "
                "not a game, accessory, controller, or different console?"
            )
        ),
        "water_damage": Noul(
            instructions="Does the listing mention water damage or liquid exposure?"
        ),
        "includes_controllers": Noul(
            instructions="Does the listing include any controller(s)?"
        ),
        "includes_games": Noul(
            instructions="Does the listing include any game(s)?"
        ),
        "includes_cords": Noul(
            instructions="Does the listing include any cords or cables (power, AV, or other)?"
        ),
        "model_number": Choice(
            instructions=(
                "Which model number matches this listing? Select unknown if none match."
            ),
            criteria={**{model: None for model in model_numbers}, "unknown": None},
        ),
        "number_of_consoles": Choice(
            instructions="How many consoles are in this listing?",
            criteria={
                **{str(number): None for number in range(1, 10)},
                "10+": None,
            },
        ),
    }


def noul_value(result: dict, name: str) -> float:
    raw = result.get("nouls", {}).get(name, {}).get("noul")
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def included_flags(result: dict, threshold: float) -> dict:
    return {
        "controllers": noul_value(result, "includes_controllers") >= threshold,
        "games": noul_value(result, "includes_games") >= threshold,
        "cords": noul_value(result, "includes_cords") >= threshold,
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
        consoles = number_of_consoles(result)
        included = included_flags(result, settings.include_item_threshold)
        total_cost = listing_total_cost(listing)
        sold_average = sold_average_for(sold_value_summary, model_number)
        per_console_cost = total_cost / consoles if total_cost is not None else None
        accepted = should_accept(
            result,
            per_console_cost,
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
                    "included": included,
                    "verdict": "ACCEPT" if accepted else "REJECT",
                    "correct_product": correct_product,
                    "water_damage": water_damage,
                    "model_number": model_number,
                    "number_of_consoles": consoles,
                    "total_cost": total_cost,
                    "per_console_cost": per_console_cost,
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
                {"product": product, "listing": {**listing, "included": included}, "decision": result}
            ]
        }

    return evaluate_listing
