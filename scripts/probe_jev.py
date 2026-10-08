import asyncio
import json

from ebay_research_agent.config import get_settings
from ebay_research_agent.jev import JevClient, should_accept
from ebay_research_agent.nodes.evaluate_listing import build_accept_questions
from ebay_research_agent.sold_values import comps_for, summarize_sold_values

SAMPLES = [
    {
        "name": "under-priced wii parts",
        "listing": {
            "product": "wii",
            "issue": "won't read discs",
            "title": "Nintendo Wii Console RVL-001 For Parts - Won't Read Discs",
            "description": "For parts or not working. Powers on but will not read game discs.",
            "price": 15.0,
            "currency": "USD",
            "shipping_cost": 10.0,
            "total_cost": "25.00",
            "totalPrice": "$25.00",
            "url": "https://example.com/item/1",
        },
    },
    {
        "name": "non-wii (game disc)",
        "listing": {
            "product": "wii",
            "issue": "unknown",
            "title": "Wii Sports Game Disc Only - Tested Works",
            "description": "Wii Sports game disc, no case. Tested and working.",
            "price": 5.0,
            "currency": "USD",
            "shipping_cost": 0.0,
            "total_cost": "5.00",
            "totalPrice": "$5.00",
            "url": "https://example.com/item/2",
        },
    },
    {
        "name": "over-priced working wii bundle",
        "listing": {
            "product": "wii",
            "issue": "unknown",
            "title": "Nintendo Wii Console Bundle - Working - Cables + 2 Remotes",
            "description": "Fully working Wii console bundle with cables and two remotes.",
            "price": 90.0,
            "currency": "USD",
            "shipping_cost": 10.0,
            "total_cost": "100.00",
            "totalPrice": "$100.00",
            "url": "https://example.com/item/3",
        },
    },
]


async def main() -> None:
    settings = get_settings()
    summary = summarize_sold_values(comps_for("wii"))
    print("=== sold-value summary ===")
    print(json.dumps(summary, indent=2))
    jev = JevClient(api_key=settings.typesafe_api_key, model=settings.typesafe_model)
    try:
        for sample in SAMPLES:
            print(f"\n=== {sample['name']} ===")
            state = {
                "product": "wii",
                "listing": sample["listing"],
                "sold_value_summary": summary,
            }
            result = await jev.evaluate(state, build_accept_questions())
            print(json.dumps(result, indent=2))
            print(
                "ACCEPTED:",
                should_accept(
                    result,
                    settings.accept_correct_product_threshold,
                    settings.accept_worth_price_threshold,
                    settings.reject_water_damage_threshold,
                ),
            )
    finally:
        await jev.close()


if __name__ == "__main__":
    asyncio.run(main())
