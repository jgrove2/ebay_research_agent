import operator
from typing import Annotated, TypedDict


class IssuesState(TypedDict):
    products: list[str]
    product: str
    listing: dict
    results: Annotated[list[dict], operator.add]
    listings: Annotated[list[dict], operator.add]
    cleaned: Annotated[list[dict], operator.add]
    evaluations: Annotated[list[dict], operator.add]
