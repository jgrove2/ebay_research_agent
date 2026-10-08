from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from ebay_research_agent.jev import JevClient
from ebay_research_agent.nodes import (
    aggregate_listings,
    aggregate_product_listings,
    build_evaluate_listing_node,
    build_get_ebay_listings_node,
    get_product_info,
    split_by_listing,
    split_by_product,
    system_out,
)
from ebay_research_agent.state import IssuesState


def build_graph(ebay_tools: list, jev: JevClient) -> CompiledStateGraph:
    builder = StateGraph(IssuesState)

    builder.add_node("get_product_info", get_product_info)
    builder.add_node("get_ebay_listings", build_get_ebay_listings_node(ebay_tools))
    builder.add_node("evaluate_listing", build_evaluate_listing_node(jev))
    builder.add_node("aggregate_listings", aggregate_listings)
    builder.add_node("aggregate_product_listings", aggregate_product_listings)
    builder.add_node("system_out", system_out)

    builder.add_conditional_edges(START, split_by_product)
    builder.add_edge("get_product_info", "get_ebay_listings")
    builder.add_conditional_edges("get_ebay_listings", split_by_listing)
    builder.add_edge("evaluate_listing", "aggregate_listings")
    builder.add_edge("aggregate_listings", "aggregate_product_listings")
    builder.add_edge("aggregate_product_listings", "system_out")
    builder.add_edge("system_out", END)

    return builder.compile()
