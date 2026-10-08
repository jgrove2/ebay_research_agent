import operator
from typing import Annotated, TypedDict


def _merge_dicts(left: dict, right: dict) -> dict:
    return {**left, **right}

class IssuesState(TypedDict):
    products: list[str]
    product: str
    listing: dict
    product_info: Annotated[dict, _merge_dicts]
    sold_product_data: Annotated[dict, _merge_dicts]
    sold_summaries: Annotated[dict, _merge_dicts]
    listings: Annotated[dict, _merge_dicts]
    evaluations: Annotated[list[dict], operator.add]
    evaluations_by_product: dict
    combined: dict
