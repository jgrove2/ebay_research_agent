import json

SYSTEM_PROMPT = (
    "You research the common issues and failure points of game consoles. "
    "First list every common problem, faulty component, and failure mode you "
    "already know about the console. If you are not fully certain the list is "
    "complete, use the web search tool to find additional common issues. "
    "Then, based on those issues, write a short blurb describing what to look "
    "for when browsing 'for parts / not working' listings for this console "
    "(which components are likely broken, what symptoms suggest a failed part, "
    "and which parts are worth harvesting for resale). If the search tool "
    "fails, base your answer only on what you already know."
)

EBAY_SYSTEM_PROMPT = (
    "You search eBay for 'for parts or not working' game console listings that "
    "could be profitable to buy, repair, or part out. Given a console, its "
    "common issues, and a blurb describing what to look for, decide a price "
    "range where the listing is cheap enough to make a profit. Use the "
    "search_ebay_for_parts tool to find listings within that range. Judge "
    "profitability by the total cost (item price plus shipping), not just the "
    "item price. Then report each listing with its title, price, shipping cost, "
    "total cost, and URL. If the search returns no results, say so."
)

EBAY_TOOL_NAME = "search_ebay_for_parts"


def issues_prompt(product: str) -> str:
    return (
        f"Console: {product}\n\n"
        f"Identify the common issues, faulty components, and failure modes for "
        f"'{product}'. Start with what you know, then search if you are unsure "
        f"or the list may be incomplete. Conclude with a short blurb describing "
        f"what to look for when browsing 'for parts' listings."
    )


def _truncate(text: str | None, limit: int = 1500) -> str:
    if not text:
        return ""
    text = text.strip()
    return text if len(text) <= limit else text[:limit] + "…"


def item_for_prompt(item: dict) -> dict:
    return {
        "title": item.get("title", ""),
        "description": _truncate(item.get("description", ""), 1500),
        "shortDescription": _truncate(item.get("short_description", ""), 500),
        "price": item.get("price"),
        "shippingCost": item.get("shipping_cost"),
        "totalCost": item.get("total_cost"),
        "url": item.get("url", ""),
    }


def judgement_prompt(product: str, items: list[dict]) -> str:
    listings_json = json.dumps([item_for_prompt(item) for item in items], indent=2)
    return (
        f"Console: {product}\n\n"
        f"Raw eBay 'for parts / not working' listings (JSON):\n{listings_json}\n\n"
        f"For each listing, review its title and description and produce a cleaned "
        f"assessment with: the console model/version (product), the primary fault "
        f"(issue, e.g. 'no power', 'disc-drive failure', \"won't read discs\", "
        f"'screen damage'), the total price including shipping (totalPrice, e.g. "
        f"'$45.00'), and the listing URL. Use 'unknown' for the issue when the "
        f"fault is not clear."
    )
