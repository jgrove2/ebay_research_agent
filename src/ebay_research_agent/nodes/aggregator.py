import json

from ebay_research_agent.state import IssuesState


def format_output(researched: list[dict], listings: list[dict]) -> str:
    lines = ["Research complete."]
    for index, result in enumerate(researched, start=1):
        lines.append(f"\n[{index}] product={result['product']}")
        lines.append("Common issues:")
        for issue in result["issues"]:
            lines.append(f"  - {issue}")
        lines.append("For-parts blurb:")
        lines.append(f"  {result['blurb']}")

    listings_by_product = {
        entry["product"]: entry.get("items", []) for entry in listings
    }
    for result in researched:
        product = result["product"]
        items = listings_by_product.get(product, [])
        lines.append(f"\neBay listings for {product}:")
        if not items:
            lines.append("  (no listings found)")
        for item in items:
            price = item.get("price")
            currency = item.get("currency") or ""
            shipping = item.get("shipping_cost")
            total = item.get("total_cost")
            lines.append(
                f"  - {item.get('title', '')} — {price} {currency} "
                f"(ship {shipping}, total {total}) — {item.get('url', '')}"
            )
    return "\n".join(lines)


def group_by_product(entries: list[dict]) -> dict:
    grouped: dict = {}
    for entry in entries:
        grouped.setdefault(entry["product"], []).append(entry)
    return grouped


def aggregate(state: IssuesState) -> dict:
    print("=== Research ===")
    print(format_output(state["results"], state["listings"]))
    print("\n=== Accepted listings ===")
    print(json.dumps(group_by_product(state.get("evaluations", [])), indent=2))
    return {}
