from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import create_react_agent
from langgraph.types import Send

from ebay_research_agent.jev import JevClient
from ebay_research_agent.models import IssuesResult, JudgementBatch, get_model
from ebay_research_agent.nodes import (
    aggregate,
    build_evaluate_listing_node,
    build_product_worker_node,
    build_sold_summary_node,
    fan_out_listings,
    join_listings,
)
from ebay_research_agent.prompts import EBAY_SYSTEM_PROMPT, SYSTEM_PROMPT
from ebay_research_agent.state import IssuesState


def fan_out(state: IssuesState) -> list[Send]:
    return [
        Send("sold_summary", {"product": product}) for product in state["products"]
    ]


def build_graph(
    search_tools: list,
    ebay_tools: list,
    jev: JevClient,
) -> CompiledStateGraph:
    worker_agent = create_react_agent(get_model(), search_tools, prompt=SYSTEM_PROMPT)
    ebay_agent = create_react_agent(get_model(), ebay_tools, prompt=EBAY_SYSTEM_PROMPT)
    extractor = get_model().with_structured_output(IssuesResult)
    judge = get_model().with_structured_output(JudgementBatch)

    builder = StateGraph(IssuesState)

    builder.add_node(
        "sold_summary",
        build_sold_summary_node(),
    )
    builder.add_node(
        "product_worker",
        build_product_worker_node(worker_agent, ebay_agent, extractor, judge),
    )
    builder.add_node("join_listings", join_listings)
    builder.add_node("evaluate_listing", build_evaluate_listing_node(jev))
    builder.add_node("aggregator", aggregate)

    builder.add_conditional_edges(START, fan_out)
    builder.add_edge("sold_summary", "product_worker")
    builder.add_edge("product_worker", "join_listings")
    builder.add_conditional_edges("join_listings", fan_out_listings)
    builder.add_edge("evaluate_listing", "aggregator")
    builder.add_edge("aggregator", END)

    return builder.compile()
