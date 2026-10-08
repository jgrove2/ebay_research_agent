import operator
from typing import Annotated, TypedDict


def _merge_dicts(left: dict, right: dict) -> dict:
    return {**left, **right}

class IssuesState_v2(TypedDict):
    products: list[str]
    product: str
    product_info: Annotated[dict, _merge_dicts]
    sold_product_data: Annotated[dict, _merge_dicts]

class IssuesState(TypedDict):
    products: list[str]
    product: str
    listing: dict
    results: Annotated[list[dict], operator.add]
    listings: Annotated[list[dict], operator.add]
    cleaned: Annotated[list[dict], operator.add]
    evaluations: Annotated[list[dict], operator.add]
    sold_summaries: Annotated[dict, _merge_dicts]
