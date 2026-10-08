import json

from ebay_research_agent.state import IssuesState


def system_out(state: IssuesState) -> dict:
    combined = state.get("combined", {})
    print(json.dumps(combined, indent=2))
    with open("output.json", "w") as file:
        json.dump(combined, file, indent=2)
    return {}
