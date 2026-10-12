import asyncio
import json

from ebay_research_agent.config import get_settings
from ebay_research_agent.ingest import post_listings
from ebay_research_agent.state import IssuesState


def _write_output(combined: dict) -> None:
    with open("output.json", "w") as file:
        json.dump(combined, file, indent=2)


async def system_out(state: IssuesState) -> dict:
    combined = state.get("combined", {})
    print(json.dumps(combined, indent=2))
    await asyncio.to_thread(_write_output, combined)
    await post_listings(combined, get_settings())
    return {}
