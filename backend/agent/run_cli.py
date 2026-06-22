"""
Interactive CLI for testing the agent end-to-end with a real LLM.

Run: python run_cli.py
Then chat with it. Try things like:
  - "what orders do I have?"
  - "my headphones arrived cracked, what do I do?"
  - "I want a refund" (should escalate, not process directly)
  - ask a question, then a FOLLOW-UP that depends on the first answer,
    to confirm short-term memory is actually working within one thread
"""

from langchain_core.messages import HumanMessage
from langgraph.types import Command
from graph import build_graph
from memory import summarize_and_save


def invoke_with_approval(app, payload, config):
    """Invoke the graph, and if it pauses on a sensitive action, ask for
    approval right here in the terminal before letting it continue."""
    result = app.invoke(payload, config=config)
    while "__interrupt__" in result:
        details = result["__interrupt__"][0].value
        print(f"\n  [APPROVAL NEEDED] Agent wants to call '{details['tool']}' with {details['args']}")
        answer = input("  Approve? (y/n): ").strip().lower()
        result = app.invoke(Command(resume=(answer in ("y", "yes"))), config=config)
    return result


def main():
    app = build_graph()

    raw = input("Customer ID to simulate (default 7 - Ananya, enterprise tier): ").strip()
    customer_id = int(raw) if raw else 7

    # thread_id is the checkpointer's key for "which conversation is this."
    # Same thread_id across calls = same memory. Change it to start fresh.
    thread_id = f"customer-{customer_id}-cli-session"
    config = {"configurable": {"thread_id": thread_id}}

    print(f"\nChatting as customer_id={customer_id}. Type 'quit' to exit.\n")

    final_state = None
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("quit", "exit"):
            break
        if not user_input:
            continue

        result = invoke_with_approval(
            app,
            {"messages": [HumanMessage(content=user_input)], "customer_id": customer_id},
            config,
        )
        final_state = result
        last_message = result["messages"][-1]
        print(f"Agent: {last_message.content}\n")

    if final_state is not None:
        print("\nSaving conversation to long-term memory...")
        new_summary = summarize_and_save(customer_id, final_state["messages"])
        print(f"Updated memory for customer {customer_id}:\n{new_summary}\n")


if __name__ == "__main__":
    main()