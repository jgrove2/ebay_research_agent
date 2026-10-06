import json
import operator
from typing import Annotated, TypedDict

from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import create_react_agent
from langgraph.types import Send
from pydantic import BaseModel, Field

from ebay_research_agent.model import get_model

SYSTEM_PROMPT = (
    "You research the common issues and failure points of game consoles. "
    "First list every common problem, faulty component, and failure mode you "
    "already know about the console. If you are not fully certain the list is "
    "complete, use the DuckDuckGo search tool to find additional common issues. "
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


class IssuesResult(BaseModel):
    issues: list[str] = Field(description="Common issues or failure points for the console")
    blurb: str = Field(
        description="What to look for when browsing 'for parts' listings for this console"
    )


class IssuesState(TypedDict):
    products: list[str]
    product: str
    results: Annotated[list[dict], operator.add]
    listings: Annotated[list[dict], operator.add]


def issues_prompt(product: str) -> str:
    return (
        f"Console: {product}\n\n"
        f"Identify the common issues, faulty components, and failure modes for "
        f"'{product}'. Start with what you know, then search if you are unsure "
        f"or the list may be incomplete. Conclude with a short blurb describing "
        f"what to look for when browsing 'for parts' listings."
    )


def orchestrate(state: IssuesState) -> dict:
    return {}


def fan_out(state: IssuesState) -> list[Send]:
    return [Send("issues_worker", {"product": product}) for product in state["products"]]


def format_output(researched: list[dict], listings: list[dict]) -> str:
    lines = ["Research complete."]
    for index, result in enumerate(researched, start=1):
        lines.append(f"\n[{index}] product={result['product']}")
        lines.append("Common issues:")
        for issue in result["issues"]:
            lines.append(f"  - {issue}")
        lines.append("For-parts blurb:")
        lines.append(f"  {result['blurb']}")

    listings_by_product = {entry["product"]: entry.get("items", []) for entry in listings}
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


def extract_items(messages: list) -> list[dict]:
    items: list[dict] = []
    for message in messages:
        if isinstance(message, ToolMessage) and message.name == EBAY_TOOL_NAME:
            try:
                parsed = json.loads(message.content)
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(parsed, list):
                items.extend(parsed)
    return items


def build_graph(search_tools: list, ebay_tools: list) -> CompiledStateGraph:
    worker_agent = create_react_agent(get_model(), search_tools, prompt=SYSTEM_PROMPT)
    ebay_agent = create_react_agent(get_model(), ebay_tools, prompt=EBAY_SYSTEM_PROMPT)
    extractor = get_model().with_structured_output(IssuesResult)

    builder = StateGraph(IssuesState)

    async def issues_worker(state: IssuesState) -> dict:
        product = state["product"]
        result = await worker_agent.ainvoke(
            {"messages": [HumanMessage(content=issues_prompt(product))]}
        )
        research = result["messages"][-1].content
        structured = await extractor.ainvoke(
            [
                HumanMessage(
                    content=(
                        f"Console: {product}\n\n"
                        f"Research notes:\n{research}\n\n"
                        f"Return the common issues and the for-parts blurb."
                    )
                )
            ]
        )
        return {
            "results": [
                {
                    "product": product,
                    "issues": structured.issues,
                    "blurb": structured.blurb,
                }
            ]
        }

    async def ebay_worker(state: IssuesState) -> dict:
        product = state["product"]
        researched = next(
            (result for result in state["results"] if result["product"] == product),
            None,
        )
        issues = researched["issues"] if researched else []
        blurb = researched["blurb"] if researched else ""
        prompt = (
            f"Console: {product}\n\n"
            f"Common issues:\n"
            + "\n".join(f"- {issue}" for issue in issues)
            + f"\n\nFor-parts blurb:\n{blurb}\n\n"
            f"Find 'for parts or not working' listings for this console within a "
            f"profitable price range (accounting for shipping), and report each "
            f"listing's title, price, shipping cost, total cost, and URL."
        )
        result = await ebay_agent.ainvoke({"messages": [HumanMessage(content=prompt)]})
        items = extract_items(result["messages"])
        return {"listings": [{"product": product, "items": items}]}

    def aggregate(state: IssuesState) -> dict:
        print(format_output(state["results"], state["listings"]))
        return {}

    builder.add_node("orchestrator", orchestrate)
    builder.add_node("issues_worker", issues_worker)
    builder.add_node("ebay_worker", ebay_worker)
    builder.add_node("aggregator", aggregate)

    builder.add_edge(START, "orchestrator")
    builder.add_conditional_edges("orchestrator", fan_out)
    builder.add_edge("issues_worker", "ebay_worker")
    builder.add_edge("ebay_worker", "aggregator")
    builder.add_edge("aggregator", END)

    return builder.compile()
