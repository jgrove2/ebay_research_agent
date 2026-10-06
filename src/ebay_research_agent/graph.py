import operator
from typing import Annotated, TypedDict

from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import create_react_agent
from langgraph.types import Send

from ebay_research_agent.model import get_model

SYSTEM_PROMPT = (
    "You research the naming forms of game consoles. "
    "First list every naming variant, model number, and edition you already know. "
    "If you are not fully certain the list is complete, use the DuckDuckGo search "
    "tool to find additional naming variants. Then output a final list of all known "
    "naming forms, each with a short note on what distinguishes it (model, region, "
    "or edition). If the search tool fails, say you were unable to research the "
    "naming variants."
)


class ResearchState(TypedDict):
    products: list[str]
    product: str
    results: Annotated[list[dict], operator.add]


def research_prompt(product: str) -> str:
    return (
        f"Console: {product}\n\n"
        f"Enumerate all naming variants, model numbers, and editions for "
        f"'{product}'. Start with what you know, then search if you are unsure "
        f"or the list may be incomplete."
    )


def orchestrate(state: ResearchState) -> dict:
    return {}


def fan_out(state: ResearchState) -> list[Send]:
    return [Send("research_worker", {"product": product}) for product in state["products"]]


def format_results(results: list[dict]) -> str:
    lines = ["Research complete."]
    for index, result in enumerate(results, start=1):
        lines.append(f"\n[{index}] product={result['product']}")
        lines.append(str(result["answer"]))
    return "\n".join(lines)


def build_graph(tools: list) -> CompiledStateGraph:
    worker_agent = create_react_agent(get_model(), tools, prompt=SYSTEM_PROMPT)

    builder = StateGraph(ResearchState)

    async def research_worker(state: ResearchState) -> dict:
        product = state["product"]
        result = await worker_agent.ainvoke(
            {"messages": [HumanMessage(content=research_prompt(product))]}
        )
        answer = result["messages"][-1].content
        return {"results": [{"product": product, "answer": answer}]}

    def aggregate(state: ResearchState) -> dict:
        print(format_results(state["results"]))
        return {}

    builder.add_node("orchestrator", orchestrate)
    builder.add_node("research_worker", research_worker)
    builder.add_node("aggregator", aggregate)

    builder.add_edge(START, "orchestrator")
    builder.add_conditional_edges("orchestrator", fan_out)
    builder.add_edge("research_worker", "aggregator")
    builder.add_edge("aggregator", END)

    return builder.compile()
