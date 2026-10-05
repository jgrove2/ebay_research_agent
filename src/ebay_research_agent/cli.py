import sys
from collections.abc import Iterator

from langchain_core.messages import HumanMessage

from repair_agent.config import get_settings
from repair_agent.graph import build_graph


def stream_responses(messages: list) -> Iterator[str]:
    graph = build_graph()
    config = {"configurable": {"thread_id": "cli"}}
    stream = graph.stream(
        {"messages": messages},
        config=config,
        stream_mode="updates",
    )
    for update in stream:
        for node_name, node_output in update.items():
            if node_name == "agent":
                message = node_output["messages"][-1]
                yield f"\n[{node_name}]\n{message.content}"
            elif node_name == "tools":
                yield f"\n[{node_name}] {node_output['messages'][-1].content}"
            else:
                yield f"\n[{node_name}] {node_output}"


def print_diagram() -> None:
    if not get_settings().deepseek_api_key:
        print("DEEPSEEK_API_KEY is not set. Add it to .env or your environment.")
        return
    print(build_graph().get_graph().draw_ascii())


def main() -> None:
    if "--diagram" in sys.argv:
        print_diagram()
        return
    if not get_settings().deepseek_api_key:
        print("DEEPSEEK_API_KEY is not set. Add it to .env or your environment.")
        return
    messages: list = []
    print("Repair agent (DeepSeek). Type 'exit' to quit.")
    while True:
        try:
            user_input = input("\nYou: ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if user_input.strip().lower() in {"exit", "quit"}:
            break
        messages.append(HumanMessage(content=user_input))
        for chunk in stream_responses(messages):
            print(chunk, end="")
        print()


if __name__ == "__main__":
    main()
