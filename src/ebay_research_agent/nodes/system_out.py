import json

from ebay_research_agent.state import IssuesState


def system_out(state: IssuesState) -> dict:
    print(json.dumps(state.get("combined", {}), indent=2))
    return {}
