import json

from ebay_research_agent.state import IssuesState_v2


def system_out(state: IssuesState_v2) -> dict:
    print(json.dumps(state.get("combined", {}), indent=2))
    return {}
